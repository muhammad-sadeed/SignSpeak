"""
FastAPI WebSocket server for the ASL interpreter.

Wraps the existing SignPredictor + WordAssembler + MediaPipe Hands pipeline
(the same logic as main.py) so a web frontend can stream webcam frames and
receive translated text + hand landmarks.

Run from the backend/ directory:
    uvicorn src.server:app --reload --port 8000
"""
import os
import sys
import json
import asyncio

# Ensure sibling modules (predictor, word_assembler) are importable when this
# file is loaded as `src.server` (the `src` namespace package doesn't add its
# own directory to sys.path).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
import mediapipe as mp
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from predictor import SignPredictor
from word_assembler import WordAssembler

mp_hands = mp.solutions.hands

app = FastAPI(title="SignSpeak API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the MediaPipe Hands instance and the PyTorch model once at startup.
# MediaPipe Hands is not thread-safe, so all calls are serialized via _lock.
_hands = mp_hands.Hands(
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
    max_num_hands=1,
)

try:
    _predictor = SignPredictor()
    print(f"Model loaded successfully on {_predictor.device}")
except (FileNotFoundError, ImportError, RuntimeError) as e:
    print(f"Model not available: {e}")
    print("Running in hand-tracking-only mode (no letter predictions).")
    _predictor = None

_lock = asyncio.Lock()


def process_frame(jpeg_bytes: bytes, assembler: WordAssembler) -> dict | None:
    """Decode a JPEG frame and run the full ASL pipeline for one frame."""
    frame = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return None

    frame = cv2.flip(frame, 1)  # mirror, matching main.py / training orientation
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = _hands.process(image_rgb)

    letter = None
    landmarks = None
    hand_detected = False

    if results.multi_hand_landmarks:
        hand_detected = True
        hand_landmarks = results.multi_hand_landmarks[0]
        landmarks = [[lm.x, lm.y] for lm in hand_landmarks.landmark]

        if _predictor is not None:
            raw = _predictor.predict(hand_landmarks.landmark)
            if raw == "space":
                assembler._finalize_word()
            elif raw == "del":
                assembler.undo()
            elif raw == "nothing":
                pass
            else:
                letter = raw

    assembler.update(letter)

    return {
        "letter": assembler.current_letter,
        "word": assembler.current_word,
        "sentence": assembler.sentence,
        "hand_detected": hand_detected,
        "landmarks": landmarks,
    }


def _state_snapshot(assembler: WordAssembler, hand_detected: bool = False,
                    landmarks: list | None = None) -> dict:
    return {
        "letter": assembler.current_letter,
        "word": assembler.current_word,
        "sentence": assembler.sentence,
        "hand_detected": hand_detected,
        "landmarks": landmarks,
    }


@app.get("/")
async def health():
    return {"status": "ok", "model_loaded": _predictor is not None}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Per-connection state, tuned identically to main.py.
    assembler = WordAssembler(
        word_cooldown_frames=60,
        min_consecutive_frames=8,
        same_letter_cooldown_frames=30,
    )

    try:
        while True:
            msg = await websocket.receive()

            if msg.get("bytes"):
                async with _lock:
                    state = await asyncio.to_thread(
                        process_frame, msg["bytes"], assembler
                    )
                if state is not None:
                    await websocket.send_text(json.dumps(state))

            elif msg.get("text"):
                try:
                    ctrl = json.loads(msg["text"])
                except json.JSONDecodeError:
                    continue
                if ctrl.get("type") == "reset":
                    assembler.reset()
                    await websocket.send_text(
                        json.dumps(_state_snapshot(assembler))
                    )
    except WebSocketDisconnect:
        pass

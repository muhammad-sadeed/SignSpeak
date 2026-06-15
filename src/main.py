import cv2
import mediapipe as mp
from predictor import SignPredictor
from word_assembler import WordAssembler

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
    max_num_hands=1,
)

try:
    predictor = SignPredictor()
    print(f"Model loaded successfully on {predictor.device}")
except (FileNotFoundError, ImportError, RuntimeError) as e:
    print(f"Model not available: {e}")
    print("Running in hand-tracking-only mode.")
    predictor = None

word_assembler = WordAssembler(word_cooldown_frames=60, min_consecutive_frames=8, same_letter_cooldown_frames=30)


def draw_overlay(frame, letter, word, sentence):
    h, w = frame.shape[:2]

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 140), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)

    cv2.putText(frame, f"Letter: {letter or '?'}",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
    cv2.putText(frame, f"Word: {word or '...'}",
                (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(frame, f"Sentence: {sentence}",
                (20, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    return frame


cap = cv2.VideoCapture(0)
print("Press 'q' to quit, 'r' to reset sentence.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(image_rgb)

    letter = None

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(
                frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
            )

            if predictor is not None:
                raw = predictor.predict(hand_landmarks.landmark)

                if raw == "space":
                    word_assembler._finalize_word()
                elif raw == "del":
                    word_assembler.undo()
                elif raw == "nothing":
                    pass
                else:
                    letter = raw

    word_assembler.update(letter)

    frame = draw_overlay(
        frame,
        word_assembler.current_letter,
        word_assembler.current_word,
        word_assembler.sentence,
    )

    cv2.imshow("SignSpeak - Hand Tracking", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break
    elif key == ord("r"):
        word_assembler.reset()

cap.release()
cv2.destroyAllWindows()

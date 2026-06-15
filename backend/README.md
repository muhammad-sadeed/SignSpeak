# SignSpeak — Real-Time ASL Fingerspelling Interpreter

Converts American Sign Language fingerspelling into text in real time using your webcam. MediaPipe extracts 21 hand landmarks per frame, and a lightweight PyTorch MLP classifies each gesture into letters (A–Z), space, delete, or nothing.

Requirements: Python 3.11+

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
pip install -r requirements.txt
```

## Run

```bash
python src/main.py
```

- Show an ASL letter to the camera — it appears on screen.
- Hold your hand still to type a word; remove it to finalize.
- Press **Q** to quit, **R** to reset the sentence.

## Controls

| Gesture | Effect |
|---------|--------|
| A–Z hand sign | Types the letter |
| Empty/open palm | Space (finalizes current word) |
| Closed fist / thumb down | Delete (removes last letter) |
| No hand detected for ~2s | Finalizes word |

## Project Structure

```
├── src/
│   ├── main.py              # Webcam loop, MediaPipe, UI overlay
│   ├── predictor.py          # MLP inference on 63D landmark vectors
│   └── word_assembler.py     # Letter deduplication, word/sentence assembly
├── models/
│   └── landmark_model.pth    # Trained MLP weights
├── data/
│   └── label_encoder.pkl     # Class label mapping
├── scripts/
│   ├── train_landmark_model.py  # Train from scratch on ASL Alphabet dataset
│   └── diagnose_model.py        # Inspect PyTorch model files
└── requirements.txt
```

## Training from Scratch

The pretrained model is included in `models/`. To retrain with your own data:

```bash
pip install kagglehub scikit-learn
python scripts/train_landmark_model.py
```

This downloads the [ASL Alphabet dataset](https://www.kaggle.com/datasets/grassknoted/asl-alphabet) (87K images, 29 classes), extracts 21 hand landmarks via MediaPipe, trains a 4-layer MLP, and saves the model to `landmark_model.pth`.

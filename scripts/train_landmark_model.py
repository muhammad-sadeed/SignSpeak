"""
Train a coordinate-based ASL sign language model using MediaPipe hand landmarks.

This script:
1. Downloads the ASL Alphabet dataset from Kaggle (87K images, 29 classes)
2. Extracts 21 hand landmarks (x,y,z) per image via MediaPipe
3. Trains a lightweight MLP classifier on the 63D landmark vectors
4. Saves the model as .pth for use in predictor.py
5. Saves pre-extracted landmarks as .npz for faster retraining

Usage:
    pip install kagglehub mediapipe torch scikit-learn
    python train_landmark_model.py

The dataset maps to your existing 29 classes:
    A-Z (26 letters) + del + nothing + space
"""
import os
import sys
import pickle
from collections import Counter

import numpy as np
import cv2

# ---------- config ----------
DATASET = "grassknoted/asl-alphabet"
DATA_DIR = "asl_alphabet_data"
LANDMARKS_FILE = "landmarks.npz"
MODEL_OUT = "landmark_model.pth"
ENCODER_OUT = "label_encoder.pkl"
INPUT_DIM = 21 * 3  # 63
HIDDEN_DIMS = [256, 128, 64]
NUM_CLASSES = 29
BATCH_SIZE = 2048
EPOCHS = 80
LR = 1e-3
MIN_CONFIDENCE = 20  # min samples per class to keep it

# ---------- step 1: download dataset ----------
def download_dataset():
    print("\n📥 Downloading ASL Alphabet dataset...")
    try:
        import kagglehub
    except ImportError:
        print("kagglehub not installed. Run: pip install kagglehub")
        sys.exit(1)

    path = kagglehub.dataset_download(DATASET)
    print(f"Downloaded to: {path}")
    return path


# ---------- step 2: extract landmarks ----------
def extract_landmarks(dataset_path):
    print("\n🖐️  Extracting MediaPipe hand landmarks...")

    try:
        import mediapipe as mp
    except ImportError:
        print("mediapipe not installed. Run: pip install mediapipe")
        sys.exit(1)

    mp_hands = mp.solutions.hands

    # ASL Alphabet structure: asl_alphabet_train/asl_alphabet_train/{A,B,C,...,space,nothing,del}/
    train_dir = None
    for root, dirs, files in os.walk(dataset_path):
        for d in dirs:
            if d == "asl_alphabet_train":
                candidate = os.path.join(root, d)
                # The class dirs (A, B, C, ...) might be directly inside
                # or one more level down (nested asl_alphabet_train).
                inner_contents = os.listdir(candidate)
                if inner_contents and os.path.isdir(os.path.join(candidate, inner_contents[0])):
                    first = inner_contents[0]
                    if first in ["A", "space", "nothing", "del"] or first == "asl_alphabet_train":
                        if first == "asl_alphabet_train":
                            train_dir = os.path.join(candidate, first)
                        else:
                            train_dir = candidate
                        break
                else:
                    train_dir = candidate
                    break
        if train_dir:
            break

    if train_dir is None:
        train_dir = dataset_path

    print(f"Training directory: {train_dir}")

    class_dirs = sorted(
        d for d in os.listdir(train_dir)
        if os.path.isdir(os.path.join(train_dir, d)) and d != "__MACOSX"
    )
    print(f"Found {len(class_dirs)} class directories: {class_dirs}")

    all_landmarks = []
    all_labels = []

    with mp_hands.Hands(
        static_image_mode=True,
        max_num_hands=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as hands:
        for class_name in class_dirs:
            class_path = os.path.join(train_dir, class_name)
            image_files = [
                f for f in os.listdir(class_path)
                if f.lower().endswith((".jpg", ".jpeg", ".png"))
            ]

            print(f"  Processing '{class_name}': {len(image_files)} images...", end=" ", flush=True)
            count = 0

            for img_file in image_files:
                img_path = os.path.join(class_path, img_file)
                image = cv2.imread(img_path)
                if image is None:
                    continue

                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = hands.process(image_rgb)

                if results.multi_hand_landmarks:
                    hand = results.multi_hand_landmarks[0]  # first hand only
                    coords = []
                    for lm in hand.landmark:
                        coords.extend([lm.x, lm.y, lm.z])
                    all_landmarks.append(coords)
                    all_labels.append(class_name)
                    count += 1

            print(f"extracted {count}")

    X = np.array(all_landmarks, dtype=np.float32)
    y = np.array(all_labels)

    print(f"\nTotal samples: {len(X)}")
    print(f"Class distribution:")
    for cls, cnt in sorted(Counter(y).items()):
        print(f"  {cls}: {cnt}")

    return X, y


# ---------- step 3: encode labels ----------
def encode_labels(y):
    from sklearn.preprocessing import LabelEncoder

    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    print(f"\nLabel mapping ({len(le.classes_)} classes):")
    for i, cls in enumerate(le.classes_):
        print(f"  {i}: {cls}")

    # Verify this matches the expected 29-class layout
    # A=0, B=1, ..., Z=25, del=26, nothing=27, space=28
    return y_enc, le


# ---------- step 4: train model ----------
def train_model(X, y_enc, num_classes):
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    print("\n🧠 Training landmark-based MLP model...")

    # Normalize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train/val split
    X_train, X_val, y_train, y_val = train_test_split(
        X_scaled, y_enc, test_size=0.15, random_state=42, stratify=y_enc
    )

    X_train_t = torch.tensor(X_train, dtype=torch.float32)
    y_train_t = torch.tensor(y_train, dtype=torch.long)
    X_val_t = torch.tensor(X_val, dtype=torch.float32)
    y_val_t = torch.tensor(y_val, dtype=torch.long)

    train_loader = DataLoader(
        TensorDataset(X_train_t, y_train_t),
        batch_size=BATCH_SIZE, shuffle=True
    )
    val_loader = DataLoader(
        TensorDataset(X_val_t, y_val_t),
        batch_size=BATCH_SIZE, shuffle=False
    )

    # Build MLP
    layers = []
    prev_dim = INPUT_DIM
    for h_dim in HIDDEN_DIMS:
        layers.extend([
            nn.Linear(prev_dim, h_dim),
            nn.BatchNorm1d(h_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
        ])
        prev_dim = h_dim
    layers.append(nn.Linear(prev_dim, num_classes))

    model = nn.Sequential(*layers)
    print(f"Model: {model}")

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_val_acc = 0
    best_state = None

    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0

        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * batch_x.size(0)
            preds = logits.argmax(dim=1)
            train_correct += (preds == batch_y).sum().item()
            train_total += batch_x.size(0)

        scheduler.step()

        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                logits = model(batch_x)
                preds = logits.argmax(dim=1)
                val_correct += (preds == batch_y).sum().item()
                val_total += batch_x.size(0)

        train_acc = train_correct / train_total
        val_acc = val_correct / val_total

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        if epoch % 5 == 0 or epoch == 1:
            print(f"  Epoch {epoch:3d}/{EPOCHS} | "
                  f"train loss: {train_loss/train_total:.4f} | "
                  f"train acc: {train_acc:.4f} | "
                  f"val acc: {val_acc:.4f}")

    print(f"\n✅ Best validation accuracy: {best_val_acc:.4f} ({best_val_acc*100:.2f}%)")

    model.load_state_dict(best_state)
    return model, scaler


# ---------- step 5: save artifacts ----------
def save_artifacts(model, scaler, label_encoder, X, y_enc):
    import torch

    print("\n💾 Saving model and artifacts...")

    state = {
        "state_dict": model.state_dict(),
        "input_dim": INPUT_DIM,
        "hidden_dims": HIDDEN_DIMS,
        "num_classes": NUM_CLASSES,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
    }
    torch.save(state, MODEL_OUT)
    print(f"  Model saved to: {MODEL_OUT}")

    with open(ENCODER_OUT, "wb") as f:
        pickle.dump(label_encoder, f)
    print(f"  Label encoder saved to: {ENCODER_OUT}")

    np.savez_compressed(LANDMARKS_FILE, X=X, y=y_enc)
    print(f"  Pre-extracted landmarks saved to: {LANDMARKS_FILE}")


# ---------- main ----------
def main():
    print("=" * 60)
    print("COORDINATE-BASED ASL LANDMARK MODEL TRAINER")
    print("=" * 60)

    # Step 1: Download
    dataset_path = download_dataset()

    # Step 2: Extract landmarks (or load cached)
    if os.path.exists(LANDMARKS_FILE):
        print(f"\n📂 Found cached landmarks: {LANDMARKS_FILE}")
        data = np.load(LANDMARKS_FILE)
        X = data["X"]
        y_enc = data["y"]
        with open(ENCODER_OUT, "rb") as f:
            le = pickle.load(f)
        print(f"Loaded {len(X)} samples, {len(le.classes_)} classes")
    else:
        X, y_raw = extract_landmarks(dataset_path)
        if len(X) == 0:
            print("ERROR: No landmarks extracted. Check dataset path or MediaPipe installation.")
            sys.exit(1)
        y_enc, le = encode_labels(y_raw)
        np.savez_compressed(LANDMARKS_FILE, X=X, y=y_enc)
        with open(ENCODER_OUT, "wb") as f:
            pickle.dump(le, f)
        print(f"Saved landmarks to {LANDMARKS_FILE} and encoder to {ENCODER_OUT}")

    # Step 3: Train
    model, scaler = train_model(X, y_enc, len(le.classes_))

    # Step 4: Save
    save_artifacts(model, scaler, le, X, y_enc)

    print("\n" + "=" * 60)
    print("DONE! You can now use landmark_model.pth in predictor.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

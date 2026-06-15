"""
SignPredictor: loads a PyTorch MLP model trained on MediaPipe hand landmarks
and runs inference on 63D landmark vectors extracted from the webcam feed.

The model was trained on 21 hand landmarks (x, y, z) = 63 features.
"""
import os
import pickle

import numpy as np

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_BASE_DIR)

MODEL_PATH = os.path.join(_PROJECT_ROOT, "models", "landmark_model.pth")
ENCODER_PATH = os.path.join(_PROJECT_ROOT, "data", "label_encoder.pkl")
MODEL_DEVICE = "cpu"
CONFIDENCE_THRESHOLD = 0.6
DEBUG_TOPK = 0

_torch = None


def _import_torch():
    global _torch
    if _torch is None:
        try:
            import torch as _t
        except ImportError:
            raise ImportError(
                "PyTorch is required. Install with: pip install torch"
            )
        _torch = _t
    return _torch


def _build_mlp(input_dim, hidden_dims, num_classes):
    torch_obj = _import_torch()
    nn = torch_obj.nn

    layers = []
    prev_dim = input_dim
    for h_dim in hidden_dims:
        layers.extend([
            nn.Linear(prev_dim, h_dim),
            nn.BatchNorm1d(h_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
        ])
        prev_dim = h_dim
    layers.append(nn.Linear(prev_dim, num_classes))
    return nn.Sequential(*layers)


class SignPredictor:
    def __init__(
        self,
        model_path=MODEL_PATH,
        device=MODEL_DEVICE,
        confidence_threshold=CONFIDENCE_THRESHOLD,
    ):
        torch_obj = _import_torch()
        self._torch = torch_obj
        self.device = torch_obj.device(device)
        self.confidence_threshold = confidence_threshold

        self.model, self.scaler_mean, self.scaler_scale, self.le = (
            self._load_model(model_path)
        )
        self.model.to(self.device)
        self.model.eval()

    def _load_model(self, model_path):
        model_path = os.path.expanduser(model_path)
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        checkpoint = self._torch.load(
            model_path, map_location=self.device, weights_only=True
        )

        input_dim = checkpoint["input_dim"]
        hidden_dims = checkpoint["hidden_dims"]
        num_classes = checkpoint["num_classes"]

        model = _build_mlp(input_dim, hidden_dims, num_classes)
        model.load_state_dict(checkpoint["state_dict"])

        scaler_mean = np.array(checkpoint["scaler_mean"], dtype=np.float32)
        scaler_scale = np.array(checkpoint["scaler_scale"], dtype=np.float32)

        with open(ENCODER_PATH, "rb") as f:
            le = pickle.load(f)

        print(f"Loaded landmark model: {num_classes} classes, input_dim={input_dim}")
        return model, scaler_mean, scaler_scale, le

    def predict(self, landmarks) -> str | None:
        """
        landmarks: list of 21 MediaPipe landmark objects (each with .x, .y, .z)
        Returns predicted label string, or None if confidence below threshold.
        """
        coords = []
        for lm in landmarks:
            coords.extend([lm.x, lm.y, lm.z])
        vec = np.array(coords, dtype=np.float32)

        vec = (vec - self.scaler_mean) / (self.scaler_scale + 1e-8)
        tensor = self._torch.tensor(vec, dtype=self._torch.float32, device=self.device)
        tensor = tensor.unsqueeze(0)

        with self._torch.no_grad():
            logits = self.model(tensor)
            probs = self._torch.softmax(logits, dim=1)
            topk_values, topk_indices = self._torch.topk(
                probs, max(3, DEBUG_TOPK), dim=1
            )
            confidence = topk_values[0, 0]
            pred_idx = topk_indices[0, 0]

        if DEBUG_TOPK:
            labels = [self.le.classes_[i.item()] for i in topk_indices[0]]
            print(" ".join(
                f"{l}:{v.item():.2f}" for l, v in zip(labels, topk_values[0])
            ))

        if confidence.item() < self.confidence_threshold:
            return None

        return self.le.classes_[pred_idx.item()]

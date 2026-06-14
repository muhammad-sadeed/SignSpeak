"""
SignPredictor: loads an EfficientNet-B3 PyTorch model and runs inference on
cropped hand images from the webcam feed.

The model was trained on 300x300 RGB images of hand signs.
"""
import os

import cv2
import numpy as np

from labels import idx_to_label, NUM_CLASSES

MODEL_PATH = "landmark_model.pth"
MODEL_DEVICE = "cpu"
CONFIDENCE_THRESHOLD = 0.1
DEBUG_TOPK = 0

_torch = None


def _import_torch():
    global _torch
    if _torch is None:
        try:
            import torch as _t
        except ImportError:
            raise ImportError(
                "PyTorch is required. Install with: pip install torch torchvision"
            )
        _torch = _t
    return _torch


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

        self.model = self._load_model(model_path)
        self.model.to(self.device)
        self.model.eval()

        self.input_size = 300
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def _load_model(self, model_path):
        model_path = os.path.expanduser(model_path)
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        import timm
        state_dict = self._torch.load(
            model_path, map_location=self.device, weights_only=True
        )
        model = timm.create_model(
            "efficientnet_b3", pretrained=False, num_classes=NUM_CLASSES
        )
        model.load_state_dict(state_dict)
        return model

    def predict(self, hand_image: np.ndarray) -> str | None:
        img = cv2.resize(hand_image, (self.input_size, self.input_size))
        img = img.astype(np.float32) / 255.0
        img = (img - self.mean) / self.std
        img = img.transpose(2, 0, 1)

        tensor = self._torch.tensor(img, dtype=self._torch.float32, device=self.device)
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
            print(
                " ".join(
                    f"{idx_to_label(topk_indices[0, i].item())}:{topk_values[0, i].item():.2f}"
                    for i in range(DEBUG_TOPK)
                )
            )

        if confidence.item() < self.confidence_threshold:
            return None

        return idx_to_label(pred_idx.item())

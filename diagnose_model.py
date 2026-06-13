import sys
import os
import argparse
from collections import OrderedDict


def diagnose_model(model_path: str):
    model_path = os.path.expanduser(model_path)

    if not os.path.exists(model_path):
        sys.exit(f"Model file not found: {model_path}")

    print(f"Diagnosing: {model_path}")
    print(f"File size: {os.path.getsize(model_path) / (1024 * 1024):.1f} MB\n")

    try:
        import torch
    except ImportError:
        sys.exit(
            "PyTorch is not installed. Run:\n"
            "  pip install torch torchvision\n"
            "Then try again."
        )

    torch.set_printoptions(precision=4, sci_mode=False)

    # --- Attempt 1: torch.load ---
    print("=" * 60)
    print("ATTEMPT 1: torch.load()")
    print("=" * 60)
    try:
        obj = torch.load(model_path, map_location="cpu", weights_only=False)
    except Exception as e:
        print(f"  FAILED: {e}")
        obj = None

    if obj is not None:
        obj_type = type(obj)

        if obj_type is OrderedDict or obj_type is dict:
            print(f"  Type: state_dict ({len(obj)} keys)\n")
            analyze_state_dict(obj)
            print()
            generate_architecture_class(obj)

        elif isinstance(obj, torch.nn.Module):
            print(f"  Type: full nn.Module ({obj.__class__.__name__})\n")
            print(f"  Architecture:\n{obj}\n")
            print("  RESULT: This model can be loaded directly with torch.load().")
            print("  UPDATE predictor.py and set MODEL_LOAD_MODE = 'full'")

        else:
            print(f"  Type: {obj_type}")
            print("  This doesn't look like a standard model file.")
            print("  Checking for nested objects...")
            if hasattr(obj, "state_dict"):
                try:
                    sd = obj.state_dict()
                    print(f"  Found state_dict() method — {len(sd)} keys")
                    analyze_state_dict(sd)
                    generate_architecture_class(sd)
                except Exception as e:
                    print(f"  state_dict() failed: {e}")

    # --- Attempt 2: torch.jit.load ---
    print("\n" + "=" * 60)
    print("ATTEMPT 2: torch.jit.load() (TorchScript)")
    print("=" * 60)
    try:
        jit_model = torch.jit.load(model_path, map_location="cpu")
        print(f"  SUCCESS: TorchScript model loaded.")
        print(f"  Module: {jit_model.__class__.__name__}")
        test_shape = list(jit_model.parameters())[0].shape if list(jit_model.parameters()) else "unknown"
        print(f"  First parameter shape: {test_shape}")
        print("  RESULT: This is a TorchScript model.")
        print("  UPDATE predictor.py and set MODEL_LOAD_MODE = 'torchscript'")
    except Exception as e:
        print(f"  Not a TorchScript model: {e}")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("1. Check the results above to determine MODEL_LOAD_MODE in predictor.py")
    print("2. If a skeleton architecture class was generated above, copy it into predictor.py")
    print("3. Verify labels.py has the correct number of classes (currently 26: A-Z)")
    print("4. Run main.py to test the full pipeline")


def analyze_state_dict(state_dict):
    keys = list(state_dict.keys())
    print(f"  --- Layer Keys ({len(keys)} total) ---")
    for k in keys:
        shape = tuple(state_dict[k].shape)
        print(f"    {k}  →  {shape}")

    num_weights = sum(1 for k in keys if "weight" in k)
    num_biases = sum(1 for k in keys if "bias" in k)
    print(f"\n  Weights: {num_weights}, Biases: {num_biases}")

    input_dim = state_dict[keys[0]].shape[1] if len(state_dict[keys[0]].shape) >= 2 else state_dict[keys[0]].shape[0]
    output_dim = state_dict[keys[-1]].shape[0] if len(state_dict[keys[-1]].shape) >= 2 else state_dict[keys[-1]].shape[0]

    print(f"  Inferred input dim: {input_dim}")
    print(f"  Inferred output dim: {output_dim} (num classes)")

    if output_dim == 63:
        print("  WARNING: Output dim is 63 — this might be 21 landmarks × 3 coords.")
        print("  The model may not be for classification. Check with your friend.")
    elif output_dim == 26:
        print("  Output dim is 26 — matches A-Z labels. Looks correct!")
    elif output_dim == 27:
        print("  Output dim is 27 — probably A-Z + extra class (space/nothing).")
    else:
        print(f"  Output dim is {output_dim} — update NUM_CLASSES in labels.py if needed.")


def generate_architecture_class(state_dict):
    keys = list(state_dict.keys())
    num_layers = sum(1 for k in keys if "weight" in k)

    print(f"\n  --- Generated Skeleton Architecture ({num_layers}-layer MLP) ---")
    print("  Copy this class into predictor.py:")
    print()

    # Extract dimensions from state_dict, but ONLY from Linear layer weights.
    # Linear weights are 2D (out, in). BatchNorm weights are 1D (dim,) — skip those.
    dims = []
    for k in keys:
        if "weight" in k:
            shape = state_dict[k].shape
            if len(shape) == 2:
                dims.append((shape[1], shape[0]))

    if len(dims) >= 2:
        # Check if there are non-linear layers (BatchNorm, Dropout, etc.)
        has_bn = any(
            "bn" in k.lower() or "norm" in k.lower() or "batchnorm" in k.lower()
            for k in keys
        )
        has_dropout = any(
            "dropout" in k.lower() or "drop" in k.lower() for k in keys
        )

        layers_with_activation = []
        for i, (in_f, out_f) in enumerate(dims):
            layers_with_activation.append(f"            nn.Linear({in_f}, {out_f}),")
            if i < len(dims) - 1:
                if has_bn:
                    layers_with_activation.append(f"            nn.BatchNorm1d({out_f}),")
                layers_with_activation.append(f"            nn.ReLU(),")
                if has_dropout:
                    layers_with_activation.append(f"            nn.Dropout(0.5),")

        layers_with_activation_str = "\n".join(layers_with_activation)

        code = f'''
import torch.nn as nn

class SignModel(nn.Module):
    def __init__(self, num_classes={dims[-1][1]}):
        super().__init__()
        self.model = nn.Sequential(
{layers_with_activation_str}
        )

    def forward(self, x):
        return self.model(x)
'''
        print(code)

        print(f"  NOTE: The generated class assumes ReLU activations.")
        print(f"  If your model uses something else (SiLU, Tanh, GELU), replace nn.ReLU().")
        print(f"  BatchNorm={has_bn}, Dropout={has_dropout} detected from key names.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diagnose a saved PyTorch model")
    parser.add_argument("model_path", nargs="?", default="model.pth",
                        help="Path to the .pt/.pth model file (default: model.pth)")
    args = parser.parse_args()
    diagnose_model(args.model_path)

import sys

sys.path.insert(0, "/opt/CGCPT")
import joblib
import json
from pathlib import Path

models_dir = Path("/opt/CGCPT/models")
for pkl in models_dir.glob("*.pkl"):
    model_id = pkl.stem
    meta_path = models_dir / f"{model_id}_meta.json"
    if meta_path.exists():
        print(f"  Skip {model_id} (meta exists)")
        continue
    try:
        data = joblib.load(pkl)
        model = data.get("model", data)
        scaler = data.get("scaler", None)
        needs_scaling = data.get("needs_scaling", False)
        feature_keys = data.get("feature_keys", [])

        n_classes = len(model.classes_) if hasattr(model, "classes_") else 0

        meta = {
            "model_id": model_id,
            "created": str(pkl.stat().st_mtime),
            "test_accuracy": 0,
            "train_accuracy": 0,
            "n_samples": 0,
            "n_classes": n_classes,
            "best_params": {
                "model_type": type(model).__name__,
                "needs_scaling": needs_scaling,
                "n_features": len(feature_keys),
            },
            "feature_keys": feature_keys,
        }

        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
        print(f"  Created meta for {model_id}: {n_classes} classes, {len(feature_keys)} features")
    except Exception as e:
        print(f"  Error {model_id}: {e}")

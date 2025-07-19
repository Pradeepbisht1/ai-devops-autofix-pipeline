"""
Run locally:

    # default demo row
    python ml_model/predict_failure.py

    # custom row via 1‑line JSON
    python ml_model/predict_failure.py \
        --input-json '{"build_time":250,"error_count":7,"cpu_usage":60,"test_pass_rate":0.70}'

    # CI mode – print only numeric probability
    python ml_model/predict_failure.py --plain \
        --input-json '{"build_time":250,"error_count":7,"cpu_usage":60,"test_pass_rate":0.70}'
"""

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

# ------------------------------------------------------------------ #
# 1. Load the trained model (path‑safe, works from any CWD)
# ------------------------------------------------------------------ #
ROOT = Path(__file__).parent  # …/ml_model
MODEL_PATH = ROOT / "models" / "model.pkl"
model = joblib.load(MODEL_PATH)

# ------------------------------------------------------------------ #
# 2. CLI – optional custom JSON row + plain numeric mode
# ------------------------------------------------------------------ #
parser = argparse.ArgumentParser()
parser.add_argument(
    "--input-json",
    help="Single JSON object with build metrics; defaults to demo row if omitted.",
)
parser.add_argument(
    "--plain",
    action="store_true",
    help="Print only raw failure probability (0‑1) for CI/CD pipelines.",
)
args = parser.parse_args()

sample_dict: dict
if args.input_json:
    sample_dict = json.loads(args.input_json)
else:
    # fallback demo row
    sample_dict = {
        "build_time": 250,
        "error_count": 7,
        "cpu_usage": 60.0,
        "test_pass_rate": 0.70,
    }

# ------------------------------------------------------------------ #
# 3. Convert to DataFrame (model was trained on same feature order)
# ------------------------------------------------------------------ #
row = pd.DataFrame([sample_dict])

# ------------------------------------------------------------------ #
# 4. Predict
# ------------------------------------------------------------------ #
prob_failure = model.predict_proba(row)[0][1]  # probability of class 1 (failure)
pred_label = int(prob_failure >= 0.5)  # threshold 0.5; adjust if needed

if args.plain:
    # CI mode – emit only numeric value with 4‑dec precision
    print(f"{prob_failure:.4f}")
else:
    status = "Failure" if pred_label else "Success"
    print(f"Predicted Status       : {status}")
    print(f"Failure Probability    : {prob_failure:.2%}")

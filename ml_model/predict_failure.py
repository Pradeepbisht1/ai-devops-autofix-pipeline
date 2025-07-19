"""
Run locally:

    # default demo row
    python ml_model/predict_failure.py

    # custom row via 1‑line JSON
    python ml_model/predict_failure.py \
        --input-json '{"build_time":250,"error_count":7,"cpu_usage":60,"test_pass_rate":0.70}'
"""

import argparse, json, joblib, pandas as pd
from pathlib import Path

# ------------------------------------------------------------------ #
# 1.  Load the trained model (path‑safe, works from any CWD)
# ------------------------------------------------------------------ #
ROOT   = Path(__file__).parent                # …/ml_model
MODEL  = ROOT / "models" / "model.pkl"
model  = joblib.load(MODEL)

# ------------------------------------------------------------------ #
# 2.  CLI – optional custom JSON row
# ------------------------------------------------------------------ #
parser = argparse.ArgumentParser()
parser.add_argument(
    "--input-json",
    help="single JSON object with build metrics; "
         "defaults to demo row if omitted",
)
args = parser.parse_args()

if args.input_json:
    sample_dict = json.loads(args.input_json)
else:  # fallback demo
    sample_dict = {
        "build_time": 250,
        "error_count": 7,
        "cpu_usage": 60.0,
        "test_pass_rate": 0.70,
    }

# ------------------------------------------------------------------ #
# 3.  Convert to DataFrame (model was trained on same feature order)
# ------------------------------------------------------------------ #
row = pd.DataFrame([sample_dict])

# ------------------------------------------------------------------ #
# 4.  Predict
# ------------------------------------------------------------------ #
pred       = model.predict(row)[0]                      # 0 = success, 1 = failure
fail_prob  = model.predict_proba(row)[0][1]             # prob of failure (class 1)

print(f"Predicted Status       : {'Failure' if pred else 'Success'}")
print(f"Failure Probability    : {fail_prob:.2%}")

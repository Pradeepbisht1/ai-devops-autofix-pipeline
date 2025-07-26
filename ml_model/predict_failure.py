"""
Run locally:

    # default demo row
    python ml_model/predict_failure.py

    # custom row via 1‑line JSON
    python ml_model/predict_failure.py \
        --input-json '{"build_time":250,"error_count":7,"cpu_usage":60,"test_pass_rate":0.70}'

    # CI mode – print only numeric probability
    python ml_model/predict_failure.py --plain \
        --input-json '{"build_time":250,"error_count":7,"cpu_usage":60,"test_pass_rate":0.70}'
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import pandas as pd

# ------------------------------------------------------------------ #
# 1) Load model (safe at import time; no CLI parsing here)
# ------------------------------------------------------------------ #
ROOT = Path(__file__).parent  # …/ml_model
MODEL_PATH = ROOT / "models" / "model.pkl"
model = joblib.load(MODEL_PATH)


# ------------------------------------------------------------------ #
# 2) Core API (import‑safe): use in tests or other modules
# ------------------------------------------------------------------ #
def predict_failure_from_dict(sample: dict, *, _model=model) -> float:
    """
    Return failure probability in [0, 1] for a single metrics row.

    Expected keys (as trained): build_time, error_count, cpu_usage, test_pass_rate
    """
    row = pd.DataFrame([sample])
    prob_failure = float(_model.predict_proba(row)[0][1])  # probability of class 1 (failure)
    return prob_failure


# Backward‑compat shim for older tests/imports
def predict_failure(sample: dict) -> float:
    """
    Backward‑compatible wrapper around predict_failure_from_dict().
    Keeps existing tests/imports working.
    """
    return predict_failure_from_dict(sample)


# ------------------------------------------------------------------ #
# 3) CLI plumbing (runs only when executed as a script)
# ------------------------------------------------------------------ #
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Predict CI failure probability from build/test metrics."
    )
    p.add_argument(
        "--input-json",
        help="Single JSON object with build metrics; defaults to demo row if omitted.",
    )
    p.add_argument(
        "--plain",
        action="store_true",
        help="Print only raw failure probability (0‑1) for CI/CD pipelines.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

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

    prob_failure = predict_failure_from_dict(sample_dict)
    pred_label = int(prob_failure >= 0.5)  # threshold 0.5; adjust if needed

    if args.plain:
        # CI mode – emit only numeric value with 4‑dec precision
        print(f"{prob_failure:.4f}")
    else:
        status = "Failure" if pred_label else "Success"
        print(f"Predicted Status       : {status}")
        print(f"Failure Probability    : {prob_failure:.2%}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

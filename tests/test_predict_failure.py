import json
from pathlib import Path

import joblib
import pandas as pd

# ------------------------------------------------------------------ #
# 1. Load model (works from any CWD)
# ------------------------------------------------------------------ #
ROOT = Path(__file__).parent
MODEL_PATH = ROOT / "models" / "model.pkl"
model = joblib.load(MODEL_PATH)


def predict_failure(metrics: dict) -> float:
    """Return probability of failure (0–1) given metrics dict."""
    row = pd.DataFrame([{
        "build_time": metrics["build_time"],
        "error_count": metrics["error_count"],
        "cpu_usage": metrics["cpu_usage"],
        "test_pass_rate": metrics["test_pass_rate"],
    }])
    prob_failure = model.predict_proba(row)[0][1]
    return float(prob_failure)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-json",
        help="Single JSON object with build metrics; defaults to demo row if omitted.",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Print only raw failure probability (0-1) for CI/CD pipelines.",
    )
    args = parser.parse_args()

    if args.input_json:
        metrics = json.loads(args.input_json)
    else:
        metrics = {
            "build_time": 250,
            "error_count": 7,
            "cpu_usage": 60.0,
            "test_pass_rate": 0.70,
        }

    prob = predict_failure(metrics)
    if args.plain:
        print(f"{prob:.4f}")
    else:
        status = "Failure" if prob >= 0.5 else "Success"
        print(f"Predicted Status       : {status}")
        print(f"Failure Probability    : {prob:.2%}")


if __name__ == "__main__":
    main()

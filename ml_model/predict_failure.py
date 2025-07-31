#!/usr/bin/env python3
"""
Usage examples:

  # default demo row (heuristic if no model available)
  python ml_model/predict_failure.py

  # custom input
  python ml_model/predict_failure.py \
      --input-json '{"restart_count_last_5m":1,"cpu_usage_pct":20,"memory_usage_bytes":200000000,"ready_replica_ratio":1.0,"unavailable_replicas":0,"network_receive_bytes_per_s":0,"http_5xx_error_rate":0.0}'

  # CI mode – only probability
  python ml_model/predict_failure.py --plain \
      --input-json '{"restart_count_last_5m":1,"cpu_usage_pct":20,"memory_usage_bytes":200000000,"ready_replica_ratio":1.0,"unavailable_replicas":0,"network_receive_bytes_per_s":0,"http_5xx_error_rate":0.0}'
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Tuple

import joblib

# --- constants ------------------------------------------------------ #
DEFAULT_FEATURES = [
    "restart_count_last_5m",        # crash/restart risk
    "cpu_usage_pct",                # CPU saturation
    "memory_usage_bytes",           # memory pressure
    "ready_replica_ratio",          # readiness vs desired
    "unavailable_replicas",         # rollout health
    "network_receive_bytes_per_s",  # I/O pressure
    "http_5xx_error_rate",          # application error surface
]
MODEL_PATH = Path(__file__).parent / "models" / "model.pkl"
HIGH_RISK_DEFAULT_THRESHOLD = 0.6

# --- logging -------------------------------------------------------- #
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("predict_failure")

# --- model loading & fallback -------------------------------------- #
def load_model() -> Tuple[object | None, list[str]]:
    if MODEL_PATH.exists():
        try:
            blob = joblib.load(MODEL_PATH)
            model = blob.get("model") if isinstance(blob, dict) else blob
            features = (
                blob.get("metadata", {}).get("features")
                if isinstance(blob, dict)
                else None
            )
            if model is None:
                raise RuntimeError("Loaded object missing 'model'; falling back.")
            if not features:
                features = DEFAULT_FEATURES
            logger.info(f"Loaded model from {MODEL_PATH}, using features: {features}")
            return model, features
        except Exception as e:
            logger.warning(f"Failed to load trained model ({e}); using heuristic fallback.")
    else:
        logger.info(f"No model file at {MODEL_PATH}; using heuristic fallback.")
    return None, DEFAULT_FEATURES


def heuristic_failure_probability(x: dict) -> float:
    """
    Conservative heuristic combining key risk signals to approximate failure probability.
    Weights can be tuned over time based on historical performance.
    """
    # Normalize / clamp inputs
    cpu = min(max(x.get("cpu_usage_pct", 0) / 100.0, 0.0), 1.0)
    mem = min(x.get("memory_usage_bytes", 0) / (512 * 1024 * 1024), 1.0)  # baseline 512Mi
    net = min(x.get("network_receive_bytes_per_s", 0) / 1_000_000, 1.0)   # baseline 1MB/s
    rdy = x.get("ready_replica_ratio", 1.0)
    unavail = min(x.get("unavailable_replicas", 0), 10) / 10.0
    restarts = min(x.get("restart_count_last_5m", 0), 5) / 5.0
    http5 = min(x.get("http_5xx_error_rate", 0), 5) / 5.0

    # Weighted sum: readiness drop and restarts are strongest indicators
    score = 0.0
    score += 0.35 * (1 - rdy)          # readiness gaps
    score += 0.20 * restarts           # recent restarts
    score += 0.15 * http5              # application errors
    score += 0.10 * unavail            # unavailable replicas
    score += 0.10 * cpu                # CPU pressure
    score += 0.05 * mem                # Memory pressure
    score += 0.05 * net                # Network receive

    return max(0.0, min(score, 1.0))


def predict_from_dict(sample: dict, model_obj, feature_order: list[str]) -> float:
    # Build feature vector in expected order
    row = []
    for feat in feature_order:
        raw = sample.get(feat, 0.0)
        try:
            row.append(float(raw))
        except Exception:
            logger.warning(f"Feature {feat} has non-numeric value {raw}, coercing to 0.")
            row.append(0.0)

    if model_obj is not None:
        try:
            # Most classifiers used (e.g., GradientBoostingClassifier) have predict_proba
            prob = float(model_obj.predict_proba([row])[0][1])
            return max(0.0, min(prob, 1.0))
        except Exception as e:
            logger.warning(f"Model inference failed ({e}); falling back to heuristic.")
    # fallback
    return heuristic_failure_probability(sample)


# --- CLI ------------------------------------------------------------ #
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Predict deployment failure probability from runtime metrics."
    )
    p.add_argument(
        "--input-json",
        help=(
            "JSON object of features, or @<file> to load a file. "
            f"Defaults to a safe demo row if omitted."
        ),
    )
    p.add_argument(
        "--plain",
        action="store_true",
        help="Print only raw probability (for CI output).",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=HIGH_RISK_DEFAULT_THRESHOLD,
        help=f"Threshold above which risk is considered high (default {HIGH_RISK_DEFAULT_THRESHOLD}).",
    )
    return p


def load_input(raw: str | None) -> dict:
    if not raw:
        # demo synthetic row - neutral healthy baseline
        return {
            "restart_count_last_5m": 0,
            "cpu_usage_pct": 5.0,
            "memory_usage_bytes": 50 * 1024 * 1024,  # 50Mi
            "ready_replica_ratio": 1.0,
            "unavailable_replicas": 0,
            "network_receive_bytes_per_s": 0,
            "http_5xx_error_rate": 0.0,
        }

    if raw.startswith("@"):
        path = raw[1:]
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read JSON from file {path}: {e}")
            sys.exit(2)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON provided: {e}")
        sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    sample = load_input(args.input_json)
    model_obj, feature_order = load_model()
    prob = predict_from_dict(sample, model_obj, feature_order)
    highrisk = prob > args.threshold

    if args.plain:
        # only the probability (for GH Actions output consumption)
        print(f"{prob:.4f}")
    else:
        status = "HIGH RISK" if highrisk else "OK"
        print(f"Predicted Risk           : {status}")
        print(f"Failure Probability      : {prob:.2%}")
        print(f"Threshold (high risk)    : {args.threshold:.2f}")
        print(f"Used model inference     : {'yes' if model_obj is not None else 'no (heuristic)'}")
        print(f"Input features           : {json.dumps(sample, sort_keys=True)}")

    # Also set GitHub Actions output if applicable
    if "GITHUB_OUTPUT" in os.environ:
        try:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"fail_prob={prob}\n")
                f.write(f"highrisk={'true' if highrisk else 'false'}\n")
        except Exception as e:
            logger.warning(f"Could not write to GITHUB_OUTPUT: {e}")

    # Important: exit 0 so the workflow can branch (auto-heal/rollout) based on outputs.
    return 0


if __name__ == "__main__":
    sys.exit(main())

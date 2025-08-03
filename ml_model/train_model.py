from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler, StandardScaler, FunctionTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV


# ----------------------------- Config -------------------------------- #

CANONICAL_FEATURES = [
    "restart_count_last_5m",
    "cpu_usage_pct",
    "memory_usage_bytes",
    "ready_replica_ratio",
    "unavailable_replicas",
    "network_receive_bytes_per_s",
    "http_5xx_error_rate",
]

# Aliases you might have in CSV; normalized below
ALIASES = {
    "cpu_usage_%": "cpu_usage_pct",
    "cpu_usage": "cpu_usage_pct",
    "network_receive_bytes/s": "network_receive_bytes_per_s",
    "net_rx_bytes_per_s": "network_receive_bytes_per_s",
    "http5xx_rate": "http_5xx_error_rate",
    "http_5xx_rate": "http_5xx_error_rate",
    "unavailable_replicas_count": "unavailable_replicas",
    "ready_ratio": "ready_replica_ratio",
    "restarts_5m": "restart_count_last_5m",
}

DEFAULT_TARGETS = ["is_failure", "failure", "label", "y"]  # first that exists is used

HEAVY_TAIL = ["restart_count_last_5m", "memory_usage_bytes", "network_receive_bytes_per_s"]
REST = ["cpu_usage_pct", "ready_replica_ratio", "unavailable_replicas", "http_5xx_error_rate"]


# ------------------------- Utility functions ------------------------- #

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # strip spaces and unify case
    df.columns = df.columns.str.strip()
    # apply aliases
    rename_map = {c: ALIASES.get(c, c) for c in df.columns}
    df = df.rename(columns=rename_map)
    # if cpu is 0..1, convert to percent
    if "cpu_usage_pct" in df.columns:
        cpu = pd.to_numeric(df["cpu_usage_pct"], errors="coerce")
        if cpu.max(skipna=True) is not None and cpu.max(skipna=True) <= 1.0:
            df["cpu_usage_pct"] = cpu * 100.0
    return df


def _pick_target(df: pd.DataFrame, explicit: Optional[str]) -> str:
    if explicit and explicit in df.columns:
        return explicit
    for c in DEFAULT_TARGETS:
        if c in df.columns:
            return c
    raise ValueError(
        f"Target column not found. Provide one of {DEFAULT_TARGETS} via --target "
        f"or include it in the CSV."
    )


def _prepare_xy(df: pd.DataFrame, target_col: str) -> Tuple[pd.DataFrame, pd.Series]:
    missing = [f for f in CANONICAL_FEATURES if f not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required features: {missing}")

    X = df[CANONICAL_FEATURES].copy()
    y = df[target_col].copy()

    # Coerce y to {0,1}
    if y.dtype == "O":
        y = (
            y.astype(str)
             .str.strip()
             .str.lower()
             .map({"1": 1, "true": 1, "yes": 1, "fail": 1,
                   "0": 0, "false": 0, "no": 0, "pass": 0})
        )
    y = y.fillna(0).astype(int).clip(0, 1)

    # Gentle sanitization / clipping
    for col in CANONICAL_FEATURES:
        X[col] = pd.to_numeric(X[col], errors="coerce")

    X["restart_count_last_5m"] = X["restart_count_last_5m"].clip(lower=0)
    X["cpu_usage_pct"] = X["cpu_usage_pct"].clip(lower=0, upper=100)
    X["ready_replica_ratio"] = X["ready_replica_ratio"].clip(lower=0, upper=1)

    for col in ("memory_usage_bytes", "network_receive_bytes_per_s",
                "http_5xx_error_rate", "unavailable_replicas"):
        X[col] = X[col].clip(lower=0)

    return X, y


def _preprocessor_for_linear() -> ColumnTransformer:
    """
    Heavy-tailed features -> log1p + RobustScaler
    Rest -> StandardScaler
    """
    return ColumnTransformer(
        transformers=[
            ("heavy", Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("log1p", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
                ("scaler", RobustScaler()),
            ]), HEAVY_TAIL),
            ("rest", Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]), REST),
        ],
        remainder="drop",
    )


def _preprocessor_for_trees() -> ColumnTransformer:
    """
    Trees don’t need scaling, but log1p helps stabilize large ranges.
    """
    return ColumnTransformer(
        transformers=[
            ("heavy", Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("log1p", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
            ]), HEAVY_TAIL),
            ("rest", SimpleImputer(strategy="median"), REST),
        ],
        remainder="drop",
    )


def _build_base_pipelines() -> Dict[str, Pipeline]:
    lr = LogisticRegression(
        solver="lbfgs",  # stable for binary
        penalty="l2",
        C=0.2,           # regularize to avoid coef blow-up
        max_iter=2000,
        class_weight="balanced",
        random_state=42,
    )
    gb = GradientBoostingClassifier(random_state=42)

    lr_pipe = Pipeline([("prep", _preprocessor_for_linear()), ("clf", lr)])
    gb_pipe = Pipeline([("prep", _preprocessor_for_trees()), ("clf", gb)])
    return {"logreg": lr_pipe, "gboost": gb_pipe}


def _wrap_with_calibration(pipe: Pipeline, method: str) -> Pipeline | CalibratedClassifierCV:
    if method == "none":
        return pipe
    # ✅ scikit-learn 1.7.0 uses `estimator=` (not `base_estimator=`)
    return CalibratedClassifierCV(estimator=pipe, cv=5, method=method)


def _cv_scores(model, X: pd.DataFrame, y: pd.Series, n_splits=5) -> Dict[str, float]:
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    aucs, f1s = [], []
    for tr_idx, va_idx in skf.split(X, y):
        Xtr, Xva = X.iloc[tr_idx], X.iloc[va_idx]
        ytr, yva = y.iloc[tr_idx], y.iloc[va_idx]
        model.fit(Xtr, ytr)
        prob = model.predict_proba(Xva)[:, 1]
        pred = (prob >= 0.5).astype(int)
        aucs.append(roc_auc_score(yva, prob))
        f1s.append(f1_score(yva, pred))
    return {"roc_auc_mean": float(np.mean(aucs)), "f1_mean": float(np.mean(f1s))}


# ------------------------------ CLI ---------------------------------- #

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Train failure-risk model on Prometheus features and export model.pkl"
    )
    p.add_argument("--csv", default="prom_features.csv",
                   help="Path to input CSV containing the 7 features + target column.")
    p.add_argument("--target", default=None,
                   help=f"Target column (default: first of {DEFAULT_TARGETS} found).")
    p.add_argument("--model", choices=["auto", "logreg", "gboost"],
                   default="auto", help="Choose model or let CV pick best.")
    p.add_argument("--calibration", choices=["isotonic", "sigmoid", "none"],
                   default="isotonic", help="Probability calibration method.")
    p.add_argument("--test-size", type=float, default=0.2,
                   help="Holdout size for final report (stratified).")
    p.add_argument("--out-model", default="ml_model/models/model.pkl",
                   help="Where to save the trained model.")
    p.add_argument("--out-metrics", default="ml_model/models/metrics.json",
                   help="Where to save training metrics JSON.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_model = Path(args.out_model)
    out_metrics = Path(args.out_metrics)
    out_model.parent.mkdir(parents=True, exist_ok=True)
    out_metrics.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.csv)
    df = _normalize_columns(df)

    target_col = _pick_target(df, args.target)
    X, y = _prepare_xy(df, target_col)

    # Split a holdout for final, honest report
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=args.test_size, stratify=y, random_state=42
    )

    base_pipes = _build_base_pipelines()

    if args.model in ("logreg", "gboost"):
        candidates = [args.model]
    else:
        candidates = ["logreg", "gboost"]

    results: Dict[str, Dict[str, float]] = {}
    best_name, best_model, best_cv = None, None, -1.0

    for name in candidates:
        model = _wrap_with_calibration(base_pipes[name], args.calibration)
        scores = _cv_scores(model, Xtr, ytr, n_splits=5)
        results[name] = scores
        if scores["roc_auc_mean"] > best_cv:
            best_name, best_model, best_cv = name, model, scores["roc_auc_mean"]

    # Fit best on all training and evaluate on holdout
    assert best_model is not None
    best_model.fit(Xtr, ytr)
    prob = best_model.predict_proba(Xte)[:, 1]
    pred = (prob >= 0.5).astype(int)

    report = {
        "chosen_model": best_name,
        "calibration": args.calibration,
        "cv": results.get(best_name, {}),
        "holdout": {
            "roc_auc": float(roc_auc_score(yte, prob)),
            "f1": float(f1_score(yte, pred)),
            "precision": float(precision_score(yte, pred, zero_division=0)),
            "recall": float(recall_score(yte, pred, zero_division=0)),
            "accuracy": float(accuracy_score(yte, pred)),
            "n_train": int(Xtr.shape[0]),
            "n_test": int(Xte.shape[0]),
            "positive_rate_train": float(ytr.mean()),
            "positive_rate_test": float(yte.mean()),
        },
        "features": CANONICAL_FEATURES,
        "target": target_col,
    }

    joblib.dump(best_model, out_model)
    out_metrics.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"Saved model to {out_model}")
    print(f"Saved metrics to {out_metrics}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

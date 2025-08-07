import os, json, logging, random, time, math, pickle
from functools import wraps
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

from flask import Flask, request, jsonify
from flask_cors import CORS
from prometheus_client import Counter, Gauge, Summary, generate_latest, CONTENT_TYPE_LATEST
from werkzeug.middleware.proxy_fix import ProxyFix

try:
    import joblib               # preferred for model load
except ImportError:
    joblib = None

# ─────────────────────────── Config ────────────────────────────
class Config:
    LOG_LEVEL            = os.getenv("LOG_LEVEL", "INFO").upper()
    RATE_LIMIT           = int(os.getenv("RATE_LIMIT", "200"))
    FAILURE_PROB         = float(os.getenv("FAILURE_INJECTION_PROB", "0.0"))
    CORS_ALLOW_ORIGINS   = os.getenv("CORS_ALLOW_ORIGINS", "*")
    MODEL_PATH           = os.getenv("MODEL_PATH", "ml_model/models/model.pkl")
    RISK_HIGH_THRESHOLD  = float(os.getenv("RISK_HIGH_THRESHOLD", "0.7"))

REQUIRED_FEATURES: List[str] = [
    "restart_count_last_5m", "cpu_usage_pct", "memory_usage_bytes",
    "ready_replica_ratio",   "unavailable_replicas",
    "network_receive_bytes_per_s", "http_5xx_error_rate"
]

# ────────────────────────── Logging ────────────────────────────
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app")

# ─────────────────────────── Flask ─────────────────────────────
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": Config.CORS_ALLOW_ORIGINS}})
app.wsgi_app = ProxyFix(app.wsgi_app)        # behind proxy/LB

# ────────────────────────── Metrics ────────────────────────────
HTTP_REQS       = Counter("http_request_total", "HTTP requests", ["method", "status"])
FAILURE_PROB    = Gauge("predicted_failure_probability", "Predicted failure probability")
PREDICT_DURATION= Summary("predict_duration_seconds", "Time taken for prediction")
REQ_LATENCY     = Summary("api_request_latency_seconds", "Request latency", ["path"])

# ─────────────────────── Model loading ─────────────────────────
_model: Optional[Any] = None
_model_err: Optional[str] = None

def _resolve_model_path() -> Optional[str]:
    for p in (
        os.getenv("MODEL_PATH", Config.MODEL_PATH),
        "ml_model/models/model.pkl", "ml_model/models/model.joblib",
        "ml_model/model.pkl",        "ml_model/model.joblib",
    ):
        if p and Path(p).exists():
            return p
    return None

def _load_model_if_needed() -> None:
    global _model, _model_err
    if _model is not None or _model_err is not None:
        return
    path = _resolve_model_path()
    if not path:
        _model_err = "Model not found – heuristic fallback in use"
        logger.warning(_model_err); return

    try:
        if joblib:
            try:           # most robust for sklearn objects
                _model = joblib.load(path)
            except Exception as je:
                logger.warning("joblib.load failed (%s); trying pickle", je)
                _model = pickle.load(open(path, "rb"))
        else:
            _model = pickle.load(open(path, "rb"))
        logger.info("Loaded model from %s", path)
    except Exception as e:
        _model_err = f"Failed to load model: {e}"
        logger.exception(_model_err)

# ───────────────────────── Utilities ───────────────────────────
def _json_error(msg: str, code: int = 400):
    HTTP_REQS.labels(method=request.method, status=str(code)).inc()
    return jsonify({"ok": False, "error": msg}), code

def _coerce_float(x) -> float:
    if x in (None, ""): return 0.0
    try:   return float(x)
    except Exception: raise ValueError(f"Cannot convert '{x}' to float")

def _validate(payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, float]], Optional[str]]:
    missing = [k for k in REQUIRED_FEATURES if k not in payload]
    if missing: return None, f"Missing features: {', '.join(missing)}"
    try:
        f = {
            "restart_count_last_5m"      : max(0.0, _coerce_float(payload["restart_count_last_5m"])),
            "cpu_usage_pct"              : min(max(_coerce_float(payload["cpu_usage_pct"]), 0.0), 100.0),
            "memory_usage_bytes"         : max(0.0, _coerce_float(payload["memory_usage_bytes"])),
            "ready_replica_ratio"        : min(max(_coerce_float(payload["ready_replica_ratio"]), 0.0), 1.0),
            "unavailable_replicas"       : max(0.0, _coerce_float(payload["unavailable_replicas"])),
            "network_receive_bytes_per_s": max(0.0, _coerce_float(payload["network_receive_bytes_per_s"])),
            "http_5xx_error_rate"        : max(0.0, _coerce_float(payload["http_5xx_error_rate"])),
        }
    except ValueError as ve:
        return None, str(ve)
    return f, None

def _predict_probability(f: Dict[str, float]) -> float:
    _load_model_if_needed()
    if _model is not None:
        try:
            X = [[f[k] for k in REQUIRED_FEATURES]]
            prob = float(getattr(_model, "predict_proba")(X)[0][1])
            return max(0.0, min(prob, 1.0))
        except Exception as e:
            logger.warning("Model inference failed, fallback used: %s", e)

    # heuristic (logistic-style)
    r, cpu, mem = f["restart_count_last_5m"], f["cpu_usage_pct"]/100, min(f["memory_usage_bytes"]/(1024**3), 1.0)
    ratio, unavail = 1.0-f["ready_replica_ratio"], f["unavailable_replicas"]
    net = min(f["network_receive_bytes_per_s"]/(1024**2), 1.0)
    e5xx = f["http_5xx_error_rate"]
    s = 0.25*r + 1.2*cpu + 0.6*mem + 1.5*ratio + 0.3*unavail + 0.4*net + 2.0*e5xx
    return max(0.0, min(1 - math.exp(-s)/(1+math.exp(-s)), 1.0))

# ───────────────────── Simple in-mem rate-limit ────────────────
REQUEST_COUNTS: Dict[str, int] = {}

def rate_limit(limit: int = Config.RATE_LIMIT):
    def deco(f):
        @wraps(f)
        def wrapped(*a, **kw):
            # Skip rate limit in CI or test env
            if os.getenv("DISABLE_RATE_LIMIT", "false").lower() == "true":
                return f(*a, **kw)

            ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
            REQUEST_COUNTS[ip] = REQUEST_COUNTS.get(ip, 0) + 1
            if REQUEST_COUNTS[ip] > limit:
                HTTP_REQS.labels(method=request.method, status="429").inc()
                return jsonify({"ok": False, "error": "rate limit exceeded"}), 429
            return f(*a, **kw)
        return wrapped
    return deco


# ────────────────────────── Routes ─────────────────────────────
@app.get("/")
def root():
    HTTP_REQS.labels(method="GET", status="200").inc()
    return (
        "<h3>AI-DevOps Risk API</h3><ul>"
        "<li><code>/healthz</code></li>"
        "<li><code>/predict</code> (POST)</li>"
        "<li><code>/predict/sample</code></li>"
        "<li><code>/metrics</code></li></ul>", 200,
        {"Content-Type": "text/html"},
    )

@app.get("/healthz")
def healthz():
    _load_model_if_needed()
    HTTP_REQS.labels(method="GET", status="200").inc()
    try:
        import sklearn; skl_ver = sklearn.__version__
    except Exception: skl_ver = None
    path = _resolve_model_path() or Config.MODEL_PATH
    return jsonify({
        "ok": True,
        "status": "ok" if (_model or _model_err) else "init",
        "model_loaded": _model is not None,
        "model_error": _model_err,
        "model_path": path,
        "model_path_exists": Path(path).exists(),
        "sklearn_version": skl_ver,
    }), 200

@app.get("/predict/sample")
def sample():
    HTTP_REQS.labels(method="GET", status="200").inc()
    return jsonify({
        "restart_count_last_5m": 0, "cpu_usage_pct": 10,
        "memory_usage_bytes": 50*1024*1024, "ready_replica_ratio": 1.0,
        "unavailable_replicas": 0, "network_receive_bytes_per_s": 0,
        "http_5xx_error_rate": 0.0,
    }), 200

@app.post("/predict")
@rate_limit()
def predict():
    start = time.time()
    try:
        payload = request.get_json(force=True, silent=False) or {}
    except Exception:
        return _json_error("Invalid JSON", 400)

    feats, err = _validate(payload)
    if err: return _json_error(err, 400)

    if random.random() < Config.FAILURE_PROB:
        HTTP_REQS.labels(method="POST", status="500").inc()
        logger.error(json.dumps({"event": "inject_failure"}))
        return jsonify({"ok": False, "error": "internal (injected)"}), 500

    prob = _predict_probability(feats)
    FAILURE_PROB.set(prob)
    resp = {
        "ok": True,
        "probability": prob,
        "risk": "HIGH" if prob >= Config.RISK_HIGH_THRESHOLD else "LOW",
        "features": feats,
        "model_loaded": _model is not None,
        "model_error": _model_err,
    }
    HTTP_REQS.labels(method="POST", status="200").inc()
    PREDICT_DURATION.observe(time.time()-start)
    REQ_LATENCY.labels(path="/predict").observe(time.time()-start)
    return jsonify(resp), 200

@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

# ───────────────────────── Entrypoint ──────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    logger.info("Starting app on port %d", port)
    app.run(host="0.0.0.0", port=port)

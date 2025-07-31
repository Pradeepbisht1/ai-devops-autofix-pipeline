import os
import json
import logging
import random
from flask import Flask, request, jsonify
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST, Gauge, Summary
from werkzeug.middleware.proxy_fix import ProxyFix
from functools import wraps
import time

# Logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format='%(message)s')
logger = logging.getLogger("app")

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

# Prometheus metrics
HTTP_REQS = Counter("http_request_total", "HTTP requests", ["method", "status"])
FAILURE_PROB = Gauge("predicted_failure_probability", "Predicted failure probability")
PREDICT_DURATION = Summary("predict_duration_seconds", "Time taken for prediction")

# Simple rate limiter placeholder (production: use redis-backed or middleware)
REQUEST_COUNTS = {}

def rate_limit(limit=100):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr or "unknown"
            REQUEST_COUNTS.setdefault(ip, 0)
            REQUEST_COUNTS[ip] += 1
            if REQUEST_COUNTS[ip] > limit:
                HTTP_REQS.labels(method=request.method, status="429").inc()
                return jsonify({"error": "rate limit exceeded"}), 429
            return f(*args, **kwargs)
        return wrapped
    return decorator

@app.get("/healthz")
def healthz():
    HTTP_REQS.labels(method="GET", status="200").inc()
    return jsonify({"status": "ok"}), 200

@app.post("/predict")
@rate_limit(limit=int(os.getenv("RATE_LIMIT", "100")))
def predict():
    start = time.time()
    try:
        # simulate work or real inference
        # load model once globally if heavy
        s = sum(i * i for i in range(30000))  # placeholder
        result = {"y": s % 7}

        # Simulate occasional 5xx (for testing, remove in real prod)
        if random.random() < float(os.getenv("FAILURE_INJECTION_PROB", "0.0")):
            HTTP_REQS.labels(method="POST", status="500").inc()
            logger.error(json.dumps({"event": "inject_failure", "reason": "test"}))
            return jsonify({"error": "internal"}), 500

        HTTP_REQS.labels(method="POST", status="200").inc()
        return jsonify(result), 200
    except Exception as e:
        HTTP_REQS.labels(method="POST", status="500").inc()
        logger.exception("Predict failure")
        return jsonify({"error": "internal"}), 500
    finally:
        duration = time.time() - start
        PREDICT_DURATION.observe(duration)

@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

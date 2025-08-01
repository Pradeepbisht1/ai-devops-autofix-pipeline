import os
import json
import logging
import random
import time
from functools import wraps

from flask import Flask, request, jsonify
from prometheus_client import (
    Counter,
    Gauge,
    Summary,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from werkzeug.middleware.proxy_fix import ProxyFix

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app")

# -------------------------------------------------------------------
# Flask & Middleware
# -------------------------------------------------------------------
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

# -------------------------------------------------------------------
# Prometheus metrics
# -------------------------------------------------------------------
HTTP_REQS = Counter("http_request_total", "HTTP requests", ["method", "status"])
FAILURE_PROB = Gauge(
    "predicted_failure_probability", "Predicted failure probability"
)  # currently unused but reserved
PREDICT_DURATION = Summary(
    "predict_duration_seconds", "Time taken for prediction"
)

# -------------------------------------------------------------------
# Simple in-memory rate limiter (for dev). For prod use Redis or API-gateway.
# -------------------------------------------------------------------
REQUEST_COUNTS: dict[str, int] = {}

def rate_limit(limit: int = 100):
    """Decorator that limits number of calls per IP (naïve, resets on restart)."""

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

# -------------------------------------------------------------------
# Index & Health endpoints
# -------------------------------------------------------------------
@app.get("/")
def index():
    """Simple landing page so browsers don't 404 at root."""
    HTTP_REQS.labels(method="GET", status="200").inc()
    return (
        """
        <h3>AI-DevOps Demo API</h3>
        <ul>
          <li><code>/healthz</code></li>
          <li><code>/predict</code> <em>(POST)</em></li>
          <li><code>/metrics</code></li>
        </ul>
        """,
        200,
        {"Content-Type": "text/html"},
    )


@app.get("/healthz")
def healthz():
    HTTP_REQS.labels(method="GET", status="200").inc()
    return jsonify({"status": "ok"}), 200

# -------------------------------------------------------------------
# Predict endpoint (dummy implementation for now)
# -------------------------------------------------------------------
@app.post("/predict")
@rate_limit(limit=int(os.getenv("RATE_LIMIT", "100")))
def predict():
    start = time.time()
    try:
        # Simulate some CPU-work (replace with real model inference)
        s = sum(i * i for i in range(30_000))
        result = {"y": s % 7}

        # Failure-injection for chaos testing
        if random.random() < float(os.getenv("FAILURE_INJECTION_PROB", "0.0")):
            HTTP_REQS.labels(method="POST", status="500").inc()
            logger.error(json.dumps({"event": "inject_failure", "reason": "test"}))
            return jsonify({"error": "internal"}), 500

        HTTP_REQS.labels(method="POST", status="200").inc()
        return jsonify(result), 200
    except Exception as e:  # noqa: BLE001
        HTTP_REQS.labels(method="POST", status="500").inc()
        logger.exception("Predict failure: %s", e)
        return jsonify({"error": "internal"}), 500
    finally:
        PREDICT_DURATION.observe(time.time() - start)

# -------------------------------------------------------------------
# Prometheus scrape endpoint
# -------------------------------------------------------------------
@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

# -------------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    logger.info("Starting app on port %d", port)
    app.run(host="0.0.0.0", port=port)

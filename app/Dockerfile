# syntax=docker/dockerfile:1.6
ARG PY_BASE=mirror.gcr.io/library/python:3.10-slim
FROM ${PY_BASE} AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=5000 \
    GUNICORN_WORKERS=2 \
    GUNICORN_THREADS=4 \
    GUNICORN_TIMEOUT=120 \
    GUNICORN_KEEPALIVE=5 \
    LOG_LEVEL=INFO \
    PYTHONPATH=/app

WORKDIR /app

#  keep image small: no apt-get

COPY app/src/requirements.txt ./requirements-app.txt
COPY ml_model/requirements.txt ./requirements-model.txt

# Pin pip < 25 to avoid rare hash/CA issues seen on your host
RUN python -m venv /venv \
 && /venv/bin/python -m pip install --no-cache-dir --upgrade "pip<25" setuptools wheel \
 && /venv/bin/pip install -r requirements-app.txt \
 && /venv/bin/pip install -r requirements-model.txt \
 && /venv/bin/pip install gunicorn

COPY app/src/ ./
COPY ml_model/models/model.pkl ./ml_model/models/model.pkl

RUN adduser --disabled-password --gecos "" --uid 10001 appuser
USER appuser

ENV PATH="/venv/bin:${PATH}"
EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["python","-c","import os,urllib.request;port=os.environ.get('PORT','5000');urllib.request.urlopen('http://127.0.0.1:'+port+'/healthz',timeout=3).read();print('ok')"]

CMD ["sh","-c","gunicorn -k gthread -w ${GUNICORN_WORKERS} --threads ${GUNICORN_THREADS} -b 0.0.0.0:${PORT} app:app --timeout ${GUNICORN_TIMEOUT} --graceful-timeout 30 --keep-alive ${GUNICORN_KEEPALIVE} --log-level ${LOG_LEVEL}"]

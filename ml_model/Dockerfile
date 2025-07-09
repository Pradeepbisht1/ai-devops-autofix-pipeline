FROM python:3.10-slim

WORKDIR /app

COPY model.pkl /app/
COPY inference_server.py /app/
COPY requirements.txt /app/

RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "inference_server:app"]

FROM python:3.10-slim

WORKDIR /app

COPY model.pkl /app/
COPY inference_server.py /app/
COPY requirements.txt /app/

# wrapper script copy karo
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

RUN pip install -r requirements.txt

EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD []

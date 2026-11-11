# Contexto de build: carpeta functions/ (ver functions/docker-compose.yml)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# 1) Empaquetar la Lambda: handler.py + su dependencia (pg8000, Python puro) en un .zip
COPY send-notification/handler.py /function-build/
RUN pip install --no-cache-dir --target /function-build pg8000 \
    && cd /function-build && python -m zipfile -c /function.zip *

# 2) Migraciones de notification_db
COPY send-notification/alembic.ini /migrations/alembic.ini
COPY send-notification/migrations /migrations/migrations

# 3) El conector
WORKDIR /app
COPY notification-connector/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY notification-connector/ /app/

CMD ["sh", "/app/entrypoint.sh"]

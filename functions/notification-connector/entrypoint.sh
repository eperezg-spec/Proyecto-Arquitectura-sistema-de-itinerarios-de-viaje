#!/bin/sh
# Arranque del conector:
#   1) migraciones de notification_db (Alembic)
#   2) despliegue de la Lambda en LocalStack
#   3) escuchar la cola de RabbitMQ
set -e

echo "1/3 Aplicando migraciones de notification_db..."
cd /migrations && alembic upgrade head

echo "2/3 Desplegando SendNotificationFunction en LocalStack..."
python /app/deploy_lambda.py

echo "3/3 Iniciando conector RabbitMQ -> Lambda..."
exec python /app/connector.py

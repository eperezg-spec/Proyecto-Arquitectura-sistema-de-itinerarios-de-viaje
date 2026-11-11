"""
CONECTOR RabbitMQ -> AWS Lambda.

En AWS real, una Lambda se "suscribe" a una cola con un Event Source Mapping.
LocalStack (versión gratuita) no lo ofrece para RabbitMQ, así que este pequeño
proceso hace ese papel: escucha la cola e invoca la Lambda por cada mensaje.
NO tiene lógica de negocio (igual que el connector-sdk de OpenFaaS).

  RabbitMQ (cola notifications.itinerary-created)
       │  mensaje ItineraryCreatedEvent
       ▼
  connector.py  ──lambda.invoke()──>  SendNotificationFunction (LocalStack)
       │
       ├─ OK    -> ack  (se borra de la cola)
       └─ error -> nack (va a la Dead Letter Queue: notifications.dead-letter)
"""
import json
import logging
import os
import sys
import time

import boto3
import pika
from botocore.config import Config

from messaging import QUEUE, declare_topology

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2F")
LOCALSTACK_URL = os.getenv("LOCALSTACK_URL", "http://localhost:4566")
FUNCTION_NAME = os.getenv("FUNCTION_NAME", "SendNotificationFunction")

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
logger = logging.getLogger("notification-connector")
logging.getLogger("pika").setLevel(logging.WARNING)  # pika es muy verboso en INFO


def log(level: int, message: str, **fields) -> None:
    logger.log(level, json.dumps({"level": logging.getLevelName(level), "service": "notification-connector", "message": message, **fields}))


# Región y credenciales se leen de AWS_DEFAULT_REGION / AWS_ACCESS_KEY_ID /
# AWS_SECRET_ACCESS_KEY (en docker-compose valen "test": LocalStack no las valida).
lambda_client = boto3.client(
    "lambda",
    endpoint_url=LOCALSTACK_URL,
    # La primera invocación puede tardar (LocalStack descarga la imagen del runtime)
    config=Config(read_timeout=300, retries={"max_attempts": 0}),
)


def on_message(channel, method, properties, body: bytes) -> None:
    headers = properties.headers or {}
    log(logging.INFO, "Evento recibido", event_id=properties.message_id, traceparent=headers.get("traceparent"))
    try:
        response = lambda_client.invoke(FunctionName=FUNCTION_NAME, InvocationType="RequestResponse", Payload=body)
        result = json.loads(response["Payload"].read() or b"{}")
        if "FunctionError" in response:
            raise RuntimeError(f"La Lambda devolvió un error: {result}")
    except Exception as exc:
        log(logging.ERROR, "Fallo al invocar la Lambda, el mensaje va a la DLQ", event_id=properties.message_id, error=str(exc))
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    log(logging.INFO, "Lambda ejecutada", event_id=properties.message_id, result=result)
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            declare_topology(channel)
            channel.basic_qos(prefetch_count=1)  # un mensaje a la vez
            channel.basic_consume(queue=QUEUE, on_message_callback=on_message)
            log(logging.INFO, "Escuchando la cola", queue=QUEUE)
            channel.start_consuming()
        except pika.exceptions.AMQPError as exc:
            log(logging.WARNING, "RabbitMQ no disponible, reintentando en 5s", error=str(exc))
            time.sleep(5)


if __name__ == "__main__":
    main()

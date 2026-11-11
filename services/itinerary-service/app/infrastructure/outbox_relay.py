"""
OUTBOX RELAY: proceso aparte que publica en RabbitMQ los eventos guardados en
la tabla outbox_messages. Se ejecuta con:

    python -m app.infrastructure.outbox_relay

Ciclo:
  1. SELECT de mensajes con published_at IS NULL  (FOR UPDATE SKIP LOCKED permite
     correr varias réplicas sin que dos publiquen el mismo mensaje).
  2. Publicar en RabbitMQ con "publisher confirms" (el broker confirma la recepción).
  3. Marcar published_at = ahora. COMMIT.

Garantía: "at-least-once" (al menos una vez). Si el relay se cae entre el paso 2
y el 3, el mensaje se volverá a publicar; por eso el consumidor es idempotente
(usa event_id para ignorar duplicados).
"""
import json
import logging
import os
import time
from datetime import datetime, timezone

import pika
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.messaging import EXCHANGE, declare_topology
from app.infrastructure.orm import OutboxMessageRow

logger = logging.getLogger("outbox-relay")

BATCH_SIZE = 50
POLL_INTERVAL_SECONDS = float(os.getenv("OUTBOX_POLL_INTERVAL_SECONDS", "1"))
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2F")


def publish_pending(session_factory: sessionmaker[Session], channel) -> int:
    """Publica un lote de mensajes pendientes. Devuelve cuántos publicó."""
    with session_factory() as session, session.begin():
        query = (
            select(OutboxMessageRow)
            .where(OutboxMessageRow.published_at.is_(None))
            .order_by(OutboxMessageRow.occurred_at)
            .limit(BATCH_SIZE)
            .with_for_update(skip_locked=True)
        )
        messages = session.scalars(query).all()
        for message in messages:
            channel.basic_publish(
                exchange=EXCHANGE,
                routing_key=message.event_type,
                body=json.dumps(message.payload).encode(),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,  # mensaje persistente (sobrevive a reinicios del broker)
                    message_id=str(message.id),
                    type=message.event_type,
                    headers=message.headers or {},
                ),
            )
            message.published_at = datetime.now(timezone.utc)
            logger.info(
                "Evento publicado",
                extra={"extra_fields": {"event_id": str(message.id), "event_type": message.event_type}},
            )
        return len(messages)


def main() -> None:
    from app.infrastructure.database import SessionLocal
    from app.infrastructure.observability import setup_logging

    setup_logging("outbox-relay")
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            declare_topology(channel)
            channel.confirm_delivery()  # publisher confirms
            logger.info("Outbox relay conectado a RabbitMQ")
            while True:
                if publish_pending(SessionLocal, channel) == 0:
                    # connection.sleep (y no time.sleep) mantiene vivo el heartbeat
                    connection.sleep(POLL_INTERVAL_SECONDS)
        except pika.exceptions.AMQPError as exc:
            logger.warning("RabbitMQ no disponible, reintentando en 5s", extra={"extra_fields": {"error": str(exc)}})
            time.sleep(5)
        except Exception:
            logger.exception("Error en el outbox relay, reintentando en 5s")
            time.sleep(5)


if __name__ == "__main__":
    main()

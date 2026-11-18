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
from prometheus_client import start_http_server
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.messaging import EXCHANGE, declare_topology
from app.infrastructure.metrics import OUTBOX_PENDING, OUTBOX_PUBLISHED
from app.infrastructure.orm import OutboxMessageRow

logger = logging.getLogger("outbox-relay")

BATCH_SIZE = 50
POLL_INTERVAL_SECONDS = float(os.getenv("OUTBOX_POLL_INTERVAL_SECONDS", "1"))
METRICS_PORT = int(os.getenv("METRICS_PORT", "9100"))


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
            OUTBOX_PUBLISHED.labels(message.event_type).inc()
            logger.info(
                "Evento publicado",
                extra={"extra_fields": {"event_id": str(message.id), "event_type": message.event_type}},
            )
        # Cuántos quedan pendientes (lo vigila la alerta "OutboxAtascado"). El autoflush de la
        # sesión ya envió los published_at de este lote, así que no se cuentan.
        pending = session.scalar(
            select(func.count()).select_from(OutboxMessageRow).where(OutboxMessageRow.published_at.is_(None))
        )
        OUTBOX_PENDING.set(pending or 0)
        return len(messages)


def main() -> None:
    from app.infrastructure.database import SessionLocal
    from app.infrastructure.observability import setup_logging
    from app.infrastructure.vault import get_secret

    setup_logging("outbox-relay")
    rabbitmq_url = get_secret(
        "itinerario/itinerary-service", "rabbitmq_url", env_var="RABBITMQ_URL",
        default="amqp://guest:guest@localhost:5672/%2F",
    )
    start_http_server(METRICS_PORT)  # GET :9100/metrics para Prometheus
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
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

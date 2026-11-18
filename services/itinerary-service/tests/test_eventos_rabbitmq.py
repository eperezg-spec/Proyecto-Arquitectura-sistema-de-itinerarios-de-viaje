"""
PRUEBAS DE EVENTOS DE INTEGRACIÓN con un RabbitMQ REAL (Testcontainers).

Testcontainers levanta un contenedor rabbitmq:3.13 solo para estas pruebas y lo
borra al terminar. Se verifica la TOPOLOGÍA real del sistema:

    outbox relay ──> exchange itinerary.events (topic) ──itinerary.created──> cola notifications.itinerary-created
                                                                                   │ nack (requeue=False)
                                                                                   ▼
                                     exchange itinerary.events.dlx ──> cola notifications.dead-letter (DLQ)

Requiere Docker. Si no está disponible, las pruebas se omiten (skip).
    pytest -m integration
"""
import json
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.models import Itinerary
from app.infrastructure.messaging import DEAD_LETTER_QUEUE as DLQ, QUEUE, declare_topology
from app.infrastructure.orm import Base
from app.infrastructure.outbox_relay import publish_pending
from app.infrastructure.sql_repository import SqlItineraryRepository

pytestmark = pytest.mark.integration

pika = pytest.importorskip("pika")
rabbitmq_module = pytest.importorskip("testcontainers.rabbitmq")


@pytest.fixture(scope="module")
def rabbitmq():
    try:
        container = rabbitmq_module.RabbitMqContainer("rabbitmq:3.13-alpine")
        container.start()
    except Exception as exc:  # noqa: BLE001 - sin Docker no se puede correr
        pytest.skip(f"Docker no disponible: {exc}")
    yield container
    container.stop()


@pytest.fixture
def channel(rabbitmq):
    connection = pika.BlockingConnection(rabbitmq.get_connection_params())
    channel = connection.channel()
    declare_topology(channel)  # misma función que usan el relay y el conector
    channel.queue_purge(QUEUE)
    channel.queue_purge(DLQ)
    channel.confirm_delivery()  # publisher confirms, igual que en producción
    yield channel
    connection.close()


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _get(channel, queue, attempts=20):
    """Lee un mensaje de la cola (espera un poco a que llegue)."""
    for _ in range(attempts):
        method, properties, body = channel.basic_get(queue)
        if method is not None:
            return method, properties, body
        time.sleep(0.2)
    return None, None, None


def test_el_evento_llega_a_la_cola_del_consumidor(channel, session_factory, valid_data):
    itinerary = Itinerary.create(**valid_data.__dict__)
    SqlItineraryRepository(session_factory).add(itinerary)

    assert publish_pending(session_factory, channel) == 1

    method, properties, body = _get(channel, QUEUE)
    assert method is not None, "el mensaje no llegó a notifications.itinerary-created"
    event = json.loads(body)
    assert event["event_type"] == "itinerary.created"
    assert event["data"]["itinerary_id"] == str(itinerary.id)
    assert properties.message_id == event["event_id"]
    assert properties.delivery_mode == 2  # persistente
    channel.basic_ack(method.delivery_tag)


def test_un_mensaje_rechazado_termina_en_la_dead_letter_queue(channel, session_factory, valid_data):
    SqlItineraryRepository(session_factory).add(Itinerary.create(**valid_data.__dict__))
    publish_pending(session_factory, channel)

    method, _, body = _get(channel, QUEUE)
    # Lo que hace el notification-connector cuando la Lambda falla:
    channel.basic_nack(method.delivery_tag, requeue=False)

    dead_method, _, dead_body = _get(channel, DLQ)
    assert dead_method is not None, "el mensaje rechazado no llegó a la DLQ"
    assert json.loads(dead_body) == json.loads(body)  # el mismo evento, intacto, para reprocesarlo
    channel.basic_ack(dead_method.delivery_tag)


def test_varios_eventos_llegan_en_orden(channel, session_factory, valid_data):
    repo = SqlItineraryRepository(session_factory)
    ids = []
    for minutes in (30, 60, 90):
        itinerary = Itinerary.create(**{**valid_data.__dict__, "duration_minutes": minutes})
        repo.add(itinerary)
        ids.append(str(itinerary.id))
        time.sleep(0.01)  # occurred_at distinto para que el orden sea determinista

    assert publish_pending(session_factory, channel) == 3

    received = []
    for _ in ids:
        method, _, body = _get(channel, QUEUE)
        received.append(json.loads(body)["data"]["itinerary_id"])
        channel.basic_ack(method.delivery_tag)
    assert received == ids

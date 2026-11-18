"""
PRUEBAS DE EVENTOS en la arquitectura hexagonal (sin Docker).

Recorren el evento ItineraryCreated capa por capa, de adentro hacia afuera:

  DOMINIO          Itinerary.create() registra el evento de dominio ItineraryCreated
     │
  APLICACIÓN       ItineraryService entrega el agregado (con su evento) al PUERTO ItineraryRepository
     │
  INFRAESTRUCTURA  SqlItineraryRepository traduce a evento de INTEGRACIÓN (contrato AsyncAPI)
     │             y lo guarda en la tabla outbox en la MISMA transacción
     │
  RELAY            publish_pending() lo publica en RabbitMQ (at-least-once)

La versión con un RabbitMQ real está en test_eventos_rabbitmq.py.
"""
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import jsonschema
import pytest
import yaml
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.itinerary_service import ItineraryService
from app.domain.events import ItineraryCreated
from app.domain.exceptions import AirportNotFound, InvalidItinerary
from app.domain.models import Itinerary
from app.infrastructure import sql_repository
from app.infrastructure.integration_events import ITINERARY_CREATED, to_integration_event
from app.infrastructure.orm import Base, ItineraryRow, OutboxMessageRow
from app.infrastructure.outbox_relay import publish_pending
from app.infrastructure.sql_repository import SqlItineraryRepository
from tests.conftest import FakeAirportChecker, InMemoryRepository

ASYNCAPI = Path(__file__).resolve().parents[3] / "contracts" / "asyncapi.yaml"


@pytest.fixture(scope="module")
def payload_schema() -> dict:
    """Esquema JSON del evento, leído del contrato AsyncAPI (fuente única de verdad)."""
    spec = yaml.safe_load(ASYNCAPI.read_text(encoding="utf-8"))
    return spec["components"]["schemas"]["ItineraryCreatedPayload"]


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


class FakeChannel:
    """Canal de RabbitMQ falso. Con fail=True simula que el broker se cae al publicar."""

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.published = []

    def basic_publish(self, exchange, routing_key, body, properties):
        if self.fail:
            raise ConnectionError("RabbitMQ no disponible")
        self.published.append({"routing_key": routing_key, "body": json.loads(body), "properties": properties})


def _count(session_factory, model, *where):
    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(model).where(*where))


# ============================================================ 1. DOMINIO
def test_dominio_crear_registra_un_evento_con_los_datos_del_agregado(valid_data):
    itinerary = Itinerary.create(**valid_data.__dict__)

    [event] = itinerary.pull_events()

    assert isinstance(event, ItineraryCreated)
    assert event.itinerary_id == itinerary.id
    assert event.user_name == itinerary.user_name
    assert (event.departure_airport_id, event.arrival_airport_id) == (1, 2)


def test_dominio_pull_events_entrega_cada_evento_una_sola_vez(valid_data):
    itinerary = Itinerary.create(**valid_data.__dict__)
    assert len(itinerary.pull_events()) == 1
    assert itinerary.pull_events() == []  # no se duplican si se vuelve a pedir


def test_dominio_actualizar_no_emite_itinerary_created(valid_data):
    itinerary = Itinerary.create(**valid_data.__dict__)
    itinerary.pull_events()

    itinerary.update(**replace(valid_data, duration_minutes=90).__dict__)

    assert itinerary.pull_events() == []


def test_dominio_si_falla_una_regla_no_se_emite_ningun_evento(valid_data):
    with pytest.raises(InvalidItinerary):
        Itinerary.create(**replace(valid_data, arrival_airport_id=valid_data.departure_airport_id).__dict__)
    # no hay agregado, así que tampoco puede haber evento: se valida ANTES de registrar


# ========================================================= 2. APLICACIÓN
def test_aplicacion_el_caso_de_uso_entrega_el_evento_al_puerto_de_salida(valid_data):
    repo = InMemoryRepository()
    service = ItineraryService(repository=repo, airport_checker=FakeAirportChecker())

    itinerary = service.create(valid_data)

    # El caso de uso NO publica en RabbitMQ: solo usa el puerto. Quien implemente el
    # puerto decide cómo (aquí, en memoria; en producción, tabla outbox).
    assert [event.itinerary_id for event in repo.outbox] == [itinerary.id]


def test_aplicacion_si_el_aeropuerto_no_existe_no_se_emite_evento(valid_data):
    repo = InMemoryRepository()
    service = ItineraryService(repository=repo, airport_checker=FakeAirportChecker())

    with pytest.raises(AirportNotFound):
        service.create(replace(valid_data, arrival_airport_id=999))

    assert repo.outbox == []


# ==================================================== 3. INFRAESTRUCTURA
def test_integracion_el_evento_cumple_el_esquema_asyncapi(valid_data, payload_schema):
    [event] = Itinerary.create(**valid_data.__dict__).pull_events()

    payload = to_integration_event(event)

    jsonschema.validate(payload, payload_schema)  # lanza ValidationError si no cumple
    assert payload["event_type"] == ITINERARY_CREATED


def test_integracion_el_evento_es_json_puro_sin_tipos_de_dominio(valid_data):
    [event] = Itinerary.create(**valid_data.__dict__).pull_events()

    payload = to_integration_event(event)

    assert json.loads(json.dumps(payload)) == payload  # serializable sin conversiones
    assert date.fromisoformat(payload["data"]["travel_date"]) == valid_data.travel_date


def test_outbox_itinerario_y_evento_se_guardan_juntos(session_factory, valid_data):
    SqlItineraryRepository(session_factory).add(Itinerary.create(**valid_data.__dict__))

    assert _count(session_factory, ItineraryRow) == 1
    assert _count(session_factory, OutboxMessageRow, OutboxMessageRow.published_at.is_(None)) == 1


def test_outbox_si_falla_el_guardado_del_evento_tampoco_se_guarda_el_itinerario(
    session_factory, valid_data, monkeypatch
):
    """Atomicidad (Double Write Problem): o se guardan los dos, o ninguno."""

    def broken(_event):
        raise RuntimeError("fallo al serializar el evento")

    monkeypatch.setattr(sql_repository, "to_integration_event", broken)

    with pytest.raises(RuntimeError):
        SqlItineraryRepository(session_factory).add(Itinerary.create(**valid_data.__dict__))

    assert _count(session_factory, ItineraryRow) == 0  # rollback: no quedó un itinerario "huérfano"
    assert _count(session_factory, OutboxMessageRow) == 0


# =============================================================== 4. RELAY
def test_relay_publica_con_routing_key_id_y_mensaje_persistente(session_factory, valid_data):
    itinerary = Itinerary.create(**valid_data.__dict__)
    SqlItineraryRepository(session_factory).add(itinerary)
    channel = FakeChannel()

    assert publish_pending(session_factory, channel) == 1

    [message] = channel.published
    assert message["routing_key"] == ITINERARY_CREATED
    assert message["body"]["data"]["itinerary_id"] == str(itinerary.id)
    assert message["properties"].message_id == message["body"]["event_id"]  # para la idempotencia
    assert message["properties"].delivery_mode == 2  # persistente
    assert _count(session_factory, OutboxMessageRow, OutboxMessageRow.published_at.is_(None)) == 0


def test_relay_si_el_broker_falla_el_evento_sigue_pendiente(session_factory, valid_data):
    """At-least-once: si no se pudo publicar, NO se marca como publicado y se reintenta luego."""
    SqlItineraryRepository(session_factory).add(Itinerary.create(**valid_data.__dict__))

    with pytest.raises(ConnectionError):
        publish_pending(session_factory, FakeChannel(fail=True))
    assert _count(session_factory, OutboxMessageRow, OutboxMessageRow.published_at.is_(None)) == 1

    # El broker vuelve: el siguiente ciclo del relay lo publica
    assert publish_pending(session_factory, FakeChannel()) == 1
    assert _count(session_factory, OutboxMessageRow, OutboxMessageRow.published_at.is_(None)) == 0


def test_relay_no_vuelve_a_publicar_lo_ya_publicado(session_factory, valid_data):
    SqlItineraryRepository(session_factory).add(Itinerary.create(**valid_data.__dict__))
    publish_pending(session_factory, FakeChannel())

    second = FakeChannel()
    assert publish_pending(session_factory, second) == 0
    assert second.published == []

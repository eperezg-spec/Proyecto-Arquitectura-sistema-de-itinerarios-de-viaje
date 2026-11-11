"""
Pruebas del Transactional Outbox con SQLite en memoria (no requiere Docker):
  - el itinerario y el evento se guardan juntos,
  - el relay publica los pendientes y los marca como publicados.
"""
import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.models import Itinerary
from app.infrastructure.orm import Base, ItineraryRow, OutboxMessageRow
from app.infrastructure.outbox_relay import publish_pending
from app.infrastructure.sql_repository import SqlItineraryRepository


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


class FakeChannel:
    def __init__(self):
        self.published = []

    def basic_publish(self, exchange, routing_key, body, properties):
        self.published.append((routing_key, json.loads(body)))


def test_itinerario_y_evento_se_guardan_en_la_misma_transaccion(session_factory, valid_data):
    repo = SqlItineraryRepository(session_factory)
    itinerary = Itinerary.create(**valid_data.__dict__)

    repo.add(itinerary)

    with session_factory() as session:
        assert session.get(ItineraryRow, itinerary.id) is not None
        message = session.scalars(select(OutboxMessageRow)).one()
        assert message.event_type == "itinerary.created"
        assert message.payload["data"]["itinerary_id"] == str(itinerary.id)
        assert message.published_at is None  # pendiente de publicar


def test_relay_publica_y_marca_los_mensajes(session_factory, valid_data):
    SqlItineraryRepository(session_factory).add(Itinerary.create(**valid_data.__dict__))
    channel = FakeChannel()

    assert publish_pending(session_factory, channel) == 1
    assert channel.published[0][0] == "itinerary.created"
    # Segunda pasada: ya no hay pendientes
    assert publish_pending(session_factory, channel) == 0


def test_crud_del_repositorio(session_factory, valid_data):
    repo = SqlItineraryRepository(session_factory)
    itinerary = Itinerary.create(**valid_data.__dict__)
    repo.add(itinerary)

    itinerary.update(**{**valid_data.__dict__, "duration_minutes": 120})
    repo.update(itinerary)
    assert repo.get(itinerary.id).duration_minutes == 120
    assert len(repo.list(limit=10, offset=0)) == 1

    assert repo.delete(itinerary.id) is True
    assert repo.get(itinerary.id) is None

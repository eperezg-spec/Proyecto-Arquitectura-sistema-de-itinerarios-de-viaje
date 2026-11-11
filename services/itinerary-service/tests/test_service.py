"""Pruebas de los casos de uso usando fakes de los puertos (sin BD ni red)."""
from dataclasses import replace
from uuid import uuid4

import pytest

from app.application.itinerary_service import ItineraryService
from app.domain.exceptions import AirportNotFound, ItineraryNotFound
from tests.conftest import FakeAirportChecker, InMemoryRepository


@pytest.fixture
def repo():
    return InMemoryRepository()


@pytest.fixture
def service(repo):
    return ItineraryService(repo, FakeAirportChecker())


def test_crear_guarda_itinerario_y_evento(service, repo, valid_data):
    itinerary = service.create(valid_data)

    assert repo.get(itinerary.id) is not None
    assert len(repo.outbox) == 1


def test_crear_con_aeropuerto_inexistente_falla(service, repo, valid_data):
    with pytest.raises(AirportNotFound) as error:
        service.create(replace(valid_data, arrival_airport_id=999))

    assert error.value.airport_ids == [999]
    assert repo.items == {}  # no se guardó nada


def test_actualizar_y_eliminar(service, valid_data):
    itinerary = service.create(valid_data)

    updated = service.update(itinerary.id, replace(valid_data, duration_minutes=90))
    assert updated.duration_minutes == 90
    assert updated.updated_at is not None

    service.delete(itinerary.id)
    with pytest.raises(ItineraryNotFound):
        service.get(itinerary.id)


def test_eliminar_inexistente_falla(service):
    with pytest.raises(ItineraryNotFound):
        service.delete(uuid4())

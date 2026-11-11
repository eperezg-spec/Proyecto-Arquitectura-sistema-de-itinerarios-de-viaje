"""Pruebas de las reglas de negocio del agregado Itinerary (Python puro)."""
from dataclasses import replace
from datetime import date, timedelta

import pytest

from app.domain.events import ItineraryCreated
from app.domain.exceptions import InvalidItinerary
from app.domain.models import Itinerary


def test_crear_itinerario_valido_registra_evento(valid_data):
    itinerary = Itinerary.create(**valid_data.__dict__)

    events = itinerary.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], ItineraryCreated)
    assert events[0].itinerary_id == itinerary.id
    assert itinerary.pull_events() == []  # pull vacía la lista


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"user_name": "   "}, "nombre"),
        ({"arrival_airport_id": 1}, "distintos"),
        ({"duration_minutes": 0}, "duración"),
        ({"travel_date": date.today() - timedelta(days=1)}, "pasado"),
    ],
)
def test_reglas_de_negocio(valid_data, changes, message):
    with pytest.raises(InvalidItinerary, match=message):
        Itinerary.create(**replace(valid_data, **changes).__dict__)

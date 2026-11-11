"""Fakes compartidos por las pruebas (implementan los puertos en memoria)."""
from datetime import date, timedelta

import pytest

from app.application.itinerary_service import ItineraryData
from app.application.ports import AirportChecker, ItineraryRepository

KNOWN_AIRPORTS = {1, 2, 3}


class FakeAirportChecker(AirportChecker):
    def exists(self, airport_id: int) -> bool:
        return airport_id in KNOWN_AIRPORTS


class InMemoryRepository(ItineraryRepository):
    def __init__(self):
        self.items = {}
        self.outbox = []

    def add(self, itinerary):
        self.items[itinerary.id] = itinerary
        self.outbox.extend(itinerary.pull_events())

    def get(self, itinerary_id):
        return self.items.get(itinerary_id)

    def list(self, limit, offset):
        return list(self.items.values())[offset : offset + limit]

    def update(self, itinerary):
        self.items[itinerary.id] = itinerary

    def delete(self, itinerary_id):
        return self.items.pop(itinerary_id, None) is not None


@pytest.fixture
def valid_data() -> ItineraryData:
    return ItineraryData(
        user_name="Ana Gómez",
        departure_airport_id=1,
        arrival_airport_id=2,
        travel_date=date.today() + timedelta(days=10),
        duration_minutes=60,
    )

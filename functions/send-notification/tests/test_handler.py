"""Pruebas unitarias de la Lambda con una conexión falsa (sin PostgreSQL)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from handler import process_event  # noqa: E402

EVENT = {
    "event_id": "6f1c1f1e-0000-4000-8000-000000000001",
    "event_type": "itinerary.created",
    "event_version": 1,
    "occurred_at": "2026-11-11T10:00:00+00:00",
    "data": {
        "itinerary_id": "6f1c1f1e-0000-4000-8000-0000000000aa",
        "user_name": "Ana",
        "departure_airport_id": 1,
        "arrival_airport_id": 2,
        "travel_date": "2026-12-01",
        "duration_minutes": 60,
    },
}


class FakeConnection:
    """Simula la restricción UNIQUE(event_id) de la tabla."""

    def __init__(self):
        self.saved_event_ids = set()
        self.commits = 0

    def cursor(self):
        return self

    def execute(self, sql, params):
        event_id = params[0]
        self.rowcount = 0 if event_id in self.saved_event_ids else 1
        self.saved_event_ids.add(event_id)

    def commit(self):
        self.commits += 1


def test_guarda_la_notificacion():
    result = process_event(EVENT, FakeConnection())
    assert result["status"] == "sent"


def test_es_idempotente_ante_eventos_duplicados():
    connection = FakeConnection()
    process_event(EVENT, connection)
    result = process_event(EVENT, connection)
    assert result["status"] == "duplicate"

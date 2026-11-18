"""
PRUEBA DE CONTRATO (Pact) - lado CONSUMIDOR.

La Lambda SendNotificationFunction CONSUME el evento ItineraryCreated que
publica el Itinerary Service. Aquí la Lambda declara QUÉ necesita del mensaje
(campos y tipos). Pact:
  1. Genera un mensaje de ejemplo que cumple esas reglas.
  2. Se lo pasa a process_event() para comprobar que la Lambda sabe procesarlo.
  3. Escribe el contrato en contracts/pacts/send-notification-function-itinerary-service.json

Después, el Itinerary Service (PROVEEDOR) verifica ese mismo archivo en
services/itinerary-service/tests/test_pact_provider.py. Si algún día el
proveedor renombra o quita un campo que la Lambda usa, ESA prueba falla en CI
antes de llegar a producción.
"""
import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("PACT_DO_NOT_TRACK", "true")  # sin telemetría anónima de Pact

from pact import Pact, match  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from handler import process_event  # noqa: E402
from test_handler import FakeConnection  # noqa: E402

PACT_DIR = Path(__file__).resolve().parents[3] / "contracts" / "pacts"


@pytest.fixture
def pact():
    pact = Pact("send-notification-function", "itinerary-service").with_specification("V4")
    yield pact
    pact.write_file(PACT_DIR, overwrite=True)


def test_la_lambda_procesa_el_evento_itinerary_created(pact):
    (
        pact.upon_receiving("un evento ItineraryCreated", "Async")
        .given("se creó un itinerario")
        .with_body(
            {
                # match.* = "cualquier valor de este TIPO/FORMATO" (no un valor exacto)
                "event_id": match.uuid("6f1c1f1e-0000-4000-8000-000000000001"),
                "event_type": "itinerary.created",  # valor EXACTO: así se enruta el mensaje
                "event_version": match.int(1, min=1),
                "occurred_at": match.str("2026-11-11T10:00:00+00:00"),
                "data": {
                    "itinerary_id": match.uuid("6f1c1f1e-0000-4000-8000-0000000000aa"),
                    "user_name": match.str("Ana Gómez"),
                    "departure_airport_id": match.int(1),
                    "arrival_airport_id": match.int(2),
                    "travel_date": match.date("2026-12-01", "%Y-%m-%d"),
                    "duration_minutes": match.int(60, min=1),
                },
            },
            content_type="application/json",
        )
    )

    connection = FakeConnection()

    def handler(body, metadata):
        """Lo que hace la Lambda con el mensaje: debe poder procesarlo sin errores."""
        event = json.loads(body)
        result = process_event(event, connection)
        assert result["status"] == "sent"

    pact.verify(handler, "Async")
    assert connection.commits == 1

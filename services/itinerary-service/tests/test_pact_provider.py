"""
PRUEBA DE CONTRATO (Pact) - lado PROVEEDOR.

Lee el contrato que escribió la Lambda (consumidor) en
contracts/pacts/send-notification-function-itinerary-service.json y comprueba
que el evento que REALMENTE produce este servicio lo cumple.

El mensaje se construye con el mismo código de producción:
    Itinerary.create(...)  ->  pull_events()  ->  to_integration_event()
(dominio)                    (evento de dominio)   (evento de integración = JSON público)

Si alguien cambia to_integration_event() y rompe lo que la Lambda espera
(por ejemplo, renombra user_name), esta prueba falla.
"""
import json
import os
from datetime import date, timedelta
from pathlib import Path

import pytest

os.environ.setdefault("PACT_DO_NOT_TRACK", "true")  # sin telemetría anónima de Pact

from pact import Verifier  # noqa: E402

from app.domain.models import Itinerary  # noqa: E402
from app.infrastructure.integration_events import to_integration_event  # noqa: E402

PACT_FILE = (
    Path(__file__).resolve().parents[3] / "contracts" / "pacts" / "send-notification-function-itinerary-service.json"
)


def produce_itinerary_created() -> dict:
    """Produce el mensaje igual que en producción (lo que el outbox guardará y el relay publicará)."""
    itinerary = Itinerary.create(
        user_name="Ana Gómez",
        departure_airport_id=1,
        arrival_airport_id=2,
        travel_date=date.today() + timedelta(days=30),
        duration_minutes=60,
    )
    [event] = itinerary.pull_events()
    return {
        "contents": json.dumps(to_integration_event(event)).encode(),
        "metadata": None,
        "content_type": "application/json",
    }


@pytest.mark.skipif(not PACT_FILE.exists(), reason="Primero corre la prueba del consumidor (functions/send-notification)")
def test_itinerary_service_cumple_el_contrato_de_la_lambda():
    verifier = (
        Verifier("itinerary-service")
        .message_handler({"un evento ItineraryCreated": lambda *_args, **_kwargs: produce_itinerary_created()})
        .state_handler({"se creó un itinerario": lambda *_args, **_kwargs: None})
        .add_source(PACT_FILE)
    )
    verifier.verify()


@pytest.mark.skipif(not PACT_FILE.exists(), reason="Primero corre la prueba del consumidor (functions/send-notification)")
def test_un_cambio_incompatible_en_el_evento_rompe_el_contrato():
    """Simula un error típico: renombrar user_name -> username en el evento publicado."""

    def broken_producer(*_args, **_kwargs) -> dict:
        message = produce_itinerary_created()
        event = json.loads(message["contents"])
        event["data"]["username"] = event["data"].pop("user_name")
        message["contents"] = json.dumps(event).encode()
        return message

    verifier = (
        Verifier("itinerary-service")
        .message_handler({"un evento ItineraryCreated": broken_producer})
        .state_handler({"se creó un itinerario": lambda *_args, **_kwargs: None})
        .add_source(PACT_FILE)
    )
    with pytest.raises(RuntimeError):  # Pact detecta que falta "user_name"
        verifier.verify()

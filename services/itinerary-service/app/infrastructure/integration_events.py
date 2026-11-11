"""
Traduce EVENTOS DE DOMINIO a EVENTOS DE INTEGRACIÓN (el JSON público que viaja
por RabbitMQ). El contrato está documentado en contracts/asyncapi.yaml.

Un evento de integración:
  - tiene event_id (para que el consumidor sea idempotente),
  - tiene event_type y event_version (contrato versionado),
  - solo lleva datos serializables (ids, fechas en ISO 8601).
"""
from opentelemetry.propagate import inject

from app.domain.events import ItineraryCreated

ITINERARY_CREATED = "itinerary.created"


def to_integration_event(event: ItineraryCreated) -> dict:
    return {
        "event_id": str(event.event_id),
        "event_type": ITINERARY_CREATED,
        "event_version": 1,
        "occurred_at": event.occurred_at.isoformat(),
        "data": {
            "itinerary_id": str(event.itinerary_id),
            "user_name": event.user_name,
            "departure_airport_id": event.departure_airport_id,
            "arrival_airport_id": event.arrival_airport_id,
            "travel_date": event.travel_date.isoformat(),
            "duration_minutes": event.duration_minutes,
        },
    }


def current_trace_headers() -> dict:
    """Guarda el contexto de la traza actual (header W3C 'traceparent')
    para que el consumidor del evento pueda continuar la misma traza."""
    carrier: dict = {}
    inject(carrier)
    return carrier

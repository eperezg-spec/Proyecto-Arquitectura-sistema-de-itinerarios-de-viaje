"""
EVENTOS DE DOMINIO: "algo importante pasó" dentro del contexto de Planificación.

Diferencia clave:
  - Evento de DOMINIO (este archivo): objeto Python, vive en memoria, interno.
  - Evento de INTEGRACIÓN (infrastructure/integration_events.py): JSON versionado
    que viaja por RabbitMQ a OTROS servicios. Su contrato está en contracts/asyncapi.yaml.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class ItineraryCreated:
    itinerary_id: UUID
    user_name: str
    departure_airport_id: int
    arrival_airport_id: int
    travel_date: date
    duration_minutes: int
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

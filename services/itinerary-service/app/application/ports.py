"""
PUERTOS de salida del Itinerary Service (contratos que la infraestructura implementa).

  ItineraryRepository  <-- SqlItineraryRepository (PostgreSQL + tabla outbox)
  AirportChecker       <-- HttpAirportChecker (llama al Airport Service)
"""
from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.models import Itinerary


class ItineraryRepository(ABC):
    @abstractmethod
    def add(self, itinerary: Itinerary) -> None:
        """Guarda el itinerario Y sus eventos pendientes en UNA sola transacción."""

    @abstractmethod
    def get(self, itinerary_id: UUID) -> Itinerary | None: ...

    @abstractmethod
    def list(self, limit: int, offset: int) -> list[Itinerary]: ...

    @abstractmethod
    def update(self, itinerary: Itinerary) -> None: ...

    @abstractmethod
    def delete(self, itinerary_id: UUID) -> bool:
        """Devuelve False si no existía."""


class AirportChecker(ABC):
    @abstractmethod
    def exists(self, airport_id: int) -> bool:
        """True/False según exista. Lanza AirportServiceUnavailable si no se puede saber."""

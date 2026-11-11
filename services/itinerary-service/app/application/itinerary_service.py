"""
CASOS DE USO del Itinerary Service (CRUD).

Orquesta: dominio (reglas) + AirportChecker (validación remota) + repositorio.
Solo depende de PUERTOS, por eso se prueba con fakes sin base de datos ni red.
"""
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.application.ports import AirportChecker, ItineraryRepository
from app.domain.exceptions import AirportNotFound, ItineraryNotFound
from app.domain.models import Itinerary


@dataclass(frozen=True)
class ItineraryData:
    """Datos de entrada para crear/actualizar un itinerario."""

    user_name: str
    departure_airport_id: int
    arrival_airport_id: int
    travel_date: date
    duration_minutes: int


class ItineraryService:
    def __init__(self, repository: ItineraryRepository, airport_checker: AirportChecker):
        self._repository = repository
        self._airport_checker = airport_checker

    def create(self, data: ItineraryData) -> Itinerary:
        # 1. Reglas de negocio locales (baratas) -> lanza InvalidItinerary
        itinerary = Itinerary.create(**data.__dict__)
        # 2. Validación remota: ¿existen los aeropuertos? (llamada HTTP)
        self._ensure_airports_exist(itinerary)
        # 3. Persistir itinerario + evento (Transactional Outbox)
        self._repository.add(itinerary)
        return itinerary

    def get(self, itinerary_id: UUID) -> Itinerary:
        itinerary = self._repository.get(itinerary_id)
        if itinerary is None:
            raise ItineraryNotFound(f"El itinerario {itinerary_id} no existe")
        return itinerary

    def list(self, limit: int = 20, offset: int = 0) -> list[Itinerary]:
        return self._repository.list(limit, offset)

    def update(self, itinerary_id: UUID, data: ItineraryData) -> Itinerary:
        itinerary = self.get(itinerary_id)
        itinerary.update(**data.__dict__)
        self._ensure_airports_exist(itinerary)
        self._repository.update(itinerary)
        return itinerary

    def delete(self, itinerary_id: UUID) -> None:
        if not self._repository.delete(itinerary_id):
            raise ItineraryNotFound(f"El itinerario {itinerary_id} no existe")

    def _ensure_airports_exist(self, itinerary: Itinerary) -> None:
        airport_ids = [itinerary.departure_airport_id, itinerary.arrival_airport_id]
        missing = [airport_id for airport_id in airport_ids if not self._airport_checker.exists(airport_id)]
        if missing:
            raise AirportNotFound(missing)

"""
CAPA DE DOMINIO - Contexto delimitado "Planificación de Viajes".

Itinerary es la RAÍZ DE AGREGADO: toda modificación pasa por sus métodos, que
garantizan las reglas de negocio (invariantes). Python puro, sin frameworks.

Decisión DDD: el aeropuerto NO es parte de este agregado. Solo guardamos su ID
(referencia por valor). El dueño de los aeropuertos es el contexto "Catálogo
Aeroportuario" (Airport Service), al que le preguntamos si existen.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from app.domain.events import ItineraryCreated
from app.domain.exceptions import InvalidItinerary

MAX_USER_NAME_LENGTH = 100


@dataclass
class Itinerary:
    id: UUID
    user_name: str
    departure_airport_id: int
    arrival_airport_id: int
    travel_date: date
    duration_minutes: int
    created_at: datetime
    updated_at: datetime | None = None
    # Eventos de dominio pendientes de publicar (no se persisten como columna).
    events: list = field(default_factory=list, repr=False, compare=False)

    @classmethod
    def create(
        cls,
        user_name: str,
        departure_airport_id: int,
        arrival_airport_id: int,
        travel_date: date,
        duration_minutes: int,
    ) -> "Itinerary":
        """Fábrica: crea un itinerario válido y registra el evento ItineraryCreated."""
        itinerary = cls(
            id=uuid4(),
            user_name=user_name.strip(),
            departure_airport_id=departure_airport_id,
            arrival_airport_id=arrival_airport_id,
            travel_date=travel_date,
            duration_minutes=duration_minutes,
            created_at=datetime.now(timezone.utc),
        )
        itinerary._validate()
        itinerary.events.append(
            ItineraryCreated(
                itinerary_id=itinerary.id,
                user_name=itinerary.user_name,
                departure_airport_id=departure_airport_id,
                arrival_airport_id=arrival_airport_id,
                travel_date=travel_date,
                duration_minutes=duration_minutes,
            )
        )
        return itinerary

    def update(
        self,
        user_name: str,
        departure_airport_id: int,
        arrival_airport_id: int,
        travel_date: date,
        duration_minutes: int,
    ) -> None:
        self.user_name = user_name.strip()
        self.departure_airport_id = departure_airport_id
        self.arrival_airport_id = arrival_airport_id
        self.travel_date = travel_date
        self.duration_minutes = duration_minutes
        self.updated_at = datetime.now(timezone.utc)
        self._validate()

    def pull_events(self) -> list:
        """Entrega los eventos pendientes y vacía la lista."""
        events, self.events = self.events, []
        return events

    # ---- Reglas de negocio (invariantes) -------------------------------
    def _validate(self) -> None:
        if not self.user_name:
            raise InvalidItinerary("El nombre del usuario es obligatorio")
        if len(self.user_name) > MAX_USER_NAME_LENGTH:
            raise InvalidItinerary(f"El nombre del usuario no puede superar {MAX_USER_NAME_LENGTH} caracteres")
        if self.departure_airport_id <= 0 or self.arrival_airport_id <= 0:
            raise InvalidItinerary("Los IDs de aeropuerto deben ser positivos")
        if self.departure_airport_id == self.arrival_airport_id:
            raise InvalidItinerary("El aeropuerto de salida y el de llegada deben ser distintos")
        if self.duration_minutes <= 0:
            raise InvalidItinerary("La duración del viaje debe ser mayor a 0 minutos")
        if self.travel_date < date.today():
            raise InvalidItinerary("La fecha de viaje no puede estar en el pasado")

"""Modelos Pydantic de entrada/salida (lo que se documenta en Swagger)."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.application.itinerary_service import ItineraryData
from app.domain.models import Itinerary


class ItineraryRequest(BaseModel):
    user_name: str = Field(min_length=1, max_length=100, examples=["Ana Gómez"])
    departure_airport_id: int = Field(gt=0, description="ID del aeropuerto de salida", examples=[1])
    arrival_airport_id: int = Field(gt=0, description="ID del aeropuerto de llegada", examples=[3])
    travel_date: date = Field(examples=["2027-03-15"])
    duration_minutes: int = Field(gt=0, description="Duración del viaje en minutos", examples=[55])

    def to_data(self) -> ItineraryData:
        return ItineraryData(**self.model_dump())


class ItineraryResponse(BaseModel):
    id: UUID
    user_name: str
    departure_airport_id: int
    arrival_airport_id: int
    travel_date: date
    duration_minutes: int
    created_at: datetime
    updated_at: datetime | None

    @classmethod
    def from_domain(cls, itinerary: Itinerary) -> "ItineraryResponse":
        return cls.model_validate(itinerary, from_attributes=True)


class ErrorResponse(BaseModel):
    status: int = Field(examples=[404])
    title: str = Field(examples=["Not Found"])
    detail: str = Field(examples=["El itinerario no existe"])

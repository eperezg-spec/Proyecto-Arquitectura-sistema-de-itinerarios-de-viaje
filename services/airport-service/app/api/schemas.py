"""Modelos Pydantic de entrada/salida de la API REST (lo que se ve en Swagger)."""
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models import Airport


class AirportResponse(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["Aeropuerto Internacional El Edén"])
    iata_code: str = Field(examples=["AXM"])
    oaci_code: str = Field(examples=["SKAR"])
    airport_type: str = Field(examples=["Internacional"])
    city: str = Field(examples=["Armenia"])
    department: str = Field(examples=["Quindío"])
    latitude: float | None = Field(examples=[4.4532])
    longitude: float | None = Field(examples=[-75.7659])

    @classmethod
    def from_domain(cls, airport: Airport) -> "AirportResponse":
        return cls(**airport.__dict__)


class PlotlyMapResponse(BaseModel):
    """Formato listo para Plotly.newPlot(div, data, layout)."""

    data: list[dict[str, Any]]
    layout: dict[str, Any]


class CacheInvalidationResponse(BaseModel):
    deleted_keys: int


class ErrorResponse(BaseModel):
    """Formato único de error para todos los servicios."""

    status: int = Field(examples=[404])
    title: str = Field(examples=["Not Found"])
    detail: str = Field(examples=["El aeropuerto 999 no existe"])

"""
CASOS DE USO del Airport Service.

Esta clase solo conoce el PUERTO (AirportProvider), nunca la implementación.
No sabe si los datos vienen de API Colombia, de Redis o de un fake de pruebas.
"""
from typing import Any

from app.application.plotly_mapper import to_plotly_map
from app.application.ports import AirportProvider
from app.domain.models import Airport


class AirportService:
    def __init__(self, provider: AirportProvider):
        self._provider = provider

    def get_airport(self, airport_id: int) -> Airport:
        return self._provider.get_by_id(airport_id)

    def list_airports(self) -> list[Airport]:
        return sorted(self._provider.list_all(), key=lambda airport: airport.name)

    def get_map(self) -> dict[str, Any]:
        """Mapa Plotly con todos los aeropuertos."""
        return to_plotly_map(self.list_airports())

    def get_airport_map(self, airport_id: int) -> dict[str, Any]:
        """Mapa Plotly con un solo aeropuerto."""
        return to_plotly_map([self.get_airport(airport_id)])

    def invalidate_cache(self) -> int:
        return self._provider.invalidate_cache()

"""
PUERTOS (interfaces) de la capa de aplicación.

Un "puerto" es un contrato: dice QUÉ necesita la aplicación, no CÓMO se hace.
La implementación concreta (el "adapter") vive en la capa de infraestructura.

    Caso de uso  --usa-->  AirportProvider (puerto)  <--implementa--  ApiColombiaAirportAdapter

Gracias a esto podríamos cambiar API Colombia por otra fuente (o por un fake en
las pruebas) sin tocar ni una línea del dominio ni de los casos de uso.
"""
from abc import ABC, abstractmethod

from app.domain.models import Airport


class AirportProvider(ABC):
    """Puerto de salida: fuente de información de aeropuertos."""

    @abstractmethod
    def get_by_id(self, airport_id: int) -> Airport:
        """Devuelve el aeropuerto o lanza AirportNotFound."""

    @abstractmethod
    def list_all(self) -> list[Airport]:
        """Devuelve todos los aeropuertos disponibles."""

    def invalidate_cache(self) -> int:
        """Borra la caché si la implementación tiene una. Devuelve cuántas claves borró."""
        return 0

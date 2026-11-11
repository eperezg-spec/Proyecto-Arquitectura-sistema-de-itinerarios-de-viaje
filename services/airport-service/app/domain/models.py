"""
CAPA DE DOMINIO - Contexto delimitado "Catálogo Aeroportuario".

Aquí vive el modelo PROPIO del sistema. Regla de oro de la arquitectura
hexagonal: este archivo NO importa nada de frameworks (FastAPI, httpx, Redis...).
Es Python puro, por eso es fácil de probar y no depende de la API externa.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Airport:
    """Aeropuerto colombiano tal como lo entiende NUESTRO sistema.

    Fíjate que los nombres de los campos son nuestros (snake_case, en el idioma
    del dominio), no los de API Colombia (iataCode, deparmentId...). El Adapter
    es el encargado de traducir de un formato al otro.
    """

    id: int
    name: str
    iata_code: str
    oaci_code: str
    airport_type: str
    city: str
    department: str
    latitude: float | None
    longitude: float | None

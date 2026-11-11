"""
RAÍZ DE COMPOSICIÓN: conecta los puertos con sus adapters reales.
En las pruebas se reemplaza con app.dependency_overrides.
"""
import os

from fastapi import Depends

from app.api.security import require_user
from app.application.itinerary_service import ItineraryService
from app.infrastructure.airport_client import HttpAirportChecker
from app.infrastructure.database import SessionLocal
from app.infrastructure.sql_repository import SqlItineraryRepository

AIRPORT_SERVICE_URL = os.getenv("AIRPORT_SERVICE_URL", "http://localhost:8001")


def get_itinerary_service(user: dict = Depends(require_user)) -> ItineraryService:
    # El checker se crea por petición porque lleva el token del usuario actual.
    return ItineraryService(
        repository=SqlItineraryRepository(SessionLocal),
        airport_checker=HttpAirportChecker(AIRPORT_SERVICE_URL, token=user["raw_token"]),
    )

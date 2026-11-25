"""
RAÍZ DE COMPOSICIÓN: conecta los puertos con sus adapters reales.
En las pruebas se reemplaza con app.dependency_overrides.

El puerto AirportChecker tiene DOS adapters intercambiables:
  AIRPORT_TRANSPORT=grpc  (por defecto) -> GrpcAirportChecker, gRPC + mTLS
  AIRPORT_TRANSPORT=http                -> HttpAirportChecker, REST + JWT
"""
import os
from functools import lru_cache

from fastapi import Depends

from app.api.security import require_user
from app.application.itinerary_service import ItineraryService
from app.application.ports import AirportChecker
from app.infrastructure.airport_client import HttpAirportChecker
from app.infrastructure.database import SessionLocal
from app.infrastructure.sql_repository import SqlItineraryRepository

AIRPORT_TRANSPORT = os.getenv("AIRPORT_TRANSPORT", "grpc")
AIRPORT_SERVICE_URL = os.getenv("AIRPORT_SERVICE_URL", "http://localhost:8001")
AIRPORT_GRPC_TARGET = os.getenv("AIRPORT_GRPC_TARGET", "localhost:50051")


@lru_cache  # un solo canal gRPC (y un solo certificado) para todo el proceso
def _grpc_airport_checker() -> AirportChecker:
    from app.infrastructure.airport_grpc_client import GrpcAirportChecker, create_channel
    from app.infrastructure.vault import issue_certificate

    tls = issue_certificate(os.getenv("SERVICE_CN", "itinerary-service"))
    return GrpcAirportChecker(create_channel(AIRPORT_GRPC_TARGET, tls))


def get_airport_checker(user: dict = Depends(require_user)) -> AirportChecker:
    if AIRPORT_TRANSPORT == "http":
        # El adapter HTTP se crea por petición porque propaga el token del usuario actual.
        return HttpAirportChecker(AIRPORT_SERVICE_URL, token=user["raw_token"])
    return _grpc_airport_checker()


def get_itinerary_service(airport_checker: AirportChecker = Depends(get_airport_checker)) -> ItineraryService:
    return ItineraryService(repository=SqlItineraryRepository(SessionLocal), airport_checker=airport_checker)

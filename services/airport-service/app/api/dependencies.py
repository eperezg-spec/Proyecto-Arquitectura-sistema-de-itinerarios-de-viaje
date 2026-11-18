"""
RAÍZ DE COMPOSICIÓN: aquí (y solo aquí) se conectan los puertos con sus adapters.

    AirportService( CachedAirportProvider( ApiColombiaAirportAdapter( CircuitBreaker ) ) )

En las pruebas se reemplaza get_airport_service con app.dependency_overrides.
"""
import os
from functools import lru_cache

import redis

from app.application.airport_service import AirportService
from app.infrastructure.api_colombia_adapter import ApiColombiaAirportAdapter
from app.infrastructure.circuit_breaker import CircuitBreaker
from app.infrastructure.redis_cache import CachedAirportProvider


@lru_cache  # una sola instancia para toda la app (el circuit breaker debe ser compartido)
def get_airport_service() -> AirportService:
    adapter = ApiColombiaAirportAdapter(
        base_url=os.getenv("API_COLOMBIA_URL", "https://api-colombia.com"),
        circuit_breaker=CircuitBreaker(
            failure_threshold=int(os.getenv("CB_FAILURE_THRESHOLD", "5")),
            reset_timeout=float(os.getenv("CB_RESET_TIMEOUT_SECONDS", "30")),
        ),
        timeout_seconds=float(os.getenv("API_COLOMBIA_TIMEOUT_SECONDS", "3")),
    )
    redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
    cached = CachedAirportProvider(adapter, redis_client, ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "3600")))
    return AirportService(cached)


def start_grpc_server():
    """Arranca el servidor gRPC interno (lo llama el lifespan de main.py).

    Con Vault: pide un certificado para "airport-service" y exige mTLS.
    Sin Vault: servidor sin TLS (solo para desarrollo/pruebas).
    """
    from app.api.grpc_server import AirportGrpcService, create_grpc_server
    from app.infrastructure.vault import issue_certificate

    tls = issue_certificate(os.getenv("SERVICE_CN", "airport-service"))
    allowed = {name.strip() for name in os.getenv("GRPC_ALLOWED_CLIENTS", "itinerary-service").split(",")}
    servicer = AirportGrpcService(get_airport_service, allowed_clients=allowed if tls else None)
    server, _ = create_grpc_server(servicer, port=int(os.getenv("GRPC_PORT", "50051")), tls=tls)
    server.start()
    return server

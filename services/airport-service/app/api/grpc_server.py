"""
ADAPTER DE ENTRADA gRPC (igual que routes.py es el adapter de entrada REST).

Arquitectura hexagonal: el MISMO caso de uso (AirportService) se expone por dos
puertas distintas sin cambiar una línea del dominio:

    navegador / gateway ──REST/JSON──> routes.py      ─┐
                                                       ├──> AirportService (caso de uso)
    itinerary-service ───gRPC + mTLS──> grpc_server.py ─┘

mTLS (TLS mutuo): el servidor presenta su certificado Y exige uno al cliente,
ambos firmados por la CA interna de Vault. Además se verifica el nombre (CN) del
certificado del cliente: solo "itinerary-service" puede llamar.
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import grpc

from app.application.airport_service import AirportService
from app.domain.exceptions import AirportNotFound, AirportProviderUnavailable
from app.domain.models import Airport
from app.grpc_stubs import airport_pb2, airport_pb2_grpc
from app.infrastructure.metrics import GRPC_REQUESTS
from app.infrastructure.vault import TlsMaterial

logger = logging.getLogger(__name__)


def to_message(airport: Airport) -> airport_pb2.Airport:
    """Dominio -> mensaje Protobuf."""
    has_coordinates = airport.latitude is not None and airport.longitude is not None
    return airport_pb2.Airport(
        id=airport.id,
        name=airport.name,
        iata_code=airport.iata_code,
        city=airport.city,
        department=airport.department,
        has_coordinates=has_coordinates,
        latitude=airport.latitude or 0.0,
        longitude=airport.longitude or 0.0,
    )


class AirportGrpcService(airport_pb2_grpc.AirportServiceServicer):
    def __init__(self, service_factory: Callable[[], AirportService], allowed_clients: set[str] | None = None):
        self._service_factory = service_factory
        self._allowed_clients = allowed_clients

    def GetAirport(self, request, context):  # noqa: N802 - nombre definido por el .proto
        self._authorize(context)
        try:
            airport = self._service_factory().get_airport(request.id)
        except AirportNotFound as exc:
            GRPC_REQUESTS.labels("GetAirport", "NOT_FOUND").inc()
            context.abort(grpc.StatusCode.NOT_FOUND, str(exc))
        except AirportProviderUnavailable as exc:
            GRPC_REQUESTS.labels("GetAirport", "UNAVAILABLE").inc()
            context.abort(grpc.StatusCode.UNAVAILABLE, str(exc))
        GRPC_REQUESTS.labels("GetAirport", "OK").inc()
        return to_message(airport)

    def _authorize(self, context) -> None:
        """Autorización por identidad de servicio: CN del certificado del cliente."""
        if self._allowed_clients is None:  # sin mTLS (desarrollo / pruebas)
            return
        names = {value.decode() for value in context.auth_context().get("x509_common_name", [])}
        if not names & self._allowed_clients:
            GRPC_REQUESTS.labels("GetAirport", "PERMISSION_DENIED").inc()
            logger.warning("Cliente gRPC no autorizado", extra={"extra_fields": {"client_cn": sorted(names)}})
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Este servicio no puede consultar aeropuertos")


def create_grpc_server(
    servicer: AirportGrpcService, port: int, tls: TlsMaterial | None, host: str = "[::]"
) -> tuple[grpc.Server, int]:
    """Crea el servidor (sin arrancarlo). Devuelve (servidor, puerto real); port=0 elige uno libre."""
    server = grpc.server(ThreadPoolExecutor(max_workers=10))
    airport_pb2_grpc.add_AirportServiceServicer_to_server(servicer, server)
    address = f"{host}:{port}"
    if tls is None:
        port = server.add_insecure_port(address)
        logger.warning("Servidor gRPC SIN TLS (no hay Vault configurado)", extra={"extra_fields": {"port": port}})
    else:
        credentials = grpc.ssl_server_credentials(
            [(tls.private_key, tls.certificate)],
            root_certificates=tls.ca_certificate,
            require_client_auth=True,  # <- esto es lo que lo hace "mutuo"
        )
        port = server.add_secure_port(address, credentials)
        logger.info("Servidor gRPC con mTLS", extra={"extra_fields": {"port": port}})
    return server, port

"""
ADAPTER gRPC + mTLS que implementa el puerto AirportChecker (es el que se usa por defecto).

    ItineraryService ──> AirportChecker (puerto)
                              ▲
              ┌───────────────┴────────────────┐
     GrpcAirportChecker (este)        HttpAirportChecker (alternativa REST)

El caso de uso no sabe cuál de los dos se usa: se elige en dependencies.py con
la variable AIRPORT_TRANSPORT=grpc|http. Esto demuestra la arquitectura
hexagonal: cambiar el protocolo NO toca el dominio ni la aplicación.

Seguridad: el canal usa mTLS. Este servicio presenta un certificado con
CN=itinerary-service emitido por la CA de Vault, y verifica que el servidor
presente uno válido para "airport-service".
"""
import logging

import grpc

from app.application.ports import AirportChecker
from app.domain.exceptions import AirportServiceUnavailable
from app.grpc_stubs import airport_pb2, airport_pb2_grpc
from app.infrastructure.vault import TlsMaterial

logger = logging.getLogger(__name__)


def create_channel(target: str, tls: TlsMaterial | None) -> grpc.Channel:
    """Canal gRPC reutilizable (HTTP/2 multiplexa todas las llamadas en una conexión)."""
    if tls is None:
        logger.warning("Canal gRPC SIN TLS (no hay Vault configurado)", extra={"extra_fields": {"target": target}})
        return grpc.insecure_channel(target)
    credentials = grpc.ssl_channel_credentials(
        root_certificates=tls.ca_certificate,  # para verificar al servidor
        private_key=tls.private_key,  # para que el servidor nos verifique a nosotros
        certificate_chain=tls.certificate,
    )
    return grpc.secure_channel(target, credentials)


class GrpcAirportChecker(AirportChecker):
    def __init__(self, channel: grpc.Channel, timeout_seconds: float = 5.0):
        self._stub = airport_pb2_grpc.AirportServiceStub(channel)
        self._timeout = timeout_seconds

    def exists(self, airport_id: int) -> bool:
        try:
            self._stub.GetAirport(airport_pb2.GetAirportRequest(id=airport_id), timeout=self._timeout)
            return True
        except grpc.RpcError as exc:
            if exc.code() == grpc.StatusCode.NOT_FOUND:
                return False
            logger.error(
                "Fallo la llamada gRPC al Airport Service",
                extra={"extra_fields": {"code": exc.code().name, "detail": exc.details()}},
            )
            raise AirportServiceUnavailable(f"Airport Service no disponible (gRPC {exc.code().name})") from exc

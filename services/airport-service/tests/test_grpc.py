"""
Pruebas del ADAPTER DE ENTRADA gRPC, con un servidor gRPC real en un puerto local.

- Sin TLS: se prueba el mapeo dominio -> Protobuf y los códigos de error.
- Con mTLS: se generan certificados de prueba con `trustme` (una CA falsa, igual
  que la CA de Vault) y se comprueba que:
    * itinerary-service (CN permitido) puede llamar,
    * otro servicio con certificado válido pero CN no permitido recibe PERMISSION_DENIED,
    * un cliente SIN certificado no logra ni conectarse.
"""
import grpc
import pytest
import trustme

from app.api.grpc_server import AirportGrpcService, create_grpc_server
from app.application.airport_service import AirportService
from app.application.ports import AirportProvider
from app.domain.exceptions import AirportNotFound, AirportProviderUnavailable
from app.domain.models import Airport
from app.grpc_stubs import airport_pb2, airport_pb2_grpc
from app.infrastructure.vault import TlsMaterial

BOGOTA = Airport(1, "El Dorado", "BOG", "SKBO", "Internacional", "Bogotá", "Cundinamarca", 4.70, -74.14)
SIN_COORDENADAS = Airport(2, "Del Café", "AXM", "SKAR", "Nacional", "Armenia", "Quindío", None, None)


class FakeProvider(AirportProvider):
    unavailable = False

    def get_by_id(self, airport_id):
        if self.unavailable:
            raise AirportProviderUnavailable("API caída")
        airports = {1: BOGOTA, 2: SIN_COORDENADAS}
        if airport_id not in airports:
            raise AirportNotFound(airport_id)
        return airports[airport_id]

    def list_all(self):
        return [BOGOTA, SIN_COORDENADAS]


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def insecure_stub(provider):
    servicer = AirportGrpcService(lambda: AirportService(provider))
    server, port = create_grpc_server(servicer, port=0, tls=None, host="127.0.0.1")
    server.start()
    channel = grpc.insecure_channel(f"127.0.0.1:{port}")
    yield airport_pb2_grpc.AirportServiceStub(channel)
    channel.close()
    server.stop(None)


# --------------------------------------------------------------- sin TLS
def test_get_airport_devuelve_el_mensaje_protobuf(insecure_stub):
    airport = insecure_stub.GetAirport(airport_pb2.GetAirportRequest(id=1), timeout=5)
    assert airport.iata_code == "BOG"
    assert airport.has_coordinates is True
    assert airport.latitude == pytest.approx(4.70)


def test_aeropuerto_sin_coordenadas_se_marca_con_has_coordinates_false(insecure_stub):
    airport = insecure_stub.GetAirport(airport_pb2.GetAirportRequest(id=2), timeout=5)
    assert airport.has_coordinates is False


def test_aeropuerto_inexistente_devuelve_not_found(insecure_stub):
    with pytest.raises(grpc.RpcError) as error:
        insecure_stub.GetAirport(airport_pb2.GetAirportRequest(id=999), timeout=5)
    assert error.value.code() == grpc.StatusCode.NOT_FOUND


def test_api_externa_caida_devuelve_unavailable(insecure_stub, provider):
    provider.unavailable = True
    with pytest.raises(grpc.RpcError) as error:
        insecure_stub.GetAirport(airport_pb2.GetAirportRequest(id=1), timeout=5)
    assert error.value.code() == grpc.StatusCode.UNAVAILABLE


# --------------------------------------------------------------- con mTLS
@pytest.fixture(scope="module")
def ca():
    return trustme.CA()


def _material(ca, cert) -> TlsMaterial:
    return TlsMaterial(
        certificate=b"".join(blob.bytes() for blob in cert.cert_chain_pems),
        private_key=cert.private_key_pem.bytes(),
        ca_certificate=ca.cert_pem.bytes(),
    )


@pytest.fixture
def mtls_port(ca, provider):
    server_tls = _material(ca, ca.issue_cert("localhost", common_name="airport-service"))
    servicer = AirportGrpcService(lambda: AirportService(provider), allowed_clients={"itinerary-service"})
    server, port = create_grpc_server(servicer, port=0, tls=server_tls, host="localhost")
    server.start()
    yield port
    server.stop(None)


def _client(ca, port, client_cn=None):
    if client_cn is None:  # cliente sin certificado propio
        credentials = grpc.ssl_channel_credentials(root_certificates=ca.cert_pem.bytes())
    else:
        tls = _material(ca, ca.issue_cert(client_cn, common_name=client_cn))
        credentials = grpc.ssl_channel_credentials(tls.ca_certificate, tls.private_key, tls.certificate)
    channel = grpc.secure_channel(f"localhost:{port}", credentials)
    return airport_pb2_grpc.AirportServiceStub(channel)


def test_mtls_cliente_autorizado_puede_consultar(ca, mtls_port):
    stub = _client(ca, mtls_port, client_cn="itinerary-service")
    assert stub.GetAirport(airport_pb2.GetAirportRequest(id=1), timeout=5).name == "El Dorado"


def test_mtls_certificado_valido_pero_cn_no_permitido_es_rechazado(ca, mtls_port):
    stub = _client(ca, mtls_port, client_cn="servicio-intruso")
    with pytest.raises(grpc.RpcError) as error:
        stub.GetAirport(airport_pb2.GetAirportRequest(id=1), timeout=5)
    assert error.value.code() == grpc.StatusCode.PERMISSION_DENIED


def test_mtls_cliente_sin_certificado_no_puede_conectarse(ca, mtls_port):
    stub = _client(ca, mtls_port, client_cn=None)
    with pytest.raises(grpc.RpcError) as error:
        stub.GetAirport(airport_pb2.GetAirportRequest(id=1), timeout=5)
    assert error.value.code() == grpc.StatusCode.UNAVAILABLE  # el handshake TLS falla

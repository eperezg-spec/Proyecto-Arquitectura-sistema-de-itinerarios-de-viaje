"""
Pruebas del ADAPTER de salida GrpcAirportChecker contra un servidor gRPC falso
(en memoria, en un puerto local). Verifican la traducción de códigos gRPC a la
respuesta que espera el puerto AirportChecker:
  OK -> True,  NOT_FOUND -> False,  cualquier otro error -> AirportServiceUnavailable
"""
from concurrent.futures import ThreadPoolExecutor

import grpc
import pytest

from app.domain.exceptions import AirportServiceUnavailable
from app.grpc_stubs import airport_pb2, airport_pb2_grpc
from app.infrastructure.airport_grpc_client import GrpcAirportChecker, create_channel


class FakeAirportServer(airport_pb2_grpc.AirportServiceServicer):
    def __init__(self):
        self.error_code = None

    def GetAirport(self, request, context):  # noqa: N802
        if self.error_code is not None:
            context.abort(self.error_code, "falla simulada")
        if request.id != 1:
            context.abort(grpc.StatusCode.NOT_FOUND, "no existe")
        return airport_pb2.Airport(id=1, name="El Dorado", iata_code="BOG")


@pytest.fixture
def fake_server():
    servicer = FakeAirportServer()
    server = grpc.server(ThreadPoolExecutor(max_workers=2))
    airport_pb2_grpc.add_AirportServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    yield servicer, f"127.0.0.1:{port}"
    server.stop(None)


def test_aeropuerto_existente(fake_server):
    _, target = fake_server
    assert GrpcAirportChecker(create_channel(target, tls=None)).exists(1) is True


def test_aeropuerto_inexistente(fake_server):
    _, target = fake_server
    assert GrpcAirportChecker(create_channel(target, tls=None)).exists(999) is False


def test_servicio_caido_lanza_airport_service_unavailable(fake_server):
    servicer, target = fake_server
    servicer.error_code = grpc.StatusCode.UNAVAILABLE
    with pytest.raises(AirportServiceUnavailable):
        GrpcAirportChecker(create_channel(target, tls=None)).exists(1)


def test_servidor_inalcanzable_lanza_airport_service_unavailable():
    checker = GrpcAirportChecker(create_channel("127.0.0.1:1", tls=None), timeout_seconds=1)
    with pytest.raises(AirportServiceUnavailable):
        checker.exists(1)

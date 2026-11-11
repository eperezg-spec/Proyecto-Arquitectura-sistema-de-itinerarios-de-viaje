"""Pruebas del patrón Adapter: traducción + reintentos. No llaman a internet (MockTransport)."""
import httpx
import pytest

from app.domain.exceptions import AirportNotFound, AirportProviderUnavailable
from app.infrastructure.api_colombia_adapter import ApiColombiaAirportAdapter
from app.infrastructure.circuit_breaker import CircuitBreaker

# Respuesta real (recortada) de https://api-colombia.com/api/v1/Airport/1
# Nota: latitude y longitude vienen INVERTIDAS desde la API.
API_COLOMBIA_AIRPORT = {
    "id": 1,
    "name": "Aeropuerto Internacional El Edén",
    "iataCode": "AXM",
    "oaciCode": "SKAR",
    "type": "Internacional",
    "deparmentId": 25,
    "department": {"id": 25, "name": "Quindío"},
    "cityId": 885,
    "city": {"id": 885, "name": "Armenia"},
    "latitude": -75.7659806671205,
    "longitude": 4.4532428642135,
}


def make_adapter(handler, breaker: CircuitBreaker | None = None) -> ApiColombiaAirportAdapter:
    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://fake-api")
    return ApiColombiaAirportAdapter(client=client, circuit_breaker=breaker or CircuitBreaker())


def test_traduce_respuesta_externa_al_modelo_de_dominio():
    adapter = make_adapter(lambda request: httpx.Response(200, json=API_COLOMBIA_AIRPORT))

    airport = adapter.get_by_id(1)

    assert airport.name == "Aeropuerto Internacional El Edén"
    assert airport.iata_code == "AXM"
    assert airport.city == "Armenia"
    assert airport.department == "Quindío"
    # El adapter corrige las coordenadas invertidas de la API externa
    assert airport.latitude == pytest.approx(4.4532, abs=1e-3)
    assert airport.longitude == pytest.approx(-75.7659, abs=1e-3)


def test_coordenadas_0_0_se_consideran_desconocidas():
    sin_coordenadas = {**API_COLOMBIA_AIRPORT, "latitude": 0, "longitude": 0}
    adapter = make_adapter(lambda request: httpx.Response(200, json=sin_coordenadas))

    airport = adapter.get_by_id(1)

    assert airport.latitude is None
    assert airport.longitude is None


def test_404_de_la_api_se_traduce_a_airport_not_found():
    adapter = make_adapter(lambda request: httpx.Response(404))

    with pytest.raises(AirportNotFound):
        adapter.get_by_id(999)


def test_reintenta_3_veces_ante_error_500_y_luego_falla():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(500)

    adapter = make_adapter(handler)

    with pytest.raises(AirportProviderUnavailable):
        adapter.get_by_id(1)
    assert len(calls) == 3


def test_circuit_breaker_abierto_no_llama_a_la_api():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(500)

    adapter = make_adapter(handler, CircuitBreaker(failure_threshold=1, reset_timeout=60))

    with pytest.raises(AirportProviderUnavailable):
        adapter.get_by_id(1)  # 3 intentos fallidos -> el circuito se abre
    calls.clear()

    with pytest.raises(AirportProviderUnavailable, match="abierto"):
        adapter.get_by_id(1)
    assert calls == []  # falla rápido, sin tocar la API

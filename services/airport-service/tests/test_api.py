"""Pruebas de la API REST reemplazando el proveedor real por uno falso."""
import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_airport_service
from app.api.security import JWT_ALGORITHM, JWT_SECRET
from app.application.airport_service import AirportService
from app.application.ports import AirportProvider
from app.domain.exceptions import AirportNotFound, AirportProviderUnavailable
from app.domain.models import Airport
from app.main import app

AIRPORT = Airport(1, "El Dorado", "BOG", "SKBO", "Internacional", "Bogotá", "Cundinamarca", 4.70, -74.14)


class FakeProvider(AirportProvider):
    unavailable = False

    def get_by_id(self, airport_id):
        if self.unavailable:
            raise AirportProviderUnavailable("API caída")
        if airport_id != 1:
            raise AirportNotFound(airport_id)
        return AIRPORT

    def list_all(self):
        return [AIRPORT]


@pytest.fixture
def provider():
    fake = FakeProvider()
    app.dependency_overrides[get_airport_service] = lambda: AirportService(fake)
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    token = jwt.encode({"sub": "tester"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


def test_obtener_aeropuerto(provider, client):
    response = client.get("/api/v1/airports/1")
    assert response.status_code == 200
    assert response.json()["iata_code"] == "BOG"


def test_aeropuerto_inexistente_devuelve_404(provider, client):
    response = client.get("/api/v1/airports/999")
    assert response.status_code == 404
    assert response.json()["title"] == "Not Found"


def test_api_externa_caida_devuelve_503(provider, client):
    provider.unavailable = True
    response = client.get("/api/v1/airports/1")
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "30"


def test_mapa_en_formato_plotly(provider, client):
    body = client.get("/api/v1/airports/map").json()
    assert body["data"][0]["type"] == "scattergeo"
    assert body["data"][0]["lat"] == [4.70]


def test_sin_token_devuelve_401(provider):
    response = TestClient(app).get("/api/v1/airports/1")
    assert response.status_code == 401

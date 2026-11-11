"""Pruebas de la API REST con el servicio conectado a fakes."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_itinerary_service
from app.api.security import require_user
from app.application.itinerary_service import ItineraryService
from app.main import app
from tests.conftest import FakeAirportChecker, InMemoryRepository


@pytest.fixture
def client():
    service = ItineraryService(InMemoryRepository(), FakeAirportChecker())
    app.dependency_overrides[get_itinerary_service] = lambda: service
    app.dependency_overrides[require_user] = lambda: {"sub": "tester", "raw_token": "x"}
    yield TestClient(app)
    app.dependency_overrides.clear()


def body(**changes):
    data = {
        "user_name": "Ana",
        "departure_airport_id": 1,
        "arrival_airport_id": 2,
        "travel_date": str(date.today() + timedelta(days=5)),
        "duration_minutes": 60,
    }
    return {**data, **changes}


def test_crud_completo(client):
    created = client.post("/api/v1/itineraries", json=body())
    assert created.status_code == 201
    itinerary_id = created.json()["id"]
    assert created.headers["Location"].endswith(itinerary_id)

    assert client.get(f"/api/v1/itineraries/{itinerary_id}").status_code == 200
    assert len(client.get("/api/v1/itineraries").json()) == 1

    updated = client.put(f"/api/v1/itineraries/{itinerary_id}", json=body(duration_minutes=90))
    assert updated.json()["duration_minutes"] == 90

    assert client.delete(f"/api/v1/itineraries/{itinerary_id}").status_code == 204
    assert client.get(f"/api/v1/itineraries/{itinerary_id}").status_code == 404


def test_aeropuerto_inexistente_devuelve_422(client):
    response = client.post("/api/v1/itineraries", json=body(arrival_airport_id=999))
    assert response.status_code == 422
    assert response.json()["title"] == "Airport Not Found"


def test_datos_invalidos_devuelven_422(client):
    response = client.post("/api/v1/itineraries", json=body(duration_minutes=-5))
    assert response.status_code == 422


def test_sin_token_devuelve_401():
    response = TestClient(app).get("/api/v1/itineraries")
    assert response.status_code == 401

"""
PRUEBA E2E con Testcontainers: levanta TODO el docker-compose, ejecuta el flujo
completo y al final destruye el entorno.

  pip install -r tests/e2e/requirements.txt
  pytest tests/e2e -v -s          (tarda varios minutos la primera vez)

Flujo verificado:
  login -> mapa -> crear itinerario (valida aeropuertos vía HTTP) ->
  outbox -> RabbitMQ -> Lambda -> fila en notification_db
"""
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
import psycopg
import pytest
from testcontainers.compose import DockerCompose

ROOT = Path(__file__).resolve().parents[2]
GATEWAY = "http://localhost:8080"


def wait_until(check, timeout: int, message: str):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            result = check()
            if result:
                return result
        except Exception:
            pass
        time.sleep(3)
    pytest.fail(message)


@pytest.fixture(scope="module")
def system():
    compose = DockerCompose(str(ROOT), compose_file_name="docker-compose.yml", build=True)
    compose.start()
    try:
        wait_until(lambda: httpx.get(f"{GATEWAY}/").status_code == 200, 180, "El gateway no arrancó")
        yield compose
    finally:
        compose.stop()  # destruye contenedores (equivale a docker compose down)


def test_crear_itinerario_genera_notificacion(system):
    token = wait_until(
        lambda: httpx.post(f"{GATEWAY}/auth/token", json={"username": "viajero", "password": "viajero123"}).json()["access_token"],
        120,
        "No se pudo obtener token",
    )
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Mapa Plotly desde el Airport Service (vía gateway)
    figure = wait_until(lambda: httpx.get(f"{GATEWAY}/api/v1/airports/map", headers=headers, timeout=30).json(), 120, "Mapa no disponible")
    assert figure["data"][0]["type"] == "scattergeo"

    # 2. Crear itinerario
    body = {
        "user_name": "E2E Tester",
        "departure_airport_id": 1,
        "arrival_airport_id": 2,
        "travel_date": str(date.today() + timedelta(days=7)),
        "duration_minutes": 50,
    }
    created = wait_until(
        lambda: (r := httpx.post(f"{GATEWAY}/api/v1/itineraries", json=body, headers=headers, timeout=30)).status_code == 201 and r.json(),
        120,
        "No se pudo crear el itinerario",
    )

    # 3. Aeropuerto inexistente -> 422
    bad = httpx.post(f"{GATEWAY}/api/v1/itineraries", json={**body, "arrival_airport_id": 99999}, headers=headers, timeout=30)
    assert bad.status_code == 422

    # 4. La notificación llega a notification_db (asíncrono: RabbitMQ -> Lambda)
    def notification_saved():
        with psycopg.connect("postgresql://notification_user:notification_pass@localhost:5432/notification_db") as conn:
            row = conn.execute("SELECT status FROM notifications WHERE itinerary_id = %s", (created["id"],)).fetchone()
            return row and row[0] == "SENT"

    wait_until(notification_saved, 300, "La notificación no se guardó en notification_db")

"""
PRUEBAS DE CARGA con Locust (contra el API Gateway).

  pip install locust
  locust -f tests/load/locustfile.py --host http://localhost:8080
  -> abrir http://localhost:8089, o en modo headless con reporte HTML:
  locust -f tests/load/locustfile.py --host http://localhost:8080 --headless -u 30 -r 5 -t 1m --html reporte-carga.html

Nota: el gateway limita a 10 req/s por IP. Verás respuestas 429 (rate limiting
funcionando); se cuentan como "esperadas" y no como fallos.
"""
import random
from datetime import date, timedelta

from locust import HttpUser, between, task

AIRPORT_IDS = [1, 2, 3, 4, 5, 6, 7, 8]


class TravelerUser(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self):
        response = self.client.post("/auth/token", json={"username": "viajero", "password": "viajero123"})
        self.client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"

    def _check(self, response):
        if response.status_code == 429:
            response.success()  # rate limiting esperado

    @task(4)
    def ver_mapa(self):
        with self.client.get("/api/v1/airports/map", catch_response=True) as response:
            self._check(response)

    @task(2)
    def listar_itinerarios(self):
        with self.client.get("/api/v1/itineraries", catch_response=True) as response:
            self._check(response)

    @task(1)
    def crear_itinerario(self):
        departure, arrival = random.sample(AIRPORT_IDS, 2)
        body = {
            "user_name": "Usuario de carga",
            "departure_airport_id": departure,
            "arrival_airport_id": arrival,
            "travel_date": str(date.today() + timedelta(days=random.randint(1, 90))),
            "duration_minutes": random.randint(40, 180),
        }
        with self.client.post("/api/v1/itineraries", json=body, catch_response=True) as response:
            self._check(response)

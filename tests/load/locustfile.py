"""
PRUEBAS DE CARGA con Locust (contra el API Gateway).

  pip install locust
  locust -f tests/load/locustfile.py --host http://localhost:8080
  -> abrir http://localhost:8089, o en modo headless con reporte HTML:
  locust -f tests/load/locustfile.py --host http://localhost:8080 --headless -u 30 -r 5 -t 1m --html reporte-carga.html

Escenarios usados en el informe de pruebas (docs/pruebas/informe-de-pruebas.md):
  Carga nominal:  -u 10 -r 2 -t 2m   (por debajo del límite del gateway)
  Estrés:         -u 60 -r 10 -t 2m  (muy por encima: se espera 429, nunca 5xx)

Nota: el gateway limita a 10 req/s por IP. Verás respuestas 429 (rate limiting
funcionando); se cuentan como "esperadas" y no como fallos. Al terminar se
imprime y se guarda (LOCUST_CODES_FILE) el conteo de códigos HTTP.
"""
import collections
import json
import os
import random
import time
from datetime import date, timedelta

from locust import HttpUser, between, events, task
from locust.exception import StopUser

STATUS_CODES = collections.Counter()


@events.request.add_listener
def count_status(response=None, exception=None, **_kwargs):
    STATUS_CODES[str(response.status_code) if response is not None else type(exception).__name__] += 1


@events.quitting.add_listener
def save_status_codes(**_kwargs):
    summary = dict(sorted(STATUS_CODES.items()))
    print("Códigos HTTP:", summary)
    if os.getenv("LOCUST_CODES_FILE"):
        with open(os.environ["LOCUST_CODES_FILE"], "w", encoding="utf-8") as file:
            json.dump(summary, file, indent=2)

AIRPORT_IDS = [1, 2, 3, 4, 5, 6, 7, 8]


class TravelerUser(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self):
        # Si el gateway responde 429 al login (muchos usuarios a la vez), se reintenta.
        for _ in range(30):
            with self.client.post(
                "/auth/token", json={"username": "viajero", "password": "viajero123"}, catch_response=True
            ) as response:
                if response.status_code == 200:
                    self.client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
                    return
                self._check(response)
            time.sleep(1)
        raise StopUser()  # sin token no tiene sentido seguir

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

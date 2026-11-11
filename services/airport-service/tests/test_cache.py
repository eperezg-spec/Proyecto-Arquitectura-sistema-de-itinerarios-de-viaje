"""Pruebas de la caché con un Redis falso en memoria (no hace falta levantar Redis)."""
import fnmatch

import pytest

from app.application.ports import AirportProvider
from app.domain.exceptions import AirportProviderUnavailable
from app.domain.models import Airport
from app.infrastructure.redis_cache import CachedAirportProvider

AIRPORT = Airport(1, "El Dorado", "BOG", "SKBO", "Internacional", "Bogotá", "Cundinamarca", 4.70, -74.14)


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

    def setex(self, key, ttl, value):
        self.data[key] = value

    def scan_iter(self, pattern):
        return [k for k in list(self.data) if fnmatch.fnmatch(k, pattern)]

    def delete(self, *keys):
        for key in keys:
            self.data.pop(key, None)


class CountingProvider(AirportProvider):
    def __init__(self):
        self.calls = 0
        self.fail = False

    def get_by_id(self, airport_id):
        self.calls += 1
        if self.fail:
            raise AirportProviderUnavailable("caída")
        return AIRPORT

    def list_all(self):
        return [self.get_by_id(1)]


def test_segunda_consulta_sale_de_la_cache():
    inner = CountingProvider()
    cached = CachedAirportProvider(inner, FakeRedis())

    assert cached.get_by_id(1) == AIRPORT
    assert cached.get_by_id(1) == AIRPORT
    assert inner.calls == 1


def test_fallback_a_copia_stale_si_la_api_falla():
    inner = CountingProvider()
    cached = CachedAirportProvider(inner, FakeRedis())
    cached.get_by_id(1)  # llena la caché

    cached.invalidate_cache()  # borra la copia fresca, queda la stale
    inner.fail = True

    assert cached.get_by_id(1) == AIRPORT


def test_sin_copia_stale_propaga_el_error():
    inner = CountingProvider()
    inner.fail = True
    cached = CachedAirportProvider(inner, FakeRedis())

    with pytest.raises(AirportProviderUnavailable):
        cached.get_by_id(1)

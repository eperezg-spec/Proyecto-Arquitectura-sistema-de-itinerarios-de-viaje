"""
Caché en Redis implementada como DECORADOR del puerto AirportProvider.

    CachedAirportProvider  --envuelve-->  ApiColombiaAirportAdapter

Ambos implementan el mismo puerto, así que el caso de uso no nota la diferencia.

Guardamos dos copias de cada dato:
  airport:fresh:<clave>  -> con TTL (expira). Se usa normalmente.
  airport:stale:<clave>  -> sin TTL. Solo se usa como FALLBACK si la API externa
                            falla (circuit breaker abierto, timeout...).
"""
import json
import logging
from dataclasses import asdict
from typing import Any, Callable, TypeVar

import redis

from app.application.ports import AirportProvider
from app.domain.exceptions import AirportProviderUnavailable
from app.domain.models import Airport

logger = logging.getLogger(__name__)
T = TypeVar("T")

FRESH_PREFIX = "airport:fresh:"
STALE_PREFIX = "airport:stale:"


class CachedAirportProvider(AirportProvider):
    def __init__(self, inner: AirportProvider, redis_client: redis.Redis, ttl_seconds: int = 3600):
        self._inner = inner
        self._redis = redis_client
        self._ttl = ttl_seconds

    def get_by_id(self, airport_id: int) -> Airport:
        return self._get_or_load(
            key=f"id:{airport_id}",
            loader=lambda: self._inner.get_by_id(airport_id),
            to_json=asdict,
            from_json=lambda data: Airport(**data),
        )

    def list_all(self) -> list[Airport]:
        return self._get_or_load(
            key="all",
            loader=self._inner.list_all,
            to_json=lambda airports: [asdict(a) for a in airports],
            from_json=lambda data: [Airport(**item) for item in data],
        )

    def invalidate_cache(self) -> int:
        """Invalida la caché "fresca". La copia stale se conserva para fallback."""
        keys = list(self._redis.scan_iter(f"{FRESH_PREFIX}*"))
        if keys:
            self._redis.delete(*keys)
        logger.info("Caché invalidada", extra={"extra_fields": {"deleted_keys": len(keys)}})
        return len(keys)

    # ------------------------------------------------------------------
    def _get_or_load(
        self,
        key: str,
        loader: Callable[[], T],
        to_json: Callable[[T], Any],
        from_json: Callable[[Any], T],
    ) -> T:
        cached = self._read(FRESH_PREFIX + key)
        if cached is not None:
            logger.info("Cache HIT", extra={"extra_fields": {"key": key}})
            return from_json(json.loads(cached))

        logger.info("Cache MISS", extra={"extra_fields": {"key": key}})
        try:
            value = loader()
        except AirportProviderUnavailable:
            # FALLBACK: la API externa falló, intentamos con la última copia conocida.
            stale = self._read(STALE_PREFIX + key)
            if stale is None:
                raise
            logger.warning("Fallback: se sirve la copia stale de la caché", extra={"extra_fields": {"key": key}})
            return from_json(json.loads(stale))

        payload = json.dumps(to_json(value), ensure_ascii=False)
        self._write(key, payload)
        return value

    def _read(self, full_key: str) -> str | None:
        try:
            return self._redis.get(full_key)
        except redis.RedisError as exc:
            # Si Redis se cae, el servicio sigue funcionando (sin caché).
            logger.warning("Redis no disponible al leer", extra={"extra_fields": {"error": str(exc)}})
            return None

    def _write(self, key: str, payload: str) -> None:
        try:
            self._redis.setex(FRESH_PREFIX + key, self._ttl, payload)
            self._redis.set(STALE_PREFIX + key, payload)
        except redis.RedisError as exc:
            logger.warning("Redis no disponible al escribir", extra={"extra_fields": {"error": str(exc)}})

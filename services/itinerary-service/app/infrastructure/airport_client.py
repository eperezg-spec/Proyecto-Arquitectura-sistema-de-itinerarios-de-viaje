"""
ADAPTER HTTP que implementa el puerto AirportChecker llamando al Airport Service.

Propaga el JWT del usuario (seguridad servicio a servicio) y, gracias a
OpenTelemetry, también el header 'traceparent' (traza distribuida).
"""
import logging

import httpx

from app.application.ports import AirportChecker
from app.domain.exceptions import AirportServiceUnavailable

logger = logging.getLogger(__name__)


class HttpAirportChecker(AirportChecker):
    def __init__(self, base_url: str, token: str, timeout_seconds: float = 5.0):
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout_seconds

    def exists(self, airport_id: int) -> bool:
        url = f"{self._base_url}/api/v1/airports/{airport_id}"
        try:
            response = httpx.get(url, headers={"Authorization": f"Bearer {self._token}"}, timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise AirportServiceUnavailable(f"No se pudo contactar al Airport Service: {exc}") from exc

        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False
        logger.error("Respuesta inesperada del Airport Service", extra={"extra_fields": {"status": response.status_code}})
        raise AirportServiceUnavailable(f"El Airport Service respondió HTTP {response.status_code}")

"""
PATRÓN ADAPTER: ApiColombiaAirportAdapter.

- La API externa (API Colombia) tiene SU formato: camelCase, objetos anidados,
  un typo ("deparmentId") y... ¡latitud y longitud invertidas!
- Nuestro dominio tiene SU modelo: app.domain.models.Airport.
- Este adapter implementa el puerto AirportProvider y TRADUCE un formato al otro.

Nadie fuera de este archivo sabe que API Colombia existe. Si mañana cambiamos de
proveedor, solo se escribe otro adapter.

Además aquí aplicamos la resiliencia frente a la API externa:
  timeout -> reintentos con backoff exponencial + jitter -> circuit breaker
"""
import logging

import httpx
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)

from app.application.ports import AirportProvider
from app.domain.exceptions import AirportNotFound, AirportProviderUnavailable
from app.domain.models import Airport
from app.infrastructure.circuit_breaker import CircuitBreaker, CircuitOpenError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DTOs: reflejan EXACTAMENTE el JSON de API Colombia (por eso van en camelCase).
# Pydantic valida la respuesta externa e ignora los campos que no usamos.
# ---------------------------------------------------------------------------
class _NamedRef(BaseModel):
    name: str


class ApiColombiaAirportDTO(BaseModel):
    id: int
    name: str
    iataCode: str | None = None
    oaciCode: str | None = None
    type: str | None = None
    city: _NamedRef | None = None
    department: _NamedRef | None = None
    latitude: float | None = None
    longitude: float | None = None


class _RetryableError(Exception):
    """Error 5xx de la API externa: vale la pena reintentar."""


def _log_retry(retry_state) -> None:
    logger.warning(
        "Reintentando llamada a API Colombia",
        extra={"extra_fields": {"attempt": retry_state.attempt_number}},
    )


# Reintentos: máximo 3 intentos, esperando 0.2s, 0.4s... (exponencial) + jitter
# aleatorio para que muchos clientes no reintenten todos al mismo tiempo.
# Solo se reintenta en errores de red/timeout y 5xx (un 404 NO se reintenta).
_retry_policy = retry(
    retry=retry_if_exception_type((httpx.TransportError, _RetryableError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.2, max=2) + wait_random(0, 0.2),  # backoff + jitter
    before_sleep=_log_retry,
    reraise=True,
)


class ApiColombiaAirportAdapter(AirportProvider):
    def __init__(
        self,
        base_url: str = "https://api-colombia.com",
        circuit_breaker: CircuitBreaker | None = None,
        client: httpx.Client | None = None,
        timeout_seconds: float = 3.0,
    ):
        # Timeout: nunca esperamos indefinidamente a la API externa.
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout_seconds)
        self._breaker = circuit_breaker or CircuitBreaker()

    # ---- Implementación del puerto -------------------------------------
    def get_by_id(self, airport_id: int) -> Airport:
        response = self._call(f"/api/v1/Airport/{airport_id}")
        if response.status_code == 404:
            raise AirportNotFound(airport_id)
        return self._to_domain(ApiColombiaAirportDTO.model_validate(response.json()))

    def list_all(self) -> list[Airport]:
        response = self._call("/api/v1/Airport")
        return [self._to_domain(ApiColombiaAirportDTO.model_validate(item)) for item in response.json()]

    # ---- Traducción formato externo -> modelo de dominio ---------------
    @staticmethod
    def _to_domain(dto: ApiColombiaAirportDTO) -> Airport:
        lat, lon = dto.latitude, dto.longitude
        # API Colombia entrega las coordenadas INVERTIDAS (latitude trae la longitud).
        # En Colombia la latitud está entre -5 y 14 y la longitud entre -82 y -66,
        # así que si "latitud" vale más de 20 en valor absoluto, están al revés.
        if lat is not None and lon is not None and abs(lat) > 20 >= abs(lon):
            lat, lon = lon, lat
        # Algunos aeropuertos (ej. "Aeropuerto del Café") vienen con 0,0 = sin dato.
        if lat == 0 and lon == 0:
            lat = lon = None

        return Airport(
            id=dto.id,
            name=dto.name,
            iata_code=dto.iataCode or "N/A",
            oaci_code=dto.oaciCode or "N/A",
            airport_type=dto.type or "Desconocido",
            city=dto.city.name if dto.city else "",
            department=dto.department.name if dto.department else "",
            latitude=lat,
            longitude=lon,
        )

    # ---- Llamada HTTP con resiliencia ----------------------------------
    def _call(self, path: str) -> httpx.Response:
        try:
            # El circuit breaker envuelve a los reintentos: si después de los
            # 3 intentos sigue fallando, cuenta como UN fallo para el breaker.
            return self._breaker.call(self._get_with_retry, path)
        except CircuitOpenError as exc:
            raise AirportProviderUnavailable(str(exc)) from exc
        except (httpx.HTTPError, _RetryableError) as exc:
            raise AirportProviderUnavailable(f"API Colombia no disponible: {exc}") from exc

    @_retry_policy
    def _get_with_retry(self, path: str) -> httpx.Response:
        response = self._client.get(path)
        if response.status_code >= 500:
            raise _RetryableError(f"API Colombia respondió HTTP {response.status_code}")
        if response.status_code not in (200, 404):
            response.raise_for_status()  # otros 4xx: error inesperado, no se reintenta
        return response

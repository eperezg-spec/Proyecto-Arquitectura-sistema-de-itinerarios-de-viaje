"""
Circuit Breaker (cortacircuitos) escrito a mano para que se entienda cómo funciona.

Estados:
  CLOSED    -> todo normal, las llamadas pasan. Se cuentan los fallos seguidos.
  OPEN      -> hubo demasiados fallos: NO se llama a la API externa, se falla rápido.
  HALF_OPEN -> pasó el tiempo de espera: se deja pasar UNA llamada de prueba.
               Si sale bien -> CLOSED. Si falla -> OPEN otra vez.

      fallos >= umbral             pasa reset_timeout
  CLOSED ---------------> OPEN ----------------------> HALF_OPEN
     ^                                                    |   |
     |_________________ llamada OK _______________________|   | llamada falla -> OPEN
"""
import logging
import threading
import time
from enum import Enum
from typing import Callable, TypeVar

from app.infrastructure.metrics import CIRCUIT_STATE, CIRCUIT_VALUES

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(Exception):
    """Se lanza cuando el circuito está abierto y no se intenta la llamada."""


class CircuitBreaker:
    def __init__(
        self,
        name: str = "api-colombia",
        failure_threshold: int = 5,
        reset_timeout: float = 30.0,
        clock: Callable[[], float] = time.monotonic,  # inyectable para poder probarlo
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._clock = clock
        self._lock = threading.Lock()  # FastAPI atiende peticiones en varios hilos
        self._failures = 0
        self._opened_at = 0.0
        self.state = CircuitState.CLOSED
        CIRCUIT_STATE.labels(name).set(0)  # métrica para Prometheus / alertas

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._clock() - self._opened_at >= self.reset_timeout:
                    self._change_state(CircuitState.HALF_OPEN)
                else:
                    raise CircuitOpenError(f"Circuito '{self.name}' abierto: no se llama a la API externa")

        try:
            result = func(*args, **kwargs)
        except Exception:
            self._record_failure()
            raise
        self._record_success()
        return result

    def _record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self.state == CircuitState.HALF_OPEN or self._failures >= self.failure_threshold:
                self._opened_at = self._clock()
                self._change_state(CircuitState.OPEN)

    def _record_success(self) -> None:
        with self._lock:
            self._failures = 0
            if self.state != CircuitState.CLOSED:
                self._change_state(CircuitState.CLOSED)

    def _change_state(self, new_state: CircuitState) -> None:
        logger.warning(
            "Circuit breaker cambia de estado",
            extra={"extra_fields": {"circuit": self.name, "from": self.state.value, "to": new_state.value}},
        )
        self.state = new_state
        CIRCUIT_STATE.labels(self.name).set(CIRCUIT_VALUES[new_state.value])

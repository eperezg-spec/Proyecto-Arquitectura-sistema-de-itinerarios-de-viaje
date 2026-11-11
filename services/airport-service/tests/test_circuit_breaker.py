import pytest

from app.infrastructure.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


class FakeClock:
    """Reloj manual para no tener que esperar 30 segundos en la prueba."""

    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def failing():
    raise RuntimeError("API caída")


def test_se_abre_despues_de_n_fallos_y_se_recupera():
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=2, reset_timeout=30, clock=clock)

    for _ in range(2):
        with pytest.raises(RuntimeError):
            breaker.call(failing)
    assert breaker.state == CircuitState.OPEN

    # Mientras está abierto falla rápido
    with pytest.raises(CircuitOpenError):
        breaker.call(lambda: "ok")

    # Pasan 30 segundos -> HALF_OPEN -> llamada exitosa -> CLOSED
    clock.now = 31
    assert breaker.call(lambda: "ok") == "ok"
    assert breaker.state == CircuitState.CLOSED


def test_en_half_open_un_fallo_lo_vuelve_a_abrir():
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=1, reset_timeout=10, clock=clock)
    with pytest.raises(RuntimeError):
        breaker.call(failing)

    clock.now = 11
    with pytest.raises(RuntimeError):
        breaker.call(failing)
    assert breaker.state == CircuitState.OPEN

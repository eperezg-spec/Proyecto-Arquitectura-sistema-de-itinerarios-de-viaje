"""
MÉTRICAS Prometheus del Airport Service (se exponen en GET /metrics).

Prometheus las lee cada 15 s y, con las reglas de infra/monitoring/alerts.yml,
dispara ALERTAS (por ejemplo "circuit breaker abierto") hacia Alertmanager.
Grafana las dibuja en el dashboard "Itinerarios".
"""
from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "http_requests_total", "Peticiones HTTP atendidas", ["service", "method", "path", "status"]
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds", "Duración de las peticiones HTTP", ["service", "method", "path"]
)
GRPC_REQUESTS = Counter("grpc_requests_total", "Llamadas gRPC atendidas", ["method", "code"])

# 0 = CLOSED, 1 = HALF_OPEN, 2 = OPEN   (la alerta CircuitBreakerAbierto mira el valor 2)
CIRCUIT_STATE = Gauge("circuit_breaker_state", "Estado del circuit breaker (0 cerrado, 1 semiabierto, 2 abierto)", ["circuit"])
CIRCUIT_VALUES = {"CLOSED": 0, "HALF_OPEN": 1, "OPEN": 2}

# result: hit (copia fresca), miss (se fue a la API), stale (fallback con copia vieja)
CACHE_EVENTS = Counter("airport_cache_events_total", "Uso de la caché Redis", ["result"])

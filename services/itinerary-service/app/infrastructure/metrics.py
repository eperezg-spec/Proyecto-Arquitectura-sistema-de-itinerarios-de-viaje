"""
MÉTRICAS Prometheus del Itinerary Service (GET /metrics) y del outbox relay (puerto 9100).

Las alertas de infra/monitoring/alerts.yml usan, por ejemplo:
  - outbox_pending_messages  -> "OutboxAtascado" si hay eventos sin publicar por mucho tiempo
  - http_requests_total{status=~"5.."} -> "TasaDeErrores5xx"
"""
from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "http_requests_total", "Peticiones HTTP atendidas", ["service", "method", "path", "status"]
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds", "Duración de las peticiones HTTP", ["service", "method", "path"]
)

# Outbox relay
OUTBOX_PENDING = Gauge("outbox_pending_messages", "Eventos en la tabla outbox aún sin publicar")
OUTBOX_PUBLISHED = Counter("outbox_published_total", "Eventos publicados en RabbitMQ", ["event_type"])

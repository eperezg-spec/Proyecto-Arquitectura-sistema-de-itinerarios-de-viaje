"""
Observabilidad: logs JSON con trace_id/span_id + trazas distribuidas (OpenTelemetry -> Jaeger).

Cada línea de log sale así:
  {"timestamp": "...", "level": "INFO", "service": "airport-service",
   "message": "request", "trace_id": "4bf9...", "span_id": "00f0...", ...}

El trace_id es el "correlation ID": es el mismo en todos los servicios que
participan en una petición, así se puede seguir el recorrido completo.
"""
import json
import logging
import os
import sys
import time

from fastapi import FastAPI, Request
from opentelemetry import trace

logger = logging.getLogger("http")


class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        span_context = trace.get_current_span().get_span_context()
        log = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": format(span_context.trace_id, "032x") if span_context.is_valid else None,
            "span_id": format(span_context.span_id, "016x") if span_context.is_valid else None,
        }
        # Campos adicionales: logger.info("msg", extra={"extra_fields": {...}})
        log.update(getattr(record, "extra_fields", {}))
        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)
        return json.dumps(log, ensure_ascii=False, default=str)


def setup_logging(service_name: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service_name))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    # Usamos nuestro propio log de peticiones (con trace_id), no el de uvicorn.
    logging.getLogger("uvicorn.access").disabled = True
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("pika").setLevel(logging.WARNING)


def add_request_logging(app: FastAPI) -> None:
    """Middleware que escribe un log JSON por cada petición HTTP."""

    @app.middleware("http")
    async def log_request(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        logger.info(
            "request",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                    "request_id": request.headers.get("x-request-id"),
                }
            },
        )
        return response


def setup_tracing(app: FastAPI, service_name: str) -> None:
    """Activa OpenTelemetry solo si hay un colector configurado (Jaeger)."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)  # crea un span por cada petición entrante
    HTTPXClientInstrumentor().instrument()  # propaga el contexto (header traceparent) en llamadas salientes

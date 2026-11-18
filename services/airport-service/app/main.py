"""Punto de entrada del Airport Service.

  REST  (puerto 8000): Swagger en http://localhost:8001/docs   -> lo usa el gateway/frontend
  gRPC  (puerto 50051, mTLS): contracts/proto/airport.proto     -> lo usa el itinerary-service
  /metrics: métricas Prometheus
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.dependencies import start_grpc_server
from app.api.errors import register_error_handlers
from app.api.routes import router
from app.infrastructure.observability import add_request_logging, setup_logging, setup_tracing

SERVICE_NAME = "airport-service"
setup_logging(SERVICE_NAME)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Al arrancar: servidor gRPC en un hilo aparte. Al apagar: se detiene con 2 s de gracia.
    grpc_server = start_grpc_server()
    yield
    grpc_server.stop(grace=2)


app = FastAPI(
    title="Airport Service",
    version="1.1.0",
    lifespan=lifespan,
    description=(
        "Microservicio del contexto **Catálogo Aeroportuario**. Consume API Colombia mediante el "
        "patrón Adapter, cachea en Redis y aplica timeout + retry + circuit breaker. "
        "Expone REST (esta documentación) y gRPC con mTLS para el Itinerary Service. "
        "Usa el botón *Authorize* con un token obtenido en `POST /auth/token` del auth-service."
    ),
)
register_error_handlers(app)
add_request_logging(app, SERVICE_NAME)  # antes de setup_tracing para que el log tenga el trace_id
setup_tracing(app, SERVICE_NAME)
app.include_router(router)


@app.get("/health", tags=["Salud"], summary="Healthcheck")
def health():
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Métricas en formato Prometheus (Prometheus las lee cada 15 s)."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

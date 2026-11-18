"""Punto de entrada del Itinerary Service. Swagger: http://localhost:8002/docs  ·  Métricas: /metrics"""
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.errors import register_error_handlers
from app.api.routes import router
from app.infrastructure.observability import add_request_logging, setup_logging, setup_tracing

SERVICE_NAME = "itinerary-service"
setup_logging(SERVICE_NAME)

app = FastAPI(
    title="Itinerary Service",
    version="1.1.0",
    description=(
        "Microservicio del contexto **Planificación de Viajes**. CRUD de itinerarios, validación de "
        "aeropuertos contra el Airport Service (gRPC + mTLS) y publicación de `ItineraryCreatedEvent` con el patrón "
        "Transactional Outbox. Usa *Authorize* con un token de `POST /auth/token`."
    ),
)
register_error_handlers(app)
add_request_logging(app, SERVICE_NAME)
setup_tracing(app, SERVICE_NAME)
app.include_router(router)


@app.get("/health", tags=["Salud"], summary="Healthcheck")
def health():
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Métricas en formato Prometheus (Prometheus las lee cada 15 s)."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

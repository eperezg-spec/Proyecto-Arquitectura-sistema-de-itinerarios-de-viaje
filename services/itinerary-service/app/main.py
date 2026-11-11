"""Punto de entrada del Itinerary Service. Swagger: http://localhost:8002/docs"""
from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.routes import router
from app.infrastructure.observability import add_request_logging, setup_logging, setup_tracing

SERVICE_NAME = "itinerary-service"
setup_logging(SERVICE_NAME)

app = FastAPI(
    title="Itinerary Service",
    version="1.0.0",
    description=(
        "Microservicio del contexto **Planificación de Viajes**. CRUD de itinerarios, validación de "
        "aeropuertos contra el Airport Service y publicación de `ItineraryCreatedEvent` con el patrón "
        "Transactional Outbox. Usa *Authorize* con un token de `POST /auth/token`."
    ),
)
register_error_handlers(app)
add_request_logging(app)
setup_tracing(app, SERVICE_NAME)
app.include_router(router)


@app.get("/health", tags=["Salud"], summary="Healthcheck")
def health():
    return {"status": "ok"}

"""Punto de entrada del Airport Service. Swagger: http://localhost:8001/docs"""
from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.routes import router
from app.infrastructure.observability import add_request_logging, setup_logging, setup_tracing

SERVICE_NAME = "airport-service"
setup_logging(SERVICE_NAME)

app = FastAPI(
    title="Airport Service",
    version="1.0.0",
    description=(
        "Microservicio del contexto **Catálogo Aeroportuario**. Consume API Colombia mediante el "
        "patrón Adapter, cachea en Redis y aplica timeout + retry + circuit breaker. "
        "Usa el botón *Authorize* con un token obtenido en `POST /auth/token` del auth-service."
    ),
)
register_error_handlers(app)
add_request_logging(app)  # antes de setup_tracing para que el log tenga el trace_id
setup_tracing(app, SERVICE_NAME)
app.include_router(router)


@app.get("/health", tags=["Salud"], summary="Healthcheck")
def health():
    return {"status": "ok"}

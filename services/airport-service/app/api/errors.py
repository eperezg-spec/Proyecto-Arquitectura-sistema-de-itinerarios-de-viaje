"""
Manejo centralizado de errores: traduce excepciones del dominio a respuestas HTTP
con un formato consistente {"status", "title", "detail"}.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.exceptions import AirportNotFound, AirportProviderUnavailable

logger = logging.getLogger(__name__)


def problem(status: int, title: str, detail: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"status": status, "title": title, "detail": detail}, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AirportNotFound)
    async def airport_not_found(_: Request, exc: AirportNotFound):
        return problem(404, "Not Found", str(exc))

    @app.exception_handler(AirportProviderUnavailable)
    async def provider_unavailable(_: Request, exc: AirportProviderUnavailable):
        logger.error("Proveedor de aeropuertos no disponible", extra={"extra_fields": {"error": str(exc)}})
        # Retry-After le dice al cliente cuándo volver a intentar.
        return problem(503, "Service Unavailable", str(exc), headers={"Retry-After": "30"})

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        return problem(exc.status_code, "HTTP Error", str(exc.detail), headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        detail = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        return problem(422, "Validation Error", detail)

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, exc: Exception):
        logger.exception("Error inesperado")
        return problem(500, "Internal Server Error", "Ocurrió un error inesperado")

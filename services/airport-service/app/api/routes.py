"""
ADAPTER DE ENTRADA (REST). Solo traduce HTTP <-> casos de uso; no tiene lógica de negocio.
"""
from fastapi import APIRouter, Depends, Path

from app.api.dependencies import get_airport_service
from app.api.schemas import AirportResponse, CacheInvalidationResponse, ErrorResponse, PlotlyMapResponse
from app.api.security import require_user
from app.application.airport_service import AirportService

ERRORS = {
    401: {"model": ErrorResponse, "description": "Token ausente o inválido"},
    503: {"model": ErrorResponse, "description": "API Colombia no disponible y sin copia en caché"},
}

router = APIRouter(prefix="/api/v1/airports", tags=["Aeropuertos"], dependencies=[Depends(require_user)])


@router.get("", response_model=list[AirportResponse], responses=ERRORS, summary="Listar aeropuertos")
def list_airports(service: AirportService = Depends(get_airport_service)):
    return [AirportResponse.from_domain(a) for a in service.list_airports()]


# OJO: /map debe declararse ANTES de /{airport_id} para que no lo capture esa ruta.
@router.get("/map", response_model=PlotlyMapResponse, responses=ERRORS, summary="Mapa Plotly de todos los aeropuertos")
def get_map(service: AirportService = Depends(get_airport_service)):
    return service.get_map()


@router.delete("/cache", response_model=CacheInvalidationResponse, summary="Invalidar la caché Redis")
def invalidate_cache(service: AirportService = Depends(get_airport_service)):
    return CacheInvalidationResponse(deleted_keys=service.invalidate_cache())


@router.get(
    "/{airport_id}",
    response_model=AirportResponse,
    responses={404: {"model": ErrorResponse, "description": "No existe"}, **ERRORS},
    summary="Obtener un aeropuerto por ID",
)
def get_airport(airport_id: int = Path(gt=0), service: AirportService = Depends(get_airport_service)):
    return AirportResponse.from_domain(service.get_airport(airport_id))


@router.get(
    "/{airport_id}/map",
    response_model=PlotlyMapResponse,
    responses={404: {"model": ErrorResponse}, **ERRORS},
    summary="Mapa Plotly de un aeropuerto",
)
def get_airport_map(airport_id: int = Path(gt=0), service: AirportService = Depends(get_airport_service)):
    return service.get_airport_map(airport_id)

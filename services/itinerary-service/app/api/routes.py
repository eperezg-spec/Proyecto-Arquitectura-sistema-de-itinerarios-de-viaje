"""ADAPTER DE ENTRADA (REST): CRUD de itinerarios. Sin lógica de negocio."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_itinerary_service
from app.api.schemas import ErrorResponse, ItineraryRequest, ItineraryResponse
from app.api.security import require_user
from app.application.itinerary_service import ItineraryService

router = APIRouter(prefix="/api/v1/itineraries", tags=["Itinerarios"], dependencies=[Depends(require_user)])

E401 = {401: {"model": ErrorResponse, "description": "Token ausente o inválido"}}
E404 = {404: {"model": ErrorResponse, "description": "El itinerario no existe"}}
E422 = {422: {"model": ErrorResponse, "description": "Datos inválidos o aeropuerto inexistente"}}
E503 = {503: {"model": ErrorResponse, "description": "Airport Service no disponible"}}


@router.post(
    "",
    response_model=ItineraryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={**E401, **E422, **E503},
    summary="Crear itinerario (valida aeropuertos y publica ItineraryCreatedEvent)",
)
def create_itinerary(body: ItineraryRequest, response: Response, service: ItineraryService = Depends(get_itinerary_service)):
    itinerary = service.create(body.to_data())
    response.headers["Location"] = f"/api/v1/itineraries/{itinerary.id}"
    return ItineraryResponse.from_domain(itinerary)


@router.get("", response_model=list[ItineraryResponse], responses=E401, summary="Listar itinerarios (paginado)")
def list_itineraries(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: ItineraryService = Depends(get_itinerary_service),
):
    return [ItineraryResponse.from_domain(i) for i in service.list(limit, offset)]


@router.get("/{itinerary_id}", response_model=ItineraryResponse, responses={**E401, **E404}, summary="Obtener itinerario")
def get_itinerary(itinerary_id: UUID, service: ItineraryService = Depends(get_itinerary_service)):
    return ItineraryResponse.from_domain(service.get(itinerary_id))


@router.put(
    "/{itinerary_id}",
    response_model=ItineraryResponse,
    responses={**E401, **E404, **E422, **E503},
    summary="Actualizar itinerario",
)
def update_itinerary(itinerary_id: UUID, body: ItineraryRequest, service: ItineraryService = Depends(get_itinerary_service)):
    return ItineraryResponse.from_domain(service.update(itinerary_id, body.to_data()))


@router.delete(
    "/{itinerary_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**E401, **E404},
    summary="Eliminar itinerario",
)
def delete_itinerary(itinerary_id: UUID, service: ItineraryService = Depends(get_itinerary_service)):
    service.delete(itinerary_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

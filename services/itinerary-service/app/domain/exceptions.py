"""Errores del dominio. La capa API los convierte en códigos HTTP."""


class InvalidItinerary(Exception):
    """El itinerario rompe una regla de negocio (422)."""


class ItineraryNotFound(Exception):
    """No existe un itinerario con ese id (404)."""


class AirportNotFound(Exception):
    """Uno o varios aeropuertos del itinerario no existen (422)."""

    def __init__(self, airport_ids: list[int]):
        self.airport_ids = airport_ids
        super().__init__(f"Aeropuerto(s) inexistente(s): {airport_ids}")


class AirportServiceUnavailable(Exception):
    """No se pudo consultar al Airport Service (503)."""

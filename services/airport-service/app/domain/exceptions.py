"""Errores del dominio. La capa API los traduce a códigos HTTP (404, 503...)."""


class AirportNotFound(Exception):
    """El aeropuerto solicitado no existe."""

    def __init__(self, airport_id: int):
        self.airport_id = airport_id
        super().__init__(f"El aeropuerto {airport_id} no existe")


class AirportProviderUnavailable(Exception):
    """La fuente de aeropuertos (API externa) no está disponible en este momento."""

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class GetAirportRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class Airport(_message.Message):
    __slots__ = ("id", "name", "iata_code", "city", "department", "has_coordinates", "latitude", "longitude")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    IATA_CODE_FIELD_NUMBER: _ClassVar[int]
    CITY_FIELD_NUMBER: _ClassVar[int]
    DEPARTMENT_FIELD_NUMBER: _ClassVar[int]
    HAS_COORDINATES_FIELD_NUMBER: _ClassVar[int]
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    id: int
    name: str
    iata_code: str
    city: str
    department: str
    has_coordinates: bool
    latitude: float
    longitude: float
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., iata_code: _Optional[str] = ..., city: _Optional[str] = ..., department: _Optional[str] = ..., has_coordinates: _Optional[bool] = ..., latitude: _Optional[float] = ..., longitude: _Optional[float] = ...) -> None: ...

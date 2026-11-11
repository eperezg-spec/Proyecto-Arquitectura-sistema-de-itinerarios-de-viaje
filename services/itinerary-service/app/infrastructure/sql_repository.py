"""
ADAPTER de persistencia: implementa ItineraryRepository con SQLAlchemy.

TRANSACTIONAL OUTBOX (solución al "Double Write Problem"):
  Si hiciéramos  1) INSERT en la BD  y  2) publish en RabbitMQ  por separado,
  podría fallar uno de los dos y quedaríamos inconsistentes (itinerario sin
  evento, o evento de un itinerario que no se guardó).

  Solución: en la MISMA transacción guardamos el itinerario y una fila en la
  tabla outbox_messages. O se guardan los dos, o ninguno. Después, otro proceso
  (outbox_relay.py) lee la tabla y publica en RabbitMQ.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.application.ports import ItineraryRepository
from app.domain.models import Itinerary
from app.infrastructure.integration_events import current_trace_headers, to_integration_event
from app.infrastructure.orm import ItineraryRow, OutboxMessageRow


def _to_row(itinerary: Itinerary) -> ItineraryRow:
    return ItineraryRow(
        id=itinerary.id,
        user_name=itinerary.user_name,
        departure_airport_id=itinerary.departure_airport_id,
        arrival_airport_id=itinerary.arrival_airport_id,
        travel_date=itinerary.travel_date,
        duration_minutes=itinerary.duration_minutes,
        created_at=itinerary.created_at,
        updated_at=itinerary.updated_at,
    )


def _to_domain(row: ItineraryRow) -> Itinerary:
    return Itinerary(
        id=row.id,
        user_name=row.user_name,
        departure_airport_id=row.departure_airport_id,
        arrival_airport_id=row.arrival_airport_id,
        travel_date=row.travel_date,
        duration_minutes=row.duration_minutes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlItineraryRepository(ItineraryRepository):
    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def add(self, itinerary: Itinerary) -> None:
        # session.begin() = UNA transacción. Commit automático al salir del bloque,
        # rollback automático si ocurre una excepción.
        with self._session_factory() as session, session.begin():
            session.add(_to_row(itinerary))
            for event in itinerary.pull_events():
                payload = to_integration_event(event)
                session.add(
                    OutboxMessageRow(
                        id=event.event_id,
                        aggregate_id=itinerary.id,
                        event_type=payload["event_type"],
                        payload=payload,
                        headers=current_trace_headers(),
                        occurred_at=event.occurred_at,
                    )
                )

    def get(self, itinerary_id: UUID) -> Itinerary | None:
        with self._session_factory() as session:
            row = session.get(ItineraryRow, itinerary_id)
            return _to_domain(row) if row else None

    def list(self, limit: int, offset: int) -> list[Itinerary]:
        with self._session_factory() as session:
            query = select(ItineraryRow).order_by(ItineraryRow.created_at.desc()).limit(limit).offset(offset)
            return [_to_domain(row) for row in session.scalars(query)]

    def update(self, itinerary: Itinerary) -> None:
        with self._session_factory() as session, session.begin():
            session.merge(_to_row(itinerary))

    def delete(self, itinerary_id: UUID) -> bool:
        with self._session_factory() as session, session.begin():
            row = session.get(ItineraryRow, itinerary_id)
            if row is None:
                return False
            session.delete(row)
            return True

"""
Tablas (modelos ORM de SQLAlchemy). Son INFRAESTRUCTURA: el dominio no las conoce.
El esquema real se crea con las migraciones de Alembic (carpeta migrations/).
"""
import uuid
from datetime import date, datetime

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ItineraryRow(Base):
    __tablename__ = "itineraries"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="ck_itineraries_duration_positive"),
        CheckConstraint("departure_airport_id <> arrival_airport_id", name="ck_itineraries_distinct_airports"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    user_name: Mapped[str] = mapped_column(String(100))
    departure_airport_id: Mapped[int]
    arrival_airport_id: Mapped[int]
    travel_date: Mapped[date] = mapped_column(Date)
    duration_minutes: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OutboxMessageRow(Base):
    """
    Tabla OUTBOX (buzón de salida). Cada fila es un evento de integración que
    todavía hay que publicar en RabbitMQ. published_at = NULL -> pendiente.
    """

    __tablename__ = "outbox_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # = event_id
    aggregate_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    event_type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSON)
    headers: Mapped[dict] = mapped_column(JSON)  # contexto de traza (traceparent)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

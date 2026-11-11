"""Crea la tabla de notificaciones.

Revision ID: 0001
Revises:
Create Date: 2026-11-11
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # UNIQUE en event_id = idempotencia: el mismo evento no se procesa dos veces
        sa.Column("event_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("itinerary_id", sa.Uuid(), nullable=False),
        sa.Column("recipient", sa.String(100), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("notifications")

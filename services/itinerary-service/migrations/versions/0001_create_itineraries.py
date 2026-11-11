"""Crea la tabla de itinerarios.

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
        "itineraries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_name", sa.String(100), nullable=False),
        sa.Column("departure_airport_id", sa.Integer(), nullable=False),
        sa.Column("arrival_airport_id", sa.Integer(), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("duration_minutes > 0", name="ck_itineraries_duration_positive"),
        sa.CheckConstraint("departure_airport_id <> arrival_airport_id", name="ck_itineraries_distinct_airports"),
    )


def downgrade() -> None:
    op.drop_table("itineraries")

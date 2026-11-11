"""Entorno de Alembic para notification_db."""
import os

from alembic import context
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("NOTIFICATION_DB_URL", "sqlite:///./notifications.db")

engine = create_engine(DATABASE_URL)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()

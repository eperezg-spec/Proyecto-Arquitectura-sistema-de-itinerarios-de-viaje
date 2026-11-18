"""Conexión a la base de datos propia del servicio (itinerary_db)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.vault import get_secret

# Con Vault: secret/itinerario/itinerary-service -> database_url. Sin Vault: variable DATABASE_URL.
DATABASE_URL = get_secret(
    "itinerario/itinerary-service", "database_url", env_var="DATABASE_URL", default="sqlite:///./itinerary.db"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

"""
AUTH SERVICE (servicio de soporte, contexto genérico "Identidad").

Emite tokens JWT para usuarios de demostración. Es deliberadamente mínimo: un
proyecto real usaría Keycloak, Auth0, Cognito... Los demás servicios validan
el token con el mismo secreto (JWT_SECRET) y lo propagan entre ellos.
Swagger: http://localhost:8003/docs
"""
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

JWT_SECRET = os.getenv("JWT_SECRET", "cambia-este-secreto-en-produccion")
JWT_ALGORITHM = "HS256"
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "60"))

# Usuarios de DEMO (en un sistema real estarían en una BD con contraseñas hasheadas)
DEMO_USERS = {"viajero": "viajero123", "admin": "admin123"}

app = FastAPI(title="Auth Service", version="1.0.0", description="Emite JWT de demostración (usuario: viajero / viajero123).")


class TokenRequest(BaseModel):
    username: str = Field(examples=["viajero"])
    password: str = Field(examples=["viajero123"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@app.post("/auth/token", response_model=TokenResponse, tags=["Auth"], summary="Iniciar sesión y obtener un JWT")
def login(body: TokenRequest):
    expected = DEMO_USERS.get(body.username)
    # compare_digest evita ataques de tiempo al comparar contraseñas
    if expected is None or not hmac.compare_digest(expected, body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario o contraseña incorrectos")

    now = datetime.now(timezone.utc)
    claims = {"sub": body.username, "iat": now, "exp": now + timedelta(minutes=TOKEN_MINUTES)}
    token = jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return TokenResponse(access_token=token, expires_in=TOKEN_MINUTES * 60)


@app.get("/health", tags=["Salud"])
def health():
    return {"status": "ok"}

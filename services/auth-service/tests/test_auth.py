import jwt
from fastapi.testclient import TestClient

from app.main import JWT_ALGORITHM, JWT_SECRET, app

client = TestClient(app)


def test_login_correcto_devuelve_jwt_valido():
    response = client.post("/auth/token", json={"username": "viajero", "password": "viajero123"})
    assert response.status_code == 200
    claims = jwt.decode(response.json()["access_token"], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert claims["sub"] == "viajero"


def test_login_incorrecto_devuelve_401():
    response = client.post("/auth/token", json={"username": "viajero", "password": "mal"})
    assert response.status_code == 401

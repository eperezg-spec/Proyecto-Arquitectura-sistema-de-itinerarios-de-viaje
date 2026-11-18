"""
Pruebas del módulo de Vault con un cliente FALSO (no necesitan Vault real):
  - sin VAULT_ADDR se usan variables de entorno y no se emite certificado,
  - con VAULT_ADDR se leen los secretos de KV y el certificado de PKI.
"""
import pytest

from app.infrastructure import vault


class FakeVaultClient:
    """Imita las partes de hvac.Client que usamos."""

    def __init__(self):
        self.secrets = self
        self.kv = self
        self.v2 = self
        self.pki = self

    def read_secret_version(self, path, mount_point, raise_on_deleted_version):
        assert mount_point == "secret"
        return {"data": {"data": {"secret": f"valor-de-{path}"}}}

    def generate_certificate(self, name, common_name, extra_params, mount_point):
        assert (name, mount_point) == ("servicios", "pki")
        return {"data": {"certificate": f"CERT-{common_name}", "private_key": "KEY", "issuing_ca": "CA", "serial_number": "01"}}


@pytest.fixture
def with_vault(monkeypatch):
    monkeypatch.setenv("VAULT_ADDR", "http://vault:8200")
    monkeypatch.setattr(vault, "_client", lambda: FakeVaultClient())


@pytest.fixture
def without_vault(monkeypatch):
    monkeypatch.delenv("VAULT_ADDR", raising=False)


def test_sin_vault_usa_la_variable_de_entorno(without_vault, monkeypatch):
    monkeypatch.setenv("MI_SECRETO", "desde-env")
    assert vault.get_secret("itinerario/jwt", "secret", env_var="MI_SECRETO") == "desde-env"


def test_sin_vault_usa_el_valor_por_defecto(without_vault, monkeypatch):
    monkeypatch.delenv("MI_SECRETO", raising=False)
    assert vault.get_secret("x", "y", env_var="MI_SECRETO", default="por-defecto") == "por-defecto"


def test_sin_vault_y_sin_variable_falla_con_mensaje_claro(without_vault, monkeypatch):
    monkeypatch.delenv("MI_SECRETO", raising=False)
    with pytest.raises(RuntimeError, match="MI_SECRETO"):
        vault.get_secret("x", "y", env_var="MI_SECRETO")


def test_sin_vault_no_se_emite_certificado(without_vault):
    assert vault.issue_certificate("airport-service") is None


def test_con_vault_lee_el_secreto_de_kv(with_vault, monkeypatch):
    monkeypatch.setenv("MI_SECRETO", "NO-debe-usarse")
    assert vault.get_secret("itinerario/jwt", "secret", env_var="MI_SECRETO") == "valor-de-itinerario/jwt"


def test_con_vault_emite_certificado_mtls(with_vault):
    tls = vault.issue_certificate("itinerary-service")
    assert tls.certificate == b"CERT-itinerary-service"
    assert (tls.private_key, tls.ca_certificate) == (b"KEY", b"CA")

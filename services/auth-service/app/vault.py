"""
SECRETOS y CERTIFICADOS desde HashiCorp Vault.

    ┌──────────────┐  token del servicio   ┌────────────────────────────────┐
    │ este servicio│ ────────────────────> │ Vault                          │
    │              │ <──────────────────── │  secret/itinerario/...  (KV)   │
    └──────────────┘  secretos + cert TLS  │  pki/issue/servicios    (CA)   │
                                           └────────────────────────────────┘

- KV (key/value): secretos como JWT_SECRET o la URL de la base de datos. Así no
  quedan escritos en el código ni en el docker-compose.
- PKI: Vault actúa como Autoridad Certificadora interna y emite, al arrancar,
  un certificado de corta duración para este servicio. Ese certificado es el
  que se usa en el mTLS de gRPC.

Si VAULT_ADDR NO está definida (pruebas unitarias, desarrollo local) se usan
variables de entorno y gRPC sin TLS. Así las pruebas no necesitan Vault.
"""
import logging
import os
import time
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TlsMaterial:
    """Certificado + llave privada del servicio y certificado de la CA (todo en PEM)."""

    certificate: bytes
    private_key: bytes
    ca_certificate: bytes


def vault_enabled() -> bool:
    return bool(os.getenv("VAULT_ADDR"))


@lru_cache  # un solo cliente por proceso
def _client():
    import hvac  # import aquí: sin Vault no hace falta la librería

    client = hvac.Client(url=os.environ["VAULT_ADDR"], token=os.environ["VAULT_TOKEN"])
    # Vault puede tardar unos segundos en estar listo: reintentamos.
    for attempt in range(1, 31):
        try:
            if client.is_authenticated():
                logger.info("Conectado a Vault", extra={"extra_fields": {"vault": os.environ["VAULT_ADDR"]}})
                return client
        except Exception as exc:  # noqa: BLE001 - cualquier error de red cuenta como "no listo"
            logger.warning("Vault no disponible", extra={"extra_fields": {"attempt": attempt, "error": str(exc)}})
        time.sleep(2)
    raise RuntimeError("No fue posible autenticarse en Vault")


def get_secret(path: str, key: str, env_var: str, default: str | None = None) -> str:
    """Lee secret/<path> -> <key> de Vault, o la variable de entorno env_var si no hay Vault."""
    if vault_enabled():
        response = _client().secrets.kv.v2.read_secret_version(
            path=path, mount_point="secret", raise_on_deleted_version=True
        )
        logger.info("Secreto leído de Vault", extra={"extra_fields": {"path": path, "key": key}})
        return response["data"]["data"][key]

    value = os.getenv(env_var, default)
    if value is None:
        raise RuntimeError(f"Falta la variable de entorno {env_var}")
    return value


def issue_certificate(common_name: str) -> TlsMaterial | None:
    """Pide a la CA de Vault un certificado para este servicio (None si no hay Vault)."""
    if not vault_enabled():
        return None
    response = _client().secrets.pki.generate_certificate(
        name=os.getenv("VAULT_PKI_ROLE", "servicios"),
        common_name=common_name,
        extra_params={"ttl": os.getenv("CERT_TTL", "72h")},
        mount_point="pki",
    )
    data = response["data"]
    logger.info(
        "Certificado mTLS emitido por Vault",
        extra={"extra_fields": {"common_name": common_name, "serial": data["serial_number"]}},
    )
    return TlsMaterial(
        certificate=data["certificate"].encode(),
        private_key=data["private_key"].encode(),
        ca_certificate=data["issuing_ca"].encode(),
    )

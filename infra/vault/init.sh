#!/bin/sh
# =============================================================================
#  Inicialización de HashiCorp Vault (lo ejecuta el contenedor "vault-init").
#
#  1. PKI  -> Vault se convierte en la Autoridad Certificadora (CA) interna que
#             firma los certificados mTLS de los servicios (gRPC).
#  2. KV   -> guarda los secretos (JWT_SECRET, URLs de BD y RabbitMQ).
#  3. Políticas + tokens -> cada servicio solo puede leer SUS secretos
#             (principio de mínimo privilegio).
#
#  Vault corre en modo "dev" (en memoria, token raíz "root"): suficiente para
#  la demo. En producción: modo servidor con almacenamiento persistente, unseal
#  y autenticación por Kubernetes/AppRole en vez de tokens fijos.
# =============================================================================
set -e
export VAULT_ADDR="${VAULT_ADDR:-http://vault:8200}"
export VAULT_TOKEN="${VAULT_TOKEN:-root}"

echo "== Esperando a Vault"
until vault status >/dev/null 2>&1; do sleep 1; done

# ---------------------------------------------------------------- 1. PKI
echo "== Configurando la CA interna (PKI)"
vault secrets enable pki 2>/dev/null || echo "   pki ya estaba habilitado"
vault secrets tune -max-lease-ttl=87600h pki
# Solo se genera la CA raíz la primera vez: si se regenerara, los certificados
# ya emitidos dejarían de ser válidos y el mTLS entre servicios fallaría.
if vault read -field=certificate pki/cert/ca >/dev/null 2>&1; then
  echo "   la CA raíz ya existía"
else
  vault write -field=certificate pki/root/generate/internal \
    common_name="Itinerario Root CA" ttl=87600h >/dev/null
fi
# Rol "servicios": solo puede emitir certificados para nuestros servicios.
vault write pki/roles/servicios \
  allowed_domains="airport-service,itinerary-service,localhost" \
  allow_bare_domains=true allow_localhost=true \
  server_flag=true client_flag=true \
  max_ttl=72h

# ----------------------------------------------------------------- 2. KV
echo "== Guardando secretos en secret/itinerario/*"
vault kv put secret/itinerario/jwt secret="${JWT_SECRET:-cambia-este-secreto-en-produccion}"
vault kv put secret/itinerario/itinerary-service \
  database_url="postgresql+psycopg://itinerary_user:itinerary_pass@postgres:5432/itinerary_db" \
  rabbitmq_url="amqp://itinerario:itinerario@rabbitmq:5672/%2F"

# ------------------------------------------------- 3. Políticas y tokens
echo "== Creando políticas de mínimo privilegio"
vault policy write auth-service - <<'EOF'
path "secret/data/itinerario/jwt" { capabilities = ["read"] }
EOF

vault policy write airport-service - <<'EOF'
path "secret/data/itinerario/jwt" { capabilities = ["read"] }
path "pki/issue/servicios"        { capabilities = ["create", "update"] }
EOF

vault policy write itinerary-service - <<'EOF'
path "secret/data/itinerario/jwt"               { capabilities = ["read"] }
path "secret/data/itinerario/itinerary-service" { capabilities = ["read"] }
path "pki/issue/servicios"                      { capabilities = ["create", "update"] }
EOF

# Tokens con id fijo para que docker-compose pueda pasarlos a cada servicio.
for service in auth-service airport-service itinerary-service; do
  vault token create -id="${service}-token" -policy="${service}" -orphan -period=24h >/dev/null 2>&1 \
    || echo "   token de ${service} ya existía"
done

echo "== Vault listo"

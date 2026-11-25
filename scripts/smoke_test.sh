#!/usr/bin/env bash
# =============================================================================
#  SMOKE TEST: verificación rápida después de un despliegue.
#  Uso: bash scripts/smoke_test.sh http://localhost:8080
#  Falla (exit != 0) si algo del flujo principal no responde.
# =============================================================================
set -euo pipefail
BASE="${1:-http://localhost:8080}"
PY="${PYTHON:-python3}"   # en Windows: PYTHON=python bash scripts/smoke_test.sh

echo "1) Frontend"
curl -sf "$BASE/" > /dev/null

echo "2) Login"
TOKEN=$(curl -sf -X POST "$BASE/auth/token" -H 'Content-Type: application/json' \
  -d '{"username":"viajero","password":"viajero123"}' | "$PY" -c 'import json,sys;print(json.load(sys.stdin)["access_token"])')
AUTH="Authorization: Bearer $TOKEN"

echo "3) Aeropuertos (Airport Service -> API Colombia / Redis)"
curl -sf "$BASE/api/v1/airports" -H "$AUTH" | "$PY" -c 'import json,sys; n=len(json.load(sys.stdin)); assert n > 0, n; print("   aeropuertos:", n)'

echo "4) Crear itinerario (Itinerary Service -> gRPC mTLS -> Airport Service)"
IDS=$(curl -sf "$BASE/api/v1/airports" -H "$AUTH" | "$PY" -c 'import json,sys; a=json.load(sys.stdin); print(a[0]["id"], a[1]["id"])')
read -r FROM TO <<< "$IDS"
TRAVEL_DATE=$(date -d '+30 days' +%F 2>/dev/null || date -v+30d +%F)
curl -sf -X POST "$BASE/api/v1/itineraries" -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"user_name\":\"Smoke test\",\"departure_airport_id\":$FROM,\"arrival_airport_id\":$TO,\"travel_date\":\"$TRAVEL_DATE\",\"duration_minutes\":60}" > /dev/null

echo "5) Listar itinerarios"
curl -sf "$BASE/api/v1/itineraries" -H "$AUTH" > /dev/null

echo "Smoke test OK"

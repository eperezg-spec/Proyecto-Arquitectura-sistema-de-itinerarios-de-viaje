#!/usr/bin/env bash
# =============================================================================
#  Despliega el sistema en Kubernetes (kind, minikube, k3s o Docker Desktop).
#
#  Requisitos: kubectl apuntando al clúster y las imágenes construidas:
#      docker compose build            (crea itinerario/*:latest)
#      kind load docker-image ...      (solo si usas kind; ver k8s/README.md)
#
#  Uso (desde la raíz del repo):   bash k8s/deploy.sh
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Namespace"
kubectl apply -f k8s/base/namespace.yaml

echo "== ConfigMaps desde los mismos archivos que usa docker-compose (sin duplicarlos)"
kubectl -n itinerario create configmap postgres-init \
  --from-file=init.sql=infra/postgres/init.sql --dry-run=client -o yaml | kubectl apply -f -
kubectl -n itinerario create configmap vault-init-script \
  --from-file=init.sh=infra/vault/init.sh --dry-run=client -o yaml | kubectl apply -f -

echo "== Recursos (kustomize)"
kubectl apply -k k8s/base

echo "== Esperando a que todo esté listo"
kubectl -n itinerario wait --for=condition=complete job/vault-init --timeout=180s
kubectl -n itinerario wait --for=condition=complete job/itinerary-migrations --timeout=300s
kubectl -n itinerario rollout status deployment --timeout=300s

echo "== Listo: http://localhost:30080  (usuario viajero / viajero123)"
kubectl -n itinerario get pods -o wide

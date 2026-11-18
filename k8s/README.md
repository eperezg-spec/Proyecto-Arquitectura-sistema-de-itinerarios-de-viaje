# Kubernetes + Chaos Mesh

Despliegue del sistema en Kubernetes y experimentos de caos (Nivel 3).
Docker Compose sigue siendo la forma principal de ejecutar el proyecto. Kubernetes muestra cómo se llevaría a un clúster: réplicas, autoescalado, sondas de salud y Jobs.

```
k8s/
├── deploy.sh                 # despliega todo (crea ConfigMaps + kubectl apply -k)
├── base/                     # manifiestos (kustomize)
│   ├── namespace.yaml        # namespace "itinerario"
│   ├── config.yaml           # ConfigMap (config no secreta) + Secret (credenciales de infraestructura)
│   ├── postgres.yaml         # StatefulSet + PVC (itinerary_db y notification_db)
│   ├── redis-rabbitmq.yaml   # caché y broker
│   ├── vault.yaml            # Vault + Job vault-init (CA interna, secretos, políticas)
│   ├── auth-gateway.yaml     # auth-service + gateway (NodePort 30080)
│   ├── airport-service.yaml  # 2 réplicas + HPA (2-5) + puertos REST 8000 y gRPC 50051
│   └── itinerary-service.yaml# Job de migraciones + 2 réplicas + HPA + outbox-relay
└── chaos/                    # experimentos de Chaos Mesh
    ├── 01-pod-kill-airport.yaml
    ├── 02-latencia-api-colombia.yaml
    └── 03-particion-rabbitmq.yaml
```

## 1. Crear un clúster local

Sirve cualquiera de estas opciones:

| Opción | Comando |
|---|---|
| Docker Desktop | Settings → Kubernetes → *Enable Kubernetes* |
| kind | `kind create cluster --name itinerario` |
| minikube | `minikube start --cpus 4 --memory 6g` |
| k3s en Docker (la que usamos para probar) | `docker run -d --name itinerario-k3s --privileged -p 16443:6443 -p 30080:30080 rancher/k3s:v1.31.2-k3s1 server --disable traefik` |

## 2. Construir y cargar las imágenes

```bash
docker compose build                       # crea itinerario/*:latest
# kind:
for s in airport-service itinerary-service auth-service gateway; do kind load docker-image itinerario/$s:latest --name itinerario; done
# k3s en Docker:
docker save itinerario/airport-service:latest itinerario/itinerary-service:latest \
  itinerario/auth-service:latest itinerario/gateway:latest | docker exec -i itinerario-k3s ctr -n k8s.io images import -
```

(En Docker Desktop no hace falta cargarlas: el clúster ve las imágenes locales.)

## 3. Desplegar

```bash
bash k8s/deploy.sh
# -> http://localhost:30080   (viajero / viajero123)
kubectl -n itinerario get pods,svc,hpa
```

## 4. Instalar Chaos Mesh

```bash
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace --version 2.7.0 \
  --set chaosDaemon.runtime=containerd \
  --set chaosDaemon.socketPath=/run/containerd/containerd.sock   # en k3s: /run/k3s/containerd/containerd.sock
```

## 5. Experimentos de caos

Cada YAML explica en su encabezado la hipótesis, cómo ejecutarlo y qué observar.

| # | Experimento | Hipótesis | Resultado obtenido (18/11/2026) |
|---|---|---|---|
| 1 | `PodChaos`: matar un pod del Airport Service | Con 2 réplicas el usuario no ve errores | ✅ **47/47 respuestas 200** mientras Kubernetes recreaba el pod. *Antes de corregir la sonda de Vault: 39 respuestas 502* (ver abajo) |
| 2 | `NetworkChaos`: 4 s de latencia hacia api-colombia.com | Timeout → retry → circuit breaker abierto → copia stale de Redis | ✅ El circuito pasó de `CLOSED` a `OPEN` y **todas las respuestas fueron 200** (copia stale). ⚠️ Hasta abrirse, cada petición tardó ~10 s |
| 3 | `NetworkChaos`: partición outbox-relay ↔ RabbitMQ | El outbox no pierde eventos aunque el broker no esté | ✅ Se crearon 5 itinerarios durante la partición (todos 201). Quedaron 5 eventos pendientes y se publicaron al volver la red. **0 eventos perdidos** |

### Lo que descubrimos gracias al caos

1. **La sonda de Vault tenía un timeout demasiado corto.** Era `exec: vault status` con 1 s. Con el nodo cargado fallaba, Vault salía del Service y los pods nuevos del Airport Service no podían pedir su certificado: 502 en el experimento 1. Se cambió por `httpGet /v1/sys/health` con `timeoutSeconds: 3`.
2. **Vault en modo dev guarda todo en memoria.** Si su pod se reinicia, hay que volver a ejecutar el Job `vault-init`. En producción se usaría almacenamiento persistente (Raft) y alta disponibilidad.
3. **El circuit breaker es por réplica y envuelve los 3 reintentos.** Cada réplica necesita 5 peticiones lentas (~10 s cada una) antes de abrirse. Mejora propuesta: bajar el timeout a ~1,5 s, contar cada intento fallido o compartir el estado del circuito en Redis.

## Fuera de Kubernetes

- **Notificaciones serverless (LocalStack):** LocalStack necesita el socket de Docker para crear los contenedores de la Lambda. En un despliegue real se usaría AWS Lambda con un *event source mapping* sobre Amazon MQ, o Knative/OpenFaaS dentro del clúster.
- **Observabilidad (Prometheus/Grafana/Jaeger):** en el clúster se instalaría con `kube-prometheus-stack`. Los pods ya tienen las anotaciones `prometheus.io/scrape`.

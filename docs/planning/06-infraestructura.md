# 06 — Infraestructura compartida

## API Gateway (Traefik v3)

- Único punto de entrada: `http://localhost:8080`.
- Rutas:
  - `/api/v1/airports/*` → airport-service
  - `/api/v1/itineraries/*` → itinerary-service
  - `/api/v1/reports/*` → Lambda de reportes (LocalStack)
  - `/auth/*` → auth-service (público)
  - `/` → frontend
- Middlewares: `rateLimit` (p.ej. average 20 req/s, burst 40 por IP), `forwardAuth` → `auth-service/verify` (valida JWT; devuelve 401), `headers` (CORS), cabecera `X-Request-ID` si no existe.
- Sin lógica de negocio: solo configuración declarativa en `gateway/dynamic/*.yml`.
- Swagger agregado: cada servicio expone `/docs`; se enlazan desde el frontend o se publican rutas `/docs/airport`, `/docs/itinerary`.

## Auth y propagación de JWT

- `auth-service` (FastAPI): `POST /auth/token` (usuarios semilla), `GET /auth/verify`, `GET /.well-known/jwks.json` (si RS256).
- Gateway valida en el borde; **cada servicio también valida** (dependencia FastAPI `get_current_user`) → defensa en profundidad.
- Itinerary → Airport reenvía el mismo `Authorization: Bearer` (propagación S2S).
- N3 opcional: OAuth2 Client Credentials (token propio de servicio con scope `airports:read`).

## Broker — RabbitMQ

- Imagen `rabbitmq:3.13-management` + plugin `rabbitmq_prometheus`.
- Topología en [05](05-notification-serverless.md). Usuarios separados para publisher y consumer.

## Persistencia

- PostgreSQL 16: `airport_db`, `itinerary_db`, `notification_db` (usuario distinto por BD). En compose “prod-like”, contenedores separados.
- Cada servicio ejecuta `alembic upgrade head` en un contenedor *init* (`depends_on: condition: service_completed_successfully`).

## Observabilidad

| Señal | Implementación |
|---|---|
| Logs | `structlog` JSON: `timestamp, level, service, message, trace_id, span_id, correlation_id, path, status`. Middleware que toma/crea `X-Request-ID` |
| Trazas | OTel SDK (auto-instrumentación FastAPI, httpx, SQLAlchemy, redis, aio-pika) → OTel Collector → **Jaeger** (`:16686`). Contexto W3C en HTTP y headers AMQP |
| Métricas | `prometheus-fastapi-instrumentator` + métricas propias (CB, caché, outbox, conector) → **Prometheus** → **Grafana** (dashboards provisionados) |
| Alertas (N3) | `infra/observability/alerts.yml`: `CircuitBreakerOpen` (estado=1 por 1m), `RabbitDeadLetters` (mensajes en DLQ > 0), `OutboxBacklog` (pendientes > 50 por 5m), `HighErrorRate` (5xx > 5 %) |

## docker-compose

Perfiles para controlar consumo de recursos:

| Perfil | Servicios |
|---|---|
| `core` (default) | postgres, redis, rabbitmq, localstack, auth, airport, itinerary, outbox-relay, connector, gateway, frontend, migraciones |
| `observability` | otel-collector, jaeger, prometheus, grafana |
| `quality` | sonarqube + sonar-db |
| `chaos` | toxiproxy (entre airport-service y API Colombia) |

Comandos objetivo (en `Makefile`):

```
make up            # docker compose --profile core up -d --build
make up-all        # core + observability
make test          # unitarias de todos los servicios
make e2e           # suite Testcontainers
make load          # locust headless
make sonar         # análisis SonarQube
make chaos-down-api  # toxiproxy: cortar API Colombia
```

Healthchecks en todos los contenedores; `depends_on` con `condition: service_healthy`.

## Resiliencia demostrable (Nivel 2) y Chaos (Nivel 3)

- Toxiproxy entre airport-service y `api-colombia.com` (el adapter apunta a `toxiproxy:8474` vía `API_COLOMBIA_BASE_URL`).
- Escenarios: `timeout` total (CB se abre → fallback caché → 503), `latency 3000ms` (timeouts + retries), `bandwidth` / caída parcial.
- Evidencia: Grafana (estado CB), Jaeger (spans con retries), logs JSON.

## Opcionales Nivel 3

- **Vault** (modo dev) con secretos de BD y `JWT_SECRET`, leídos al arranque por `pydantic-settings` + `hvac`.
- **Kubernetes** (kind): manifiestos en `infra/k8s` (Deployment, Service, ConfigMap, Secret, probes `/health/live` y `/health/ready`).
- **gRPC** Itinerary↔Airport con `contracts/proto/airport.proto`.

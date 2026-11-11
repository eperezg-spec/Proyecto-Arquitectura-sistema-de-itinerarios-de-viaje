# 09 — Backlog (listo para Jira)

Formato: `ID | Historia | Criterios de aceptación | SP | Nivel`. Los IDs son tentativos; Jira asignará `ITIN-n`.

## EP-01 · Fundaciones y DevOps

| ID | Historia | Criterios de aceptación | SP | Nivel |
|---|---|---|---|---|
| H-01 | Como equipo quiero el repo con estructura de monorepo, `main`/`develop` protegidas, plantilla de PR, CODEOWNERS y commitlint | Ramas protegidas; PR sin CI verde no se puede mergear | 2 | 1 |
| H-02 | Como equipo quiero un proyecto Jira con el backlog cargado y vinculado a GitHub | Issues aparecen en PRs y commits | 1 | DevOps |
| H-03 | Como dev quiero una plantilla hexagonal de servicio (FastAPI, Pydantic, Alembic, structlog, Dockerfile, compose) | `cookiecutter`/carpeta plantilla; servicio vacío levanta con `/health` y `/docs` | 3 | 1 |
| H-04 | Como dev quiero CI (lint, tests, coverage, build) en GitHub Actions | Workflow corre en cada PR | 3 | DevOps |
| H-05 | Como equipo quiero SonarQube con quality gate | Análisis visible y gate bloquea PR | 3 | DevOps |
| H-06 | Como equipo quiero docker-compose raíz con perfiles y Makefile | `make up` levanta todo el core | 3 | 1 |

## EP-02 · Airport Service

| ID | Historia | Criterios de aceptación | SP | Nivel |
|---|---|---|---|---|
| H-10 | Como sistema quiero un puerto `AirportProvider` y un adapter de API Colombia que traduzca al modelo de dominio | Tests del mapeo con JSON real; dominio sin imports externos | 5 | 1 |
| H-11 | Como usuario quiero consultar un aeropuerto por ID | 200 / 404 / 422 con RFC 7807; Swagger documentado | 3 | 1 |
| H-12 | Como frontend quiero aeropuertos en formato Plotly | `/airports/map` devuelve `scattergeo` válido | 3 | 1 |
| H-13 | Como operador quiero logs JSON con trace_id/span_id | Cada request genera log JSON correlacionado | 2 | 1 |
| H-14 | Como sistema quiero migraciones Alembic para `airport_snapshot` | `alembic upgrade head` en contenedor init | 2 | 1 |
| H-15 | Como sistema quiero caché Redis con TTL e invalidación | Segundo GET no llama a la API (métrica hits) ; DELETE invalida | 3 | 2 |
| H-16 | Como sistema quiero retry con backoff exponencial y jitter | Test con `respx` verifica 3 intentos solo en 5xx/timeout | 3 | 2 |
| H-17 | Como sistema quiero circuit breaker con fallback | CB abre tras 5 fallos, sirve caché stale o 503 + `Retry-After` | 5 | 2 |
| H-18 | Como sistema quiero bulkhead para llamadas externas | Semáforo + pools separados, test de saturación | 3 | 3 |

## EP-03 · Itinerary Service

| ID | Historia | Criterios de aceptación | SP | Nivel |
|---|---|---|---|---|
| H-20 | Como viajero quiero crear un itinerario validando aeropuertos | 201; 422 si aeropuerto no existe; 503 si Airport caído | 5 | 1 |
| H-21 | Como viajero quiero listar (paginado), ver, actualizar y eliminar itinerarios | Códigos correctos, 409 por versión | 5 | 1 |
| H-22 | Como sistema quiero persistencia PostgreSQL con Alembic | Migraciones versionadas; constraints de dominio en BD | 3 | 1 |
| H-23 | Como sistema quiero propagar JWT y traceparent al llamar a Airport | Traza única en Jaeger con ambos servicios | 2 | 2 |
| H-24 | Como sistema quiero Transactional Outbox + relay | Rollback ⇒ no hay mensaje; broker caído ⇒ se publica al volver | 8 | 3 |
| H-25 | Como sistema quiero copia local de aeropuertos para validar si Airport falla | Validación funciona con Airport detenido para IDs conocidos | 3 | 3 |

## EP-04 · Eventos y Serverless

| ID | Historia | Criterios de aceptación | SP | Nivel |
|---|---|---|---|---|
| H-30 | Como arquitecto quiero el contrato AsyncAPI del evento `ItineraryCreatedEvent` | YAML válido en CI + HTML generado | 2 | 2 |
| H-31 | Como sistema quiero RabbitMQ con exchange, cola y DLQ declarados | `definitions.json` cargado al arrancar | 2 | 2 |
| H-32 | Como viajero quiero recibir una notificación cuando creo un itinerario | Lambda en LocalStack registra notificación en `notification_db` | 5 | 2 |
| H-33 | Como sistema quiero un conector RabbitMQ→Lambda con ack/nack y DLQ | Mensaje inválido termina en DLQ | 5 | 2 |
| H-34 | Como sistema quiero que el consumidor sea idempotente | Mismo `event_id` dos veces ⇒ una sola notificación | 2 | 3 |
| H-35 | Como analista quiero un reporte bajo demanda de itinerarios | Lambda de reporte accesible por gateway | 3 | opc. |

## EP-05 · Gateway y seguridad

| ID | Historia | Criterios de aceptación | SP | Nivel |
|---|---|---|---|---|
| H-40 | Como sistema quiero un gateway Traefik con ruteo a todos los servicios | Todo se accede por `:8080` | 3 | 2 |
| H-41 | Como sistema quiero rate limiting | Locust evidencia 429 al exceder | 1 | 2 |
| H-42 | Como usuario quiero autenticarme y obtener un JWT | `/auth/token` emite token; endpoints protegidos devuelven 401 sin él | 3 | 2 |
| H-43 | Como sistema quiero validar JWT en gateway y servicios y propagarlo | Llamada directa sin token al servicio ⇒ 401 | 3 | 2 |
| H-44 | (Opc.) OAuth2 Client Credentials S2S / Vault para secretos | Secretos fuera del compose | 5 | 3 |

## EP-06 · Frontend

| ID | Historia | Criterios de aceptación | SP | Nivel |
|---|---|---|---|---|
| H-50 | Como usuario quiero ver los aeropuertos en un mapa Plotly | Al menos 1 aeropuerto visible, datos vía gateway | 3 | 1 |
| H-51 | Como usuario quiero gestionar itinerarios desde la UI | CRUD funcional, errores visibles | 5 | 1 |
| H-52 | Como usuario quiero login y ver la ruta del itinerario en el mapa | Línea origen→destino | 3 | 2 |

## EP-07 · Observabilidad

| ID | Historia | Criterios de aceptación | SP | Nivel |
|---|---|---|---|---|
| H-60 | Como operador quiero trazas distribuidas en Jaeger | Traza frontend→gateway→itinerary→airport (+ relay/conector) | 5 | 2 |
| H-61 | Como operador quiero métricas en Prometheus y dashboard Grafana | Dashboard provisionado con RPS, latencia, CB, caché, outbox | 3 | 2 |
| H-62 | Como operador quiero alertas (CB abierto, DLQ, outbox backlog) | Alerta dispara en demo de chaos | 3 | 3 |

## EP-08 · Calidad y pruebas

| ID | Historia | Criterios de aceptación | SP | Nivel |
|---|---|---|---|---|
| H-70 | Pruebas unitarias ≥ 80 % en dominio/aplicación | Reporte coverage en CI y Sonar | 5 | DevOps |
| H-71 | Suite E2E con Testcontainers | Flujo completo verificado y entorno destruido | 5 | 2 |
| H-72 | Pruebas de carga con Locust | Reporte HTML con p95 y RPS | 3 | DevOps |
| H-73 | Demo de resiliencia con Toxiproxy | Script + evidencia (captura/video) del CB | 3 | 2 |
| H-74 | Contract testing con Pact | Verificación del proveedor en CI | 3 | 3 |
| H-75 | Chaos engineering (latencia, pérdida, CPU) | Escenarios documentados con resultados | 3 | 3 |

## EP-09 · CI/CD y despliegue

| ID | Historia | Criterios de aceptación | SP | Nivel |
|---|---|---|---|---|
| H-80 | Pipeline CD: build, push a GHCR, deploy de ejemplo y smoke test | Tag `v*` dispara despliegue | 5 | 3 / DevOps |
| H-81 | (Opc.) Despliegue en Kubernetes con probes | `kubectl get pods` todos Ready | 8 | 3 |
| H-82 | (Opc.) gRPC Itinerary↔Airport | Mismo puerto, adapter gRPC intercambiable | 5 | 3 |

## EP-10 · Documentación y entrega

| ID | Historia | Criterios de aceptación | SP | Nivel |
|---|---|---|---|---|
| H-90 | README completo con todos los diagramas y secciones exigidas | Checklist de [11-entregables.md](11-entregables.md) al 100 % | 5 | 1 |
| H-91 | Documento de arquitectura corto + ADRs | `docs/architecture.md` y `docs/adr/*` | 3 | DevOps |
| H-92 | Evidencias (capturas/video) y tabla de autoevaluación | Carpeta `docs/evidence/` | 2 | 1 |

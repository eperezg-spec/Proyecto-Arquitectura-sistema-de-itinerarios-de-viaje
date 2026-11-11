# 00 — Visión y alcance

## Objetivo

Construir un sistema de planificación de viajes que:

1. Consulta aeropuertos colombianos desde **API Colombia** (`https://api-colombia.com/api/v1/Airport`).
2. Muestra aeropuertos en un **mapa interactivo Plotly JS**.
3. Permite a un usuario **crear y gestionar itinerarios** (CRUD).
4. **Valida** que los aeropuertos del itinerario existan.
5. **Notifica de forma asíncrona** la creación de itinerarios (event-driven + serverless).
6. Demuestra **concurrencia, resiliencia y observabilidad** de un sistema distribuido.
7. Se desacopla de la API externa con el **patrón Adapter** (Puerto + Adapter).

A esto se suma la rúbrica DevOps: backlog en Jira, Git con ramas estándar y PRs, pruebas unitarias y de carga, Swagger, SonarQube, despliegue continuo de ejemplo, Docker/docker-compose por servicio y documento de arquitectura corto.

## Nivel objetivo

| Nivel | Objetivo | Compromiso |
|---|---|---|
| 1 — Base | **Obligatorio** | 100 % |
| 2 — Avanzado | **Meta del equipo** | 100 % |
| 3 — Experto (bonus) | Selección de ítems de mejor costo/beneficio | Outbox, consistencia distribuida, Bulkhead, Alerting, CI/CD, API versioning + paginación, Contract Testing (Pact). Opcionales si sobra tiempo: gRPC, Toxiproxy, Vault, Kubernetes, OAuth2 Client Credentials |

> Justificación: Outbox es requerido por el propio enunciado del Itinerary Service; CI/CD y SonarQube los exige la rúbrica DevOps; Bulkhead, alerting, versioning y Pact son incrementales sobre lo que ya se construye en Nivel 2.

## Dentro del alcance

- 3 componentes de negocio: Airport Service, Itinerary Service, Notification Functions (Lambda).
- Infraestructura: API Gateway (Traefik), Auth (emisión JWT de demo), RabbitMQ, PostgreSQL, Redis, LocalStack, OpenTelemetry Collector, Jaeger, Prometheus, Grafana, SonarQube.
- Frontend estático (HTML + JS + Plotly) servido por nginx.
- Pruebas: unitarias (pytest), integración, E2E (Testcontainers), carga (Locust), contrato (Pact).

## Fuera del alcance

- Gestión real de usuarios (registro, recuperación de contraseña). Se usa un auth mínimo con usuarios semilla.
- Envío real de correos (se simula y se registra).
- Despliegue en nube real (todo local; K8s solo si sobra tiempo, con kind/minikube).

## Supuestos

- Lenguaje: **Python 3.12** en todos los servicios.
- La API Colombia es pública, sin autenticación, y puede fallar o ser lenta → justifica resiliencia y caché.
- El equipo trabaja con GitHub (repos, PRs, Actions) y Jira (backlog).

## Riesgos principales

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Disparar Lambda en LocalStack desde RabbitMQ (no hay event source mapping nativo gratuito) | Alto | Conector `rabbitmq-lambda-connector` que consume la cola e invoca la Lambda vía `boto3` (patrón “connector” de OpenFaaS). Ver ADR-004 |
| API Colombia caída durante la demo | Medio | Caché Redis precargada + fallback + Toxiproxy para demostrar fallos de forma controlada |
| Consumo de RAM del stack completo (SonarQube + Jaeger + Grafana + LocalStack) | Medio | Perfiles de docker-compose (`core`, `observability`, `quality`) |
| Alcance del Nivel 3 | Medio | Priorizar por la lista de arriba; cada ítem es una historia independiente |

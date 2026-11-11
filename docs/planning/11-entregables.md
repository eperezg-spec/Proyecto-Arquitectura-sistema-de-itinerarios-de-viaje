# 11 — Entregables y autoevaluación

## Checklist del README final

- [ ] Arquitectura utilizada (las 3: microservicios, eventos, serverless)
- [ ] Diagrama de componentes
- [ ] Diagrama de clases (Adapter, puertos, agregados)
- [ ] Diagrama relacional (itinerary_db, notification_db, airport_db)
- [ ] Diagrama de secuencia (frontend → gateway → itinerary → airport)
- [ ] Diagrama de despliegue (docker-compose / Kubernetes)
- [ ] Contextos delimitados y lenguaje ubicuo
- [ ] Decisión sobre el agregado Aeropuerto (referencia de valor)
- [ ] Diferencia entre eventos de dominio e integración
- [ ] Explicación del patrón Adapter implementado
- [ ] Explicación del flujo asíncrono de notificaciones
- [ ] Resolución del Double Write Problem (Outbox)
- [ ] Instrucciones de ejecución (`make up`, URLs, usuarios de prueba)
- [ ] Diagrama simple de arquitectura
- [ ] Tabla de autoevaluación

Diagramas en **Mermaid** dentro del README (renderizan en GitHub) + exportados a `docs/diagrams/*.png`. Se reutilizan los de este plan.

## Evidencias (`docs/evidence/`)

| Evidencia | Formato | Nivel |
|---|---|---|
| Mapa Plotly con aeropuertos | captura | 1 |
| Crear itinerario + notificación en `notification_db` + log de la Lambda | captura / video | 1–2 |
| Swagger de cada servicio | captura | 1 |
| Base de datos funcional (tablas con datos) | captura | 1 |
| Traza distribuida en Jaeger | captura | 2 |
| Circuit breaker abierto con Toxiproxy (Grafana + respuesta fallback) | video corto | 2 |
| Reporte Locust | HTML + captura | DevOps |
| Dashboard SonarQube | captura | DevOps |
| Pipeline GitHub Actions verde (CI y CD) | captura | DevOps / 3 |
| Alertas Prometheus disparadas / resultados chaos | captura | 3 |
| Tablero Jira y PRs | captura | DevOps |

## URLs locales esperadas

| Servicio | URL |
|---|---|
| Frontend (vía gateway) | http://localhost:8080 |
| Airport Swagger | http://localhost:8080/docs/airport (o puerto directo 8001/docs) |
| Itinerary Swagger | http://localhost:8080/docs/itinerary (o 8002/docs) |
| Traefik dashboard | http://localhost:8081 |
| RabbitMQ | http://localhost:15672 |
| Jaeger | http://localhost:16686 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| SonarQube | http://localhost:9000 |

## Plantilla de autoevaluación

| Nivel | Criterio | Estado | Evidencia / justificación |
|---|---|---|---|
| 1 | Patrón Adapter | ⬜ | `services/airport-service/app/infrastructure/adapters/api_colombia.py` |
| 1 | Arquitectura hexagonal | ⬜ | import-linter en CI |
| 1 | DDD básico | ⬜ | README §DDD |
| 1 | CRUD de itinerarios | ⬜ | |
| 1 | BD relacional | ⬜ | |
| 1 | Migraciones | ⬜ | |
| 1 | Swagger | ⬜ | |
| 1 | Manejo de errores | ⬜ | RFC 7807 |
| 1 | Logs estructurados | ⬜ | |
| 1 | Frontend Plotly | ⬜ | |
| 1 | Docker + compose | ⬜ | |
| 1 | README y diagramas | ⬜ | |
| 2 | Circuit Breaker | ⬜ | |
| 2 | Retry con backoff | ⬜ | |
| 2 | Cache Redis | ⬜ | |
| 2 | API Gateway | ⬜ | |
| 2 | Notification (serverless) | ⬜ | |
| 2 | Broker | ⬜ | |
| 2 | AsyncAPI | ⬜ | |
| 2 | Trazas distribuidas | ⬜ | |
| 2 | Propagación JWT | ⬜ | |
| 2 | E2E Testcontainers | ⬜ | |
| 2 | Demo resiliencia | ⬜ | |
| 3 | Transactional Outbox | ⬜ | |
| 3 | Consistencia distribuida | ⬜ | |
| 3 | gRPC | ⬜ | |
| 3 | Seguridad S2S | ⬜ | |
| 3 | Vault / Config | ⬜ | |
| 3 | Chaos Engineering | ⬜ | |
| 3 | Bulkhead | ⬜ | |
| 3 | Alerting | ⬜ | |
| 3 | CI/CD | ⬜ | |
| 3 | Kubernetes | ⬜ | |
| 3 | Contract Testing | ⬜ | |
| 3 | API versioning | ⬜ | |
| DevOps | Jira, ramas, PRs, unitarias, carga, Sonar, CD, compose por servicio | ⬜ | |

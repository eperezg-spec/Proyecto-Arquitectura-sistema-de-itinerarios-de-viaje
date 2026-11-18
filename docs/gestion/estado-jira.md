# Estado del proyecto en Jira

> Generado automáticamente por `python jira/jira_sync.py report --offline` el 2026-11-18. Fuente: jira/backlog.csv (modo offline).

## Resumen por estado

| To Do | In Design | In Review | Approved | Done | Total |
|---|---|---|---|---|---|
| 1 | 1 | 6 | 1 | 32 | 41 |

## Reparto por integrante

| Integrante | Issues | Done | En curso / revisión | Pendientes |
|---|---|---|---|---|
| Compartido | 6 | 2 | 3 | 1 |
| Elizabeth Pérez González | 17 | 15 | 2 | 0 |
| María Fernanda Ceballos | 18 | 15 | 3 | 0 |

## Compartido

| Clave | Entregable | Estado | Prioridad | Sprint | Resuelto |
|---|---|---|---|---|---|
| ITIN-1 | Crear repositorio Git con ramas main/develop/feature y plantilla de PR | Done | Highest | S0 | 2026-11-11 |
| ITIN-20 | Swagger documentado en cada servicio | Done | Medium | S5 | 2026-11-11 |
| ITIN-22 | Revisión del avance en clase | Approved | High | S5 | 2026-11-18 |
| ITIN-35 | Informe de pruebas en la rama pruebas | In Review | Highest | S6 | — |
| ITIN-40 | Roadmap y reparto ajustados a 2 integrantes | In Review | Medium | S6 | — |
| ITIN-41 | Sustentación final y demo | To Do | Highest | S7 | — |

## Elizabeth Pérez González

| Clave | Entregable | Estado | Prioridad | Sprint | Resuelto |
|---|---|---|---|---|---|
| ITIN-4 | docker-compose por servicio y compose raíz con extends | Done | High | S0 | 2026-11-11 |
| ITIN-5 | Adapter de API Colombia con DTO y traducción al modelo de dominio | Done | Highest | S1 | 2026-11-11 |
| ITIN-6 | Corregir coordenadas invertidas y 0,0 de API Colombia en el Adapter | Done | High | S1 | 2026-11-11 |
| ITIN-7 | Mapa Plotly de aeropuertos (endpoint /map) | Done | High | S1 | 2026-11-11 |
| ITIN-8 | Caché Redis con copia fresca y copia stale de respaldo | Done | High | S3 | 2026-11-11 |
| ITIN-9 | Timeout + retry con backoff + circuit breaker hacia API Colombia | Done | High | S3 | 2026-11-11 |
| ITIN-16 | API Gateway nginx con rate limiting y ruteo | Done | High | S3 | 2026-11-11 |
| ITIN-17 | Auth Service con JWT y propagación del token | Done | High | S3 | 2026-11-11 |
| ITIN-18 | Frontend (login + mapa + CRUD + ruta) | Done | Medium | S3 | 2026-11-11 |
| ITIN-23 | Comunicación interna Itinerary -> Airport por gRPC (contrato .proto) | Done | High | S6 | 2026-11-18 |
| ITIN-24 | mTLS en el canal gRPC con autorización por CN del certificado | Done | High | S6 | 2026-11-18 |
| ITIN-25 | HashiCorp Vault: secretos (KV) + CA interna (PKI) + políticas de mínimo privilegio | Done | High | S6 | 2026-11-18 |
| ITIN-26 | Despliegue en Kubernetes (Deployments + HPA + probes + Job de migraciones) | Done | High | S6 | 2026-11-18 |
| ITIN-27 | Experimentos de Chaos Mesh (pod-kill + latencia + partición) | Done | Medium | S6 | 2026-11-18 |
| ITIN-30 | Mejora del circuit breaker detectada en caos (timeout por intento / estado compartido) | In Design | Low | S7 | — |
| ITIN-33 | Automatización web con Selenium (9 casos de prueba) | Done | Highest | S6 | 2026-11-18 |
| ITIN-36 | Documento de arquitectura con diagramas mejorados (formato del ejemplo) | In Review | Highest | S6 | — |

## María Fernanda Ceballos

| Clave | Entregable | Estado | Prioridad | Sprint | Resuelto |
|---|---|---|---|---|---|
| ITIN-2 | Configurar proyecto Jira con flujo To Do / In Design / In Review / Approved / Done | Done | High | S0 | 2026-11-11 |
| ITIN-3 | Pipeline CI en GitHub Actions (pruebas por servicio + build de imágenes) | Done | Highest | S0 | 2026-11-11 |
| ITIN-10 | Agregado Itinerary con reglas de negocio y evento de dominio | Done | Highest | S2 | 2026-11-11 |
| ITIN-11 | CRUD de itinerarios con validación de aeropuertos | Done | Highest | S2 | 2026-11-11 |
| ITIN-12 | Migraciones Alembic (itineraries + outbox) | Done | Medium | S2 | 2026-11-11 |
| ITIN-13 | Transactional Outbox + relay (FOR UPDATE SKIP LOCKED + publisher confirms) | Done | High | S4 | 2026-11-11 |
| ITIN-14 | Topología RabbitMQ (topic exchange + DLX/DLQ) y contrato AsyncAPI | Done | High | S4 | 2026-11-11 |
| ITIN-15 | Lambda SendNotificationFunction idempotente en LocalStack + conector | Done | High | S4 | 2026-11-11 |
| ITIN-19 | Logs JSON con trace_id y trazas distribuidas en Jaeger | Done | Medium | S5 | 2026-11-11 |
| ITIN-21 | SonarQube (perfil quality + job de CI) | Done | Medium | S5 | 2026-11-11 |
| ITIN-28 | Pruebas de contrato Pact del evento ItineraryCreated | Done | High | S6 | 2026-11-18 |
| ITIN-29 | Métricas Prometheus + 6 alertas + Alertmanager + dashboard Grafana | Done | High | S6 | 2026-11-18 |
| ITIN-31 | Pruebas funcionales con Pytest (unitarias + eventos de la arquitectura hexagonal) | Done | Highest | S6 | 2026-11-18 |
| ITIN-32 | Pruebas de eventos con RabbitMQ real (Testcontainers) incluida la DLQ | Done | High | S6 | 2026-11-18 |
| ITIN-34 | Pruebas de carga y estrés con Locust | Done | Highest | S6 | 2026-11-18 |
| ITIN-37 | README detallado: DDD + Adapter + eventos + flujo asíncrono + Double Write | In Review | High | S6 | — |
| ITIN-38 | Ciclo DevOps detallado por fases | In Review | High | S6 | — |
| ITIN-39 | Gestión en Jira vinculada por API (script de sincronización) | In Review | High | S6 | — |

## Épicas

| Clave | Épica | Responsable | Estado |
|---|---|---|---|
| EP-01 | Fundaciones DevOps (repo, Jira, CI) | Compartido | Done |
| EP-02 | Airport Service (Nivel 1-2) | Elizabeth Pérez González | Done |
| EP-03 | Itinerary Service (Nivel 1-2) | María Fernanda Ceballos | Done |
| EP-04 | Eventos y Serverless (Nivel 2) | María Fernanda Ceballos | Done |
| EP-05 | Gateway, seguridad y frontend | Elizabeth Pérez González | Done |
| EP-06 | Observabilidad y calidad | María Fernanda Ceballos | Done |
| EP-07 | Nivel 3 (correcciones del profesor) | Compartido | In Review |
| EP-08 | Pruebas y aseguramiento de calidad (correcciones) | Compartido | In Review |
| EP-09 | Documentación y entrega final | Compartido | In Review |

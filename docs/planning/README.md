# Planning — Sistema de Itinerarios Personales

Índice del plan de implementación. Fuentes: *Arquitecturas para un sistema de itinerarios personales* (enunciado) y *Rúbrica del proyecto* (DevOps).

> **Plan inicial vs. implementación final.** Estos documentos son el plan con el que arrancó el proyecto. Durante la implementación se tomaron decisiones distintas en algunos puntos, todas justificadas en el [documento de arquitectura](../arquitectura/):
>
> | Plan inicial | Implementación final | Motivo |
> |---|---|---|
> | Traefik como gateway | **nginx** (plantilla con DNS de Docker/Kubernetes) | Más simple de explicar; rate limiting nativo |
> | Toxiproxy para simular fallos | **`docker-compose.chaos.yml`** (API caída) + **Chaos Mesh** en Kubernetes | Chaos Mesh cubre más escenarios (pod-kill, latencia, partición) |
> | Validación de aeropuertos por HTTP | **gRPC + mTLS** (el adapter HTTP se conserva como alternativa) | Corrección del profesor: comunicación interna por gRPC |
> | Secretos en variables de entorno | **HashiCorp Vault** (KV + PKI) | Corrección del profesor (nivel 3) |
> | Equipo de 3–4 personas | **2 integrantes** | Ver el reparto en [10-roadmap.md](10-roadmap.md) y [Jira](../gestion/jira.md) |

| # | Documento | Contenido |
|---|-----------|-----------|
| 00 | [Visión y alcance](00-vision-y-alcance.md) | Objetivo, alcance por nivel, nivel objetivo, supuestos |
| 01 | [Arquitectura y decisiones](01-arquitectura.md) | Vista general, stack, ADRs, estructura del monorepo |
| 02 | [DDD: contextos y lenguaje ubicuo](02-ddd.md) | Bounded contexts, glosario, agregados, eventos |
| 03 | [Airport Service](03-airport-service.md) | Adapter, puerto, caché Redis, resiliencia, Plotly |
| 04 | [Itinerary Service](04-itinerary-service.md) | CRUD, validación, Outbox, migraciones |
| 05 | [Notificaciones (Serverless)](05-notification-serverless.md) | Lambdas en LocalStack, conector RabbitMQ, AsyncAPI |
| 06 | [Infraestructura compartida](06-infraestructura.md) | Gateway, JWT, RabbitMQ, observabilidad, docker-compose |
| 07 | [Frontend](07-frontend.md) | Mapa Plotly, gestión de itinerarios |
| 08 | [DevOps](08-devops.md) | Jira, ramas, PRs, pruebas, SonarQube, CI/CD |
| 09 | [Backlog](09-backlog.md) | Épicas e historias listas para Jira |
| 10 | [Roadmap por sprints](10-roadmap.md) | Fases, sprints, hitos, Definition of Done |
| 11 | [Entregables y autoevaluación](11-entregables.md) | Checklist del README final, evidencias, tabla de autoevaluación |

## Resumen en una línea por arquitectura

| Arquitectura | Dónde | Cómo |
|---|---|---|
| Microservicios | Airport Service, Itinerary Service | FastAPI independientes, BD por servicio, HTTP (gRPC en Nivel 3) |
| Basada en eventos | Itinerary → RabbitMQ | Transactional Outbox + relay, contrato AsyncAPI |
| Serverless | Notificaciones / reportes | AWS Lambda en LocalStack disparada por eventos del broker |

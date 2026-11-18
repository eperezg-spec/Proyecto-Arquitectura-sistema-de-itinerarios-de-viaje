# Gestión del proyecto con Jira

**Equipo (2 integrantes):** Elizabeth Pérez González y María Fernanda Ceballos.

El planning vive en dos lugares sincronizados:

```
jira/backlog.csv  ──python jira/jira_sync.py push──>  Jira (tablero del proyecto ITIN)
     (planning en git)                                     │
                                                           │  las integrantes mueven los issues
docs/gestion/estado-jira.md  <──python jira/jira_sync.py report──┘
     (estado real, leído por la API REST de Jira)
```

- **`jira/backlog.csv`**: cada entregable con su responsable, estado, prioridad, sprint y fechas. Queda versionado en git y es revisable en un PR.
- **`jira/jira_sync.py`**: usa la **API REST v3 de Jira**. Crea o actualiza los issues y los asigna. También los mueve al estado correcto y lee el estado real para generar el reporte.
- **`docs/gestion/estado-jira.md`**: el reporte generado, con el resumen por estado y el detalle por integrante.

## 1. Flujo de estados

```mermaid
flowchart LR
    T[To Do] --> D[In Design] --> R[In Review] --> A[Approved] --> F[Done]
    R -- cambios pedidos --> D
```

| Estado | Significado en este proyecto | Quién lo mueve |
|---|---|---|
| **To Do** | Entregable identificado; aún no se empieza | Quien planifica el sprint |
| **In Design** | Se está diseñando o programando (rama `feature/ITIN-n-*` abierta) | La responsable |
| **In Review** | PR abierto, o documento entregado y pendiente de revisión (compañera o profesor) | La responsable |
| **Approved** | La compañera aprobó el PR, o el profesor revisó y aprobó | La revisora |
| **Done** | Mergeado a `develop`/`main` con CI en verde. La fecha de resolución queda registrada | La responsable |

**Configuración en Jira (una sola vez):** *Project settings → Workflows*. Agregar los estados **In Design**, **In Review** y **Approved** entre *To Do* y *Done*, y permitir transiciones desde cualquier estado ("*Allow all statuses to transition to this one*"). El script busca la transición por el nombre del estado destino.

**Prioridades:** Highest (bloquea la entrega), High, Medium, Low.

## 2. División de responsabilidades

Dividimos el trabajo **por contexto delimitado**: cada integrante es dueña de un microservicio completo, con su código, pruebas, documentación y despliegue. Así cada una puede trabajar sin bloquear a la otra, como en un equipo de microservicios real. Lo transversal se reparte según afinidad con cada servicio.

| | **Elizabeth Pérez González** | **María Fernanda Ceballos** |
|---|---|---|
| **Contexto principal** | Catálogo Aeroportuario (**Airport Service**) | Planificación de Viajes (**Itinerary Service**) |
| **Nivel 1-2** | Adapter de API Colombia (corrección de coordenadas), mapa Plotly, caché Redis, timeout/retry/circuit breaker | Agregado Itinerary, CRUD, migraciones, Transactional Outbox, RabbitMQ + AsyncAPI, Lambda en LocalStack + conector |
| **Transversal** | API Gateway, Auth Service (JWT), frontend | Observabilidad (logs JSON, Jaeger), SonarQube, pipeline CI/CD |
| **Nivel 3 (correcciones)** | gRPC, mTLS, Vault, Kubernetes, Chaos Mesh | Pact, Prometheus + alertas + Grafana |
| **Pruebas** | Selenium (automatización web) | Pytest de eventos, Testcontainers (RabbitMQ), Locust |
| **Documentación** | Documento de arquitectura y diagramas | README (DDD, eventos, Outbox), ciclo DevOps, Jira |
| **Compartido** | Repositorio y ramas, Swagger, informe de pruebas, roadmap, sustentación | |

Las cifras exactas (issues por persona y por estado) están en [estado-jira.md](estado-jira.md).

### Entregables y estado actual

| Entregable | Responsable | Estado | Prioridad | Resuelto |
|---|---|---|---|---|
| Sistema base Nivel 1-2 (Airport, Itinerary, eventos, serverless, gateway) | Ambas, según la tabla anterior | Done | Highest | 2026-11-11 |
| Revisión del avance en clase | Compartido | Approved | High | 2026-11-18 |
| gRPC + mTLS + Vault | Elizabeth | Done | High | 2026-11-18 |
| Kubernetes + Chaos Mesh | Elizabeth | Done | High/Medium | 2026-11-18 |
| Pact + Prometheus/alertas/Grafana | María Fernanda | Done | High | 2026-11-18 |
| Pruebas Pytest/eventos/Locust | María Fernanda | Done | Highest | 2026-11-18 |
| Pruebas Selenium | Elizabeth | Done | Highest | 2026-11-18 |
| Informe de pruebas (rama `pruebas`) | Compartido | In Review | Highest | — |
| Documento de arquitectura | Elizabeth | In Review | Highest | — |
| README detallado, ciclo DevOps, Jira | María Fernanda | In Review | High | — |
| Mejora del circuit breaker (hallazgo de caos) | Elizabeth | In Design | Low | — |
| Sustentación final | Compartido | To Do | Highest | — |

> **Sobre las fechas:** "2026-11-11" es la fecha en que el sistema base quedó en el repositorio (primer commit). "2026-11-18" es la de las correcciones. Si en Jira se trabajó con otras fechas, se corrigen en `jira/backlog.csv` y se vuelve a ejecutar `push`.

## 3. Vincular Jira con el código

1. **Ramas con la clave del issue:** `feature/ITIN-23-grpc-airport`. Con la app *GitHub for Jira* (gratuita en Atlassian Marketplace), el issue muestra sus ramas, commits y PRs.
2. **Smart commits** en los mensajes: `ITIN-23 #comment servidor gRPC con mTLS #done`.
3. **El PR** incluye la clave en el título (`ITIN-23: comunicación gRPC Itinerary → Airport`) y usa `.github/pull_request_template.md`.

## 4. Usar el script

```bash
# 1. Token personal: https://id.atlassian.com/manage-profile/security/api-tokens
export JIRA_URL=https://<sitio>.atlassian.net
export JIRA_EMAIL=<correo de quien ejecuta>
export JIRA_API_TOKEN=<token>          # nunca subirlo a git
export JIRA_PROJECT=ITIN
export JIRA_USER_ELIZABETH=<correo de Elizabeth en Jira>
export JIRA_USER_MARIA_FERNANDA=<correo de María Fernanda en Jira>

# 2. Ver qué haría, sin tocar Jira
python jira/jira_sync.py push --dry-run

# 3. Crear o actualizar los issues
#    Se puede repetir sin duplicar: cada issue lleva la etiqueta local-<clave>
python jira/jira_sync.py push

# 4. Generar el reporte con el estado REAL leído desde Jira
python jira/jira_sync.py report
```

| Llamada a la API | Para qué |
|---|---|
| `POST /rest/api/3/issue` | Crear épicas, historias y tareas (con `parent` = épica) |
| `PUT /rest/api/3/issue/{key}` | Actualizar un issue que ya existe |
| `GET /rest/api/3/user/search` | Encontrar el `accountId` de cada integrante para asignarle el issue |
| `GET/POST /rest/api/3/issue/{key}/transitions` | Mover el issue al estado del CSV |
| `POST /rest/api/3/issue/{key}/comment` | Dejar constancia de la fecha de resolución |
| `POST /rest/api/3/search/jql` | Leer el estado real para el reporte |

> Jira registra su propia `resolutiondate` en el momento en que el issue pasa a *Done*. Si el script crea el issue hoy, esa fecha será la de hoy. Por eso la fecha real de resolución queda también en la descripción y en un comentario.

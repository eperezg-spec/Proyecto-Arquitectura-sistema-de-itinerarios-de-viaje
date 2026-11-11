# 08 — Ciclo DevOps

Cubre la rúbrica: Jira, repos Git, PRs, ramas estándar, pruebas (unitarias, carga), Swagger, SonarQube, despliegue continuo de ejemplo, Docker/compose por servicio.

## 1. Planning en Jira

- Proyecto Scrum `ITIN`. Importar [09-backlog.md](09-backlog.md) (épicas → historias → subtareas).
- Sprints de 1 semana (ver [10-roadmap.md](10-roadmap.md)).
- Campos: Story points (Fibonacci), etiqueta de nivel (`nivel-1`, `nivel-2`, `nivel-3`), componente (`airport`, `itinerary`, `notification`, `infra`, `frontend`, `devops`).
- Integración Jira ↔ GitHub: la clave del issue en rama, commits y PR (`ITIN-12`) para trazabilidad automática.
- Flujo del tablero: `To Do → In Progress → In Review → Done`.

## 2. Git: ramas estándar (GitFlow simplificado)

| Rama | Uso |
|---|---|
| `main` | Producción / entrega. Protegida. Solo merge desde `release/*` o `hotfix/*` |
| `develop` | Integración. Protegida. Destino de los PRs de features |
| `feature/ITIN-<n>-<slug>` | Una historia |
| `bugfix/ITIN-<n>-<slug>` | Correcciones sobre develop |
| `release/x.y.z` | Estabilización antes de `main` |
| `hotfix/ITIN-<n>-<slug>` | Correcciones urgentes sobre main |

> Nota: el repo actual está en `master`; se renombra a `main` y se crea `develop` en el Sprint 0.

Commits: **Conventional Commits** (`feat(itinerary): ITIN-14 crear itinerario`), validado con `commitlint` en pre-commit. Versionado semántico con tags `vX.Y.Z`.

## 3. Pull Requests

- Plantilla `.github/pull_request_template.md`: issue Jira, descripción, tipo de cambio, cómo probar, checklist (tests, docs, Swagger, migración).
- Reglas de protección en `develop` y `main`: 1 aprobación mínima, CI verde obligatorio (lint, tests, coverage, Sonar quality gate), sin push directo, rama actualizada.
- `CODEOWNERS` por carpeta de servicio.

## 4. Pruebas

| Tipo | Herramienta | Dónde | Meta |
|---|---|---|---|
| Unitarias | pytest, pytest-asyncio | `services/*/tests/unit` | Cobertura ≥ 80 % en dominio y aplicación |
| Integración | Testcontainers (Postgres, Redis, RabbitMQ) | `services/*/tests/integration` | Repos, caché, outbox |
| E2E | Testcontainers + docker compose | `tests/e2e` | Login → crear itinerario → evento → fila en `notification_db`; luego destruye el entorno |
| Carga | **Locust** | `tests/load/locustfile.py` | Escenarios: lectura mapa (con caché), CRUD itinerarios. Objetivo: p95 < 300 ms a 50 usuarios en GET cacheado; reportar rate limiting (429) |
| Contrato | Pact (pact-python) | `contracts/pacts` | Itinerary (consumidor) ↔ Airport (proveedor) |
| Resiliencia | Toxiproxy + pytest | `tests/e2e/test_resilience.py` | CB abre y fallback funciona |

Reportes de Locust (HTML) y cobertura se guardan como artefactos del pipeline y como evidencia.

## 5. Swagger

FastAPI genera `/docs` y `/openapi.json` en cada servicio. Requisitos: `summary`, `description`, `responses` con modelos de error, ejemplos en schemas, tags, `security` Bearer. CI exporta `openapi.json` y falla si no se puede generar.

## 6. SonarQube

- Contenedor en perfil `quality` (`sonarqube:community`, `:9000`).
- `sonar-project.properties` por servicio (o monorepo con módulos): `sonar.python.coverage.reportPaths=coverage.xml`, `sonar.python.version=3.12`.
- Quality Gate: cobertura nuevo código ≥ 80 %, 0 bugs/vulnerabilidades nuevas, duplicación < 3 %.
- En CI: `SonarSource/sonarqube-scan-action` contra SonarCloud (gratis para repos públicos) o contra instancia local con runner self-hosted. Captura del dashboard como evidencia.
- Complementos: Ruff (lint/format), mypy, Bandit, `pip-audit`, Trivy (imágenes).

## 7. Docker

- Un `Dockerfile` multi-stage por servicio (builder con `uv`/pip → runtime `python:3.12-slim`, usuario no root, `HEALTHCHECK`).
- Un `docker-compose.yml` por servicio (servicio + sus dependencias directas, para desarrollo aislado).
- `docker-compose.yml` raíz con `include:` de todos + infraestructura compartida.

## 8. CI/CD (GitHub Actions)

```
.github/workflows/
├── ci.yml        # en PR y push a develop
├── cd.yml        # en push a main / tag v*
└── e2e.yml       # nightly o manual
```

**ci.yml** (matriz por servicio, con `paths-filter` para solo construir lo cambiado):
1. Checkout → setup Python → instalar deps (caché).
2. Ruff + mypy + import-linter (arquitectura hexagonal).
3. pytest unitarias + integración (Testcontainers) → `coverage.xml`.
4. Pact: publicar/verificar contratos.
5. Validar `asyncapi.yaml` y exportar OpenAPI.
6. SonarQube scan + Quality Gate.
7. `docker build` + Trivy scan.

**cd.yml** (despliegue continuo de ejemplo):
1. Build & push de imágenes a **GHCR** con tags `sha` y `vX.Y.Z`.
2. Deploy de ejemplo: job que levanta `docker compose` en el runner (o en un **kind** cluster si se hace K8s), corre smoke tests (`/health/ready`, crear itinerario) y publica el resultado.
3. Release notes automáticas desde Conventional Commits.

## 9. Documento de arquitectura (corto)

`docs/architecture.md` (2–4 páginas) siguiendo los ejemplos del aula: contexto, drivers/atributos de calidad, vistas (componentes, despliegue, secuencia), decisiones (ADRs), riesgos. Se enlaza desde el README.

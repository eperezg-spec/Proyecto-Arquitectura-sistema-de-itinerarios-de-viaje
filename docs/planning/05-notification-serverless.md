# 05 — Notificaciones y procesamiento (Serverless)

## Componentes

| Componente | Tipo | Disparo | Responsabilidad |
|---|---|---|---|
| `SendNotificationFunction` | AWS Lambda (LocalStack, Python 3.12) | Evento `itinerary.created` | Idempotencia, simular envío de correo (log), guardar historial en `notification_db` |
| `GenerateItineraryReportFunction` (opcional) | AWS Lambda | Bajo demanda (HTTP vía gateway → Lambda Function URL / API Gateway de LocalStack) | Consolidar métricas: itinerarios por ruta, por aeropuerto, duración media |
| `rabbitmq-lambda-connector` | Contenedor ligero Python | Consume cola `notification.itinerary-created` | Invoca la Lambda con el payload; ack solo si la invocación fue exitosa; nack → DLQ tras N reintentos |

> El conector es infraestructura (equivalente al *connector-sdk* de OpenFaaS o al *event source mapping* de AWS). No contiene lógica de negocio. Ver ADR-004.

## Topología RabbitMQ

```
exchange: itinerary.events (topic, durable)
  ├── routing key itinerary.created  → queue notification.itinerary-created (durable, x-dead-letter-exchange=itinerary.dlx)
  ├── routing key itinerary.updated  → (reservado)
  └── routing key itinerary.deleted  → (reservado)
exchange: itinerary.dlx (fanout) → queue itinerary.dead-letter
```

Definido en `infra/rabbitmq/definitions.json` (cargado al iniciar).

## Contrato del evento (AsyncAPI — `contracts/asyncapi.yaml`)

```yaml
asyncapi: 3.0.0
info: { title: Itinerary Events, version: 1.0.0 }
servers:
  local: { host: rabbitmq:5672, protocol: amqp }
channels:
  itineraryCreated:
    address: itinerary.events
    bindings: { amqp: { is: routingKey, exchange: { name: itinerary.events, type: topic } } }
    messages:
      ItineraryCreatedEvent:
        headers: { type: object, properties: { traceparent: {type: string}, correlation_id: {type: string} } }
        payload:
          type: object
          required: [event_id, event_type, event_version, occurred_at, data]
          properties:
            event_id: { type: string, format: uuid }
            event_type: { const: itinerary.created }
            event_version: { const: 1 }
            occurred_at: { type: string, format: date-time }
            data:
              type: object
              properties:
                itinerary_id: { type: string, format: uuid }
                traveler_name: { type: string }
                origin_airport_id: { type: integer }
                destination_airport_id: { type: integer }
                travel_date: { type: string, format: date }
                duration_minutes: { type: integer }
operations:
  publishItineraryCreated: { action: send, channel: { $ref: '#/channels/itineraryCreated' } }
```

Se valida en CI con `@asyncapi/cli validate` y se genera HTML de documentación.

## notification_db

| Tabla | Columnas |
|---|---|
| `notification` | id, event_id (UNIQUE), itinerary_id, recipient, channel (`email-simulado`), status, message, created_at |
| `processed_event` | event_id PK, processed_at — idempotencia |

Migraciones con Alembic en `functions/send-notification/migrations` (ejecutadas por un contenedor `notification-migrations` one-shot antes de desplegar la Lambda).

## Despliegue local

1. LocalStack con `SERVICES=lambda,logs,iam`, `LAMBDA_DOCKER_NETWORK=<red-compose>` para que la Lambda alcance PostgreSQL.
2. Script `infra/localstack/init/ready.d/deploy-functions.sh`: empaqueta zip (código + dependencias, p.ej. `psycopg[binary]`) y ejecuta `awslocal lambda create-function`.
3. Variables de entorno de la Lambda: `DB_URL`, `OTEL_EXPORTER_OTLP_ENDPOINT`.
4. Propagación de trazas: el conector extrae `traceparent` de los headers AMQP y lo pasa en el payload; la Lambda crea span hijo.

## Pruebas

- Unitarias del handler (`handler(event, context)`) con BD fake: crea notificación, idempotente ante evento repetido.
- Integración: LocalStack + RabbitMQ con Testcontainers, publicar mensaje → verificar fila en `notification_db`.
- Mensaje inválido → termina en `itinerary.dead-letter` (para la alerta de N3).

## Tareas

1. Definir AsyncAPI y `definitions.json` de RabbitMQ.
2. Handler `SendNotificationFunction` + idempotencia + migraciones.
3. Script de despliegue en LocalStack.
4. Conector RabbitMQ→Lambda con ack/nack/DLQ y métricas.
5. (Opcional) `GenerateItineraryReportFunction` + ruta en gateway.
6. Trazas y logs JSON en conector y Lambda.

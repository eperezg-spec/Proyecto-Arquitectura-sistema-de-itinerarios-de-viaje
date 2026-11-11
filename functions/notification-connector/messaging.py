"""
Topología de RabbitMQ (documentada en contracts/asyncapi.yaml).

  exchange "itinerary.events" (topic)
      └── routing key "itinerary.created" ──> cola "notifications.itinerary-created"
                                                    │ (si el mensaje falla)
  exchange "itinerary.events.dlx" (fanout) ──> cola "notifications.dead-letter"

Declarar es idempotente: el productor y el consumidor lo hacen al arrancar,
así no importa quién arranca primero y no se pierden mensajes.
"""
EXCHANGE = "itinerary.events"
DEAD_LETTER_EXCHANGE = "itinerary.events.dlx"
QUEUE = "notifications.itinerary-created"
DEAD_LETTER_QUEUE = "notifications.dead-letter"
ROUTING_KEY = "itinerary.created"


def declare_topology(channel) -> None:
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.exchange_declare(exchange=DEAD_LETTER_EXCHANGE, exchange_type="fanout", durable=True)
    channel.queue_declare(queue=DEAD_LETTER_QUEUE, durable=True)
    channel.queue_bind(queue=DEAD_LETTER_QUEUE, exchange=DEAD_LETTER_EXCHANGE)
    channel.queue_declare(queue=QUEUE, durable=True, arguments={"x-dead-letter-exchange": DEAD_LETTER_EXCHANGE})
    channel.queue_bind(queue=QUEUE, exchange=EXCHANGE, routing_key=ROUTING_KEY)

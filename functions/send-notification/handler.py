"""
FUNCIÓN SERVERLESS: SendNotificationFunction (AWS Lambda, desplegada en LocalStack).

No es un servidor encendido todo el tiempo: LocalStack crea un contenedor
efímero y ejecuta handler() SOLO cuando llega un evento ItineraryCreatedEvent.

Qué hace:
  1. Guarda la notificación en SU PROPIA base de datos (notification_db).
  2. Es IDEMPOTENTE: si llega dos veces el mismo event_id (el outbox garantiza
     "al menos una vez"), la segunda vez no hace nada (UNIQUE + ON CONFLICT).
  3. Simula el envío de un correo escribiendo un log.
"""
import json
import os


def build_message(data: dict) -> str:
    return (
        f"Hola {data['user_name']}, tu itinerario del {data['travel_date']} "
        f"(aeropuerto {data['departure_airport_id']} -> {data['arrival_airport_id']}, "
        f"{data['duration_minutes']} min) fue creado correctamente."
    )


def process_event(event: dict, connection) -> dict:
    """Lógica de la función, separada del handler para poder probarla sin BD real."""
    data = event["data"]
    message = build_message(data)

    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO notifications (event_id, itinerary_id, recipient, channel, message, status)
        VALUES (%s::uuid, %s::uuid, %s, 'email-simulado', %s, 'SENT')
        ON CONFLICT (event_id) DO NOTHING
        """,
        (event["event_id"], data["itinerary_id"], data["user_name"], message),
    )
    inserted = cursor.rowcount
    connection.commit()

    if inserted == 0:
        log("Evento duplicado, se ignora", event_id=event["event_id"])
        return {"status": "duplicate", "event_id": event["event_id"]}

    log("EMAIL SIMULADO enviado", to=data["user_name"], body=message, event_id=event["event_id"])
    return {"status": "sent", "event_id": event["event_id"]}


def handler(event, context):
    """Punto de entrada que invoca AWS Lambda."""
    import pg8000.dbapi  # import aquí: las pruebas unitarias no lo necesitan

    connection = pg8000.dbapi.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    try:
        return process_event(event, connection)
    finally:
        connection.close()


def log(message: str, **fields) -> None:
    """Log en JSON (CloudWatch / logs de LocalStack)."""
    print(json.dumps({"level": "INFO", "service": "send-notification-function", "message": message, **fields}, ensure_ascii=False))

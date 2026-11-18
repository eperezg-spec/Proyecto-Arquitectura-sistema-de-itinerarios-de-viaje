"""
Receptor de alertas MUY simple (webhook de Alertmanager).

Simula el canal del equipo (Slack/Teams/correo): imprime cada alerta en una línea
legible. Ver con:  docker compose logs -f alert-receiver
Solo usa la librería estándar de Python.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class AlertHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 - nombre exigido por http.server
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        for alert in body.get("alerts", []):
            icon = "🔥" if alert["status"] == "firing" else "✅"
            labels, annotations = alert["labels"], alert.get("annotations", {})
            print(
                f"{icon} [{alert['status'].upper()}] {labels.get('alertname')} "
                f"({labels.get('severity')}): {annotations.get('summary', '')}",
                flush=True,
            )
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):  # silencia el log por defecto de cada petición
        pass


if __name__ == "__main__":
    print("alert-receiver escuchando en :5001/alertas", flush=True)
    HTTPServer(("0.0.0.0", 5001), AlertHandler).serve_forever()

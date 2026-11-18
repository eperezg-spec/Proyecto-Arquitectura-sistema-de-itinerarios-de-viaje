"""
SINCRONIZACIÓN CON JIRA mediante su API REST (v3).

jira/backlog.csv es la fuente del planning: cada fila es un entregable con
responsable, estado, prioridad y fechas. Este script:

  push    Crea (o actualiza) en Jira las épicas e issues del CSV, asigna a cada
          integrante, pone prioridad, fecha límite, etiquetas y mueve el issue al
          estado indicado (To Do / In Design / In Review / Approved / Done).
  report  Lee el estado REAL desde Jira (búsqueda JQL) y genera
          docs/gestion/estado-jira.md. Con --offline lo genera desde el CSV.

Uso (desde la raíz del repo; solo librería estándar de Python):
    python jira/jira_sync.py push --dry-run       # muestra lo que haría, sin llamar a Jira
    python jira/jira_sync.py push
    python jira/jira_sync.py report
    python jira/jira_sync.py report --offline

Variables de entorno (NUNCA subir el token a git):
    JIRA_URL                   https://<sitio>.atlassian.net
    JIRA_EMAIL                 correo de la cuenta que crea los issues
    JIRA_API_TOKEN             https://id.atlassian.com/manage-profile/security/api-tokens
    JIRA_PROJECT               clave del proyecto (por defecto ITIN)
    JIRA_USER_ELIZABETH        correo de Elizabeth en Jira (para asignar)
    JIRA_USER_MARIA_FERNANDA   correo de María Fernanda en Jira (para asignar)
"""
import argparse
import base64
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "jira" / "backlog.csv"
REPORT = ROOT / "docs" / "gestion" / "estado-jira.md"
STATES = ["To Do", "In Design", "In Review", "Approved", "Done"]
PEOPLE_ENV = {
    "Elizabeth Pérez González": "JIRA_USER_ELIZABETH",
    "María Fernanda Ceballos": "JIRA_USER_MARIA_FERNANDA",
}


# ----------------------------------------------------------------- utilidades
def load_backlog() -> list[dict]:
    with BACKLOG.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def adf(*paragraphs: str) -> dict:
    """Texto -> Atlassian Document Format (formato que exige la API v3 para descripciones)."""
    return {
        "type": "doc",
        "version": 1,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": p}]} for p in paragraphs if p],
    }


class Jira:
    """Cliente mínimo de la API REST de Jira Cloud (autenticación básica correo + token)."""

    def __init__(self, url: str, email: str, token: str, dry_run: bool = False):
        self.url = url.rstrip("/")
        self.dry_run = dry_run
        self._auth = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()
        self._users: dict[str, str | None] = {}

    def call(self, method: str, path: str, body: dict | None = None) -> dict:
        if self.dry_run:  # no se hace NINGUNA llamada de red
            if method != "GET":
                print(f"  [dry-run] {method} {path} {json.dumps(body, ensure_ascii=False)[:150]}")
            return {"key": "DRY-RUN", "transitions": []}
        request = urllib.request.Request(
            f"{self.url}{path}",
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": self._auth, "Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            sys.exit(f"Error {exc.code} en {method} {path}: {exc.read().decode(errors='replace')}")

    def account_id(self, email: str | None) -> str | None:
        if not email or self.dry_run:
            return None
        if email not in self._users:
            found = self.call("GET", f"/rest/api/3/user/search?query={urllib.parse.quote(email)}")
            self._users[email] = found[0]["accountId"] if found else None
        return self._users[email]

    def search(self, jql: str, fields: list[str]) -> list[dict]:
        issues, token = [], None
        while True:
            body = {"jql": jql, "fields": fields, "maxResults": 100}
            if token:
                body["nextPageToken"] = token
            page = self.call("POST", "/rest/api/3/search/jql", body)
            issues += page.get("issues", [])
            token = page.get("nextPageToken")
            if not token:
                return issues

    def find_by_local_key(self, project: str, local_key: str) -> str | None:
        """Cada issue lleva la etiqueta local-<clave> para poder re-ejecutar el script sin duplicar."""
        if self.dry_run:
            return None
        found = self.search(f'project = "{project}" AND labels = "local-{local_key}"', ["summary"])
        return found[0]["key"] if found else None

    def transition_to(self, issue_key: str, state: str) -> None:
        transitions = self.call("GET", f"/rest/api/3/issue/{issue_key}/transitions").get("transitions", [])
        match = next((t for t in transitions if t["to"]["name"].lower() == state.lower()), None)
        if match:
            self.call("POST", f"/rest/api/3/issue/{issue_key}/transitions", {"transition": {"id": match["id"]}})
        elif not self.dry_run:
            print(f"  ! {issue_key}: no hay transición directa a '{state}' (revisa el flujo del proyecto)")


# ----------------------------------------------------------------------- push
def push(dry_run: bool) -> None:
    jira = Jira(
        os.getenv("JIRA_URL", "https://ejemplo.atlassian.net"),
        os.getenv("JIRA_EMAIL", ""),
        os.getenv("JIRA_API_TOKEN", ""),
        dry_run=dry_run,
    )
    if not dry_run and not all(os.getenv(v) for v in ("JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")):
        sys.exit("Faltan JIRA_URL, JIRA_EMAIL o JIRA_API_TOKEN (o usa --dry-run)")
    project = os.getenv("JIRA_PROJECT", "ITIN")
    rows = load_backlog()
    created: dict[str, str] = {}

    # Primero las épicas (los demás issues las referencian como "parent")
    for row in sorted(rows, key=lambda r: r["tipo"] != "Epic"):
        fields = {
            "project": {"key": project},
            "summary": row["resumen"],
            "issuetype": {"name": row["tipo"]},
            "priority": {"name": row["prioridad"]},
            "labels": [f"local-{row['clave']}", f"sprint-{row['sprint']}", *row["etiquetas"].split(";")],
            "description": adf(
                f"Entregable: {row['entregable']}",
                f"Responsable: {row['responsable']}",
                f"Sprint: {row['sprint']}",
                f"Fecha de resolución: {row['fecha_resolucion']}" if row["fecha_resolucion"] else "",
            ),
        }
        if row["fecha_limite"]:
            fields["duedate"] = row["fecha_limite"]
        if row["epica"] in created:
            fields["parent"] = {"key": created[row["epica"]]}
        account = jira.account_id(os.getenv(PEOPLE_ENV.get(row["responsable"], ""), "") or None)
        if account:
            fields["assignee"] = {"accountId": account}

        existing = jira.find_by_local_key(project, row["clave"])
        if existing:
            fields.pop("project")
            fields.pop("issuetype")
            jira.call("PUT", f"/rest/api/3/issue/{existing}", {"fields": fields})
            key = existing
            action = "actualizado"
        else:
            key = jira.call("POST", "/rest/api/3/issue", {"fields": fields})["key"]
            action = "creado"
        created[row["clave"]] = key
        jira.transition_to(key, row["estado"])
        if row["fecha_resolucion"] and action == "creado":
            jira.call(
                "POST", f"/rest/api/3/issue/{key}/comment",
                {"body": adf(f"Resuelto el {row['fecha_resolucion']} por {row['responsable']}.")},
            )
        print(f"{row['clave']:7} -> {key:10} {action:11} [{row['estado']}] {row['resumen'][:60]}")


# --------------------------------------------------------------------- report
def rows_from_jira() -> list[dict]:
    jira = Jira(os.environ["JIRA_URL"], os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"])
    project = os.getenv("JIRA_PROJECT", "ITIN")
    fields = ["summary", "status", "assignee", "priority", "duedate", "resolutiondate", "labels", "issuetype", "parent"]
    rows = []
    for issue in jira.search(f'project = "{project}" ORDER BY key', fields):
        f = issue["fields"]
        local = next((label[6:] for label in f["labels"] if label.startswith("local-")), issue["key"])
        rows.append({
            "clave": f"{issue['key']} ({local})",
            "tipo": f["issuetype"]["name"],
            "resumen": f["summary"],
            "responsable": (f.get("assignee") or {}).get("displayName", "Sin asignar"),
            "estado": f["status"]["name"],
            "prioridad": (f.get("priority") or {}).get("name", ""),
            "sprint": next((label[7:] for label in f["labels"] if label.startswith("sprint-")), ""),
            "fecha_limite": f.get("duedate") or "",
            "fecha_resolucion": (f.get("resolutiondate") or "")[:10],
        })
    return rows


def report(offline: bool) -> None:
    rows = load_backlog() if offline else rows_from_jira()
    source = "jira/backlog.csv (modo offline)" if offline else f"API de Jira ({os.environ['JIRA_URL']})"
    work = [r for r in rows if r["tipo"] != "Epic"]
    by_person = defaultdict(list)
    for row in work:
        by_person[row["responsable"]].append(row)

    lines = [
        "# Estado del proyecto en Jira",
        "",
        f"> Generado automáticamente por `python jira/jira_sync.py report{' --offline' if offline else ''}` "
        f"el {date.today().isoformat()}. Fuente: {source}.",
        "",
        "## Resumen por estado",
        "",
        "| " + " | ".join(STATES) + " | Total |",
        "|" + "---|" * (len(STATES) + 1),
    ]
    counts = Counter(r["estado"] for r in work)
    lines.append("| " + " | ".join(str(counts.get(s, 0)) for s in STATES) + f" | {len(work)} |")
    lines += ["", "## Reparto por integrante", "", "| Integrante | Issues | Done | En curso / revisión | Pendientes |", "|---|---|---|---|---|"]
    for person, items in sorted(by_person.items()):
        c = Counter(i["estado"] for i in items)
        lines.append(
            f"| {person} | {len(items)} | {c['Done']} | {c['In Design'] + c['In Review'] + c['Approved']} | {c['To Do']} |"
        )
    for person, items in sorted(by_person.items()):
        lines += ["", f"## {person}", "", "| Clave | Entregable | Estado | Prioridad | Sprint | Resuelto |", "|---|---|---|---|---|---|"]
        for i in items:
            lines.append(
                f"| {i['clave']} | {i['resumen']} | {i['estado']} | {i['prioridad']} | {i['sprint']} | {i['fecha_resolucion'] or '—'} |"
            )
    epics = [r for r in rows if r["tipo"] == "Epic"]
    if epics:
        lines += ["", "## Épicas", "", "| Clave | Épica | Responsable | Estado |", "|---|---|---|---|"]
        lines += [f"| {e['clave']} | {e['resumen']} | {e['responsable']} | {e['estado']} |" for e in epics]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Reporte escrito en {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    push_cmd = sub.add_parser("push", help="crear/actualizar issues en Jira desde jira/backlog.csv")
    push_cmd.add_argument("--dry-run", action="store_true", help="no llama a Jira, solo muestra lo que haría")
    report_cmd = sub.add_parser("report", help="generar docs/gestion/estado-jira.md")
    report_cmd.add_argument("--offline", action="store_true", help="usar el CSV en vez de la API")
    args = parser.parse_args()
    push(args.dry_run) if args.command == "push" else report(args.offline)

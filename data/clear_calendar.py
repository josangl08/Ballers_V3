#!/usr/bin/env python3
"""
Borra eventos en el calendario de Ballers App.

Por defecto elimina ÚNICAMENTE los eventos que tienen
`extendedProperties.private.session_id` (es decir, las sesiones creadas
/sincronizadas por la aplicación).  Cambia ONLY_SESSIONS a False para
vaciar todo el calendario.

⚠️  ¡Irreversible! Usa primero dry‑run.

Requisitos:
    pip install google-api-python-client    (ya lo tienes en el proyecto)
"""
import os
import datetime as dt
import sys
import pathlib
from googleapiclient.errors import HttpError
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from controllers.google_client import calendar   # tu helper existente
from dotenv import load_dotenv
load_dotenv()   

# ------------------------------------------------------------------------
CAL_ID         = os.getenv("CALENDAR_ID")         # mismo env var que la app
ONLY_SESSIONS  = False     # ← Cambia a False para borrar TODO el calendario
DRY_RUN        = False     # True = solo imprime, False = borra de verdad
UTC       = dt.timezone.utc
NOW_UTC   = dt.datetime.now(UTC).replace(microsecond=0)
TIME_MIN  = (NOW_UTC - dt.timedelta(days=365)).isoformat()
TIME_MAX  = (NOW_UTC + dt.timedelta(days=365)).isoformat()
# ------------------------------------------------------------------------

def wipe_calendar():
    svc = calendar()
    page_token = None
    deleted = 0
    
    while True:
        resp = (
            svc.events()
            .list(
                calendarId=CAL_ID,
                timeMin=TIME_MIN,
                timeMax=TIME_MAX,
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token,
            )
            .execute()
        )
        for ev in resp.get("items", []):
            if ONLY_SESSIONS:
                props = ev.get("extendedProperties", {}).get("private", {})
                if not props.get("session_id"):
                    continue        # salta eventos ajenos a la app
            summary = ev.get("summary", "(sin título)")
            if DRY_RUN:
                print(f"[dry‑run] {summary}  —  {ev['id']}")
            else:
                try:
                    svc.events().delete(calendarId=CAL_ID, eventId=ev["id"]).execute()
                    deleted += 1
                    print(f"🗑  {summary}")
                except HttpError as exc:
                    print(f"❌  No se pudo borrar {summary}: {exc}")

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(
        "\nFin del script.",
        f"{'Se habrían borrado' if DRY_RUN else 'Borrados'} {deleted} eventos."
    )

# ------------------------------------------------------------------------
if __name__ == "__main__":
    banner = (
        "\n======  BORRAR EVENTOS DE GOOGLE CALENDAR  ======\n"
        f"Calendario: {CAL_ID}\n"
        f"ONLY_SESSIONS = {ONLY_SESSIONS}\n"
        f"DRY_RUN       = {DRY_RUN}\n"
        "=================================================\n"
    )
    print(banner)
    if DRY_RUN:
        print("→  DRY_RUN está activado: no se eliminará nada.\n")
    confirm = input("Escribe 'DELETE' (en mayúsculas) para continuar: ")
    if confirm == "DELETE":
        wipe_calendar()
    else:
        print("Operación cancelada.")
        sys.exit(0)

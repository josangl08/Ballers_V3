import streamlit as st
import datetime as dt
import os
import re 
import logging
from googleapiclient.errors import HttpError
from sqlalchemy import select
from .google_client import calendar
from googleapiclient.errors import HttpError
from models import Session, SessionStatus, Coach, Player, User        
from controllers.db import get_db_session
from unidecode import unidecode
from config import CALENDAR_COLORS
COLOR = {k: v["google"] for k, v in CALENDAR_COLORS.items()} 
CAL_ID = os.getenv("CALENDAR_ID")

logger = logging.getLogger(__name__)

def _db():
    return get_db_session()

def _service():
    return calendar()

def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
    
d_safe_int = lambda x: int(x) if x and str(x).isdigit() else None

def _normalize(text: str) -> str:
    """Pasa a minúsculas, quita tildes y unifica espacios."""
    return re.sub(r"\s+", " ", unidecode(text or "").strip().lower())

def _extract_id(text: str, pattern: str):
    """Busca con regex y devuelve el grupo 1 como int, o None."""
    m = re.search(pattern, text, flags=re.I)
    return _safe_int(m.group(1)) if m else None

def _find_unique(model, name_norm: str):
    """
    Trae todos los registros del modelo (Coach o Player),
    normaliza user.name y devuelve el único que coincide con name_norm.
    Si hay 0 o >1, devuelve None.
    """
    db = get_db_session()
    rows = (
        db.query(model)
          .join(User)
          .filter(User.is_active)
          .all()
    )
    matches = [r for r in rows if _normalize(r.user.name) == name_norm]
    return matches[0] if len(matches) == 1 else None

# —————————————————————————————————————————————————————————————————————
# Función mixta para sacar coach_id y player_id de un evento de Google
# —————————————————————————————————————————————————————————————————————
def _guess_ids(ev):
    """
    1) private props
    2) #C / #P o Coach# / Player#
    3) nombres “Coach × Player” (sin prefijo “Session:” ni “Sesión:”)
    """
    props = ev.get("extendedProperties", {}).get("private", {})
    # 1) extendedProperties
    cid = _safe_int(props.get("coach_id"))
    pid = _safe_int(props.get("player_id"))
    if cid and pid:
        return cid, pid

    # Extrae el summary para los siguientes pasos
    summary = ev.get("summary", "") or ""

    # 2) IDs en texto (case-insensitive)
    cid = (_extract_id(summary, r"#C(\d+)") or
        _extract_id(summary, r"Coach[#\s]*(\d+)"))
    pid = (_extract_id(summary, r"#P(\d+)") or
        _extract_id(summary, r"Player[#\s]*(\d+)"))
    if cid and pid:
        return cid, pid

    # 3) quitamos prefijo “Session:” / “Sesión:” (si existe)
    summary_clean = re.sub(r'^(?:sesión|session)[:\-]\s*', '', summary, flags=re.IGNORECASE)

    # 4) nombres separados por × o x
    m = re.search(r"(.+?)\s*[×x]\s*(.+)", summary_clean)
    if not m:
        return None, None

    coach_name_raw  = m.group(1)
    player_name_raw = m.group(2)
    coach_name_norm  = _normalize(coach_name_raw)
    player_name_norm = _normalize(player_name_raw)

    coach  = _find_unique(Coach,  coach_name_norm)
    player = _find_unique(Player, player_name_norm)

    if coach and player:
        return coach.coach_id, player.player_id

    # Si alguno es None o hay duplicados, ignoramos e informamos
    
    logging.getLogger(__name__).warning(
        "No unique match for event summary '%s': coach=%s player=%s",
        summary, coach_name_raw, player_name_raw
    )
    return None, None

# ---------- DB → Calendar ----------
def push_session(session: Session):
    body = _build_body(session)
    ev = _service().events().insert(calendarId=CAL_ID, body=body).execute()
    session.calendar_event_id = ev["id"]
    _db().commit()

# --------------------------------------------------------------------------
#  ACTUALIZAR una sesión existente
def update_session(session: Session):
    """
    Sincroniza todos los cambios de una sesión existente con Google Calendar:
      • Nuevos summary, dates, notas, color…
      • Si el evento no existe (404), lo recrea.
    """
    db = get_db_session()
    # Si no teníamos event_id, lo empujamos como nuevo
    if not session.calendar_event_id:
        return push_session(session)

    # Construye el body con resumen, fechas, notas y color
    body = _build_body(session)
    try:
        _service().events().patch(
            calendarId=CAL_ID,
            eventId=session.calendar_event_id,
            body=body
        ).execute()
    except HttpError as e:
        if e.resp.status == 404:
            # Evento borrado manualmente en GCal → lo recreamos
            push_session(session)
        else:
            raise
    else:
        # Asegúrate de persistir en BD cualquier cambio de event_id nuevo
        db.commit()

# --------------------------------------------------------------------------
#  BORRAR una sesión
def delete_session(session: Session):
    """
    Borra el evento de Calendar si existe y devuelve True/False
    según se haya eliminado o no.
    """
    if not session.calendar_event_id:
        return False
    try:
        _service().events().delete(
            calendarId=CAL_ID,
            eventId=session.calendar_event_id
        ).execute()
        return True
    except HttpError as e:                 # ya no existe → ignoramos
        if e.resp.status != 404:
            raise
        return False

# --------------------------------------------------------------------------
#  UTILIDAD compartida
def _build_body(session: Session) -> dict:
    """Devuelve el diccionario body que Calendar API espera."""
    return {
        "summary": (
            f"Session: {session.coach.user.name} × {session.player.user.name} "
            f"#C{session.coach_id} #P{session.player_id}"
        ),
        "description": session.notes or "",
        "start": {"dateTime": session.start_time.astimezone(dt.timezone.utc).isoformat()},
        "end":   {"dateTime": session.end_time.astimezone(dt.timezone.utc).isoformat()},
        "colorId": COLOR[session.status.value],
        "extendedProperties": {
            "private": {
                "session_id": str(session.id),
                "coach_id":   str(session.coach_id),
                "player_id":  str(session.player_id),
            }
        },
    }

def patch_color(event_id: str, status: SessionStatus):
    _service().events().patch(
        calendarId=CAL_ID, eventId=event_id,
        body={"colorId": COLOR[status.value]}
    ).execute()

def patch_event_after_import(session: Session, event_id: str):
    """
    Parcha un evento importado: añade IDs y formatea el título.
    """
    db = get_db_session()

    coach_name = db.query(User.name).join(Coach).filter(Coach.coach_id == session.coach_id).scalar()
    player_name = db.query(User.name).join(Player).filter(Player.player_id == session.player_id).scalar()

    patch_body = {
        "summary": f"Sesión: {coach_name} × {player_name}  #C{session.coach_id} #P{session.player_id}",
        "extendedProperties": {
            "private": {
                "session_id": str(session.id),
                "coach_id": str(session.coach_id),
                "player_id": str(session.player_id),
            }
        }
    }

    _service().events().patch(
        calendarId=CAL_ID,
        eventId=event_id,
        body=patch_body
    ).execute()

# ---------- DB → Calendar ----------   
def sync_db_to_calendar():
    """
    Recorre todas las sesiones en BD y:
      - push_session() si no tienen calendar_event_id
      - update_session() si ya lo tienen
    Devuelve (pushed, updated).
    """
    db = get_db_session()
    pushed = updated = 0

    for ses in db.query(Session).all():
        if not ses.calendar_event_id:
            push_session(ses)
            pushed += 1
        else:
            update_session(ses)
            updated += 1

    return pushed, updated

# ---------- Calendar → DB ----------
@st.cache_data(ttl=int(os.getenv("SYNC_INTERVAL_MIN", "5")) * 60, show_spinner=False)
def sync_calendar_to_db():
    svc = _service()
    db  = get_db_session()

    imported = updated = deleted = 0
    seen_ev_ids: set[str] = set()

    now = dt.datetime.now(dt.timezone.utc)
    win_start = now - dt.timedelta(days=1)
    win_end   = now + dt.timedelta(days=90)

    events = svc.events().list(
        calendarId=CAL_ID,
        timeMin=win_start.isoformat(),
        timeMax=win_end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute().get("items", [])

    def _to_dt(iso: str) -> dt.datetime:
        return dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))

    # 1) Cargar todas las sesiones con calendar_event_id ya guardado
    db_sessions = {
        s.calendar_event_id: s
        for s in db.query(Session)
                    .filter(Session.calendar_event_id != None)
                    .all()
    }

    for ev in events:
        ev_id    = ev["id"]
        seen_ev_ids.add(ev_id)

        props    = ev.get("extendedProperties", {}).get("private", {})
        sess_id  = props.get("session_id")
        start_dt = _to_dt(ev["start"]["dateTime"])
        end_dt   = _to_dt(ev["end"]["dateTime"])
        status   = _status_from_color(ev.get("colorId", "9"))

        # —————————————————————————————————————————————————————————
        #  A) Buscar si ya existe en BD
        # —————————————————————————————————————————————————————————
        ses = None
        if sess_id and sess_id.isdigit():
            ses = db.get(Session, int(sess_id))
        if not ses:
            with db.no_autoflush:
                ses = db_sessions.get(ev_id) or db.query(Session).filter_by(calendar_event_id=ev_id).first()

        if ses:
            # Actualizar si cambia algo
            changed = False
            if ses.status != status:
                ses.status = status
                changed = True

            db_start = ses.start_time.astimezone(dt.timezone.utc).replace(microsecond=0)
            new_start = start_dt.astimezone(dt.timezone.utc).replace(microsecond=0)
            if db_start != new_start:
                ses.start_time = start_dt
                changed = True

            db_end = ses.end_time.astimezone(dt.timezone.utc).replace(microsecond=0)
            new_end = end_dt.astimezone(dt.timezone.utc).replace(microsecond=0)
            if db_end != new_end:
                ses.end_time = end_dt
                changed = True

            if changed:
                db.add(ses)
                updated += 1
            continue  # evitamos crear duplicados

        # —————————————————————————————————————————————————————————
        #  B) Evento nuevo: importar
        # —————————————————————————————————————————————————————————
        coach_id, player_id = _guess_ids(ev)
        if coach_id is None or player_id is None:
            continue  # no podemos mapearlo

        ses = Session(
            coach_id=coach_id,
            player_id=player_id,
            start_time=start_dt,
            end_time=end_dt,
            status=status,
            notes=ev.get("description"),
            calendar_event_id=ev_id,
        )
        db.add(ses)
        db.flush()   # Para obtener ses.id antes de patch

        # Parchar el evento para añadir IDs + formatear título
        patch_event_after_import(ses, ev_id)

        imported += 1

    # —————————————————————————————————————————————————————————
    #  C) Eliminar sesiones cuyo evento ya no existe en GCal
    # —————————————————————————————————————————————————————————
    for ev_id, ses in db_sessions.items():
        if ev_id not in seen_ev_ids:
            db.delete(ses)
            deleted += 1

    db.commit()
    return imported, updated, deleted


def _status_from_color(color: str) -> SessionStatus:
    """
    Dado un colorId de Google Calendar, devuelve el estado correspondiente.
    • Reds → CANCELED
    • Greens → COMPLETED
    • El resto → SCHEDULED
    """
    cid = str(color)

    # 1) Todos los rojos → canceled
    red_ids = {"11", "6", "5"}  # ajusta aquí si usas varios tonos de rojo
    if cid in red_ids:
        return SessionStatus.CANCELED

    # 2) Todos los verdes → completed
    green_ids = {"2", "10", "12", "13"}  # tonos de verde en tu paleta
    if cid in green_ids:
        return SessionStatus.COMPLETED

    # 3) El resto → scheduled
    return SessionStatus.SCHEDULED

def update_past_sessions():
    db = get_db_session()
    now = dt.datetime.now(dt.timezone.utc)
    todo = db.query(Session).filter(
        Session.status == SessionStatus.SCHEDULED,
        Session.end_time <= now
    ).all()
    for s in todo:
        s.status = SessionStatus.COMPLETED
        if s.calendar_event_id:
            patch_color(s.calendar_event_id, s.status)
    if todo:
        db.commit()
    return len(todo)

def get_sessions(
    start: dt,
    end: dt,
    coach_id: int | None = None,
    player_id: int | None = None,
    statuses: list[SessionStatus] | None = None,
):
    # Devuelve las sesiones filtradas y ordenadas por fecha de inicio.

    db = get_db_session()
    q = db.query(Session).filter(Session.start_time >= start,
                                 Session.start_time <= end)
    if coach_id:
        q = q.filter(Session.coach_id == coach_id)
    if player_id:
        q = q.filter(Session.player_id == player_id)
    if statuses:
        q = q.filter(Session.status.in_(statuses))
    return q.order_by(Session.start_time.asc()).all()

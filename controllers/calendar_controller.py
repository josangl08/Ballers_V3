import datetime as dt
import os, streamlit as st
from .google_client import calendar
from models import Session, SessionStatus         
from controllers.db import get_db_session
import re 
from config import CALENDAR_COLORS
COLOR = {k: v["google"] for k, v in CALENDAR_COLORS.items()} 

CAL_ID = os.getenv("CALENDAR_ID")


def _db():
    return get_db_session()

def _service():
    return calendar()

def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

# ---------- DB → Calendar ----------
def push_session(session: Session):
    body = {
    "summary": (
        f"Sesión: {session.coach.user.name} × {session.player.user.name} "
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
    ev = _service().events().insert(calendarId=CAL_ID, body=body).execute()
    session.calendar_event_id = ev["id"]
    _db().commit()

def patch_color(event_id: str, status: SessionStatus):
    _service().events().patch(
        calendarId=CAL_ID, eventId=event_id,
        body={"colorId": COLOR[status.value]}
    ).execute()

# ---------- DB → Calendar ----------   
def push_all_sessions_to_calendar(progress_cb=None) -> int:
    db = get_db_session()
    todo = db.query(Session).filter(Session.calendar_event_id == None).all()
    total = len(todo)
    for i, ses in enumerate(todo, 1):
        push_session(ses)
        if progress_cb:
            progress_cb(i / total)
    db.commit()
    return total

# ---------- Calendar → DB ----------
@st.cache_data(ttl=int(os.getenv("SYNC_INTERVAL_MIN", "5")) * 60, show_spinner=False)
def sync_calendar_to_db():
    """
    Sincroniza Google Calendar → base de datos.

    • Actualiza las sesiones existentes cuando cambian en Calendar  
    • Importa eventos nuevos (si puede mapear coach & player)  
    • Crea/actualiza extendedProperties con coach_id y player_id
    """
    svc = _service()
    db  = get_db_session()

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

    def _to_dt(iso):
        return dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))

    for ev in events:
        props   = ev.get("extendedProperties", {}).get("private", {})
        sess_id = props.get("session_id")
        start_dt = _to_dt(ev["start"]["dateTime"])
        end_dt   = _to_dt(ev["end"]["dateTime"])
        status   = _status_from_color(ev.get("colorId", "9"))

        # ── Caso A: el evento ya pertenece a una sesión de BBDD ──────────
        if sess_id and sess_id.isdigit():
            ses = db.query(Session).filter_by(id=int(sess_id)).first()
        else:
            ses = None
            if ses:
                changed = False
                if ses.status != status:
                    ses.status = status
                    changed = True
                if ses.start_time != start_dt or ses.end_time != end_dt:
                    ses.start_time, ses.end_time = start_dt, end_dt
                    changed = True
                if changed:
                    db.add(ses)

                # Garantiza que el evento tenga los IDs grabados
                if not props.get("coach_id") or not props.get("player_id"):
                    svc.events().patch(
                        calendarId=CAL_ID,
                        eventId=ev["id"],
                        body={
                            "extendedProperties": {
                                "private": {
                                    **props,
                                    "coach_id": str(ses.coach_id),
                                    "player_id": str(ses.player_id),
                                }
                            }
                        },
                    ).execute()
            continue   # pasa al siguiente evento

        # ── Caso B: evento nuevo en Google Calendar ──────────────────────
        coach_id, player_id = _guess_ids(ev)
        if coach_id is None or player_id is None:
            continue   # no se puede mapear → se ignora

        ses = Session(
            coach_id=coach_id,
            player_id=player_id,
            start_time=start_dt,
            end_time=end_dt,
            status=status,
            notes=ev.get("description"),
            calendar_event_id=ev["id"],
        )
        db.add(ses)

        # Añade session_id al evento para futuras actualizaciones
        svc.events().patch(
            calendarId=CAL_ID,
            eventId=ev["id"],
            body={
                "extendedProperties": {
                    "private": {
                        "session_id": str(ses.id),
                        "coach_id":   str(coach_id),
                        "player_id":  str(player_id),
                    }
                }
            },
        ).execute()

    db.commit()


def _status_from_color(color):
    return {v: SessionStatus(k) for k, v in COLOR.items()}.get(color, SessionStatus.SCHEDULED)

# Devuelve (coach_id, player_id) o (None, None)
def _guess_ids(ev):
   
    props = ev.get("extendedProperties", {}).get("private", {})
    cid = _safe_int(props.get("coach_id"))
    pid = _safe_int(props.get("player_id"))
    if cid and pid:
        return cid, pid

    # Eventos creados a mano en Google: intenta descubrir IDs en el summary
    summary = ev.get("summary", "")
    coach_id = _extract_id(summary, r"Coach[#\s]*(\d+)")
    player_id = _extract_id(summary, r"Player[#\s]*(\d+)")
    return coach_id, player_id


def _extract_id(text, pattern):
    m = re.search(pattern, text, re.IGNORECASE)
    return int(m.group(1)) if m else None


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

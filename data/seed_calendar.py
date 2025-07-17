# data/seed_calendar.py

import random
import sys
import time
from datetime import datetime
from datetime import time as dt_time
from datetime import timedelta
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from controllers.db import get_db_session
from models.coach_model import Coach
from models.player_model import Player
from models.session_model import Session, SessionStatus


# --------------------------- #
# Función interna específica para SEED
def create_event_return_id(session):
    """Crea evento en Google Calendar y devuelve solo el event_id (sin hacer commit en base de datos)."""
    from controllers.calendar_sync_core import CAL_ID
    from controllers.calendar_utils import build_calendar_event_body
    from controllers.google_client import calendar

    body = build_calendar_event_body(session)
    ev = calendar().events().insert(calendarId=CAL_ID, body=body).execute()
    return ev["id"]


# --------------------------- #

# Configuración de rangos
COMPLETED_RANGE = (2, 3)
SCHEDULED_RANGE = (2, 3)
CANCELED_RANGE = (0, 2)

START_HOURS = list(range(8, 19))  # 8:00 a 18:00
DAYS_OF_WEEK = [0, 1, 2, 3, 4, 5]  # Lunes a sábado

now = datetime.now()
two_months_ago = now - timedelta(days=30)
next_month = now + timedelta(days=30)

NOTES_OPTIONS = [
    "Entrenamiento de resistencia",
    "Sesión técnica de control y pase",
    "Trabajo táctico de líneas",
    "Entrenamiento de velocidad",
    "Sesión de recuperación",
    "Tiro a portería",
    "Sesión psicológica",
    "Trabajo de fuerza específica",
    "Estrategias a balón parado",
    "Test de agilidad",
]

TAGS = ["Técnico", "Físico", "Táctico", "Psicológico"]


def random_datetime_within(start_date, end_date):
    while True:
        random_days = random.randint(0, (end_date - start_date).days)
        random_date = start_date + timedelta(days=random_days)
        if random_date.weekday() in DAYS_OF_WEEK:
            start_hour = random.choice(START_HOURS)
            start = datetime.combine(random_date.date(), dt_time(start_hour, 0))
            end = start + timedelta(hours=1)
            return start, end


def random_note():
    return random.choice(NOTES_OPTIONS)


def random_tag():
    return f"[{random.choice(TAGS)}] "


def create_sessions(player, coaches, coach_index):
    sessions = []
    coach_count = len(coaches)

    n_completed = random.randint(*COMPLETED_RANGE)
    n_scheduled = random.randint(*SCHEDULED_RANGE)
    n_canceled = random.randint(*CANCELED_RANGE)

    player_sessions_by_day = set()
    coach_sessions_by_hour = dict()

    total_sessions = n_completed + n_scheduled + n_canceled
    session_types = (
        [SessionStatus.COMPLETED] * n_completed
        + [SessionStatus.SCHEDULED] * n_scheduled
        + [SessionStatus.CANCELED] * n_canceled
    )
    random.shuffle(session_types)

    for status in session_types:
        for _ in range(100):
            if status == SessionStatus.SCHEDULED:
                start, end = random_datetime_within(now, next_month)
            else:
                start, end = random_datetime_within(two_months_ago, now)

            day = start.date()
            coach = coaches[coach_index % coach_count]
            coach_key = (coach.coach_id, start)

            if (day in player_sessions_by_day) or (coach_key in coach_sessions_by_hour):
                continue
            else:
                session = Session(
                    player_id=player.player_id,
                    coach_id=coach.coach_id,
                    start_time=start,
                    end_time=end,
                    status=status,
                    notes=random_tag() + random_note(),
                )
                sessions.append(session)
                player_sessions_by_day.add(day)
                coach_sessions_by_hour[coach_key] = True
                coach_index += 1
                break
        else:
            print(
                f"⚠️ No se pudo asignar sesión {status} para el jugador {player.player_id} tras 100 intentos."
            )

    return sessions, coach_index


def seed_all_sessions():
    db = get_db_session()
    players = db.query(Player).all()
    coaches = db.query(Coach).all()

    if not players or not coaches:
        raise ValueError("No hay jugadores o entrenadores en la base de datos.")

    all_sessions = []
    coach_index = 0

    for player in players:
        player_sessions, coach_index = create_sessions(player, coaches, coach_index)
        all_sessions.extend(player_sessions)

    print(
        f"✅ {len(all_sessions)} sesiones generadas localmente. Guardando en la base de datos..."
    )

    # Guardar las sesiones en la base de datos
    db.bulk_save_objects(all_sessions)
    db.commit()

    print(f"🔄 Ahora sincronizando con Google Calendar...")

    sessions_in_db = db.query(Session).filter(Session.calendar_event_id == None).all()

    synced_count = 0
    for idx, session in enumerate(sessions_in_db, 1):
        try:
            print(
                f"➡️ [{idx}/{len(sessions_in_db)}] Creando evento para sesión ID {session.id}..."
            )
            event_id = create_event_return_id(
                session
            )  # 🚀 Usamos nuestra función interna
            session.calendar_event_id = event_id
            db.add(session)  # Marcar la sesión modificada
            synced_count += 1
            time.sleep(0.2)  # Pequeño delay para proteger la API
        except Exception as e:
            print(f"⚠️ Error al sincronizar sesión ID {session.id}: {e}")

    db.commit()
    db.close()

    print(
        f"""\n✅ Base de datos rellenada y sincronizada.
    Sesiones creadas: {len(all_sessions)}
    Sesiones sincronizadas con Google Calendar: {synced_count}
    """
    )


if __name__ == "__main__":
    seed_all_sessions()

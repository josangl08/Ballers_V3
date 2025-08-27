# data/seed_sessions_simple.py
# Versión simplificada que usa SQL directo para evitar conflictos con enum

import os
import random
import sys
from datetime import datetime, timedelta, timezone

from faker import Faker
from sqlalchemy import text

from controllers.db import get_db_session, initialize_database

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ENVIRONMENT
from models import Coach, Player, Session, SessionStatus

# Configuración
SESSIONS_PER_PLAYER = (10, 15)
CANCELED_SESSIONS_TOTAL = (10, 15)
MAX_CANCELED_PER_PLAYER = 2
WORK_START_HOUR = 8
WORK_END_HOUR = 18

fake = Faker()
db_session = None


def generate_session_time(is_past=True):
    """Genera fechas/horas para sesiones"""
    now = datetime.now(timezone.utc)

    if is_past:
        start_date = now - timedelta(days=30)
        end_date = now
    else:
        start_date = now
        end_date = now + timedelta(days=30)

    random_date = fake.date_time_between(
        start_date=start_date, end_date=end_date, tzinfo=timezone.utc
    )

    work_hour = random.randint(WORK_START_HOUR, WORK_END_HOUR - 1)
    work_minute = random.choice([0, 15, 30, 45])

    session_start = random_date.replace(
        hour=work_hour, minute=work_minute, second=0, microsecond=0
    )

    session_end = session_start + timedelta(hours=1)
    return session_start, session_end


def generate_notes(status):
    """Generar notas según el estado"""
    if status == "completed":
        templates = [
            "Sesión completada. Excelente progreso en {}.",
            "Entrenamiento finalizado. Se trabajó {}.",
            "Sesión exitosa. El jugador mostró mejoras en {}.",
        ]
        skills = ["control de balón", "finalización", "pase", "regate"]
        return random.choice(templates).format(random.choice(skills))
    elif status == "scheduled":
        templates = [
            "Sesión programada. Enfoque en {}.",
            "Entrenamiento planificado. Trabajar {}.",
        ]
        areas = ["técnica individual", "condición física", "trabajo táctico"]
        return random.choice(templates).format(random.choice(areas))
    else:  # canceled
        return random.choice(
            [
                "Cancelado por lesión del jugador.",
                "Cancelado por enfermedad.",
                "Cancelado por condiciones climáticas.",
            ]
        )


def create_sessions_orm():
    """Crear sesiones usando ORM para valores enum correctos"""

    # Obtener jugadores y coaches
    players = db_session.query(Player).all()
    coaches = db_session.query(Coach).all()

    if not players or not coaches:
        print("❌ No se encontraron jugadores o entrenadores")
        return []

    print(
        f"📊 Generando sesiones para {len(players)} jugadores con {len(coaches)} entrenadores"
    )

    all_sessions = []

    # Crear sesiones para cada jugador
    for player in players:
        num_sessions = random.randint(*SESSIONS_PER_PLAYER)
        completed_count = num_sessions // 2
        scheduled_count = num_sessions - completed_count

        # Sesiones completadas
        for _ in range(completed_count):
            coach = random.choice(coaches)
            start_time, end_time = generate_session_time(is_past=True)

            session = Session(
                coach_id=coach.coach_id,
                player_id=player.player_id,
                coach_name_snapshot=coach.user.name,
                player_name_snapshot=player.user.name,
                start_time=start_time,
                end_time=end_time,
                status=SessionStatus.COMPLETED.value,  # Usar .value para forzar lowercase
                notes=generate_notes("completed"),
                source="app",
                version=1,
                is_dirty=False,
            )

            db_session.add(session)
            all_sessions.append(session)

        # Sesiones programadas
        for _ in range(scheduled_count):
            coach = random.choice(coaches)
            start_time, end_time = generate_session_time(is_past=False)

            session = Session(
                coach_id=coach.coach_id,
                player_id=player.player_id,
                coach_name_snapshot=coach.user.name,
                player_name_snapshot=player.user.name,
                start_time=start_time,
                end_time=end_time,
                status=SessionStatus.SCHEDULED.value,  # Usar .value para forzar lowercase
                notes=generate_notes("scheduled"),
                source="app",
                version=1,
                is_dirty=False,
            )

            db_session.add(session)
            all_sessions.append(session)

        print(
            f"  👤 {player.user.name}: {num_sessions} sesiones ({completed_count} completadas, {scheduled_count} programadas)"
        )

    # Commit todas las sesiones
    db_session.commit()
    print(f"✅ Insertadas {len(all_sessions)} sesiones")

    # Añadir sesiones canceladas
    add_canceled_sessions_orm(all_sessions)

    return all_sessions


def add_canceled_sessions_orm(all_sessions):
    """Convertir sesiones aleatorias a canceladas usando ORM"""

    total_to_cancel = random.randint(*CANCELED_SESSIONS_TOTAL)
    print(f"🚫 Añadiendo {total_to_cancel} sesiones canceladas...")

    # Filtrar solo sesiones no canceladas
    available_sessions = [
        s for s in all_sessions if s.status != SessionStatus.CANCELED.value
    ]

    if not available_sessions:
        print("⚠️ No hay sesiones disponibles para cancelar")
        return

    # Mezclar sesiones aleatoriamente
    random.shuffle(available_sessions)

    # Rastrear cancelaciones por jugador
    canceled_per_player = {}
    canceled_count = 0

    for session in available_sessions:
        if canceled_count >= total_to_cancel:
            break

        player_id = session.player_id

        # Verificar límite por jugador
        if canceled_per_player.get(player_id, 0) < MAX_CANCELED_PER_PLAYER:
            # Cambiar estado a cancelado usando enum
            session.status = (
                SessionStatus.CANCELED.value
            )  # Usar .value para forzar lowercase
            session.notes = generate_notes("canceled")

            canceled_per_player[player_id] = canceled_per_player.get(player_id, 0) + 1
            canceled_count += 1

            print(
                f"  ❌ Cancelada: {session.player_name_snapshot} - {session.start_time.strftime('%Y-%m-%d %H:%M')}"
            )

    # Commit cambios
    db_session.commit()
    print(f"✅ Total canceladas: {canceled_count}")


def clear_existing_sessions():
    """Limpiar sesiones existentes"""
    print("🧹 Limpiando sesiones existentes...")

    try:
        result = db_session.execute(text("DELETE FROM sessions"))
        deleted_count = result.rowcount
        db_session.commit()
        print(f"✅ {deleted_count} sesiones eliminadas")
    except Exception as e:
        print(f"⚠️ Error limpiando sesiones: {e}")
        db_session.rollback()


def show_statistics():
    """Mostrar estadísticas de sesiones creadas"""
    print("\n📈 Estadísticas finales:")

    stats_query = """
    SELECT
        status,
        COUNT(*) as count
    FROM sessions
    GROUP BY status
    ORDER BY status
    """

    result = db_session.execute(text(stats_query))
    stats = result.fetchall()

    total = sum(stat.count for stat in stats)
    print(f"  📊 Total de sesiones: {total}")

    for stat in stats:
        emoji = (
            "✅"
            if stat.status == "completed"
            else "📅" if stat.status == "scheduled" else "❌"
        )
        print(f"  {emoji} {stat.status.capitalize()}: {stat.count}")

    # Estadísticas por jugador
    player_stats_query = """
    SELECT
        p.user_id,
        u.name as player_name,
        COUNT(s.id) as total_sessions
    FROM players p
    JOIN users u ON p.user_id = u.user_id
    LEFT JOIN sessions s ON p.player_id = s.player_id
    GROUP BY p.user_id, u.name
    ORDER BY total_sessions DESC
    """

    result = db_session.execute(text(player_stats_query))
    player_stats = result.fetchall()

    print("\n👥 Sesiones por jugador:")
    for stat in player_stats:
        print(f"  👤 {stat.player_name}: {stat.total_sessions} sesiones")


def main():
    global db_session

    print("🏗️ Iniciando generación de sesiones (versión ORM con enum correctos)...")

    initialize_database()

    with get_db_session() as session:
        db_session = session

        clear_existing_sessions()
        sessions = create_sessions_orm()

        if sessions:
            show_statistics()
            print(f"\n🎯 Entorno: {ENVIRONMENT}")
            print("🏗️ ¡Generación de sesiones completada!")
        else:
            print("❌ No se pudieron generar sesiones")


if __name__ == "__main__":
    main()

# data/seed_sessions.py

import hashlib
import os
import random
import sys
from datetime import datetime, timedelta, timezone

from faker import Faker
from controllers.db import get_db_session, initialize_database

# Asegurar importación de modelos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ENVIRONMENT
from models import Coach, Player, Session, SessionStatus

# Configuración del generador de sesiones
SESSIONS_PER_PLAYER = (10, 15)  # Rango de sesiones por jugador
CANCELED_SESSIONS_TOTAL = (10, 15)  # Total de sesiones canceladas
MAX_CANCELED_PER_PLAYER = 2  # Máximo canceladas por jugador
SESSION_DURATION_HOURS = 1  # Duración estándar de sesión

# Horarios laborales
WORK_START_HOUR = 8  # 8:00 AM
WORK_END_HOUR = 18   # 6:00 PM

# Inicializar Faker para datos realistas
fake = Faker()
db_session = None


def generate_session_time(is_past=True):
    """
    Genera fechas/horas para sesiones dentro del horario laboral
    
    Args:
        is_past: True para sesiones pasadas, False para futuras
    """
    now = datetime.now(timezone.utc)
    
    if is_past:
        # Sesiones pasadas: hasta 30 días atrás
        start_date = now - timedelta(days=30)
        end_date = now
    else:
        # Sesiones futuras: hasta 30 días adelante
        start_date = now
        end_date = now + timedelta(days=30)
    
    # Generar fecha aleatoria en el rango
    random_date = fake.date_time_between(
        start_date=start_date, 
        end_date=end_date,
        tzinfo=timezone.utc
    )
    
    # Ajustar a horario laboral (8:00-18:00)
    work_hour = random.randint(WORK_START_HOUR, WORK_END_HOUR - 1)
    work_minute = random.choice([0, 15, 30, 45])  # Intervalos de 15 minutos
    
    session_start = random_date.replace(
        hour=work_hour, 
        minute=work_minute, 
        second=0, 
        microsecond=0
    )
    
    session_end = session_start + timedelta(hours=SESSION_DURATION_HOURS)
    
    return session_start, session_end


def generate_session_notes(status):
    """Generar notas realistas según el estado de la sesión"""
    if status == "completed":
        templates = [
            "Sesión completada. Excelente progreso en {}.",
            "Entrenamiento finalizado. Se trabajó {}.",
            "Sesión exitosa. El jugador mostró mejoras en {}.",
            "Entrenamiento completado. Se enfocó en {}."
        ]
        skills = [
            "control de balón", "finalización", "pase", "regate", 
            "resistencia física", "táctica defensiva", "visión de juego"
        ]
        return random.choice(templates).format(random.choice(skills))
        
    elif status == "scheduled":
        templates = [
            "Sesión programada. Enfoque en {}.",
            "Entrenamiento planificado. Trabajar {}.",
            "Próxima sesión: desarrollo de {}.",
            "Sesión programada para mejorar {}."
        ]
        areas = [
            "técnica individual", "condición física", "trabajo táctico", 
            "finalización", "pase largo", "juego aéreo"
        ]
        return random.choice(templates).format(random.choice(areas))
        
    else:  # CANCELED
        reasons = [
            "Cancelado por lesión del jugador.",
            "Cancelado por enfermedad.",
            "Cancelado por condiciones climáticas.",
            "Cancelado por compromiso familiar del jugador.",
            "Cancelado por disponibilidad del entrenador.",
            "Cancelado y reprogramado para otra fecha."
        ]
        return random.choice(reasons)


def create_sessions():
    """Crear sesiones para todos los jugadores"""
    
    # Obtener todos los jugadores y coaches
    players = db_session.query(Player).all()
    coaches = db_session.query(Coach).all()
    
    if not players:
        print("❌ No se encontraron jugadores en la base de datos")
        return []
        
    if not coaches:
        print("❌ No se encontraron entrenadores en la base de datos")
        return []
    
    print(f"📊 Generando sesiones para {len(players)} jugadores con {len(coaches)} entrenadores")
    
    all_sessions = []
    sessions_by_player = {}
    
    # Crear sesiones para cada jugador
    for player in players:
        # Número aleatorio de sesiones por jugador (10-15)
        num_sessions = random.randint(*SESSIONS_PER_PLAYER)
        player_sessions = []
        
        # Dividir sesiones: 50% completadas, 50% programadas
        completed_count = num_sessions // 2
        scheduled_count = num_sessions - completed_count
        
        # Crear sesiones completadas (fechas pasadas)
        for _ in range(completed_count):
            coach = random.choice(coaches)
            start_time, end_time = generate_session_time(is_past=True)
            
            # Crear sesión manualmente sin usar relaciones
            session = Session(
                coach_id=coach.coach_id,
                player_id=player.player_id,
                coach_name_snapshot=coach.user.name,
                player_name_snapshot=player.user.name,
                start_time=start_time,
                end_time=end_time,
                status=SessionStatus.COMPLETED,
                notes=generate_session_notes("completed"),
                source="app",
                version=1,
                is_dirty=False
            )
            # Forzar el valor string directamente para evitar problemas de enum
            session.status = "completed"
            
            db_session.add(session)
            player_sessions.append(session)
            all_sessions.append(session)
        
        # Crear sesiones programadas (fechas futuras)
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
                status=SessionStatus.SCHEDULED,
                notes=generate_session_notes("scheduled"),
                source="app",
                version=1,
                is_dirty=False
            )
            # Forzar el valor string directamente
            session.status = "scheduled"
            
            db_session.add(session)
            player_sessions.append(session)
            all_sessions.append(session)
        
        sessions_by_player[player.player_id] = player_sessions
        print(f"  👤 {player.user.name}: {num_sessions} sesiones ({completed_count} completadas, {scheduled_count} programadas)")
    
    # Commit sesiones básicas
    db_session.commit()
    
    # Añadir sesiones canceladas aleatoriamente
    add_canceled_sessions(all_sessions, sessions_by_player)
    
    return all_sessions


def add_canceled_sessions(all_sessions, sessions_by_player):
    """Convertir algunas sesiones aleatorias a canceladas"""
    
    # Número total de sesiones a cancelar
    total_to_cancel = random.randint(*CANCELED_SESSIONS_TOTAL)
    print(f"🚫 Añadiendo {total_to_cancel} sesiones canceladas...")
    
    # Rastrear cancelaciones por jugador
    canceled_per_player = {player_id: 0 for player_id in sessions_by_player.keys()}
    
    # Seleccionar sesiones aleatorias para cancelar
    available_sessions = all_sessions.copy()
    random.shuffle(available_sessions)
    
    canceled_count = 0
    
    for session in available_sessions:
        if canceled_count >= total_to_cancel:
            break
            
        player_id = session.player_id
        
        # Verificar que no exceda el máximo por jugador
        if canceled_per_player[player_id] < MAX_CANCELED_PER_PLAYER:
            # Cambiar estado a cancelado (forzar string directamente)
            session.status = "canceled"
            session.notes = generate_session_notes("canceled")
            
            canceled_per_player[player_id] += 1
            canceled_count += 1
            
            print(f"  ❌ Cancelada: {session.player_name_snapshot} - {session.start_time.strftime('%Y-%m-%d %H:%M')}")
    
    # Commit cambios de cancelaciones
    db_session.commit()
    
    # Mostrar resumen de cancelaciones por jugador
    print("📋 Resumen de cancelaciones por jugador:")
    for player_id, count in canceled_per_player.items():
        if count > 0:
            player_name = sessions_by_player[player_id][0].player_name_snapshot
            print(f"  👤 {player_name}: {count} cancelada(s)")


def clear_existing_sessions():
    """Limpiar sesiones existentes"""
    print("🧹 Limpiando sesiones existentes...")
    
    try:
        deleted_count = db_session.query(Session).delete()
        db_session.commit()
        print(f"✅ {deleted_count} sesiones eliminadas")
    except Exception as e:
        print(f"⚠️ Error limpiando sesiones: {e}")
        db_session.rollback()


def show_statistics():
    """Mostrar estadísticas de las sesiones creadas"""
    print("\n📈 Estadísticas de sesiones creadas:")
    
    total_sessions = db_session.query(Session).count()
    completed_sessions = db_session.query(Session).filter(
        Session.status == SessionStatus.COMPLETED
    ).count()
    scheduled_sessions = db_session.query(Session).filter(
        Session.status == SessionStatus.SCHEDULED
    ).count()
    canceled_sessions = db_session.query(Session).filter(
        Session.status == SessionStatus.CANCELED
    ).count()
    
    print(f"  📊 Total de sesiones: {total_sessions}")
    print(f"  ✅ Completadas: {completed_sessions}")
    print(f"  📅 Programadas: {scheduled_sessions}")
    print(f"  ❌ Canceladas: {canceled_sessions}")
    
    # Estadísticas por jugador
    print("\n👥 Sesiones por jugador:")
    players = db_session.query(Player).all()
    for player in players:
        player_sessions = db_session.query(Session).filter(
            Session.player_id == player.player_id
        ).count()
        print(f"  👤 {player.user.name}: {player_sessions} sesiones")


def main():
    global db_session

    print("🏗️ Iniciando generación de sesiones...")

    # Inicializar la base de datos
    print("Inicializando conexión a base de datos...")
    initialize_database()

    with get_db_session() as session:
        db_session = session
        
        # Limpiar sesiones existentes
        clear_existing_sessions()

        print("Creando sesiones para todos los jugadores...")
        sessions = create_sessions()
        
        if sessions:
            print(f"✅ Generadas {len(sessions)} sesiones exitosamente")
            
            # Mostrar estadísticas
            show_statistics()
            
            print(f"\n🎯 Entorno: {ENVIRONMENT}")
            print("🏗️ ¡Generación de sesiones completada!")
        else:
            print("❌ No se pudieron generar sesiones")


if __name__ == "__main__":
    main()
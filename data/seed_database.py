#!/usr/bin/env python3
# seed_database.py - Script para poblar la base de datos con datos de ejemplo

import os
import sys
import random
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from faker import Faker

# Asegúrate de que el script pueda importar los modelos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar los modelos
from models import Base, User, UserType, Coach, Player, Admin, Session, SessionStatus, TestResult

# Configuración - Ajustada según tus requerimientos
DATABASE_URL = "sqlite:///./data/ballers_app.db"  # Base de datos en la carpeta data
NUM_ADMINS = 2
NUM_COACHES = 6
NUM_PLAYERS = 30
NUM_SESSIONS = 120
TESTS_PER_PLAYER = 4

# Inicializar Faker para generar datos realistas
fake = Faker()

# Conectar a la base de datos
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
DBSession = sessionmaker(bind=engine)
db_session = DBSession()

def create_users():
    """Crear usuarios de diferentes tipos"""
    users = []
    user_types = [
        (UserType.admin, NUM_ADMINS),
        (UserType.coach, NUM_COACHES),
        (UserType.player, NUM_PLAYERS)
    ]
    
    for user_type, count in user_types:
        for i in range(count):
            first_name = fake.first_name()
            last_name = fake.last_name()
            username = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 99)}"
            
            user = User(
                username=username,
                name=f"{first_name} {last_name}",
                password_hash=generate_password_hash("password123"),
                email=f"{username}@example.com",
                phone=fake.phone_number(),
                line=f"line.{username}",
                profile_photo="assets/profiles_photos/default_profile.png",  # Usar imagen por defecto para todos
                date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=45),
                user_type=user_type,
                permit_level=1 if user_type != UserType.admin else random.randint(1, 3),
                is_active=True
            )
            
            db_session.add(user)
            users.append((user, user_type))
    
    db_session.commit()
    return users

def create_profiles(users):
    """Crear perfiles específicos basados en el tipo de usuario"""
    coaches = []
    players = []
    
    for user, user_type in users:
        if user_type == UserType.admin:
            admin = Admin(
                user_id=user.user_id,
                role=random.choice(["Super Admin", "Content Manager", "Support Admin"])
            )
            db_session.add(admin)
        
        elif user_type == UserType.coach:
            license_type = random.choice(["Professional", "Advanced", "Master"])
            coach = Coach(
                user_id=user.user_id,
                license=f"{license_type}-{random.randint(10000, 99999)}"
            )
            db_session.add(coach)
            coaches.append(coach)
        
        elif user_type == UserType.player:
            service = random.choice(["Premium", "Standard", "Basic"])
            enrolment = random.randint(5, 30)
            player = Player(
                user_id=user.user_id,
                service=service,
                enrolment=enrolment,
                notes=fake.paragraph(nb_sentences=2)
            )
            db_session.add(player)
            players.append(player)
    
    db_session.commit()
    return coaches, players

def create_sessions(coaches, players):
    """Crear sesiones entre coaches y jugadores"""
    sessions = []
    
    # Fechas para distribuir las sesiones (pasadas, presentes y futuras)
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=180)  # 6 meses atrás para tener un historial más amplio
    end_date = now + timedelta(days=60)  # 2 meses en el futuro
    
    # Asegurarse de que cada jugador tenga al menos unas pocas sesiones
    for player in players:
        # Seleccionar un coach aleatorio para cada jugador
        coach = random.choice(coaches)
        
        # Crear 3-5 sesiones para cada jugador
        for _ in range(random.randint(3, 5)):
            # Generar fecha aleatoria para la sesión
            session_date = fake.date_time_between(start_date=start_date, end_date=end_date).replace(tzinfo=timezone.utc)
            end_time = session_date + timedelta(hours=random.choice([1, 1.5, 2]))
            
            # Determinar estado basado en la fecha
            if session_date < now:
                status = SessionStatus.COMPLETED if random.random() > 0.1 else SessionStatus.CANCELED
                notes = fake.paragraph(nb_sentences=3) if status == SessionStatus.COMPLETED else "Cancelado: " + fake.sentence()
            else:
                status = SessionStatus.SCHEDULED
                notes = "Sesión programada: " + fake.sentence()
            
            session = Session(
                coach_id=coach.coach_id,
                player_id=player.player_id,
                start_time=session_date,
                end_time=end_time,
                status=status,
                notes=notes,
                calendar_event_id=f"cal_{fake.uuid4()}" if random.random() > 0.3 else None
            )
            
            db_session.add(session)
            sessions.append(session)
    
    # Crear más sesiones aleatorias hasta alcanzar el número deseado
    remaining_sessions = NUM_SESSIONS - len(sessions)
    for _ in range(max(0, remaining_sessions)):
        coach = random.choice(coaches)
        player = random.choice(players)
        
        # Generar fecha aleatoria para la sesión
        session_date = fake.date_time_between(start_date=start_date, end_date=end_date).replace(tzinfo=timezone.utc)
        end_time = session_date + timedelta(hours=random.choice([1, 1.5, 2]))
        
        # Determinar estado basado en la fecha
        if session_date < now:
            status = SessionStatus.COMPLETED if random.random() > 0.1 else SessionStatus.CANCELED
            notes = fake.paragraph(nb_sentences=3) if status == SessionStatus.COMPLETED else "Cancelado: " + fake.sentence()
        else:
            status = SessionStatus.SCHEDULED
            notes = "Sesión programada: " + fake.sentence()
        
        session = Session(
            coach_id=coach.coach_id,
            player_id=player.player_id,
            start_time=session_date,
            end_time=end_time,
            status=status,
            notes=notes,
            calendar_event_id=f"cal_{fake.uuid4()}" if random.random() > 0.3 else None
        )
        
        db_session.add(session)
        sessions.append(session)
    
    db_session.commit()
    return sessions

def create_test_results(players):
    """Crear resultados de pruebas para los jugadores, mostrando progresión"""
    now = datetime.now(timezone.utc)
    
    for player in players:
        # Crear 3-4 pruebas por jugador a lo largo del tiempo para mostrar progresión
        num_tests = TESTS_PER_PLAYER
        
        # Fechas de evaluación: una cada 2-3 meses en los últimos 9-12 meses
        test_dates = []
        for i in range(num_tests):
            # Distribuir las pruebas en el tiempo, la más reciente hace 15 días
            days_ago = 15 + (i * random.randint(60, 90))
            test_date = now - timedelta(days=days_ago)
            test_dates.append(test_date.replace(tzinfo=timezone.utc))
        
        # Ordenar fechas de más antigua a más reciente
        test_dates.sort()
        
        # Valores iniciales (base) para las métricas
        base_metrics = {
            'weight': round(random.uniform(65.0, 95.0), 1),
            'height': round(random.uniform(165.0, 190.0), 1),
            'ball_control': round(random.uniform(5.0, 7.0), 1),
            'control_pass': round(random.uniform(5.0, 7.0), 1),
            'receive_scan': round(random.uniform(5.0, 7.0), 1),
            'dribling_carriying': round(random.uniform(5.0, 7.0), 1),
            'shooting': round(random.uniform(5.0, 7.0), 1),
            'crossbar': round(random.uniform(5.0, 7.0), 1),
            'sprint': round(random.uniform(4.5, 5.8), 2),  # Tiempo en segundos (menor es mejor)
            't_test': round(random.uniform(10.0, 12.0), 2),  # Tiempo en segundos (menor es mejor)
            'jumping': round(random.uniform(30.0, 50.0), 1)  # Altura en cm (mayor es mejor)
        }
        
        # Crear pruebas con progresión
        for i, test_date in enumerate(test_dates):
            # Factor de mejora: pequeñas mejoras en cada prueba (con algo de variabilidad)
            improvement_factor = (i + 1) * 0.1  # 10% de mejora por prueba
            variance = random.uniform(-0.05, 0.05)  # +/- 5% de variabilidad
            
            test_result = TestResult(
                player_id=player.player_id,
                test_name=random.choice(["Evaluación Completa", "Prueba Técnica", "Prueba Física", "Evaluación Trimestral"]),
                date=test_date,
                
                # El peso puede variar ligeramente (subir o bajar un poco)
                weight=round(base_metrics['weight'] * (1 + random.uniform(-0.03, 0.03)), 1),
                
                # La altura se mantiene prácticamente constante
                height=base_metrics['height'],
                
                # Métricas técnicas mejoran gradualmente (escala 0-10)
                ball_control=min(9.8, round(base_metrics['ball_control'] * (1 + improvement_factor + variance), 1)),
                control_pass=min(9.8, round(base_metrics['control_pass'] * (1 + improvement_factor + variance), 1)),
                receive_scan=min(9.8, round(base_metrics['receive_scan'] * (1 + improvement_factor + variance), 1)),
                dribling_carriying=min(9.8, round(base_metrics['dribling_carriying'] * (1 + improvement_factor + variance), 1)),
                shooting=min(9.8, round(base_metrics['shooting'] * (1 + improvement_factor + variance), 1)),
                crossbar=min(9.8, round(base_metrics['crossbar'] * (1 + improvement_factor + variance), 1)),
                
                # Métricas físicas mejoran gradualmente
                # Para sprint y t-test, menor tiempo es mejor (reducción)
                sprint=max(3.2, round(base_metrics['sprint'] * (1 - improvement_factor * 0.5 + variance * 0.3), 2)),
                t_test=max(8.0, round(base_metrics['t_test'] * (1 - improvement_factor * 0.5 + variance * 0.3), 2)),
                
                # Para salto, mayor altura es mejor (aumento)
                jumping=min(70.0, round(base_metrics['jumping'] * (1 + improvement_factor + variance), 1))
            )
            
            db_session.add(test_result)
    
    db_session.commit()

def main():
    """Función principal para ejecutar la carga de datos"""
    print("Iniciando población de la base de datos...")
    
    try:
        # Crear directorio para la base de datos si no existe
        os.makedirs("data", exist_ok=True)
        
        # Comprobar si la base de datos ya existe
        db_path = os.path.join("data", "ballers_app.db")
        if os.path.exists(db_path):
            print(f"La base de datos ya existe en {db_path}")
            choice = input("¿Desea limpiar los datos existentes? (s/n): ")
            if choice.lower() == 's':
                # Limpiar datos existentes
                db_session.query(TestResult).delete()
                db_session.query(Session).delete()
                db_session.query(Player).delete()
                db_session.query(Coach).delete()
                db_session.query(Admin).delete()
                db_session.query(User).delete()
                db_session.commit()
                print("Datos existentes eliminados")
            else:
                print("Se agregarán datos a la base de datos existente")
        else:
            print(f"Creando nueva base de datos en {db_path}")
        
        # Verificar si el directorio de perfiles existe, si no, advertir
        assets_dir = "assets/profiles_photos"
        if not os.path.exists(assets_dir):
            print(f"ADVERTENCIA: El directorio {assets_dir} no existe.")
            print("Se usará una ruta predeterminada para las fotos de perfil.")
            print(f"Crea el directorio {assets_dir} manualmente si es necesario.")
            print("---")
        
        print("Creando usuarios...")
        users = create_users()
        print(f"Creados {len(users)} usuarios")
        
        print("Creando perfiles específicos...")
        coaches, players = create_profiles(users)
        print(f"Creados {len(coaches)} entrenadores y {len(players)} jugadores")
        
        print("Creando sesiones...")
        sessions = create_sessions(coaches, players)
        print(f"Creadas {len(sessions)} sesiones")
        
        print("Creando resultados de pruebas...")
        create_test_results(players)
        total_tests = TESTS_PER_PLAYER * NUM_PLAYERS
        print(f"Creados {total_tests} resultados de pruebas")
        
        print("¡Base de datos poblada exitosamente!")
        
        # Estadísticas básicas 
        print("\nEstadísticas:")
        print(f"- Usuarios administradores: {db_session.query(Admin).count()}")
        print(f"- Entrenadores: {db_session.query(Coach).count()}")
        print(f"- Jugadores: {db_session.query(Player).count()}")
        print(f"- Sesiones programadas: {db_session.query(Session).filter(Session.status == SessionStatus.SCHEDULED).count()}")
        print(f"- Sesiones completadas: {db_session.query(Session).filter(Session.status == SessionStatus.COMPLETED).count()}")
        print(f"- Sesiones canceladas: {db_session.query(Session).filter(Session.status == SessionStatus.CANCELED).count()}")
        print(f"- Resultados de pruebas: {db_session.query(TestResult).count()}")
        
        # Comprobar que cada jugador tenga tests para progresión
        players_without_tests = db_session.query(Player).filter(~Player.player_id.in_(
            db_session.query(TestResult.player_id).distinct()
        )).count()
        if players_without_tests > 0:
            print(f"ADVERTENCIA: Hay {players_without_tests} jugadores sin resultados de pruebas")
        
    except Exception as e:
        print(f"Error: {e}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
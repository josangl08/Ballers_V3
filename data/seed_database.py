# data/seed_database.py

import hashlib
import os
import random
import sys
from datetime import datetime, timedelta, timezone, date

from faker import Faker
from controllers.db import get_db_session, initialize_database

# Asegúrate de que el script pueda importar los modelos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SUPABASE_DATABASE_URL, ENVIRONMENT

# Importar los modelos
from models import (
    Admin,
    Coach,
    Player,
    TestResult,
    User,
    UserType,
)

# Configuración - Ajustada según requerimientos específicos
NUM_ADMINS = 2
NUM_COACHES = 6
NUM_AMATEUR_PLAYERS = 5  # Jugadores amateur (9-14 años)
NUM_PROFESSIONAL_PLAYERS = 8  # Jugadores con datos profesionales (NO marcados como profesionales)

# Jugadores profesionales seleccionados (con 4+ temporadas)
# Nota: NO se marcan automáticamente como profesionales ni se asigna wyscout_id
PROFESSIONAL_PLAYERS = [
    {
        'player_name': 'Bill',
        'full_name': 'Rosimar Amancio',
        'position': 'CF',
        'age': 37,
        'num_seasons': 4
    },
    {
        'player_name': 'A. Worawong',
        'full_name': 'Apirak Worawong',
        'position': 'GK',
        'age': 25,
        'num_seasons': 5
    },
    {
        'player_name': 'A. Harntes',
        'full_name': 'Adisak Harntes',
        'position': 'LB',
        'age': 29,
        'num_seasons': 5
    },
    {
        'player_name': 'N. Selanon',
        'full_name': 'Nitipong Selanon',
        'position': 'RB',
        'age': 28,
        'num_seasons': 5
    },
    {
        'player_name': 'N. Kerdkaew',
        'full_name': 'Noppol Kerdkaew',
        'position': 'RCB',
        'age': 20,
        'num_seasons': 4
    },
    {
        'player_name': 'A. Ngrnbukkol',
        'full_name': 'Anuchit Ngrnbukkol',
        'position': 'RCMF',
        'age': 28,
        'num_seasons': 4
    },
    {
        'player_name': 'J. Wonggorn',
        'full_name': 'Jaroensak Wonggorn',
        'position': 'RW',
        'age': 24,
        'num_seasons': 5
    },
    {
        'player_name': 'P. Sookjitthammakul',
        'full_name': 'Phitiwat Sookjitthammakul',
        'position': 'LCMF',
        'age': 26,
        'num_seasons': 5
    }
]

# Inicializar Faker para generar datos realistas
fake = Faker()
db_session = None


# Función para crear hash de contraseña (igual que en login.py)
def hash_password(password):
    """Convierte una contraseña en un hash SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_users():
    """Crear usuarios de diferentes tipos"""
    users = []
    total_players = NUM_AMATEUR_PLAYERS + NUM_PROFESSIONAL_PLAYERS
    user_types = [
        (UserType.admin, NUM_ADMINS),
        (UserType.coach, NUM_COACHES),
        (UserType.player, total_players),
    ]

    for user_type, count in user_types:
        for i in range(count):
            if user_type == UserType.admin:
                username = f"admin{i+1}"
                name = fake.name()
                password = hash_password("admin123")
                phone = fake.phone_number()
            elif user_type == UserType.coach:
                username = f"coach{i+1}"
                name = fake.name()
                password = hash_password("coach123")
                phone = fake.phone_number()
            else:  # UserType.player
                username = f"player{i+1}"
                name = fake.name()
                password = hash_password("player123")
                phone = fake.phone_number()

            email = f"{username}@ballers.com"

            user = User(
                username=username,
                name=name,
                email=email,
                phone=phone,
                password_hash=password,
                user_type=user_type,
                is_active=True,
                profile_photo="assets/profile_photos/default_profile.png",  # Foto por defecto
                date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=65),
            )

            db_session.add(user)
            users.append(user)

    db_session.commit()
    return users


def create_profiles(users):
    """Crear perfiles específicos para cada tipo de usuario"""
    coaches = []
    players = []
    admin_count = 0
    coach_count = 0
    player_count = 0

    for user in users:
        if user.user_type == UserType.admin:
            admin = Admin(
                user_id=user.user_id,
                system_permissions="full_access",
            )
            db_session.add(admin)
            admin_count += 1

        elif user.user_type == UserType.coach:
            coach = Coach(
                user_id=user.user_id,
                service="Personal Training",
                schedule_settings=f"Lunes a Viernes: {random.randint(8, 10)}:00-{random.randint(17, 19)}:00",
                notes=fake.paragraph(nb_sentences=2),
                hourly_rate=round(random.uniform(25.0, 45.0), 2),
                certification=random.choice(["UEFA B", "UEFA A", "Nacional", "Regional"]),
                specialization=random.choice(["Técnica individual", "Fitness", "Táctica", "Porteros"])
            )
            db_session.add(coach)
            coaches.append(coach)
            coach_count += 1

        elif user.user_type == UserType.player:
            # Configurar datos específicos según si es amateur o profesional
            service = random.choice(["Premium", "Standard", "Basic"])
            enrolment = random.randint(5, 30)
            
            # Determinar si usar datos profesionales (pero NO marcar como profesional)
            use_professional_data = player_count >= NUM_AMATEUR_PLAYERS
            
            if use_professional_data:
                # Asignar datos del jugador profesional correspondiente
                prof_index = player_count - NUM_AMATEUR_PLAYERS
                if prof_index < len(PROFESSIONAL_PLAYERS):
                    prof_player = PROFESSIONAL_PLAYERS[prof_index]
                    
                    # Actualizar nombre del usuario con el nombre real del jugador profesional
                    user.name = prof_player['full_name']
                    user.username = f"pro_{prof_player['player_name'].lower().replace(' ', '_').replace('.', '')}"
                    
                    # Calcular fecha de nacimiento basada en la edad
                    current_year = datetime.now().year
                    birth_year = current_year - prof_player['age']
                    user.date_of_birth = fake.date_between(start_date=date(birth_year, 1, 1), end_date=date(birth_year, 12, 31))
            
            # IMPORTANTE: NO marcar como profesional ni asignar wyscout_id automáticamente
            player = Player(
                user_id=user.user_id,
                service=service,
                enrolment=enrolment,
                notes=fake.paragraph(nb_sentences=2),
                is_professional=False,  # Siempre False inicialmente
                wyscout_id=None,       # Siempre None inicialmente
            )
            db_session.add(player)
            players.append(player)
            player_count += 1

    db_session.commit()
    return coaches, players


def create_test_results(players):
    """Crear resultados de pruebas para todos los jugadores (4-8 tests por jugador)"""
    now = datetime.now(timezone.utc)

    for player in players:
        # Crear 4-8 pruebas por jugador a lo largo del tiempo
        num_tests = random.randint(4, 8)

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
            "weight": round(random.uniform(30.0, 80.0), 1),  # Peso para jugadores
            "height": round(random.uniform(140.0, 185.0), 1),  # Altura para jugadores
            "ball_control": round(random.uniform(4.0, 8.0), 1),
            "control_pass": round(random.uniform(4.0, 8.0), 1),
            "receive_scan": round(random.uniform(4.0, 8.0), 1),
            "dribling_carriying": round(random.uniform(4.0, 8.0), 1),
            "shooting": round(random.uniform(4.0, 8.0), 1),
            "crossbar": round(random.uniform(4.0, 8.0), 1),
            "sprint": round(random.uniform(10.0, 16.0), 1),  # segundos para sprint
            "t_test": round(random.uniform(8.0, 12.0), 1),   # segundos para T-test
            "jumping": round(random.uniform(20.0, 60.0), 1), # cm para salto vertical
        }

        # Crear las pruebas con progresión
        for test_idx, test_date in enumerate(test_dates):
            test_name = f"Evaluación {test_idx + 1}"
            
            # Simular progresión/regresión leve en cada prueba
            improvement_factor = 1 + (test_idx * random.uniform(-0.05, 0.15))  # ±5% a +15%
            variance = random.uniform(0.9, 1.1)  # Variabilidad natural ±10%
            
            test_result = TestResult(
                player_id=player.player_id,
                test_name=test_name,
                date=test_date,
                weight=round(base_metrics["weight"] * improvement_factor * variance, 1),
                height=round(base_metrics["height"], 1),  # La altura no cambia mucho
                ball_control=round(min(10.0, base_metrics["ball_control"] * improvement_factor * variance), 1),
                control_pass=round(min(10.0, base_metrics["control_pass"] * improvement_factor * variance), 1),
                receive_scan=round(min(10.0, base_metrics["receive_scan"] * improvement_factor * variance), 1),
                dribling_carriying=round(min(10.0, base_metrics["dribling_carriying"] * improvement_factor * variance), 1),
                shooting=round(min(10.0, base_metrics["shooting"] * improvement_factor * variance), 1),
                crossbar=round(min(10.0, base_metrics["crossbar"] * improvement_factor * variance), 1),
                sprint=round(max(8.0, base_metrics["sprint"] / improvement_factor * variance), 1),  # Menor tiempo = mejor
                t_test=round(max(6.0, base_metrics["t_test"] / improvement_factor * variance), 1),   # Menor tiempo = mejor
                jumping=round(base_metrics["jumping"] * improvement_factor * variance, 1),
            )
            
            db_session.add(test_result)

    db_session.commit()


def clear_existing_data():
    """Limpiar datos existentes en la base de datos"""
    print("🧹 Limpiando datos existentes...")
    
    try:
        # Eliminar en orden inverso por las foreign keys
        db_session.query(TestResult).delete()
        db_session.query(Player).delete()
        db_session.query(Coach).delete()
        db_session.query(Admin).delete()
        db_session.query(User).delete()
        
        db_session.commit()
        print("✅ Datos existentes eliminados")
    except Exception as e:
        print(f"⚠️ Error limpiando datos: {e}")
        db_session.rollback()


def main():
    global db_session

    print("🏗️ Iniciando poblamiento de la base de datos...")

    # Inicializar la base de datos
    print("Inicializando base de datos...")
    initialize_database()

    with get_db_session() as session:
        db_session = session
        
        # Limpiar datos existentes primero
        clear_existing_data()

        print("Creando usuarios...")
        users = create_users()
        print(f"Creados {len(users)} usuarios")
        print("NOTA: Todos los usuarios tienen contraseñas basadas en su tipo (admin123, coach123, player123)")

        print("Creando perfiles específicos...")
        coaches, players = create_profiles(users)
        amateur_players = players[:NUM_AMATEUR_PLAYERS]  # Primeros 5 son amateur
        professional_like_players = players[NUM_AMATEUR_PLAYERS:]  # Últimos 8 son con datos profesionales
        print(f"Creados {len(coaches)} entrenadores")
        print(f"Creados {len(amateur_players)} jugadores amateur (9-14 años)")
        print(f"Creados {len(professional_like_players)} jugadores con datos profesionales (NO marcados como profesionales)")
        
        print("Creando resultados de pruebas para TODOS los jugadores...")
        create_test_results(players)  # Para todos los jugadores (amateur + profesionales)
        total_tests_approx = 6 * len(players)  # Aproximadamente 6 tests por jugador (promedio entre 4-8)
        print(f"Creados aprox. {total_tests_approx} resultados de pruebas para todos los jugadores")

        print("¡Base de datos poblada exitosamente!")

        # Estadísticas básicas
        print("\nEstadísticas:")
        print(f"- Usuarios administradores: {db_session.query(Admin).count()}")
        print(f"- Entrenadores: {db_session.query(Coach).count()}")
        print(f"- Jugadores totales: {db_session.query(Player).count()}")
        print(f"- Test results: {db_session.query(TestResult).count()}")

        print("\nDetalle de usuarios creados:")
        for user in users:
            print(f"  {user.username} ({user.user_type.value}) - {user.name}")

        print(f"\n🎯 Entorno: {ENVIRONMENT}")
        if ENVIRONMENT == "production":
            print(f"🗄️ Base de datos: Supabase PostgreSQL")
        else:
            print(f"🗄️ Base de datos: Local SQLite")


if __name__ == "__main__":
    main()
# data/create_admin.py
import sys
import os
from pathlib import Path
import hashlib
import shutil
from datetime import datetime

# Agregar la ruta raíz al path de Python
sys.path.append(str(Path(__file__).parent.parent))

# Importar modelos y configuración
from config import ASSETS_DIR, DEFAULT_PROFILE_PHOTO, DATABASE_PATH
from models import Base, User, UserType, Admin

def ensure_directories():
    """Asegura que existan los directorios necesarios."""
    # Crear estructura de directorios
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    os.makedirs(os.path.join(ASSETS_DIR, "profile_photos"), exist_ok=True)
    
    # Crear archivo de imagen por defecto si no existe
    if not os.path.exists(DEFAULT_PROFILE_PHOTO):
        # Intentar crear un archivo vacío como placeholder
        with open(DEFAULT_PROFILE_PHOTO, "w") as f:
            f.write("")
        print(f"Archivo {DEFAULT_PROFILE_PHOTO} creado (vacío)")

def create_admin_user():
    """Crea un usuario administrador en la base de datos."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Hash para la contraseña "admin"
    password_hash = hashlib.sha256("admin".encode()).hexdigest()
    
    # Configurar la conexión a la base de datos
    engine = create_engine(f'sqlite:///{DATABASE_PATH}')
    Base.metadata.create_all(engine)  # Crea tablas si no existen
    Session = sessionmaker(bind=engine)
    db_session = Session()

    # Verificar si ya existe un usuario admin
    existing_admin = db_session.query(User).filter_by(username="admin").first()

    if not existing_admin:
        # Crear usuario admin
        admin_user = User(
            username="admin",
            name="Administrador",
            password_hash=password_hash,
            email="admin@example.com",
            user_type=UserType.admin,
            permit_level=10,
            is_active=True,
            profile_photo=DEFAULT_PROFILE_PHOTO
        )
        
        db_session.add(admin_user)
        db_session.flush()
        
        # Crear perfil de admin
        admin_profile = Admin(
            user_id=admin_user.user_id,
            role="Super Admin"
        )
        
        db_session.add(admin_profile)
        db_session.commit()
        print("Usuario administrador creado con éxito")
        print("  - Usuario: admin")
        print("  - Contraseña: admin")
    else:
        print("El usuario administrador ya existe")

    db_session.close()

def create_test_data():
    """Opcionalmente crea datos de prueba."""
    create_test = input("¿Deseas crear datos de prueba? (s/n): ").lower() == 's'
    
    if create_test:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from models import Coach, Player, Session, SessionStatus, TestResult
        from datetime import datetime, timedelta
        
        # Configurar conexión
        engine = create_engine(f'sqlite:///{DATABASE_PATH}')
        Session = sessionmaker(bind=engine)
        db_session = Session()
        
        try:
            # Crear algunos usuarios de prueba si no existen
            if db_session.query(User).filter_by(username="coach1").first() is None:
                # Coach
                coach_user = User(
                    username="coach1",
                    name="Entrenador Demo",
                    password_hash=hashlib.sha256("coach123".encode()).hexdigest(),
                    email="coach@example.com",
                    user_type=UserType.coach,
                    is_active=True,
                    profile_photo=DEFAULT_PROFILE_PHOTO
                )
                db_session.add(coach_user)
                db_session.flush()
                
                coach_profile = Coach(
                    user_id=coach_user.user_id,
                    license="COACH-001"
                )
                db_session.add(coach_profile)
                
                # Jugadores
                player_names = ["Carlos Pérez", "Ana García", "Miguel Rodríguez"]
                for i, name in enumerate(player_names):
                    username = f"player{i+1}"
                    
                    player_user = User(
                        username=username,
                        name=name,
                        password_hash=hashlib.sha256("player123".encode()).hexdigest(),
                        email=f"{username}@example.com",
                        user_type=UserType.player,
                        is_active=True,
                        profile_photo=DEFAULT_PROFILE_PHOTO
                    )
                    db_session.add(player_user)
                    db_session.flush()
                    
                    player_profile = Player(
                        user_id=player_user.user_id,
                        service="Premium" if i == 0 else "Básico",
                        enrolment=10 if i == 0 else 5,
                        notes=f"Notas de prueba para {name}"
                    )
                    db_session.add(player_profile)
                
                db_session.commit()
                print("Usuarios de prueba creados con éxito")
                print("  - Coach: coach1 / coach123")
                print("  - Jugadores: player1, player2, player3 / player123")
                
                # Añadir sesiones y datos de prueba
                coach = db_session.query(Coach).join(User).filter(User.username == "coach1").first()
                players = db_session.query(Player).all()
                
                # Crear algunas sesiones
                today = datetime.now()
                
                # IMPORTANTE: Verificar los nombres de los campos del modelo Session
                for i, player in enumerate(players):
                    # Para verificar los nombres correctos de los campos, imprimimos la estructura
                    session_obj = Session()
                    print(f"Campos disponibles en Session: {dir(session_obj)}")
                    
                    # Usamos la forma correcta según los campos disponibles
                    # Sesión pasada (completada)
                    past_date = today - timedelta(days=7 + i)
                    past_session = Session()
                    # Configuramos los atributos directamente
                    past_session.coach_id = coach.coach_id
                    past_session.player_id = player.player_id
                    past_session.start_time = past_date.replace(hour=10, minute=0)
                    past_session.end_time = past_date.replace(hour=11, minute=0)
                    past_session.status = SessionStatus.COMPLETED
                    past_session.notes = f"Sesión completada con {player.user.name}"
                    db_session.add(past_session)
                    
                    # Sesión futura (programada)
                    future_date = today + timedelta(days=i + 1)
                    future_session = Session()
                    future_session.coach_id = coach.coach_id
                    future_session.player_id = player.player_id
                    future_session.start_time = future_date.replace(hour=10, minute=0)
                    future_session.end_time = future_date.replace(hour=11, minute=0)
                    future_session.status = SessionStatus.SCHEDULED
                    future_session.notes = f"Sesión programada con {player.user.name}"
                    db_session.add(future_session)
                    
                    # Crear resultados de prueba
                    for j in range(2):
                        test_date = today - timedelta(days=90 - j*30)
                        test_result = TestResult(
                            player_id=player.player_id,
                            test_name=f"Prueba {j+1}",
                            date=test_date,
                            weight=70.0 + j*2,
                            height=175.0 + j,
                            ball_control=7.0 + j*0.5,
                            control_pass=6.5 + j*0.5,
                            receive_scan=7.2 + j*0.3,
                            dribling_carriying=8.0 + j*0.2,
                            shooting=7.5 + j*0.5,
                            crossbar=6.0 + j*0.5,
                            sprint=8.5 - j*0.2,
                            t_test=7.0 + j*0.3,
                            jumping=8.2 + j*0.1
                        )
                        db_session.add(test_result)
                
                db_session.commit()
                print("Datos de prueba creados con éxito (sesiones y resultados)")
            else:
                print("Ya existen datos de prueba en la base de datos")
        
        except Exception as e:
            db_session.rollback()
            print(f"Error al crear datos de prueba: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            db_session.close()

def main():
    """Función principal."""
    print("=== Ballers App - Configuración inicial ===")
    
    # Verificar directorios
    print("\nVerificando estructura de directorios...")
    ensure_directories()
    print("Estructura de directorios verificada.")
    
    # Crear usuario administrador
    print("\nCreando usuario administrador...")
    create_admin_user()
    
    # Crear datos de prueba
    print("\nConfiguración de datos de prueba:")
    create_test_data()
    
    print("\n=== Configuración completada ===")
    print(f"Base de datos: {DATABASE_PATH}")
    print("Puedes iniciar la aplicación con: streamlit run main.py")

if __name__ == "__main__":
    main()
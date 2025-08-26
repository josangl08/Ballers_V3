# controllers/db.py
import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.orm import sessionmaker

from config import DATABASE_PATH
from models import Base

# Variables globales para reutilizar engine y Session
_engine = None
_Session: Optional[sessionmaker] = None


def initialize_database() -> bool:
    """
    Inicializa la base de datos solo una vez al inicio de la aplicación.
    Usa configuración dual: SQLite para desarrollo, PostgreSQL para producción.

    Returns:
        bool: True si la inicialización fue exitosa, False en caso contrario
    """
    global _engine, _Session

    try:
        if _engine is None:
            # Lectura directa de variables en tiempo de ejecución (no importación)
            environment = os.getenv('ENVIRONMENT', 'development')
            supabase_db_url = os.getenv('SUPABASE_DATABASE_URL', '')
            
            # Determinar DATABASE_URL basado en entorno en tiempo real
            if environment == 'production':
                if not supabase_db_url:
                    raise ValueError("SUPABASE_DATABASE_URL no configurada para producción")
                database_url = supabase_db_url
            else:
                database_url = f"sqlite:///{DATABASE_PATH}"

            # Debug: Verificar detección de variables de entorno críticas
            print(f"🔍 DEBUG - Variables de entorno en tiempo de ejecución:")
            print(f"   ENVIRONMENT (direct): {environment}")
            print(f"   DATABASE_URL determinada: {database_url.split('@')[0] if '@' in database_url else database_url[:50]}...")
            print(f"   SUPABASE_URL disponible: {'SÍ' if os.getenv('SUPABASE_URL') else 'NO'}")

            print(
                f"🔧 Conectando a base de datos ({environment}): {database_url.split('@')[0] if '@' in database_url else database_url[:50]}..."
            )
            _engine = create_engine(database_url)

            # Para SQLite, crear tablas si no existe o está vacía
            if environment != "production":
                if (
                    not os.path.exists(DATABASE_PATH)
                    or os.path.getsize(DATABASE_PATH) == 0
                ):
                    print("🔧 Creando nueva base de datos SQLite...")
                    Base.metadata.create_all(_engine)
                    print("✅ Tablas SQLite creadas exitosamente")
            else:
                # Para PostgreSQL, las tablas ya existen en Supabase
                print("✅ Usando base de datos PostgreSQL existente en Supabase")

            _Session = sessionmaker(bind=_engine)
            print(f"✅ Base de datos {environment} inicializada correctamente")
            return True

    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")
        _engine = None
        _Session = None
        return False

    return True


def get_db_session() -> SQLAlchemySession:
    """
    Devuelve una sesión SQLAlchemy lista para usar.

    Returns:
        SQLAlchemySession: Sesión de base de datos

    Raises:
        RuntimeError: Si no se puede inicializar la base de datos
    """
    global _Session

    # Asegurar que la base de datos esté inicializada
    if _Session is None:
        if not initialize_database():
            raise RuntimeError(
                "No se pudo inicializar la base de datos. "
                "Verifica que el archivo de configuración y los permisos sean correctos."
            )

    # Para satisfacer a Pylance
    if _Session is None:
        raise RuntimeError(
            "Error crítico: _Session sigue siendo None después de la inicialización"
        )

    return _Session()


def close_all_connections():
    """Cierra todas las conexiones y limpia los recursos globales."""
    global _engine, _Session

    if _engine is not None:
        _engine.dispose()
        _engine = None

    _Session = None
    print("🔒 Conexiones de base de datos cerradas")


def get_database_info() -> dict:
    """
    Devuelve información sobre el estado de la base de datos.

    Returns:
        dict: Información sobre la base de datos
    """
    if ENVIRONMENT == "production":
        # Para PostgreSQL/Supabase
        return {
            "database_url": (
                DATABASE_URL.split("@")[0] + "@***" if DATABASE_URL else None
            ),
            "environment": ENVIRONMENT,
            "database_type": "PostgreSQL (Supabase)",
            "is_initialized": _Session is not None,
            "engine_active": _engine is not None,
        }
    else:
        # Para SQLite local
        exists = os.path.exists(DATABASE_PATH) if DATABASE_PATH else False
        return {
            "database_path": DATABASE_PATH,
            "environment": ENVIRONMENT,
            "database_type": "SQLite (Local)",
            "exists": exists,
            "size_bytes": (
                os.path.getsize(DATABASE_PATH) if (exists and DATABASE_PATH) else 0
            ),
            "is_initialized": _Session is not None,
            "engine_active": _engine is not None,
        }

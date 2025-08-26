# controllers/db.py
import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.orm import sessionmaker

from models import Base

# Variables globales para reutilizar engine y Session
_engine = None
_Session: Optional[sessionmaker] = None


def initialize_database() -> bool:
    """
    Inicializa la base de datos PostgreSQL de Supabase.
    Configuración simplificada solo para producción.

    Returns:
        bool: True si la inicialización fue exitosa, False en caso contrario
    """
    global _engine, _Session

    try:
        if _engine is None:
            # Obtener URL de Supabase directamente
            supabase_db_url = os.getenv('SUPABASE_DATABASE_URL')
            
            if not supabase_db_url:
                print("❌ SUPABASE_DATABASE_URL no está configurada")
                return False

            print(f"🔧 Conectando a Supabase PostgreSQL...")
            print(f"   URL: {supabase_db_url.split('@')[0]}...")
            
            _engine = create_engine(supabase_db_url)

            # Para PostgreSQL de Supabase, las tablas ya existen
            print("✅ Conectado a base de datos PostgreSQL de Supabase")

            _Session = sessionmaker(bind=_engine)
            print("✅ Base de datos inicializada correctamente")
            return True

    except Exception as e:
        print(f"❌ Error conectando a Supabase: {e}")
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

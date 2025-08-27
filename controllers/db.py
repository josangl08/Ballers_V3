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

# Connection pooling configuration optimizado para Supabase
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "3"))  # Reducido para Supabase
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "2"))  # Total máximo: 5 conexiones


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
            supabase_db_url = os.getenv("SUPABASE_DATABASE_URL")

            if not supabase_db_url:
                print("❌ SUPABASE_DATABASE_URL no está configurada")
                return False

            print(f"🔧 Conectando a Supabase PostgreSQL...")
            print(f"   URL: {supabase_db_url.split('@')[0]}...")

            # Configurar engine con connection pooling optimizado para Supabase
            _engine = create_engine(
                supabase_db_url,
                pool_size=POOL_SIZE,  # Conexiones persistentes en el pool
                max_overflow=MAX_OVERFLOW,  # Conexiones adicionales si es necesario
                pool_timeout=20,  # Timeout más agresivo para Supabase
                pool_recycle=1800,  # Reciclar cada 30 min (Supabase cierra idle)
                pool_pre_ping=True,  # Verificar conexiones antes de usar
                pool_reset_on_return="rollback",  # Limpiar transacciones al devolver
                echo=False,  # No logging SQL (performance)
            )

            print(f"🏊 Connection pool configurado (optimizado para Supabase):")
            print(f"   - Pool size: {POOL_SIZE}")
            print(f"   - Max overflow: {MAX_OVERFLOW}")
            print(f"   - Pool timeout: 20s")
            print(f"   - Pool recycle: 30m")
            print(f"   - Pool reset: rollback")

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
    """Cierra todas las conexiones del pool y limpia los recursos globales."""
    global _engine, _Session

    if _engine is not None:
        print(f"🔒 Cerrando connection pool...")
        print(f"   - Conexiones activas: {_engine.pool.checkedout()}")
        print(f"   - Conexiones en pool: {_engine.pool.checkedin()}")

        _engine.dispose()  # Cierra todas las conexiones del pool
        _engine = None

    _Session = None
    print("✅ Connection pool cerrado correctamente")


def get_database_info() -> dict:
    """
    Devuelve información sobre el estado de la base de datos incluyendo pool info.

    Returns:
        dict: Información sobre la base de datos
    """
    base_info = {
        "database_type": "PostgreSQL (Supabase)",
        "is_initialized": _Session is not None,
        "engine_active": _engine is not None,
    }

    # Información del connection pool si está disponible
    if _engine is not None:
        pool = _engine.pool
        base_info.update(
            {
                "pool_size": pool.size(),
                "pool_checked_in": pool.checkedin(),
                "pool_checked_out": pool.checkedout(),
                "pool_overflow": pool.overflow(),
                "pool_invalid": pool.invalid(),
            }
        )

    return base_info

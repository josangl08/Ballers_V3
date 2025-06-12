# controllers/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from models import Base
from config import DATABASE_PATH
import os
from typing import Optional

# Variables globales para reutilizar engine y Session
_engine = None
_Session: Optional[sessionmaker] = None

def initialize_database() -> bool:
    """
    Inicializa la base de datos solo una vez al inicio de la aplicación.
    
    Returns:
        bool: True si la inicialización fue exitosa, False en caso contrario
    """
    global _engine, _Session
    
    try:
        if _engine is None:
            if not DATABASE_PATH or not isinstance(DATABASE_PATH, str):
                raise ValueError("DATABASE_PATH must be a valid string path")
                
            _engine = create_engine(f"sqlite:///{DATABASE_PATH}")
            
            # Solo crear tablas si la base de datos no existe o está vacía
            if not os.path.exists(DATABASE_PATH) or os.path.getsize(DATABASE_PATH) == 0:
                print("🔧 Creando nueva base de datos...")
                Base.metadata.create_all(_engine)
                print("✅ Tablas creadas exitosamente")
            
            _Session = sessionmaker(bind=_engine)
            print("✅ Base de datos inicializada correctamente")
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
        raise RuntimeError("Error crítico: _Session sigue siendo None después de la inicialización")
    
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
    exists = os.path.exists(DATABASE_PATH) if DATABASE_PATH else False
    return {
        "database_path": DATABASE_PATH,
        "exists": exists,
        "size_bytes": os.path.getsize(DATABASE_PATH) if (exists and DATABASE_PATH) else 0,
        "is_initialized": _Session is not None,
        "engine_active": _engine is not None
    }
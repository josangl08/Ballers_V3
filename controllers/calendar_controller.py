# controllers/calendar_controller.py
"""
ARCHIVO TEMPORAL DE COMPATIBILIDAD
Este archivo mantiene las funciones públicas para no romper imports existentes.
TODO: Eliminar cuando todos los imports estén actualizados.
"""

# Importaciones desde los nuevos módulos
from .session_controller import (
    get_sessions,
    push_session, 
    update_session,
    delete_session,
    update_past_sessions
)

from .calendar_sync_core import (
    sync_calendar_to_db,
    sync_calendar_to_db_with_feedback,
    sync_db_to_calendar,
    status_from_color as _status_from_color,
    patch_color
)

from models import SessionStatus

# Re-exportar para compatibilidad
__all__ = [
    'get_sessions',
    'push_session', 
    'update_session',
    'delete_session',
    'update_past_sessions',
    'sync_calendar_to_db',
    'sync_calendar_to_db_with_feedback', 
    'sync_db_to_calendar',
    'SessionStatus',
    'patch_color'
]

print("⚠️ WARNING: Usando calendar_controller.py de compatibilidad. Actualizar imports a nuevos módulos.")
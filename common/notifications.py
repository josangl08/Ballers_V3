# common/notifications.py
"""
Sistema de notificaciones simplificado para problemas de sincronización.
Ahora solo funciones de compatibilidad - la lógica está en NotificationController.
"""
from typing import List, Dict, Any, Optional
import streamlit as st
from controllers.notification_controller import (
    NotificationController,
    save_sync_problems as _save_sync_problems,
    get_sync_problems as _get_sync_problems,
    clear_sync_problems as _clear_sync_problems,
    auto_cleanup_old_problems as _auto_cleanup_old_problems
)


# ========================================================================
# FUNCIONES PÚBLICAS DE COMPATIBILIDAD
# ========================================================================

def save_sync_problems(rejected_events: List[Dict], warning_events: List[Dict]) -> None:
    """
    Guarda problemas de sincronización del sync ACTUAL.
    🔄 REFACTORIZADO: Ahora usa NotificationController.
    
    Args:
        rejected_events: Lista de eventos rechazados
        warning_events: Lista de eventos con advertencias
    """
    _save_sync_problems(rejected_events, warning_events)


def get_sync_problems() -> Optional[Dict[str, Any]]:
    """
    Obtiene problemas de sincronización guardados.
    🔄 REFACTORIZADO: Ahora usa NotificationController.
    
    Returns:
        Dict con problemas o None si no hay datos válidos
    """
    return _get_sync_problems()


def clear_sync_problems() -> None:
    """
    Limpia todos los problemas guardados.
    🔄 REFACTORIZADO: Ahora usa NotificationController.
    """
    _clear_sync_problems()


def auto_cleanup_old_problems(max_age_hours: int = 24) -> None:
    """
    Limpia automáticamente problemas antiguos.
    🔄 REFACTORIZADO: Ahora usa NotificationController.
    
    Args:
        max_age_hours: Máximo tiempo en horas para mantener problemas
    """
    _auto_cleanup_old_problems(max_age_hours)


# ========================================================================
# FUNCIONES ADICIONALES PARA COMPATIBILIDAD TOTAL
# ========================================================================

def has_sync_problems() -> bool:
    """
    Verifica si hay problemas de sincronización pendientes.
    🆕 NUEVA: Disponible a través del controller.
    
    Returns:
        True si hay problemas rechazados o warnings
    """
    controller = NotificationController()
    return controller.has_problems()


def get_problems_summary() -> str:
    """
    Devuelve resumen textual de problemas para logs o mensajes.
    🆕 NUEVA: Disponible a través del controller.
    
    Returns:
        String con resumen, vacío si no hay problemas
    """
    controller = NotificationController()
    return controller.get_summary_text()


def mark_problems_as_seen() -> None:
    """
    Marca los problemas como vistos por el usuario.
    🆕 NUEVA: Útil para dashboard que muestra todos los detalles.
    """
    controller = NotificationController()
    controller.mark_as_seen()


# ========================================================================
# FUNCIONES AVANZADAS PARA UI (NUEVAS CAPACIDADES)
# ========================================================================

def get_problems_for_sidebar() -> Optional[Dict[str, Any]]:
    """
    🆕 NUEVA: Obtiene problemas solo si son muy recientes (para sidebar).
    
    Returns:
        Dict con datos para sidebar o None si no hay problemas recientes
    """
    from controllers.notification_controller import get_problems_for_display
    return get_problems_for_display("sidebar")


def get_problems_for_settings() -> Optional[Dict[str, Any]]:
    """
    🆕 NUEVA: Obtiene problemas para página de settings (más tolerante con edad).
    
    Returns:
        Dict con datos para settings o None si no hay problemas
    """
    from controllers.notification_controller import get_problems_for_display
    return get_problems_for_display("settings")


def get_problems_for_dashboard() -> Optional[Dict[str, Any]]:
    """
    🆕 NUEVA: Obtiene problemas para dashboard completo.
    
    Returns:
        Dict con datos completos para dashboard
    """
    from controllers.notification_controller import get_problems_for_display
    return get_problems_for_display("dashboard")


# ========================================================================
# UTILITIES PARA DESARROLLO Y DEBUG
# ========================================================================

def get_notification_controller() -> NotificationController:
    """
    🆕 NUEVA: Acceso directo al controller para casos avanzados.
    
    Returns:
        Instancia del NotificationController
    """
    from controllers.notification_controller import get_notification_controller
    return get_notification_controller()


def force_cleanup_all_notification_data() -> None:
    """
    🆕 NUEVA: Limpieza forzada de todos los datos (útil para desarrollo).
    """
    controller = NotificationController()
    controller.clear_all()
    print("🧹 All notification data force-cleaned")


def get_notification_debug_info() -> Dict[str, Any]:
    """
    🆕 NUEVA: Información de debug sobre el estado de notificaciones.
    
    Returns:
        Dict con información de debug
    """
    controller = NotificationController()
    problems = controller.get_problems()
    
    if not problems:
        return {
            "status": "no_problems",
            "has_data": False,
            "storage_key_exists": controller.STORAGE_KEY in st.session_state
        }
    
    return {
        "status": "has_problems",
        "has_data": True,
        "rejected_count": len(problems.rejected),
        "warnings_count": len(problems.warnings),
        "total_count": problems.problem_count(),
        "timestamp": problems.timestamp,
        "age_minutes": problems.get_age_minutes(),
        "seen": problems.seen,
        "storage_key": controller.STORAGE_KEY
    }


# ========================================================================
# BACKWARD COMPATIBILITY (si es necesario)
# ========================================================================

# Aliases para máxima compatibilidad si algún código los usa
cleanup_old_problems = auto_cleanup_old_problems  # Alias
get_problems = get_sync_problems  # Alias
save_problems = save_sync_problems  # Alias
clear_problems = clear_sync_problems  # Alias
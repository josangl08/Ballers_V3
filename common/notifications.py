# common/notifications.py
"""
Sistema de notificaciones simplificado para problemas de sincronización.
Ahora solo funciones de compatibilidad - la lógica está en NotificationController.
"""
from typing import List, Dict, Any, Optional
import streamlit as st
from controllers.notification_controller import (

    save_sync_problems as _save_sync_problems,
    get_sync_problems as _get_sync_problems,
    clear_sync_problems as _clear_sync_problems,
    auto_cleanup_old_problems as _auto_cleanup_old_problems
)
# Funciones publicas

def save_sync_problems(rejected_events: List[Dict], warning_events: List[Dict]) -> None:
    """
    Guarda problemas de sincronización del sync ACTUAL.
    
    Args:
        rejected_events: Lista de eventos rechazados
        warning_events: Lista de eventos con advertencias
    """
    _save_sync_problems(rejected_events, warning_events)


def get_sync_problems() -> Optional[Dict[str, Any]]:
    """
    Obtiene problemas de sincronización guardados.
    
    Returns:
        Dict con problemas o None si no hay datos válidos
    """
    return _get_sync_problems()


def clear_sync_problems() -> None:
    """
    Limpia todos los problemas guardados.
    """
    _clear_sync_problems()


def auto_cleanup_old_problems(max_age_hours: int = 24) -> None:
    """
    Limpia automáticamente problemas antiguos.
    
    Args:
        max_age_hours: Máximo tiempo en horas para mantener problemas
    """
    _auto_cleanup_old_problems(max_age_hours)


# Aliases para máxima compatibilidad si algún código los usa
cleanup_old_problems = auto_cleanup_old_problems  # Alias
get_problems = get_sync_problems  # Alias
save_problems = save_sync_problems  # Alias
clear_problems = clear_sync_problems  # Alias
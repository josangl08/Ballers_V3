# controllers/sync_coordinator.py
"""
Coordinador de sincronización - gestiona auto-sync, locks y estadísticas.
Anteriormente: sync.py
"""

import datetime as dt
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

import streamlit as st

from controllers.db import get_db_session
from controllers.notification_controller import save_sync_problems
from models import Coach, User

from .calendar_sync_core import sync_calendar_to_db_with_feedback, sync_db_to_calendar
from .session_controller import update_past_sessions

logger = logging.getLogger(__name__)


# Funciones simples para reemplazar cloud_utils (eliminado)
def is_streamlit_cloud():
    """Siempre False ya que no usamos Streamlit Cloud"""
    return False


def safe_database_operation(operation, *args, **kwargs):
    """Ejecuta operación de BD de forma simple"""
    try:
        return operation(*args, **kwargs)
    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        return None


# Internal helpers


def _toast(msg: str, icon: str = "") -> None:
    """Muestra un mensaje flotante con duración extendida."""
    if hasattr(st, "toast"):
        st.toast(msg, icon=icon)
        if "Auto-Sync" in msg and (
            "importada" in msg or "actualizada" in msg or "eliminada" in msg
        ):
            if "sync_notification" not in st.session_state:
                st.session_state["sync_notification"] = msg
                st.session_state["sync_notification_time"] = dt.datetime.now()
    else:
        # Fallback para versiones sin toast
        if icon == "✅":
            st.success(msg)
        elif icon == "⚠️":
            st.warning(msg)
        else:
            st.info(msg)


# Lógica de sync


def get_coach_id_if_needed() -> Optional[int]:
    """Obtiene coach_id si el usuario actual es coach, None en caso contrario."""
    user_type = st.session_state.get("user_type")
    if user_type != "coach":
        return None

    try:

        user_id = st.session_state.get("user_id")
        db = get_db_session()
        coach = db.query(Coach).join(User).filter(User.user_id == user_id).first()
        db.close()

        return coach.coach_id if coach else None
    except Exception:
        return None


def filter_sync_results_by_coach(
    result: Dict[str, Any], coach_id: int
) -> Dict[str, Any]:
    """Filtra resultados de sync para mostrar solo eventos del coach específico."""
    if not result or not coach_id:
        return result

    # Buscar con mayúscula y minúscula
    coach_patterns = [
        f"#C{coach_id}",  # Mayúscula: #C1
        f"#c{coach_id}",  # Minúscula: #c1
        f"coach {coach_id}",  # Texto: coach 1
        f"Coach {coach_id}",  # Texto: Coach 1
    ]

    def is_coach_event(title: str) -> bool:
        """Verifica si un título pertenece al coach."""
        if not title:
            return False
        title_lower = title.lower()
        for pattern in coach_patterns:
            if pattern.lower() in title_lower:
                return True
        return False

    coach_rejected = []
    coach_warnings = []

    # Filtrar eventos rechazados
    for event in result.get("rejected_events", []):
        if is_coach_event(event.get("title", "")):
            coach_rejected.append(event)

    # Filtrar warnings
    for event in result.get("warning_events", []):
        if is_coach_event(event.get("title", "")):
            coach_warnings.append(event)

    # Devolver resultado filtrado
    filtered_result = result.copy()
    filtered_result["rejected_events"] = coach_rejected
    filtered_result["warning_events"] = coach_warnings

    return filtered_result


def build_stats_from_manual_sync(result: Dict[str, Any]) -> Dict[str, Any]:
    """Construye stats desde manual sync con filtrado por coach."""
    # Aplicar filtrado por coach si es necesario
    coach_id = get_coach_id_if_needed()
    if coach_id:
        result = filter_sync_results_by_coach(result, coach_id)

    return {
        "imported": result.get("imported", 0),
        "updated": result.get("updated", 0),
        "deleted": result.get("deleted", 0),
        "rejected": len(result.get("rejected_events", [])),
        "warnings": len(result.get("warning_events", [])),
        "sync_time": result.get("duration", 0),
    }


def build_stats_from_auto_sync(auto_status: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """DEPRECATED: Auto-sync stats no longer available"""
    # Return empty stats as auto-sync has been removed
    return None


def get_sync_stats_unified() -> Optional[Dict[str, Any]]:
    """
    Simplified sync stats - only uses manual sync data (auto-sync removed)
    """
    # Evitar bucles infinitos
    if getattr(st.session_state, "_reading_stats", False):
        return None

    st.session_state._reading_stats = True

    try:
        # Only check manual sync results
        if "last_sync_result" in st.session_state:
            result = st.session_state["last_sync_result"]
            timestamp = result.get("timestamp")

            if timestamp:
                try:
                    sync_time = dt.datetime.fromisoformat(timestamp)
                    seconds_ago = (dt.datetime.now() - sync_time).total_seconds()

                    if seconds_ago < 90:  # 90 segundos
                        return build_stats_from_manual_sync(result)
                    else:
                        # Auto-limpiar datos expirados
                        del st.session_state["last_sync_result"]
                except Exception:
                    # Si hay error, limpiar
                    if "last_sync_result" in st.session_state:
                        del st.session_state["last_sync_result"]

        # No manual sync data available
        return None

    finally:
        # Limpiar flag siempre
        if hasattr(st.session_state, "_reading_stats"):
            del st.session_state._reading_stats


# Funciones públicas


def run_sync_once(force: bool = False) -> None:
    """
    Ejecuta la sincronización completa usando force_manual_sync.
    Mantiene compatibilidad con interfaz anterior pero simplifica lógica.
    """
    # Verificar si ya se ejecutó (solo si no es forzado)
    if st.session_state.get("_synced") and not force:
        return

    st.session_state["_synced"] = True

    # Usar force_manual_sync como función principal
    with st.spinner("Sincronizando..."):
        result = force_manual_sync()

        if result["success"]:
            # Mostrar mensajes de éxito basados en resultado
            total_changes = (
                result.get("imported", 0)
                + result.get("updated", 0)
                + result.get("deleted", 0)
            )
            rejected = len(result.get("rejected_events", []))
            warnings = len(result.get("warning_events", []))

            if rejected > 0:
                _toast(f"Sync completado con {rejected} eventos rechazados", "⚠️")
            elif warnings > 0:
                _toast(f"Sync completado con {warnings} advertencias", "⚠️")
            elif total_changes > 0:
                _toast(f"Sync completado: {total_changes} cambios", "✅")
            else:
                _toast("Sync completado sin cambios", "✅")
        else:
            _toast(f"Error en sync: {result.get('error', 'Unknown')}", "❌")


# Auto-Sync Clases y funciones


# Auto-sync classes removed - migrated to webhook-based real-time sync
# Legacy manual sync functionality preserved below


# Legacy auto-sync functions - deprecated, will be removed in favor of webhooks
def start_auto_sync(interval_minutes: int = 5) -> bool:
    """DEPRECATED: Auto-sync replaced with webhook-based real-time sync"""
    logger.warning("start_auto_sync called but auto-sync has been deprecated")
    return False


def stop_auto_sync() -> bool:
    """DEPRECATED: Auto-sync replaced with webhook-based real-time sync"""
    logger.warning("stop_auto_sync called but auto-sync has been deprecated")
    return False


def get_auto_sync_status() -> Dict[str, Any]:
    """DEPRECATED: Returns empty status as auto-sync has been replaced"""
    return {
        "running": False,
        "last_sync_time": None,
        "last_sync_duration": 0,
        "total_syncs": 0,
        "successful_syncs": 0,
        "failed_syncs": 0,
        "last_error": "Auto-sync deprecated - use webhook-based sync",
        "interval_minutes": 0,
        "last_changes": None,
        "last_changes_time": None,
        "changes_notified": True,
        "last_rejected_events": [],
        "last_warning_events": [],
        "problems_timestamp": None,
    }


def is_auto_sync_running() -> bool:
    """DEPRECATED: Always returns False as auto-sync has been replaced"""
    return False


def has_pending_notifications() -> bool:
    """DEPRECATED: Always returns False as auto-sync notifications replaced with webhook notifications"""
    return False


# New manual sync function - independent of auto-sync infrastructure
def force_manual_sync() -> Dict[str, Any]:
    """Manual sync independent of auto-sync system"""

    if is_streamlit_cloud():
        print("🌐 Cloud: Simulando sync manual...")
        return {
            "success": True,
            "duration": 1.5,
            "imported": 0,
            "updated": 0,
            "deleted": 0,
            "past_updated": 0,
            "rejected_events": [],
            "warning_events": [],
            "error": None,
        }

    start_time = time.time()

    try:
        # Execute core sync functionality
        imported, updated, deleted, rejected_events, warning_events = (
            sync_calendar_to_db_with_feedback()
        )

        # Update past sessions if needed
        n_past = update_past_sessions()
        if n_past > 0:
            sync_db_to_calendar()

        duration = time.time() - start_time

        # Save sync problems using NotificationController
        save_sync_problems(rejected_events, warning_events)

        # Logging
        total_problems = len(rejected_events) + len(warning_events)
        if total_problems > 0:
            logger.warning(
                f"🔧 Manual sync completed with issues: {len(rejected_events)} rejected, {len(warning_events)} warnings"
            )
        else:
            logger.info(f"✅ Manual sync completed successfully")

        return {
            "success": True,
            "duration": duration,
            "imported": imported,
            "updated": updated,
            "deleted": deleted,
            "past_updated": n_past,
            "rejected_events": rejected_events,
            "warning_events": warning_events,
            "error": None,
        }

    except Exception as e:
        duration = time.time() - start_time

        # Clear problems on error
        save_sync_problems([], [])
        logger.error(f"❌ Manual sync error: {e}")

        return {
            "success": False,
            "duration": duration,
            "rejected_events": [],
            "warning_events": [],
            "error": str(e),
        }


# Legacy toast function removed - replaced with webhook-based notifications

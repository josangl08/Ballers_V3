# controllers/sync_coordinator.py
"""
Coordinador de sincronización - gestiona auto-sync, locks y estadísticas.
Anteriormente: sync.py
"""

import datetime as dt
import logging
import threading
import time
from typing import Any, Dict, Optional

import schedule

from controllers.db import get_db_session
from controllers.notification_controller import save_sync_problems
from models import Coach, User

from .calendar_sync_core import sync_calendar_to_db_with_feedback, sync_db_to_calendar
from .session_controller import update_past_sessions

# Completamente migrado a Dash


logger = logging.getLogger(__name__)

# Variable global para almacenar último mensaje de sync (para callbacks de Dash)
_last_sync_message = {"message": "", "icon": "", "timestamp": None}


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
    """Muestra un mensaje flotante - MIGRADO A DASH."""
    # En Dash, los mensajes se manejan a través de callback returns y alerts
    # Esta función ahora solo registra el mensaje para uso interno
    logger.info(f"Sync message: {icon} {msg}")

    # Almacenar mensaje para callbacks de Dash (usando variable global temporal)
    global _last_sync_message
    _last_sync_message = {"message": msg, "icon": icon, "timestamp": dt.datetime.now()}


# Lógica de sync


def get_coach_id_if_needed(session_data: Optional[Dict] = None) -> Optional[int]:
    """Obtiene coach_id si el usuario actual es coach, None en caso contrario."""
    if not session_data:
        logger.warning("get_coach_id_if_needed called without session_data")
        return None

    user_type = session_data.get("user_type")
    if user_type != "coach":
        return None

    try:
        user_id = session_data.get("user_id")
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


def get_sync_stats_unified(
    session_data: Optional[Dict] = None,
) -> Optional[Dict[str, Any]]:
    """
    Simplified sync stats - only uses manual sync data (auto-sync removed) - MIGRADO A DASH.  # noqa: E501
    """
    # En Dash, los stats se manejan via stores y callbacks
    # Esta función ahora usa el último mensaje de sync almacenado globalmente

    global _last_sync_message

    if not _last_sync_message.get("timestamp"):
        return None

    # Verificar si el mensaje es reciente (90 segundos)
    timestamp = _last_sync_message["timestamp"]
    seconds_ago = (dt.datetime.now() - timestamp).total_seconds()

    if seconds_ago < 90:
        # Construir stats básicos desde el mensaje
        message = _last_sync_message["message"]
        icon = _last_sync_message["icon"]

        # Extraer información básica del mensaje para stats
        changes = 0
        warnings = 0
        rejected = 0

        if "cambios" in message.lower():
            # Intentar extraer número de cambios del mensaje
            import re

            match = re.search(r"(\d+)\s+cambios", message.lower())
            if match:
                changes = int(match.group(1))

        if "advertencias" in message.lower() or icon == "⚠️":
            warnings = 1

        if "rechazados" in message.lower():
            rejected = 1

        return {
            "imported": changes if "importad" in message.lower() else 0,
            "updated": changes if "actualizad" in message.lower() else 0,
            "deleted": changes if "eliminad" in message.lower() else 0,
            "rejected": rejected,
            "warnings": warnings,
            "sync_time": 1.0,  # Tiempo estimado
        }

    return None


# Funciones públicas


def run_sync_once(
    force: bool = False, session_data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Ejecuta la sincronización completa usando force_manual_sync - MIGRADO A DASH.
    Mantiene compatibilidad con interfaz anterior pero simplifica lógica.
    """
    # En Dash, callbacks manejan la prevención de duplicados  # noqa: E501

    # Usar force_manual_sync como función principal (sin st.spinner en Dash)
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

    return result


def get_last_sync_message() -> Dict[str, Any]:
    """
    Obtiene el último mensaje de sync para callbacks de Dash.
    """
    global _last_sync_message
    return _last_sync_message.copy()


def clear_sync_message() -> None:
    """
    Limpia el mensaje de sync almacenado.
    """
    global _last_sync_message
    _last_sync_message = {"message": "", "icon": "", "timestamp": None}


# Manual sync functionality
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
                f"🔧 Manual sync completed with issues: {len(rejected_events)} rejected, {len(warning_events)} warnings"  # noqa: E501
            )
        else:
            logger.info("✅ Manual sync completed successfully")

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


# Toast function replaced with webhook-based notifications

# === THAI LEAGUE SCHEDULING ===

# Variables globales para Thai League scheduler
_thai_league_scheduler_thread = None
_thai_league_scheduler_running = False


def thai_league_weekly_job():
    """
    Job semanal que ejecuta la actualización inteligente de Thai League.
    Se ejecuta los lunes a las 9:00 AM.
    """
    try:
        logger.info("🕘 Ejecutando job semanal de Thai League")

        from controllers.thai_league_controller import ThaiLeagueController

        controller = ThaiLeagueController()
        result = controller.smart_weekly_update()

        action = result.get("action", "unknown")
        success = result.get("success", False)
        message = result.get("message", "Sin mensaje")

        if success:
            logger.info(f"✅ Thai League job exitoso: {action} - {message}")
        else:
            logger.error(f"❌ Thai League job falló: {action} - {message}")

    except Exception as e:
        logger.error(f"❌ Error crítico en Thai League job: {str(e)}")


def _run_thai_league_scheduler():
    """Ejecuta el scheduler de Thai League en background."""
    global _thai_league_scheduler_running

    logger.info("🚀 Iniciando Thai League scheduler...")

    # Programar job para lunes a las 9:00 AM
    schedule.every().monday.at("09:00").do(thai_league_weekly_job)

    _thai_league_scheduler_running = True

    while _thai_league_scheduler_running:
        try:
            schedule.run_pending()
            time.sleep(60)  # Verificar cada minuto
        except Exception as e:
            logger.error(f"Error en Thai League scheduler: {str(e)}")
            time.sleep(60)

    logger.info("🛑 Thai League scheduler detenido")


def start_thai_league_scheduler():
    """
    Inicia el scheduler de Thai League en background.

    Returns:
        bool: True si se inició correctamente
    """
    global _thai_league_scheduler_thread, _thai_league_scheduler_running

    if _thai_league_scheduler_running:
        logger.warning("Thai League scheduler ya está ejecutándose")
        return True

    try:
        _thai_league_scheduler_thread = threading.Thread(
            target=_run_thai_league_scheduler, daemon=True, name="ThaiLeagueScheduler"
        )
        _thai_league_scheduler_thread.start()

        logger.info("✅ Thai League scheduler iniciado exitosamente")
        return True

    except Exception as e:
        logger.error(f"❌ Error iniciando Thai League scheduler: {str(e)}")
        return False


def stop_thai_league_scheduler():
    """
    Detiene el scheduler de Thai League.

    Returns:
        bool: True si se detuvo correctamente
    """
    global _thai_league_scheduler_running

    if not _thai_league_scheduler_running:
        logger.warning("Thai League scheduler no está ejecutándose")
        return True

    try:
        _thai_league_scheduler_running = False
        schedule.clear()  # Limpiar jobs programados

        logger.info("✅ Thai League scheduler detenido exitosamente")
        return True

    except Exception as e:
        logger.error(f"❌ Error deteniendo Thai League scheduler: {str(e)}")
        return False


def get_thai_league_scheduler_status():
    """
    Obtiene el estado actual del Thai League scheduler.

    Returns:
        Dict con información del scheduler
    """
    return {
        "running": _thai_league_scheduler_running,
        "jobs_count": len(schedule.jobs),
        "next_run": str(schedule.next_run()) if schedule.jobs else None,
        "thread_alive": (
            _thai_league_scheduler_thread.is_alive()
            if _thai_league_scheduler_thread
            else False
        ),
    }


def force_thai_league_update():
    """
    Ejecuta manualmente la actualización de Thai League.

    Returns:
        Dict con resultado de la operación
    """
    try:
        logger.info("🔧 Ejecutando actualización manual de Thai League")

        from controllers.thai_league_controller import ThaiLeagueController

        controller = ThaiLeagueController()
        result = controller.smart_weekly_update()

        logger.info(
            f"Resultado actualización manual: {result.get('action')} - {result.get('message')}"
        )
        return result

    except Exception as e:
        error_msg = f"Error en actualización manual: {str(e)}"
        logger.error(error_msg)
        return {"action": "error", "success": False, "message": error_msg, "stats": {}}

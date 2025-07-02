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

from common.cloud_utils import is_streamlit_cloud, safe_database_operation
from controllers.db import get_db_session
from controllers.notification_controller import save_sync_problems
from models import Coach, User

from .calendar_sync_core import sync_calendar_to_db_with_feedback, sync_db_to_calendar
from .session_controller import update_past_sessions

logger = logging.getLogger(__name__)

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
    """Construye stats desde auto-sync usando datos internos de AutoSyncStats."""

    # Stats de cambios
    last_changes = auto_status.get("last_changes") or {}

    # Obtener problemas directamente de AutoSyncStats
    rejected_events = auto_status.get("last_rejected_events", [])
    warning_events = auto_status.get("last_warning_events", [])

    # Filtrar por coach si es necesario
    coach_id = get_coach_id_if_needed()
    if coach_id:
        temp_result = {
            "rejected_events": rejected_events,
            "warning_events": warning_events,
        }
        filtered_result = filter_sync_results_by_coach(temp_result, coach_id)
        rejected_count = len(filtered_result.get("rejected_events", []))
        warnings_count = len(filtered_result.get("warning_events", []))
    else:
        rejected_count = len(rejected_events)
        warnings_count = len(warning_events)

    return {
        "imported": last_changes.get("imported", 0),
        "updated": last_changes.get("updated", 0),
        "deleted": last_changes.get("deleted", 0),
        "rejected": rejected_count,
        "warnings": warnings_count,
        "sync_time": auto_status.get("last_sync_duration", 0),
    }


def get_sync_stats_unified() -> Optional[Dict[str, Any]]:
    """
    Reemplaza la compleja get_last_sync_stats() de menu.py
    """
    # Evitar bucles infinitos
    if getattr(st.session_state, "_reading_stats", False):
        return None

    st.session_state._reading_stats = True

    try:
        manual_stats = None
        auto_stats = None

        # Fuente 1: Manual sync (más reciente)
        if "last_sync_result" in st.session_state:
            result = st.session_state["last_sync_result"]
            timestamp = result.get("timestamp")

            if timestamp:
                try:
                    sync_time = dt.datetime.fromisoformat(timestamp)
                    seconds_ago = (dt.datetime.now() - sync_time).total_seconds()

                    if seconds_ago < 90:  # 90 segundos
                        manual_stats = build_stats_from_manual_sync(result)
                    else:
                        # Auto-limpiar datos expirados
                        del st.session_state["last_sync_result"]
                except Exception:
                    # Si hay error, limpiar
                    if "last_sync_result" in st.session_state:
                        del st.session_state["last_sync_result"]

        # Fuente 2: Auto-sync - con validación
        if not manual_stats:
            try:
                auto_status = get_auto_sync_status()
                last_sync_time = auto_status.get("last_sync_time")

                # Verificar que auto-sync tenga datos válidos
                if last_sync_time and auto_status.get("last_sync_duration", 0) > 0:
                    last_sync = dt.datetime.fromisoformat(last_sync_time)
                    time_since_sync = (dt.datetime.now() - last_sync).total_seconds()

                    if time_since_sync < 300:  # 5 minutos
                        auto_stats = build_stats_from_auto_sync(auto_status)

                        # Validar que auto_stats tenga datos útiles
                        if auto_stats:
                            total_data = (
                                auto_stats["imported"]
                                + auto_stats["updated"]
                                + auto_stats["deleted"]
                                + auto_stats["rejected"]
                                + auto_stats["warnings"]
                            )

                            # Si auto-sync solo tiene duración pero no datos, ignorar
                            if total_data == 0:
                                auto_stats = None

            except Exception:
                auto_stats = None

        # Decidir cuál usar - priorizar manual si ambos tienen datos
        if manual_stats and auto_stats:
            manual_total = sum(
                [
                    manual_stats["imported"],
                    manual_stats["updated"],
                    manual_stats["deleted"],
                    manual_stats["rejected"],
                    manual_stats["warnings"],
                ]
            )
            auto_total = sum(
                [
                    auto_stats["imported"],
                    auto_stats["updated"],
                    auto_stats["deleted"],
                    auto_stats["rejected"],
                    auto_stats["warnings"],
                ]
            )

            return manual_stats if manual_total >= auto_total else auto_stats

        return manual_stats or auto_stats

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


@dataclass
class AutoSyncStats:
    """Estadísticas de auto-sync (simple)"""

    running: bool = False
    last_sync_time: Optional[str] = None
    last_sync_duration: float = 0.0
    total_syncs: int = 0
    successful_syncs: int = 0
    failed_syncs: int = 0
    last_error: Optional[str] = None
    interval_minutes: int = 5
    last_changes: Optional[Dict[str, int]] = None
    last_changes_time: Optional[str] = None
    changes_notified: bool = True
    _last_problems: Optional[str] = None
    last_rejected_events: List[Dict[str, Any]] = field(default_factory=list)
    last_warning_events: List[Dict[str, Any]] = field(default_factory=list)
    problems_timestamp: Optional[str] = None


class SimpleAutoSync:
    """Auto-sync simple sin warnings de Streamlit"""

    def __init__(self):
        self.stats = AutoSyncStats()
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._sync_in_progress = False
        self._stats_lock = threading.Lock()

    def start(self, interval_minutes: int = 5) -> bool:
        """Inicia auto-sync - CON PROTECCIÓN CLOUD"""

        if is_streamlit_cloud():
            # En Cloud: no iniciar thread real
            print("🌐 Cloud: Auto-sync no iniciado (modo demo)")
            self.stats.running = False  # Simular que no está corriendo
            return True

        # En local: código original
        if self.stats.running:
            return False

        self.stats.running = True
        self.stats.interval_minutes = interval_minutes
        self._stop_event.clear()

        self.thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.thread.start()

        return True

    def stop(self) -> bool:
        """Detiene auto-sync"""

        if is_streamlit_cloud():
            # En Cloud: simular parada
            self.stats.running = False
            return True

        # En local: código original
        if not self.stats.running:
            return False

        self.stats.running = False
        self._stop_event.set()

        if self.thread:
            self.thread.join(timeout=5)

        return True

    def force_sync(self) -> Dict[str, Any]:
        """Sync manual usando versión UI normal - CON PROTECCIÓN CLOUD"""

        if is_streamlit_cloud():
            # En Cloud: simular sync sin escribir a BD
            print("🌐 Cloud: Simulando force_sync...")

            return {
                "success": True,
                "duration": 2.0,
                "imported": 0,
                "updated": 0,
                "deleted": 0,
                "past_updated": 0,
                "rejected_events": [],
                "warning_events": [],
                "error": None,
            }

        # En local: código original completo
        start_time = time.time()

        try:
            # Para sync manual, usar función que devuelve estadísticas
            imported, updated, deleted, rejected_events, warning_events = (
                sync_calendar_to_db_with_feedback()
            )

            # Actualizar sesiones pasadas si es necesario
            n_past = update_past_sessions()
            if n_past > 0:
                sync_db_to_calendar()

            duration = time.time() - start_time

            _auto_sync.stats.total_syncs += 1
            _auto_sync.stats.successful_syncs += 1
            _auto_sync.stats.last_sync_time = dt.datetime.now().isoformat()
            _auto_sync.stats.last_sync_duration = duration
            _auto_sync.stats.last_error = None

            # CRÍTICO: SIEMPRE guardar problemas del sync actual (incluso si está vacío)
            save_sync_problems(rejected_events, warning_events)

            # LOGGING PRECISO para manual sync
            total_problems = len(rejected_events) + len(warning_events)
            if total_problems > 0:
                logger.warning(
                    f"🔧 Manual sync completado con problemas: {len(rejected_events)} rechazados, {len(warning_events)} warnings"
                )
            else:
                logger.info(f"✅ Manual sync completado sin problemas")

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

            _auto_sync.stats.total_syncs += 1
            _auto_sync.stats.failed_syncs += 1
            _auto_sync.stats.last_error = str(e)

            # LIMPIAR problemas en caso de error
            save_sync_problems([], [])
            logger.error(f"❌ Error manual sync: {e}")

            return {
                "success": False,
                "duration": duration,
                "rejected_events": [],
                "warning_events": [],
                "error": str(e),
            }

    def get_status(self) -> Dict[str, Any]:
        """Estado actual"""
        with self._stats_lock:
            return asdict(self.stats)

    def _sync_loop(self):
        """Loop con detección de cambios para notificaciones"""
        while not self._stop_event.is_set():
            try:
                start_time = time.time()

                # Ejecutar sync y capturar cambios
                imported, updated, deleted, rejected_events, warning_events = (
                    sync_calendar_to_db_with_feedback()
                )

                duration = time.time() - start_time

                # Actualizar estadísticas
                self.stats.total_syncs += 1
                self.stats.successful_syncs += 1
                self.stats.last_sync_time = dt.datetime.now().isoformat()
                self.stats.last_sync_duration = duration
                self.stats.last_error = None

                # Guardar problemas en AutoSyncStats
                self.stats.last_rejected_events = rejected_events
                self.stats.last_warning_events = warning_events
                self.stats.problems_timestamp = dt.datetime.now().strftime(
                    "%d/%m/%Y %H:%M:%S"
                )

                # Guardar también en session_state para página de settings
                save_sync_problems(rejected_events, warning_events)

                # Detectar y guardar cambios para notificaciones
                total_changes = imported + updated + deleted
                total_problems = len(rejected_events) + len(warning_events)

                if total_changes > 0:
                    # Hay cambios → guardar para notificación
                    self.stats.last_changes = {
                        "imported": imported,
                        "updated": updated,
                        "deleted": deleted,
                    }
                    self.stats.last_changes_time = dt.datetime.now().isoformat()
                    self.stats.changes_notified = (
                        False  # Marcar como pendiente de notificar
                    )
                    logger.info(
                        f"🔔 Auto-sync detectó cambios: {imported}+{updated}+{deleted}"
                    )
                else:
                    # Sin cambios → no notificar
                    self.stats.last_changes = {
                        "imported": 0,
                        "updated": 0,
                        "deleted": 0,
                    }
                    self.stats.changes_notified = True

                # Log solo si hay cambios o es diferente al anterior
                current_problems = f"{len(rejected_events)}+{len(warning_events)}"
                if rejected_events or warning_events:
                    if self.stats._last_problems != current_problems:
                        logger.warning(
                            f"🚨 Auto-sync detectó problemas: {len(rejected_events)} rechazados, {len(warning_events)} warnings"
                        )
                        self.stats._last_problems = current_problems
                else:
                    self.stats._last_problems = None

                # Loggings consistentes
                if total_problems > 0:
                    logger.warning(
                        f"⚠️ Auto-sync completado con problemas en {duration:.1f}s: {imported}+{updated}+{deleted}"
                    )
                else:
                    logger.info(
                        f"✅ Auto-sync OK en {duration:.1f}s: {imported}+{updated}+{deleted}"
                    )

            except Exception as e:
                self.stats.total_syncs += 1
                self.stats.failed_syncs += 1
                self.stats.last_error = str(e)
                self.stats.changes_notified = True

                # Limpiar problemas en caso de error
                self.stats.last_rejected_events = []
                self.stats.last_warning_events = []
                save_sync_problems([], [])
                logger.error(f"❌ Error auto-sync: {e}")

            # Esperar hasta próximo sync
            self._stop_event.wait(timeout=self.stats.interval_minutes * 60)


# Instancia única global
_auto_sync = SimpleAutoSync()


# Funciones públicas (mantener nombres originales)
def start_auto_sync(interval_minutes: int = 5) -> bool:
    """Inicia auto-sync - CON PROTECCIÓN CLOUD"""

    if is_streamlit_cloud():
        # En Cloud: simular que se inició pero no hacer nada
        print("🌐 Cloud: Auto-sync simulado (modo demo)")
        return True

    # En local: auto-sync real
    return _auto_sync.start(interval_minutes)


def stop_auto_sync() -> bool:
    """Detiene auto-sync - CON PROTECCIÓN CLOUD"""

    if is_streamlit_cloud():
        # En Cloud: simular parada
        print("🌐 Cloud: Auto-sync detenido (modo demo)")
        return True

    # En local: parar auto-sync real
    return _auto_sync.stop()


def get_auto_sync_status() -> Dict[str, Any]:
    """Estado del auto-sync - CON DATOS SIMULADOS PARA CLOUD"""

    if is_streamlit_cloud():
        # En Cloud: devolver estado simulado
        return {
            "running": False,
            "last_sync_time": None,
            "last_sync_duration": 0,
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "last_error": None,
            "interval_minutes": 5,
            "last_changes": None,
            "last_changes_time": None,
            "changes_notified": True,
            "last_rejected_events": [],
            "last_warning_events": [],
            "problems_timestamp": None,
        }

    # En local: estado real
    return _auto_sync.get_status()


@safe_database_operation("Manual sync")
def force_manual_sync() -> Dict[str, Any]:
    """Sync manual inmediato - CON PROTECCIÓN CLOUD"""

    if is_streamlit_cloud():
        # En Cloud: simular sync exitoso
        print("🌐 Cloud: Simulando sync manual...")

        return {
            "success": True,
            "duration": 1.5,  # Simular duración
            "imported": 0,
            "updated": 0,
            "deleted": 0,
            "past_updated": 0,
            "rejected_events": [],
            "warning_events": [],
            "error": None,
        }

    # En local: ejecutar sync real
    return _auto_sync.force_sync()


def is_auto_sync_running() -> bool:
    """Verifica si auto-sync está ejecutándose"""

    if is_streamlit_cloud():
        # En Cloud: simular que no está corriendo
        return False

    # En local: estado real
    return _auto_sync.stats.running


def has_pending_notifications() -> bool:
    """Verifica si hay notificaciones pendientes"""
    global _auto_sync

    # Verificar si los atributos existen antes de usarlos
    if not hasattr(_auto_sync.stats, "changes_notified"):
        return False
    if not hasattr(_auto_sync.stats, "last_changes"):
        return False

    return (
        not _auto_sync.stats.changes_notified
        and _auto_sync.stats.last_changes is not None
    )


# Función para crear mensaje de toast inteligente
def show_toast_if_needed(self):
    """Muestra toast si hay cambios pendientes"""
    if self.stats.last_changes and not getattr(self.stats, "toast_shown", True):

        changes = self.stats.last_changes
        total = sum(changes.values())

        if total > 0:
            try:
                _toast(f"Auto-Sync: {total} cambios", "✅")
                self.stats.toast_shown = True  # ← Usar campo simple
            except:
                pass

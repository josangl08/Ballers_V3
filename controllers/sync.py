from __future__ import annotations

import fcntl 
import streamlit as st 
import tempfile
import os
import threading
import time
import datetime as dt
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import streamlit as st
import logging
from common.notifications import save_sync_problems, clear_sync_problems
from controllers.calendar_controller import sync_calendar_to_db, update_past_sessions, sync_db_to_calendar, sync_calendar_to_db_with_feedback
from controllers.sheets_controller import get_accounting_df 

logger = logging.getLogger(__name__)

# Internal helpers -----------------------------------------------------------

SYNC_LOCK_FILE = os.path.join(tempfile.gettempdir(), "ballers_sync.lock")

def _acquire_sync_lock():
    """Adquiere lock de archivo para sync exclusivo"""
    try:
        lock_file = open(SYNC_LOCK_FILE, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_file
    except (IOError, OSError):
        return None

def _release_sync_lock(lock_file):
    """Libera lock de archivo"""
    if lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
            if os.path.exists(SYNC_LOCK_FILE):
                os.remove(SYNC_LOCK_FILE)
        except:
            pass
   
def _toast(msg: str, icon: str = "") -> None:
    """Muestra un mensaje flotante con duración extendida."""
    if hasattr(st, "toast"):
        # 🔧 FIX: Aumentar duración de toast a 5 segundos
        st.toast(msg, icon=icon)
        # Nota: Streamlit no permite configurar duración directamente,
        # pero podemos mostrar también en sidebar para notificaciones importantes
        if "Auto-Sync" in msg and ("importada" in msg or "actualizada" in msg or "eliminada" in msg):
            # Para cambios importantes, también mostrar en sidebar temporalmente
            if 'sync_notification' not in st.session_state:
                st.session_state['sync_notification'] = msg
                st.session_state['sync_notification_time'] = dt.datetime.now()
    else:
        # Fallback para versiones sin toast
        if icon == "✅":
            st.success(msg)
        elif icon == "⚠️":
            st.warning(msg)
        else:
            st.info(msg)

# — Pull de Google a BBDD ----------------------------------------------------
#   TTL 300 s = 5 minutos                                                     
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def _pull_google() -> None:
    """Sincroniza BBDD ← Google Calendar."""
    sync_calendar_to_db()

# — Push de BBDD a Google Calendar + pull final -----------------------------
def _push_local() -> None:
    """Marca sesiones pasadas como *completed*, sube cambios y refresca."""
    with st.spinner("🔄 Actualizando sesiones pasadas..."):
        n = update_past_sessions()
        if n:
            st.info(f"✅ Marcadas {n} sesiones como completadas")
        
    with st.spinner("📤 Sincronizando cambios locales..."):
        if n:
            sync_db_to_calendar()
            st.info("✅ Cambios enviados a Google Calendar")
    
    with st.spinner("📥 Descargando cambios de Calendar..."):
        sync_calendar_to_db()
        st.info("✅ Cambios descargados de Google Calendar")


def run_sync_once(force: bool = False) -> None:
    """
    Ejecuta la sincronización completa usando force_manual_sync.
    Mantiene compatibilidad con interfaz anterior pero simplifica lógica.
    
    Parameters
    ----------
    force: bool, default False
        Si se pasa True se ignora la bandera en st.session_state y se
        vuelve a sincronizar.
    """
    # Verificar si ya se ejecutó (solo si no es forzado)
    if st.session_state.get("_synced") and not force:
        return
    
    st.session_state["_synced"] = True
    
    # Usar force_manual_sync como función principal
    with st.spinner("Sincronizando..."):
        result = force_manual_sync()
        
        if result['success']:
            # Mostrar mensajes de éxito basados en resultado
            total_changes = result.get('imported', 0) + result.get('updated', 0) + result.get('deleted', 0)
            rejected = len(result.get('rejected_events', []))
            warnings = len(result.get('warning_events', []))
            
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

# Auto-Sync Classes and Functions ------------------------------------------

    
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

class SimpleAutoSync:
    """Auto-sync simple sin warnings de Streamlit"""
    
    def __init__(self):
        self.stats = AutoSyncStats()
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._sync_in_progress = False  # 🔧 Agregar flag interno
        
    def start(self, interval_minutes: int = 5) -> bool:
        """Inicia auto-sync"""
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
        if not self.stats.running:
            return False
            
        self.stats.running = False
        self._stop_event.set()
        
        if self.thread:
            self.thread.join(timeout=5)
            
        return True
    
    def force_sync(self) -> Dict[str, Any]:
        """🔧 FIX: Sync manual usando versión UI normal"""
        start_time = time.time()
        
        try:
            # Para sync manual, usar función que devuelve estadísticas
            imported, updated, deleted, rejected_events, warning_events = sync_calendar_to_db_with_feedback()
            
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

            # 🔧 CRÍTICO: SIEMPRE guardar problemas del sync actual (incluso si está vacío)
            save_sync_problems(rejected_events, warning_events)
            
            # 🔧 LOGGING PRECISO para manual sync
            total_problems = len(rejected_events) + len(warning_events)
            if total_problems > 0:
                print(f"🔧 Manual sync completado con problemas: {len(rejected_events)} rechazados, {len(warning_events)} warnings")
            else:
                print(f"✅ Manual sync completado sin problemas")
            
            return {
                "success": True,
                "duration": duration,
                "imported": imported,
                "updated": updated, 
                "deleted": deleted,
                "past_updated": n_past,
                "rejected_events": rejected_events,      
                "warning_events": warning_events,    
                "error": None
            }
            
        except Exception as e:
            duration = time.time() - start_time
            
            _auto_sync.stats.total_syncs += 1
            _auto_sync.stats.failed_syncs += 1
            _auto_sync.stats.last_error = str(e)

            # 🔧 LIMPIAR problemas en caso de error
            save_sync_problems([], [])
            print(f"❌ Error manual sync: {e}")
            
            return {
                "success": False,
                "duration": duration,
                "rejected_events": [],
                "warning_events": [],
                "error": str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Estado actual"""
        return asdict(self.stats)       

    def _sync_loop(self):
        """ Loop con detección de cambios para notificaciones"""
        while not self._stop_event.is_set():
            try:
                start_time = time.time()

                # Ejecutar sync y capturar cambios
                imported, updated, deleted, rejected_events, warning_events = sync_calendar_to_db_with_feedback()
            
                duration = time.time() - start_time
                    
                # Actualizar estadísticas
                self.stats.total_syncs += 1
                self.stats.successful_syncs += 1
                self.stats.last_sync_time = dt.datetime.now().isoformat()
                self.stats.last_sync_duration = duration
                self.stats.last_error = None
                    
                # Detectar y guardar cambios para notificaciones
                total_changes = imported + updated + deleted
                total_problems = len(rejected_events) + len(warning_events)

                if total_changes > 0:
                    # Hay cambios → guardar para notificación
                    self.stats.last_changes = {
                        "imported": imported,
                        "updated": updated, 
                        "deleted": deleted
                    }
                    self.stats.last_changes_time = dt.datetime.now().isoformat()
                    self.stats.changes_notified = False  # Marcar como pendiente de notificar
                        
                    print(f"🔔 Auto-sync detectó cambios: {imported}+{updated}+{deleted}")
                else:
                    # Sin cambios → no notificar
                    self.stats.changes_notified = True
                
                # Crear estadísticas para auto-sync
                sync_stats = {
                    'imported': imported,
                    'updated': updated,
                    'deleted': deleted,
                    'duration': duration,
                    'past_updated': 0  # Auto-sync no actualiza past sessions
                }
                
                # Guardar problemas automáticamente
                save_sync_problems(rejected_events, warning_events)

                # Log solo si hay cambios o es diferente al anterior
                current_problems = f"{len(rejected_events)}+{len(warning_events)}"
                if rejected_events or warning_events:
                    if not hasattr(self.stats, '_last_problems') or self.stats._last_problems != current_problems:
                        print(f"🚨 Auto-sync detectó problemas: {len(rejected_events)} rechazados, {len(warning_events)} warnings")
                        self.stats._last_problems = current_problems
                else:
                    # Limpiar flag de problemas anteriores
                    if hasattr(self.stats, '_last_problems'):
                        delattr(self.stats, '_last_problems')
                
                # 🔧 LOGGING CONSISTENTE
                if total_problems > 0:
                    print(f"⚠️ Auto-sync completado con problemas en {duration:.1f}s: {imported}+{updated}+{deleted}")
                else:
                    print(f"✅ Auto-sync OK en {duration:.1f}s: {imported}+{updated}+{deleted}")
            
            except Exception as e:
                self.stats.total_syncs += 1
                self.stats.failed_syncs += 1
                self.stats.last_error = str(e)
                self.stats.changes_notified = True
                
                # 🔧 LIMPIAR problemas en caso de error
                save_sync_problems([], [])
                print(f"❌ Error auto-sync: {e}")
        
            # Esperar hasta próximo sync
            self._stop_event.wait(timeout=self.stats.interval_minutes * 60)

# Instancia única global
_auto_sync = SimpleAutoSync()

# Funciones públicas (mantener nombres originales)
def start_auto_sync(interval_minutes: int = 5) -> bool:
    """Inicia auto-sync"""
    return _auto_sync.start(interval_minutes)

def stop_auto_sync() -> bool:
    """Detiene auto-sync"""
    return _auto_sync.stop()

def get_auto_sync_status() -> Dict[str, Any]:
    """Estado del auto-sync"""
    return _auto_sync.get_status()

def force_manual_sync() -> Dict[str, Any]:
    """Sync manual inmediato"""
    return _auto_sync.force_sync()

def is_auto_sync_running() -> bool:
    """Verifica si auto-sync está ejecutándose"""
    return _auto_sync.stats.running

# Funcion para crear mensaje de toast inteligente
def _format_changes_message(imported: int, updated: int, deleted: int) -> tuple[str, str]:
    """
    Formatea mensaje de toast basado en tipos de cambios.
    Returns: (message, icon)
    """
    changes = []
    
    if imported > 0:
        changes.append(f"{imported} importada{'s' if imported != 1 else ''}")
    if updated > 0:
        changes.append(f"{updated} actualizada{'s' if updated != 1 else ''}")
    if deleted > 0:
        changes.append(f"{deleted} eliminada{'s' if deleted != 1 else ''}")
    
    if not changes:
        return "", ""
    
    # Crear mensaje descriptivo
    if len(changes) == 1:
        message = f"🔄 Auto-Sync: {changes[0]}"
    elif len(changes) == 2:
        message = f"🔄 Auto-Sync: {changes[0]} y {changes[1]}"
    else:
        message = f"🔄 Auto-Sync: {', '.join(changes[:-1])} y {changes[-1]}"
    
    # Elegir icono apropiado
    if deleted > 0:
        icon = "🗑️"  # Prioridad a eliminaciones
    elif imported > 0:
        icon = "📥"  # Importaciones
    else:
        icon = "🔄"  # Solo actualizaciones
    
    return message, icon

# 🔔 FUNCIÓN pública para verificar y mostrar notificaciones
def check_and_show_autosync_notifications():
    """
    Verifica si hay cambios pendientes de notificar y muestra toast.
    Llamar desde sidebar o UI principal.
    """
    global _auto_sync
    
    # Verificar si hay cambios pendientes
    if (hasattr(_auto_sync.stats, 'changes_notified') and 
        not _auto_sync.stats.changes_notified and 
        hasattr(_auto_sync.stats, 'last_changes') and
        _auto_sync.stats.last_changes and 
        hasattr(_auto_sync.stats, 'last_changes_time') and
        _auto_sync.stats.last_changes_time):
        
        # Obtener detalles de cambios
        changes = _auto_sync.stats.last_changes
        imported = changes.get("imported", 0)
        updated = changes.get("updated", 0) 
        deleted = changes.get("deleted", 0)
        
        # Verificar que realmente hay cambios
        total_changes = imported + updated + deleted
        if total_changes > 0:
            # Crear y mostrar notificación
            message, icon = _format_changes_message(imported, updated, deleted)
            
            if message:
                # 🔔 REUTILIZAR función _toast existente
                try:
                    _toast(message, icon)
                    print(f"🔔 Toast mostrado: {message}")
                    
                except Exception as e:
                    print(f"⚠️ Error mostrando toast: {e}")
        
        # Marcar como notificado (sin importar si tuvo éxito)
        _auto_sync.stats.changes_notified = True

# 🔔 FUNCIÓN auxiliar para UI (opcional)
def has_pending_notifications() -> bool:
    """Verifica si hay notificaciones pendientes"""
    global _auto_sync
    
    # Verificar si los atributos existen antes de usarlos
    if not hasattr(_auto_sync.stats, 'changes_notified'):
        return False
    if not hasattr(_auto_sync.stats, 'last_changes'):
        return False
        
    return (not _auto_sync.stats.changes_notified and 
            _auto_sync.stats.last_changes is not None)
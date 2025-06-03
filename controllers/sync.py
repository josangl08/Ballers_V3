# controllers/sync.py - ARCHIVO COMPLETO CORREGIDO

from __future__ import annotations
"""utils/sync.py — One‑shot bidirectional synchronisation helper.

Import and call :pyfunc:`run_sync_once` **once** after el login en ``main.py``.
Mantiene la coherencia entre BBDD y Google Calendar evitando bucles y
re‑renderizados continuos gracias a Streamlit cache.
"""
import fcntl  # Para file locking
import tempfile
import os
import threading
import time
import datetime as dt
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import streamlit as st
from controllers.calendar_controller import sync_calendar_to_db, update_past_sessions, sync_db_to_calendar
from controllers.sheets_controller import get_accounting_df 

# ---------------------------------------------------------------------------
# Internal helpers -----------------------------------------------------------
# ---------------------------------------------------------------------------
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
    """Muestra un mensaje flotante o, si la versión de Streamlit no soporta
    ``st.toast()``, cae a ``st.success()``/``st.warning()``.
    """
    if hasattr(st, "toast"):
        st.toast(msg, icon=icon)
    else:
        # Selección rápida de fallback según icono
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

# 🔧 FIX: Versión SILENT de run_sync_once (sin Streamlit UI)
def run_sync_once_silent() -> tuple[int, int, int]:
    """
    Versión REALMENTE silenciosa con control de concurrencia.
    """
    # Intentar adquirir lock
    lock_file = _acquire_sync_lock()
    if not lock_file:
        print("⚠️ Sync ya en progreso, saltando...")
        return 0, 0, 0
    
    try:
        # 1. Pull Google Calendar → BD
        imported, updated, deleted = sync_calendar_to_db()
        
        # 2. Push BD → Google Calendar (solo si necesario)
        n_past = update_past_sessions()
        if n_past > 0:
            sync_db_to_calendar()
        
        # 3. NO tocar Google Sheets (evita warnings)
        
        return imported, updated, deleted
        
    except Exception as e:
        print(f"❌ Error en sync silencioso: {e}")
        return 0, 0, 0
    finally:
        # Siempre liberar lock
        _release_sync_lock(lock_file)

# ---------------------------------------------------------------------------
# Public API ----------------------------------------------------------------
# ---------------------------------------------------------------------------

def run_sync_once(force: bool = False) -> None:
    """Ejecuta la sincronización completa la **primera** vez que se llama.

    Parameters
    ----------
    force: bool, default ``False``
        Si se pasa ``True`` se ignora la bandera en ``st.session_state`` y se
        vuelve a sincronizar (útil en un botón «Refrescar»).
    """
    if st.session_state.get("_synced") and not force:
        return
    st.session_state["_synced"] = True
    # Descargar cambios de Google Calendar -----------------------------
    with st.spinner("Actualizando desde Google Calendar…"):
        try:
            _pull_google()
        except Exception as exc:  # pylint: disable=broad-except
            _toast(f"No se pudo sincronizar desde Google Calendar: {exc}", "⚠️")
        else:
            _toast("Google Calendar actualizado", "✅")

    # Subir cambios locales y refrescar --------------------------------
    with st.spinner("Sincronizando base de datos…"):
        try:
            _push_local()
        except Exception as exc:  # pylint: disable=broad-except
            _toast(f"No se pudo sincronizar la base de datos: {exc}", "⚠️")
        else:
            _toast("Base de datos actualizada", "✅")
    # Google Sheets ---------------------------------------------------
    with st.spinner("Actualizando Google Sheets…"):
        try:
            get_accounting_df.clear()      # invalida la caché de 5 min
            get_accounting_df()            # recarga y deja el DataFrame en cache
        except Exception as exc:           # pylint: disable=broad-except
            _toast(f"No se pudo sincronizar Google Sheets: {exc}", "⚠️")
        else:
            _toast("Google Sheets actualizado", "✅")

    st.session_state["_synced"] = True

# ---------------------------------------------------------------------------
# Auto-Sync Classes and Functions ------------------------------------------
# ---------------------------------------------------------------------------
    
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
    last_changes: Optional[Dict[str, int]] = None  # {"imported": 0, "updated": 1, "deleted": 0}
    last_changes_time: Optional[str] = None        # Timestamp para evitar duplicados
    changes_notified: bool = True   

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
            # Para sync manual, usar versión con UI
            run_sync_once(force=True)
            
            duration = time.time() - start_time
            
            self.stats.total_syncs += 1
            self.stats.successful_syncs += 1
            self.stats.last_sync_time = dt.datetime.now().isoformat()
            self.stats.last_sync_duration = duration
            self.stats.last_error = None
            
            return {
                "success": True,
                "duration": duration,
                "error": None
            }
            
        except Exception as e:
            duration = time.time() - start_time
            
            self.stats.total_syncs += 1
            self.stats.failed_syncs += 1
            self.stats.last_error = str(e)
            
            return {
                "success": False,
                "duration": duration,
                "error": str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Estado actual"""
        return asdict(self.stats)       

    def _sync_loop(self):
        """🔔 MODIFICADO: Loop con detección de cambios para notificaciones"""
        while not self._stop_event.is_set():
            try:
                start_time = time.time()
                
                # Ejecutar sync y capturar cambios
                imported, updated, deleted = run_sync_once_silent()
                
                duration = time.time() - start_time
                
                # Actualizar estadísticas
                self.stats.total_syncs += 1
                self.stats.successful_syncs += 1
                self.stats.last_sync_time = dt.datetime.now().isoformat()
                self.stats.last_sync_duration = duration
                self.stats.last_error = None
                
                # 🔔 NUEVO: Detectar y guardar cambios para notificaciones
                total_changes = imported + updated + deleted
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
                
                print(f"✅ Auto-sync OK en {duration:.1f}s: {imported}+{updated}+{deleted}")
                
            except Exception as e:
                self.stats.total_syncs += 1
                self.stats.failed_syncs += 1
                self.stats.last_error = str(e)
                self.stats.changes_notified = True  # No notificar errores por toast
                print(f"❌ Error auto-sync: {e}")
            
            # Esperar hasta próximo sync
            self._stop_event.wait(timeout=self.stats.interval_minutes * 60)

# 🔧 FIX: Instancia única global
_auto_sync = SimpleAutoSync()

# 🔧 FIX: Funciones públicas (mantener nombres originales)
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

# 🔔 FUNCIÓN para crear mensaje de toast inteligente
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
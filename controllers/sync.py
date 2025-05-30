from __future__ import annotations
"""utils/sync.py — One‑shot bidirectional synchronisation helper.

Import and call :pyfunc:`run_sync_once` **once** after el login en ``main.py``.
Mantiene la coherencia entre BBDD y Google Calendar evitando bucles y
re‑renderizados continuos gracias a Streamlit cache.
"""

import streamlit as st
from controllers.calendar_controller import sync_calendar_to_db, update_past_sessions, sync_db_to_calendar
from controllers.sheets_controller import get_accounting_df 
# ---------------------------------------------------------------------------
# Internal helpers -----------------------------------------------------------
# ---------------------------------------------------------------------------

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

# — Pull de Google a BBDD ----------------------------------------------------
#   TTL 300 s = 5 minutos                                                     
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def _pull_google() -> None:
    """Sincroniza BBDD ← Google Calendar."""
    sync_calendar_to_db()

# — Push de BBDD a Google Calendar + pull final -----------------------------
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
    if st.session_state.get("_synced"):
        return
    st.session_state["_synced"] = True
    # Descargar cambios de Google Calendar -----------------------------
    with st.spinner("Actualizando desde Google Calendar…"):
        try:
            _pull_google()
        except Exception as exc:  # pylint: disable=broad-except
            _toast(f"No se pudo sincronizar desde Google Calendar: {exc}", "⚠️")
        else:
            _toast("Google Calendar actualizado", "✅")

    # Subir cambios locales y refrescar --------------------------------
    with st.spinner("Sincronizando base de datos…"):
        try:
            _push_local()
        except Exception as exc:  # pylint: disable=broad-except
            _toast(f"No se pudo sincronizar la base de datos: {exc}", "⚠️")
        else:
            _toast("Base de datos actualizada", "✅")
    # Google Sheets ---------------------------------------------------
    with st.spinner("Actualizando Google Sheets…"):
        try:
            get_accounting_df.clear()      # invalida la caché de 5 min
            get_accounting_df()            # recarga y deja el DataFrame en cache
        except Exception as exc:           # pylint: disable=broad-except
            _toast(f"No se pudo sincronizar Google Sheets: {exc}", "⚠️")
        else:
            _toast("Google Sheets actualizado", "✅")

    st.session_state["_synced"] = True
    
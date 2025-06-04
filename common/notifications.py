# common/notifications.py
"""
Sistema de notificaciones persistentes para problemas de sincronización.
Solo muestra mensajes cuando hay problemas (rechazados o warnings).
"""
import streamlit as st
import datetime as dt
from typing import List, Dict, Any, Optional


def save_sync_problems(rejected_events: List[Dict], warning_events: List[Dict]) -> None:
    """
    Guarda problemas de sincronización de forma persistente.
    Solo se guardan si hay problemas reales.
    
    Args:
        rejected_events: Lista de eventos rechazados
        warning_events: Lista de eventos con warnings
    """
    # Solo guardar si hay problemas
    if not rejected_events and not warning_events:
        clear_sync_problems()  # Limpiar problemas previos si todo está OK
        return
    
    # Guardar con timestamp
    st.session_state['sync_problems'] = {
        'rejected': rejected_events,
        'warnings': warning_events,
        'timestamp': dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'seen': False  # Para tracking si el usuario ya vio los problemas
    }
    
    # Actualizar también las claves legacy para compatibilidad
    st.session_state['last_rejected_events'] = rejected_events
    st.session_state['last_warning_events'] = warning_events
    st.session_state['last_sync_time'] = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def get_sync_problems() -> Optional[Dict[str, Any]]:
    """
    Obtiene problemas de sincronización guardados.
    
    Returns:
        Dict con rejected, warnings, timestamp y seen, o None si no hay problemas
    """
    return st.session_state.get('sync_problems', None)


def has_sync_problems() -> bool:
    """
    Verifica si hay problemas de sincronización pendientes.
    
    Returns:
        True si hay problemas rechazados o warnings
    """
    problems = get_sync_problems()
    if not problems:
        return False
    
    return bool(problems.get('rejected') or problems.get('warnings'))


def mark_problems_as_seen() -> None:
    """
    Marca los problemas como vistos por el usuario.
    Útil para dashboard que muestra todos los detalles.
    """
    if 'sync_problems' in st.session_state:
        st.session_state['sync_problems']['seen'] = True


def clear_sync_problems() -> None:
    """
    Limpia todos los problemas guardados.
    """
    keys_to_remove = [
        'sync_problems',
        'last_rejected_events', 
        'last_warning_events', 
        'last_sync_time'
    ]
    
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]


def show_sync_problems_compact(location: str = "settings") -> bool:
    """
    Muestra problemas de sync de forma compacta.
    
    Args:
        location: Dónde se muestra ("settings", "sidebar", "dashboard")
        
    Returns:
        True si se mostraron problemas, False si no hay
    """
    problems = get_sync_problems()
    
    if not problems:
        return False
    
    rejected = problems.get('rejected', [])
    warnings = problems.get('warnings', [])
    timestamp = problems.get('timestamp', '')
    
    # Título con timestamp
    title_suffix = f" ({timestamp})" if timestamp else ""
    
    # 🚫 EVENTOS RECHAZADOS (prioridad alta)
    if rejected:
        st.error(f"❌ {len(rejected)} eventos rechazados{title_suffix}")
        
        # Mostrar solo el primero en vista compacta
        if location in ["settings", "sidebar"]:
            first_rejected = rejected[0]
            with st.expander(f"🚫 {first_rejected['title']}", expanded=False):
                st.write(f"**📅 Fecha**: {first_rejected.get('date', 'N/A')}")
                st.write(f"**🕐 Horario**: {first_rejected.get('time', 'N/A')}")
                st.write(f"**❌ Problema**: {first_rejected['reason']}")
                st.write(f"**💡 Solución**: {first_rejected['suggestion']}")
            
            if len(rejected) > 1:
                st.info(f"+ {len(rejected) - 1} eventos rechazados más")
        
        # Vista completa para dashboard
        elif location == "dashboard":
            for i, event in enumerate(rejected):
                with st.expander(f"🚫 {event['title']} - {event.get('date', 'N/A')}", expanded=(i==0)):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**📅 Fecha**: {event.get('date', 'N/A')}")
                        st.write(f"**🕐 Horario**: {event.get('time', 'N/A')}")
                        st.write(f"**❌ Problema**: {event['reason']}")
                        st.write(f"**💡 Solución**: {event['suggestion']}")
                    
                    with col2:
                        if st.button("🔗 Calendar", key=f"cal_rej_{i}", help="Abrir Google Calendar"):
                            st.link_button("📅 Google Calendar", "https://calendar.google.com")
    
    # ⚠️ EVENTOS CON WARNINGS (solo si no hay rechazados o en dashboard)
    elif warnings or location == "dashboard":
        if warnings:
            st.warning(f"⚠️ {len(warnings)} eventos con advertencias{title_suffix}")
            
            # Mostrar solo el primero en vista compacta
            if location in ["settings", "sidebar"]:
                first_warning = warnings[0]
                with st.expander(f"⚠️ {first_warning['title']}", expanded=False):
                    st.write(f"**📅 Fecha**: {first_warning.get('date', 'N/A')}")
                    st.write(f"**🕐 Horario**: {first_warning.get('time', 'N/A')}")
                    st.write("**⚠️ Advertencias**:")
                    for warning in first_warning.get('warnings', []):
                        st.write(f"• {warning}")
                    st.info("💡 Sesión importada correctamente")
                
                if len(warnings) > 1:
                    st.info(f"+ {len(warnings) - 1} eventos con advertencias más")
            
            # Vista completa para dashboard
            elif location == "dashboard":
                for i, event in enumerate(warnings):
                    with st.expander(f"⚠️ {event['title']} - {event.get('date', 'N/A')}", expanded=False):
                        st.write(f"**📅 Fecha**: {event.get('date', 'N/A')}")
                        st.write(f"**🕐 Horario**: {event.get('time', 'N/A')}")
                        st.write("**⚠️ Advertencias**:")
                        for warning in event.get('warnings', []):
                            st.write(f"• {warning}")
                        st.info("💡 Sesión importada correctamente")
    
    # Botón para limpiar (solo en settings)
    if location == "settings":
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🧹 Marcar como visto", help="Ocultar estos problemas", key=f"clear_problems_{location}"):
                clear_sync_problems()
                st.rerun()
    
    # Link a dashboard completo (solo si no estamos ya en dashboard)
    if location != "dashboard" and (rejected or warnings):
        st.info("💡 **Tip**: Ve a Administration → 🚨 Sync Problems para gestionar todos los problemas.")
    
    return True


def show_sidebar_alert() -> bool:
    """
    Muestra alerta compacta en sidebar.
    Solo muestra si hay problemas sin ver.
    
    Returns:
        True si se mostró alerta, False si no
    """
    problems = get_sync_problems()
    
    if not problems:
        return False
    
    rejected = problems.get('rejected', [])
    warnings = problems.get('warnings', [])
    seen = problems.get('seen', False)
    
    # Solo mostrar alerta si no se han visto los problemas
    if seen:
        return False
    
    # 🚫 ALERTAS CRÍTICAS (rechazados) - prioridad
    if rejected:
        st.error(f"🚫 {len(rejected)} eventos rechazados")
        if st.button("Ver detalles", key="sidebar_view_rejected", help="Ver eventos rechazados", use_container_width=True):
            # Marcar como visto y redirigir
            mark_problems_as_seen()
            st.session_state['show_sync_problems_tab'] = True
            st.rerun()
        return True
    
    # ⚠️ ALERTAS DE WARNINGS (solo si no hay rechazados)
    elif warnings:
        st.warning(f"⚠️ {len(warnings)} eventos con advertencias")
        if st.button("Ver advertencias", key="sidebar_view_warnings", help="Ver eventos con horarios no ideales", use_container_width=True):
            # Marcar como visto y redirigir
            mark_problems_as_seen()
            st.session_state['show_sync_problems_tab'] = True
            st.rerun()
        return True
    
    return False


def get_problems_summary() -> str:
    """
    Devuelve resumen textual de problemas para logs o mensajes.
    
    Returns:
        String con resumen, vacío si no hay problemas
    """
    problems = get_sync_problems()
    
    if not problems:
        return ""
    
    rejected = problems.get('rejected', [])
    warnings = problems.get('warnings', [])
    
    parts = []
    
    if rejected:
        parts.append(f"{len(rejected)} rechazados")
    
    if warnings:
        parts.append(f"{len(warnings)} con advertencias")
    
    if parts:
        return f"Problemas de sync: {', '.join(parts)}"
    
    return ""


def auto_cleanup_old_problems(max_age_hours: int = 24) -> None:
    """
    Limpia automáticamente problemas antiguos.
    
    Args:
        max_age_hours: Máximo tiempo en horas para mantener problemas
    """
    problems = get_sync_problems()
    
    if not problems or not problems.get('timestamp'):
        return
    
    try:
        # Parsear timestamp guardado
        problem_time = dt.datetime.strptime(problems['timestamp'], "%d/%m/%Y %H:%M:%S")
        current_time = dt.datetime.now()
        
        # Calcular diferencia en horas
        age_hours = (current_time - problem_time).total_seconds() / 3600
        
        # Limpiar si es muy antiguo
        if age_hours > max_age_hours:
            clear_sync_problems()
            
    except (ValueError, KeyError):
        # Si hay error parseando timestamp, limpiar por seguridad
        clear_sync_problems()
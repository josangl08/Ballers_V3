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
    Guarda problemas de sincronización ROBUSTAMENTE.
    """
    try:
        # Solo guardar si hay problemas reales
        if not rejected_events and not warning_events:
            # Limpiar problemas previos si todo está OK
            if 'sync_problems' in st.session_state:
                del st.session_state['sync_problems']
            print("🔍 No problems to save, cleared existing")
            return
        
        # Validar que los datos sean serializables
        import json
        
        # Test serialización antes de guardar
        test_data = {
            'rejected': rejected_events,
            'warnings': warning_events,
            'timestamp': dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'seen': False
        }
        
        # Verificar que se puede serializar a JSON
        json.dumps(test_data, default=str)  # Test serialization
        
        # Si llegamos aquí, los datos son válidos
        st.session_state['sync_problems'] = test_data
        
        print(f"🔍 SAVED: {len(rejected_events)} rejected, {len(warning_events)} warnings")
        
    except Exception as e:
        print(f"🔍 ERROR saving sync_problems: {e}")
        # Si falla guardar, al menos no crashear
        return


def get_sync_problems() -> Optional[Dict[str, Any]]:
    """
    Obtiene problemas de sincronización guardados.
    VERSIÓN ROBUSTA - manejo completo de errores
    """
    try:
        # DEBUG: Ver qué hay exactamente en session_state
        print(f"🔍 session_state keys: {list(st.session_state.keys())}")
        
        # Verificar si existe sync_problems
        if 'sync_problems' not in st.session_state:
            print("🔍 No sync_problems key found")
            return None
        
        # Obtener el valor RAW
        raw_problems = st.session_state['sync_problems']
        print(f"🔍 Raw sync_problems type: {type(raw_problems)}")
        print(f"🔍 Raw sync_problems value: {raw_problems}")
        
        # Validar que sea un dict
        if not isinstance(raw_problems, dict):
            print(f"🔍 sync_problems is not dict, is {type(raw_problems)}")
            return None
        
        # Verificar claves mínimas
        if 'rejected' not in raw_problems or 'warnings' not in raw_problems:
            print(f"🔍 Missing required keys. Available: {raw_problems.keys()}")
            return None
        
        print(f"🔍 SUCCESS: Found {len(raw_problems.get('rejected', []))} rejected, {len(raw_problems.get('warnings', []))} warnings")
        return raw_problems
        
    except Exception as e:
        print(f"🔍 Exception in get_sync_problems: {e}")
        print(f"🔍 Exception type: {type(e)}")
        
        # Si hay error, intentar limpiar datos corruptos
        try:
            if 'sync_problems' in st.session_state:
                del st.session_state['sync_problems']
                print("🔍 Cleared corrupted sync_problems")
        except:
            pass
            
        return None

def get_sync_problems_simple():
    """Versión ultra-simple sin dependencias complicadas"""
    
    # Método 1: Desde session_state simple
    try:
        problems = st.session_state.get('sync_problems')
        if problems and isinstance(problems, dict):
            return problems
    except:
        pass
    
    # Método 2: Construir desde last_sync_result si existe
    try:
        if 'last_sync_result' in st.session_state:
            result = st.session_state['last_sync_result']
            if isinstance(result, dict):
                return {
                    'rejected': result.get('rejected_events', []),
                    'warnings': result.get('warning_events', []),
                    'timestamp': result.get('timestamp', ''),
                    'seen': False
                }
    except:
        pass
    
    # Método 3: Vacío pero válido
    return {
        'rejected': [],
        'warnings': [],
        'timestamp': '',
        'seen': True
    }

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
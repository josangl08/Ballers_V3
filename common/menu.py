# common/menu.py
import streamlit as st
import re
import datetime as dt
from streamlit_option_menu import option_menu
from common.login import logout
from controllers.calendar_controller import sync_calendar_to_db
from controllers.sync import is_auto_sync_running, get_auto_sync_status, force_manual_sync, check_and_show_autosync_notifications
from common.notifications import show_sidebar_alert

def get_last_sync_stats():
    """Lee las estadísticas del último sync desde session_state"""
    if 'last_sync_result' in st.session_state:
        result = st.session_state['last_sync_result']
        
        # Verificar que sea reciente (menos de 1 minuto)
        timestamp = result.get('timestamp')
        if timestamp:
            import datetime as dt
            try:
                sync_time = dt.datetime.fromisoformat(timestamp)
                if (dt.datetime.now() - sync_time).total_seconds() > 60:
                    return None  # Más de 1 minuto, no mostrar
            except:
                pass
        
        return {
            "imported": result.get('imported', 0),
            "updated": result.get('updated', 0),
            "deleted": result.get('deleted', 0),
            "rejected": len(result.get('rejected_events', [])),
            "warnings": len(result.get('warning_events', [])),
            "sync_time": result.get('duration', 0)
        }
    return None

def show_sync_status_message(stats):
    """Muestra mensaje de sync con color apropiado"""
    # Construir texto de estadísticas
    changes = []
    if stats['imported'] > 0:
        changes.append(f"{stats['imported']}📥")
    if stats['updated'] > 0:
        changes.append(f"{stats['updated']}🔄")
    if stats['deleted'] > 0:
        changes.append(f"{stats['deleted']}🗑️")
        
    problems = []
    if stats['rejected'] > 0:
        problems.append(f"{stats['rejected']}🚫")
    if stats['warnings'] > 0:
        problems.append(f"{stats['warnings']}⚠️")
    
    # Determinar color y mensaje
    has_changes = stats['imported'] + stats['updated'] + stats['deleted'] > 0
    has_warnings = stats['warnings'] > 0
    has_rejected = stats['rejected'] > 0
    
    if has_rejected:
        # ROJO - Hay rechazados
        changes_text = " ".join(changes) if changes else ""
        problems_text = " ".join(problems)
        separator = " • " if changes_text and problems_text else ""
        message = f"Sync {stats['sync_time']:.1f}s • {changes_text}{separator}{problems_text}"
        st.error(message)
        
    elif has_warnings:
        # AMARILLO - Hay warnings
        changes_text = " ".join(changes) if changes else ""
        problems_text = " ".join(problems)
        separator = " • " if changes_text and problems_text else ""
        message = f"Sync {stats['sync_time']:.1f}s • {changes_text}{separator}{problems_text}"
        st.warning(message)
        
    elif has_changes:
        # VERDE - Hay cambios normales
        changes_text = " ".join(changes)
        message = f"Sync {stats['sync_time']:.1f}s • {changes_text}"
        st.success(message)
        
    else:
        # AZUL - Sin cambios
        message = f"Sync {stats['sync_time']:.1f}s • Sin cambios"
        st.info(message)
    
    # Mostrar enlace a detalles solo si hay problemas
    if has_rejected or has_warnings:
        user_type = st.session_state.get("user_type")
        detail_location = "Settings" if user_type == "admin" else "Administration"
        st.info(f"🔍 Ver detalles en **{detail_location}**")


def create_sidebar_menu():
    """
    Crea un menú lateral personalizado según el tipo de usuario.
    Returns:
        str: La sección seleccionada del menú.
    """
    # Verificar si hay usuario en sesión
    if "user_id" not in st.session_state:
        return None
    
    # Obtener el tipo de usuario de la sesión
    user_type: str = st.session_state.get("user_type", "player")
    user_name = st.session_state.get("name", "")
    
    # Definir opciones de menú según el tipo de usuario
    menu_options = {
        "player": {
            "options": ["Ballers"],
            "icons": ["person-badge"]
        },
        "coach": {
            "options": ["Ballers", "Administration"],
            "icons": ["people-fill", "calendar-week"]
        },
        "admin": {
            "options": ["Ballers", "Administration", "Settings"],
            "icons": ["people-fill", "calendar-week", "gear"]
        }
    }
    
    # Obtener configuración de menú para el tipo de usuario actual
    current_menu = menu_options.get(user_type) or menu_options["player"]
    
    # Crear menú
    with st.sidebar:
        try:
            st.image("assets/ballers/isotipo_white.png", width=200)
        except:
            st.write("Logo no encontrado")
        
        # Crear string personalizado para el título del menú con iconos
        menu_title = f" {user_name}    |    🔑 {user_type.capitalize()}"
        
        # Menú de opciones con título personalizado
        selected = option_menu(
            menu_title, 
            current_menu["options"],
            icons=current_menu["icons"],
            menu_icon="person-circle",
            default_index=0,
            styles={
                "container": {"padding": "1!important","margin-top": "2!important", "background-color": "#1D1B1A"},
                "icon": {"color": "#1DDD6E", "font-size": "18px"},
                "nav": {
                    "font-size": "16px",
                    "text-align": "left",
                    "margin": "0px",
                    "transition": "all 0.3s ease",
                    "--hover-color": "#333333",
                },
                "nav-link-selected": {
                    "background-color": "#333333",
                }, 
                "menu-title": {
                    "font-size": "14px",
                    "font-weight": "bold",
                    "margin-bottom": "10px",
                    "color": "#FFFFFF",
                    "text-align": "center"
                }
            }
        )
        
        # Seccion Auto-sync unificada (solo admins y coaches)
        if user_type in ["admin", "coach"]:
            st.divider()
            
            # 🎯 MOSTRAR ESTADÍSTICAS SIMPLE (temporal - usando datos del log)
            stats = get_last_sync_stats()
            if stats:
                # Formato: "1🔄 1🗑️ • 1🚫"
                changes = []
                if stats['imported'] > 0:
                    changes.append(f"{stats['imported']}📥")
                if stats['updated'] > 0:
                    changes.append(f"{stats['updated']}🔄")
                if stats['deleted'] > 0:
                    changes.append(f"{stats['deleted']}🗑️")
                    
                problems = []
                if stats['rejected'] > 0:
                    problems.append(f"{stats['rejected']}🚫")
                if stats['warnings'] > 0:
                    problems.append(f"{stats['warnings']}⚠️")
                
                # Mostrar solo si hay datos
                if changes or problems:
                    changes_text = " ".join(changes) if changes else ""
                    problems_text = " ".join(problems) if problems else ""
                    separator = " • " if changes_text and problems_text else ""
                    
                    st.markdown(f"**Last sync**: {stats['sync_time']:.1f}s • {changes_text}{separator}{problems_text}")
                    
                    # Enlace a detalles si hay problemas
                    if problems:
                        detail_location = "Settings" if user_type == "admin" else "Administration"
                        st.info(f"🔍 Ver detalles en **{detail_location}**")
            
            # 🎯 AUTO-SYNC STATUS (código existente)
            if user_type in ["admin", "coach"]:
    
                # 🎯 ÁREA DE SYNC (solo si hay datos recientes)
                stats = get_last_sync_stats()
                if stats:
                    st.divider()
                    show_sync_status_message(stats)
                    st.divider()
                
                # 🎯 AUTO-SYNC STATUS
                if is_auto_sync_running():
                    st.success("🔄 Auto-Sync: ✅")
                else:
                    st.info("🔄 Auto-Sync: ⏸️")
                
                # 🎯 QUICK SYNC
                if st.button("⚡ Quick Sync", type="primary", use_container_width=True):
                    with st.spinner("Ejecutando sync manual..."):
                        result = force_manual_sync()
                        
                        if result['success']:
                            # Guardar resultado con timestamp para que dure 1 minuto
                            import datetime as dt
                            result['timestamp'] = dt.datetime.now().isoformat()
                            st.session_state['last_sync_result'] = result
                            st.rerun()  # Refrescar para mostrar el mensaje
                        else:
                            st.error(f"❌ Error: {result['error']}")
        
        # Botón de cerrar sesión
        if st.button("📤 Log Out", key="logout_button", 
                   type="primary", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            st.session_state["show_logout_message"] = True
            st.rerun()

    return selected

def get_content_path(section):
    """
    Devuelve la ruta al módulo de contenido según la sección seleccionada.
    
    Args:
        section (str): Sección seleccionada en el menú
        
    Returns:
        str: Ruta al módulo de contenido
    """
    content_map = {
        "Ballers": "pages.ballers",
        "Administration": "pages.administration",
        "Settings": "pages.settings"
    }
    
    return content_map.get(section)

if __name__ == "__main__":
    
    # Mostrar mensaje de cierre de sesión si es necesario
    if st.session_state.get("show_logout_message"):
        st.success("Has cerrado sesión correctamente")
        del st.session_state["show_logout_message"]
    
    selected = create_sidebar_menu()
    st.title(f"Sección: {selected}")




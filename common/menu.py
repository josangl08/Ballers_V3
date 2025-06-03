# common/menu.py
import streamlit as st
import datetime as dt
from streamlit_option_menu import option_menu
from common.login import logout
from controllers.calendar_controller import sync_calendar_to_db
from controllers.sync import is_auto_sync_running, get_auto_sync_status, force_manual_sync, check_and_show_autosync_notifications

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

        if 'sync_notification' in st.session_state:
            notification_time = st.session_state.get('sync_notification_time')
            if notification_time:
                # Mostrar por 10 segundos
                elapsed = (dt.datetime.now() - notification_time).total_seconds()
                if elapsed < 10:
                    st.info(st.session_state['sync_notification'])
                else:
                    # Limpiar después de 10 segundos
                    del st.session_state['sync_notification']
                    del st.session_state['sync_notification_time']
        
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
        
        # 🔧 FIX: SECCIÓN AUTO-SYNC UNIFICADA (solo admins y coaches)
        if user_type in ["admin", "coach"]:
            
            st.divider()
            try:
                check_and_show_autosync_notifications()
            except Exception as e:
                # Fallar silenciosamente para no romper el sidebar
                pass
            # Estado del auto-sync
            if is_auto_sync_running():
                status = get_auto_sync_status()
                if status['last_sync_time']:
                    last_sync = dt.datetime.fromisoformat(status['last_sync_time'])
                    time_ago = dt.datetime.now() - last_sync
                    minutes_ago = int(time_ago.total_seconds() / 60)
                    st.success(f"🔄 Auto-Sync: ✅ ({minutes_ago}m ago)")
                else:
                    st.success("🔄 Auto-Sync: ✅")
            else:
                st.info("🔄 Auto-Sync: ⏸️")
            
            #  UN SOLO BOTÓN DE SYNC MANUAL
            
            if st.button("⚡ Quick Sync", type="primary", use_container_width=True):
                with st.spinner("Ejecutando sync manual..."):
                    result = force_manual_sync()
                    if result['success']:
                        st.success(f"✅ Sync completado en {result['duration']:.1f}s")
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
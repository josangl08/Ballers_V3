# common/menu.py
import streamlit as st
from streamlit_option_menu import option_menu
from common.login import logout
from controllers.calendar_controller import sync_calendar_to_db

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
    user_type = st.session_state.get("user_type")
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
    current_menu = menu_options.get(user_type, menu_options["player"])
    
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
        
        # Botón de cerrar sesión estilizado
        if st.button("📤 Log Out", key="logout_button", 
                   type="primary", use_container_width=True):
            # En lugar de llamar a una función callback, hacemos todo directamente aquí
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            # Agregamos una clave especial para mostrar mensaje en la siguiente ejecución
            st.session_state["show_logout_message"] = True
            
            # Usar st.rerun() directamente en el flujo principal (no en callback)
            st.rerun()

        if st.button("Bring events ← Google Calendar"):
            sync_calendar_to_db.clear()  # invalida la caché
            with st.spinner("Sincronizando con Google Calendar..."):
                imported, updated, deleted = sync_calendar_to_db()
            st.success(
                f"{imported} sesiones nuevas importadas ,  "
                f"{updated} sesiones actualizadas ,  "
                f"{deleted} sesiones eliminadas"
            )
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
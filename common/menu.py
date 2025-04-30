# common/menu.py
import streamlit as st
from streamlit_option_menu import option_menu
import os

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
        
        # Información del usuario
        st.write(f"Usuario: {st.session_state.get('name', '')}")
        st.write(f"Tipo: {user_type.capitalize()}")
        
        # Menú de opciones
        selected = option_menu(
            "Menu", 
            current_menu["options"],
            icons=current_menu["icons"],
            menu_icon="cast",
            default_index=0,
        )
        
        # Botón de cerrar sesión
        st.button("Cerrar Sesión", on_click=logout)
        
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

def logout():
    """Cierra la sesión del usuario."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.success("Has cerrado sesión correctamente")
    st.experimental_rerun()

if __name__ == "__main__":
    # Para probar el menú de forma independiente
    st.session_state["user_id"] = 1
    st.session_state["username"] = "test_user"
    st.session_state["name"] = "Test User"
    st.session_state["user_type"] = "admin"
    
    selected = create_sidebar_menu()
    st.title(f"Sección: {selected}")
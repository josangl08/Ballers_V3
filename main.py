# main.py
import streamlit as st
import importlib
import os
import sys
from pathlib import Path

# Importar configuración
from config import STYLES_DIR, APP_NAME, APP_ICON, CSS_FILE

# Importar módulos personalizados
from common.login import login_page
from common.menu import create_sidebar_menu, get_content_path
from controllers.calendar_controller import sync_calendar_to_db

# Configuración de la página
st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aplicar estilos personalizados
def load_css():
    try:
        # Asegurarse de que la carpeta existe
        os.makedirs(STYLES_DIR, exist_ok=True)
        
        # Si el archivo no existe, lo creamos
        if not os.path.exists(CSS_FILE):
            with open(CSS_FILE, "w") as f:
                f.write("""
/* Estilos básicos */
body {
    color: #333333;
    font-family: 'Roboto', sans-serif;
}

h1 {
    color: #1E88E5;
    font-weight: 700;
}

h2, h3 {
    color: #0D47A1;
    font-weight: 600;
}

.stButton>button {
    border-radius: 5px;
    font-weight: 500;
    background-color: #1E88E5;
    color: white;
}

.stButton>button:hover {
    background-color: #0D47A1;
}
                """)
            print(f"Archivo CSS creado en: {CSS_FILE}")
        
        # Leer y aplicar estilos
        with open(CSS_FILE, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
            
    except Exception as e:
        st.warning(f"No se pudo cargar el archivo de estilos: {str(e)}. Usando estilos por defecto.")
        # Aplicar estilos básicos si falla la carga del archivo
        st.markdown("""
        <style>
        body {color: #333333; font-family: 'Roboto', sans-serif;}
        h1 {color: #1E88E5; font-weight: 700;}
        h2, h3 {color: #0D47A1; font-weight: 600;}
        .stButton>button {border-radius: 5px; background-color: #1E88E5; color: white;}
        </style>
        """, unsafe_allow_html=True)

# Función principal
def main():
    
    # Comprobar si ya hay un usuario en sesión antes de configurar la página
    has_session = "user_id" in st.session_state
    
    # Cargar estilos
    load_css()
    
    # Si no hay sesión, ocultar completamente el sidebar
    if not has_session:
        # Aplicar estilo para ocultar completamente el sidebar
        st.markdown("""
        <style>
        /* Ocultar control de sidebar */
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        
        /* Ocultar sidebar completamente */
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Mostrar página de login
        login_page()
        st.stop()
    else:
    
        # Mostrar logo centrado
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("assets/ballers/logo_white.png", width=400)
       
        # Si hay sesión, mostrar menú y contenido según selección
        selected_section = create_sidebar_menu()
        
        if selected_section:
            # Obtener la ruta del módulo para la sección seleccionada
            content_module_path = get_content_path(selected_section)
            
            if content_module_path:
                try:
                    # Importar dinámicamente el módulo de contenido
                    content_module = importlib.import_module(content_module_path)
                    
                    # Ejecutar la función principal del módulo
                    if hasattr(content_module, "show_content"):
                        content_module.show_content()
                    else:
                        st.error(f"El módulo {content_module_path} no tiene la función show_content")
                except ModuleNotFoundError:
                    st.error(f"No se encontró el módulo {content_module_path}. Asegúrate de crear la estructura de directorios correcta.")
                except Exception as e:
                    st.error(f"Error al cargar el contenido: {str(e)}")
                    if os.getenv("DEBUG", "False") == "True":
                        st.exception(e)
            else:
                st.warning("Sección no implementada")
        try:
            sync_calendar_to_db()
        except Exception as e:
            st.warning(f"No se pudo sincronizar desde Google Calendar: {e}")
        try:
            sync_calendar_to_db()
        except Exception as e:     
            st.warning(f"No se pudo sincronizar la base de datos: {e}")    
            
if __name__ == "__main__":
    main()
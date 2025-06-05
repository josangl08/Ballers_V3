# common/login.py
import streamlit as st
import hashlib
from models import User
import os
import sys
from controllers.db import get_db_session
from common.utils import hash_password


# Agregar la ruta raíz al path de Python para importar config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DEBUG


def login_user(username, password):
    """Verifica credenciales de usuario y devuelve el objeto User si es válido."""
    db_session = get_db_session()
    hashed_password = hash_password(password)
    
    user = db_session.query(User).filter_by(
        username=username, 
        password_hash=hashed_password
    ).first()
    
    db_session.close()
    return user

    
    st.markdown(background_image_style, unsafe_allow_html=True)
def login_page():
    """Renderiza la página de login y gestiona la autenticación."""
    

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("assets/ballers/logo_white.png", width=400)

# Comprobar si ya hay un usuario en sesión
    if "user_id" in st.session_state and st.session_state["user_id"]:
        st.success(f"Ya has iniciado sesión como {st.session_state['username']}")
        st.button("Cerrar Sesión", on_click=logout)
        return True
    
    # Crear columnas para centrar el formulario
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Formulario de login
        with st.form("login_form"):
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            # Crear dos columnas dentro del formulario para el botón y el enlace
            btn_col, link_col = st.columns([1, 1])
            
            with btn_col:
                submit_button = st.form_submit_button("Login")
            
            with link_col:
                # Centrar verticalmente el texto "¿Olvidaste tu contraseña?"
                st.markdown("""
                <div style="height: 46px; display: flex; align-items: center; justify-content: center;">
                    <a href="#" onclick="toggleForgotPassword()">¿Olvidaste tu contraseña?</a>
                </div>
                """, unsafe_allow_html=True)
            
            if submit_button:
                if not username or not password:
                    st.error("Please enter username and password")
                    return False
                    
                user = login_user(username, password)
                
                if user:
                    # Comprobar si el usuario está activo (si existe el campo)
                    if hasattr(user, 'is_active') and not user.is_active:
                        st.error("This user is deactivated. Contact an administrator.")
                        return False
                    
                    # Guardar información de usuario en la sesión
                    st.session_state["user_id"] = user.user_id
                    st.session_state["username"] = user.username
                    st.session_state["name"] = user.name
                    st.session_state["user_type"] = user.user_type.name
                    st.session_state["permit_level"] = user.permit_level
                    
                    st.success(f"¡Bienvenido, {user.name}!")
                    st.rerun()
                    return True
                else:
                    st.error("Incorrect username or password")
                    return False
        
        # Contenedor para mostrar/ocultar info de recuperación
        with st.container():
            # Este div será mostrado/ocultado con Javascript
            st.markdown("""
            <div id="forgotPasswordInfo" style="display: none; background-color: #f9f9f9; padding: 15px; border-radius: 10px; margin-top: -10px; margin-bottom: 20px; border: 1px solid #eee;">
                <h4>Recuperación de contraseña</h4>
                <p>Contacta con un administrador para restablecer tu contraseña enviando un correo a:</p>
                <p><a href="mailto:admin@ballersapp.com?subject=Recuperación%20de%20contraseña">admin@ballersapp.com</a></p>
            </div>
            
            <script>
            function toggleForgotPassword() {
                var x = document.getElementById("forgotPasswordInfo");
                if (x.style.display === "none") {
                    x.style.display = "block";
                } else {
                    x.style.display = "none";
                }
            }
            </script>
            """, unsafe_allow_html=True)
    

def logout():
    """Cierra la sesión del usuario."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.success("Has cerrado sesión correctamente")
    st.rerun()

if __name__ == "__main__":
    login_page()
# common/login.py
import streamlit as st
import hashlib
from models import User
import os
import datetime as dt
import sys
from controllers.db import get_db_session
from common.utils import hash_password

def restore_session_from_url():
    """Restaura sesión desde parámetros de URL."""
    try:
        # No restaurar si acabamos de hacer logout
        if st.session_state.get("just_logged_out", False):
            # Limpiar flag y parámetros
            st.session_state.pop("just_logged_out", None)
            st.query_params.clear()
            return False
        
        if "auto_login" in st.query_params and "uid" in st.query_params:
            user_id = int(st.query_params["uid"][0])
            
            # Verificar que el usuario existe y está activo
            db_session = get_db_session()
            user = db_session.query(User).filter_by(user_id=user_id).first()
            db_session.close()
            
            if user and getattr(user, 'is_active', True):
                # Restaurar datos de sesión
                st.session_state["user_id"] = user.user_id
                st.session_state["username"] = user.username
                st.session_state["name"] = user.name
                st.session_state["user_type"] = user.user_type.name
                st.session_state["permit_level"] = user.permit_level
                
                return True
                
    except Exception as e:
        print(f"Error restoring session: {e}")
        # Limpiar parámetros inválidos
        st.query_params.clear()
    
    return False

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
    """Renderiza la página de login y gestiona la autenticación - CORREGIDA."""
    
    # Verificar auto-login desde URL ANTES de mostrar UI
    if restore_session_from_url():
        st.rerun()
        return True
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("assets/ballers/logo_white.png", width=400)

    # Comprobar si ya hay un usuario en sesión
    if "user_id" in st.session_state and st.session_state["user_id"]:
        st.success(f"You are already logged in as {st.session_state['username']}")
        st.button("Log Out", on_click=logout)
        return True
    
    # Crear columnas para centrar el formulario
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        
        # Formulario de login
        with st.form("login_form"):
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            # Checkbox para recordar sesión
            remember_me = st.checkbox("Remember me")
            
            submit_button = st.form_submit_button("Login", use_container_width=True)
            
            if submit_button:
                if not username or not password:
                    st.error("Please enter username and password")
                    return False
                    
                user = login_user(username, password)
                
                if user:
                    # Comprobar si el usuario está activo
                    if hasattr(user, 'is_active') and not user.is_active:
                        st.error("This user is deactivated. Contact an administrator.")
                        return False
                    
                    # Guardar información de usuario en la sesión
                    st.session_state["user_id"] = user.user_id
                    st.session_state["username"] = user.username
                    st.session_state["name"] = user.name
                    st.session_state["user_type"] = user.user_type.name
                    st.session_state["permit_level"] = user.permit_level
                    
                    # Si "Remember me", agregar parámetros a URL
                    if remember_me:
                        st.query_params.update({
                            "auto_login":"true",
                            "uid":str(user.user_id)
                        })
                    
                    st.success(f"¡Welcome, {user.name}!")
                    st.rerun()
                    return True
                else:
                    st.error("Incorrect username or password")
                    return False
        
        # Botón "¿Olvidaste tu contraseña?" FUERA del form
        forgot_password = st.button("Forgot your password??", use_container_width=True)

        # Panel de recuperación FUERA del form
        if forgot_password:
            st.session_state['show_forgot_password'] = True
            st.rerun()
        
        # Mostrar panel de recuperación si está activo
        if st.session_state.get('show_forgot_password', False):
            with st.container(border=True):
                st.subheader("🔑 Password Recovery")
                st.info("**Contact administrator to reset your password:**")
                st.markdown("📧 **Email:** admin08@ballers.com")
                st.markdown("📱 **Phone:** +34 XXX XXX XXX")
                
                recovery_email = st.text_input("Your registered email:")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📧 Send Request", key="send_recovery"):
                        if recovery_email:
                            st.success(f"Recovery request sent for: {recovery_email}")
                            st.info("You will receive instructions via email within 24 hours.")
                        else:
                            st.error("Please enter your email address.")
                
                with col2:
                    if st.button("❌ Cancel", key="cancel_recovery"):
                        st.session_state['show_forgot_password'] = False
                        st.rerun()
    

def logout():
    """Cierra la sesión del usuario."""
    # Marcar que acabamos de hacer logout
    st.session_state["just_logged_out"] = True
    # Limpiar parámetros de URL
    st.query_params.clear()

    keys_to_delete = [key for key in st.session_state.keys() if key != "just_logged_out"]
    for key in keys_to_delete:
        del st.session_state[key]
    st.success("You have successfully logged out")
    st.rerun()

if __name__ == "__main__":
    login_page()
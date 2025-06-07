# common/login.py
import streamlit as st
import os
import sys

from controllers.auth_controller import AuthController, authenticate_user, create_user_session, restore_session_from_url, clear_user_session

# Agregar la ruta raíz al path de Python para importar config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DEBUG


def login_page():
    """Renderiza la página de login - REFACTORIZADA CON CONTROLLER."""
    
    # Verificar auto-login desde URL usando controller
    success, message = restore_session_from_url()
    if success:
        print(f"Session restored: {message}")
        st.rerun()
        return True
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("assets/ballers/logo_white.png", width=400)

    # Verificar si ya hay sesión activa usando controller
    with AuthController() as auth:
        if auth.is_logged_in():
            user_data = auth.get_current_user_data()
            if user_data:
                st.success(f"You are already logged in as {user_data['username']}")
            else:
                st.success("You are already logged in")
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
                # Usar controller para autenticación
                success, message, user = authenticate_user(username, password)
                
                if success and user is not None:
                    # Usar controller para crear sesión
                    create_user_session(user, remember_me)
                    
                    st.success(message)
                    st.rerun()
                    return True
                else:
                    st.error(message)
                    return False
        
        # Botón "¿Olvidaste tu contraseña?" fuera del form
        forgot_password = st.button("Forgot your password?", use_container_width=True)

        # Panel de recuperación fuera del form
        if forgot_password:
            st.session_state['show_forgot_password'] = True
            st.rerun()
        
        # Mostrar panel de recuperación si está activo
        if st.session_state.get('show_forgot_password', False):
            with st.container(border=True):
                st.subheader("🔑 Password Recovery")
                st.info("**Contact administrator to reset your password:**")
                st.markdown("📧 **Email:** admin@ballersapp.com")
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
    """Cierra la sesión del usuario - REFACTORIZADA."""
    clear_user_session(show_message=True)
    st.rerun()


if __name__ == "__main__":
    login_page()
# common/login.py
import streamlit as st
import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, UserType, Base
import os
import sys
import base64
from datetime import datetime, timedelta

# Agregar la ruta raíz al path de Python para importar config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DATABASE_PATH, DEBUG

# Configuración de la base de datos
def get_db_session():
    """Crea y devuelve una sesión de SQLAlchemy."""
    engine = create_engine(f'sqlite:///{DATABASE_PATH}')
    Base.metadata.create_all(engine)  # Crea tablas si no existen
    Session = sessionmaker(bind=engine)
    return Session()

def hash_password(password):
    """Convierte una contraseña en un hash SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

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
def get_base64_from_image(image_path):
    """Convierte una imagen a formato base64."""
    if not os.path.isfile(image_path):
        # Si no encuentra la imagen, buscamos alternativas
        alternatives = [
            f"assets/ballers/{os.path.basename(image_path)}", 
            f"static/{os.path.basename(image_path)}",
            f"../assets/ballers/{os.path.basename(image_path)}"
        ]
        for alt_path in alternatives:
            if os.path.isfile(alt_path):
                image_path = alt_path
                break
        else:
            print(f"No se pudo encontrar la imagen de fondo: {image_path}")
            return ""
            
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def add_bg_from_image(image_path):
    """Añade una imagen de fondo usando base64."""
    base64_image = get_base64_from_image(image_path)
    if not base64_image:
        return
        
    background_image_style = f"""
    <style>
    [data-testid="stAppViewContainer"]::before {{
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: url("data:image/png;base64,{base64_image}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        opacity: 1; /* Ajusta este valor entre 0 y 1 para cambiar la transparencia */
        z-index: -1;
    }}
    </style>
    """
    
    st.markdown(background_image_style, unsafe_allow_html=True)
def login_page():
    """Renderiza la página de login y gestiona la autenticación."""
    
    # Agregar CSS personalizado para la imagen de fondo
    add_bg_from_image("assets/ballers/360_mix.png")
    st.title("Ballers App - Login")
    
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
            st.subheader("Iniciar Sesión")
            username = st.text_input("Nombre de Usuario")
            password = st.text_input("Contraseña", type="password")
            
            # Crear dos columnas dentro del formulario para el botón y el enlace
            btn_col, link_col = st.columns([1, 1])
            
            with btn_col:
                submit_button = st.form_submit_button("Iniciar Sesión")
            
            with link_col:
                # Centrar verticalmente el texto "¿Olvidaste tu contraseña?"
                st.markdown("""
                <div style="height: 46px; display: flex; align-items: center; justify-content: center;">
                    <a href="#" onclick="toggleForgotPassword()">¿Olvidaste tu contraseña?</a>
                </div>
                """, unsafe_allow_html=True)
            
            if submit_button:
                if not username or not password:
                    st.error("Por favor, introduce usuario y contraseña")
                    return False
                    
                user = login_user(username, password)
                
                if user:
                    # Comprobar si el usuario está activo (si existe el campo)
                    if hasattr(user, 'is_active') and not user.is_active:
                        st.error("Este usuario está desactivado. Contacta con un administrador.")
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
                    st.error("Usuario o contraseña incorrectos")
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
    
    # Mostrar información de usuarios en modo debug (también centrado)
    if DEBUG:
        with col2:
            with st.expander("Información de Debug"):
                st.warning("MODO DEBUG ACTIVADO - Solo para desarrollo")
                db_session = get_db_session()
                users = db_session.query(User).all()
                
                if users:
                    st.write("Usuarios disponibles:")
                    for user in users:
                        st.write(f"- Usuario: {user.username}, Tipo: {user.user_type.name}")
                else:
                    st.write("No hay usuarios en la base de datos.")
                    st.write("Ejecuta el script create_admin.py para crear un usuario administrador.")
                
                db_session.close()
    
    return False

def logout():
    """Cierra la sesión del usuario."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.success("Has cerrado sesión correctamente")
    st.rerun()

if __name__ == "__main__":
    login_page()
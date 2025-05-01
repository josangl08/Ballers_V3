# pages/settings.py
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, UserType, Coach, Player, Admin, Base
import hashlib
from datetime import datetime
import os
import shutil

def get_db_session():
    """Crea y devuelve una sesión de SQLAlchemy."""
    engine = create_engine('sqlite:///ballers_app.db')
    Base.metadata.create_all(engine)  # Crea tablas si no existen
    Session = sessionmaker(bind=engine)
    return Session()

def hash_password(password):
    """Convierte una contraseña en un hash SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def save_profile_photo(uploaded_file, username):
    """Guarda la foto de perfil y devuelve la ruta."""
    if not os.path.exists("assets/profile_photos"):
        os.makedirs("assets/profile_photos")
    
    # Generar nombre de archivo único
    file_ext = os.path.splitext(uploaded_file.name)[1]
    filename = f"{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}{file_ext}"
    file_path = os.path.join("assets/profile_photos", filename)
    
    # Guardar archivo
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path

def create_user_form():
    """Formulario para crear un nuevo usuario."""
    st.subheader("Crear Nuevo Usuario")
    
    with st.form("create_user_form"):
        # Información básica
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Nombre completo*")
            username = st.text_input("Nombre de usuario*")
            email = st.text_input("Correo electrónico*")
        
        with col2:
            password = st.text_input("Contraseña*", type="password")
            confirm_password = st.text_input("Confirmar contraseña*", type="password")
            user_type = st.selectbox("Tipo de usuario*", options=[t.name for t in UserType])
        
        # Información adicional
        phone = st.text_input("Teléfono")
        line = st.text_input("LINE ID")
        date_of_birth = st.date_input("Fecha de nacimiento", value=None)
        profile_photo = st.file_uploader("Foto de perfil", type=["jpg", "jpeg", "png"])
        
        # Información específica según el tipo de usuario
        if user_type == "coach":
            license_number = st.text_input("Número de licencia")
        elif user_type == "player":
            service_type = st.selectbox("Tipo de servicio", options=["Básico", "Premium", "Elite"])
            enrolment = st.number_input("Número de sesiones inscritas", min_value=0, value=0)
            notes = st.text_area("Notas adicionales")
        elif user_type == "admin":
            role = st.text_input("Rol interno")
            permit_level = st.number_input("Nivel de permiso", min_value=1, max_value=10, value=1)
        
        submit = st.form_submit_button("Crear Usuario")
        
        if submit:
            # Validar campos obligatorios
            if not name or not username or not email or not password or not confirm_password:
                st.error("Por favor, completa todos los campos obligatorios.")
                return
            
            # Validar contraseñas
            if password != confirm_password:
                st.error("Las contraseñas no coinciden.")
                return
            
            # Validar que el username y email no existan
            db_session = get_db_session()
            existing_username = db_session.query(User).filter_by(username=username).first()
            existing_email = db_session.query(User).filter_by(email=email).first()
            
            if existing_username:
                st.error("El nombre de usuario ya está en uso.")
                db_session.close()
                return
            
            if existing_email:
                st.error("El correo electrónico ya está en uso.")
                db_session.close()
                return
            
            # Guardar foto de perfil si se proporcionó
            profile_photo_path = "assets/default_profile.png"  # Valor por defecto
            if profile_photo:
                profile_photo_path = save_profile_photo(profile_photo, username)
            
            # Crear objeto de usuario
            new_user = User(
                username=username,
                name=name,
                password_hash=hash_password(password),
                email=email,
                phone=phone,
                line=line,
                profile_photo=profile_photo_path,
                date_of_birth=datetime.combine(date_of_birth, datetime.min.time()) if date_of_birth else None,
                user_type=UserType[user_type],
                permit_level=permit_level if user_type == "admin" else 1
            )
            
            db_session.add(new_user)
            db_session.flush()  # Para obtener el ID generado
            
            # Crear perfil específico según el tipo
            if user_type == "coach":
                coach_profile = Coach(
                    user_id=new_user.user_id,
                    license=license_number
                )
                db_session.add(coach_profile)
            
            elif user_type == "player":
                player_profile = Player(
                    user_id=new_user.user_id,
                    service=service_type,
                    enrolment=enrolment,
                    notes=notes
                )
                db_session.add(player_profile)
            
            elif user_type == "admin":
                admin_profile = Admin(
                    user_id=new_user.user_id,
                    role=role
                )
                db_session.add(admin_profile)
            
            # Guardar cambios
            db_session.commit()
            db_session.close()
            
            st.success(f"Usuario {name} creado correctamente.")
            st.rerun()

def edit_profile():
    """Formulario para editar el perfil del usuario actual."""
    db_session = get_db_session()
    
    # Obtener usuario actual
    user_id = st.session_state.get("user_id")
    user = db_session.query(User).filter_by(user_id=user_id).first()
    
    if not user:
        st.error("No se pudo cargar la información del usuario.")
        db_session.close()
        return
    
    st.subheader("Editar Perfil")
    
    # Mostrar foto de perfil actual
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.image(user.profile_photo, width=150)
    
    with col2:
        st.write(f"**Usuario:** {user.username}")
        st.write(f"**Tipo:** {user.user_type.name}")
    
    # Formulario de edición
    with st.form("edit_profile_form"):
        name = st.text_input("Nombre completo", value=user.name)
        email = st.text_input("Correo electrónico", value=user.email)
        phone = st.text_input("Teléfono", value=user.phone or "")
        line = st.text_input("LINE ID", value=user.line or "")
        
        # Opción para cambiar contraseña
        st.subheader("Cambiar Contraseña")
        current_password = st.text_input("Contraseña actual", type="password")
        new_password = st.text_input("Nueva contraseña", type="password")
        confirm_password = st.text_input("Confirmar nueva contraseña", type="password")
        
        # Opción para cambiar foto de perfil
        st.subheader("Cambiar Foto de Perfil")
        new_profile_photo = st.file_uploader("Nueva foto de perfil", type=["jpg", "jpeg", "png"])
        
        submit = st.form_submit_button("Guardar Cambios")
        
        if submit:
            # Validar campos
            if not name or not email:
                st.error("El nombre y el correo electrónico son obligatorios.")
                return
            
            # Validar que el email no esté en uso por otro usuario
            existing_email = db_session.query(User).filter(
                User.email == email,
                User.user_id != user_id
            ).first()
            
            if existing_email:
                st.error("El correo electrónico ya está en uso por otro usuario.")
                return
            
            # Actualizar campos básicos
            user.name = name
            user.email = email
            user.phone = phone
            user.line = line
            
            # Cambiar contraseña si se proporcionó
            if current_password and new_password and confirm_password:
                if hash_password(current_password) != user.password_hash:
                    st.error("La contraseña actual es incorrecta.")
                    return
                
                if new_password != confirm_password:
                    st.error("Las nuevas contraseñas no coinciden.")
                    return
                
                user.password_hash = hash_password(new_password)
            
            # Cambiar foto de perfil si se proporcionó
            if new_profile_photo:
                profile_photo_path = save_profile_photo(new_profile_photo, user.username)
                
                # Eliminar foto anterior si no es la predeterminada
                if user.profile_photo != "assets/default_profile.png" and os.path.exists(user.profile_photo):
                    try:
                        os.remove(user.profile_photo)
                    except:
                        pass
                
                user.profile_photo = profile_photo_path
            
            # Guardar cambios
            db_session.commit()
            st.success("Perfil actualizado correctamente.")
            
            # Actualizar nombre en la sesión
            st.session_state["name"] = name
            
            st.rerun()
    
    db_session.close()

def system_settings():
    """Configuración del sistema (solo para administradores)."""
    st.subheader("Configuración del Sistema")
    
    # Crear carpetas necesarias si no existen
    if st.button("Verificar y crear directorios del sistema"):
        directories = ["assets", "assets/profile_photos", "data", "logs"]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                st.success(f"Directorio {directory} creado correctamente.")
            else:
                st.info(f"Directorio {directory} ya existe.")
    
    # Opción para crear copia de seguridad de la base de datos
    if st.button("Crear copia de seguridad de la base de datos"):
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/ballers_app_{timestamp}.db"
        
        try:
            shutil.copy2("ballers_app.db", backup_file)
            st.success(f"Copia de seguridad creada: {backup_file}")
        except Exception as e:
            st.error(f"Error al crear copia de seguridad: {str(e)}")

def show_content():
    """Función principal para mostrar el contenido de la sección Settings."""
    st.title("Configuración")
    
    # Verificar si el usuario es administrador
    user_type = st.session_state.get("user_type")
    
    if user_type != "admin":
        # Mostrar solo edición de perfil para usuarios no administradores
        edit_profile()
        return
    
    # Para administradores, mostrar todas las opciones
    tab1, tab2, tab3 = st.tabs(["Crear Usuario", "Editar Perfil", "Sistema"])
    
    with tab1:
        create_user_form()
    
    with tab2:
        edit_profile()
    
    with tab3:
        system_settings()

if __name__ == "__main__":
    # Para pruebas
    st.session_state["user_id"] = 1
    st.session_state["username"] = "admin"
    st.session_state["name"] = "Administrador"
    st.session_state["user_type"] = "admin"
    
    show_content()
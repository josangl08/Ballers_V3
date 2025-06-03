# pages/settings.py
import streamlit as st
from models import User, UserType, Coach, Player, Admin, Base
import hashlib
import datetime as dt
import os
import shutil
from controllers.calendar_controller import sync_db_to_calendar
from controllers.sync import start_auto_sync, stop_auto_sync, get_auto_sync_status, force_manual_sync, is_auto_sync_running, has_pending_notifications
from controllers.db import get_db_session 
from controllers.sheets_controller import get_accounting_df
from common.validation import validate_user_data

def hash_password(password):
    """Convierte una contraseña en un hash SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def save_profile_photo(uploaded_file, username):
    """Guarda la foto de perfil y devuelve la ruta."""
    if not os.path.exists("assets/profile_photos"):
        os.makedirs("assets/profile_photos")
    
    # Generar nombre de archivo único
    file_ext = os.path.splitext(uploaded_file.name)[1]
    filename = f"{username}_{dt.datetime.now().strftime('%Y%m%d%H%M%S')}{file_ext}"
    file_path = os.path.join("assets/profile_photos", filename)
    
    # Guardar archivo
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path

def create_user_form():
    """Formulario para crear un nuevo usuario."""
    st.subheader("Create New User")
    
    with st.form("create_user_form"):
        # Información básica
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name*")
            username = st.text_input("Username*")
            email = st.text_input("E-mail*")
        
        with col2:
            password = st.text_input("Password*", type="password")
            confirm_password = st.text_input("Confirm Password*", type="password")
            user_type = st.selectbox("User Type*", options=[t.name for t in UserType])
        
        # Información adicional
        phone = st.text_input("Telf")
        line = st.text_input("LINE ID")
        date_of_birth = st.date_input("Date of Birth", value=None)
        profile_photo = st.file_uploader("Profile Picture", type=["jpg", "jpeg", "png"])
        
        # Información específica según el tipo de usuario
        if user_type == "coach":
            license_number = st.text_input("License Name")
        elif user_type == "player":
            service_options = ["Basic", "Premium", "Elite", "Performance", "Recovery"]
            service_type = st.multiselect("Service type(s)", options=service_options, default=["Basic"])
            enrolment = st.number_input("Number of enrolled sessions", min_value=0, value=0)
            notes = st.text_area("Additional notes")
        elif user_type == "admin":
            role = st.text_input("Internal Role")
            permit_level = st.number_input("Permit Level", min_value=1, max_value=10, value=1)
        
        submit = st.form_submit_button("Create User")
        
        if submit:
            # Validar campos obligatorios
            is_valid, error_msg = validate_user_data(name, username, email, password)
            if not is_valid:
                st.error(error_msg)
                return
            
            # Validar contraseñas
            if password != confirm_password:
                st.error("The passwords do not match.")
                return
            
            # Validar que el username y email no existan
            db_session = get_db_session()
            existing_username = db_session.query(User).filter_by(username=username).first()
            existing_email = db_session.query(User).filter_by(email=email).first()
            
            if existing_username:
                st.error("The username is already in use.")
                db_session.close()
                return
            
            if existing_email:
                st.error("The email is already in use.")
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
                date_of_birth=dt.datetime.combine(date_of_birth, dt.datetime.min.time()) if date_of_birth else None,
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
                    service=", ".join(service_type), 
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
            
            st.success(f"User {name} created successfully.")
            st.rerun()


def edit_any_user():
    """Función para que los administradores editen cualquier usuario."""
    st.subheader("Editar Usuarios")
    
    # Obtener todos los usuarios de la base de datos
    db_session = get_db_session()
    users = db_session.query(User).all()
    
    if not users:
        st.info("There are no users in the database.")
        db_session.close()
        return
    
    # Crear un selector de usuarios
    user_options = [(u.user_id, f"{u.name} ({u.username}, {u.user_type.name})") for u in users]
    selected_user_id = st.selectbox(
        "Select User to Edit:",
        options=[u[0] for u in user_options],
        format_func=lambda x: next((u[1] for u in user_options if u[0] == x), "")
    )
    
    # Obtener el usuario seleccionado
    selected_user = db_session.query(User).filter_by(user_id=selected_user_id).first()
    
    if not selected_user:
        st.error("It was not possible to load the selected user.")
        db_session.close()
        return
    
    # Mostrar información del usuario
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.image(selected_user.profile_photo, width=150)
    
    with col2:
        st.write(f"**Username:** {selected_user.username}")
        st.write(f"**User Type:** {selected_user.user_type.name}")
        st.write(f"**E-mail:** {selected_user.email}")
    
    # Formulario de edición para el administrador
    with st.form("admin_edit_user_form"):
        name = st.text_input("Full Name", value=selected_user.name)
        email = st.text_input("E-mail", value=selected_user.email)
        phone = st.text_input("Telf", value=selected_user.phone or "")
        line = st.text_input("LINE ID", value=selected_user.line or "")
        
        # Opción para cambiar el tipo de usuario
        new_user_type = st.selectbox(
            "User Type", 
            options=[t.name for t in UserType],
            index=[t.name for t in UserType].index(selected_user.user_type.name)
        )
        
        # Permitir habilitar/deshabilitar el usuario
        is_active = getattr(selected_user, 'is_active', True)
        status = st.checkbox("User Active", value=is_active)
        
        # Información específica según el tipo de usuario
        if new_user_type == "coach":
            # Obtener perfil de coach si existe
            coach_profile = db_session.query(Coach).filter_by(user_id=selected_user.user_id).first()
            license_number = ""
            if coach_profile:
                license_number = coach_profile.license
            
            license_input = st.text_input("License Name", value=license_number)
            
        elif new_user_type == "player":
            # Obtener perfil de jugador si existe
            player_profile = db_session.query(Player).filter_by(user_id=selected_user.user_id).first()
            service_type = "Basic"
            enrolment = 0
            notes = ""
            
            if player_profile:
                service_type = player_profile.service or "Basic"
                enrolment = player_profile.enrolment or 0
                notes = player_profile.notes or ""
            
            service_options = ["Basic", "Premium", "Elite", "Performance", "Recovery"]
            current_services = service_type.split(", ") if service_type else ["Basic"]
            current_services = [s for s in current_services if s in service_options]

            service_input: list[str] = st.multiselect(
                "Service(s)",
                options=service_options,
                default=(
                    player_profile.service.split(", ")
                    if player_profile and player_profile.service
                    else []
                ),
            )
            enrolment_input = st.number_input("Number of enrolled sessions", min_value=0, value=enrolment)
            notes_input = st.text_area("Additional notes", value=notes)
            
        elif new_user_type == "admin":
            # Obtener perfil de admin si existe
            admin_profile = db_session.query(Admin).filter_by(user_id=selected_user.user_id).first()
            role = ""
            permit_level = 1
            
            if admin_profile:
                role = admin_profile.role or ""
            
            if hasattr(selected_user, 'permit_level'):
                permit_level = selected_user.permit_level
            
            role_input = st.text_input("Internal Role", value=role)
            permit_level_input = st.number_input("Permit Level", min_value=1, max_value=10, value=permit_level)
        
        # Opción para cambiar la contraseña
        st.subheader("Change Password")
        st.info("As an administrator, you can change the password without knowing the previous password.")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        # Opción para cambiar foto de perfil
        st.subheader("Change Profile Picture")
        new_profile_photo = st.file_uploader("New Profile Picture", type=["jpg", "jpeg", "png"])
        
        submit = st.form_submit_button("Save Changes")
        
        if submit:
            # Validar campos
            is_valid, error_msg = validate_user_data(name, selected_user.username, email) 
            if not is_valid:
                st.error(error_msg)
                return
            
            # Validar que el email no esté en uso por otro usuario
            existing_email = db_session.query(User).filter(
                User.email == email,
                User.user_id != selected_user.user_id
            ).first()
            
            if existing_email:
                st.error("The email is already in use.")
                return
            
            # Actualizar campos básicos
            selected_user.name = name
            selected_user.email = email
            selected_user.phone = phone
            selected_user.line = line
            
            # Actualizar estado de activación
            if hasattr(selected_user, 'is_active'):
                selected_user.is_active = status
            
            # Manejar cambio de tipo de usuario
            if new_user_type != selected_user.user_type.name:
                # Cambiar el tipo de usuario
                selected_user.user_type = UserType[new_user_type]
                
                # Eliminar perfiles existentes (limpiar relaciones)
                if hasattr(selected_user, 'coach_profile') and selected_user.coach_profile:
                    db_session.delete(selected_user.coach_profile)
                
                if hasattr(selected_user, 'player_profile') and selected_user.player_profile:
                    db_session.delete(selected_user.player_profile)
                
                if hasattr(selected_user, 'admin_profile') and selected_user.admin_profile:
                    db_session.delete(selected_user.admin_profile)
                
                # Crear nuevo perfil según el tipo
                if new_user_type == "coach":
                    coach_profile = Coach(
                        user_id=selected_user.user_id,
                        license=license_input
                    )
                    db_session.add(coach_profile)
                
                elif new_user_type == "player":
                    player_profile = db_session.query(Player).filter_by(user_id=selected_user.user_id).first()
                    if player_profile:
                        player_profile.service = ", ".join(service_input)
                        player_profile.enrolment = enrolment_input
                        player_profile.notes = notes_input
                    else:
                        player_profile = Player(
                            user_id=selected_user.user_id,
                            service=", ".join(service_input),
                            enrolment=enrolment_input,
                            notes=notes_input
                        )
                        db_session.add(player_profile)
                
                elif new_user_type == "admin":
                    admin_profile = Admin(
                        user_id=selected_user.user_id,
                        role=role_input
                    )
                    db_session.add(admin_profile)
                    # Actualizar nivel de permiso
                    selected_user.permit_level = permit_level_input
            else:
                # Actualizar información específica según el tipo actual
                if new_user_type == "coach":
                    coach_profile = db_session.query(Coach).filter_by(user_id=selected_user.user_id).first()
                    if coach_profile:
                        coach_profile.license = license_input
                    else:
                        coach_profile = Coach(
                            user_id=selected_user.user_id,
                            license=license_input
                        )
                        db_session.add(coach_profile)
                
                elif new_user_type == "player":
                    player_profile = db_session.query(Player).filter_by(user_id=selected_user.user_id).first()
                    service_str = ", ".join(service_input) or None
                    if player_profile:
                        player_profile.service = service_str
                        player_profile.enrolment = enrolment_input
                        player_profile.notes = notes_input
                    else:
                        player_profile = Player(
                            user_id=selected_user.user_id,
                            service=service_str,
                            enrolment=enrolment_input,
                            notes=notes_input
                        )
                        db_session.add(player_profile)
                
                elif new_user_type == "admin":
                    admin_profile = db_session.query(Admin).filter_by(user_id=selected_user.user_id).first()
                    if admin_profile:
                        admin_profile.role = role_input
                    else:
                        admin_profile = Admin(
                            user_id=selected_user.user_id,
                            role=role_input
                        )
                        db_session.add(admin_profile)
                    
                    # Actualizar nivel de permiso
                    if hasattr(selected_user, 'permit_level'):
                        selected_user.permit_level = permit_level_input
            
            # Cambiar contraseña si se proporcionó
            if new_password and confirm_password:
                if new_password != confirm_password:
                    st.error("The new passwords do not match.")
                    return
                
                selected_user.password_hash = hash_password(new_password)
            
            # Cambiar foto de perfil si se proporcionó
            if new_profile_photo:
                profile_photo_path = save_profile_photo(new_profile_photo, selected_user.username)
                
                # Eliminar foto anterior si no es la predeterminada
                if selected_user.profile_photo != "assets/default_profile.png" and os.path.exists(selected_user.profile_photo):
                    try:
                        os.remove(selected_user.profile_photo)
                    except:
                        pass
                
                selected_user.profile_photo = profile_photo_path
            
            # Guardar cambios
            db_session.commit()
            db_session.close()
            st.success(f"User {name} updated successfully.")
            st.rerun()
    
    db_session.close()
# In pages/settings.py, add this new function:

def delete_user():
    """Function for admins to delete users."""
    st.subheader("Delete User")
    
    # Obtener todos los usuarios de la base de datos
    db_session = get_db_session()
    users = db_session.query(User).all()
    
    if not users:
        st.info("No registered users in the system.")
        db_session.close()
        return
    
    # Crear un selector de usuarios
    user_options = [(u.user_id, f"{u.name} ({u.username}, {u.user_type.name})") for u in users]
    selected_user_id = st.selectbox(
        "Select user to delete:",
        options=[u[0] for u in user_options],
        format_func=lambda x: next((u[1] for u in user_options if u[0] == x), "")
    )
    
    # Obtener el usuario seleccionado
    selected_user = db_session.query(User).filter_by(user_id=selected_user_id).first()
    
    if not selected_user:
        st.error("Could not load the selected user.")
        db_session.close()
        return
    
    # Show user information
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.image(selected_user.profile_photo, width=150)
    
    with col2:
        st.write(f"**Username:** {selected_user.username}")
        st.write(f"**Type:** {selected_user.user_type.name}")
        st.write(f"**Email:** {selected_user.email}")
    
    # Confirm deletion
    st.warning("Warning: This action cannot be undone!")
    confirm_text = st.text_input("Type 'DELETE' to confirm:")
    
    if st.button("Delete User"):
        if confirm_text != "DELETE":
            st.error("Please type 'DELETE' to confirm.")
            return
            
        try:
            # Delete profile first (due to foreign key constraints)
            if selected_user.user_type == UserType.coach and selected_user.coach_profile:
                db_session.delete(selected_user.coach_profile)
                
            elif selected_user.user_type == UserType.player and selected_user.player_profile:
                db_session.delete(selected_user.player_profile)
                
            elif selected_user.user_type == UserType.admin and selected_user.admin_profile:
                db_session.delete(selected_user.admin_profile)
            
            # Delete user
            db_session.delete(selected_user)
            db_session.commit()
            st.success(f"User {selected_user.name} successfully deleted.")
            st.rerun()
            
        except Exception as e:
            db_session.rollback()
            st.error(f"Error deleting user: {str(e)}")
            st.info("This user may have associated sessions or other data that prevents deletion.")
    
    db_session.close()


def system_settings():
    """Configuración del sistema (solo para administradores)."""
    st.subheader("Database/Googlesheets Management")
    col1, col2 = st.columns(2)
    with col1:
        # Opción para crear copia de seguridad de la base de datos
        if st.button("Create a backup copy of the database"):
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{backup_dir}/ballers_app_{timestamp}.db"
            
            try:
                shutil.copy2("data/ballers_app.db", backup_file)
                st.success(f"Copia de seguridad creada: {backup_file}")
            except Exception as e:
                st.error(f"Error al crear copia de seguridad: {str(e)}")
    with col2:
        if st.button("🔄 Refresh Google Sheets", help="Actualizar datos financieros desde Google Sheets"):
            with st.spinner("Actualizando Google Sheets..."):
                try:
                    get_accounting_df.clear()
                    df = get_accounting_df()
                    st.success("✅ Google Sheets actualizado correctamente")
                except Exception as e:
                    st.error(f"❌ Error actualizando Google Sheets: {e}")

    st.subheader("Manual Synchronisation")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Push local sessions → Google Calendar"):
            with st.spinner("Pushing sessions..."):
                pushed, updated = sync_db_to_calendar()
            st.success(
                f"{pushed} sesiones nuevas enviadas, "
                f"{updated} sesiones actualizadas en Google Calendar."
            )

    with col2:
        # 🔧 FIX: Usar nueva función de sync manual
        
        if st.button("Bring events ← Google Calendar"):
            with st.spinner("Ejecutando sync manual..."):
                result = force_manual_sync()
                if result['success']:
                    # Mostrar estadísticas detalladas
                    stats_msg = f"✅ Sync completado en {result['duration']:.1f}s"
                    if any([result.get('imported', 0), result.get('updated', 0), result.get('deleted', 0)]):
                        stats_msg += f" - {result.get('imported', 0)} importadas, {result.get('updated', 0)} actualizadas, {result.get('deleted', 0)} eliminadas"
                    if result.get('past_updated', 0) > 0:
                        stats_msg += f", {result['past_updated']} marcadas como completadas"
                    st.success(stats_msg)
                else:
                    st.error(f"❌ Error: {result['error']}")

    # 🔧 FIX: AUTO-SYNC MANAGEMENT MEJORADO
    st.subheader("🤖 Auto-Sync Management")
    
    if has_pending_notifications():
        st.info("🔔 Hay cambios pendientes de notificar del auto-sync")

    # Estado actual
    if is_auto_sync_running():
        st.success("✅ Auto-Sync ACTIVO")
        
        # Mostrar estadísticas
        status = get_auto_sync_status()
        
        if status['total_syncs'] > 0:
            success_rate = (status['successful_syncs'] / status['total_syncs']) * 100
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Syncs", status['total_syncs'])
            col2.metric("Tasa Éxito", f"{success_rate:.0f}%")
            col3.metric("Intervalo", f"{status['interval_minutes']}m")

            if status.get('last_changes'):
                changes = status['last_changes']
                imported = changes.get('imported', 0)
                updated = changes.get('updated', 0)
                deleted = changes.get('deleted', 0)
                
                if imported + updated + deleted > 0:
                    st.info(f"📊 Últimos cambios: {imported} importadas, {updated} actualizadas, {deleted} eliminadas")
            
            
            if status['last_sync_time']:
                last_sync = dt.datetime.fromisoformat(status['last_sync_time'])
                time_ago = dt.datetime.now() - last_sync
                
                if time_ago.total_seconds() < 60:
                    st.info(f"Último sync: {int(time_ago.total_seconds())}s ago")
                elif time_ago.total_seconds() < 3600:
                    st.info(f"Último sync: {int(time_ago.total_seconds()/60)}m ago")
                else:
                    st.info(f"Último sync: {last_sync.strftime('%H:%M:%S')}")
        
        # Botones de control
        if st.button("⏸️ Detener Auto-Sync", use_container_width=True):
            if stop_auto_sync():
                st.success("Auto-Sync detenido")
                st.rerun()
            else:
                st.error("Error deteniendo Auto-Sync")
                
        # 💡 Agregar nota informativa
        st.info("💡 Para sync manual usa: 'Bring events ← Google Calendar' arriba")
    
    else:
        st.info("⏸️ Auto-Sync INACTIVO")
        
        # Configuración
        interval = st.slider(
            "Intervalo de sincronización (minutos)",
            min_value=2,  # 🔧 Mínimo 2 minutos para evitar database locking
            max_value=60,
            value=5,
            help="Frecuencia de sincronización automática (mínimo 2 min para evitar conflictos)"
        )

        # 🔧 AGREGAR advertencia si es muy bajo:
        if interval < 3:
            st.warning("⚠️ Intervalos muy cortos (< 3 min) pueden causar errores de concurrencia")
            st.info("💡 Recomendado: 5+ minutos para máxima estabilidad")
        
        auto_start = st.checkbox(
            "Auto-iniciar al login",
            value=st.session_state.get("auto_sync_auto_start", False),
            help="Iniciar auto-sync automáticamente al hacer login"
        )
        
        if auto_start != st.session_state.get("auto_sync_auto_start", False):
            st.session_state["auto_sync_auto_start"] = auto_start
        
        # Botón de inicio
        if st.button("▶️ Iniciar Auto-Sync"):
            if start_auto_sync(interval):
                st.success(f"Auto-sync iniciado (intervalo: {interval} min)")
                st.rerun()
            else:
                st.error("Auto-sync ya está ejecutándose")



def show_content():
    """Función principal para mostrar el contenido de la sección Settings."""
    st.markdown('<h3 class="section-title">Settings</h3>', unsafe_allow_html=True)
    
  
    # Para administradores, mostrar todas las opciones con la nueva estructura
    tab1, tab2 = st.tabs(["Users", "System"])
    
    with tab1:
        # Subtabs dentro de Users
        user_tab1, user_tab2, user_tab3 = st.tabs(["Create User", "Edit User", "Delete User"])
        
        with user_tab1:
            create_user_form()
        
        with user_tab2:
            edit_any_user()

        with user_tab3:
            delete_user()
    
    with tab2:
        system_settings()

if __name__ == "__main__":
    
    show_content()
# pages/settings.py
import streamlit as st
import pandas as pd
import datetime as dt
import os
import shutil

from controllers.user_controller import UserController, get_users_for_management, create_user_simple, update_user_simple, delete_user_simple, get_user_with_profile
from controllers.calendar_sync_core import sync_db_to_calendar
from controllers.sync_coordinator import start_auto_sync, stop_auto_sync, get_auto_sync_status, force_manual_sync, is_auto_sync_running, has_pending_notifications
from controllers.sheets_controller import get_accounting_df
from controllers.notification_controller import auto_cleanup_old_problems, get_sync_problems, clear_sync_problems
from models import UserType
from controllers.validation_controller import ValidationController


def create_user_form():
    """Formulario con selector integrado visualmente."""
    st.subheader("Create New User")
    
    # Key dinámica para limpiar formulario solo en éxito
    if "create_user_success_count" not in st.session_state:
        st.session_state.create_user_success_count = 0
    
    # Contenerdor Rpincipal que simula un form único
    with st.container(border=True):
        st.markdown("### 👤 User Information")
        
        # Stor fuera del form(pero dentro del contenedor)
        user_type = st.selectbox(
            "User Type*", 
            options=[t.name for t in UserType],
            help="Select user type to see specific fields below"
        )
        
        # Form visual con key dinámica
        with st.form(f"create_user_form_{st.session_state.create_user_success_count}", clear_on_submit=False, border=True):
            # Información básica
            st.markdown("#### Basic Information")
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name*")
                username = st.text_input("Username*")
                email = st.text_input("E-mail*")
            
            with col2:
                password = st.text_input("Password*", type="password")
                confirm_password = st.text_input("Confirm Password*", type="password")
            
            # Información adicional común
            st.markdown("#### Additional Information")
            col3, col4 = st.columns(2)
            with col3:
                phone = st.text_input("Phone")
                line = st.text_input("LINE ID")
            with col4:
                date_of_birth = st.date_input("Date of Birth", value=dt.date(2000, 1, 1), 
                    min_value=dt.date(1900, 1, 1), max_value=dt.date.today())
                profile_photo = st.file_uploader("Profile Picture", type=["jpg", "jpeg", "png"])
            
            # Campos especificos dinamicos
            if user_type == "coach":
                st.markdown("#### 📢 Coach Information")
                license_number = st.text_input("License Name", 
                    help="Professional coaching license or certification")
                
            elif user_type == "player":
                st.markdown("#### ⚽ Player Information")
                service_options = ["Basic", "Premium", "Elite", "Performance", "Recovery"]
                service_type = st.multiselect("Service type(s)", options=service_options, default=["Basic"])
                
                col5, col6 = st.columns(2)
                with col5:
                    enrolment = st.number_input("Number of enrolled sessions", min_value=0, value=0)
                with col6:
                    st.empty()  # Para layout
                
                notes = st.text_area("Additional notes")
                
            elif user_type == "admin":
                st.markdown("#### 🔑 Admin Information")
                col7, col8 = st.columns(2)
                with col7:
                    role = st.text_input("Internal Role")
                with col8:
                    permit_level = st.number_input("Permit Level", min_value=1, max_value=10, value=1)
            
            # Submit button
            submit = st.form_submit_button("Create User", type="primary", use_container_width=True)
            
            if submit:
                # Usar ValidationController para validar campos
                is_valid, error = ValidationController.validate_password_match(password, confirm_password)
                if not is_valid:
                    st.error(error)
                    return
                
                # Preparar datos específicos
                profile_data = {}
                if user_type == "coach":
                    profile_data['license'] = license_number
                elif user_type == "player":
                    profile_data.update({
                        'services': service_type,
                        'enrolment': enrolment,
                        'notes': notes
                    })
                elif user_type == "admin":
                    profile_data.update({
                        'role': role,
                        'permit_level': permit_level
                    })
                
                user_data = {
                    'name': name, 'username': username, 'email': email, 'password': password,
                    'user_type': user_type, 'phone': phone, 'line': line,
                    'date_of_birth': date_of_birth, 'profile_photo_file': profile_photo,
                    **profile_data
                }
                
                success, message = create_user_simple(user_data)
                if success:
                    st.success(message)
                    # Incrementar contador para limpiar formulario en próximo render
                    st.session_state.create_user_success_count += 1
                    st.rerun()
                else:
                    st.error(message)


def edit_any_user():
    """Función para que los administradores editen cualquier usuario - MEJORADO."""
    st.subheader("Edit Users")
    
    # Key dinámica para limpiar formulario solo en éxito
    if "edit_user_success_count" not in st.session_state:
        st.session_state.edit_user_success_count = 0
    
    # Usar nueva función sin lazy loading
    users_data = get_users_for_management()
    
    if not users_data:
        st.info("There are no users in the database.")
        return
    
    # Selector de usuarios
    selected_user_id = st.selectbox(
        "Select User to Edit:",
        options=[u["ID"] for u in users_data],
        format_func=lambda x: next((f"{u['Name']} ({u['Username']}, {u['User Type']})" for u in users_data if u["ID"] == x), "")
    )
    
    # Usar función que evita lazy loading
    user_data = get_user_with_profile(selected_user_id)
    if not user_data:
        st.error("Could not load the selected user.")
        return
    
    # Mostrar información del usuario
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.image(user_data["profile_photo"], width=150)
    
    with col2:
        st.write(f"**Username:** {user_data['username']}")
        st.write(f"**User Type:** {user_data['user_type']}")
        st.write(f"**E-mail:** {user_data['email']}")
    
    # Formulario de edición con key dinámica
    with st.form(f"admin_edit_user_form_{st.session_state.edit_user_success_count}", clear_on_submit=False):
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name", value=user_data["name"])
            username = st.text_input("Username", value=user_data["username"])  # 🆕 NUEVO
            email = st.text_input("E-mail", value=user_data["email"])
        with col2:
            phone = st.text_input("Phone", value=user_data["phone"] or "")
            line = st.text_input("LINE ID", value=user_data["line"] or "")
            
            # Estado activo
            status = st.checkbox("User Active", value=user_data["is_active"])
        
        # Tipo de usuario
        new_user_type = st.selectbox(
            "User Type", 
            options=[t.name for t in UserType],
            index=[t.name for t in UserType].index(user_data["user_type"])
        )
        
        # Información específica del perfil (dinámico)
        st.divider()
        st.subheader(f"{new_user_type} Specific Information")
        
        profile_data = {}
        
        if new_user_type == "coach":
            license_current = user_data.get("coach_license", "")
            license_input = st.text_input("License Name", value=license_current)
            profile_data['license'] = license_input
            
        elif new_user_type == "player":
            service_current = user_data.get("player_service", "")
            enrolment_current = user_data.get("player_enrolment", 0)
            notes_current = user_data.get("player_notes", "")
            
            service_options = ["Basic", "Premium", "Elite", "Performance", "Recovery"]
            current_services = service_current.split(", ") if service_current else []
            current_services = [s for s in current_services if s in service_options]
            
            service_input = st.multiselect(
                "Service(s)",
                options=service_options,
                default=current_services
            )
            enrolment_input = st.number_input("Number of enrolled sessions", min_value=0, value=enrolment_current)
            notes_input = st.text_area("Additional notes", value=notes_current)
            
            profile_data.update({
                'services': service_input,
                'enrolment': enrolment_input,
                'notes': notes_input
            })
            
        elif new_user_type == "admin":
            role_current = user_data.get("admin_role", "")
            permit_level_current = user_data.get("permit_level", 1)
            
            role_input = st.text_input("Internal Role", value=role_current)
            permit_level_input = st.number_input("Permit Level", min_value=1, max_value=10, value=permit_level_current)
            
            profile_data.update({
                'role': role_input,
                'permit_level': permit_level_input
            })
        
        # Cambio de contraseña
        st.divider()
        st.subheader("Change Password")
        st.info("As an administrator, you can change the password without knowing the previous password.")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        # Cambio de foto
        st.subheader("Change Profile Picture")
        new_profile_photo = st.file_uploader("New Profile Picture", type=["jpg", "jpeg", "png"])
        
    
        submit = st.form_submit_button("Save Changes", type="primary")
        
        if submit:
            # Usar ValidationController para validar campos
            if new_password or confirm_password:
                is_valid, error = ValidationController.validate_password_match(new_password, confirm_password)
                if not is_valid:
                    st.error(error)
                    return
            
            # Preparar datos para actualización
            update_data = {
                'name': name,
                'username': username,  
                'email': email,
                'phone': phone if phone else None,
                'line': line if line else None,
                'is_active': status,
                'new_password': new_password if new_password else None,
                'new_user_type': new_user_type if new_user_type != user_data["user_type"] else None,
                'profile_photo_file': new_profile_photo,
                **profile_data
            }
            
            # Actualizar controller para manejar username
            success, message = update_user_simple(selected_user_id, **update_data)
            
            if success:
                st.success(message)
                # Incrementar contador para limpiar formulario en próximo render
                st.session_state.edit_user_success_count += 1
                st.rerun()
            else:
                st.error(message)


def delete_user():
    """Function for admins to delete users"""
    st.subheader("Delete User")
    
    if "delete_user_success_count" not in st.session_state:
        st.session_state.delete_user_success_count = 0
    
    users_data = get_users_for_management()
    
    if not users_data:
        st.info("No registered users in the system.")
        return
    
    selected_user_id = st.selectbox(
        "Select user to delete:",
        options=[u["ID"] for u in users_data],
        format_func=lambda x: next((f"{u['Name']} ({u['Username']}, {u['User Type']})" for u in users_data if u["ID"] == x), "")
    )
    
    # Usar get_user_with_profile
    user_data = get_user_with_profile(selected_user_id)
    if not user_data:
        st.error("Could not load the selected user.")
        return
    
    # Mostrar información del usuario
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.image(user_data["profile_photo"], width=150)  
    
    with col2:
        st.write(f"**Username:** {user_data['username']}")
        st.write(f"**Type:** {user_data['user_type']}")
        st.write(f"**Email:** {user_data['email']}")
    
    # Confirmación de eliminación
    st.warning("Warning: This action cannot be undone!")
    confirm_text = st.text_input("Type 'DELETE' to confirm:", key=f"delete_confirm_{st.session_state.delete_user_success_count}")
    
    if st.button("Delete User"):
        # Usar ValidationController en lugar de duplicación
        is_valid, error = ValidationController.validate_deletion_confirmation(confirm_text, "DELETE")
        if not is_valid:
            st.error(error)
            return
        
        # Usar controller para eliminar
        success, message = delete_user_simple(user_data["user_id"])  
        
        if success:
            st.success(message)
            st.session_state.delete_user_success_count += 1
            st.rerun()
        else:
            st.error(message)


def manage_user_status():
    """Gestiona activación/desactivación de usuarios"""
    st.subheader("User Status Management")
    
    # Obtener usuarios
    users_data = get_users_for_management()
    
    if not users_data:
        st.info("No users available.")
        return
    
    # Filtro por tipo de usuario
    col1, col2 = st.columns([1, 1])
    with col1:
        user_types = ["All"] + [t.name for t in UserType]
        selected_type = st.selectbox("Filter by User Type:", options=user_types)
    
    with col2:
        status_filter = st.selectbox("Filter by Status:", options=["All", "Active  🟢", "Inactive  🔴"])
    
    # Filtrar usuarios
    filtered_users = users_data
    
    if selected_type != "All":
        filtered_users = [u for u in filtered_users if u["User Type"] == selected_type]
    
    if status_filter == "Active":
        filtered_users = [u for u in filtered_users if u["Active_Bool"]]
    elif status_filter == "Inactive":
        filtered_users = [u for u in filtered_users if not u["Active_Bool"]]
    
    if not filtered_users:
        st.info("No users match the selected filters.")
        return
    
    # Tabla con colores e iconos
    st.subheader("Users Overview")
    
    # Preparar datos para tabla
    table_data = []
    for user in filtered_users:
        # 🎨 Iconos para estado
        status_icon = "🟢" if user["Active_Bool"] else "🔴"
        status_text = f"{status_icon} {'Active' if user['Active_Bool'] else 'Inactive'}"
        
        # Iconos para tipo de usuario
        type_icons = {
            "admin": "🔑",
            "coach": "📢", 
            "player": "⚽"
        }
        type_icon = type_icons.get(user["User Type"].lower(), "👤")
        type_text = f"{type_icon} {user['User Type']}"
        
        table_data.append({
            "ID": user["ID"],
            "Name": user["Name"],
            "Username": user["Username"],
            "Type": type_text,
            "Status": status_text,
            "Email": user["Email"]
        })
    
    # Crear DataFrame
    df = pd.DataFrame(table_data)
    
    # Estilos por tipo de usuario
    def style_users(row):
        user_type = row["Type"].split()[1].lower()  # Extraer tipo sin icono
        if user_type == "admin":
            return ["background-color: rgba(244, 67, 54, 0.2)"] * len(row)
        elif user_type == "coach":
            return ["background-color: rgba(255, 193, 7, 0.2)"] * len(row)
        elif user_type == "player":
            return ["background-color: rgba(76, 175, 80, 0.2)"] * len(row)
        return [""] * len(row)
    
    # Aplicar estilos
    styled_df = df.style.apply(style_users, axis=1)
    
    # Mostrar tabla
    st.dataframe(
        styled_df,
        column_config={
            "ID": st.column_config.NumberColumn(width="small"),
            "Name": st.column_config.TextColumn(width="medium"),
            "Username": st.column_config.TextColumn(width="medium"),
            "Type": st.column_config.TextColumn(width="small"),
            "Status": st.column_config.TextColumn(width="small"),
            "Email": st.column_config.TextColumn(width="large")
        },
        hide_index=True,
        use_container_width=True
    )
    
    st.subheader("Change User Status")
    
    # Preparar opciones del selector con iconos
    type_icons = {
        "admin": "🔑",
        "coach": "📢", 
        "player": "⚽"
    }
    
    selector_options = []
    for user in filtered_users:
        status_icon = "✅" if user["Active_Bool"] else "❌"
        type_icon = type_icons.get(user["User Type"].lower(), "👤")
        
        label = f"{type_icon} {user['Name']} ({user['Username']}) {status_icon}"
        selector_options.append((user["ID"], label))
    
    selected_user_id = st.selectbox(
        "Select user to change status:",
        options=[opt[0] for opt in selector_options],
        format_func=lambda x: next((opt[1] for opt in selector_options if opt[0] == x), "")
    )
    
    # Encontrar usuario seleccionado
    selected_user = next((u for u in filtered_users if u["ID"] == selected_user_id), None)
    
    if selected_user:
        current_status = "Active" if selected_user["Active_Bool"] else "Inactive"
        action = "Deactivate" if selected_user["Active_Bool"] else "Activate"
        action_icon = "❌" if selected_user["Active_Bool"] else "✅"
        
        # Mostrar información actual
        col1, col2 = st.columns([2, 1])
        with col1:
            st.info(f"**{selected_user['Name']}** - Current status: **{current_status}**")
        
        with col2:
            if st.button(f"{action_icon} {action} User", type="primary"):
                # Usar controller para cambiar estado
                with UserController() as controller:
                    success, message = controller.toggle_user_status(selected_user["ID"])
                
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

def system_settings():
    """Configuración del sistema"""
    # Limpiar problemas antiguos automáticamente
    auto_cleanup_old_problems(max_age_hours=2)
    
    # Mostrar detalles completos si hay flag de redirección O problemas guardados
    should_show_details = (
        st.session_state.get("show_sync_details", False) or 
        st.session_state.get("show_sync_problems_tab", False) or
        bool(get_sync_problems())
    )
    
    if should_show_details:
        with st.container():
            st.subheader("🚨 Sync Results & Monitoring")
            
            
            result_data = None
            
            if 'last_sync_result' in st.session_state:
                result_data = st.session_state['last_sync_result']
                st.info("📊 Data from: Manual Sync")
            
            if not result_data:
                problems = get_sync_problems()
                if problems:
                    # Si tiene stats del fallback, usarlos
                    if 'stats' in problems:
                        result_data = {
                            'imported': problems['stats']['imported'],
                            'updated': problems['stats']['updated'],
                            'deleted': problems['stats']['deleted'],
                            'rejected_events': problems['rejected'],
                            'warning_events': problems['warnings'],
                            'duration': problems['stats']['duration']  # ← DURACIÓN INCLUIDA
                        }
                        st.info("📊 Data from: Auto-sync (AutoSyncStats)")
                    else:
                        # Fallback tradicional sin stats
                        result_data = {
                            'imported': 0, 'updated': 0, 'deleted': 0,
                            'rejected_events': problems['rejected'],
                            'warning_events': problems['warnings'],
                            'duration': 0
                        }
                        st.info("📊 Data from: Auto-sync (problems only)")
            
            if result_data:
                imported = result_data.get('imported', 0)
                updated = result_data.get('updated', 0)
                deleted = result_data.get('deleted', 0)
                past_updated = result_data.get('past_updated', 0)
                rejected_events = result_data.get('rejected_events', [])
                warning_events = result_data.get('warning_events', [])
                duration = result_data.get('duration', 0)
                
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                col1.metric("📥 Imported", imported)
                col2.metric("🔄 Updated", updated)
                col3.metric("🗑️ Deleted", deleted)
                col4.metric("🚫 Rejected", len(rejected_events))
                col5.metric("⚠️ Warnings", len(warning_events))
                if duration > 0:
                    col6.metric("⏱️ Duration", f"{duration:.1f}s")
                else:
                    col6.metric("⏱️ Duration", "N/A")
                
                if past_updated > 0:
                    st.info(f"📅 Additionally: {past_updated} past sessions marked as completed")
                
                total_changes = imported + updated + deleted
                
                if len(rejected_events) > 0:
                    st.error(f"🚫 Sync completed with {len(rejected_events)} rejected events")
                    if total_changes > 0:
                        st.error(f"📊 Changes: {total_changes} total ({imported} imported, {updated} updated, {deleted} deleted)")
                    if len(warning_events) > 0:
                        st.warning(f"⚠️ Additionally: {len(warning_events)} events with warnings")
                        
                elif len(warning_events) > 0:
                    st.warning(f"⚠️ Sync completed with {len(warning_events)} warnings")
                    if total_changes > 0:
                        st.warning(f"📊 Changes: {total_changes} total ({imported} imported, {updated} updated, {deleted} deleted)")
                    else:
                        st.warning("📊 No data changes")
                        
                elif total_changes > 0:
                    st.success(f"✅ Sync completed successfully with changes")
                    st.success(f"📊 Changes: {total_changes} total ({imported} imported, {updated} updated, {deleted} deleted)")
                    
                else:
                    st.info(f"ℹ️ Sync completed - no changes needed")
                    st.info("📊 Database and Calendar are already in sync")
                
                # Mostrar detalles de problemas
                if rejected_events or warning_events:
                    if rejected_events and warning_events:
                        detail_tab1, detail_tab2 = st.tabs([f"🚫 Rejected ({len(rejected_events)})", f"⚠️ Warnings ({len(warning_events)})"])
                    elif rejected_events:
                        detail_tab1, = st.tabs([f"🚫 Rejected Events ({len(rejected_events)})"])
                        detail_tab2 = None
                    else:
                        detail_tab2, = st.tabs([f"⚠️ Events with Warnings ({len(warning_events)})"])
                        detail_tab1 = None
                    
                    if detail_tab1 and rejected_events:
                        with detail_tab1:
                            for i, event in enumerate(rejected_events):
                                st.error(f"**{event['title']}** - {event['date']} {event['time']}")
                                st.write(f"❌ **Problem**: {event['reason']}")
                                st.write(f"💡 **Solution**: {event['suggestion']}")
                                if i < len(rejected_events) - 1:
                                    st.markdown("---")
                    
                    if detail_tab2 and warning_events:
                        with detail_tab2:
                            for i, event in enumerate(warning_events):
                                st.warning(f"**{event['title']}** - {event['date']} {event['time']}")
                                for w in event.get('warnings', []):
                                    st.write(f"⚠️ {w}")
                                st.write("✅ **Status**: Imported successfully")
                                if i < len(warning_events) - 1:
                                    st.markdown("---")
                
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    if st.button("🧹 Clear sync results", help="Mark all problems as resolved"):
                        clear_sync_problems()
                        if 'last_sync_result' in st.session_state:
                            del st.session_state['last_sync_result']
                        st.success("Sync results cleared")
                        st.rerun()
            else:
                st.info("ℹ️ No recent sync data available")
        
        if "show_sync_details" in st.session_state:
            st.session_state["show_sync_details"] = False
        if "show_sync_problems_tab" in st.session_state:
            st.session_state["show_sync_problems_tab"] = False
            
        st.divider()

    # Resto de system settings
    st.subheader("Database/Googlesheets Management")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Create a backup copy of the database"):
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{backup_dir}/ballers_app_{timestamp}.db"
            
            try:
                shutil.copy2("data/ballers_app.db", backup_file)
                st.success(f"Backup created: {backup_file}")
            except Exception as e:
                st.error(f"Error creating backup: {str(e)}")
    with col2:
        if st.button("Refresh Google Sheets"):
            with st.spinner("Updating Google Sheets..."):
                try:
                    get_accounting_df.clear()
                    df = get_accounting_df()
                    st.success("✅ Google Sheets updated correctly")
                except Exception as e:
                    st.error(f"❌ Error updating Google Sheets: {e}")

    st.subheader("Manual Synchronisation")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Push local sessions → Google Calendar"):
            with st.spinner("Pushing sessions..."):
                pushed, updated = sync_db_to_calendar()
            st.success(
                f"{pushed} new sessions sent, "
                f"{updated} sessions updated in Google Calendar."
            )

    with col2:
        if st.button("Bring events ← Google Calendar"):
            with st.spinner("Executing manual sync..."):
                result = force_manual_sync()
                
                if result['success']:
                    duration = result['duration']
                    imported = result.get('imported', 0)
                    updated = result.get('updated', 0) 
                    deleted = result.get('deleted', 0)
                    past_updated = result.get('past_updated', 0)
                    rejected_events = result.get('rejected_events', [])
                    warning_events = result.get('warning_events', [])
                    
                    st.session_state['last_sync_result'] = result
                    
                    changes = []
                    if imported > 0:
                        changes.append(f"{imported} imported")
                    if updated > 0:
                        changes.append(f"{updated} updated") 
                    if deleted > 0:
                        changes.append(f"{deleted} deleted")
                    if past_updated > 0:
                        changes.append(f"{past_updated} marked as completed")
                        
                    changes_text = ", ".join(changes) if changes else "no changes"
                    
                    total_problems = len(rejected_events) + len(warning_events)
                    
                    if len(rejected_events) > 0:
                        st.error(f"⚠️ Sync completed with {len(rejected_events)} rejected events ({duration:.1f}s) | {changes_text}")
                    elif len(warning_events) > 0:
                        st.warning(f"⚠️ Sync completed with {len(warning_events)} warnings ({duration:.1f}s) | {changes_text}")
                    elif imported + updated + deleted > 0:
                        st.success(f"✅ Sync completed successfully ({duration:.1f}s) | {changes_text}")
                    else:
                        st.info(f"ℹ️ Sync completed - no changes ({duration:.1f}s)")
                    
                    st.session_state["show_sync_details"] = True
                    st.rerun()
                    
                else:
                    st.error(f"❌ Sync failed: {result['error']}")

    # Auto-Sync
    st.subheader("Auto-Sync Management")
    
    if has_pending_notifications():
        st.info("🔔 There are pending changes to be notified from auto-sync")

    if is_auto_sync_running():
        st.success("✅ Auto-Sync ACTIVE")
        
        status = get_auto_sync_status()
        
        if status['total_syncs'] > 0:
            success_rate = (status['successful_syncs'] / status['total_syncs']) * 100
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Syncs", status['total_syncs'])
            col2.metric("Success Rate", f"{success_rate:.0f}%")
            col3.metric("Interval", f"{status['interval_minutes']}m")

            if status.get('last_changes'):
                changes = status['last_changes']
                imported = changes.get('imported', 0)
                updated = changes.get('updated', 0)
                deleted = changes.get('deleted', 0)
                
                if imported + updated + deleted > 0:
                    st.info(f"📊 Latest changes: {imported} imported, {updated} updated, {deleted} deleted")
            
            if status['last_sync_time']:
                last_sync = dt.datetime.fromisoformat(status['last_sync_time'])
                time_ago = dt.datetime.now() - last_sync
                
                if time_ago.total_seconds() < 60:
                    st.info(f"Last sync: {int(time_ago.total_seconds())}s ago")
                elif time_ago.total_seconds() < 3600:
                    st.info(f"Last sync: {int(time_ago.total_seconds()/60)}m ago")
                else:
                    st.info(f"Last sync: {last_sync.strftime('%H:%M:%S')}")
        
        if st.button("⏸️ Stop Auto-Sync", use_container_width=True):
            if stop_auto_sync():
                st.success("Auto-Sync stopped")
                st.rerun()
            else:
                st.error("Error stopping Auto-Sync")
                
        st.info("💡 For manual sync use: 'Bring events ← Google Calendar' above")
    
    else:
        st.info("⏸️ Auto-Sync INACTIVE")
        
        interval = st.slider(
            "Synchronization interval (minutes)",
            min_value=2,
            max_value=60,
            value=5,
            help="Automatic synchronization frequency (minimum 2 min to avoid conflicts)"
        )

        if interval < 3:
            st.warning("⚠️ Very short intervals (< 3 min) can cause concurrency errors")
            st.info("💡 Recommended: 5+ minutes for maximum stability")
        
        auto_start = st.checkbox(
            "Auto-start on login",
            value=st.session_state.get("auto_sync_auto_start", False),
            help="Start auto-sync automatically when logging in"
        )
        
        if auto_start != st.session_state.get("auto_sync_auto_start", False):
            st.session_state["auto_sync_auto_start"] = auto_start
        
        if st.button("▶️ Start Auto-Sync"):
            if start_auto_sync(interval):
                st.success(f"Auto-sync started (interval: {interval} min)")
                st.rerun()
            else:
                st.error("Auto-sync is already running")
                

def show_content():
    """Función principal para mostrar el contenido de la sección Settings."""
    st.markdown('<h3 class="section-title">Settings</h3>', unsafe_allow_html=True)
    
    # System primero, Users segundo
    tab1, tab2 = st.tabs(["System", "Users"])
    
    with tab1:  # System - Pestaña Principal
        system_settings()
    
    with tab2:  # Users - Pestaña secundaria
        user_tab1, user_tab2, user_tab3, user_tab4 = st.tabs(["Create User", "Edit User", "Delete User", "User Status"])
        
        with user_tab1:
            create_user_form()
        
        with user_tab2:
            edit_any_user()

        with user_tab3:
            delete_user()
        
        with user_tab4:
            manage_user_status()


if __name__ == "__main__":
    show_content()
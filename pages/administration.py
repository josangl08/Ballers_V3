# pages/administration.py
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, Coach, Player, Session, SessionStatus, Base, UserType
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

# Agregar la ruta raíz al path de Python para importar config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DATABASE_PATH

def get_db_session():
    """Crea y devuelve una sesión de SQLAlchemy."""
    engine = create_engine(f'sqlite:///{DATABASE_PATH}')
    Base.metadata.create_all(engine)  # Crea tablas si no existen
    Session = sessionmaker(bind=engine)
    return Session()

def show_coach_calendar():
    """Muestra el calendario de sesiones para un coach."""
    db_session = get_db_session()
    
    # Obtener el ID del coach basado en el usuario actual
    user_id = st.session_state.get("user_id")
    coach = db_session.query(Coach).join(User).filter(User.user_id == user_id).first()
    
    if not coach:
        st.error("No se encontró información del coach.")
        db_session.close()
        return
    
    # Filtros de fecha
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Desde", 
            value=datetime.now().date(),
            min_value=datetime.now().date() - timedelta(days=30),
            max_value=datetime.now().date() + timedelta(days=90)
        )
    with col2:
        end_date = st.date_input(
            "Hasta", 
            value=datetime.now().date() + timedelta(days=7),
            min_value=start_date,
            max_value=datetime.now().date() + timedelta(days=90)
        )
    
    # Convertir fechas a datetime para la consulta
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Obtener sesiones del coach en el rango de fechas
    sessions = db_session.query(Session).filter(
        Session.coach_id == coach.coach_id,
        Session.start_time >= start_datetime,
        Session.start_time <= end_datetime
    ).order_by(Session.start_time).all()
    
    # Mostrar el calendario de sesiones
    st.subheader("Calendario de Sesiones")
    
    if not sessions:
        st.info(f"No hay sesiones programadas entre {start_date.strftime('%d/%m/%Y')} y {end_date.strftime('%d/%m/%Y')}.")
    else:
        # Preparar datos para mostrar
        sessions_data = []
        for session in sessions:
            player = db_session.query(Player).filter(Player.player_id == session.player_id).first()
            player_name = player.user.name if player else "Jugador no encontrado"
            
            sessions_data.append({
                "ID": session.id,
                "Jugador": player_name,
                "Fecha": session.start_time.strftime("%d/%m/%Y"),
                "Hora Inicio": session.start_time.strftime("%H:%M"),
                "Hora Fin": session.end_time.strftime("%H:%M") if session.end_time else "No establecida",
                "Estado": session.status.value,
                "session_obj": session  # Para usar después, no se muestra
            })
        
        # Crear DataFrame para mostrar
        df = pd.DataFrame(sessions_data)
        session_objects = df.pop("session_obj")  # Quitar de la visualización pero mantener para uso posterior
        
        # Mostrar calendario como tabla
        st.dataframe(
            df, 
            column_config={
                "ID": st.column_config.NumberColumn(width="small"),
                "Jugador": st.column_config.TextColumn(width="medium"),
                "Fecha": st.column_config.TextColumn(width="small"),
                "Hora Inicio": st.column_config.TextColumn(width="small"),
                "Hora Fin": st.column_config.TextColumn(width="small"),
                "Estado": st.column_config.TextColumn(width="small")
            },
            hide_index=True
        )
        
        # Permitir editar una sesión
        selected_session_id = st.selectbox(
            "Seleccionar sesión para gestionar:",
            options=[s["ID"] for s in sessions_data],
            format_func=lambda x: f"Sesión #{x} - {next((s['Jugador'] for s in sessions_data if s['ID'] == x), 'Desconocido')} ({next((s['Fecha'] for s in sessions_data if s['ID'] == x), '')} {next((s['Hora Inicio'] for s in sessions_data if s['ID'] == x), '')})"
        )
        
        if selected_session_id:
            # Encontrar la sesión seleccionada
            session_idx = next((i for i, s in enumerate(sessions_data) if s["ID"] == selected_session_id), None)
            if session_idx is not None:
                session = session_objects.iloc[session_idx]
                
                # Mostrar opciones de gestión
                st.subheader(f"Gestionar Sesión #{selected_session_id}")
                
                # Opciones según el estado actual
                current_status = session.status
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Cambiar estado
                    new_status = st.selectbox(
                        "Estado:", 
                        options=[s.value for s in SessionStatus],
                        index=[s.value for s in SessionStatus].index(current_status.value)
                    )
                
                with col2:
                    # Añadir/editar notas
                    notes = st.text_area("Notas:", value=session.notes or "")
                
                # Botón para guardar cambios
                if st.button("Guardar cambios"):
                    session.status = SessionStatus(new_status)
                    session.notes = notes
                    db_session.commit()
                    st.success("Cambios guardados correctamente")
                    st.rerun()
    
    # Botón para añadir nueva sesión
    st.subheader("Nueva Sesión")
    
    # Obtener lista de jugadores para seleccionar
    players = db_session.query(Player).join(User).filter(User.is_active == True).all()
    player_options = [(p.player_id, p.user.name) for p in players]
    
    # Formulario para nueva sesión
    with st.form("nueva_sesion"):
        col1, col2 = st.columns(2)
        
        with col1:
            player_id = st.selectbox(
                "Jugador:", 
                options=[p[0] for p in player_options],
                format_func=lambda x: next((p[1] for p in player_options if p[0] == x), "")
            )
            
            session_date = st.date_input(
                "Fecha:", 
                value=datetime.now().date(),
                min_value=datetime.now().date(),
                max_value=datetime.now().date() + timedelta(days=90)
            )
        
        with col2:
            start_time = st.time_input("Hora de inicio:", value=datetime.now().time())
            end_time = st.time_input(
                "Hora de fin:", 
                value=(datetime.now() + timedelta(hours=1)).time()
            )
            
        notes = st.text_area("Notas:")
        
        submit = st.form_submit_button("Programar Sesión")
        
        if submit:
            # Crear objetos datetime para start_time y end_time
            start_datetime = datetime.combine(session_date, start_time)
            end_datetime = datetime.combine(session_date, end_time)
            
            # Validar que end_time sea posterior a start_time
            if end_datetime <= start_datetime:
                st.error("La hora de fin debe ser posterior a la hora de inicio.")
            else:
                # Crear nueva sesión
                new_session = Session(
                    coach_id=coach.coach_id,
                    player_id=player_id,
                    start_time=start_datetime,
                    end_time=end_datetime,
                    status=SessionStatus.SCHEDULED,
                    notes=notes
                )
                
                db_session.add(new_session)
                db_session.commit()
                st.success("Sesión programada correctamente")
                st.rerun()

def show_admin_dashboard():
    """Muestra el panel de administración completo para administradores."""
    st.subheader("Panel de Administración")
    
    # Crear pestañas para las diferentes secciones
    tab1, tab2, tab3 = st.tabs(["Sesiones", "Usuarios", "Estadísticas"])
    
    with tab1:
        # Mostrar todas las sesiones para administradores
        show_all_sessions()
    
    with tab2:
        # Mostrar gestión de usuarios
        show_user_management()
    
    with tab3:
        # Mostrar estadísticas
        show_statistics()
    
    db_session = get_db_session()
    db_session.close()

def show_all_sessions():
    """Muestra todas las sesiones para los administradores."""
    db_session = get_db_session()
    
    # Filtros de fecha
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Desde", 
            value=datetime.now().date() - timedelta(days=7),
            min_value=datetime.now().date() - timedelta(days=90),
            max_value=datetime.now().date() + timedelta(days=90),
            key="admin_start_date"
        )
    with col2:
        end_date = st.date_input(
            "Hasta", 
            value=datetime.now().date() + timedelta(days=7),
            min_value=start_date,
            max_value=datetime.now().date() + timedelta(days=90),
            key="admin_end_date"
        )

    # Filtro de estado
    status_values = [s.value for s in SessionStatus]
    status_filter = st.multiselect(
        "Estado", 
        options=status_values,
        default=status_values
    )
    
    # Filtro de coach
    coaches = db_session.query(Coach).join(User).all()
    coach_options = [(c.coach_id, c.user.name) for c in coaches]
    coach_options.insert(0, (None, "Todos los coaches"))
    
    selected_coach = st.selectbox(
        "Coach:", 
        options=[c[0] for c in coach_options],
        format_func=lambda x: next((c[1] for c in coach_options if c[0] == x), ""),
        index=0
    )
    
    # Convertir fechas a datetime para la consulta
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Construir consulta base
    query = db_session.query(Session).filter(
        Session.start_time >= start_datetime,
        Session.start_time <= end_datetime
    )
    
    # Aplicar filtros adicionales
    if status_filter:
        query = query.filter(Session.status.in_([SessionStatus(s) for s in status_filter]))
    
    if selected_coach is not None and selected_coach != 0:
        query = query.filter(Session.coach_id == selected_coach)
    
    # Ejecutar consulta
    sessions = query.order_by(Session.start_time).all()
    
    # Mostrar las sesiones
    if not sessions:
        st.info("No hay sesiones que coincidan con los filtros.")
    else:
        # Preparar datos para mostrar
        sessions_data = []
        for session in sessions:
            coach = db_session.query(Coach).filter(Coach.coach_id == session.coach_id).first()
            player = db_session.query(Player).filter(Player.player_id == session.player_id).first()
            
            coach_name = coach.user.name if coach and coach.user else "Coach no encontrado"
            player_name = player.user.name if player and player.user else "Jugador no encontrado"
            
            sessions_data.append({
                "ID": session.id,
                "Coach": coach_name,
                "Jugador": player_name,
                "Fecha": session.start_time.strftime("%d/%m/%Y"),
                "Hora Inicio": session.start_time.strftime("%H:%M"),
                "Hora Fin": session.end_time.strftime("%H:%M") if session.end_time else "No establecida",
                "Estado": session.status.value,
                "session_obj": session  # Para usar después, no se muestra
            })
        
        # Crear DataFrame para mostrar
        df = pd.DataFrame(sessions_data)
        session_objects = df.pop("session_obj").reset_index(drop=True)  # Quitar de la visualización pero mantener para uso posterior
        
        # Mostrar calendario como tabla
        st.dataframe(
            df, 
            column_config={
                "ID": st.column_config.NumberColumn(width="small"),
                "Coach": st.column_config.TextColumn(width="medium"),
                "Jugador": st.column_config.TextColumn(width="medium"),
                "Fecha": st.column_config.TextColumn(width="small"),
                "Hora Inicio": st.column_config.TextColumn(width="small"),
                "Hora Fin": st.column_config.TextColumn(width="small"),
                "Estado": st.column_config.TextColumn(width="small")
            },
            hide_index=True
        )
        
        # Opciones de gestión de sesiones para administradores
        st.subheader("Gestionar Sesión")
        col1, col2 = st.columns(2)
        
        with col1:
            # Permitir eliminar una sesión
            session_to_delete = st.selectbox(
                "Seleccionar sesión para eliminar:",
                options=[s["ID"] for s in sessions_data],
                format_func=lambda x: f"Sesión #{x} - {next((s['Coach'] for s in sessions_data if s['ID'] == x), '')} con {next((s['Jugador'] for s in sessions_data if s['ID'] == x), '')}"
            )
            
            if st.button("Eliminar Sesión"):
                session_to_remove = db_session.query(Session).filter(Session.id == session_to_delete).first()
                if session_to_remove:
                    db_session.delete(session_to_remove)
                    db_session.commit()
                    st.success(f"Sesión #{session_to_delete} eliminada correctamente")
                    st.rerun()
        
        with col2:
            # Permitir cambiar el estado de una sesión
            session_to_update = st.selectbox(
                "Seleccionar sesión para actualizar:",
                options=[s["ID"] for s in sessions_data],
                format_func=lambda x: f"Sesión #{x} - {next((s['Coach'] for s in sessions_data if s['ID'] == x), '')} con {next((s['Jugador'] for s in sessions_data if s['ID'] == x), '')}",
                key="update_session_select"
            )
            
            # Encontrar índice de la sesión seleccionada
            session_idx = next((i for i, s in enumerate(sessions_data) if s["ID"] == session_to_update), None)
            if session_idx is not None:
                session = session_objects.iloc[session_idx]
                
                new_status = st.selectbox(
                    "Nuevo estado:", 
                    options=[s.value for s in SessionStatus],
                    index=[s.value for s in SessionStatus].index(session.status.value)
                )
                
                if st.button("Actualizar Estado"):
                    session.status = SessionStatus(new_status)
                    db_session.commit()
                    st.success(f"Sesión #{session_to_update} actualizada correctamente")
                    st.rerun()

def show_user_management():
    """Muestra la gestión de usuarios para administradores."""
    db_session = get_db_session()
    
    st.subheader("Gestión de Usuarios")
    
    # Filtros
    user_types = ["Todos"] + [t.name for t in UserType]
    selected_type = st.selectbox("Tipo de usuario:", options=user_types)
    
    # Construir consulta base
    query = db_session.query(User)
    
    # Aplicar filtros
    if selected_type != "Todos":
        query = query.filter(User.user_type == UserType[selected_type])
    
    # Ejecutar consulta
    users = query.order_by(User.name).all()
    
    if not users:
        st.info("No hay usuarios que coincidan con los filtros.")
        return
    
    # Preparar datos para mostrar
    users_data = []
    for user in users:
        is_active = getattr(user, 'is_active', True)  # Para compatibilidad si no existe el campo
        users_data.append({
            "ID": user.user_id,
            "Nombre": user.name,
            "Username": user.username,
            "Email": user.email,
            "Tipo": user.user_type.name,
            "Activo": "Sí" if is_active else "No",
            "user_obj": user  # Para usar después, no se muestra
        })
    
    # Crear DataFrame para mostrar
    df = pd.DataFrame(users_data)
    user_objects = df.pop("user_obj").reset_index(drop=True)  # Quitar de la visualización pero mantener para uso posterior
    
    # Mostrar usuarios como tabla
    st.dataframe(
        df,
        column_config={
            "ID": st.column_config.NumberColumn(width="small"),
            "Nombre": st.column_config.TextColumn(width="medium"),
            "Username": st.column_config.TextColumn(width="medium"),
            "Email": st.column_config.TextColumn(width="medium"),
            "Tipo": st.column_config.TextColumn(width="small"),
            "Activo": st.column_config.TextColumn(width="small")
        },
        hide_index=True
    )
    
    # Opciones de gestión de usuarios
    col1, col2 = st.columns(2)
    
    with col1:
        # Activar/desactivar usuario
        user_to_toggle = st.selectbox(
            "Seleccionar usuario para activar/desactivar:",
            options=[u["ID"] for u in users_data],
            format_func=lambda x: f"{next((u['Nombre'] for u in users_data if u['ID'] == x), '')} ({next((u['Username'] for u in users_data if u['ID'] == x), '')})"
        )
        
        # Encontrar índice del usuario seleccionado
        user_idx = next((i for i, u in enumerate(users_data) if u["ID"] == user_to_toggle), None)
        if user_idx is not None:
            user = user_objects.iloc[user_idx]
            
            # Verificar si el campo is_active existe
            if hasattr(user, 'is_active'):
                toggle_label = "Desactivar" if user.is_active else "Activar"
                if st.button(f"{toggle_label} Usuario"):
                    user.is_active = not user.is_active
                    db_session.commit()
                    st.success(f"Usuario {toggle_label.lower()}do correctamente")
                    st.rerun()
            else:
                st.info("La gestión de estado de usuario no está disponible en esta versión.")
    
    with col2:
        st.write("Crear nuevo usuario")
        st.write("Usa la página de configuración para crear usuarios")

def show_statistics():
    """Muestra estadísticas globales para administradores."""
    db_session = get_db_session()
    
    st.subheader("Estadísticas Globales")
    
    # Obtener estadísticas básicas
    total_users = db_session.query(User).count()
    total_players = db_session.query(Player).count()
    total_coaches = db_session.query(Coach).count()
    total_sessions = db_session.query(Session).count()
    
    try:
        completed_sessions = db_session.query(Session).filter(Session.status == SessionStatus.COMPLETED).count()
    except:
        completed_sessions = 0  # En caso de error o si no hay sesiones completadas
    
    # Mostrar estadísticas en tarjetas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Usuarios", total_users)
        st.metric("Total Jugadores", total_players)
    
    with col2:
        st.metric("Total Entrenadores", total_coaches)
        st.metric("Ratio Jugadores/Entrenadores", round(total_players/total_coaches, 1) if total_coaches > 0 else 0)
    
    with col3:
        st.metric("Total Sesiones", total_sessions)
        percentage = int(completed_sessions/total_sessions*100) if total_sessions > 0 else 0
        st.metric("Sesiones Completadas", f"{completed_sessions} ({percentage}%)")
    
    # Gráfico de sesiones por estado
    try:
        scheduled_sessions = db_session.query(Session).filter(Session.status == SessionStatus.SCHEDULED).count()
        canceled_sessions = db_session.query(Session).filter(Session.status == SessionStatus.CANCELED).count()
        
        status_data = pd.DataFrame({
            "Estado": ["Programadas", "Completadas", "Canceladas"],
            "Cantidad": [scheduled_sessions, completed_sessions, canceled_sessions]
        })
        
        st.subheader("Sesiones por Estado")
        st.bar_chart(status_data, x="Estado", y="Cantidad")
    except Exception as e:
        st.error(f"Error al generar estadísticas de sesiones: {str(e)}")
        st.info("Asegúrate de que existen sesiones en la base de datos para mostrar estadísticas.")

def show_content():
    """Función principal para mostrar el contenido de la sección Administration."""
    st.title("Administration")
    
    # Mostrar contenido según el tipo de usuario
    user_type = st.session_state.get("user_type")
    
    if user_type == "admin":
        # Mostrar panel de administración completo
        show_admin_dashboard()
    elif user_type == "coach":
        # Mostrar calendario del coach
        show_coach_calendar()
    else:
        st.error("No tienes permisos para acceder a esta sección.")

if __name__ == "__main__":
    # Para pruebas
    st.session_state["user_id"] = 1
    st.session_state["user_type"] = "admin"
    show_content()
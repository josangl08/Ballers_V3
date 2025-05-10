# pages/administration.py
import streamlit as st
from sqlalchemy import func, case
from models import User, Coach, Player, Session, SessionStatus, Base, UserType
import pandas as pd
import datetime as dt
import os
import sys
from controllers.calendar_controller import push_session, patch_color, get_sessions
from controllers.internal_calendar import show_calendar
from controllers.sheets_controller import get_accounting_df
from controllers.db import get_db_session

# Agregar la ruta raíz al path de Python para importar config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


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
    
    # métricas globales del coach
    comp = sum(s.status is SessionStatus.COMPLETED for s in coach.sessions)
    prog = sum(s.status is SessionStatus.SCHEDULED for s in coach.sessions)
    canc = sum(s.status is SessionStatus.CANCELED  for s in coach.sessions)

    c1, c2, c3 = st.columns(3)
    c1.metric("Sheduled", prog)
    c2.metric("Completed", comp)
    c3.metric("Canceled",  canc)
      
    st.subheader(f"Calendar of {coach.user.name}")

    # Filtros de fecha
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "From", 
            value=dt.datetime.now().date() - dt.timedelta(days=7),
            key="admin_start_date"
        )
    with col2:
        end_date = st.date_input(
            "To", 
            value=dt.datetime.now().date() + dt.timedelta(days=7),
            key="admin_end_date"
        )

    # Filtro de estado
    status_values = [s.value for s in SessionStatus]
    status_filter = st.multiselect(
        "Status", 
        options=status_values,
        default=status_values
    )
    
    if end_date < start_date:
        st.error("The 'To' date must be on or after the 'From' date.")
    else:
        # Convertir a datetime solo si las fechas son válidas
        start_datetime = dt.datetime.combine(start_date, dt.time.min)
        end_datetime   = dt.datetime.combine(end_date,   dt.time.max)
    
    # Aplicar filtros adicionales
    status_enums = [SessionStatus(s) for s in status_filter] if status_filter else None
       
    # Ejecutar consulta
    sessions = get_sessions(
        start=start_datetime,
        end=end_datetime,
        coach_id=coach.coach_id,
        statuses=status_enums
    )
    
    # Mostrar calendario del coach
    show_calendar("", sessions, key="my_cal")
    
    # Mostrar el listado de sesiones
    st.subheader("Sessions List")
    
    if not sessions:
        st.info(f"There are no scheduled sessions between {start_date.strftime('%d/%m/%Y')} y {end_date.strftime('%d/%m/%Y')}.")
    else:
        # Preparar datos para mostrar
        sessions_data = []
        for session in sessions:
            player = db_session.query(Player).filter(Player.player_id == session.player_id).first()
            player_name = player.user.name if player else "Player not found"
            
            sessions_data.append({
                "ID": session.id,
                "Player": player_name,
                "Date": session.start_time.strftime("%d/%m/%Y"),
                "Start Time": session.start_time.strftime("%H:%M"),
                "End Time": session.end_time.strftime("%H:%M") if session.end_time else "Not established",
                "Status": session.status.value,                
            })
        
        # Crear DataFrame para mostrar
        df = pd.DataFrame(sessions_data)
        
        
        # Add styling based on status
        def style_sessions(row):
            if row["Status"] == "completed":
                return ["background-color: rgba(76, 175, 80, 0.2)"] * len(row)
            elif row["Status"] == "canceled":
                return ["background-color: rgba(244, 67, 54, 0.2)"] * len(row)
            elif row["Status"] == "scheduled":
                return ["background-color: rgba(33, 150, 243, 0.2)"] * len(row)
            return [""] * len(row)

        # Apply styling
        styled_df = df.style.apply(style_sessions, axis=1)
        
        # Mostrar calendario como tabla
        st.dataframe(
            styled_df, 
            column_config={
                "ID": st.column_config.NumberColumn(width="small"),
                "Coach": st.column_config.TextColumn(width="medium"),
                "Player": st.column_config.TextColumn(width="medium"),
                "Date": st.column_config.TextColumn(width="small"),
                "Start Time": st.column_config.TextColumn(width="small"),
                "End Time": st.column_config.TextColumn(width="small"),
                "Status": st.column_config.TextColumn(width="small")
            },
            hide_index=True
        )

        st.subheader("Edit Session")

        with st.form("edit_session_form", clear_on_submit=False):
            # ---------- selector de sesión ----------
            sessions_by_id = {s.id: s for s in sessions}          # <- SOLO memoria local
            selected_id = st.selectbox(
                "Select session:",
                options=list(sessions_by_id.keys()),
                format_func=lambda sid: (
                    f"#{sid} – {next((d['Player'] for d in sessions_data if d['ID']==sid),'?')} "
                    f"({next((d['Date'] for d in sessions_data if d['ID']==sid),'')})"
                )
            )

            if selected_id:
                session = db_session.get(Session, selected_id)     # ← objeto ligado a este db_session

                col1, col2 = st.columns(2)
                new_status = col1.selectbox(
                    "Status",
                    [s.value for s in SessionStatus],
                    index=list(SessionStatus).index(session.status)
                )
                notes = col2.text_area("Notes", value=session.notes or "")

                col_save, col_del = st.columns(2)
                save_clicked   = col_save.form_submit_button("Save",   type="secondary")
                delete_clicked = col_del.form_submit_button("Delete", type="secondary")

                if delete_clicked:
                    # Guardamos el ID de la sesión candidata en el estado global
                    st.session_state["delete_candidate"] = selected_id

                elif save_clicked:
                    session.status = SessionStatus(new_status)
                    session.notes  = notes
                    db_session.commit()
                    st.success("Changes saved")
                    st.rerun()

        # -------------- DIÁLOGO FUERA DEL FORM -----------------
        if "delete_candidate" in st.session_state:
            sid = st.session_state["delete_candidate"]
            session_to_delete = db_session.get(Session, sid)   # objeto ligado a este db_session

            @st.dialog("Confirm delete")
            def confirm_delete():
                st.warning(f"Do you really want to delete Session #{sid}? This action cannot be undone.")
                c1, c2 = st.columns(2)
                if c1.button("Delete", type="primary"):
                    db_session.delete(session_to_delete)
                    db_session.commit()
                    st.session_state.pop("delete_candidate")
                    st.success("Session deleted")
                    st.rerun()      # cierra el diálogo y refresca la lista
                if c2.button("Cancel"):
                    st.session_state.pop("delete_candidate")
                    st.info("Deletion canceled")
                    st.rerun()      # solo cierra el diálogo

            #  ←– abrimos el diálogo
            confirm_delete()
    
    # Añadir nueva sesión
    st.subheader("New Session")
    
    # Obtener lista de jugadores para seleccionar
    players = db_session.query(Player).join(User).filter(User.is_active == True).all()
    player_options = [(p.player_id, p.user.name) for p in players]
    
    # --------------------------------- CONFIG ---------------------------------
    hours_start = [dt.time(h, 0) for h in range(8, 19)]   # 08:00 → 18:00
    hours_end   = [dt.time(h, 0) for h in range(9, 20)]   # 09:00 → 19:00

    # Valores por defecto de los selectores (solo la primera vez)
    if "start_hour_def" not in st.session_state:
        st.session_state["start_hour_def"] = dt.time(8, 0)
    if "end_hour_def" not in st.session_state:
        st.session_state["end_hour_def"] = dt.time(9, 0)

    # -------------------------------- FORM -----------------------------------
    st.subheader("New Session")

    with st.form("new_session_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        # -------- columna 1 : jugador + fecha -----------
        with col1:
            player_id = st.selectbox(
                "Player",
                options=[p[0] for p in player_options],
                format_func=lambda x: next(p[1] for p in player_options if p[0] == x)
            )

            session_date = st.date_input(
                "Date",
                value=dt.date.today(),
                min_value=dt.date.today(),
                max_value=dt.date.today() + dt.timedelta(days=90)
            )

        # -------- columna 2 : horas ---------------------
        with col2:
            start_time = st.selectbox(
                "Start hour",
                options=hours_start,
                index=hours_start.index(st.session_state["start_hour_def"]),
                format_func=lambda t: t.strftime("%H:%M")
            )

            end_time = st.selectbox(
                "End hour",
                options=hours_end,
                index=hours_end.index(st.session_state["end_hour_def"]),
                format_func=lambda t: t.strftime("%H:%M")
            )

        notes = st.text_area("Notes")

        # -------------- botón submit --------------------
        submit = st.form_submit_button("Save Session")

        if submit:
            # Validación: fin > inicio
            start_dt = dt.datetime.combine(session_date, start_time)
            end_dt   = dt.datetime.combine(session_date, end_time)

            if end_dt <= start_dt:
                st.error("End hour must be later than start hour.")
            else:
                new_session = Session(
                    coach_id  = coach.coach_id,
                    player_id = player_id,
                    start_time = start_dt,
                    end_time   = end_dt,
                    status   = SessionStatus.SCHEDULED,
                    notes    = notes
                )
                db_session.add(new_session)
                db_session.commit()
                push_session(new_session)

                # Guarda las últimas selecciones como “por defecto”
                st.session_state["start_hour_def"] = start_time
                st.session_state["end_hour_def"]   = end_time

                st.success("Session created successfully")
                st.rerun()

def show_admin_dashboard():
    """Muestra el panel de administración completo para administradores."""
    
    
    # Crear pestañas para las diferentes secciones
    tab1, tab2, tab3 = st.tabs(["Sessions", "Users", "Financials"])
    
    with tab1:
        # Mostrar todas las sesiones para administradores
        show_all_sessions()
    
    with tab2:
        # Mostrar gestión de usuarios
        show_user_management()
    
    with tab3:
        # Mostrar estadísticas
        
        df = get_accounting_df()
        st.subheader("Financials (Google Sheets)")
        st.dataframe(df, hide_index=True)
        st.metric("Balance €", df["Gastos"].sum() - df["Ingresos"].sum())
        show_statistics()
    
    db_session = get_db_session()
    db_session.close()

def show_all_sessions():
    """Muestra todas las sesiones para los administradores."""
    db_session = get_db_session()

    st.subheader("Sessions Calendar")
    
    # Filtros de fecha
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "From", 
            value=dt.datetime.now().date() - dt.timedelta(days=7),
            key="admin_start_date"
        )
    with col2:
        end_date = st.date_input(
            "To", 
            value=dt.datetime.now().date() + dt.timedelta(days=7),
            key="admin_end_date"
        )

    # Filtro de estado
    status_values = [s.value for s in SessionStatus]
    status_filter = st.multiselect(
        "Status", 
        options=status_values,
        default=status_values
    )
    
    # Filtro de coach
    coaches = db_session.query(Coach).join(User).all()
    coach_options = [(c.coach_id, c.user.name) for c in coaches]
    coach_options.insert(0, (None, "All Coaches"))
    
    selected_coach = st.selectbox(
        "Coach:", 
        options=[c[0] for c in coach_options],
        format_func=lambda x: next((c[1] for c in coach_options if c[0] == x), ""),
        index=0
    )
    
    if end_date < start_date:
        st.error("The 'To' date must be on or after the 'From' date.")
    else:
        # Convertir a datetime solo si las fechas son válidas
        start_datetime = dt.datetime.combine(start_date, dt.time.min)
        end_datetime   = dt.datetime.combine(end_date,   dt.time.max)

        # Estados seleccionados → lista de Enum (o None)
        status_enums = (
            [SessionStatus(s) for s in status_filter]
            if status_filter else None
        )

        # Llamada al helper  (coach_id solo si se ha filtrado)
        sessions = get_sessions(
            start   = start_datetime,
            end     = end_datetime,
            coach_id = selected_coach if selected_coach else None,
            statuses = status_enums
        )

    # Mostrar calendario global
    
    show_calendar("", sessions, key="my_cal")

    # Mostrar las sesiones
    if not sessions:
        st.info("There are no sessions that match the filters.")
    else:
        # Preparar datos para mostrar
        sessions_data = []
        for session in sessions:
            coach = db_session.query(Coach).filter(Coach.coach_id == session.coach_id).first()
            player = db_session.query(Player).filter(Player.player_id == session.player_id).first()
            
            coach_name = coach.user.name if coach and coach.user else "Coach not founded"
            player_name = player.user.name if player and player.user else "Player not founded"
            
            sessions_data.append({
                "ID": session.id,
                "Coach": coach_name,
                "Player": player_name,
                "Date": session.start_time.strftime("%d/%m/%Y"),
                "Start Time": session.start_time.strftime("%H:%M"),
                "End Time": session.end_time.strftime("%H:%M") if session.end_time else "No establecida",
                "Status": session.status.value,           
            })
        
        # Crear DataFrame para mostrar
        df = pd.DataFrame(sessions_data)
               
        # Add styling based on status
        def style_sessions(row):
            if row["Status"] == "completed":
                return ["background-color: rgba(76, 175, 80, 0.2)"] * len(row)
            elif row["Status"] == "canceled":
                return ["background-color: rgba(244, 67, 54, 0.2)"] * len(row)
            elif row["Status"] == "scheduled":
                return ["background-color: rgba(33, 150, 243, 0.2)"] * len(row)
            return [""] * len(row)

        # Apply styling
        styled_df = df.style.apply(style_sessions, axis=1)

        # Mostrar calendario como tabla
        st.dataframe(
            styled_df, 
            column_config={
                "ID": st.column_config.NumberColumn(width="small"),
                "Coach": st.column_config.TextColumn(width="medium"),
                "Player": st.column_config.TextColumn(width="medium"),
                "Date": st.column_config.TextColumn(width="small"),
                "Start Time": st.column_config.TextColumn(width="small"),
                "End Time": st.column_config.TextColumn(width="small"),
                "Status": st.column_config.TextColumn(width="small")
            },
            hide_index=True
        )
        
        # Opciones de gestión de sesiones para administradores
        st.subheader("Sessions Management")

        tab1, tab2 = st.tabs(["Create Session", "Edit Session"])
        # --------------------------------- CONFIG ---------------------------------
        hours_start = [dt.time(h, 0) for h in range(8, 19)]   # 08:00 → 18:00
        hours_end   = [dt.time(h, 0) for h in range(9, 20)]   # 09:00 → 19:00

        # Valores por defecto de los selectores (solo la primera vez)
        if "start_hour_def" not in st.session_state:
            st.session_state["start_hour_def"] = dt.time(8, 0)
        if "end_hour_def" not in st.session_state:
            st.session_state["end_hour_def"] = dt.time(9, 0)
        # ---------------------------------------------------------------------
        # 1. CREATE SESSION
        # ---------------------------------------------------------------------
        with tab1:
            st.subheader("New Session")

            # --- listas de jugadores y coaches activos ---
            players  = db_session.query(Player).join(User).filter(User.is_active).all()
            coaches  = db_session.query(Coach).join(User).filter(User.is_active).all()

            player_opts = [(p.player_id, p.user.name) for p in players]
            coach_opts  = [(c.coach_id,  c.user.name) for c in coaches]

            # --- formulario ---
            with st.form("admin_new_session", clear_on_submit=True):
                col1, col2 = st.columns(2)

                # ------------------ columna 1 ------------------
                with col1:
                    player_id = st.selectbox(
                        "Player",
                        options=[p[0] for p in player_opts],
                        format_func=lambda x: next(n for i, n in player_opts if i == x)
                    )

                    coach_id = st.selectbox(
                        "Coach",
                        options=[c[0] for c in coach_opts],
                        format_func=lambda x: next(n for i, n in coach_opts if i == x)
                    )

                    session_date = st.date_input(
                        "Date",
                        value=dt.date.today(),
                        min_value=dt.date.today(),
                        max_value=dt.date.today() + dt.timedelta(days=90)
                    )

                # ------------------ columna 2 ------------------
                with col2:
                    start_time = st.selectbox(
                    "Start hour",
                    options=hours_start,
                    index=hours_start.index(st.session_state["start_hour_def"]),
                    format_func=lambda t: t.strftime("%H:%M")
                    )

                    end_time = st.selectbox(
                        "End hour",
                        options=hours_end,
                        index=hours_end.index(st.session_state["end_hour_def"]),
                        format_func=lambda t: t.strftime("%H:%M")
                    )

                notes = st.text_area("Notes")
                submit = st.form_submit_button("Save Session")

                if submit:
                    start_dt = dt.datetime.combine(session_date, start_time)
                    end_dt   = dt.datetime.combine(session_date, end_time)

                    if end_dt <= start_dt:
                        st.error("End time should be later than start time.")
                    else:
                        new_session = Session(
                            coach_id   = coach_id,
                            player_id  = player_id,
                            start_time = start_dt,
                            end_time   = end_dt,
                            status     = SessionStatus.SCHEDULED,
                            notes      = notes
                        )
                        db_session.add(new_session)
                        db_session.commit()
                        push_session(new_session)
                        st.success("Session created successfully")
                        st.rerun()

        # ---------------------------------------------------------------------
        # 2. EDIT / DELETE SESSION
        # ---------------------------------------------------------------------
        with tab2:
            st.subheader("Edit / Delete Session")

            sessions = db_session.query(Session).all()
            if not sessions:
                st.info("There are no sessions to manage.")
            else:
                desc = {
                    s.id: f"#{s.id} – {s.coach.user.name} with {s.player.user.name} "
                        f"({s.start_time:%d/%m %H:%M})"
                    for s in sessions
                }

                hours_start = [dt.time(h, 0) for h in range(8, 19)]   # 08‑18
                hours_end   = [dt.time(h, 0) for h in range(9, 20)]   # 09‑19

                # -------- contenedor visual único -------------
                with st.container():
                    # -------- 1. selector reactivo (fuera del form) -------
                    sel_id = st.selectbox(
                        "Select session",
                        options=list(desc.keys()),
                        format_func=lambda x: desc[x],
                        key="sess_to_edit"
                    )
                    session = db_session.get(Session, sel_id)

                    # -------- 2. formulario con los campos editables ------
                    with st.form(f"admin_edit_{sel_id}", clear_on_submit=False):

                        col1, col2 = st.columns(2)

                        # ------ columna 1 : coach y status ------
                        with col1:
                            new_coach_id = st.selectbox(
                                "Coach",
                                options=[c[0] for c in coach_opts],
                                index=[c[0] for c in coach_opts].index(session.coach_id),
                                format_func=lambda x: next(n for i, n in coach_opts if i == x)
                            )

                            new_status = st.selectbox(
                                "Status",
                                options=[s.value for s in SessionStatus],
                                index=list(SessionStatus).index(session.status)
                            )

                        # ------ columna 2 : horas ------
                        with col2:
                            start_time = st.selectbox(
                                "Start hour",
                                options=hours_start,
                                index=hours_start.index(session.start_time.time()),
                                format_func=lambda t: t.strftime("%H:%M")
                            )

                            end_opts = [t for t in hours_end if t > start_time]
                            end_time = st.selectbox(
                                "End hour",
                                options=end_opts,
                                index=end_opts.index(session.end_time.time())
                                    if session.end_time and session.end_time.time() in end_opts else 0,
                                format_func=lambda t: t.strftime("%H:%M")
                            )

                        # ------ botones ------
                        col_save, col_del = st.columns(2)
                        save_clicked = col_save.form_submit_button("Save",   type="secondary")
                        del_clicked  = col_del.form_submit_button("Delete", type="secondary")

                        # --- guardar ---
                        if save_clicked:
                            start_dt = dt.datetime.combine(session.start_time.date(), start_time)
                            end_dt   = dt.datetime.combine(session.end_time.date(),   end_time)

                            if end_dt <= start_dt:
                                st.error("End hour must be later than start hour.")
                            else:
                                session.coach_id   = new_coach_id
                                session.status     = SessionStatus(new_status)
                                session.start_time = start_dt
                                session.end_time   = end_dt
                                db_session.commit()
                                st.success(f"Session #{sel_id} updated correctly")
                                st.rerun()

                        # --- borrar (1ª fase) ---
                        if del_clicked:
                            st.session_state["admin_del_candidate"] = sel_id

                # -------- diálogo de confirmación fuera del form ----------
                if "admin_del_candidate" in st.session_state:
                    sid = st.session_state["admin_del_candidate"]
                    session_to_del = db_session.get(Session, sid)

                    @st.dialog("Confirm delete")
                    def confirm_delete():
                        st.warning(f"Do you really want to delete Session #{sid}? "
                                "This action cannot be undone.")
                        c1, c2 = st.columns(2)
                        if c1.button("Delete", type="primary"):
                            db_session.delete(session_to_del)
                            db_session.commit()
                            st.session_state.pop("admin_del_candidate")
                            st.success("Session deleted")
                            st.rerun()
                        if c2.button("Cancel"):
                            st.session_state.pop("admin_del_candidate")
                            st.info("Deletion canceled")
                            st.rerun()

                    confirm_delete()
        
        

def show_user_management():
    """Muestra la gestión de usuarios para administradores."""
    db_session = get_db_session()
    
    st.subheader("User Management")
    
    # Filtros
    user_types = ["All"] + [t.name for t in UserType]
    selected_type = st.selectbox("User Type:", options=user_types)
    
    # Construir consulta base
    query = db_session.query(User)
    
    # Aplicar filtros
    if selected_type != "All":
        query = query.filter(User.user_type == UserType[selected_type])
    
    # Ejecutar consulta
    users = query.order_by(User.name).all()
    
    if not users:
        st.info("There are no users that match the filters.")
        return
    
    # Obtener estadísticas de sesiones por coach
    stats_sq = (
    db_session.query(
        Session.coach_id.label("uid"),
        func.sum(case((Session.status == SessionStatus.COMPLETED, 1), else_=0)).label("comp"),
        func.sum(case((Session.status == SessionStatus.SCHEDULED, 1), else_=0)).label("prog"),
        func.sum(case((Session.status == SessionStatus.CANCELED,  1), else_=0)).label("canc"),
    )
    .group_by(Session.coach_id)
    .subquery()
)
    
    # Preparar datos para mostrar
    users_data = []
    for user in users:
        is_active = getattr(user, 'is_active', True)  # Para compatibilidad si no existe el campo
        comp = prog = canc = 0
        if user.user_type == UserType.coach:
            row = db_session.query(stats_sq).filter(stats_sq.c.uid == user.coach_profile.coach_id).first()
            if row:
                comp, prog, canc = row.comp, row.prog, row.canc
        users_data.append({
            "ID": user.user_id,
            "Name": user.name,
            "Username": user.username,
            "Email": user.email,
            "User Type": user.user_type.name,
            "Comp": comp,
            "Prog": prog,
            "Canc": canc,
            "Active": "Sí" if is_active else "No",
            "user_obj": user  # Para usar después, no se muestra
        })
    
    # Crear DataFrame para mostrar
    df = pd.DataFrame(users_data)
    user_objects = df.pop("user_obj").reset_index(drop=True)  # Quitar de la visualización pero mantener para uso posterior
    
        # Add styling based on user type
    def style_users(row):
        if row["User Type"] == "admin":
            return ["background-color: rgba(244, 67, 54, 0.2)"] * len(row)
        elif row["User Type"] == "coach":
            return ["background-color: rgba(255, 193, 7, 0.2)"] * len(row)
        elif row["User Type"] == "player":
            return ["background-color: rgba(76, 175, 80, 0.2)"] * len(row)
        return [""] * len(row)

    # Apply styling
    styled_df = df.style.apply(style_users, axis=1)

    # Mostrar usuarios como tabla
    st.dataframe(
        styled_df,
        column_config={
            "ID": st.column_config.NumberColumn(width="small"),
            "Name": st.column_config.TextColumn(width="medium"),
            "Username": st.column_config.TextColumn(width="medium"),
            "Email": st.column_config.TextColumn(width="medium"),
            "User Type": st.column_config.TextColumn(width="small"),
            "Comp":  st.column_config.NumberColumn("Completadas", width="small"),
            "Prog":  st.column_config.NumberColumn("Programadas", width="small"),
            "Canc":  st.column_config.NumberColumn("Canceladas", width="small"),
            "Activo": st.column_config.TextColumn(width="small")
        },
        hide_index=True
    )
    
    # Opciones de gestión de usuarios
    col1, col2 = st.columns(2)
    
    with col1:
        # Activar/desactivar usuario
        user_to_toggle = st.selectbox(
            "Select user to activate/deactivate:",
            options=[u["ID"] for u in users_data],
            format_func=lambda x: f"{next((u['Name'] for u in users_data if u['ID'] == x), '')} ({next((u['Username'] for u in users_data if u['ID'] == x), '')})"
        )
        
        # Encontrar índice del usuario seleccionado
        user_idx = next((i for i, u in enumerate(users_data) if u["ID"] == user_to_toggle), None)
        if user_idx is not None:
            user = user_objects.iloc[user_idx]
            
            # Verificar si el campo is_active existe
            if hasattr(user, 'is_active'):
                toggle_label = "Deactivate" if user.is_active else "Activar"
                if st.button(f"{toggle_label} User"):
                    user.is_active = not user.is_active
                    db_session.commit()
                    st.success(f"User {toggle_label.lower()} deactivated successfully")
                    st.rerun()
            else:
                st.info("The user object does not have the 'is_active' field.")
    
    with col2:
        st.write("Create new user")
        st.write("Use the configuration page to create users")

def show_statistics():
    """Muestra estadísticas globales para administradores."""
    db_session = get_db_session()
    
    st.subheader("Global Statistics")
    
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
        st.metric("Total Users", total_users)
        st.metric("Total Players", total_players)
    
    with col2:
        st.metric("Total Coaches", total_coaches)
        st.metric("Ratio Players/Coaches", round(total_players/total_coaches, 1) if total_coaches > 0 else 0)
    
    with col3:
        st.metric("Total Sessions", total_sessions)
        percentage = int(completed_sessions/total_sessions*100) if total_sessions > 0 else 0
        st.metric("Completed Sessions", f"{completed_sessions} ({percentage}%)")
    
    # Gráfico de sesiones por estado
    try:
        scheduled_sessions = db_session.query(Session).filter(Session.status == SessionStatus.SCHEDULED).count()
        canceled_sessions = db_session.query(Session).filter(Session.status == SessionStatus.CANCELED).count()
        
        status_data = pd.DataFrame({
            "Status": ["Scheduled", "Completed", "Canceled"],
            "Amount": [scheduled_sessions, completed_sessions, canceled_sessions]
        })
        
        st.subheader("Sessions by Status")
        st.bar_chart(status_data, x="Status", y="Amount")
    except Exception as e:
        st.error(f"Error generating sessions stadistics: {str(e)}")
        st.info("Make sure there are sessions in the database to display statistics..")

def show_content():
    """Función principal para mostrar el contenido de la sección Administration."""
    st.markdown('<h3 class="section-title">Administration</h3>', unsafe_allow_html=True)
    
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
# pages/administration.py
import streamlit as st
import pandas as pd
import plotly.express as px
import datetime as dt
import os
import sys
from typing import Optional, List
import plotly.graph_objects as go
from sqlalchemy import func, case

from models import User, Coach, Session, SessionStatus, UserType, Player
from controllers.session_controller import (
    SessionController,
    create_session_with_calendar,  
    update_session_with_calendar,    
    delete_session_with_calendar,  
    get_coach_stats,              
    get_sessions_for_display,     
    format_sessions_for_table,    
    get_available_coaches,        
    get_available_players,        
    get_sessions_for_editing  
)        
from controllers.internal_calendar import show_calendar
from controllers.sheets_controller import get_accounting_df
from controllers.db import get_db_session
from common.notifications import get_sync_problems
from controllers.sync_coordinator import filter_sync_results_by_coach, get_coach_id_if_needed
# 🆕 NUEVO: Import para eliminar duplicaciones de date range validation
from controllers.validation_controller import ValidationController

# Agregar la ruta raíz al path de Python para importar config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def show_coach_sync_alerts():
    """
    Muestra alertas de sync específicas para coaches de forma no invasiva.
    NO interfiere con layout de pestañas.
    """
    
    problems = get_sync_problems()
    if not problems:
        return
    
    rejected = problems.get('rejected', [])
    warnings = problems.get('warnings', [])
    
    if not rejected and not warnings:
        return
    
    if rejected:
        with st.expander("🚫 Synchronisation Problems Detected", expanded=False):
            st.error(f"❌ {len(rejected)} rejected events in the last synchronisation")
            
            if rejected:
                first = rejected[0]
                st.write(f"**Example**: {first['title']} - {first.get('date', 'N/A')}")
                st.write(f"**Problem**: {first['reason']}")
            
            if len(rejected) > 1:
                st.info(f"+ {len(rejected) - 1} events more")
            
            st.info("💡 **Solution**: Update Session in Google Calendar")
    
    elif warnings:
        with st.expander("⚠️ Synchronisation Warnings", expanded=False):
            st.warning(f"⚠️ {len(warnings)} imported events at less than ideal times")
            
            if warnings:
                first = warnings[0]
                st.write(f"**Example**: {first['title']} - {first.get('date', 'N/A')}")
                if first.get('warnings'):
                    st.write(f"**Warning**: {first['warnings'][0]}")
            
            if len(warnings) > 1:
                st.info(f"+ {len(warnings) - 1} eventos más")
            
            st.info("💡 **Note**: The sessions were imported correctly but have times outside the recommended range (8:00-18:00).")
    st.divider()

def show_coach_calendar():
    """Muestra el calendario de sesiones para un coach - SIMPLIFICADO."""
    # Obtener coach usando el controller
    user_id = st.session_state.get("user_id")
    
    with SessionController() as controller:
        # Buscar coach actual
        coach = controller.db.query(Coach).join(User).filter(User.user_id == user_id).first()
        
        if not coach:
            st.error("No coach information found.")
            return
        
        # Usar controller para estadísticas
        stats = controller.get_coach_stats(coach.coach_id)
        
        # Mostrar métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Scheduled", stats["scheduled"])
        c2.metric("Completed", stats["completed"])
        c3.metric("Canceled", stats["canceled"])
        
        st.subheader(f"Calendar of {coach.user.name}")

        # Filtros de fecha - UI solo
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "From", 
                value=dt.datetime.now().date() - dt.timedelta(days=7),
                key="coach_start_date"
            )
        with col2:
            end_date = st.date_input(
                "To", 
                value=dt.datetime.now().date() + dt.timedelta(days=7),
                key="coach_end_date"
            )

        status_values = [s.value for s in SessionStatus]
        status_filter = st.multiselect(
            "Status", 
            options=status_values,
            default=status_values,
            key="coach_status_filter"
        )
        
        # 🔄 REFACTORIZADO: Usar ValidationController para date range validation
        is_valid, error = ValidationController.validate_date_range(start_date, end_date)
        if not is_valid:
            st.error(error)
            return

        # Usar controller para obtener sesiones
        sessions = controller.get_sessions_for_display(
            start_date=start_date,
            end_date=end_date,
            coach_id=coach.coach_id,
            status_filter=status_filter
        )
        
        # Mostrar calendario
        show_calendar("", sessions, key="coach_cal")

        # Usar controller para formatear datos de tabla
        if sessions:
            st.subheader("Sessions List")
            formatted_data = controller.format_sessions_for_table(sessions)
            
            # Crear DataFrame y aplicar estilos
            df = pd.DataFrame(formatted_data)
            
            def style_sessions(row):
                if row["Status"] == "completed":
                    return ["background-color: rgba(76, 175, 80, 0.2)"] * len(row)
                elif row["Status"] == "canceled":
                    return ["background-color: rgba(244, 67, 54, 0.2)"] * len(row)
                elif row["Status"] == "scheduled":
                    return ["background-color: rgba(33, 150, 243, 0.2)"] * len(row)
                return [""] * len(row)

            styled_df = df.style.apply(style_sessions, axis=1)
            
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
        else:
            st.info(f"There are no scheduled sessions between {start_date.strftime('%d/%m/%Y')} and {end_date.strftime('%d/%m/%Y')}.")

    # Sync details display
    if st.session_state.get("show_sync_details", False):
        st.session_state["show_sync_details"] = False
        
        with st.container():
            if 'last_sync_result' in st.session_state:
                result = st.session_state['last_sync_result']

                coach_id = get_coach_id_if_needed()
                if coach_id:
                    result = filter_sync_results_by_coach(result, coach_id)
                    st.info(f"Showing Events for Coach ID: {coach_id}")

                rejected = result.get('rejected_events', [])
                warnings = result.get('warning_events', [])
                
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                col1.metric("📥 Imported", result.get('imported', 0))
                col2.metric("🔄 Updated", result.get('updated', 0))  
                col3.metric("🗑️ Deleted", result.get('deleted', 0))
                col4.metric("🚫 Rejected", len(result.get('rejected_events', [])))
                col5.metric("⚠️ Warnings", len(result.get('warning_events', [])))
                col6.metric("⏱️ Duration", f"{result.get('duration', 0):.1f}s")
                
                if rejected or warnings:
                    if rejected:
                        st.subheader("🚫 Rejected Events")
                        for event in rejected:
                            st.error(f"**{event['title']}** - {event['date']} {event['time']}")
                            st.write(f"❌ **Problem**: {event['reason']}")
                            st.write(f"💡 **Solution**: {event['suggestion']}")
                            st.markdown("---")
                            
                    if warnings:
                        st.subheader("⚠️ Events with Warnings")
                        for event in warnings:
                            st.warning(f"**{event['title']}** - {event['date']} {event['time']}")
                            for w in event.get('warnings', []):
                                st.write(f"⚠️ {w}")
                            st.write("✅ **State**: Synced successfully")
                            st.markdown("---")
                else:
                    st.success("✅ No synchronisation problems")
            else:
                st.info("No sync data available")

    # Formularios usando controller
    show_session_management(coach_id=coach.coach_id, is_admin=False)


def show_session_management(coach_id: Optional[int] = None, is_admin: bool = True):
    """
    Formularios unificados para crear/editar sesiones.
    Elimina duplicación entre coach y admin.
    
    Args:
        coach_id: Si se especifica, restringe a sesiones de ese coach
        is_admin: Si True, permite seleccionar cualquier coach
    """
    st.subheader("My Sessions" if not is_admin else "Sessions Management")

    with SessionController() as controller:
        # Obtener opciones para selectores
        coaches = controller.get_available_coaches()
        players = controller.get_available_players()
        
        tab1, tab2 = st.tabs(["Create Session", "Edit Session"])


        # Tab 1: CREAR SESIÓN (horarios estrictos)

        with tab1:
            st.subheader("New Session")

            # 🔧 Horarios estrictos para CREAR sesiones nuevas
            hours_start_create = [dt.time(h, 0) for h in range(8, 19)]  # 8:00-18:00
            hours_end_create = [dt.time(h, 0) for h in range(9, 20)]    # 9:00-19:00

            with st.form("session_form", clear_on_submit=True):
                col1, col2 = st.columns(2)

                with col1:
                    # Coach selector (solo si es admin)
                    if is_admin:
                        selected_coach_id = st.selectbox(
                            "Coach",
                            options=[c[0] for c in coaches],
                            format_func=lambda x: next(n for i, n in coaches if i == x)
                        )
                    else:
                        selected_coach_id = coach_id
                        st.info(f"Coach: {next(n for i, n in coaches if i == coach_id)}")

                    player_id = st.selectbox(
                        "Player",
                        options=[p[0] for p in players],
                        format_func=lambda x: next(n for i, n in players if i == x)
                    )

                    session_date = st.date_input(
                        "Date",
                        value=dt.date.today(),
                        min_value=dt.date.today(),
                        max_value=dt.date.today() + dt.timedelta(days=90)
                    )

                with col2:
                    start_time = st.selectbox(
                        "Start hour",
                        options=hours_start_create,
                        format_func=lambda t: t.strftime("%H:%M")
                    )

                    end_time = st.selectbox(
                        "End hour",
                        options=hours_end_create,
                        format_func=lambda t: t.strftime("%H:%M")
                    )

                notes = st.text_area("Notes")
                submit = st.form_submit_button("Save Session")

                if submit:
                    # Usar función wrapper con sincronización
                    if selected_coach_id is None:
                        st.error("Please select a coach")
                        return
                        
                    success, message, new_session = create_session_with_calendar(
                        coach_id=selected_coach_id,
                        player_id=player_id,
                        session_date=session_date,
                        start_time=start_time,
                        end_time=end_time,
                        notes=notes
                    )
                    
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)


        # Tab 2: EDITAR SESIÓN (horarios flexibles)

        with tab2:
            st.subheader("Edit / Delete Session")

            # Usar controller para obtener sesiones editables
            session_descriptions = controller.get_sessions_for_editing(coach_id=coach_id)

            if not session_descriptions:
                st.info("No sessions available to manage." if is_admin else "You have no sessions to manage.")
                return

            selected_id = st.selectbox(
                "Select session",
                options=list(session_descriptions.keys()),
                format_func=lambda x: session_descriptions[x],
                key="session_to_edit"
            )

            # Obtener sesión seleccionada
            session = controller.db.get(Session, selected_id)

            # 🔧 HORARIOS FLEXIBLES para editar (adaptarse a sesiones existentes)
            def get_flexible_hours(existing_time: dt.time, base_hours: List[dt.time]) -> List[dt.time]:
                """
                Crea lista de horarios que incluye el horario existente si no está en el rango base.
                """
                if existing_time in base_hours:
                    return base_hours
                
                # Si el horario existente está fuera del rango, ampliarlo
                all_hours = [dt.time(h, 0) for h in range(6, 23)]  # 6:00-22:00
                if existing_time in all_hours:
                    return all_hours
                
                # Si está completamente fuera, agregarlo manualmente
                extended_hours = base_hours + [existing_time]
                return sorted(extended_hours)

            # Horarios base preferidos (8:00-18:00)
            base_start = [dt.time(h, 0) for h in range(8, 19)]
            base_end = [dt.time(h, 0) for h in range(9, 20)]
            
            # Horarios flexibles adaptados a la sesión actual
            hours_start_edit = get_flexible_hours(session.start_time.time(), base_start)
            hours_end_edit = get_flexible_hours(session.end_time.time(), base_end)

            # 🔧 Mostrar advertencia si está fuera del horario recomendado
            if (session.start_time.time() < dt.time(8, 0) or 
                session.start_time.time() >= dt.time(18, 0) or
                session.end_time.time() <= dt.time(9, 0) or 
                session.end_time.time() > dt.time(19, 0)):
                
                st.warning("⚠️ **Note**: This session has times outside the recommended range (8:00-18:00). "
                        "Consider rescheduling to a standard time slot.")

            with st.form(f"edit_session_{selected_id}", clear_on_submit=True):
                col1, col2 = st.columns(2)

                with col1:
                    # Coach (solo si es admin)
                    if is_admin:
                        new_coach_id = st.selectbox(
                            "Coach",
                            options=[c[0] for c in coaches],
                            index=[c[0] for c in coaches].index(session.coach_id),
                            format_func=lambda x: next(n for i, n in coaches if i == x)
                        )
                    else:
                        new_coach_id = session.coach_id
                        st.info(f"Coach: {session.coach.user.name}")

                    new_player_id = st.selectbox(
                        "Player",
                        options=[p[0] for p in players],
                        index=[p[0] for p in players].index(session.player_id),
                        format_func=lambda x: next(n for i, n in players if i == x)
                    )

                    new_status = st.selectbox(
                        "Status",
                        options=[s.value for s in SessionStatus],
                        index=list(SessionStatus).index(session.status)
                    )

                with col2:
                    # Validar fecha para el date_input
                    current_date = session.start_time.date()
                    min_date = dt.date.today()
                    max_date = dt.date.today() + dt.timedelta(days=90)
                    
                    # Si la fecha actual está fuera del rango, usar fecha válida
                    if current_date < min_date or current_date > max_date:
                        display_date = dt.date.today()
                    else:
                        display_date = current_date

                    session_date = st.date_input(
                        "Date",
                        value=display_date,
                        min_value=min_date,
                        max_value=max_date
                    )

                    # Usar horarios flexibles con índices seguros
                    try:
                        start_index = hours_start_edit.index(session.start_time.time())
                    except ValueError:
                        start_index = 0  # Fallback al primer horario disponible
                        st.error(f"⚠️ Original start time {session.start_time.time().strftime('%H:%M')} not available, defaulting to {hours_start_edit[0].strftime('%H:%M')}")

                    try:
                        end_index = hours_end_edit.index(session.end_time.time())
                    except ValueError:
                        end_index = 0  # Fallback al primer horario disponible
                        st.error(f"⚠️ Original end time {session.end_time.time().strftime('%H:%M')} not available, defaulting to {hours_end_edit[0].strftime('%H:%M')}")

                    start_time = st.selectbox(
                        "Start hour",
                        options=hours_start_edit,
                        index=start_index,
                        format_func=lambda t: t.strftime("%H:%M")
                    )

                    end_time = st.selectbox(
                        "End hour",
                        options=hours_end_edit,
                        index=end_index,
                        format_func=lambda t: t.strftime("%H:%M")
                    )

                notes = st.text_area("Notes", value=session.notes or "")

                # Botones
                col_save, col_del = st.columns(2)
                save_clicked = col_save.form_submit_button("Save", type="secondary")
                del_clicked = col_del.form_submit_button("Delete", type="secondary")

                if save_clicked:
                    # Usar función wrapper con sincronización
                    success, message = update_session_with_calendar(
                        session_id=selected_id,
                        coach_id=new_coach_id,
                        player_id=new_player_id,
                        session_date=session_date,
                        start_time=start_time,
                        end_time=end_time,
                        status=new_status,
                        notes=notes
                    )
                    
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

                if del_clicked:
                    # Marcar para confirmación
                    st.session_state["delete_candidate"] = selected_id

            # Diálogo de confirmación de eliminación
            if st.session_state.get("delete_candidate") == selected_id:
                @st.dialog("Confirm delete")
                def confirm_delete():
                    st.warning(f"Do you really want to delete Session #{selected_id}? This action cannot be undone.")
                    c1, c2 = st.columns(2)
                    
                    if c1.button("Delete", type="primary"):
                        # Usar función wrapper con sincronización
                        success, message = delete_session_with_calendar(selected_id)
                        
                        if "delete_candidate" in st.session_state:
                            del st.session_state["delete_candidate"]
                        
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                        st.rerun()
                    
                    if c2.button("Cancel"):
                        if "delete_candidate" in st.session_state:
                            del st.session_state["delete_candidate"]
                        st.info("Deletion canceled")
                        st.rerun()

                confirm_delete()


def show_all_sessions():
    """Muestra todas las sesiones para los administradores - SIMPLIFICADO."""
    st.subheader("Sessions Calendar")
    
    with SessionController() as controller:
        # Filtros de UI
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

        status_values = [s.value for s in SessionStatus]
        status_filter = st.multiselect(
            "Status", 
            options=status_values,
            default=status_values
        )
        
        # Filtro de coach
        coaches = controller.get_available_coaches()
        coach_options = [(None, "All Coaches")] + coaches
        selected_coach = st.selectbox(
            "Coach:", 
            options=[c[0] for c in coach_options],
            format_func=lambda x: next((c[1] for c in coach_options if c[0] == x), ""),
            index=0
        )
        
        # 🔄 REFACTORIZADO: Usar ValidationController para date range validation
        is_valid, error = ValidationController.validate_date_range(start_date, end_date)
        if not is_valid:
            st.error(error)
            return

        # Usar controller para obtener sesiones
        sessions = controller.get_sessions_for_display(
            start_date=start_date,
            end_date=end_date,
            coach_id=selected_coach,
            status_filter=status_filter
        )

        # Mostrar calendario
        show_calendar("", sessions, key="admin_cal")

        # Mostrar tabla de sesiones
        if sessions:
            formatted_data = controller.format_sessions_for_table(sessions)
            df = pd.DataFrame(formatted_data)
            
            def style_sessions(row):
                if row["Status"] == "completed":
                    return ["background-color: rgba(76, 175, 80, 0.2)"] * len(row)
                elif row["Status"] == "canceled":
                    return ["background-color: rgba(244, 67, 54, 0.2)"] * len(row)
                elif row["Status"] == "scheduled":
                    return ["background-color: rgba(33, 150, 243, 0.2)"] * len(row)
                return [""] * len(row)

            styled_df = df.style.apply(style_sessions, axis=1)

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
        else:
            st.info("There are no sessions that match the filters.")
        
        # Formularios unificados para admin
        show_session_management(coach_id=None, is_admin=True)


def show_financials():
    """Muestra datos financieros - SE MANTIENE IGUAL"""
    df = get_accounting_df()
    df_no_total = df.iloc[:-1].copy()

    st.subheader("Financials (Google Sheets)")
    st.dataframe(df_no_total, hide_index=True)

    total_gastos = df_no_total["Gastos"].sum()
    total_ingresos = df_no_total["Ingresos"].sum()
    balance = total_ingresos - total_gastos

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Balance €", f"{balance:,.2f}")
    with col2:
        st.metric("Ingresos €", f"{total_ingresos:,.2f}")
    with col3:
        st.metric("Gastos €", f"{total_gastos:,.2f}")

    fecha_col = df_no_total.columns[0]
    df_no_total[fecha_col] = pd.to_datetime(df_no_total[fecha_col], errors='coerce')
    df_no_total["Mes"] = df_no_total[fecha_col].dt.to_period("M").astype(str)

    monthly_summary = df_no_total.groupby("Mes").agg({
        "Ingresos": "sum",
        "Gastos": "sum"
    }).reset_index()

    monthly_summary["Balance mensual"] = monthly_summary["Ingresos"] - monthly_summary["Gastos"]
    monthly_summary["Balance acumulado"] = monthly_summary["Balance mensual"].cumsum()

    st.markdown(
        """
        <style>
        .vega-bindings {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.line_chart(monthly_summary.set_index("Mes")["Balance acumulado"])


def show_user_management():
    """Muestra gestión de usuarios - SE MANTIENE IGUAL (lo tocaremos después)"""
    db_session = get_db_session()
    
    st.subheader("User Management")
    
    user_types = ["All"] + [t.name for t in UserType]
    selected_type = st.selectbox("User Type:", options=user_types)
    
    query = db_session.query(User)
    
    if selected_type != "All":
        query = query.filter(User.user_type == UserType[selected_type])
    
    users = query.order_by(User.name).all()
    
    if not users:
        st.info("There are no users that match the filters.")
        db_session.close()
        return
    
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
    
    users_data = []
    for user in users:
        is_active = getattr(user, 'is_active', True)
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
            "user_obj": user
        })
    
    df = pd.DataFrame(users_data)
    user_objects = df.pop("user_obj").reset_index(drop=True)
    
    def style_users(row):
        if row["User Type"] == "admin":
            return ["background-color: rgba(244, 67, 54, 0.2)"] * len(row)
        elif row["User Type"] == "coach":
            return ["background-color: rgba(255, 193, 7, 0.2)"] * len(row)
        elif row["User Type"] == "player":
            return ["background-color: rgba(76, 175, 80, 0.2)"] * len(row)
        return [""] * len(row)

    styled_df = df.style.apply(style_users, axis=1)

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
    
    col1, col2 = st.columns(2)
    
    with col1:
        user_to_toggle = st.selectbox(
            "Select user to activate/deactivate:",
            options=[u["ID"] for u in users_data],
            format_func=lambda x: f"{next((u['Name'] for u in users_data if u['ID'] == x), '')} ({next((u['Username'] for u in users_data if u['ID'] == x), '')})"
        )
        
        user_idx = next((i for i, u in enumerate(users_data) if u["ID"] == user_to_toggle), None)
        if user_idx is not None:
            user = user_objects.iloc[user_idx]
            
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
    
    db_session.close()


def show_admin_dashboard():
    """Panel de administración para administradores."""
    tab1, tab2, tab3 = st.tabs(["Sessions", "Users", "Financials"])
    
    with tab1:
        show_all_sessions()
    
    with tab2:
        show_user_management()
    
    with tab3:
        show_financials()


def show_content():
    """Función principal para mostrar el contenido de la sección Administration."""
    st.markdown('<h3 class="section-title">Administration</h3>', unsafe_allow_html=True)
    
    user_type = st.session_state.get("user_type")
    
    if user_type == "admin":
        show_admin_dashboard()
    elif user_type == "coach":
        show_coach_calendar()
    else:
        st.error("No tienes permisos para acceder a esta sección.")


if __name__ == "__main__":
    show_content()
# callbacks/administration_callbacks.py
"""
Callbacks relacionados con la página de Administration - COPIANDO ESTRUCTURA DE BALLERS
"""
import datetime as dt

import dash_bootstrap_components as dbc
from dash import Input, Output, State, html

from controllers.internal_calendar import show_calendar_dash, update_and_get_sessions
from controllers.session_controller import SessionController
from controllers.validation_controller import ValidationController  # noqa: F401
from models import SessionStatus


def _get_toast_style():
    """Helper function para obtener el estilo consistente del toast."""
    return {
        "position": "fixed",
        "top": "20px",
        "right": "20px",
        "z-index": "1060",
        "min-width": "350px",
        "max-width": "500px",
        "box-shadow": "0 8px 16px rgba(0, 0, 0, 0.15)",
        "border-radius": "8px",
        "animation": "slideInRight 0.3s ease-out",
    }


def _update_calendar_and_table_content(from_date, to_date, coach_filter, status_filter):
    """Helper function para actualizar calendario y tabla."""
    try:
        from controllers.internal_calendar import (
            show_calendar_dash,
            update_and_get_sessions,
        )
        from models import SessionStatus

        # Usar filtros actuales
        if not status_filter:
            status_filter = [s.value for s in SessionStatus]

        # Fechas por defecto
        if not from_date:
            from_date = (dt.datetime.now().date() - dt.timedelta(days=7)).isoformat()
        if not to_date:
            to_date = (dt.datetime.now().date() + dt.timedelta(days=21)).isoformat()

        start_date_obj = dt.datetime.fromisoformat(from_date).date()
        end_date_obj = dt.datetime.fromisoformat(to_date).date()

        # Coach filter
        coach_id = coach_filter if coach_filter and coach_filter != "all" else None

        with SessionController() as controller:
            # Obtener sesiones con auto-actualización
            sessions = update_and_get_sessions(
                controller,
                start_date=start_date_obj,
                end_date=end_date_obj,
                coach_id=coach_id,
                status_filter=status_filter,
            )

            # Crear calendario
            calendar_content = show_calendar_dash(
                sessions, editable=False, key="admin-cal", height=800
            )

            # Crear tabla
            if sessions:
                from pages.ballers_dash import create_sessions_table_dash

                table_content = create_sessions_table_dash(
                    from_date=start_date_obj,
                    to_date=end_date_obj,
                    coach_id=coach_id,  # Añadir coach_id para restricciones
                    status_filter=status_filter,
                )
            else:
                table_content = html.Div(
                    "No sessions found for the selected filters",
                    style={
                        "text-align": "center",
                        "padding": "20px",
                        "color": "#FFFFFF",
                    },
                )

            return calendar_content, table_content
    except Exception as e:
        error_div = html.Div(
            f"Error loading data: {str(e)}",
            style={"color": "red", "text-align": "center", "padding": "20px"},
        )
        return error_div, error_div


def register_administration_callbacks(app):
    """Registra callbacks de Administration copiando estructura de ballers."""

    @app.callback(
        Output("admin-user-type-store", "data"),
        [Input("url", "pathname"), Input("selected-menu-item", "data")],
        [
            State("session-store", "data"),
            State("persistent-session-store", "data"),
            State("session-activity", "data"),
        ],
        prevent_initial_call=False,
    )
    def update_admin_user_type_store(
        pathname, selected_section, session_data, persistent_session_data, activity_data
    ):
        """Actualiza el store de user type basado en los datos de sesión."""
        # Determinar qué session_data usar (misma lógica que en navigation_callbacks)
        if activity_data and activity_data.get("remember_me"):
            session_data = persistent_session_data or {}
        else:
            session_data = session_data or {}

        # Obtener el tipo de usuario de la sesión actual
        user_type = session_data.get("user_type", "player")
        return user_type

    @app.callback(
        Output("admin-main-content", "children"),
        [Input("admin-main-tabs", "active_tab")],
        prevent_initial_call=False,
    )
    def update_main_tab_content(active_tab):
        """Actualiza contenido según la pestaña principal activa."""
        from pages.administration_dash import (
            create_financials_content,
            create_sessions_content,
        )

        if active_tab == "sessions-tab":
            return create_sessions_content()
        elif active_tab == "financials-tab":
            return create_financials_content()
        else:
            return html.Div("Select a tab to view content")

    @app.callback(
        Output("admin-session-tab-content", "children"),
        [Input("admin-session-tabs", "active_tab")],
        prevent_initial_call=False,
    )
    def update_session_tab_content(active_tab):
        """Actualiza contenido de Session Management según la pestaña activa."""
        from pages.administration_dash import (
            create_edit_session_form,
            create_session_form,
        )

        if active_tab == "create-session":
            return create_session_form()
        elif active_tab == "edit-session":
            return create_edit_session_form()
        else:
            return html.Div("Select a tab to view content")

    @app.callback(
        Output("admin-filter-coach", "options"),
        [Input("admin-main-tabs", "active_tab")],
        prevent_initial_call=False,
    )
    def load_filter_coach_options(active_tab):
        """Carga opciones para el filtro de coach - solo activas."""
        if active_tab != "sessions-tab":
            return []

        try:
            with SessionController() as controller:
                # Obtener coaches
                coaches = controller.get_available_coaches()
                coach_options = [
                    {"label": name, "value": coach_id} for coach_id, name in coaches
                ]

                # Opciones para filtro de coach
                filter_coach_options = [
                    {"label": "All Coaches", "value": "all"}
                ] + coach_options

                return filter_coach_options
        except Exception:
            return []

    @app.callback(
        [
            Output("admin-new-session-coach", "options"),
            Output("admin-new-session-player", "options"),
            Output("admin-new-session-start-time", "options"),
            Output("admin-new-session-end-time", "options"),
            Output("admin-new-session-coach", "value"),
            Output("admin-new-session-coach", "disabled"),
        ],
        [Input("admin-session-tabs", "active_tab")],
        [
            State("admin-user-type-store", "data"),
            State("session-store", "data"),
            State("persistent-session-store", "data"),
            State("session-activity", "data"),
        ],
        prevent_initial_call=False,
    )
    def load_create_session_options(
        active_tab, user_type, session_data, persistent_session_data, activity_data
    ):
        """Carga opciones para crear sesión - con restricciones para coaches."""
        if active_tab != "create-session":
            return [], [], [], [], None, False

        try:
            # Determinar qué session_data usar (misma lógica que en navigation_callbacks)
            if activity_data and activity_data.get("remember_me"):
                session_data = persistent_session_data or {}
            else:
                session_data = session_data or {}

            with SessionController() as controller:
                # Obtener coaches
                coaches = controller.get_available_coaches()
                coach_options = [
                    {"label": name, "value": coach_id} for coach_id, name in coaches
                ]

                # Obtener players
                players = controller.get_available_players()
                player_options = [
                    {"label": name, "value": player_id} for player_id, name in players
                ]

                # Opciones de horario
                time_options = []
                for hour in range(8, 22):
                    for minute in [0, 30]:
                        time_str = f"{hour:02d}:{minute:02d}"
                        time_options.append({"label": time_str, "value": time_str})

                # COACH RESTRICTIONS: Si es coach, predefinir y deshabilitar dropdown
                coach_value = None
                coach_disabled = False

                if user_type == "coach":
                    user_id = session_data.get("user_id")
                    if user_id:
                        from controllers.session_controller import get_coach_by_user_id

                        coach = get_coach_by_user_id(user_id)
                        if coach:
                            coach_value = coach.coach_id
                            coach_disabled = True
                            print(
                                f"🎯 COACH RESTRICTION: Coach {coach.coach_id} pre-selected and disabled"
                            )

                return (
                    coach_options,
                    player_options,
                    time_options,
                    time_options,
                    coach_value,
                    coach_disabled,
                )
        except Exception as e:
            print(f"❌ Error loading create session options: {e}")
            return [], [], [], [], None, False

    # Callback para manejar filtros rápidos y actualizar estilos
    @app.callback(
        [
            Output("admin-active-filter", "data"),
            Output("filter-last-month", "className"),
            Output("filter-last-week", "className"),
            Output("filter-yesterday", "className"),
            Output("filter-today", "className"),
            Output("filter-tomorrow", "className"),
            Output("filter-this-week", "className"),
            Output("filter-this-month", "className"),
        ],
        [
            Input("filter-last-month", "n_clicks"),
            Input("filter-last-week", "n_clicks"),
            Input("filter-yesterday", "n_clicks"),
            Input("filter-today", "n_clicks"),
            Input("filter-tomorrow", "n_clicks"),
            Input("filter-this-week", "n_clicks"),
            Input("filter-this-month", "n_clicks"),
            Input("filter-clear", "n_clicks"),
        ],
        [State("admin-active-filter", "data")],
        prevent_initial_call=True,
    )
    def update_active_filter_and_styles(
        last_month,
        last_week,
        yesterday,
        today,
        tomorrow,
        this_week,
        this_month,
        clear,
        current_filter,
    ):
        """Actualiza filtro activo y estilos de botones."""
        from dash import callback_context

        if not callback_context.triggered:
            return (
                None,
                "btn-filter-quick",
                "btn-filter-quick",
                "btn-filter-quick",
                "btn-filter-quick",
                "btn-filter-quick",
                "btn-filter-quick",
                "btn-filter-quick",
            )

        clicked_id = callback_context.triggered[0]["prop_id"].split(".")[0]

        filter_map = {
            "filter-last-month": "last_month",
            "filter-last-week": "last_week",
            "filter-yesterday": "yesterday",
            "filter-today": "today",
            "filter-tomorrow": "tomorrow",
            "filter-this-week": "this_week",
            "filter-this-month": "this_month",
            "filter-clear": None,
        }

        new_filter = filter_map.get(clicked_id)

        # Si el filtro clickeado es el mismo que el actual, desactivarlo
        if new_filter == current_filter:
            new_filter = None

        # Actualizar clases CSS basado en el filtro activo
        base_class = "btn-filter-quick"
        active_class = "btn-filter-quick filter-active"

        classes = [
            active_class if new_filter == "last_month" else base_class,
            active_class if new_filter == "last_week" else base_class,
            active_class if new_filter == "yesterday" else base_class,
            active_class if new_filter == "today" else base_class,
            active_class if new_filter == "tomorrow" else base_class,
            active_class if new_filter == "this_week" else base_class,
            active_class if new_filter == "this_month" else base_class,
        ]

        return new_filter, *classes

    @app.callback(
        Output("admin-edit-session-selector", "options"),
        [
            Input("admin-session-tabs", "active_tab"),
            Input("admin-active-filter", "data"),
            Input("admin-session-search", "value"),
        ],
        [
            State("admin-user-type-store", "data"),
            State("session-store", "data"),
            State("persistent-session-store", "data"),
            State("session-activity", "data"),
        ],
        prevent_initial_call=True,
    )
    def load_edit_session_options(
        active_tab,
        date_filter,
        search_query,
        user_type,
        session_data,
        persistent_session_data,
        activity_data,
    ):
        """Carga opciones para selector de sesiones con filtros y búsqueda - con restricciones para coaches."""
        if active_tab != "edit-session":
            from dash import no_update

            return no_update

        try:
            # Determinar qué session_data usar (misma lógica que en navigation_callbacks)
            if activity_data and activity_data.get("remember_me"):
                session_data = persistent_session_data or {}
            else:
                session_data = session_data or {}

            # COACH RESTRICTIONS: Si es coach, solo mostrar sus propias sesiones
            coach_id_filter = None
            if user_type == "coach":
                user_id = session_data.get("user_id")
                if user_id:
                    from controllers.session_controller import get_coach_by_user_id

                    coach = get_coach_by_user_id(user_id)
                    if coach:
                        coach_id_filter = coach.coach_id
                        print(
                            f"🎯 COACH EDIT RESTRICTION: Only showing sessions for coach {coach.coach_id}"
                        )

            with SessionController() as controller:
                # Obtener sesiones con filtros aplicados (incluye restricción de coach)
                session_descriptions = controller.get_sessions_for_editing(
                    coach_id=coach_id_filter,
                    date_filter=date_filter,
                    search_query=search_query,
                )

                if not session_descriptions:
                    return [
                        {"label": "No sessions found", "value": "", "disabled": True}
                    ]

                session_options = [
                    {"label": desc, "value": sid}
                    for sid, desc in session_descriptions.items()
                ]

                return session_options
        except Exception as e:
            return [
                {
                    "label": f"Error loading sessions: {str(e)}",
                    "value": "",
                    "disabled": True,
                }
            ]

    # RESTAURADO: Callback simple y funcional que actualiza calendario y tabla juntos
    @app.callback(
        [
            Output("admin-calendar", "children"),
            Output("admin-sessions-table", "children"),
        ],
        [
            Input(
                {"type": "auto-hide-date", "index": "admin-filter-from-date"}, "value"
            ),
            Input({"type": "auto-hide-date", "index": "admin-filter-to-date"}, "value"),
            Input("admin-filter-coach", "value"),
            Input("admin-status-filters", "data"),
            Input("fallback-trigger", "data"),  # Fallback trigger para auto-refresh
            Input("admin-user-type-store", "data"),  # Para filtrado por rol
        ],
        [
            State("admin-main-tabs", "active_tab"),
            State("session-store", "data"),
            State("persistent-session-store", "data"),
            State("session-activity", "data"),
        ],
        prevent_initial_call=False,
    )
    def update_calendar_and_table(
        from_date,
        to_date,
        coach_filter,
        status_filter,
        webhook_trigger,
        user_type,
        active_tab,
        session_data,
        persistent_session_data,
        activity_data,
    ):
        """Actualiza calendario y tabla según filtros con control de rol."""

        if active_tab != "sessions-tab":
            return html.Div(), html.Div()

        try:
            # Determinar qué session_data usar (misma lógica que en navigation_callbacks)
            if activity_data and activity_data.get("remember_me"):
                session_data = persistent_session_data or {}
            else:
                session_data = session_data or {}

            # Obtener user_id de la sesión
            user_id = session_data.get("user_id")

            # Usar filtros directamente del store
            if not status_filter:
                status_filter = [s.value for s in SessionStatus]

            # Fechas por defecto
            if not from_date:
                from_date = (
                    dt.datetime.now().date() - dt.timedelta(days=7)
                ).isoformat()
            if not to_date:
                to_date = (dt.datetime.now().date() + dt.timedelta(days=21)).isoformat()

            start_date_obj = dt.datetime.fromisoformat(from_date).date()
            end_date_obj = dt.datetime.fromisoformat(to_date).date()

            # Coach filter - Si es coach, solo ver sus propias sesiones
            if user_type == "coach" and user_id:
                # CORREGIDO: Obtener el coach_id correcto desde user_id
                from controllers.session_controller import get_coach_by_user_id

                coach = get_coach_by_user_id(user_id)
                if coach:
                    coach_id = coach.coach_id
                else:
                    coach_id = None
            else:
                coach_id = (
                    coach_filter if coach_filter and coach_filter != "all" else None
                )

            with SessionController() as controller:
                # Obtener sesiones con auto-actualización de sesiones pasadas
                sessions = update_and_get_sessions(
                    controller,
                    start_date=start_date_obj,
                    end_date=end_date_obj,
                    coach_id=coach_id,
                    status_filter=status_filter,
                )


                # Crear calendario usando el controller funcional

                calendar_content = show_calendar_dash(
                    sessions, editable=False, key="admin-cal", height=800
                )

                # Crear tabla usando el mismo estilo de ballers_dash
                if sessions:
                    from pages.ballers_dash import create_sessions_table_dash

                    # Usar la función existente de ballers_dash que tiene
                    # el estilo correcto - con soporte para coach_id
                    table_content = create_sessions_table_dash(
                        coach_id=coach_id,  # Añadir coach_id para filtrado correcto
                        from_date=start_date_obj,
                        to_date=end_date_obj,
                        status_filter=status_filter,
                    )
                else:
                    table_content = html.Div(
                        "No sessions found for the selected filters",
                        style={
                            "text-align": "center",
                            "padding": "20px",
                            "color": "#FFFFFF",
                        },
                    )

                return calendar_content, table_content

        except Exception as e:
            error_div = html.Div(
                f"Error loading data: {str(e)}",
                style={"color": "red", "text-align": "center", "padding": "20px"},
            )
            return error_div, error_div

    @app.callback(
        [
            Output("admin-status-filters", "data"),
            Output("admin-status-scheduled", "className"),
            Output("admin-status-completed", "className"),
            Output("admin-status-canceled", "className"),
        ],
        [
            Input("admin-status-scheduled", "n_clicks"),
            Input("admin-status-completed", "n_clicks"),
            Input("admin-status-canceled", "n_clicks"),
        ],
        [State("admin-status-filters", "data")],
        prevent_initial_call=False,
    )
    def toggle_admin_status_filters(
        scheduled_clicks, completed_clicks, canceled_clicks, current_filters
    ):
        """Toggle status badges - COPIADO EXACTAMENTE DE BALLERS."""
        from dash import callback_context

        # Verificar si es inicialización real (todos los clicks son None)
        all_clicks_none = all(
            click is None
            for click in [scheduled_clicks, completed_clicks, canceled_clicks]
        )

        if not callback_context.triggered or all_clicks_none:
            # Initial load - set all badges as active
            filters = ["scheduled", "completed", "canceled"]
            scheduled_class = "status-scheduled"
            completed_class = "status-completed"
            canceled_class = "status-canceled"
            return filters, scheduled_class, completed_class, canceled_class

        # Determinar qué badge se clickeó
        clicked_id = callback_context.triggered[0]["prop_id"].split(".")[0]
        status_map = {
            "admin-status-scheduled": "scheduled",
            "admin-status-completed": "completed",
            "admin-status-canceled": "canceled",
        }

        clicked_status = status_map.get(clicked_id)
        if not clicked_status:
            # Return current state
            filters = current_filters or ["scheduled", "completed", "canceled"]
            scheduled_class = (
                "status-scheduled" if "scheduled" in filters else "status-inactive"
            )
            completed_class = (
                "status-completed" if "completed" in filters else "status-inactive"
            )
            canceled_class = (
                "status-canceled" if "canceled" in filters else "status-inactive"
            )
            return filters, scheduled_class, completed_class, canceled_class

        # Initialize filters if empty
        filters = (
            current_filters.copy()
            if current_filters
            else ["scheduled", "completed", "canceled"]
        )

        # Toggle the clicked filter
        if clicked_status in filters:
            filters.remove(clicked_status)
        else:
            filters.append(clicked_status)

        # Update classes based on current filters
        scheduled_class = (
            "status-scheduled" if "scheduled" in filters else "status-inactive"
        )
        completed_class = (
            "status-completed" if "completed" in filters else "status-inactive"
        )
        canceled_class = (
            "status-canceled" if "canceled" in filters else "status-inactive"
        )

        return filters, scheduled_class, completed_class, canceled_class

    @app.callback(
        [
            Output("admin-alert", "children"),
            Output("admin-alert", "is_open"),
            Output("admin-alert", "color"),
            Output("admin-alert", "style"),
            Output("admin-sessions-table", "children", allow_duplicate=True),
            Output("admin-calendar", "children", allow_duplicate=True),
        ],
        [Input("admin-save-session-btn", "n_clicks")],
        [
            State("admin-new-session-coach", "value"),
            State("admin-new-session-player", "value"),
            State(
                {"type": "auto-hide-date", "index": "admin-new-session-date"}, "value"
            ),
            State("admin-new-session-start-time", "value"),
            State("admin-new-session-end-time", "value"),
            State("admin-new-session-notes", "value"),
            State("admin-active-filter", "data"),
            State("admin-session-search", "value"),
            State(
                {"type": "auto-hide-date", "index": "admin-filter-from-date"}, "value"
            ),
            State({"type": "auto-hide-date", "index": "admin-filter-to-date"}, "value"),
            State("admin-filter-coach", "value"),
            State("admin-status-filters", "data"),
            State("admin-main-tabs", "active_tab"),
            State("admin-user-type-store", "data"),
            State("session-store", "data"),
            State("persistent-session-store", "data"),
            State("session-activity", "data"),
        ],
        prevent_initial_call=True,
    )
    def create_new_session(
        n_clicks,
        coach_id,
        player_id,
        session_date,
        start_time,
        end_time,
        notes,
        date_filter,
        search_query,
        from_date,
        to_date,
        coach_filter,
        status_filter,
        active_tab,
        user_type,
        session_data,
        persistent_session_data,
        activity_data,
    ):
        """Crea una nueva sesión."""
        if not n_clicks:
            from dash import no_update

            return "", False, "info", {}, no_update, no_update

        try:
            from controllers.session_controller import create_session_with_calendar
            from controllers.validation_controller import (
                validate_coach_selection_safe,
                validate_player_selection_safe,
                validate_session_form_data,
            )

            # Validar campos requeridos
            if not session_date or not start_time or not end_time or not coach_id:
                from dash import no_update

                return (
                    "Please fill in all required fields",
                    True,
                    "warning",
                    _get_toast_style(),
                    no_update,
                    no_update,
                )

            # Convertir datos
            session_date_obj = dt.datetime.fromisoformat(session_date).date()
            start_time_obj = dt.datetime.strptime(start_time, "%H:%M").time()
            end_time_obj = dt.datetime.strptime(end_time, "%H:%M").time()

            # Validaciones
            coach_valid, coach_error, safe_coach_id = validate_coach_selection_safe(
                coach_id
            )
            if not coach_valid:
                from dash import no_update

                return (
                    f"Coach error: {coach_error}",
                    True,
                    "danger",
                    _get_toast_style(),
                    no_update,
                    no_update,
                )

            safe_player_id = None
            if player_id:
                player_valid, player_error, safe_player_id = (
                    validate_player_selection_safe(player_id)
                )
                if not player_valid:
                    from dash import no_update

                    return (
                        f"Player error: {player_error}",
                        True,
                        "danger",
                        _get_toast_style(),
                        no_update,
                        no_update,
                    )

            # Validar formulario
            form_valid, form_error = validate_session_form_data(
                coach_id=safe_coach_id,
                player_id=safe_player_id,
                session_date=session_date_obj,
                start_time=start_time_obj,
                end_time=end_time_obj,
            )

            if not form_valid:
                from dash import no_update

                return (
                    f"Validation error: {form_error}",
                    True,
                    "danger",
                    _get_toast_style(),
                    no_update,
                    no_update,
                )

            # Crear sesión
            success, message, _ = create_session_with_calendar(
                coach_id=safe_coach_id,
                player_id=safe_player_id,
                session_date=session_date_obj,
                start_time=start_time_obj,
                end_time=end_time_obj,
                notes=notes or "",
            )

            if success:
                # Actualizar calendario y tabla si estamos en sessions-tab
                if active_tab == "sessions-tab":
                    # COACH RESTRICTIONS: Si el usuario es coach, usar su coach_id en lugar del filtro
                    effective_coach_filter = coach_filter
                    if user_type == "coach":
                        # Determinar qué session_data usar
                        if activity_data and activity_data.get("remember_me"):
                            effective_session_data = persistent_session_data or {}
                        else:
                            effective_session_data = session_data or {}

                        user_id = effective_session_data.get("user_id")
                        if user_id:
                            from controllers.session_controller import (
                                get_coach_by_user_id,
                            )

                            coach = get_coach_by_user_id(user_id)
                            if coach:
                                effective_coach_filter = coach.coach_id
                                print(
                                    f"🎯 COACH CREATE RESTRICTION: Using coach_id {coach.coach_id} instead of filter {coach_filter}"
                                )

                    calendar_content, table_content = (
                        _update_calendar_and_table_content(
                            from_date, to_date, effective_coach_filter, status_filter
                        )
                    )

                    return (
                        f"Session created successfully: {message}",
                        True,
                        "success",
                        _get_toast_style(),
                        table_content,
                        calendar_content,
                    )
                else:
                    # Si no estamos en sessions-tab, no actualizar calendario/tabla
                    from dash import no_update

                    return (
                        f"Session created successfully: {message}",
                        True,
                        "success",
                        _get_toast_style(),
                        no_update,
                        no_update,
                    )
            else:
                from dash import no_update

                return (
                    f"Error creating session: {message}",
                    True,
                    "danger",
                    _get_toast_style(),
                    no_update,
                    no_update,
                )

        except Exception as e:
            from dash import no_update

            return (
                f"Unexpected error: {str(e)}",
                True,
                "danger",
                _get_toast_style(),
                no_update,
                no_update,
            )

    @app.callback(
        [
            Output("admin-financials-content", "children"),
            Output("admin-financials-metrics", "children"),
            Output("admin-financials-chart", "children"),
        ],
        [Input("admin-main-tabs", "active_tab")],
        prevent_initial_call=False,
    )
    def load_financials_data(active_tab):
        """Carga datos financieros."""
        if active_tab != "financials-tab":
            from dash import no_update

            return no_update, no_update, no_update

        try:
            import pandas as pd

            from controllers.sheets_controller_dash import get_accounting_df_dash

            df, error_msg = get_accounting_df_dash()

            if df.empty:
                error_alert = dbc.Alert(
                    f"No financial data available. {error_msg or ''}",
                    color="warning",
                    style={"margin": "20px 0"},
                )
                return error_alert, error_alert, error_alert

            # Mostrar mensaje de error si existe pero hay datos
            if error_msg:
                from common.logging_config import get_logger

                logger = get_logger(__name__)
                logger.warning(f"Warning loading financial data: {error_msg}")

            # Tabla con estilo consistente del proyecto y manejo mejorado de datos
            df_no_total = df.iloc[:-1].copy() if len(df) > 1 else df.copy()

            if df_no_total.empty:
                financials_table = dbc.Alert(
                    "No hay datos disponibles en la tabla financiera",
                    color="info",
                    style={"margin": "20px 0", "text-align": "center"},
                )
            else:
                # Crear tabla compacta con estilo consistente del proyecto
                table_header = html.Thead(
                    [
                        html.Tr(
                            [
                                html.Th(
                                    col,
                                    style={
                                        # Fondo transparente
                                        "background-color": "transparent",
                                        "color": "var(--color-primary)",
                                        "border": "1px solid var(--color-primary-alpha-50)",
                                        "padding": "8px 10px",  # Más compacto
                                        "text-align": "center",
                                        "font-weight": "600",
                                        # Tamaño consistente como en otras tablas
                                        "font-size": "0.75rem",
                                        "white-space": "nowrap",
                                    },
                                )
                                for col in df_no_total.columns
                            ]
                        )
                    ]
                )

                # Crear filas de datos más compactas
                table_rows = []
                for i in range(len(df_no_total)):
                    cells = []
                    for j, col in enumerate(df_no_total.columns):
                        cell_value = df_no_total.iloc[i, j]

                        # Formatear valores numéricos para columnas monetarias
                        numeric_keywords = [
                            "Ingresos",
                            "Gastos",
                            "Ingreso",
                            "Gasto",
                            "Total",
                            "Cantidad",
                            "Importe",
                            "Precio",
                            "Coste",
                            "Cost",
                        ]
                        is_numeric_col = any(
                            keyword.lower() in col.lower()
                            for keyword in numeric_keywords
                        )

                        if is_numeric_col and pd.notna(cell_value):
                            try:
                                if float(cell_value) != 0:
                                    cell_value = f"€{float(cell_value):,.2f}"
                                else:
                                    cell_value = "€0.00"
                            except (ValueError, TypeError):
                                cell_value = str(cell_value)
                        else:
                            cell_value = str(cell_value) if pd.notna(cell_value) else ""

                        # Estilos de celda más compactos y consistentes
                        cell_style = {
                            "color": "#FFFFFF",
                            "background-color": "#1D1B1A",  # Fondo oscuro consistente
                            "border": "1px solid #333333",
                            "padding": "6px 8px",  # Más compacto
                            "text-align": "center" if is_numeric_col else "left",
                            # Tamaño consistente como en otras tablas
                            "font-size": "0.75rem",
                            "vertical-align": "middle",
                        }

                        # Colores específicos para valores monetarios positivos
                        if is_numeric_col and pd.notna(df_no_total.iloc[i, j]):
                            try:
                                numeric_value = float(df_no_total.iloc[i, j])
                                if "Ingreso" in col and numeric_value > 0:
                                    cell_style["color"] = (
                                        "#17a2b8"  # Azul para ingresos
                                    )
                                elif "Gasto" in col and numeric_value > 0:
                                    cell_style["color"] = (
                                        "#ffc107"  # Amarillo para gastos
                                    )
                            except (ValueError, TypeError):
                                pass

                        cells.append(html.Td(cell_value, style=cell_style))

                    table_rows.append(html.Tr(cells))

                table_body = html.Tbody(
                    table_rows,
                    style={"background-color": "#1D1B1A"},  # Asegurar fondo oscuro
                )

                # Contenedor con scroll horizontal para tablas anchas
                financials_table = html.Div(
                    [
                        dbc.Table(
                            [table_header, table_body],
                            striped=False,
                            bordered=True,
                            hover=True,
                            responsive=False,  # Controlamos responsive manualmente
                            size="sm",  # Tabla más compacta
                            style={
                                "background-color": "#1D1B1A !important",
                                "border": "1px solid var(--color-primary-alpha-40)",
                                "border-radius": "6px",
                                "font-size": "0.75rem",
                                "margin": "0",
                            },
                        )
                    ],
                    style={
                        "max-height": "400px",  # Altura máxima con scroll
                        "overflow": "auto",
                        "background-color": "#1D1B1A",
                        "border-radius": "6px",
                        "padding": "0",
                        "margin": "15px 0",
                    },
                )

            # Métricas con estilo consistente del proyecto
            total_gastos = df_no_total["Gastos"].sum()
            total_ingresos = df_no_total["Ingresos"].sum()
            balance = total_ingresos - total_gastos

            metrics = dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.H4(
                                        f"€{balance:,.2f}",
                                        style={
                                            "color": (
                                                "var(--color-primary)"
                                                if balance >= 0
                                                else "#dc3545"
                                            ),
                                            "font-weight": "bold",
                                            "text-align": "center",
                                            "margin-bottom": "5px",
                                        },
                                    ),
                                    html.P(
                                        "Balance",
                                        style={
                                            "color": "#CCCCCC",
                                            "text-align": "center",
                                            "margin": "0",
                                            "font-size": "0.9rem",
                                        },
                                    ),
                                ],
                                style={
                                    "background-color": (
                                        "var(--color-primary-alpha-10)"
                                        if balance >= 0
                                        else "rgba(220, 53, 69, 0.1)"
                                    ),
                                    "border": (
                                        "1px solid var(--color-primary-alpha-30)"
                                        if balance >= 0
                                        else "1px solid rgba(220, 53, 69, 0.3)"
                                    ),
                                    "border-radius": "10px",
                                    "padding": "20px",
                                    "text-align": "center",
                                },
                            ),
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.H4(
                                        f"€{total_ingresos:,.2f}",
                                        style={
                                            "color": "#17a2b8",
                                            "font-weight": "bold",
                                            "text-align": "center",
                                            "margin-bottom": "5px",
                                        },
                                    ),
                                    html.P(
                                        "Income",
                                        style={
                                            "color": "#CCCCCC",
                                            "text-align": "center",
                                            "margin": "0",
                                            "font-size": "0.9rem",
                                        },
                                    ),
                                ],
                                style={
                                    "background-color": "rgba(23, 162, 184, 0.1)",
                                    "border": "1px solid rgba(23, 162, 184, 0.3)",
                                    "border-radius": "10px",
                                    "padding": "20px",
                                    "text-align": "center",
                                },
                            ),
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.H4(
                                        f"€{total_gastos:,.2f}",
                                        style={
                                            "color": "#ffc107",
                                            "font-weight": "bold",
                                            "text-align": "center",
                                            "margin-bottom": "5px",
                                        },
                                    ),
                                    html.P(
                                        "Expenses",
                                        style={
                                            "color": "#CCCCCC",
                                            "text-align": "center",
                                            "margin": "0",
                                            "font-size": "0.9rem",
                                        },
                                    ),
                                ],
                                style={
                                    "background-color": "rgba(255, 193, 7, 0.1)",
                                    "border": "1px solid rgba(255, 193, 7, 0.3)",
                                    "border-radius": "10px",
                                    "padding": "20px",
                                    "text-align": "center",
                                },
                            ),
                        ],
                        width=4,
                    ),
                ],
                className="mb-4",
            )

            # Gráfico de balance acumulado (replicando Streamlit)
            try:
                import pandas as pd
                import plotly.graph_objs as go
                from dash import dcc

                # Procesar datos para el gráfico como en Streamlit
                fecha_col = df_no_total.columns[0]
                df_chart = df_no_total.copy()
                df_chart[fecha_col] = pd.to_datetime(
                    df_chart[fecha_col], errors="coerce"
                )
                df_chart["Mes"] = df_chart[fecha_col].dt.to_period("M").astype(str)

                monthly_summary = (
                    df_chart.groupby("Mes")
                    .agg({"Ingresos": "sum", "Gastos": "sum"})
                    .reset_index()
                )

                monthly_summary["Balance mensual"] = (
                    monthly_summary["Ingresos"] - monthly_summary["Gastos"]
                )
                monthly_summary["Balance acumulado"] = monthly_summary[
                    "Balance mensual"
                ].cumsum()

                # Crear gráfico de línea con estilo del proyecto
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=monthly_summary["Mes"],
                        y=monthly_summary["Balance acumulado"],
                        mode="lines+markers",
                        line=dict(color="var(--color-primary)", width=3),
                        marker=dict(size=8, color="var(--color-primary)"),
                        name="Balance Acumulado",
                    )
                )

                fig.update_layout(
                    title={
                        "text": "Accumulated Balance Over Time",
                        "x": 0.5,
                        "font": {"color": "var(--color-primary)", "size": 16},
                    },
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font={"color": "#FFFFFF"},
                    xaxis=dict(
                        gridcolor="rgba(255,255,255,0.1)", tickfont={"color": "#CCCCCC"}
                    ),
                    yaxis=dict(
                        gridcolor="rgba(255,255,255,0.1)", tickfont={"color": "#CCCCCC"}
                    ),
                    margin=dict(l=40, r=40, t=60, b=40),
                    height=400,
                    showlegend=False,
                )

                chart = dcc.Graph(figure=fig, style={"margin-top": "20px"})

            except Exception as e:
                chart = dbc.Alert(f"Chart error: {str(e)}", color="warning")

            return financials_table, metrics, chart

        except Exception as e:
            error_alert = dbc.Alert(
                f"Error loading financial data: {str(e)}", color="danger"
            )
            return error_alert, error_alert, error_alert

    @app.callback(
        [
            Output("admin-edit-session-coach", "options"),
            Output("admin-edit-session-coach", "value"),
            Output("admin-edit-session-player", "options"),
            Output("admin-edit-session-player", "value"),
            Output("admin-edit-session-status", "value"),
            Output(
                {"type": "auto-hide-date", "index": "admin-edit-session-date"}, "value"
            ),
            Output("admin-edit-session-start-time", "options"),
            Output("admin-edit-session-start-time", "value"),
            Output("admin-edit-session-end-time", "options"),
            Output("admin-edit-session-end-time", "value"),
            Output("admin-edit-session-notes", "value"),
            Output("admin-edit-session-warning", "children"),
        ],
        [Input("admin-edit-session-selector", "value")],
        prevent_initial_call=True,
    )
    def auto_load_session_data(selected_session_id):
        """Auto-carga información de la sesión seleccionada."""

        # Si no hay sesión seleccionada, devolver valores vacíos
        if not selected_session_id:
            return [], None, [], None, None, "", [], None, [], None, "", html.Div()

        try:
            from controllers.validation_controller import (
                check_session_time_recommendation,
                get_edit_session_hours,
            )

            with SessionController() as controller:
                # Obtener la sesión usando el modelo correcto - SIMPLIFICADO
                from models import Session

                session = controller.db.get(Session, selected_session_id)

                if not session:
                    return (
                        [],
                        None,
                        [],
                        None,
                        None,
                        "",
                        [],
                        None,
                        [],
                        None,
                        "",
                        html.Div("Session not found", style={"color": "red"}),
                    )

                # Obtener coaches y players
                coaches = controller.get_available_coaches()
                coach_options = [
                    {"label": name, "value": coach_id} for coach_id, name in coaches
                ]

                players = controller.get_available_players()
                player_options = [
                    {"label": name, "value": player_id} for player_id, name in players
                ]

                # Obtener horarios flexibles usando ValidationController
                hours_start_edit, hours_end_edit = get_edit_session_hours(
                    existing_start=session.start_time.time(),
                    existing_end=session.end_time.time(),
                )

                # Convertir horarios a opciones para dropdown
                start_time_options = [
                    {"label": t.strftime("%H:%M"), "value": t.strftime("%H:%M")}
                    for t in hours_start_edit
                ]
                end_time_options = [
                    {"label": t.strftime("%H:%M"), "value": t.strftime("%H:%M")}
                    for t in hours_end_edit
                ]

                # Verificar recomendaciones de horarios
                is_recommended, warning_msg = check_session_time_recommendation(
                    session.start_time.time(), session.end_time.time()
                )

                warning_div = html.Div()
                if not is_recommended:
                    warning_div = html.Div(
                        [
                            html.I(
                                className="bi bi-exclamation-triangle me-2",
                                style={"color": "#ffc107"},
                            ),
                            warning_msg,
                        ],
                        style={
                            "color": "#ffc107",
                            "background-color": "rgba(255, 193, 7, 0.1)",
                            "padding": "10px",
                            "border-radius": "5px",
                            "border-left": "4px solid #ffc107",
                        },
                    )

                # Valores a establecer
                coach_value = session.coach_id
                player_value = session.player_id
                status_value = session.status.value
                date_value = session.start_time.date().isoformat()
                start_time_value = session.start_time.time().strftime("%H:%M")
                end_time_value = session.end_time.time().strftime("%H:%M")
                notes_value = session.notes or ""

                return (
                    coach_options,
                    coach_value,
                    player_options,
                    player_value,
                    status_value,
                    date_value,
                    start_time_options,
                    start_time_value,
                    end_time_options,
                    end_time_value,
                    notes_value,
                    warning_div,
                )

        except Exception as e:
            error_div = html.Div(
                f"Error loading session: {str(e)}", style={"color": "red"}
            )
            return [], None, [], None, None, "", [], None, [], None, "", error_div

    @app.callback(
        [
            Output("admin-alert", "children", allow_duplicate=True),
            Output("admin-alert", "is_open", allow_duplicate=True),
            Output("admin-alert", "color", allow_duplicate=True),
            Output("admin-alert", "style", allow_duplicate=True),
            Output("admin-sessions-table", "children", allow_duplicate=True),
            Output("admin-calendar", "children", allow_duplicate=True),
            Output("admin-edit-session-selector", "options", allow_duplicate=True),
        ],
        [Input("admin-update-session-btn", "n_clicks")],
        [
            State("admin-edit-session-selector", "value"),
            State("admin-edit-session-coach", "value"),
            State("admin-edit-session-player", "value"),
            State("admin-edit-session-status", "value"),
            State(
                {"type": "auto-hide-date", "index": "admin-edit-session-date"}, "value"
            ),
            State("admin-edit-session-start-time", "value"),
            State("admin-edit-session-end-time", "value"),
            State("admin-edit-session-notes", "value"),
            State("admin-active-filter", "data"),
            State("admin-session-search", "value"),
            State(
                {"type": "auto-hide-date", "index": "admin-filter-from-date"}, "value"
            ),
            State({"type": "auto-hide-date", "index": "admin-filter-to-date"}, "value"),
            State("admin-filter-coach", "value"),
            State("admin-status-filters", "data"),
            State("admin-main-tabs", "active_tab"),
            State("admin-session-tabs", "active_tab"),
            State("admin-user-type-store", "data"),
            State("session-store", "data"),
            State("persistent-session-store", "data"),
            State("session-activity", "data"),
        ],
        prevent_initial_call=True,
    )
    def update_existing_session(
        n_clicks,
        session_id,
        coach_id,
        player_id,
        status,
        session_date,
        start_time,
        end_time,
        notes,
        date_filter,
        search_query,
        from_date,
        to_date,
        coach_filter,
        status_filter,
        main_active_tab,
        session_active_tab,
        user_type,
        session_data,
        persistent_session_data,
        activity_data,
    ):
        """Actualiza una sesión existente."""
        if not n_clicks:
            from dash import no_update

            return "", False, "info", {}, no_update, no_update, no_update

        if not session_id:
            from dash import no_update

            return (
                "Please select a session to update",
                True,
                "warning",
                _get_toast_style(),
                no_update,
                no_update,
                no_update,
            )

        try:
            from controllers.session_controller import update_session_with_calendar
            from controllers.validation_controller import (
                validate_coach_selection_safe,
                validate_player_selection_safe,
                validate_session_form_data,
            )

            # Validar campos requeridos
            if not session_date or not start_time or not end_time or not coach_id:
                from dash import no_update

                return (
                    "Please fill in all required fields",
                    True,
                    "warning",
                    _get_toast_style(),
                    no_update,
                    no_update,
                    no_update,
                )

            # Convertir datos
            session_date_obj = dt.datetime.fromisoformat(session_date).date()
            start_time_obj = dt.datetime.strptime(start_time, "%H:%M").time()
            end_time_obj = dt.datetime.strptime(end_time, "%H:%M").time()

            # Validaciones
            coach_valid, coach_error, safe_coach_id = validate_coach_selection_safe(
                coach_id
            )
            if not coach_valid:
                from dash import no_update

                return (
                    f"Coach error: {coach_error}",
                    True,
                    "danger",
                    _get_toast_style(),
                    no_update,
                    no_update,
                    no_update,
                )

            safe_player_id = None
            if player_id:
                player_valid, player_error, safe_player_id = (
                    validate_player_selection_safe(player_id)
                )
                if not player_valid:
                    from dash import no_update

                    return (
                        f"Player error: {player_error}",
                        True,
                        "danger",
                        _get_toast_style(),
                        no_update,
                        no_update,
                        no_update,
                    )

            # Validar formulario
            form_valid, form_error = validate_session_form_data(
                coach_id=safe_coach_id,
                player_id=safe_player_id,
                session_date=session_date_obj,
                start_time=start_time_obj,
                end_time=end_time_obj,
            )

            if not form_valid:
                from dash import no_update

                return (
                    f"Validation error: {form_error}",
                    True,
                    "danger",
                    _get_toast_style(),
                    no_update,
                    no_update,
                    no_update,
                )

            # Actualizar sesión con logging de tiempo
            import time

            start_time_op = time.time()

            success, message = update_session_with_calendar(
                session_id=session_id,
                coach_id=safe_coach_id,
                player_id=safe_player_id,
                status=status,
                session_date=session_date_obj,
                start_time=start_time_obj,
                end_time=end_time_obj,
                notes=notes or "",
            )


            if success:
                # Actualizar calendario, tabla y selector después de editar exitosamente

                # 1. Actualizar calendario y tabla si estamos en sessions-tab
                if main_active_tab == "sessions-tab":
                    ui_start_time = time.time()

                    # COACH RESTRICTIONS: Si el usuario es coach, usar su coach_id en lugar del filtro
                    effective_coach_filter = coach_filter
                    if user_type == "coach":
                        # Determinar qué session_data usar
                        if activity_data and activity_data.get("remember_me"):
                            effective_session_data = persistent_session_data or {}
                        else:
                            effective_session_data = session_data or {}

                        user_id = effective_session_data.get("user_id")
                        if user_id:
                            from controllers.session_controller import (
                                get_coach_by_user_id,
                            )

                            coach = get_coach_by_user_id(user_id)
                            if coach:
                                effective_coach_filter = coach.coach_id
                                print(
                                    f"🎯 COACH UPDATE RESTRICTION: Using coach_id {coach.coach_id} instead of filter {coach_filter}"
                                )

                    calendar_content, table_content = (
                        _update_calendar_and_table_content(
                            from_date, to_date, effective_coach_filter, status_filter
                        )
                    )
                else:
                    from dash import no_update

                    calendar_content = no_update
                    table_content = no_update

                # 2. Actualizar selector de sesiones si estamos en edit-session
                if session_active_tab == "edit-session":
                    # COACH RESTRICTIONS: Aplicar mismo filtro que para calendario/tabla
                    selector_coach_id = None
                    if user_type == "coach":
                        # Reutilizar la lógica anterior para obtener coach_id
                        if activity_data and activity_data.get("remember_me"):
                            effective_session_data = persistent_session_data or {}
                        else:
                            effective_session_data = session_data or {}

                        user_id = effective_session_data.get("user_id")
                        if user_id:
                            from controllers.session_controller import (
                                get_coach_by_user_id,
                            )

                            coach = get_coach_by_user_id(user_id)
                            if coach:
                                selector_coach_id = coach.coach_id
                                print(
                                    f"🎯 COACH SELECTOR RESTRICTION: Filtering sessions for coach {coach.coach_id}"
                                )

                    with SessionController() as controller:
                        session_descriptions = controller.get_sessions_for_editing(
                            coach_id=selector_coach_id,
                            date_filter=date_filter,
                            search_query=search_query,
                        )
                        if session_descriptions:
                            session_options = [
                                {"label": desc, "value": sid}
                                for sid, desc in session_descriptions.items()
                            ]
                        else:
                            session_options = [
                                {
                                    "label": "No sessions found",
                                    "value": "",
                                    "disabled": True,
                                }
                            ]
                else:
                    from dash import no_update

                    session_options = no_update

                return (
                    f"Session updated successfully: {message}",
                    True,
                    "success",
                    _get_toast_style(),
                    table_content,
                    calendar_content,
                    session_options,
                )
            else:
                from dash import no_update

                return (
                    f"Error updating session: {message}",
                    True,
                    "danger",
                    _get_toast_style(),
                    no_update,
                    no_update,
                    no_update,
                )

        except Exception as e:
            from dash import no_update

            return (
                f"Unexpected error: {str(e)}",
                True,
                "danger",
                _get_toast_style(),
                no_update,
                no_update,
                no_update,
            )

    # Callback clientside para cerrar automáticamente las alertas
    app.clientside_callback(
        """
        function(is_open) {
            if (is_open) {
                setTimeout(function() {
                    // Activar el callback para cerrar
                    window.dash_clientside.set_props('admin-alert', {'is_open': false});
                }, 5000);
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("admin-alert", "data-temp", allow_duplicate=True),
        Input("admin-alert", "is_open"),
        prevent_initial_call=True,
    )

    # Callback para sincronizar el input de búsqueda visible con el invisible
    @app.callback(
        Output("admin-session-search", "value"),
        [Input("admin-session-search-visible", "value")],
        prevent_initial_call=True,
    )
    def sync_search_inputs(visible_value):
        """Sincroniza el input visible con el invisible para callbacks."""
        return visible_value or ""

    # Delete Session Callbacks - reutilizando helpers y patrones existentes
    @app.callback(
        Output("admin-delete-confirmation-modal", "is_open"),
        [Input("admin-delete-session-btn", "n_clicks")],
        [State("admin-edit-session-selector", "value")],
        prevent_initial_call=True,
    )
    def open_delete_confirmation_modal(n_clicks, selected_session_id):
        """Abre el modal de confirmación para eliminar sesión."""
        if not n_clicks or not selected_session_id:
            return False
        return True

    @app.callback(
        Output("admin-delete-confirmation-modal", "is_open", allow_duplicate=True),
        [Input("admin-delete-cancel-btn", "n_clicks")],
        prevent_initial_call=True,
    )
    def close_delete_confirmation_modal(n_clicks):
        """Cierra el modal de confirmación al cancelar."""
        if n_clicks:
            return False
        from dash import no_update

        return no_update

    @app.callback(
        [
            Output("admin-delete-confirmation-modal", "is_open", allow_duplicate=True),
            Output("admin-alert", "children", allow_duplicate=True),
            Output("admin-alert", "is_open", allow_duplicate=True),
            Output("admin-alert", "color", allow_duplicate=True),
            Output("admin-alert", "style", allow_duplicate=True),
            Output("admin-sessions-table", "children", allow_duplicate=True),
            Output("admin-calendar", "children", allow_duplicate=True),
            Output("admin-edit-session-selector", "options", allow_duplicate=True),
            Output("admin-edit-session-selector", "value", allow_duplicate=True),
        ],
        [Input("admin-delete-confirm-btn", "n_clicks")],
        [
            State("admin-edit-session-selector", "value"),
            State("admin-active-filter", "data"),
            State("admin-session-search", "value"),
            State(
                {"type": "auto-hide-date", "index": "admin-filter-from-date"}, "value"
            ),
            State({"type": "auto-hide-date", "index": "admin-filter-to-date"}, "value"),
            State("admin-filter-coach", "value"),
            State("admin-status-filters", "data"),
            State("admin-main-tabs", "active_tab"),
            State("admin-session-tabs", "active_tab"),
            State("admin-user-type-store", "data"),
            State("session-store", "data"),
            State("persistent-session-store", "data"),
            State("session-activity", "data"),
        ],
        prevent_initial_call=True,
    )
    def delete_session_confirmed(
        n_clicks,
        session_id,
        date_filter,
        search_query,
        from_date,
        to_date,
        coach_filter,
        status_filter,
        main_active_tab,
        session_active_tab,
        user_type,
        session_data,
        persistent_session_data,
        activity_data,
    ):
        """Elimina sesión tras confirmación - reutiliza helpers existentes."""
        from dash import no_update

        if not n_clicks or not session_id:
            return (
                False,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        try:
            from controllers.session_controller import delete_session_with_calendar

            # Eliminar sesión (reutiliza función existente)
            success, message = delete_session_with_calendar(session_id)

            if success:
                # Actualizar UI usando helpers existentes
                calendar_content = table_content = no_update
                if main_active_tab == "sessions-tab":
                    # COACH RESTRICTIONS: Si el usuario es coach, usar su coach_id en lugar del filtro
                    effective_coach_filter = coach_filter
                    if user_type == "coach":
                        # Determinar qué session_data usar
                        if activity_data and activity_data.get("remember_me"):
                            effective_session_data = persistent_session_data or {}
                        else:
                            effective_session_data = session_data or {}

                        user_id = effective_session_data.get("user_id")
                        if user_id:
                            from controllers.session_controller import (
                                get_coach_by_user_id,
                            )

                            coach = get_coach_by_user_id(user_id)
                            if coach:
                                effective_coach_filter = coach.coach_id
                                print(
                                    f"🎯 COACH DELETE RESTRICTION: Using coach_id {coach.coach_id} instead of filter {coach_filter}"
                                )

                    calendar_content, table_content = (
                        _update_calendar_and_table_content(
                            from_date, to_date, effective_coach_filter, status_filter
                        )
                    )

                # Actualizar selector usando patrón existente
                session_options = []
                if session_active_tab == "edit-session":
                    # COACH RESTRICTIONS: Aplicar mismo filtro que para calendario/tabla
                    selector_coach_id = None
                    if user_type == "coach":
                        # Reutilizar la lógica anterior para obtener coach_id
                        if activity_data and activity_data.get("remember_me"):
                            effective_session_data = persistent_session_data or {}
                        else:
                            effective_session_data = session_data or {}

                        user_id = effective_session_data.get("user_id")
                        if user_id:
                            from controllers.session_controller import (
                                get_coach_by_user_id,
                            )

                            coach = get_coach_by_user_id(user_id)
                            if coach:
                                selector_coach_id = coach.coach_id
                                print(
                                    f"🎯 COACH DELETE SELECTOR RESTRICTION: Filtering sessions for coach {coach.coach_id}"
                                )

                    with SessionController() as controller:
                        session_descriptions = controller.get_sessions_for_editing(
                            coach_id=selector_coach_id,
                            date_filter=date_filter,
                            search_query=search_query,
                        )
                        session_options = (
                            [
                                {"label": desc, "value": sid}
                                for sid, desc in session_descriptions.items()
                            ]
                            if session_descriptions
                            else [
                                {
                                    "label": "No sessions found",
                                    "value": "",
                                    "disabled": True,
                                }
                            ]
                        )

                return (
                    False,  # Cerrar modal
                    f"Session deleted successfully: {message}",
                    True,
                    "success",
                    _get_toast_style(),  # Reutiliza helper toast
                    table_content,
                    calendar_content,
                    session_options,
                    None,
                )
            else:
                return (
                    False,
                    f"Error deleting session: {message}",
                    True,
                    "danger",
                    _get_toast_style(),  # Reutiliza helper toast
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

        except Exception as e:
            return (
                False,
                f"Unexpected error: {str(e)}",
                True,
                "danger",
                _get_toast_style(),  # Reutiliza helper toast
                no_update,
                no_update,
                no_update,
                no_update,
            )

    # Callback para export PDF de financials
    @app.callback(
        [
            Output("admin-alert", "children", allow_duplicate=True),
            Output("admin-alert", "is_open", allow_duplicate=True),
            Output("admin-alert", "color", allow_duplicate=True),
            Output("admin-alert", "style", allow_duplicate=True),
        ],
        [Input("admin-financials-export-btn", "n_clicks")],
        prevent_initial_call=True,
    )
    def handle_financials_export(n_clicks):
        """Maneja la exportación de financials a PDF."""
        if not n_clicks:
            from dash import no_update

            return no_update, no_update, no_update, no_update

        try:
            import datetime as dt

            from controllers.export_controller import generate_financials_pdf

            # Usar rango amplio para incluir todos los datos como en Streamlit
            start_date = dt.date(2020, 1, 1)
            end_date = dt.date.today()

            buffer, filename = generate_financials_pdf(start_date, end_date)

            return (
                f"✅ Financial report generated successfully: {filename}",
                True,
                "success",
                _get_toast_style(),
            )

        except Exception as e:
            return (
                f"❌ Error generating financial report: {str(e)}",
                True,
                "danger",
                _get_toast_style(),
            )


def create_webhook_update_callback(app):
    """
    Crea callback global para actualizar el Store cuando hay cambios de webhook.
    Esta función será llamada por el webhook server cuando reciba eventos.
    """
    import time

    def trigger_ui_refresh():
        """Actualiza el webhook-changes-store para disparar refresh en UI."""
        timestamp = time.time()
        # En una implementación real, esto se haría vía un mecanismo IPC
        # Por ahora, podemos usar un archivo temporal o redis
        return {"timestamp": timestamp, "source": "webhook"}

    # Retornar la función para que el webhook server la pueda usar
    return trigger_ui_refresh

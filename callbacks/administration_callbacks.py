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
        ],
        [Input("admin-session-tabs", "active_tab")],
        prevent_initial_call=False,
    )
    def load_create_session_options(active_tab):
        """Carga opciones para crear sesión - solo cuando tab activa."""
        if active_tab != "create-session":
            return [], [], [], []

        try:
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

                return coach_options, player_options, time_options, time_options
        except Exception:
            return [], [], [], []

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
            Input(
                "admin-alert", "is_open"
            ),  # Se dispara cuando se muestra mensaje de éxito
        ],
        prevent_initial_call=True,
    )
    def load_edit_session_options(active_tab, date_filter, search_query, alert_is_open):
        """Carga opciones para selector de sesiones con filtros y búsqueda."""
        if active_tab != "edit-session":
            from dash import no_update

            return no_update

        try:
            with SessionController() as controller:
                # Obtener sesiones con filtros aplicados
                session_descriptions = controller.get_sessions_for_editing(
                    coach_id=None, date_filter=date_filter, search_query=search_query
                )

                if not session_descriptions:
                    return [
                        {"label": "No sessions found", "value": None, "disabled": True}
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
                    "value": None,
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
            Input("filter-from-date", "value"),
            Input("filter-to-date", "value"),
            Input("admin-filter-coach", "value"),
            Input("admin-status-filters", "data"),
        ],
        [State("admin-main-tabs", "active_tab")],
        prevent_initial_call=False,
    )
    def update_calendar_and_table(
        from_date, to_date, coach_filter, status_filter, active_tab
    ):
        """Actualiza calendario y tabla según filtros - RESTAURADO FUNCIONAL."""
        if active_tab != "sessions-tab":
            return html.Div(), html.Div()

        try:
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

            # Coach filter
            coach_id = coach_filter if coach_filter and coach_filter != "all" else None

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
                    # el estilo correcto
                    table_content = create_sessions_table_dash(
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
            State("admin-new-session-date", "value"),
            State("admin-new-session-start-time", "value"),
            State("admin-new-session-end-time", "value"),
            State("admin-new-session-notes", "value"),
            State("admin-active-filter", "data"),
            State("admin-session-search", "value"),
            State("filter-from-date", "value"),
            State("filter-to-date", "value"),
            State("admin-filter-coach", "value"),
            State("admin-status-filters", "data"),
            State("admin-main-tabs", "active_tab"),
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
                    calendar_content, table_content = (
                        _update_calendar_and_table_content(
                            from_date, to_date, coach_filter, status_filter
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
            from controllers.sheets_controller import get_accounting_df

            df = get_accounting_df()

            if df.empty:
                empty_alert = dbc.Alert("No financial data available", color="info")
                return empty_alert, empty_alert, empty_alert

            # Tabla
            df_no_total = df.iloc[:-1].copy()
            financials_table = dbc.Table.from_dataframe(
                df_no_total,
                striped=True,
                bordered=True,
                hover=True,
                responsive=True,
                dark=True,
            )

            # Métricas
            total_gastos = df_no_total["Gastos"].sum()
            total_ingresos = df_no_total["Ingresos"].sum()
            balance = total_ingresos - total_gastos

            metrics = dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                f"€{balance:,.2f}",
                                                className="text-center",
                                            ),
                                            html.P(
                                                "Balance",
                                                className="text-center text-muted",
                                            ),
                                        ]
                                    )
                                ],
                                color="success" if balance >= 0 else "danger",
                                outline=True,
                            ),
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                f"€{total_ingresos:,.2f}",
                                                className="text-center",
                                            ),
                                            html.P(
                                                "Income",
                                                className="text-center text-muted",
                                            ),
                                        ]
                                    )
                                ],
                                color="info",
                                outline=True,
                            ),
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                f"€{total_gastos:,.2f}",
                                                className="text-center",
                                            ),
                                            html.P(
                                                "Expenses",
                                                className="text-center text-muted",
                                            ),
                                        ]
                                    )
                                ],
                                color="warning",
                                outline=True,
                            ),
                        ],
                        width=4,
                    ),
                ]
            )

            # Gráfico simple
            chart = dbc.Alert("Chart visualization available", color="info")

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
            Output("admin-edit-session-date", "value"),
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
            State("admin-edit-session-date", "value"),
            State("admin-edit-session-start-time", "value"),
            State("admin-edit-session-end-time", "value"),
            State("admin-edit-session-notes", "value"),
            State("admin-active-filter", "data"),
            State("admin-session-search", "value"),
            State("filter-from-date", "value"),
            State("filter-to-date", "value"),
            State("admin-filter-coach", "value"),
            State("admin-status-filters", "data"),
            State("admin-main-tabs", "active_tab"),
            State("admin-session-tabs", "active_tab"),
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

            update_time = time.time() - start_time_op
            print(f"⏱️ Update session took: {update_time:.2f}s")

            if success:
                # Actualizar calendario, tabla y selector después de editar exitosamente

                # 1. Actualizar calendario y tabla si estamos en sessions-tab
                if main_active_tab == "sessions-tab":
                    ui_start_time = time.time()
                    calendar_content, table_content = (
                        _update_calendar_and_table_content(
                            from_date, to_date, coach_filter, status_filter
                        )
                    )
                    ui_time = time.time() - ui_start_time
                    print(f"⏱️ UI update took: {ui_time:.2f}s")
                else:
                    from dash import no_update

                    calendar_content = no_update
                    table_content = no_update

                # 2. Actualizar selector de sesiones si estamos en edit-session
                if session_active_tab == "edit-session":
                    with SessionController() as controller:
                        session_descriptions = controller.get_sessions_for_editing(
                            coach_id=None,
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
                                    "value": None,
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
                }, 4000);
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
            State("filter-from-date", "value"),
            State("filter-to-date", "value"),
            State("admin-filter-coach", "value"),
            State("admin-status-filters", "data"),
            State("admin-main-tabs", "active_tab"),
            State("admin-session-tabs", "active_tab"),
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
                    calendar_content, table_content = (
                        _update_calendar_and_table_content(
                            from_date, to_date, coach_filter, status_filter
                        )
                    )

                # Actualizar selector usando patrón existente
                session_options = []
                if session_active_tab == "edit-session":
                    with SessionController() as controller:
                        session_descriptions = controller.get_sessions_for_editing(
                            coach_id=None,
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
                                    "value": None,
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

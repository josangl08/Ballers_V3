# callbacks/administration_callbacks.py
"""
Callbacks relacionados con la página de Administration - COPIANDO ESTRUCTURA DE BALLERS
"""
import datetime as dt

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, html

from controllers.session_controller import SessionController
from controllers.validation_controller import ValidationController  # noqa: F401
from models import SessionStatus


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

    @app.callback(
        Output("admin-edit-session-selector", "options"),
        [Input("admin-session-tabs", "active_tab")],
        prevent_initial_call=False,
    )
    def load_edit_session_options(active_tab):
        """Carga opciones para selector de sesiones a editar."""
        if active_tab != "edit-session":
            return []

        try:
            with SessionController() as controller:
                # Obtener sesiones para editar
                session_descriptions = controller.get_sessions_for_editing()
                session_options = [
                    {"label": f"#{sid} - {desc}", "value": sid}
                    for sid, desc in session_descriptions.items()
                ]

                return session_options
        except Exception:
            return []

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
                # Obtener sesiones
                sessions = controller.get_sessions_for_display(
                    start_date=start_date_obj,
                    end_date=end_date_obj,
                    coach_id=coach_id,
                    status_filter=status_filter,
                )

                # Crear calendario usando el controller funcional
                from controllers.internal_calendar import show_calendar_dash

                calendar_content = show_calendar_dash(
                    sessions, editable=False, key="admin-cal"
                )

                # Crear tabla usando el mismo formato
                if sessions:
                    formatted_data = controller.format_sessions_for_table(sessions)
                    table_content = create_sessions_table_content(formatted_data)
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
        ],
        [Input("admin-save-session-btn", "n_clicks")],
        [
            State("admin-new-session-coach", "value"),
            State("admin-new-session-player", "value"),
            State("admin-new-session-date", "value"),
            State("admin-new-session-start-time", "value"),
            State("admin-new-session-end-time", "value"),
            State("admin-new-session-notes", "value"),
        ],
        prevent_initial_call=True,
    )
    def create_new_session(
        n_clicks, coach_id, player_id, session_date, start_time, end_time, notes
    ):
        """Crea una nueva sesión."""
        if not n_clicks:
            return "", False, "info"

        try:
            from controllers.session_controller import create_session_with_calendar
            from controllers.validation_controller import (
                validate_coach_selection_safe,
                validate_player_selection_safe,
                validate_session_form_data,
            )

            # Validar campos requeridos
            if not session_date or not start_time or not end_time or not coach_id:
                return "Please fill in all required fields", True, "warning"

            # Convertir datos
            session_date_obj = dt.datetime.fromisoformat(session_date).date()
            start_time_obj = dt.datetime.strptime(start_time, "%H:%M").time()
            end_time_obj = dt.datetime.strptime(end_time, "%H:%M").time()

            # Validaciones
            coach_valid, coach_error, safe_coach_id = validate_coach_selection_safe(
                coach_id
            )
            if not coach_valid:
                return f"Coach error: {coach_error}", True, "danger"

            safe_player_id = None
            if player_id:
                player_valid, player_error, safe_player_id = (
                    validate_player_selection_safe(player_id)
                )
                if not player_valid:
                    return f"Player error: {player_error}", True, "danger"

            # Validar formulario
            form_valid, form_error = validate_session_form_data(
                coach_id=safe_coach_id,
                player_id=safe_player_id,
                session_date=session_date_obj,
                start_time=start_time_obj,
                end_time=end_time_obj,
            )

            if not form_valid:
                return f"Validation error: {form_error}", True, "danger"

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
                return f"Session created successfully: {message}", True, "success"
            else:
                return f"Error creating session: {message}", True, "danger"

        except Exception as e:
            return f"Unexpected error: {str(e)}", True, "danger"

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

    # TEMPORALMENTE ELIMINADO: ClientSide callback causaba crashes de Dash
    # TODO: Implementar estrategia alternativa para actualizar eventos


def create_sessions_table_content(formatted_data):
    """Crea el contenido de la tabla de sesiones con estilos - COPIADO DE BALLERS"""
    if not formatted_data:
        return html.Div(
            "No sessions to display",
            style={"text-align": "center", "padding": "20px", "color": "#FFFFFF"},
        )

    df = pd.DataFrame(formatted_data)

    # Crear tabla con estilos por status como en ballers
    table_data = []
    for _, row in df.iterrows():
        row_data = []
        for col in df.columns:
            cell_style = {"padding": "12px", "color": "#FFFFFF"}
            if col == "Status":
                if row[col] == "completed":
                    cell_style["background-color"] = "rgba(76, 175, 80, 0.3)"
                elif row[col] == "scheduled":
                    cell_style["background-color"] = "rgba(33, 150, 243, 0.3)"
                elif row[col] == "canceled":
                    cell_style["background-color"] = "rgba(244, 67, 54, 0.3)"

            row_data.append(html.Td(str(row[col]), style=cell_style))
        table_data.append(html.Tr(row_data))

    # Headers
    headers = html.Tr(
        [
            html.Th(
                col,
                style={
                    "padding": "12px",
                    "color": "#FFFFFF",
                    "background-color": "#444444",
                    "border-bottom": "2px solid rgba(36, 222, 132, 1)",
                },
            )
            for col in df.columns
        ]
    )

    table = html.Table(
        [html.Thead(headers), html.Tbody(table_data)],
        style={
            "width": "100%",
            "border-collapse": "collapse",
            "border": "2px solid rgba(36, 222, 132, 1)",
            "border-radius": "10px",
            "overflow": "hidden",
        },
    )

    return table

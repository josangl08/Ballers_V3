# callbacks/administration_callbacks.py
"""
Callbacks relacionados con la página de Administration.
"""
import dash_bootstrap_components as dbc
from dash import Input, Output, State, html


def register_administration_callbacks(app):
    """Registra callbacks de Administration en la aplicación Dash."""

    @app.callback(
        Output("admin-user-content", "children"),
        [Input("admin-user-type-store", "data")],
        prevent_initial_call=False,
    )
    def update_admin_content(user_type):
        """Actualiza contenido de Administration según el tipo de usuario."""
        from pages.administration_dash import create_administration_dashboard_dash

        return create_administration_dashboard_dash()

    @app.callback(
        Output("admin-tab-content", "children"),
        [Input("admin-tabs", "active_tab")],
        prevent_initial_call=False,
    )
    def update_admin_tab_content(active_tab):
        """Actualiza contenido según la pestaña activa."""
        from pages.administration_dash import (
            create_session_form_dash,
            create_sessions_list_dash,
        )

        if active_tab == "sessions":
            return dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col([create_session_form_dash()], width=12, lg=6),
                            dbc.Col([create_sessions_list_dash()], width=12, lg=6),
                        ]
                    )
                ]
            )
        elif active_tab == "financials":
            return html.Div(
                [
                    html.H4(
                        "💰 Financial Management",
                        style={"color": "rgba(36, 222, 132, 1)"},
                    ),
                    html.P(
                        "Google Sheets integration for accounting data",
                        className="text-muted",
                    ),
                    dbc.Alert("Financials view - To be implemented", color="info"),
                ]
            )
        else:
            return html.Div("Select a tab to view content")

    @app.callback(
        [
            Output("admin-calendar-view", "children"),
            Output("admin-sessions-table", "children"),
        ],
        [Input("admin-apply-filters-btn", "n_clicks")],
        [
            State("admin-filter-date-start", "value"),
            State("admin-filter-date-end", "value"),
            State("admin-filter-status", "value"),
            State("admin-filter-coach", "value"),
        ],
        prevent_initial_call=False,
    )
    def update_admin_sessions_content(n_clicks, start_date, end_date, status, coach):
        """Actualiza el contenido de sesiones en Administration."""
        # Calendario placeholder
        calendar_content = dbc.Alert(
            "📅 Integrated calendar view - To be implemented with real session data",
            color="info",
        )

        # Tabla de sesiones placeholder
        sessions_table = dbc.Alert(
            "📋 Sessions table with filtering - To be implemented",
            color="info",
        )

        return calendar_content, sessions_table

    @app.callback(
        [
            Output("new-session-coach", "options"),
            Output("new-session-players", "options"),
            Output("admin-filter-coach", "options"),
        ],
        [Input("url", "pathname")],
        prevent_initial_call=False,
    )
    def load_session_form_options(pathname):
        """Carga opciones dinámicas para formularios de sesiones."""
        # Placeholder options - deberían venir de controllers
        coach_options = [
            {"label": "Coach 1", "value": "coach1"},
            {"label": "Coach 2", "value": "coach2"},
        ]

        player_options = [
            {"label": "Player 1", "value": "player1"},
            {"label": "Player 2", "value": "player2"},
        ]

        filter_coach_options = [
            {"label": "All Coaches", "value": "all"}
        ] + coach_options

        return coach_options, player_options, filter_coach_options

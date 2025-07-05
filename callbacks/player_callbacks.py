# callbacks/player_callbacks.py
"""
Callbacks relacionados con jugadores y perfiles.
"""
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, html, no_update


def register_player_callbacks(app):
    """Registra callbacks de jugadores en la aplicación Dash."""

    @app.callback(
        Output("selected-player-id", "data"),
        [Input("back-to-list-btn", "n_clicks")],
        [State("selected-player-id", "data")],
        prevent_initial_call=True,
    )
    def handle_back_to_list_callback(back_clicks, current_selection):
        """Callback para el botón de vuelta a la lista."""
        if back_clicks:
            print("DEBUG: Back to list clicked")
            return None
        return no_update

    @app.callback(
        Output("selected-player-id", "data", allow_duplicate=True),
        [Input({"type": "view-profile-button", "index": ALL}, "n_clicks")],
        [State("selected-player-id", "data")],
        prevent_initial_call=True,
    )
    def handle_view_profile_universal_callback(n_clicks_list, current_selection):
        """Callback universal para manejar todos los botones View Profile."""
        from dash import callback_context

        if not callback_context.triggered:
            return no_update

        if not any(n_clicks_list or []):
            return no_update

        trigger_id = callback_context.triggered[0]["prop_id"]
        print(f"DEBUG: Universal view profile trigger: {trigger_id}")

        try:
            if "view-profile-button" in trigger_id:
                import json

                trigger_data = json.loads(trigger_id.split(".")[0])
                player_id = trigger_data["index"]
                print(f"DEBUG: Navigating to player (complex): {player_id}")
                return player_id
            elif "view-profile-" in trigger_id:
                player_id = trigger_id.split("view-profile-")[1].split(".")[0]
                print(f"DEBUG: Navigating to player (simple): {player_id}")
                return player_id
        except Exception as e:
            print(f"DEBUG: Error parsing view profile trigger: {e}")

        return no_update

    @app.callback(
        Output("user-type-store", "data"),
        [Input("url", "pathname")],
        prevent_initial_call=False,
    )
    def get_user_type_callback(pathname):
        """Obtiene el tipo de usuario de la sesión."""
        from controllers.auth_controller import AuthController

        try:
            with AuthController() as auth:
                if auth.is_logged_in():
                    user_data = auth.get_current_user_data()
                    return (
                        user_data.get("user_type", "player") if user_data else "player"
                    )
        except:
            pass
        return "player"

    @app.callback(
        Output("ballers-user-content", "children"),
        [Input("user-type-store", "data"), Input("selected-player-id", "data")],
    )
    def update_ballers_content_callback(user_type, selected_player_id):
        """Actualiza contenido de Ballers según tipo de usuario y selección."""
        from pages.ballers_dash import (
            create_player_profile_dash,
            create_players_list_dash,
        )

        if user_type == "player":
            return create_player_profile_dash()
        elif user_type in ["coach", "admin"]:
            if selected_player_id:
                return html.Div(
                    [
                        dbc.Button(
                            "← Back to list",
                            id="back-to-list-btn",
                            color="secondary",
                            className="mb-3",
                        ),
                        create_player_profile_dash(selected_player_id),
                    ]
                )
            else:
                return create_players_list_dash()
        else:
            return dbc.Alert(
                "No tienes permisos para acceder a esta sección.", color="danger"
            )

    @app.callback(
        Output("profile-tab-content", "children"),
        [Input("profile-tabs", "active_tab")],
        prevent_initial_call=False,
    )
    def update_profile_tab_content(active_tab):
        """Actualiza contenido de las tabs del perfil - migrado de Streamlit"""
        from pages.ballers_dash import (
            create_notes_content_dash,
            create_test_results_content_dash,
        )

        if active_tab == "test-results":
            return create_test_results_content_dash()
        elif active_tab == "notes":
            return create_notes_content_dash()
        else:
            return html.Div("Select a tab to view content")

    @app.callback(
        Output("sessions-calendar-content", "children"),
        [Input("apply-filter-btn", "n_clicks")],
        [
            State("filter-from-date", "value"),
            State("filter-to-date", "value"),
            State("filter-status", "value"),
        ],
        prevent_initial_call=False,
    )
    def update_sessions_calendar_content(n_clicks, from_date, to_date, status):
        """Actualiza el contenido del calendario de sesiones - migrado de Streamlit"""
        from pages.ballers_dash import create_sessions_calendar_dash

        return create_sessions_calendar_dash(from_date, to_date, status)

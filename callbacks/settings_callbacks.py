# callbacks/settings_callbacks.py
"""
Callbacks relacionados con la página de Settings.
"""
import dash_bootstrap_components as dbc
from dash import Input, Output, html


def register_settings_callbacks(app):
    """Registra callbacks de Settings en la aplicación Dash."""

    @app.callback(
        Output("settings-main-content", "children"),
        [Input("settings-main-tabs", "active_tab")],
        prevent_initial_call=False,
    )
    def update_settings_main_content(active_tab):
        """Actualiza contenido principal de Settings según la pestaña activa."""
        from pages.settings_dash import create_sync_settings_dash

        if active_tab == "system-tab":
            return create_sync_settings_dash()
        elif active_tab == "users-tab":
            # Users tab con 4 subtabs exactamente como en el original
            return html.Div(
                [
                    dbc.Tabs(
                        [
                            dbc.Tab(
                                label="➕ Create User",
                                tab_id="create-user",
                                active_label_style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Tab(
                                label="✏️ Edit User",
                                tab_id="edit-user",
                                active_label_style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Tab(
                                label="🗑️ Delete User",
                                tab_id="delete-user",
                                active_label_style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Tab(
                                label="📊 User Status",
                                tab_id="user-status",
                                active_label_style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                        ],
                        id="users-subtabs",
                        active_tab="create-user",
                    ),
                    # Contenido de las subtabs
                    html.Div(id="users-subtab-content", className="mt-4"),
                ]
            )
        else:
            return html.Div("Select a tab to view content")

    @app.callback(
        Output("users-subtab-content", "children"),
        [Input("users-subtabs", "active_tab")],
        prevent_initial_call=False,
    )
    def update_users_subtab_content(active_subtab):
        """Actualiza contenido de las subtabs de Users."""
        from pages.settings_dash import create_user_form_dash, create_users_list_dash

        if active_subtab == "create-user":
            return create_user_form_dash()
        elif active_subtab == "edit-user":
            return html.Div(
                [
                    html.H4("✏️ Edit User", style={"color": "rgba(36, 222, 132, 1)"}),
                    create_users_list_dash(),
                ]
            )
        elif active_subtab == "delete-user":
            return html.Div(
                [
                    html.H4("🗑️ Delete User", style={"color": "rgba(36, 222, 132, 1)"}),
                    dbc.Alert("Select users from the list to delete", color="warning"),
                    create_users_list_dash(),
                ]
            )
        elif active_subtab == "user-status":
            return html.Div(
                [
                    html.H4("📊 User Status", style={"color": "rgba(36, 222, 132, 1)"}),
                    dbc.Alert("User activity and status overview", color="info"),
                    create_users_list_dash(),
                ]
            )
        else:
            return html.Div("Select a subtab to view content")

    @app.callback(
        [
            Output("player-fields", "style"),
            Output("coach-fields", "style"),
            Output("admin-fields", "style"),
        ],
        [Input("user-type-selector", "value")],
    )
    def toggle_user_type_fields(user_type):
        """Muestra/oculta campos según el tipo de usuario - migrado de Streamlit"""
        player_style = (
            {"display": "block"} if user_type == "player" else {"display": "none"}
        )
        coach_style = (
            {"display": "block"} if user_type == "coach" else {"display": "none"}
        )
        admin_style = (
            {"display": "block"} if user_type == "admin" else {"display": "none"}
        )

        return player_style, coach_style, admin_style

    @app.callback(
        Output("settings-tab-content", "children"),
        [Input("settings-tabs", "active_tab")],
        prevent_initial_call=False,
    )
    def update_settings_tab_content(active_tab):
        """Actualiza el contenido según la pestaña activa."""
        from pages.settings_dash import (
            create_sync_settings_dash,
            create_system_settings_dash,
            create_user_form_dash,
            create_users_list_dash,
        )

        if active_tab == "users":
            return dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col([create_user_form_dash()], width=12, lg=6),
                            dbc.Col([create_users_list_dash()], width=12, lg=6),
                        ]
                    )
                ]
            )
        elif active_tab == "sync":
            return create_sync_settings_dash()
        elif active_tab == "system":
            return create_system_settings_dash()
        elif active_tab == "reports":
            return html.Div("📊 System reports - To be implemented")
        else:
            return html.Div("Select a tab to view content")

# callbacks/navigation_callbacks.py
"""
Callbacks relacionados con navegación entre páginas.
"""
import dash_bootstrap_components as dbc
from dash import Input, Output, State, html, no_update


def register_navigation_callbacks(app):
    """Registra callbacks de navegación en la aplicación Dash."""

    @app.callback(
        Output("main-content", "children"),
        [Input("url", "pathname")],
        [State("session-store", "data")],
    )
    def display_page(pathname, session_data):
        """Maneja la navegación principal y muestra el contenido apropiado."""
        import logging
        import os

        from common.login_dash import login_page_dash
        from common.menu_dash import create_sidebar_menu_dash
        from controllers.auth_controller import AuthController
        from controllers.db import initialize_database

        # Configurar logging
        DEBUG_MODE = os.getenv("DEBUG", "False") == "True"
        if DEBUG_MODE:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
        else:
            logging.basicConfig(
                level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
            )

        # Inicializar base de datos
        try:
            if not initialize_database():
                return dbc.Alert(
                    [
                        "❌ Critical error: Failed to initialise database",
                        html.Br(),
                        "💡 Suggested solutions:",
                        html.Br(),
                        "1. Run `python data/check_database.py` to diagnose",
                        html.Br(),
                        "2. Verify write permissions on the `data/` folder",
                        html.Br(),
                        "3. Run `python data/seed_database.py` to recreate the database",
                    ],
                    color="danger",
                )
        except Exception as e:
            return dbc.Alert(
                f"❌ Error initializing application: {str(e)}", color="danger"
            )

        # Verificar sesión activa
        with AuthController() as auth:
            if not auth.is_logged_in():
                success, message = auth.restore_session_from_url()
                if success:
                    print(f"Auto-login: {message}")
            has_session = auth.is_logged_in()

        # Si no hay sesión, mostrar página de login
        if not has_session:
            return login_page_dash()

        # Si hay sesión, mostrar layout con flexbox para sidebar y contenido
        return html.Div(
            [
                # Sidebar colapsible
                html.Div(
                    [create_sidebar_menu_dash()],
                    id="sidebar-container",
                    style={
                        "position": "fixed",
                        "top": "0",
                        "left": "0",
                        "z-index": "1000",
                        "height": "100vh",
                    },
                ),
                # Contenido principal que se ajusta al sidebar
                html.Div(
                    [
                        dbc.Container(
                            [
                                # Logo centrado
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                html.Img(
                                                    src="/assets/ballers/logo_white.png",
                                                    style={
                                                        "width": "400px",
                                                        "max-width": "100%",
                                                        "display": "block",
                                                        "margin": "0 auto 20px auto",
                                                        "pointer-events": "none",
                                                    },
                                                )
                                            ],
                                            width=12,
                                            className="text-center",
                                        )
                                    ]
                                ),
                                # Contenido dinámico
                                html.Div(
                                    id="dynamic-content",
                                    children=[],
                                ),
                            ],
                            fluid=True,
                            style={"padding": "20px"},
                        )
                    ],
                    id="main-content-area",
                    style={
                        "margin-left": "300px",
                        "transition": "all 0.3s ease",
                        "background-color": "rgba(0, 0, 0, 0.2)",
                        "min-height": "100vh",
                        "width": "calc(100vw - 300px)",
                    },
                ),
            ],
            style={"overflow-x": "hidden"},
        )

    @app.callback(
        Output("dynamic-content", "children"),
        [Input("selected-menu-item", "data")],
        prevent_initial_call=False,
    )
    def load_dynamic_content(selected_section):
        """Carga contenido dinámico según la sección seleccionada del menú."""
        from common.menu_dash import get_content_path_dash

        if not selected_section:
            selected_section = "Ballers"

        print(f"DEBUG: Loading content for section: {selected_section}")

        try:
            content_module_path = get_content_path_dash(selected_section)

            if content_module_path:
                try:
                    if content_module_path == "pages.ballers":
                        from pages.ballers_dash import show_ballers_content_dash

                        return show_ballers_content_dash()
                    elif content_module_path == "pages.administration":
                        from pages.administration_dash import (
                            show_administration_content_dash,
                        )

                        return show_administration_content_dash()
                    elif content_module_path == "pages.settings":
                        from pages.settings_dash import show_settings_content_dash

                        return show_settings_content_dash()
                    else:
                        return html.Div(
                            [
                                html.H3(
                                    f"📄 {selected_section}",
                                    style={"color": "rgba(36, 222, 132, 1)"},
                                ),
                                html.P("Esta sección está en desarrollo."),
                                dbc.Alert(
                                    "Contenido disponible próximamente.", color="info"
                                ),
                            ]
                        )
                except ImportError as e:
                    return html.Div(
                        [
                            html.H3(
                                "❌ Import Error",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Alert(
                                f"Error importing module {content_module_path}: {str(e)}",
                                color="danger",
                            ),
                        ]
                    )
            else:
                return html.Div(
                    [
                        html.H3(
                            "⚠️ Sección no encontrada",
                            style={"color": "rgba(36, 222, 132, 1)"},
                        ),
                        dbc.Alert(
                            "La sección seleccionada no está disponible.",
                            color="warning",
                        ),
                    ]
                )

        except Exception as e:
            return html.Div(
                [
                    html.H3("❌ Error", style={"color": "rgba(36, 222, 132, 1)"}),
                    dbc.Alert(
                        f"Error al cargar el contenido: {str(e)}", color="danger"
                    ),
                ]
            )

    @app.callback(
        Output("selected-menu-item", "data"),
        [
            Input("menu-ballers", "n_clicks"),
            Input("menu-administration", "n_clicks"),
            Input("menu-settings", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def update_selected_menu_item_callback(
        ballers_clicks, admin_clicks, settings_clicks
    ):
        """Callback para navegación del menú con IDs simples."""
        from dash import callback_context

        if not callback_context.triggered:
            return no_update

        trigger_id = callback_context.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == "menu-ballers":
            print("DEBUG: Menu clicked: Ballers")
            return "Ballers"
        elif trigger_id == "menu-administration":
            print("DEBUG: Menu clicked: Administration")
            return "Administration"
        elif trigger_id == "menu-settings":
            print("DEBUG: Menu clicked: Settings")
            return "Settings"

        return no_update

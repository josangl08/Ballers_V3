# callbacks/navigation_callbacks.py
"""
Callbacks relacionados con navegación entre páginas.
"""
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html, no_update


def register_navigation_callbacks(app):
    """Registra callbacks de navegación en la aplicación Dash."""

    @app.callback(
        Output("main-content", "children"),
        [Input("url", "pathname")],
        [
            State("session-store", "data"),
            State("persistent-session-store", "data"),
            State("session-activity", "data"),
        ],
    )
    def display_page(pathname, session_data, persistent_session_data, activity_data):
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
                        "3. Run `python data/seed_database.py` to recreate the database",  # noqa: E501
                    ],
                    color="danger",
                )
        except Exception as e:
            return dbc.Alert(
                f"❌ Error initializing application: {str(e)}", color="danger"
            )

        # SISTEMA HÍBRIDO: Combinar session stores
        print(f"DEBUG navigation_callbacks: session_data: {session_data}")
        print(
            f"DEBUG navigation_callbacks: persistent_session_data: {persistent_session_data}"  # noqa: E501
        )
        print(f"DEBUG navigation_callbacks: activity_data: {activity_data}")

        # Determinar qué store usar basado en remember_me
        if activity_data and activity_data.get("remember_me"):
            # Usar persistent store si remember_me está activo
            session_data = persistent_session_data or {}
            print("DEBUG: Using persistent session (Remember Me active)")
        else:
            # Usar session store temporal
            session_data = session_data or {}
            print("DEBUG: Using temporary session (Remember Me inactive)")

            # Verificar timeout de 2 horas para sesiones sin remember_me
            if activity_data and activity_data.get("last_activity"):
                import time

                current_time = time.time()
                last_activity = activity_data["last_activity"]
                inactive_time = current_time - last_activity
                TIMEOUT_SECONDS = 2 * 60 * 60  # 2 horas

                if inactive_time > TIMEOUT_SECONDS:
                    print(
                        f"DEBUG: Session timeout ({inactive_time/3600:.1f}h > 2h), clearing session"  # noqa: E501
                    )
                    session_data = {}

        print(f"DEBUG navigation_callbacks: Final session_data: {session_data}")

        with AuthController() as auth:
            if not auth.is_logged_in(session_data):
                success, message = auth.restore_session_from_url()
                if success:
                    print(f"Auto-login: {message}")
            has_session = auth.is_logged_in(session_data)
            print(f"DEBUG navigation_callbacks: has_session = {has_session}")

        # Si no hay sesión, mostrar página de login
        if not has_session:
            return login_page_dash()

        # Si hay sesión, mostrar layout con flexbox para sidebar y contenido
        return html.Div(
            [
                # Sidebar colapsible
                html.Div(
                    [create_sidebar_menu_dash(session_data)],
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
                                                    src="/assets/ballers/logo_white.png",  # noqa: E501
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
                # Global user type store - populated from session data
                dcc.Store(
                    id="user-type-store",
                    data=session_data.get("user_type") if session_data else None,
                ),
            ],
            style={"overflow-x": "hidden"},
        )

    @app.callback(
        Output("dynamic-content", "children"),
        [Input("selected-menu-item", "data")],
        [
            State("session-store", "data"),
            State("persistent-session-store", "data"),
            State("session-activity", "data"),
        ],
        prevent_initial_call=False,
    )
    def load_dynamic_content(
        selected_section, session_data, persistent_session_data, activity_data
    ):
        """Carga contenido dinámico según la sección seleccionada del menú."""
        from common.menu_dash import get_content_path_dash

        if not selected_section:
            selected_section = "Ballers"

        print(f"DEBUG: Loading content for section: {selected_section}")

        # Determinar qué session_data usar (mismo lógica híbrida que en display_page)
        if activity_data and activity_data.get("remember_me"):
            session_data = persistent_session_data or {}
        else:
            session_data = session_data or {}

        try:
            content_module_path = get_content_path_dash(selected_section, session_data)

            if content_module_path:
                try:
                    if content_module_path == "pages.ballers":
                        from pages.ballers_dash import show_ballers_content_dash

                        return show_ballers_content_dash()
                    elif content_module_path == "pages.administration":
                        from pages.administration_dash import (
                            show_administration_content_dash,
                        )

                        # Determinar qué session_data usar (misma lógica que otros callbacks)
                        if activity_data and activity_data.get("remember_me"):
                            effective_session_data = persistent_session_data or {}
                        else:
                            effective_session_data = session_data or {}

                        return show_administration_content_dash(
                            session_data=effective_session_data
                        )
                    elif content_module_path == "pages.settings":
                        from pages.settings_dash import show_settings_content_dash

                        # Determinar qué session_data usar (misma lógica que otros callbacks)
                        if activity_data and activity_data.get("remember_me"):
                            effective_session_data = persistent_session_data or {}
                        else:
                            effective_session_data = session_data or {}

                        return show_settings_content_dash(
                            session_data=effective_session_data
                        )
                    else:
                        return html.Div(
                            [
                                html.H3(
                                    f"📄 {selected_section}",
                                    className="text-primary",
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
                                className="text-primary",
                            ),
                            dbc.Alert(
                                f"Error importing module {content_module_path}: {str(e)}",  # noqa: E501
                                color="danger",
                            ),
                        ]
                    )
            else:
                return html.Div(
                    [
                        html.H3(
                            "⚠️ Sección no encontrada",
                            className="text-primary",
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
                    html.H3("❌ Error", className="text-primary"),
                    dbc.Alert(
                        f"Error al cargar el contenido: {str(e)}", color="danger"
                    ),
                ]
            )

    @app.callback(
        Output("selected-menu-item", "data"),
        [
            Input("menu-ballers", "n_clicks"),
        ],
        [
            State("user-type-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def update_selected_menu_item_callback(ballers_clicks, user_type):
        """Callback para navegación del menú - maneja solo Ballers."""
        from dash import callback_context

        if not callback_context.triggered:
            return no_update

        trigger_id = callback_context.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == "menu-ballers":
            print("DEBUG: Menu clicked: Ballers")
            return "Ballers"

        return no_update

    # Callback separado para menu-administration solo para coach/admin
    @app.callback(
        Output("selected-menu-item", "data", allow_duplicate=True),
        [Input("menu-administration", "n_clicks")],
        [State("user-type-store", "data")],
        prevent_initial_call=True,
    )
    def update_selected_menu_item_administration_callback(admin_clicks, user_type):
        """Callback para menu-administration - solo activo para coach/admin."""
        from dash import callback_context

        if not callback_context.triggered:
            return no_update

        trigger_id = callback_context.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == "menu-administration":
            print("DEBUG: Menu clicked: Administration")
            return "Administration"

        return no_update

    # Callback separado para menu-settings solo para admin
    @app.callback(
        Output("selected-menu-item", "data", allow_duplicate=True),
        [Input("menu-settings", "n_clicks")],
        [State("user-type-store", "data")],
        prevent_initial_call=True,
    )
    def update_selected_menu_item_settings_callback(settings_clicks, user_type):
        """Callback para menu-settings - solo activo para admin."""
        from dash import callback_context

        # Solo procesar si el usuario es admin
        if user_type != "admin":
            return no_update

        if not callback_context.triggered or not settings_clicks:
            return no_update

        print("DEBUG: Menu clicked: Settings")
        return "Settings"

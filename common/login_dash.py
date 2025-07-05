# common/login_dash.py
import os
import sys

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html, no_update

from controllers.auth_controller import (
    AuthController,
    authenticate_user,
    clear_user_session,
    create_user_session,
    restore_session_from_url,
)

# Agregar la ruta raíz al path de Python para importar config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import DEBUG


def login_page_dash():
    """Renderiza la página de login para Dash - Layout centrado como Streamlit."""

    return html.Div(
        [
            # Contenedor principal con altura completa
            dbc.Container(
                [
                    # Espaciado superior
                    html.Div(style={"height": "10vh"}),
                    # Logo centrado en la parte superior
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Img(
                                                src="/assets/ballers/logo_white.png",
                                                style={
                                                    "width": "400px",
                                                    "max-width": "100%",
                                                    "height": "auto",
                                                    "display": "block",
                                                    "margin": "0 auto 40px auto",
                                                },
                                            )
                                        ],
                                        className="text-center",
                                    )
                                ],
                                width=12,
                            )
                        ]
                    ),
                    # Formulario de login centrado
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    # Mensaje de estado
                                    dbc.Alert(
                                        id="login-alert",
                                        is_open=False,
                                        dismissable=True,
                                        className="mb-4",
                                    ),
                                    # Formulario de login
                                    dbc.Card(
                                        [
                                            dbc.CardBody(
                                                [
                                                    html.H4(
                                                        "Login",
                                                        className="card-title mb-4 text-center",
                                                        style={
                                                            "color": "rgba(36, 222, 132, 1)"
                                                        },
                                                    ),
                                                    dbc.InputGroup(
                                                        [
                                                            dbc.InputGroupText("👤"),
                                                            dbc.Input(
                                                                id="username-input",
                                                                placeholder="Username",
                                                                type="text",
                                                                value="",
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    dbc.InputGroup(
                                                        [
                                                            dbc.InputGroupText("🔒"),
                                                            dbc.Input(
                                                                id="password-input",
                                                                placeholder="Password",
                                                                type="password",
                                                                value="",
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    dbc.Checklist(
                                                        id="remember-me",
                                                        options=[
                                                            {
                                                                "label": "Remember me",
                                                                "value": "remember",
                                                            }
                                                        ],
                                                        value=[],
                                                        className="mb-3",
                                                    ),
                                                    dbc.Button(
                                                        "Login",
                                                        id="login-button",
                                                        color="primary",
                                                        size="lg",
                                                        className="w-100 mb-3",
                                                    ),
                                                    html.Hr(),
                                                    dbc.Button(
                                                        "Forgot your password?",
                                                        id="forgot-password-button",
                                                        color="link",
                                                        className="w-100",
                                                        style={
                                                            "color": "rgba(36, 222, 132, 1)"
                                                        },
                                                    ),
                                                    # Panel de recuperación
                                                    dbc.Collapse(
                                                        [
                                                            dbc.Card(
                                                                [
                                                                    dbc.CardBody(
                                                                        [
                                                                            html.H5(
                                                                                "🔑 Password Recovery",
                                                                                className="mb-3",
                                                                                style={
                                                                                    "color": "rgba(36, 222, 132, 1)"
                                                                                },
                                                                            ),
                                                                            dbc.Alert(
                                                                                "Contact administrator to reset your password:",
                                                                                color="info",
                                                                                className="mb-3",
                                                                            ),
                                                                            html.P(
                                                                                "📧 Email: admin@ballersapp.com"
                                                                            ),
                                                                            html.P(
                                                                                "📱 Phone: +34 XXX XXX XXX"
                                                                            ),
                                                                            dbc.Input(
                                                                                id="recovery-email",
                                                                                placeholder="Your registered email:",
                                                                                type="email",
                                                                                className="mb-3",
                                                                            ),
                                                                            dbc.Row(
                                                                                [
                                                                                    dbc.Col(
                                                                                        [
                                                                                            dbc.Button(
                                                                                                "📧 Send Request",
                                                                                                id="send-recovery-button",
                                                                                                color="success",
                                                                                                className="w-100",
                                                                                            )
                                                                                        ],
                                                                                        width=6,
                                                                                    ),
                                                                                    dbc.Col(
                                                                                        [
                                                                                            dbc.Button(
                                                                                                "❌ Cancel",
                                                                                                id="cancel-recovery-button",
                                                                                                color="secondary",
                                                                                                className="w-100",
                                                                                            )
                                                                                        ],
                                                                                        width=6,
                                                                                    ),
                                                                                ]
                                                                            ),
                                                                        ]
                                                                    )
                                                                ],
                                                                className="mt-3",
                                                                style={
                                                                    "background-color": "#f9f9f9",
                                                                    "border-radius": "10px",
                                                                },
                                                            )
                                                        ],
                                                        id="recovery-panel",
                                                        is_open=False,
                                                    ),
                                                ]
                                            )
                                        ],
                                        className="login-card",
                                    ),
                                ],
                                width={"size": 6, "offset": 3},
                                lg={"size": 4, "offset": 4},
                            )
                        ]
                    ),
                ],
                fluid=True,
            )
        ],
        className="login-container",
    )


def logout_dash():
    """Cierra la sesión del usuario - REFACTORIZADA PARA DASH."""
    clear_user_session(show_message=True)
    return True


def register_login_callbacks(app):
    """Registra los callbacks del login manteniendo separación de responsabilidades."""

    @app.callback(
        [
            Output("login-alert", "children"),
            Output("login-alert", "color"),
            Output("login-alert", "is_open"),
            Output("username-input", "value"),
            Output("password-input", "value"),
            Output("url", "pathname"),
        ],
        [Input("login-button", "n_clicks")],
        [
            State("username-input", "value"),
            State("password-input", "value"),
            State("remember-me", "value"),
        ],
        prevent_initial_call=True,
    )
    def handle_login(n_clicks, username, password, remember_me):
        if not n_clicks:
            return no_update, no_update, no_update, no_update, no_update, no_update

        if not username or not password:
            return (
                "Please enter both username and password.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        # Usar controller para autenticación (separación de lógica de negocio)
        success, message, user = authenticate_user(username, password)

        if success and user is not None:
            # Crear sesión con remember_me
            remember = "remember" in (remember_me or [])
            create_user_session(user, remember)
            return message, "success", True, "", "", "/"  # Redirigir para recargar
        else:
            return message, "danger", True, no_update, no_update, no_update

    @app.callback(
        Output("recovery-panel", "is_open"),
        [
            Input("forgot-password-button", "n_clicks"),
            Input("cancel-recovery-button", "n_clicks"),
        ],
        [State("recovery-panel", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_recovery_panel(forgot_clicks, cancel_clicks, is_open):
        if forgot_clicks or cancel_clicks:
            return not is_open
        return is_open

    @app.callback(
        [
            Output("login-alert", "children", allow_duplicate=True),
            Output("login-alert", "color", allow_duplicate=True),
            Output("login-alert", "is_open", allow_duplicate=True),
            Output("recovery-email", "value"),
        ],
        [Input("send-recovery-button", "n_clicks")],
        [State("recovery-email", "value")],
        prevent_initial_call=True,
    )
    def handle_recovery_request(n_clicks, email):
        if not n_clicks:
            return no_update, no_update, no_update, no_update

        if not email:
            return "Please enter your email address.", "danger", True, no_update

        return (
            f"Recovery request sent for: {email}. You will receive instructions via email within 24 hours.",
            "success",
            True,
            "",
        )


if __name__ == "__main__":
    pass

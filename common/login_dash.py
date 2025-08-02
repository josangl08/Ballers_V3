# common/login_dash.py
import os
import sys

import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html, no_update

from controllers.auth_controller import (
    authenticate_user,
    clear_user_session,
    create_user_session,
)

# Agregar la ruta raíz al path de Python para importar config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def login_page_dash():
    """Renderiza la página de login para Dash - Diseño exacto como imagen original."""

    return html.Div(
        [
            # Logo "BLLRS." centrado como en la imagen original
            html.H1(
                "BLLRS.",
                className="login-logo",
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
                                            html.Div(
                                                "Login",
                                                className="login-title",
                                            ),
                                            # Campo Username con label
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Username",
                                                        className="login-label",
                                                    ),
                                                    dbc.Input(
                                                        id="username-input",
                                                        placeholder="",
                                                        type="text",
                                                        value="",
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            # Campo Password con label
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Password",
                                                        className="login-label",
                                                    ),
                                                    dbc.InputGroup(
                                                        [
                                                            dbc.Input(
                                                                id="password-input",
                                                                placeholder="",
                                                                type="password",
                                                                value="",
                                                            ),
                                                            dbc.InputGroupText(
                                                                html.I(
                                                                    className="bi bi-eye"  # noqa: E501
                                                                ),
                                                                style={
                                                                    "background-color": "#555",  # noqa: E501
                                                                    "border": "1px solid #555",  # noqa: E501
                                                                },
                                                            ),
                                                        ],
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
                                                className="login-checkbox",
                                            ),
                                            dbc.Button(
                                                "Login",
                                                id="login-button",
                                                className="login-button",
                                            ),
                                        ]
                                    )
                                ],
                                className="login-form-container",
                            ),
                            # Botón "Forgot your password?" separado
                            html.Div(
                                [
                                    dbc.Button(
                                        "Forgot your password?",
                                        id="forgot-password-button",
                                        className="forgot-password-button",
                                    ),
                                ],
                                className="forgot-password-container",
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
                                                        className="mb-3 text-primary",
                                                    ),
                                                    dbc.Alert(
                                                        "Contact administrator to reset your password:",  # noqa: E501
                                                        color="info",
                                                        className="mb-3",
                                                    ),
                                                    html.P(
                                                        "📧 Email: admin@ballersapp.com"
                                                    ),
                                                    html.P("📱 Phone: +34 XXX XXX XXX"),
                                                    dbc.Input(
                                                        id="recovery-email",
                                                        placeholder="Your registered email:",  # noqa: E501
                                                        type="email",
                                                        className="mb-3",
                                                    ),
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                [
                                                                    dbc.Button(
                                                                        "📧 Send Request",  # noqa: E501
                                                                        id="send-recovery-button",  # noqa: E501
                                                                        color="success",
                                                                        className="w-100",  # noqa: E501
                                                                    )
                                                                ],
                                                                width=6,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Button(
                                                                        "❌ Cancel",
                                                                        id="cancel-recovery-button",  # noqa: E501
                                                                        color="secondary",  # noqa: E501
                                                                        className="w-100",  # noqa: E501
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
                        ],
                        width={"size": 8, "offset": 2},
                        lg={"size": 6, "offset": 3},
                    )
                ]
            ),
            # Componente para manejar la pausa después del login exitoso
            dcc.Interval(
                id="login-redirect-interval",
                interval=2000,  # 2 segundos
                n_intervals=0,
                disabled=True,  # Deshabilitado inicialmente
            ),
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
            Output("login-redirect-interval", "disabled"),
            Output("session-store", "data"),
            Output("persistent-session-store", "data"),
            Output("session-activity", "data"),
        ],
        [
            Input("login-button", "n_clicks"),
            Input("username-input", "n_submit"),
            Input("password-input", "n_submit"),
        ],
        [
            State("username-input", "value"),
            State("password-input", "value"),
            State("remember-me", "value"),
        ],
        prevent_initial_call=True,
    )
    def handle_login(
        n_clicks, username_submit, password_submit, username, password, remember_me
    ):
        # Comprobar si se activó por click del botón o por Enter en los inputs
        if not n_clicks and not username_submit and not password_submit:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        if not username or not password:
            return (
                "Please enter both username and password.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
                no_update,  # interval disabled
                no_update,  # session-store
                no_update,  # persistent-session-store
                no_update,  # session-activity
            )

        # Usar controller para autenticación (separación de lógica de negocio)
        success, message, user = authenticate_user(username, password)

        if success and user is not None:
            # SISTEMA HÍBRIDO DE REMEMBER ME
            remember = "remember" in (remember_me or [])
            session_data = create_user_session(user, remember)

            # Agregar timestamp para timeout
            import time

            current_time = time.time()
            activity_data = {
                "last_activity": current_time,
                "remember_me": remember,
                "login_time": current_time,
            }

            welcome_message = f"¡Bienvenido {user.name}! " + (
                "Sesión persistente activada." if remember else "Sesión temporal (2h)."
            )
            print(f"DEBUG: Login successful for {user.name}, remember_me={remember}")

            if remember:
                # CON REMEMBER ME: Guardar en localStorage persistente
                return (
                    welcome_message,
                    "success",
                    True,
                    "",
                    "",
                    no_update,
                    False,  # Activar interval
                    {},  # session-store vacío
                    session_data,  # persistent-session-store
                    activity_data,  # session-activity
                )
            else:
                # SIN REMEMBER ME: sessionStorage (expira al cerrar navegador)  # noqa: E501
                return (
                    welcome_message,
                    "success",
                    True,
                    "",
                    "",
                    no_update,
                    False,  # Activar interval
                    session_data,  # session-store
                    {},  # persistent-session-store vacío
                    activity_data,  # session-activity
                )
        else:
            return (
                message,
                "danger",
                True,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

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
            f"Recovery request sent for: {email}. "
            f"You will receive instructions via email within 24 hours.",
            "success",
            True,
            "",
        )

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        [Input("login-redirect-interval", "n_intervals")],
        prevent_initial_call=True,
    )
    def handle_login_redirect(n_intervals):
        """Callback para redirigir después del login exitoso con pausa."""
        print(f"DEBUG: handle_login_redirect called with n_intervals={n_intervals}")
        if n_intervals > 0:
            print("DEBUG: Redirecting to /")
            return "/"  # Redirigir a la página principal
        return no_update

    @app.callback(
        [
            Output("url", "pathname", allow_duplicate=True),
            Output("session-store", "data", allow_duplicate=True),
            Output("persistent-session-store", "data", allow_duplicate=True),
            Output("session-activity", "data", allow_duplicate=True),
        ],
        [Input("logout-button", "n_clicks")],
        prevent_initial_call=True,
    )
    def handle_logout_callback(n_clicks):
        """Callback para logout híbrido - Limpia ambos stores."""
        if n_clicks:
            from controllers.auth_controller import AuthController

            # Log del logout usando AuthController
            with AuthController() as auth:
                auth.log_info(
                    "session_logout", message="User logged out via logout button"
                )

            print(
                "🔓 User logged out - clearing ALL session stores and redirecting to login"  # noqa: E501
            )
            # Limpiar TODOS los stores y redirigir
            return "/", {}, {}, {"last_activity": None, "remember_me": False}
        return no_update, no_update, no_update, no_update

    # Callback para renovar actividad cuando el usuario navega
    @app.callback(
        Output("session-activity", "data", allow_duplicate=True),
        [Input("url", "pathname")],
        [State("session-activity", "data")],
        prevent_initial_call=True,
    )
    def update_user_activity(pathname, activity_data):
        """Actualiza timestamp de última actividad en navegación."""
        if activity_data and activity_data.get("remember_me") is False:
            # Solo renovar actividad para sesiones SIN remember_me (que tienen timeout)
            import time

            activity_data["last_activity"] = time.time()
            print(f"DEBUG: Activity renewed at {pathname}")
            return activity_data
        return no_update


if __name__ == "__main__":
    pass

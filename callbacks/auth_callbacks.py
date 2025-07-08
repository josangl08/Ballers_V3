# callbacks/auth_callbacks.py
"""
Callbacks relacionados con autenticación y sesiones.
"""
from dash import Input, Output, State, no_update


def register_auth_callbacks(app):
    """Registra callbacks de autenticación en la aplicación Dash."""

    @app.callback(
        [
            Output("login-alert", "children"),
            Output("login-alert", "color"),
            Output("login-alert", "is_open"),
            Output("username-input", "value"),
            Output("password-input", "value"),
            Output("url", "pathname"),
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
    def handle_login_callback(
        n_clicks, username_submit, password_submit, username, password, remember_me
    ):
        """Callback de login centralizado."""
        from controllers.auth_controller import authenticate_user, create_user_session

        # Comprobar si se activó por click del botón o por Enter en los inputs
        if not n_clicks and not username_submit and not password_submit:
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

        success, message, user = authenticate_user(username, password)

        if success and user is not None:
            remember = "remember" in (remember_me or [])
            create_user_session(user, remember)
            return message, "success", True, "", "", "/"
        else:
            return message, "danger", True, no_update, no_update, no_update

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        [Input("logout-button", "n_clicks")],
        prevent_initial_call=True,
    )
    def handle_logout_callback(n_clicks):
        """Callback para logout."""
        if n_clicks:
            from controllers.auth_controller import clear_user_session

            clear_user_session(show_message=False)
            return "/"
        return "/"

    @app.callback(
        Output("recovery-panel", "is_open"),
        [
            Input("forgot-password-button", "n_clicks"),
            Input("cancel-recovery-button", "n_clicks"),
        ],
        [State("recovery-panel", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_recovery_panel_callback(forgot_clicks, cancel_clicks, is_open):
        """Callback para panel de recuperación."""
        if forgot_clicks or cancel_clicks:
            return not is_open
        return is_open

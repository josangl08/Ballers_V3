# callbacks/sidebar_callbacks.py
"""
Callbacks relacionados con el sidebar colapsible.
"""
from dash import Input, Output, State, callback, no_update


def register_sidebar_callbacks(app):
    """Registra callbacks del sidebar colapsible en la aplicación Dash."""

    @app.callback(
        [
            Output("sidebar-menu", "style"),
            Output("main-content-area", "style"),
            Output("sidebar-collapsed", "data"),
        ],
        [Input("sidebar-toggle", "n_clicks")],
        [State("sidebar-collapsed", "data")],
        prevent_initial_call=True,
    )
    def toggle_sidebar(n_clicks, is_collapsed):
        """Toggle del sidebar colapsible."""
        if not n_clicks:
            return no_update, no_update, no_update

        # Cambiar estado
        new_collapsed = not is_collapsed

        if new_collapsed:
            # Sidebar colapsado
            sidebar_style = {
                "background-color": "#1D1B1A",
                "padding": "10px",
                "height": "100vh",
                "overflow-y": "auto",
                "transition": "all 0.3s ease",
                "width": "70px",
            }
            content_style = {
                "padding-left": "70px",
                "transition": "all 0.3s ease",
                "background-color": "rgba(0, 0, 0, 0.2)",
                "min-height": "100vh",
            }
        else:
            # Sidebar expandido
            sidebar_style = {
                "background-color": "#1D1B1A",
                "padding": "20px",
                "height": "100vh",
                "overflow-y": "auto",
                "transition": "all 0.3s ease",
                "width": "300px",
            }
            content_style = {
                "padding-left": "300px",
                "transition": "all 0.3s ease",
                "background-color": "rgba(0, 0, 0, 0.2)",
                "min-height": "100vh",
            }

        return sidebar_style, content_style, new_collapsed

    @app.callback(
        [
            Output({"type": "menu-text", "index": "ALL"}, "style"),
            Output("sidebar-logo", "style"),
            Output("sidebar-title", "style"),
            Output("auto-sync-area", "style"),
        ],
        [Input("sidebar-collapsed", "data")],
        prevent_initial_call=False,
    )
    def update_sidebar_content_visibility(is_collapsed):
        """Actualiza la visibilidad del contenido del sidebar."""
        if is_collapsed:
            # Ocultar textos y elementos cuando está colapsado
            text_style = {"display": "none"}
            logo_style = {
                "width": "40px",
                "display": "block",
                "margin": "0 auto 10px auto",
                "pointer-events": "none",
                "transition": "all 0.3s ease",
            }
            title_style = {"display": "none"}
            sync_style = {"display": "none"}
        else:
            # Mostrar todo cuando está expandido
            text_style = {"display": "inline"}
            logo_style = {
                "width": "150px",
                "display": "block",
                "margin": "0 auto 20px auto",
                "pointer-events": "none",
                "transition": "all 0.3s ease",
            }
            title_style = {
                "font-size": "14px",
                "font-weight": "bold",
                "margin-bottom": "10px",
                "color": "#FFFFFF",
                "transition": "all 0.3s ease",
                "display": "block",
            }
            sync_style = {"transition": "all 0.3s ease", "display": "block"}

        # Para los textos del menú necesitamos una lista con el mismo estilo para cada elemento
        # Incluye 3 elementos del menú + 1 logout button = 4 elementos total
        num_menu_items = 4  # Ballers, Administration, Settings, Logout
        text_styles = [text_style] * num_menu_items

        return text_styles, logo_style, title_style, sync_style

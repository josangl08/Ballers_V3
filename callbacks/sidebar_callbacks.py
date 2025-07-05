# callbacks/sidebar_callbacks.py
"""
Callbacks relacionados con el sidebar colapsible.
"""
from dash import Input, Output, State, callback, no_update, html


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
                "padding": "5px",
                "height": "100vh",
                "overflow-y": "hidden",
                "transition": "all 0.3s ease",
                "width": "50px",
            }
            content_style = {
                "padding-left": "50px",
                "transition": "all 0.3s ease",
                "background-color": "rgba(0, 0, 0, 0.2)",
                "min-height": "100vh",
                "width": "calc(100vw - 50px)",
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
                "width": "calc(100vw - 300px)",
            }

        return sidebar_style, content_style, new_collapsed

    @app.callback(
        [
            Output("sidebar-logo", "style"),
            Output("sidebar-title", "style"),
            Output("auto-sync-area", "style"),
            Output("sidebar-toggle", "children"),
        ],
        [Input("sidebar-collapsed", "data")],
        prevent_initial_call=False,
    )
    def update_sidebar_content_visibility(is_collapsed):
        """Actualiza la visibilidad del contenido del sidebar."""
        if is_collapsed:
            # Sidebar colapsado
            logo_style = {
                "width": "30px",
                "display": "block",
                "margin": "5px auto",
                "pointer-events": "none",
                "transition": "all 0.3s ease",
            }
            title_style = {"display": "none"}
            sync_style = {"display": "none"}
            # Icono de flecha hacia la derecha para expandir
            toggle_icon = html.I(className="bi bi-chevron-right", style={"font-size": "20px"})
        else:
            # Sidebar expandido
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
            # Icono de flecha hacia la izquierda para colapsar
            toggle_icon = html.I(className="bi bi-chevron-left", style={"font-size": "20px"})

        return logo_style, title_style, sync_style, toggle_icon

    @app.callback(
        Output({"type": "menu-text", "index": "ALL"}, "style"),
        [Input("sidebar-collapsed", "data")],
        prevent_initial_call=True,
    )
    def update_menu_text_visibility(is_collapsed):
        """Actualiza la visibilidad de los textos del menú."""
        if is_collapsed:
            return {"display": "none"}
        else:
            return {"display": "inline"}

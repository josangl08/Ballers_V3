# common/menu_dash.py
from typing import Optional

import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html, no_update

from controllers.menu_controller import MenuController, get_sync_status_for_ui
from controllers.sync_coordinator import force_manual_sync


def get_sync_status_component_dash(stats: dict):
    """
    Retorna componente de estado de sync para Dash.
    """
    # Construir texto de estadísticas
    changes = []
    if stats["imported"] > 0:
        changes.append(f"{stats['imported']} 📥")
    if stats["updated"] > 0:
        changes.append(f"{stats['updated']} 🔄")
    if stats["deleted"] > 0:
        changes.append(f"{stats['deleted']} 🗑️")

    problems = []
    if stats["rejected"] > 0:
        problems.append(f"{stats['rejected']} 🚫")
    if stats["warnings"] > 0:
        problems.append(f"{stats['warnings']} ⚠️")

    # Construir mensaje completo
    message_parts = [f"Sync: ⏱ {stats['sync_time']:.1f}s"]

    if changes or problems:
        message_parts.append(" ● ")
        message_parts.extend(changes + problems)
    else:
        message_parts.append("● No Changes")

    message = " ".join(message_parts)

    # Determinar color apropiado
    has_rejected = stats["rejected"] > 0
    has_warnings = stats["warnings"] > 0
    has_changes = stats["imported"] + stats["updated"] + stats["deleted"] > 0

    if has_rejected:
        color = "danger"
    elif has_warnings:
        color = "warning"
    elif has_changes:
        color = "success"
    else:
        color = "info"

    components = [dbc.Alert(message, color=color, className="mb-2")]

    # Botón para ver detalles si hay problemas
    if has_rejected or has_warnings:
        components.append(
            dbc.Button(
                "🔍 See details",
                id="view-sync-details",
                color="secondary",
                size="sm",
                className="w-100 mb-2",
            )
        )

    return components


def get_auto_sync_area_dash():
    """
    Retorna componentes de área de auto-sync para Dash.
    """
    # Usar MenuController para obtener datos
    sync_data = get_sync_status_for_ui()

    if not sync_data or not sync_data["show_sync_area"]:
        return []

    components = []

    # Mostrar estadísticas si hay datos
    if sync_data["sync_stats"]:
        components.append(html.Hr())
        components.extend(get_sync_status_component_dash(sync_data["sync_stats"]))
        components.append(html.Hr())

    # Mostrar estado de auto-sync
    auto_status = sync_data["auto_sync_status"]
    if auto_status["type"] == "success":
        color = "success"
    else:
        color = "info"

    components.append(dbc.Alert(auto_status["status"], color=color, className="mb-2"))

    # Quick sync button
    components.append(
        dbc.Button(
            "⚡ Quick Sync",
            id="quick-sync-button",
            color="primary",
            className="w-100 mb-2",
        )
    )

    # Alert para mostrar resultado de sync
    components.append(
        dbc.Alert(
            id="sync-result-alert", is_open=False, dismissable=True, className="mb-2"
        )
    )

    return components


def create_sidebar_menu_dash():
    """
    Crea menú lateral colapsible para Dash usando MenuController.
    """
    # Crear instancia del controller
    controller = MenuController()

    # Verificar si hay usuario logueado
    if not controller.is_user_logged_in():
        return html.Div()

    # Obtener configuración del menú
    menu_config = controller.get_menu_config()
    menu_title = controller.get_menu_title()

    # Crear opciones del menú con IDs simples
    menu_items = []
    for i, (option, icon) in enumerate(
        zip(menu_config["options"], menu_config["icons"])
    ):
        menu_items.append(
            dbc.Button(
                [
                    html.I(
                        className=f"bi bi-{icon} me-2",
                        style={"color": "#1DDD6E", "font-size": "18px"},
                    ),
                    html.Span(
                        option,
                        id={"type": "menu-text", "index": i},
                        className="menu-text",
                    ),
                ],
                id=f"menu-{option.lower().replace(' ', '-')}",
                color="link",
                className="text-white text-start w-100 py-2 mb-1",
                style={
                    "font-size": "16px",
                    "text-align": "left",
                    "border": "none",
                    "background": "transparent",
                    "text-decoration": "none",
                },
            )
        )

    # Componentes del sidebar colapsible
    sidebar_content = [
        # Botón toggle en la esquina superior derecha
        html.Div(
            dbc.Button(
                html.I(className="bi bi-chevron-left", style={"font-size": "20px"}),
                id="sidebar-toggle",
                color="link",
                className="text-white p-1",
                style={
                    "background": "transparent",
                    "border": "none",
                    "position": "absolute",
                    "top": "10px",
                    "right": "10px",
                },
            ),
            style={"position": "relative", "height": "40px"},
        ),
        # Logo (con clase para ocultar/mostrar)
        html.Div(
            [
                html.Img(
                    src="/assets/ballers/isotipo_white.png",
                    id="sidebar-logo",
                    style={
                        "width": "150px",
                        "display": "block",
                        "margin": "0 auto 20px auto",
                        "pointer-events": "none",
                        "transition": "all 0.3s ease",
                    },
                )
            ],
            className="text-center sidebar-logo",
        ),
        # Título del menú (con clase para ocultar/mostrar)
        html.H6(
            menu_title,
            id="sidebar-title",
            className="text-center text-white mb-3 sidebar-title",
            style={
                "font-size": "14px",
                "font-weight": "bold",
                "margin-bottom": "10px",
                "color": "#FFFFFF",
                "transition": "all 0.3s ease",
            },
        ),
        # Menú de navegación con botones simples
        html.Div(menu_items, className="mb-3"),
        # Área de auto-sync (con clase para ocultar/mostrar)
        html.Div(
            id="auto-sync-area",
            children=get_auto_sync_area_dash(),
            className="sidebar-sync-area",
            style={"transition": "all 0.3s ease"},
        ),
        # Botón de logout con estilos migrados
        dbc.Button(
            [
                html.I(className="bi bi-box-arrow-right me-2"),
                html.Span(
                    "📤 Log Out",
                    id={"type": "menu-text", "index": "logout"},
                    className="menu-text",
                ),
            ],
            id="logout-button",
            className="w-100 mt-3",
            style={
                "border-radius": "20px",
                "font-weight": "500",
                "background-color": "#333333",
                "color": "rgba(36, 222, 132, 1)",
                "border": "none",
                "padding": "0.5rem 1rem",
                "transition": "all 0.3s ease",
            },
        ),
        # Stores
        dcc.Store(id="selected-menu-item", data="Ballers"),
        dcc.Store(id="sidebar-collapsed", data=False),
    ]

    return html.Div(
        sidebar_content,
        id="sidebar-menu",
        style={
            "background-color": "#1D1B1A",
            "padding": "20px",
            "height": "100vh",
            "overflow-y": "auto",
            "transition": "all 0.3s ease",
            "width": "300px",
        },
    )


def get_content_path_dash(section: str) -> Optional[str]:
    """
    Función de compatibilidad que usa MenuController para Dash.

    Args:
        section: Sección seleccionada en el menú

    Returns:
        str: Ruta al módulo de contenido
    """
    controller = MenuController()
    return controller.get_content_route(section)


def register_menu_callbacks(app):
    """Registra los callbacks del menú manteniendo separación de responsabilidades."""

    @app.callback(
        Output("selected-menu-item", "data"),
        [Input({"type": "nav-link", "index": "ALL"}, "n_clicks")],
        [State({"type": "nav-link", "index": "ALL"}, "children")],
        prevent_initial_call=True,
    )
    def update_selected_menu_item(n_clicks_list, children_list):
        if not any(n_clicks_list):
            return no_update

        # Encontrar cuál fue clickeado
        for i, n_clicks in enumerate(n_clicks_list):
            if n_clicks:
                # Extraer el texto del elemento clickeado
                if children_list[i] and len(children_list[i]) > 1:
                    return children_list[i][1]  # El texto está en la segunda posición

        return no_update

    @app.callback(
        [
            Output("sync-result-alert", "children"),
            Output("sync-result-alert", "color"),
            Output("sync-result-alert", "is_open"),
        ],
        [Input("quick-sync-button", "n_clicks")],
        prevent_initial_call=True,
    )
    def handle_quick_sync(n_clicks):
        if not n_clicks:
            return no_update, no_update, no_update

        # Usar controller para lógica de negocio (separación de responsabilidades)
        result = force_manual_sync()

        if result["success"]:
            return "✅ Sync completed successfully", "success", True
        else:
            return f"❌ Error: {result['error']}", "danger", True


if __name__ == "__main__":
    pass

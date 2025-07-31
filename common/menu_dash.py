# common/menu_dash.py
from typing import Dict, Optional

import dash_bootstrap_components as dbc
from dash import dcc, html

from controllers.menu_controller import MenuController

# force_manual_sync importado solo donde se necesita (settings_callbacks.py)
# get_sync_status_for_ui no utilizado - eliminado para cumplir flake8


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


def get_auto_sync_area_dash(session_data: Optional[Dict] = None):
    """
    Retorna componentes de área de auto-sync para Dash.
    ELIMINADO: Auto-sync funcionalidad removida - solo sync manual en settings.
    """
    # Auto-sync funcionalidad eliminada - solo sync manual disponible en settings
    return []


def create_sidebar_menu_dash(session_data: Optional[Dict] = None):
    """
    Crea menú lateral colapsible para Dash usando MenuController.
    TEMPORAL: Acepta session_data para compatibilidad.
    """
    # Crear instancia del controller con session_data
    controller = MenuController(session_data)

    # TEMPORAL: Comentar validación de login para que el menu siempre aparezca
    # Esto debe ser arreglado cuando se complete la migración de MenuController
    # if not controller.is_user_logged_in():
    #     return html.Div()

    # Obtener configuración del menú
    menu_config = controller.get_menu_config()

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
                className="sidebar-menu-button text-white text-start w-100",
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
                    "top": "0px",
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
                        "width": "120px",
                        "display": "block",
                        "margin": "0 auto 20px auto",
                        "pointer-events": "none",
                        "transition": "all 0.3s ease",
                    },
                )
            ],
            className="text-center sidebar-logo",
        ),
        # Recuadro negro con información del usuario
        html.Div(
            [
                html.Div(
                    [
                        # Foto de perfil
                        html.Div(
                            html.Img(
                                src="/assets/profile_photos/default_profile.png",
                                style={
                                    "width": "40px",
                                    "height": "40px",
                                    "border-radius": "50%",
                                    "object-fit": "cover",
                                    "margin-right": "10px",
                                },
                            ),
                            id="sidebar-user-photo",
                        ),
                        # Información del usuario
                        html.Div(
                            [
                                html.Div(
                                    controller.user_name or "Administrator",
                                    className="sidebar-user-name",
                                    style={
                                        "color": "#FFFFFF",
                                        "font-size": "14px",
                                        "font-weight": "bold",
                                        "margin-bottom": "2px",
                                    },
                                ),
                                html.Div(
                                    [
                                        html.I(
                                            className="bi bi-key",
                                            style={
                                                "color": "#FFD700",
                                                "font-size": "12px",
                                                "margin-right": "5px",
                                            },
                                        ),
                                        html.Span(
                                            "Admin",
                                            style={
                                                "color": "#FFFFFF",
                                                "font-size": "12px",
                                            },
                                        ),
                                    ],
                                    className="sidebar-user-type",
                                ),
                            ],
                            className="sidebar-user-info",
                            style={"display": "flex", "flex-direction": "column"},
                        ),
                    ],
                    style={
                        "display": "flex",
                        "align-items": "center",
                        "padding": "10px",
                        "background-color": "#1D1B1A",
                        "border-radius": "10px",
                    },
                ),
            ],
            id="sidebar-user-container",
            className="sidebar-user-container",
        ),
        # Menú de navegación con botones simples
        html.Div(menu_items),
        # Área de auto-sync en su propio div
        html.Div(
            id="auto-sync-area",
            children=get_auto_sync_area_dash(session_data),
            className="sidebar-sync-area",
            style={"transition": "all 0.3s ease"},
        ),
        # Botones de acción agrupados
        html.Div(
            [
                dbc.Button(
                    [
                        html.I(className="bi bi-box-arrow-right me-2"),
                        html.Span(
                            "Log Out",
                            id={"type": "menu-text", "index": "logout"},
                            className="menu-text",
                        ),
                    ],
                    id="logout-button",
                    className="sidebar-action-button w-100",
                    style={"margin-bottom": "8px"},
                ),
            ],
            className="sidebar-action-buttons",
        ),
        # Stores
        dcc.Store(id="selected-menu-item", data="Ballers"),
        dcc.Store(id="sidebar-collapsed", data=False),
    ]

    return html.Div(
        sidebar_content,
        id="sidebar-menu",
        style={
            "background-color": "#333333",
            "padding": "20px",
            "height": "100vh",
            "overflow-y": "auto",
            "transition": "all 0.3s ease",
            "width": "300px",
        },
    )


def get_content_path_dash(
    section: str, session_data: Optional[Dict] = None
) -> Optional[str]:
    """
    Función de compatibilidad que usa MenuController para Dash.

    Args:
        section: Sección seleccionada en el menú
        session_data: Datos de sesión de Dash

    Returns:
        str: Ruta al módulo de contenido
    """
    controller = MenuController(session_data)
    return controller.get_content_route(section)


def register_menu_callbacks(app):
    """Registra los callbacks del menú manteniendo separación de responsabilidades."""

    # Callback removido - ya existe en navigation_callbacks.py
    # Quick sync callback eliminado - funcionalidad movida a settings

    # TEMPORAL: Callback de logout movido a auth_callbacks.py para evitar duplicación
    # @app.callback(
    #     Output("url", "pathname", allow_duplicate=True),
    #     [Input("logout-button", "n_clicks")],
    #     prevent_initial_call=True,
    # )
    # def handle_logout(n_clicks):
    #     """Callback para logout."""
    #     if n_clicks:
    #         from controllers.auth_controller import clear_user_session
    #
    #         clear_user_session(show_message=False)
    #         return "/"
    #     return no_update


if __name__ == "__main__":
    pass

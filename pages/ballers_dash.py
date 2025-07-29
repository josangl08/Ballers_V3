# pages/ballers_dash.py - Migración visual de ballers.py a Dash
from __future__ import annotations

import datetime

import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html  # noqa: F401

from controllers.player_controller import get_player_profile_data, get_players_for_list


# Funciones simples para reemplazar cloud_utils removido
def is_streamlit_cloud():
    return False


def show_cloud_feature_limitation(feature_name):
    return f"Feature {feature_name} not available in local mode"


def show_cloud_mode_info():
    return "Running in local mode"


def create_player_profile_dash(player_id=None, user_id=None):
    """Crea el perfil de un jugador para Dash - migrado exactamente de Streamlit"""

    try:
        # Obtener datos usando controller (lógica mantenida de Streamlit)
        profile_data = get_player_profile_data(player_id=player_id, user_id=user_id)

        if not profile_data:
            return dbc.Alert("No player information found.", color="danger")

        player = profile_data["player"]
        user = profile_data["user"]
        stats = profile_data.get("stats", {})

    except Exception as e:
        return dbc.Alert(f"Error loading player profile: {str(e)}", color="danger")

    # Layout completo del perfil migrado exactamente de Streamlit (lines 35-285)
    return dbc.Container(
        [
            # Cabecera con foto e info (reestructurada)
            dbc.Row(
                [
                    # Columna 1: Foto del perfil
                    dbc.Col(
                        [
                            html.Img(
                                src=user.profile_photo
                                or "/assets/profile_photos/default_profile.png",
                                style={
                                    "width": "180px",
                                    "height": "180px",
                                    "object-fit": "cover",
                                    "border-radius": "50%",
                                    "border": "3px solid rgba(36, 222, 132, 1)",
                                },
                                className="mx-auto d-block ms-3 mt-2",
                            )
                        ],
                        width=3,
                    ),
                    # Columna 2: Información básica centrada
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.H2(
                                        user.name,
                                        style={"color": "rgba(36, 222, 132, 1)"},
                                        className="title-lg mb-3",
                                    ),
                                    html.P(
                                        [
                                            html.I(
                                                className="bi bi-at me-2",
                                                style={"color": "#24DE84"},
                                            ),
                                            user.username,
                                        ],
                                        className="mb-2",
                                        style={"color": "#FFFFFF"},
                                    ),
                                    html.P(
                                        [
                                            html.I(
                                                className="bi bi-envelope me-2",
                                                style={"color": "#24DE84"},
                                            ),
                                            user.email,
                                        ],
                                        className="mb-2",
                                        style={"color": "#FFFFFF"},
                                    ),
                                    html.P(
                                        [
                                            html.I(
                                                className="bi bi-telephone me-2",
                                                style={"color": "#24DE84"},
                                            ),
                                            user.phone or "No phone",
                                        ],
                                        className="mb-2",
                                        style={"color": "#FFFFFF"},
                                    ),
                                    html.P(
                                        [
                                            html.I(
                                                className="bi bi-calendar-date me-2",
                                                style={"color": "#24DE84"},
                                            ),
                                            f"Age: {stats.get('age', 'N/A')}",
                                        ],
                                        className="mb-2",
                                        style={"color": "#FFFFFF"},
                                    ),
                                    html.P(
                                        [
                                            html.I(
                                                className="bi bi-briefcase me-2",
                                                style={"color": "#24DE84"},
                                            ),
                                            (
                                                f"Service: "
                                                f"{player.service or 'No service'}"
                                            ),
                                        ],
                                        className="mb-2",
                                        style={"color": "#FFFFFF"},
                                    ),
                                    html.P(
                                        [
                                            html.I(
                                                className="bi bi-collection me-2",
                                                style={"color": "#24DE84"},
                                            ),
                                            f"Enrolled Sessions: {player.enrolment}",
                                        ],
                                        className="mb-2",
                                        style={"color": "#FFFFFF"},
                                    ),
                                ],
                                style={
                                    "padding-left": "100px"
                                },  # Separar un poco más de la imagen
                            )
                        ],
                        width=9,  # Expandir para ocupar más espacio
                    ),
                ],
                className="mb-4",
            ),
            # Estadísticas en métricas (migrada de lines 70-95)
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                html.I(className="bi bi-check-circle"),
                                                className="text-center",
                                                style={
                                                    "color": "rgba(36, 222, 132, 1)"
                                                },
                                            ),
                                            html.H2(
                                                str(stats.get("completed", 0)),
                                                className="text-center",
                                                style={"color": "#FFFFFF"},
                                            ),
                                            html.P(
                                                "Completed",
                                                className="text-center",
                                                style={"color": "#FFFFFF"},
                                            ),
                                        ]
                                    )
                                ],
                                style={
                                    "background-color": "#333333",
                                    "border-radius": "10px",
                                    "text-align": "center",
                                },
                            )
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                html.I(
                                                    className="bi bi-calendar-event"
                                                ),
                                                className="text-center",
                                                style={
                                                    "color": "rgba(36, 222, 132, 1)"
                                                },
                                            ),
                                            html.H2(
                                                str(stats.get("scheduled", 0)),
                                                className="text-center",
                                                style={"color": "#FFFFFF"},
                                            ),
                                            html.P(
                                                "Scheduled",
                                                className="text-center",
                                                style={"color": "#FFFFFF"},
                                            ),
                                        ]
                                    )
                                ],
                                style={
                                    "background-color": "#333333",
                                    "border-radius": "10px",
                                    "text-align": "center",
                                },
                            )
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                html.I(className="bi bi-arrow-repeat"),
                                                className="text-center",
                                                style={
                                                    "color": "rgba(36, 222, 132, 1)"
                                                },
                                            ),
                                            html.H2(
                                                str(stats.get("remaining", 0)),
                                                className="text-center",
                                                style={"color": "#FFFFFF"},
                                            ),
                                            html.P(
                                                "Remaining",
                                                className="text-center",
                                                style={"color": "#FFFFFF"},
                                            ),
                                        ]
                                    )
                                ],
                                style={
                                    "background-color": "#333333",
                                    "border-radius": "10px",
                                    "text-align": "center",
                                },
                            )
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                html.I(className="bi bi-calendar-plus"),
                                                className="text-center",
                                                style={
                                                    "color": "rgba(36, 222, 132, 1)"
                                                },
                                            ),
                                            html.H2(
                                                "Next",
                                                className="text-center",
                                                style={"color": "#FFFFFF"},
                                            ),
                                            html.P(
                                                stats.get(
                                                    "next_session", "No sessions"
                                                ),
                                                className="text-center",
                                                style={"color": "#FFFFFF"},
                                            ),
                                        ]
                                    )
                                ],
                                style={
                                    "background-color": "#333333",
                                    "border-radius": "10px",
                                    "text-align": "center",
                                },
                            )
                        ],
                        width=3,
                    ),
                ],
                className="mb-4",
            ),
            # Separador horizontal - opaco 1.5px
            html.Hr(
                style={
                    "border": "none",
                    "height": "1.5px",
                    "background-color": "#333333",
                    "margin": "1.5rem 0",
                    "opacity": "1",
                }
            ),
            # Filtros de fecha y estado - directo sobre fondo
            html.Div(
                [
                    html.H5(
                        [
                            html.I(className="bi bi-calendar-week me-2"),
                            f"Sessions Calendar of {user.name}",
                        ],
                        style={
                            "color": "rgba(36, 222, 132, 1)",
                            "margin-bottom": "20px",
                            "font-size": "1.1rem",
                        },
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "From",
                                        style={
                                            "color": "#FFFFFF",
                                            "font-weight": "500",
                                            "font-size": "0.9rem",
                                        },
                                    ),
                                    dbc.Input(
                                        id={
                                            "type": "auto-hide-date",
                                            "index": "ballers-filter-from-date",
                                        },
                                        type="date",
                                        className="date-filter-input",
                                        value=(
                                            datetime.date.today()
                                            - datetime.timedelta(days=7)
                                        ).isoformat(),
                                    ),
                                    # Div de output para auto-hide callback
                                    html.Div(
                                        id={
                                            "type": "datepicker-output",
                                            "index": "ballers-filter-from-date",
                                        },
                                        style={"display": "none"},
                                    ),
                                ],
                                width=3,  # Reducir de 4 a 3
                            ),
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "To",
                                        style={
                                            "color": "#FFFFFF",
                                            "font-weight": "500",
                                            "font-size": "0.9rem",
                                        },
                                    ),
                                    dbc.Input(
                                        id={
                                            "type": "auto-hide-date",
                                            "index": "ballers-filter-to-date",
                                        },
                                        type="date",
                                        className="date-filter-input",
                                        value=(
                                            datetime.date.today()
                                            + datetime.timedelta(days=21)
                                        ).isoformat(),
                                    ),
                                    # Div de output para auto-hide callback
                                    html.Div(
                                        id={
                                            "type": "datepicker-output",
                                            "index": "ballers-filter-to-date",
                                        },
                                        style={"display": "none"},
                                    ),
                                ],
                                width=3,  # Reducir de 4 a 3
                            ),
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    dbc.Label(
                                                        "Status",
                                                        style={
                                                            "color": "#FFFFFF",
                                                            "font-weight": "500",
                                                            "margin-bottom": "8px",
                                                            "font-size": "0.9rem",
                                                        },
                                                    ),
                                                ],
                                                style={
                                                    "text-align": "left"
                                                },  # Alinear label a la izquierda
                                            ),
                                            html.Div(
                                                [
                                                    html.Span(
                                                        "Scheduled",
                                                        id="status-scheduled",
                                                        className="status-scheduled",
                                                        style={
                                                            "cursor": "pointer",
                                                            "margin-right": "10px",
                                                        },
                                                    ),
                                                    html.Span(
                                                        "Completed",
                                                        id="status-completed",
                                                        className="status-completed",
                                                        style={
                                                            "cursor": "pointer",
                                                            "margin-right": "10px",
                                                        },
                                                    ),
                                                    html.Span(
                                                        "Canceled",
                                                        id="status-canceled",
                                                        className="status-canceled",
                                                        style={
                                                            "cursor": "pointer",
                                                        },
                                                    ),
                                                ],
                                                style={
                                                    "text-align": "left"
                                                },  # Alinear badges a la izquierda
                                            ),
                                        ],
                                        style={
                                            "margin-left": "auto",
                                            "width": "fit-content",
                                        },  # Mover todo el conjunto a la derecha manteniendo alineación interna izquierda
                                    )
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-4",
                    ),
                    # Calendario - directo sobre fondo
                    html.Div(
                        [html.Div(id="calendar-display")],
                        style={"margin-bottom": "30px", "margin-top": "20px"},
                    ),
                    # Lista de sesiones - directo sobre fondo
                    html.Div(
                        [
                            html.H6(
                                [
                                    html.I(className="bi bi-list-ul me-2"),
                                    "Sessions List",
                                ],
                                style={
                                    "color": "rgba(36, 222, 132, 1)",
                                    "margin-bottom": "15px",
                                    "font-size": "1rem",
                                },
                            ),
                            html.Div(id="sessions-table"),
                        ],
                        style={"margin-bottom": "30px"},
                    ),
                ],
                style={"margin-bottom": "30px"},
            ),
            # Tabs de Test Results y Notes - estilo minimalista
            dbc.Tabs(
                [
                    dbc.Tab(
                        label="Test Results",
                        tab_id="test-results",
                        active_label_style={
                            "color": "rgba(36, 222, 132, 1)",
                            "font-size": "0.9rem",
                        },
                        label_style={"font-size": "0.9rem"},
                    ),
                    dbc.Tab(
                        label="Notes",
                        tab_id="notes",
                        active_label_style={
                            "color": "rgba(36, 222, 132, 1)",
                            "font-size": "0.9rem",
                        },
                        label_style={"font-size": "0.9rem"},
                    ),
                ],
                id="profile-tabs",
                active_tab="test-results",
                style={"margin-bottom": "20px"},
            ),
            # Contenido de las tabs - directo sobre fondo
            html.Div(id="profile-tab-content", style={"margin-top": "20px"}),
            # Alerta para mensajes
            dbc.Alert(
                id="profile-alert", is_open=False, dismissable=True, className="mb-3"
            ),
        ]
    )


def create_player_card(player_data):
    """Crea una tarjeta individual de jugador reutilizable"""
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    # Foto de perfil centrada con estilo circular
                    html.Div(
                        [
                            html.Img(
                                src=(
                                    player_data["profile_photo"]
                                    if player_data["profile_photo"]
                                    else "/assets/profile_photos/default_profile.png"
                                ),
                                style={
                                    "width": "80px",
                                    "height": "80px",
                                    "object-fit": "cover",
                                    "border-radius": "50%",
                                    "margin": "0 auto 15px auto",
                                    "display": "block",
                                },
                            )
                        ],
                        className="text-center",
                    ),
                    # Nombre del jugador
                    html.H5(
                        player_data["name"],
                        className="text-center",
                        style={"color": "#FFFFFF", "margin-bottom": "10px"},
                    ),
                    # Información del jugador en formato vertical centrado
                    html.Div(
                        [
                            html.P(
                                f"Age: {player_data['age'] if player_data['age'] else 'N/A'} years",
                                className="text-center text-muted mb-1",
                            ),
                            html.P(
                                f"Service: {player_data['service'] or 'Basic'}",
                                className="text-center text-muted mb-1",
                            ),
                            html.P(
                                f"Sessions: {player_data.get('sessions_count', 0)}",
                                className="text-center text-muted mb-1",
                            ),
                            html.P(
                                f"Remaining: {player_data.get('remaining_sessions', 0)}",
                                className="text-center text-muted mb-3",
                            ),
                        ]
                    ),
                    # Información de próxima sesión pegada al borde inferior
                    html.Div(
                        [
                            html.P(
                                f"Next Session: {player_data.get('next_session', 'To be confirmed')}",
                                className="text-center text-muted mb-3",
                                style={"font-size": "0.85rem", "font-style": "italic"},
                            ),
                            # Botón Ver Perfil usando las clases CSS
                            dbc.Button(
                                "View Profile",
                                id={
                                    "type": "view-profile-button",
                                    "index": player_data["player_id"],
                                },
                                className="w-100",  # Los estilos están en CSS
                            ),
                        ],
                        className="mt-auto",
                    ),
                ],
                style={"display": "flex", "flex-direction": "column", "height": "100%"},
            )
        ],
        className="player-card",  # Usar la clase CSS existente
        style={"height": "100%"},  # Asegurar altura completa
    )


def create_players_list_dash():
    """Crea la lista de jugadores para Dash - migrado exactamente de Streamlit"""

    # Obtener datos usando controller (como en la función original)
    players_data = get_players_for_list()

    if not players_data:
        return dbc.Alert("No registered players.", color="info")

    # Crear tarjetas de jugadores usando la función reutilizable
    player_cards = []
    for i, player_data in enumerate(players_data):
        card = create_player_card(player_data)
        player_cards.append(dbc.Col([card], width=12, md=6, lg=4))

    # Filtro de búsqueda usando estilos existentes
    search_section = dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Input(
                        id="search-player-input",
                        placeholder="Search Player by name:",
                        type="text",
                        className="dash-input mb-3",  # Usar la clase existente
                    )
                ],
                width=12,
            )
        ]
    )

    return dbc.Container(
        [
            search_section,
            dbc.Row(
                player_cards,
                id="players-cards-container",
                className="g-3",  # Espaciado consistente entre cards
            ),
        ],
        fluid=True,  # Para ocupar todo el espacio disponible
        className="h-100",  # Altura completa
    )


def create_overview_content_dash():
    """Crea el contenido de overview para Dash - migrado de Streamlit"""

    return dbc.Container(
        [
            # Métricas principales (migradas de Streamlit)
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                "👥",
                                                className="text-center",
                                                style={
                                                    "color": "rgba(36, 222, 132, 1)"
                                                },
                                            ),
                                            html.H2(
                                                "0",
                                                className="text-center",
                                                id="total-players",
                                            ),
                                            html.P(
                                                "Total Players",
                                                className="text-center text-muted",
                                            ),
                                        ]
                                    )
                                ],
                                style={
                                    "background-color": "#3b3b3a",
                                    "border-radius": "5px",
                                    "box-shadow": "0 2px 4px rgba(0, 0, 0, 0.05)",
                                },
                            )
                        ],
                        width=12,
                        md=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                html.I(
                                                    className="bi bi-calendar-event"
                                                ),
                                                className="text-center",
                                                style={
                                                    "color": "rgba(36, 222, 132, 1)"
                                                },
                                            ),
                                            html.H2(
                                                "0",
                                                className="text-center",
                                                id="total-sessions",
                                            ),
                                            html.P(
                                                "Total Sessions",
                                                className="text-center text-muted",
                                            ),
                                        ]
                                    )
                                ],
                                style={
                                    "background-color": "#3b3b3a",
                                    "border-radius": "5px",
                                    "box-shadow": "0 2px 4px rgba(0, 0, 0, 0.05)",
                                },
                            )
                        ],
                        width=12,
                        md=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                "✅",
                                                className="text-center",
                                                style={
                                                    "color": "rgba(36, 222, 132, 1)"
                                                },
                                            ),
                                            html.H2(
                                                "0",
                                                className="text-center",
                                                id="completed-sessions",
                                            ),
                                            html.P(
                                                "Completed Sessions",
                                                className="text-center text-muted",
                                            ),
                                        ]
                                    )
                                ],
                                style={
                                    "background-color": "#3b3b3a",
                                    "border-radius": "5px",
                                    "box-shadow": "0 2px 4px rgba(0, 0, 0, 0.05)",
                                },
                            )
                        ],
                        width=12,
                        md=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                html.I(className="bi bi-arrow-repeat"),
                                                className="text-center",
                                                style={
                                                    "color": "rgba(36, 222, 132, 1)"
                                                },
                                            ),
                                            html.H2(
                                                "0",
                                                className="text-center",
                                                id="active-sessions",
                                            ),
                                            html.P(
                                                "Active Sessions",
                                                className="text-center text-muted",
                                            ),
                                        ]
                                    )
                                ],
                                style={
                                    "background-color": "#3b3b3a",
                                    "border-radius": "5px",
                                    "box-shadow": "0 2px 4px rgba(0, 0, 0, 0.05)",
                                },
                            )
                        ],
                        width=12,
                        md=3,
                    ),
                ],
                className="mb-4",
            ),
            # Gráficos (migrados de Streamlit)
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H5(
                                                [
                                                    html.I(
                                                        className="bi bi-graph-up me-2"
                                                    ),
                                                    "Session Trends",
                                                ],
                                                className="card-title",
                                                style={
                                                    "color": "rgba(36, 222, 132, 1)"
                                                },
                                            ),
                                            dcc.Graph(id="session-trends-chart"),
                                        ]
                                    )
                                ],
                                style={
                                    "background-color": "#333333",
                                    "border-radius": "10px",
                                    "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
                                },
                            )
                        ],
                        width=12,
                    )
                ]
            ),
        ]
    )


# Función principal para mostrar contenido (migrada de ballers.py)
def show_ballers_content_dash():
    """Función principal para mostrar el contenido de la sección Ballers - MIGRADA DE STREAMLIT."""

    return html.Div(
        [
            # Contenido según el tipo de usuario (migrada la lógica de Streamlit)
            html.Div(id="ballers-user-content"),
            # Store para manejar estados
            dcc.Store(id="selected-player-id", data=None),
            dcc.Store(
                id="user-type-store", data="player"
            ),  # Se actualizará dinámicamente
            dcc.Store(
                id="status-filters", data=["scheduled", "completed", "canceled"]
            ),  # Filtros iniciales activos
        ]
    )


# Callbacks movidos a callbacks/ballers_callbacks.py para mantener separación de responsabilidades


def create_test_results_content_dash():
    """Crea el contenido de Test Results - migrado de lines 188-245 en ballers.py"""
    # Obtener lista de métricas del controller usando la misma lógica que Streamlit
    from controllers.player_controller import PlayerController

    with PlayerController() as controller:
        metrics_list = controller.get_test_metrics_list()

    # Crear opciones para dropdown usando métricas reales
    dropdown_options = [{"label": metric, "value": metric} for metric in metrics_list]

    return dbc.Container(
        [
            # Selector de métricas (usando controller como en Streamlit)
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label(
                                "Select metrics for visualization",
                                style={"color": "#FFFFFF", "font-weight": "500"},
                            ),
                            dcc.Dropdown(
                                id="metrics-selector",
                                options=dropdown_options,
                                value=metrics_list[
                                    :3
                                ],  # Primeras 3 métricas por defecto como en Streamlit
                                multi=True,
                                style={
                                    "border-radius": "5px",
                                    "background-color": "#555",
                                    "color": "#000",
                                },
                            ),
                        ],
                        width=12,
                    )
                ],
                className="mb-4",
            ),
            # Gráfico de evolución - directo sobre fondo
            html.Div(
                [
                    html.H5(
                        [
                            html.I(className="bi bi-graph-up me-2"),
                            "Performance Evolution",
                        ],
                        style={
                            "color": "rgba(36, 222, 132, 1)",
                            "margin-bottom": "15px",
                            "font-size": "1rem",
                        },
                    ),
                    dcc.Graph(
                        id="performance-evolution-chart",
                        figure={
                            "data": [],
                            "layout": {
                                "plot_bgcolor": "#333333",
                                "paper_bgcolor": "#333333",
                                "font": {"color": "#FFFFFF"},
                                "title": {
                                    "text": "Select metrics to display performance evolution",
                                    "font": {"color": "#24DE84"},
                                },
                                "xaxis": {
                                    "gridcolor": "#555",
                                    "color": "#FFFFFF",
                                },
                                "yaxis": {
                                    "gridcolor": "#555",
                                    "color": "#FFFFFF",
                                },
                            },
                        },
                        config={
                            "displayModeBar": False,  # Ocultar barra de herramientas
                            "displaylogo": False,  # Ocultar logo de plotly
                        },
                    ),
                ],
                style={"margin-bottom": "30px"},
            ),
            # Historial de tests - directo sobre fondo
            html.Div(
                [
                    html.H5(
                        [
                            html.I(className="bi bi-clock-history me-2"),
                            "Test History",
                        ],
                        style={
                            "color": "rgba(36, 222, 132, 1)",
                            "margin-bottom": "15px",
                            "font-size": "1rem",
                        },
                    ),
                    html.Div(id="test-history-content"),
                ],
                style={"margin-bottom": "30px"},
            ),
        ]
    )


def create_notes_content_dash():
    """Crea el contenido de Notes - migrado de lines 247-270 en ballers.py"""
    return html.Div(
        [
            html.H5(
                [
                    html.I(className="bi bi-person-lines-fill me-2"),
                    "Player Notes",
                ],
                style={
                    "color": "rgba(36, 222, 132, 1)",
                    "margin-bottom": "15px",
                    "font-size": "1rem",
                },
            ),
            html.P(
                "Current notes:",
                style={
                    "color": "#CCCCCC",
                    "margin-bottom": "10px",
                    "font-size": "0.9rem",
                },
            ),
            html.Div(
                id="current-notes-display",
                className="mb-3",
                style={"color": "#FFFFFF", "font-size": "0.9rem"},
            ),
            # Editor de notas con estilo coherente
            dbc.Label(
                "Edit Notes:",
                style={
                    "color": "#FFFFFF",
                    "font-weight": "500",
                    "margin-bottom": "8px",
                    "font-size": "0.9rem",
                },
            ),
            dbc.Textarea(
                id="notes-editor",
                placeholder="Add or edit notes about this player...",
                style={
                    "border-radius": "5px",
                    "background-color": "#333333",
                    "border": "1px solid #666",
                    "color": "#FFFFFF",  # Texto blanco
                    "min-height": "150px",
                    "font-size": "0.9rem",
                    "::placeholder": {"color": "#CCCCCC", "opacity": 1},
                },
                className="mb-3",
            ),
            dbc.Button(
                [html.I(className="bi bi-save me-2"), "Save Notes"],
                id="save-notes-profile-btn",
                className="custom-button",  # Usar la clase CSS para los estilos
                style={"font-size": "0.9rem"},
            ),
        ],
        style={"margin-bottom": "30px"},
    )


# Callback movido a callbacks/player_callbacks.py


def create_calendar_display_dash(player_id=None):
    """Crea el display del calendario usando el controller existente"""
    try:
        # Importar el controller interno para obtener eventos del calendario
        from datetime import datetime, timedelta

        from controllers.session_controller import SessionController

        # Obtener rango de fechas por defecto (última semana hasta próxima semana)
        today = datetime.now().date()
        start_date = today - timedelta(days=7)
        end_date = today + timedelta(days=14)

        with SessionController() as controller:
            # Obtener sesiones para el jugador específico
            sessions = controller.get_sessions_for_display(
                start_date=start_date, end_date=end_date, player_id=player_id
            )

        # Por ahora, mostrar placeholder para FullCalendar
        # TODO: Implementar integración completa de FullCalendar
        return html.Div(
            [
                html.Div(
                    [
                        html.H6(
                            "Calendar View",
                            style={
                                "color": "#24DE84",
                                "text-align": "center",
                                "margin-bottom": "20px",
                            },
                        ),
                        html.P(
                            f"Found {len(sessions) if sessions else 0} sessions",
                            style={"color": "#CCCCCC", "text-align": "center"},
                        ),
                        html.P(
                            "FullCalendar integration - Coming soon",
                            style={
                                "color": "#999999",
                                "text-align": "center",
                                "font-style": "italic",
                            },
                        ),
                    ],
                    style={
                        "min-height": "300px",
                        "background-color": "#2A2A2A",
                        "border-radius": "10px",
                        "display": "flex",
                        "flex-direction": "column",
                        "align-items": "center",
                        "justify-content": "center",
                        "padding": "20px",
                    },
                )
            ]
        )

    except Exception as e:
        return html.Div(
            f"Error loading calendar: {str(e)}",
            style={"color": "#F44336", "text-align": "center", "padding": "20px"},
        )


def create_sessions_table_dash(
    player_id=None, coach_id=None, from_date=None, to_date=None, status_filter=None
):
    """Crea la tabla de sesiones usando el controller existente - soporta player_id y coach_id"""

    print(f"🔍 DEBUG Sessions Table Creation:")
    print(f"  - player_id: {player_id}")
    print(f"  - coach_id: {coach_id}")
    print(f"  - from_date: {from_date}, to_date: {to_date}")
    print(f"  - status_filter: {status_filter}")

    try:
        from datetime import datetime, timedelta

        from controllers.session_controller import SessionController

        # Configurar fechas por defecto si no se proporcionan
        if not from_date:
            from_date = (datetime.now() - timedelta(days=7)).date()
        if not to_date:
            to_date = (datetime.now() + timedelta(days=14)).date()

        with SessionController() as controller:
            # Obtener sesiones filtradas usando el controller existente
            sessions = controller.get_sessions_for_display(
                start_date=from_date,
                end_date=to_date,
                player_id=player_id,
                coach_id=coach_id,  # Añadir soporte para coach_id
                status_filter=status_filter,  # Usar el filtro ya implementado
            )

            print(f"  - sessions found: {len(sessions)} sessions")
            if sessions:
                print(
                    f"  - first session player_id: {sessions[0].player_id if sessions else 'N/A'}"
                )
                print(
                    f"  - all player_ids: {[s.player_id for s in sessions[:3]]}"
                )  # First 3 only

            if not sessions:
                return dbc.Alert(
                    "No sessions found for the selected period.",
                    color="info",
                    style={
                        "background-color": "#2A2A2A",
                        "border": "none",
                        "color": "#CCCCCC",
                    },
                )

            # Formatear sesiones para tabla usando el controller
            table_data = controller.format_sessions_for_table(sessions)

            # Crear encabezados usando estilos existentes
            headers = [
                html.Th("ID"),
                html.Th("Coach"),
                html.Th("Player"),
                html.Th("Date"),
                html.Th("Start Time"),
                html.Th("End Time"),
                html.Th("Status"),
            ]

            # Crear filas usando clases existentes
            rows = []
            for session_data in table_data:
                # Usar clase CSS existente para hover
                row = html.Tr(
                    [
                        html.Td(session_data.get("ID", "")),
                        html.Td(session_data.get("Coach", "")),
                        html.Td(session_data.get("Player", "")),
                        html.Td(session_data.get("Date", "")),
                        html.Td(session_data.get("Start Time", "")),
                        html.Td(session_data.get("End Time", "")),
                        html.Td(
                            [
                                html.Span(
                                    session_data.get("Status", "").title(),
                                    className=f"status-{session_data.get('Status', 'scheduled')}",
                                )
                            ]
                        ),
                    ],
                    className="table-row-hover",  # Usar clase CSS existente
                )
                rows.append(row)

            # Crear tabla usando estilos mínimos
            table = dbc.Table(
                [html.Thead(html.Tr(headers)), html.Tbody(rows)],
                striped=True,
                bordered=True,
                hover=True,
                responsive=True,
                className="table-dark",  # Usar clase CSS en lugar de prop dark
            )

            return table

    except Exception as e:
        return dbc.Alert(
            f"Error loading sessions: {str(e)}",
            color="danger",
            style={"background-color": "#2A2A2A", "border": "none", "color": "#F44336"},
        )


def create_sessions_calendar_dash(
    from_date=None, to_date=None, status_filter=None, player_id=None
):
    """
    Crea el calendario de sesiones para Dash.
    Reutiliza controllers existentes para máxima separación de responsabilidades.
    """
    try:
        import datetime as dt

        from controllers.internal_calendar import show_calendar_dash
        from controllers.session_controller import SessionController

        # Valores por defecto para fechas (misma lógica que Streamlit)
        if not from_date:
            from_date = (dt.datetime.now().date() - dt.timedelta(days=7)).isoformat()
        if not to_date:
            to_date = (dt.datetime.now().date() + dt.timedelta(days=7)).isoformat()

        # Convertir strings ISO a objetos date si es necesario
        if isinstance(from_date, str):
            from_date = dt.datetime.fromisoformat(from_date).date()
        if isinstance(to_date, str):
            to_date = dt.datetime.fromisoformat(to_date).date()

        # Status filter por defecto (todos los estados como en Streamlit)
        if status_filter is None:
            status_filter = ["scheduled", "completed", "canceled"]

        # Usar SessionController existente (misma lógica que Streamlit)
        with SessionController() as controller:
            sessions = controller.get_sessions_for_display(
                start_date=from_date,
                end_date=to_date,
                player_id=player_id,
                status_filter=status_filter,
            )

        # Usar función del controller para generar el calendario
        return show_calendar_dash(sessions, editable=False, key="dash-calendar")

    except Exception as e:
        return dbc.Alert(
            f"Error loading calendar: {str(e)}",
            color="danger",
            style={"background-color": "#2A2A2A", "border": "none", "color": "#F44336"},
        )


if __name__ == "__main__":
    # Para testing
    pass

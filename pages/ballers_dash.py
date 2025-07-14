# pages/ballers_dash.py - Migración visual de ballers.py a Dash
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

from controllers.player_controller import get_player_profile_data, get_players_for_list


# Funciones simples para reemplazar cloud_utils removido
def is_streamlit_cloud():
    return False


def show_cloud_feature_limitation(feature_name):
    return f"Feature {feature_name} not available in local mode"


def show_cloud_mode_info():
    return "Running in local mode"


def create_player_profile_dash(player_id=None):
    """Crea el perfil de un jugador para Dash - migrado exactamente de Streamlit"""

    try:
        # Obtener datos usando controller (lógica mantenida de Streamlit)
        user_id = None  # Para coaches/admin no se usa user_id
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
            # Filtros de fecha y estado (migrado de lines 95-125)
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H5(
                                [
                                    html.I(className="bi bi-calendar-week me-2"),
                                    "Sessions Calendar",
                                ],
                                style={"color": "rgba(36, 222, 132, 1)"},
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
                                                },
                                            ),
                                            dbc.Input(
                                                id="filter-from-date",
                                                type="date",
                                                className="dash-input",
                                                style={
                                                    "border-radius": "5px",
                                                    "background-color": "#555",
                                                    "border": "1px solid #666",
                                                    "color": "#FAFAFA",
                                                    "max-width": "180px",
                                                },
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
                                                },
                                            ),
                                            dbc.Input(
                                                id="filter-to-date",
                                                type="date",
                                                className="dash-input",
                                                style={
                                                    "border-radius": "5px",
                                                    "background-color": "#555",
                                                    "border": "1px solid #666",
                                                    "color": "#FAFAFA",
                                                    "max-width": "180px",
                                                },
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
                                                                },
                                                            ),
                                                        ],
                                                        style={
                                                            "text-align": "left"
                                                        },  # Alinear label a la izquierda
                                                    ),
                                                    html.Div(
                                                        [
                                                            dbc.Badge(
                                                                "Scheduled",
                                                                id="status-scheduled",
                                                                className="status-scheduled",
                                                                style={
                                                                    "cursor": "pointer",
                                                                    "padding": "8px 12px",
                                                                    "font-size": "14px",
                                                                    "margin-right": "15px",
                                                                },
                                                            ),
                                                            dbc.Badge(
                                                                "Completed",
                                                                id="status-completed",
                                                                className="status-completed",
                                                                style={
                                                                    "cursor": "pointer",
                                                                    "padding": "8px 12px",
                                                                    "font-size": "14px",
                                                                    "margin-right": "15px",
                                                                },
                                                            ),
                                                            dbc.Badge(
                                                                "Canceled",
                                                                id="status-canceled",
                                                                className="status-canceled",
                                                                style={
                                                                    "cursor": "pointer",
                                                                    "padding": "8px 12px",
                                                                    "font-size": "14px",
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
                            # Calendario
                            html.Div(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardBody(
                                                [html.Div(id="calendar-display")]
                                            )
                                        ],
                                        style={
                                            "background-color": "#333333",
                                            "border": "none",
                                            "border-radius": "10px",
                                            "margin-bottom": "20px",
                                        },
                                    )
                                ]
                            ),
                            # Lista de sesiones
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
                                        },
                                    ),
                                    dbc.Card(
                                        [dbc.CardBody([html.Div(id="sessions-table")])],
                                        style={
                                            "background-color": "#333333",
                                            "border": "none",
                                            "border-radius": "10px",
                                        },
                                    ),
                                ]
                            ),
                        ]
                    )
                ],
                className="mb-4",
                style={
                    "background-color": "#333333",
                    "border-radius": "10px",
                    "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
                },
            ),
            # Tabs de Test Results y Notes (migrado de lines 188-270)
            dbc.Tabs(
                [
                    dbc.Tab(
                        label="Test Results",
                        tab_id="test-results",
                        active_label_style={"color": "rgba(36, 222, 132, 1)"},
                    ),
                    dbc.Tab(
                        label="Notes",
                        tab_id="notes",
                        active_label_style={"color": "rgba(36, 222, 132, 1)"},
                    ),
                ],
                id="profile-tabs",
                active_tab="test-results",
            ),
            # Contenido de las tabs
            html.Div(id="profile-tab-content", className="mt-4"),
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
            dcc.Store(id="status-filters", data=[]),  # Para filtros de estado activos
        ]
    )


# Función para registrar callbacks específicos de ballers
def register_ballers_callbacks(app):
    """Registra los callbacks específicos de la página Ballers."""

    # Callback para filtrado de jugadores
    @app.callback(
        Output("players-cards-container", "children"),
        [Input("search-player-input", "value")],
        prevent_initial_call=True,
    )
    def filter_players_list(search_term):
        """Filtra la lista de jugadores según el término de búsqueda - MIGRADO DE STREAMLIT."""

        # Obtener datos con filtro (como en la función original)
        players_data = get_players_for_list(search_term=search_term)

        if not players_data:
            if search_term:
                return [
                    dbc.Col(
                        [
                            dbc.Alert(
                                f"No players found matching '{search_term}'.",
                                color="info",
                            )
                        ],
                        width=12,
                    )
                ]
            else:
                return [
                    dbc.Col(
                        [dbc.Alert("No registered players.", color="info")], width=12
                    )
                ]

        # Recrear tarjetas con datos filtrados usando la función reutilizable
        player_cards = []
        for i, player_data in enumerate(players_data):
            card = create_player_card(player_data)
            player_cards.append(dbc.Col([card], width=12, md=6, lg=4))

        return player_cards

    # Callback para actualizar calendario según filtros de fecha
    @app.callback(
        Output("calendar-display", "children"),
        [Input("filter-from-date", "value"), Input("filter-to-date", "value")],
        [State("selected-player-id", "data")],
        prevent_initial_call=True,
    )
    def update_calendar_display(from_date, to_date, selected_player_id):
        """Actualiza el display del calendario según los filtros de fecha"""
        try:
            return create_calendar_display_dash(player_id=selected_player_id)
        except Exception as e:
            return html.Div(
                f"Error updating calendar: {str(e)}",
                style={"color": "#F44336", "padding": "20px"},
            )

    # Callback para manejar el estado de filtros de status
    @app.callback(
        [
            Output("status-filters", "data"),
            Output("status-scheduled", "color"),
            Output("status-completed", "color"),
            Output("status-canceled", "color"),
        ],
        [
            Input("status-scheduled", "n_clicks"),
            Input("status-completed", "n_clicks"),
            Input("status-canceled", "n_clicks"),
        ],
        [State("status-filters", "data")],
        prevent_initial_call=True,
    )
    def toggle_status_filters(
        scheduled_clicks, completed_clicks, canceled_clicks, current_filters
    ):
        """Maneja el toggle de los filtros de estado"""
        from dash import callback_context

        if not callback_context.triggered:
            return (
                current_filters or ["scheduled", "completed", "canceled"],
                "secondary",
                "secondary",
                "secondary",
            )

        # Determinar qué badge se clickeó
        clicked_id = callback_context.triggered[0]["prop_id"].split(".")[0]
        status_map = {
            "status-scheduled": "scheduled",
            "status-completed": "completed",
            "status-canceled": "canceled",
        }

        clicked_status = status_map.get(clicked_id)
        if not clicked_status:
            return (
                current_filters or ["scheduled", "completed", "canceled"],
                "secondary",
                "secondary",
                "secondary",
            )

        # Inicializar filtros si está vacío
        filters = (
            current_filters.copy()
            if current_filters
            else ["scheduled", "completed", "canceled"]
        )

        # Toggle del filtro clickeado
        if clicked_status in filters:
            filters.remove(clicked_status)
        else:
            filters.append(clicked_status)

        # Si no hay filtros, mostrar todos
        if not filters:
            filters = ["scheduled", "completed", "canceled"]

        # Determinar colores de badges
        scheduled_color = "primary" if "scheduled" in filters else "secondary"
        completed_color = "success" if "completed" in filters else "secondary"
        canceled_color = "danger" if "canceled" in filters else "secondary"

        return filters, scheduled_color, completed_color, canceled_color

    # Callback para actualizar tabla de sesiones según filtros
    @app.callback(
        Output("sessions-table", "children"),
        [
            Input("filter-from-date", "value"),
            Input("filter-to-date", "value"),
            Input("status-filters", "data"),
        ],
        [State("selected-player-id", "data")],
        prevent_initial_call=True,
    )
    def update_sessions_table(from_date, to_date, status_filters, selected_player_id):
        """Actualiza la tabla de sesiones según los filtros"""
        try:
            # Convertir strings de fecha a objetos date si están disponibles
            from_date_obj = None
            to_date_obj = None

            if from_date:
                from datetime import datetime

                from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()

            if to_date:
                from datetime import datetime

                to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            # Usar los filtros del estado o todos por defecto
            status_filter = (
                status_filters
                if status_filters
                else ["scheduled", "completed", "canceled"]
            )

            return create_sessions_table_dash(
                player_id=selected_player_id,
                from_date=from_date_obj,
                to_date=to_date_obj,
                status_filter=status_filter,
            )
        except Exception as e:
            return dbc.Alert(
                f"Error updating sessions table: {str(e)}",
                color="danger",
                style={
                    "background-color": "#2A2A2A",
                    "border": "none",
                    "color": "#F44336",
                },
            )


# Callbacks movidos a callbacks/player_callbacks.py


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
            # Gráfico de evolución (migrado del original)
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H5(
                                [
                                    html.I(className="bi bi-graph-up me-2"),
                                    "Performance Evolution",
                                ],
                                style={"color": "rgba(36, 222, 132, 1)"},
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
                        ]
                    )
                ],
                className="mb-4",
                style={
                    "background-color": "#333333",
                    "border-radius": "10px",
                    "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
                },
            ),
            # Historial de tests (migrado del original)
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H5(
                                [
                                    html.I(className="bi bi-clock-history me-2"),
                                    "Test History",
                                ],
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            html.Div(id="test-history-content"),
                        ]
                    )
                ],
                style={
                    "background-color": "#333333",
                    "border-radius": "10px",
                    "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
                },
            ),
        ]
    )


def create_notes_content_dash():
    """Crea el contenido de Notes - migrado de lines 247-270 en ballers.py"""
    return dbc.Container(
        [
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H5(
                                [
                                    html.I(className="bi bi-person-lines-fill me-2"),
                                    "Player Notes",
                                ],
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            html.P(
                                "Current notes:",
                                style={"color": "#CCCCCC", "margin-bottom": "10px"},
                            ),
                            html.Div(
                                id="current-notes-display",
                                className="mb-3",
                                style={"color": "#FFFFFF"},
                            ),
                            # Editor de notas con estilo coherente
                            dbc.Label(
                                "Edit Notes:",
                                style={
                                    "color": "#FFFFFF",
                                    "font-weight": "500",
                                    "margin-bottom": "8px",
                                },
                            ),
                            dbc.Textarea(
                                id="notes-editor",
                                placeholder="Add or edit notes about this player...",
                                style={
                                    "border-radius": "5px",
                                    "background-color": "#555",
                                    "border": "1px solid #666",
                                    "color": "#FFFFFF",  # Texto blanco
                                    "min-height": "150px",
                                    "::placeholder": {"color": "#CCCCCC", "opacity": 1},
                                },
                                className="mb-3",
                            ),
                            dbc.Button(
                                [html.I(className="bi bi-save me-2"), "Save Notes"],
                                id="save-notes-profile-btn",
                                className="custom-button",  # Usar la clase CSS para los estilos
                            ),
                        ]
                    )
                ],
                style={
                    "background-color": "#333333",
                    "border-radius": "10px",
                    "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
                },
            )
        ]
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
    player_id=None, from_date=None, to_date=None, status_filter=None
):
    """Crea la tabla de sesiones usando el controller existente"""
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
                status_filter=status_filter,  # Usar el filtro ya implementado
            )

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


if __name__ == "__main__":
    # Para testing
    pass

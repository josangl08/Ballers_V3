# pages/ballers_dash.py - Migración visual de ballers.py a Dash
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html

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
        test_results = profile_data.get("test_results", [])

    except Exception as e:
        return dbc.Alert(f"Error loading player profile: {str(e)}", color="danger")

    # Layout completo del perfil migrado exactamente de Streamlit (lines 35-285)
    return dbc.Container(
        [
            # Cabecera con foto, info y export (migrada de lines 35-70)
            dbc.Row(
                [
                    # Columna 1: Foto del perfil (lines 35-45)
                    dbc.Col(
                        [
                            html.Img(
                                src=user.profile_photo
                                or "/assets/profile_photos/default_profile.png",
                                style={
                                    "width": "150px",
                                    "height": "150px",
                                    "object-fit": "cover",
                                    "border-radius": "50%",
                                    "border": "3px solid rgba(36, 222, 132, 1)",
                                },
                                className="mx-auto d-block",
                            )
                        ],
                        width=3,
                    ),
                    # Columna 2: Información básica (lines 45-65)
                    dbc.Col(
                        [
                            html.H2(
                                f"👤 {user.name}",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            html.H5(f"@{user.username}", className="text-muted"),
                            html.P(f"📧 {user.email}"),
                            html.P(f"📞 {user.phone or 'No phone'}"),
                            html.P(f"🎂 Age: {stats.get('age', 'N/A')}"),
                            html.P(f"💼 Service: {player.service or 'No service'}"),
                            html.P(f"🎯 Enrolled Sessions: {player.enrolment}"),
                        ],
                        width=6,
                    ),
                    # Columna 3: Botones de export (lines 65-70)
                    dbc.Col(
                        [
                            dbc.Button(
                                "📋 Export Profile PDF",
                                id="export-profile-btn",
                                color="primary",
                                className="w-100 mb-2",
                                style={
                                    "border-radius": "20px",
                                    "background-color": "#333333",
                                    "color": "rgba(36, 222, 132, 1)",
                                    "border": "none",
                                },
                            ),
                            dbc.Button(
                                "🖨️ Print Profile",
                                id="print-profile-btn",
                                color="secondary",
                                className="w-100",
                                style={
                                    "border-radius": "20px",
                                    "background-color": "#666666",
                                    "color": "white",
                                    "border": "none",
                                },
                            ),
                        ],
                        width=3,
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
                                                "✅",
                                                className="text-center",
                                                style={
                                                    "color": "rgba(36, 222, 132, 1)"
                                                },
                                            ),
                                            html.H2(
                                                str(stats.get("completed", 0)),
                                                className="text-center",
                                            ),
                                            html.P(
                                                "Completed",
                                                className="text-center text-muted",
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
                                                "📅",
                                                className="text-center",
                                                style={
                                                    "color": "rgba(36, 222, 132, 1)"
                                                },
                                            ),
                                            html.H2(
                                                str(stats.get("scheduled", 0)),
                                                className="text-center",
                                            ),
                                            html.P(
                                                "Scheduled",
                                                className="text-center text-muted",
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
                                                "🔄",
                                                className="text-center",
                                                style={
                                                    "color": "rgba(36, 222, 132, 1)"
                                                },
                                            ),
                                            html.H2(
                                                str(stats.get("remaining", 0)),
                                                className="text-center",
                                            ),
                                            html.P(
                                                "Remaining",
                                                className="text-center text-muted",
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
                                                "🔥",
                                                className="text-center",
                                                style={
                                                    "color": "rgba(36, 222, 132, 1)"
                                                },
                                            ),
                                            html.H2("Next", className="text-center"),
                                            html.P(
                                                stats.get(
                                                    "next_session", "No sessions"
                                                ),
                                                className="text-center text-muted",
                                                style={"font-size": "12px"},
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
                                "📅 Sessions Calendar",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("From Date"),
                                            dbc.Input(
                                                id="filter-from-date",
                                                type="date",
                                                style={"border-radius": "5px"},
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("To Date"),
                                            dbc.Input(
                                                id="filter-to-date",
                                                type="date",
                                                style={"border-radius": "5px"},
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Status Filter"),
                                            dcc.Dropdown(
                                                id="filter-status",
                                                options=[
                                                    {"label": "All", "value": "all"},
                                                    {
                                                        "label": "✅ Completed",
                                                        "value": "completed",
                                                    },
                                                    {
                                                        "label": "📅 Scheduled",
                                                        "value": "scheduled",
                                                    },
                                                    {
                                                        "label": "❌ Canceled",
                                                        "value": "canceled",
                                                    },
                                                ],
                                                value="all",
                                                style={"border-radius": "5px"},
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Br(),
                                            dbc.Button(
                                                "🔍 Filter",
                                                id="apply-filter-btn",
                                                color="primary",
                                                className="w-100",
                                                style={"border-radius": "20px"},
                                            ),
                                        ],
                                        width=3,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Contenido del calendario y sesiones
                            html.Div(id="sessions-calendar-content"),
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
                        label="📊 Test Results",
                        tab_id="test-results",
                        active_label_style={"color": "rgba(36, 222, 132, 1)"},
                    ),
                    dbc.Tab(
                        label="📝 Notes",
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


def create_ballers_dashboard_dash():
    """Crea el dashboard principal de Ballers para Dash - migrado de Streamlit"""

    return dbc.Container(
        [
            # Cabecera principal
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H1(
                                "🏀 Ballers Dashboard",
                                style={
                                    "color": "rgba(36, 222, 132, 1)",
                                    "text-align": "center",
                                },
                            ),
                            html.P(
                                "Welcome to the Ballers management system",
                                className="text-center text-muted",
                            ),
                        ],
                        width=12,
                    )
                ],
                className="mb-4",
            ),
            # Navegación por pestañas (migrado de Streamlit)
            dbc.Tabs(
                [
                    dbc.Tab(
                        label="📊 Overview",
                        tab_id="overview",
                        active_label_style={"color": "rgba(36, 222, 132, 1)"},
                    ),
                    dbc.Tab(
                        label="👥 Players",
                        tab_id="players",
                        active_label_style={"color": "rgba(36, 222, 132, 1)"},
                    ),
                    dbc.Tab(
                        label="📅 Calendar",
                        tab_id="calendar",
                        active_label_style={"color": "rgba(36, 222, 132, 1)"},
                    ),
                    dbc.Tab(
                        label="📈 Statistics",
                        tab_id="statistics",
                        active_label_style={"color": "rgba(36, 222, 132, 1)"},
                    ),
                ],
                id="ballers-tabs",
                active_tab="overview",
            ),
            # Contenido de las pestañas
            html.Div(id="ballers-tab-content", className="mt-4"),
        ]
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
                                                "📅",
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
                                                "🔄",
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
                                                "📊 Session Trends",
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
            # Título de la sección (migrado de Streamlit)
            html.H3(
                "Profiles",
                style={"color": "rgba(36, 222, 132, 1)", "text-align": "center"},
                className="section-title mb-4",
            ),
            # Contenido según el tipo de usuario (migrada la lógica de Streamlit)
            html.Div(id="ballers-user-content"),
            # Store para manejar estados
            dcc.Store(id="selected-player-id", data=None),
            dcc.Store(
                id="user-type-store", data="player"
            ),  # Se actualizará dinámicamente
        ]
    )


# Función para registrar callbacks específicos de ballers
def register_ballers_callbacks(app):
    """Registra los callbacks específicos de la página Ballers."""

    # Callbacks removidos - ya existen en player_callbacks.py

    # Callback removido - ya existe en player_callbacks.py

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


# Callbacks movidos a callbacks/player_callbacks.py


def create_test_results_content_dash():
    """Crea el contenido de Test Results - migrado de lines 188-245 en ballers.py"""
    return dbc.Container(
        [
            # Selector de métricas (migrado del original)
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Select Metrics to Display"),
                            dcc.Dropdown(
                                id="metrics-selector",
                                options=[
                                    {"label": "Ball Control", "value": "ball_control"},
                                    {"label": "Shooting", "value": "shooting"},
                                    {"label": "Passing", "value": "passing"},
                                    {"label": "Dribbling", "value": "dribbling"},
                                    {"label": "Speed", "value": "speed"},
                                    {"label": "Stamina", "value": "stamina"},
                                ],
                                value=["ball_control", "shooting"],
                                multi=True,
                                style={"border-radius": "5px"},
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
                                "📈 Performance Evolution",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dcc.Graph(id="performance-evolution-chart"),
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
                                "📊 Test History",
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
                                "📝 Player Notes",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            html.P("Current notes:", className="text-muted"),
                            html.Div(id="current-notes-display", className="mb-3"),
                            # Editor de notas
                            dbc.Label("Edit Notes:"),
                            dbc.Textarea(
                                id="notes-editor",
                                placeholder="Add or edit notes about this player...",
                                style={
                                    "border-radius": "5px",
                                    "border": "1px solid #e0e0e0",
                                    "min-height": "150px",
                                },
                                className="mb-3",
                            ),
                            dbc.Button(
                                "💾 Save Notes",
                                id="save-notes-profile-btn",
                                color="success",
                                style={"border-radius": "20px"},
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


def create_sessions_calendar_dash(from_date=None, to_date=None, status="all"):
    """Crea el calendario de sesiones - migrado del original"""
    return dbc.Container(
        [
            # Tabla de sesiones estilizada
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H6(
                                "📅 Sessions List",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            # Aquí iría la tabla de sesiones con datos reales
                            dbc.Alert(
                                "Sessions calendar integration - To be implemented with real data",
                                color="info",
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


if __name__ == "__main__":
    # Para testing
    pass

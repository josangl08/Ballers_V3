# pages/ballers_dash.py - Migración visual de ballers.py a Dash
from __future__ import annotations

import datetime

import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html  # noqa: F401

from controllers.player_controller import get_player_profile_data, get_players_for_list
from controllers.thai_league_controller import ThaiLeagueController


# Funciones simples para reemplazar cloud_utils removido
def is_streamlit_cloud():
    return False


def show_cloud_feature_limitation(feature_name):
    return f"Feature {feature_name} not available in local mode"


def show_cloud_mode_info():
    return "Running in local mode"


def create_evolution_chart(player_stats):
    """
    Crea gráfico de evolución temporal de estadísticas principales.

    Args:
        player_stats: Lista de diccionarios con estadísticas por temporada

    Returns:
        Componente dcc.Graph con el gráfico de evolución
    """
    if not player_stats:
        return dbc.Alert("No statistical data available", color="warning")

    # Extraer datos para el gráfico
    seasons = [stat["season"] for stat in player_stats]
    goals = [stat["goals"] or 0 for stat in player_stats]
    assists = [stat["assists"] or 0 for stat in player_stats]
    matches = [stat["matches_played"] or 0 for stat in player_stats]

    # Crear gráfico con múltiples líneas
    fig = go.Figure()

    # Línea de goles
    fig.add_trace(
        go.Scatter(
            x=seasons,
            y=goals,
            mode="lines+markers",
            name="Goals",
            line=dict(color="#24DE84", width=3),
            marker=dict(size=8),
        )
    )

    # Línea de asistencias
    fig.add_trace(
        go.Scatter(
            x=seasons,
            y=assists,
            mode="lines+markers",
            name="Assists",
            line=dict(color="#FFA726", width=3),
            marker=dict(size=8),
        )
    )

    # Línea de partidos (escala reducida para mejor visualización)
    fig.add_trace(
        go.Scatter(
            x=seasons,
            y=[m / 5 for m in matches],  # Dividir por 5 para escalar
            mode="lines+markers",
            name="Matches (/5)",
            line=dict(color="#42A5F5", width=2, dash="dash"),
            marker=dict(size=6),
        )
    )

    # Personalizar layout
    fig.update_layout(
        title={
            "text": "Performance Evolution by Season",
            "x": 0.5,
            "font": {"color": "#24DE84", "size": 16},
        },
        xaxis_title="Season",
        yaxis_title="Statistical Value",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#FFFFFF"},
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.1)", linecolor="rgba(255,255,255,0.2)"
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.1)", linecolor="rgba(255,255,255,0.2)"
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0.5)", bordercolor="rgba(36,222,132,0.3)", borderwidth=1
        ),
        height=400,
    )

    return dcc.Graph(
        figure=fig, style={"height": "400px"}, config={"displayModeBar": False}
    )


def create_radar_chart(player_stats):
    """
    Crea radar chart de habilidades del jugador basado en estadísticas recientes.

    Args:
        player_stats: Lista de diccionarios con estadísticas por temporada

    Returns:
        Componente dcc.Graph con el radar chart
    """
    if not player_stats:
        return dbc.Alert("No statistical data available", color="warning")

    # Usar la temporada más reciente
    latest_stats = player_stats[-1] if player_stats else {}

    # Definir categorías y normalizar valores (0-100)
    categories = ["Attack", "Passing", "Defense", "Shooting", "Consistency"]

    # Calcular métricas normalizadas
    goals = latest_stats.get("goals", 0) or 0
    assists = latest_stats.get("assists", 0) or 0
    shot_acc = latest_stats.get("shot_accuracy", 0) or 0
    pass_acc = latest_stats.get("pass_accuracy", 0) or 0
    def_actions = latest_stats.get("defensive_actions", 0) or 0
    matches = latest_stats.get("matches_played", 0) or 0

    # Normalizar valores a escala 0-100
    attack_score = min(
        100, (goals + assists) * 10
    )  # Máximo razonable: 10 goles+asistencias
    passing_score = min(100, pass_acc) if pass_acc > 0 else 50
    defense_score = min(
        100, def_actions * 2
    )  # Máximo razonable: 50 acciones defensivas
    shooting_score = min(100, shot_acc) if shot_acc > 0 else 50
    consistency_score = min(100, matches * 3)  # Máximo: ~33 partidos

    values = [
        attack_score,
        passing_score,
        defense_score,
        shooting_score,
        consistency_score,
    ]

    # Crear radar chart
    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill="toself",
            fillcolor="rgba(36, 222, 132, 0.3)",
            line=dict(color="#24DE84", width=2),
            marker=dict(size=8, color="#24DE84"),
            name="Player Stats",
        )
    )

    # Personalizar layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor="rgba(255,255,255,0.2)",
                linecolor="rgba(255,255,255,0.3)",
                tickcolor="rgba(255,255,255,0.5)",
                tickfont=dict(color="#FFFFFF", size=10),
            ),
            angularaxis=dict(
                gridcolor="rgba(255,255,255,0.2)",
                linecolor="rgba(255,255,255,0.3)",
                tickcolor="rgba(255,255,255,0.5)",
                tickfont=dict(color="#FFFFFF", size=12),
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=False,
        title={
            "text": f'Player Skills Profile - {latest_stats.get("season", "Current")}',
            "x": 0.5,
            "font": {"color": "#24DE84", "size": 16},
        },
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=400,
    )

    return dcc.Graph(
        figure=fig, style={"height": "400px"}, config={"displayModeBar": False}
    )


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
            # Tabs condicionales para jugadores profesionales (Info/Stats) - REUBICADAS
            html.Div(id="professional-tabs-container"),
            # Contenido de las tabs profesionales
            html.Div(id="professional-tab-content", style={"margin-bottom": "30px"}),
            # Contenido para jogadores amateur (sin tabs profesionales)
            html.Div(
                id="amateur-content",
                children=[
                    # Filtros de fecha y estado - directo sobre fondo
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
                                width=3,
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
                                width=3,
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
                                                style={"text-align": "left"},
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
                                                        style={"cursor": "pointer"},
                                                    ),
                                                ],
                                                style={"text-align": "left"},
                                            ),
                                        ],
                                        style={
                                            "margin-left": "auto",
                                            "width": "fit-content",
                                        },
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
            # Tabs de Test Results y Notes - solo para jugadores amateur
            html.Div(
                id="amateur-test-notes-tabs",
                children=[
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
                        id="profile-alert",
                        is_open=False,
                        dismissable=True,
                        className="mb-3",
                    ),
                ],
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


def create_professional_tabs(player, user):
    """
    Crea tabs condicionales Info/Stats para jugadores profesionales.

    Args:
        player: Objeto Player con información del jugador
        user: Objeto User con información del usuario

    Returns:
        Componente Dash con tabs condicionales o div vacío
    """
    # Verificar si es jugador profesional
    if not hasattr(player, "is_professional") or not player.is_professional:
        return html.Div()  # Sin tabs para jugadores amateur

    # Crear tabs para jugadores profesionales
    tabs = dbc.Tabs(
        [
            dbc.Tab(
                label="Info",
                tab_id="professional-info",
                active_label_style={
                    "color": "rgba(36, 222, 132, 1)",
                    "font-size": "0.9rem",
                },
                label_style={"font-size": "0.9rem"},
            ),
            dbc.Tab(
                label="Stats",
                tab_id="professional-stats",
                active_label_style={
                    "color": "rgba(36, 222, 132, 1)",
                    "font-size": "0.9rem",
                },
                label_style={"font-size": "0.9rem"},
            ),
        ],
        id="professional-tabs",
        active_tab="professional-info",
        style={"margin-bottom": "20px", "margin-top": "20px"},
    )

    return html.Div(
        [
            html.H6(
                [
                    html.I(className="bi bi-trophy me-2"),
                    "Professional Player",
                ],
                style={
                    "color": "rgba(36, 222, 132, 1)",
                    "margin-bottom": "15px",
                    "font-size": "1rem",
                },
            ),
            tabs,
        ]
    )


def create_professional_info_content(player, user):
    """
    Crea contenido de la tab Info para jugadores profesionales.

    Returns minimal informative content to avoid DOM element ID duplication.
    The actual functional elements (filters, calendar, sessions table) are already
    visible through the amateur-content container and will be controlled by
    existing callbacks in ballers_callbacks.py.

    Args:
        player: Objeto Player
        user: Objeto User

    Returns:
        Minimal informative HTML content without duplicated form elements
    """
    return html.Div(
        [
            dbc.Alert(
                [
                    html.I(className="bi bi-info-circle me-2"),
                    f"Professional player view for {user.name}. ",
                    "Use the calendar and session controls below to manage training sessions and view performance data.",
                ],
                color="info",
                style={
                    "background-color": "rgba(36, 222, 132, 0.1)",
                    "border": "1px solid rgba(36, 222, 132, 0.3)",
                    "color": "#FFFFFF",
                    "margin-bottom": "20px",
                },
            )
        ]
    )


def create_professional_stats_content(player, user):
    """
    Crea contenido de la tab Stats para jugadores profesionales.

    Args:
        player: Objeto Player
        user: Objeto User

    Returns:
        Contenido HTML con estadísticas profesionales
    """
    try:
        # Obtener estadísticas usando ThaiLeagueController
        controller = ThaiLeagueController()
        player_stats = controller.get_player_stats(player.player_id)

        # Si no hay estadísticas, mostrar mensaje informativo
        if not player_stats:
            return dbc.Container(
                [
                    dbc.Alert(
                        [
                            html.I(className="bi bi-info-circle me-2"),
                            f"No professional statistics found for {user.name}.",
                            html.Br(),
                            f"WyscoutID: {player.wyscout_id or 'Not assigned'}",
                            html.Br(),
                            "Statistics will appear here once the player data is synchronized with Thai League database.",
                        ],
                        color="info",
                        className="mb-3",
                    ),
                ],
                fluid=True,
                className="p-0",
            )

        # Calcular estadísticas resumidas de todas las temporadas
        total_goals = sum(stat.get("goals", 0) or 0 for stat in player_stats)
        total_assists = sum(stat.get("assists", 0) or 0 for stat in player_stats)
        total_matches = sum(stat.get("matches_played", 0) or 0 for stat in player_stats)
        latest_season = player_stats[-1] if player_stats else {}
        current_team = latest_season.get("team", "Unknown")

        return dbc.Container(
            [
                # Header con información del jugador
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Alert(
                                    [
                                        html.I(className="bi bi-trophy me-2"),
                                        f"Professional Stats for {user.name}",
                                        html.Br(),
                                        f"Current Team: {current_team} | WyscoutID: {player.wyscout_id}",
                                        html.Br(),
                                        f"Career: {total_goals} goals, {total_assists} assists in {total_matches} matches",
                                    ],
                                    color="success",
                                    className="mb-3",
                                ),
                            ],
                            width=12,
                        ),
                    ]
                ),
                # Gráficos principales
                dbc.Row(
                    [
                        # Gráfico de evolución temporal
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            html.H6(
                                                "Performance Evolution",
                                                className="card-title mb-0",
                                                style={
                                                    "color": "rgba(36, 222, 132, 1)"
                                                },
                                            )
                                        ),
                                        dbc.CardBody(
                                            [create_evolution_chart(player_stats)],
                                            className="p-2",
                                        ),
                                    ],
                                    style={
                                        "background-color": "#2B2B2B",
                                        "border-color": "rgba(36, 222, 132, 0.3)",
                                    },
                                ),
                            ],
                            width=12,
                            lg=8,
                            className="mb-3",
                        ),
                        # Radar chart de habilidades
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            html.H6(
                                                "Skills Profile",
                                                className="card-title mb-0",
                                                style={
                                                    "color": "rgba(36, 222, 132, 1)"
                                                },
                                            )
                                        ),
                                        dbc.CardBody(
                                            [create_radar_chart(player_stats)],
                                            className="p-2",
                                        ),
                                    ],
                                    style={
                                        "background-color": "#2B2B2B",
                                        "border-color": "rgba(36, 222, 132, 0.3)",
                                    },
                                ),
                            ],
                            width=12,
                            lg=4,
                            className="mb-3",
                        ),
                    ]
                ),
                # Cards con estadísticas resumidas por categoría
                dbc.Row(
                    [
                        # Estadísticas ofensivas
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                html.H6(
                                                    "Offensive Stats",
                                                    className="card-title",
                                                    style={
                                                        "color": "rgba(36, 222, 132, 1)"
                                                    },
                                                ),
                                                html.P(
                                                    f"Goals: {total_goals}",
                                                    style={"color": "#FFFFFF"},
                                                ),
                                                html.P(
                                                    f"Assists: {total_assists}",
                                                    style={"color": "#FFFFFF"},
                                                ),
                                                html.P(
                                                    f"G+A per Match: {((total_goals + total_assists) / max(total_matches, 1)):.2f}",
                                                    style={"color": "#FFA726"},
                                                ),
                                            ]
                                        )
                                    ],
                                    style={
                                        "background-color": "#2B2B2B",
                                        "border-color": "rgba(36, 222, 132, 0.3)",
                                    },
                                ),
                            ],
                            width=12,
                            md=4,
                            className="mb-3",
                        ),
                        # Estadísticas de participación
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                html.H6(
                                                    "Participation",
                                                    className="card-title",
                                                    style={
                                                        "color": "rgba(36, 222, 132, 1)"
                                                    },
                                                ),
                                                html.P(
                                                    f"Total Matches: {total_matches}",
                                                    style={"color": "#FFFFFF"},
                                                ),
                                                html.P(
                                                    f"Seasons: {len(player_stats)}",
                                                    style={"color": "#FFFFFF"},
                                                ),
                                                html.P(
                                                    f"Avg per Season: {(total_matches / max(len(player_stats), 1)):.1f}",
                                                    style={"color": "#42A5F5"},
                                                ),
                                            ]
                                        )
                                    ],
                                    style={
                                        "background-color": "#2B2B2B",
                                        "border-color": "rgba(36, 222, 132, 0.3)",
                                    },
                                ),
                            ],
                            width=12,
                            md=4,
                            className="mb-3",
                        ),
                        # Estadísticas actuales
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                html.H6(
                                                    f"Current Season ({latest_season.get('season', 'N/A')})",
                                                    className="card-title",
                                                    style={
                                                        "color": "rgba(36, 222, 132, 1)"
                                                    },
                                                ),
                                                html.P(
                                                    f"Goals: {latest_season.get('goals', 0) or 0}",
                                                    style={"color": "#FFFFFF"},
                                                ),
                                                html.P(
                                                    f"Assists: {latest_season.get('assists', 0) or 0}",
                                                    style={"color": "#FFFFFF"},
                                                ),
                                                html.P(
                                                    f"Matches: {latest_season.get('matches_played', 0) or 0}",
                                                    style={"color": "#E57373"},
                                                ),
                                            ]
                                        )
                                    ],
                                    style={
                                        "background-color": "#2B2B2B",
                                        "border-color": "rgba(36, 222, 132, 0.3)",
                                    },
                                ),
                            ],
                            width=12,
                            md=4,
                            className="mb-3",
                        ),
                    ]
                ),
            ],
            fluid=True,
            className="p-0",
        )

    except Exception as e:
        return dbc.Alert(f"Error loading professional stats: {str(e)}", color="danger")


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

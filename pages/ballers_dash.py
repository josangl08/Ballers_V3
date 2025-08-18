# pages/ballers_dash.py - Migración visual de ballers.py a Dash
from __future__ import annotations

import base64
import datetime
import logging
import os
import re

import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
import requests
from dash import Input, Output, State, dcc, html  # noqa: F401

from common.format_utils import format_name_with_del
from controllers.player_controller import get_player_profile_data, get_players_for_list

# ML Pipeline Imports - Phase 13.3 Dashboard Integration (Migrated to ml_system)
from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer


def get_local_team_logo(team_name, team_logo_url):
    """
    Obtiene la ruta del logo local del equipo o lo descarga si no existe.

    Args:
        team_name: Nombre del equipo
        team_logo_url: URL del logo del equipo

    Returns:
        Ruta local del logo del equipo
    """
    if not team_name or not team_logo_url:
        return "assets/team_logos/default_team.png"

    # Crear nombre de archivo seguro
    safe_name = re.sub(r"[^\w\s-]", "", team_name)
    safe_name = re.sub(r"[-\s]+", "_", safe_name)
    local_path = f"assets/team_logos/{safe_name}.png"

    # Si el archivo ya existe, devolverlo
    if os.path.exists(local_path):
        return local_path

    # Intentar descargar el logo
    try:
        response = requests.get(team_logo_url, timeout=10)
        response.raise_for_status()

        # Crear directorio si no existe
        os.makedirs("assets/team_logos", exist_ok=True)

        # Guardar imagen
        with open(local_path, "wb") as f:
            f.write(response.content)

        print(f"✅ Logo descargado para {team_name}: {local_path}")
        return local_path

    except Exception as e:
        print(f"❌ Error descargando logo para {team_name}: {e}")
        return "assets/team_logos/default_team.png"


def load_logo_as_base64(logo_path):
    """
    Convierte imagen local a base64 para mejor compatibilidad con Plotly.

    Args:
        logo_path: Ruta local del logo

    Returns:
        String base64 o None si hay error
    """
    try:
        with open(logo_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{encoded}"
    except Exception as e:
        print(f"❌ Error converting logo to base64: {e}")
        return None


# from controllers.thai_league_controller import ThaiLeagueController  # REDUNDANTE - usar ml_system directamente
from models.user_model import UserType

# from controllers.etl_controller import ETLController  # REDUNDANTE - usar ml_system directamente
# from ml_system.data_acquisition.extractors import ThaiLeagueExtractor  # Temporal - no usado


# TODO: Import otros componentes ML según se necesiten

# Configurar logger
logger = logging.getLogger(__name__)


# Funciones simples para reemplazar cloud_utils removido
def is_streamlit_cloud():
    return False


def show_cloud_feature_limitation(feature_name):
    return f"Feature {feature_name} not available in local mode"


def show_cloud_mode_info():
    return "Running in local mode"


def create_evolution_chart(player_stats):
    """
    Crea gráfico de evolución temporal avanzado con equipos integrados.

    Args:
        player_stats: Lista de diccionarios con estadísticas por temporada

    Returns:
        Componente dcc.Graph con el gráfico de evolución con equipos
    """
    if not player_stats:
        return dbc.Alert("No statistical data available", color="warning")

    # Extraer datos para el gráfico
    seasons = [stat["season"] for stat in player_stats]
    goals = [stat["goals"] or 0 for stat in player_stats]
    assists = [stat["assists"] or 0 for stat in player_stats]
    matches = [stat["matches_played"] or 0 for stat in player_stats]

    # Nuevas estadísticas para el gráfico integral
    minutes = [stat.get("minutes_played") or 0 for stat in player_stats]
    duels_won_pct = [stat.get("duels_won_pct") or 0 for stat in player_stats]
    pass_accuracy_pct = [stat.get("pass_accuracy_pct") or 0 for stat in player_stats]

    # Normalizar minutes para escala 0-100 (dividir por 30 minutos típicos por partido)
    minutes_normalized = [min(100, (m / 30)) if m > 0 else 0 for m in minutes]
    # Escalar matches para mejor visualización en escala 0-100 (multiplicar por 2.5)
    matches_scaled = [min(100, m * 2.5) for m in matches]

    # Extraer datos de equipos para tooltips y logos
    teams = [stat.get("team", "Unknown Team") for stat in player_stats]
    team_logos = [stat.get("team_logo_url", "") for stat in player_stats]

    # Formatear temporadas para tooltips (20-21 formato)
    formatted_seasons = []
    for season in seasons:
        if season.startswith("20"):
            # Convertir "2020-21" a "20-21"
            formatted_seasons.append(season.replace("20", "", 1))
        else:
            formatted_seasons.append(season)

    # Crear posiciones numéricas para coordenadas X (solución al desplazamiento)
    x_positions = list(range(len(formatted_seasons)))

    # Crear cabeceras de tooltip con formato "20-21 - Equipo"
    tooltip_headers = [
        f"{season} - {team}" for season, team in zip(formatted_seasons, teams)
    ]

    # Calcular métricas normalizadas por 90 minutos
    goals_per_90 = [stat.get("goals_per_90") or 0 for stat in player_stats]
    assists_per_90 = [stat.get("assists_per_90") or 0 for stat in player_stats]

    # Calcular expected goals si está disponible
    expected_goals = [stat.get("expected_goals") or 0 for stat in player_stats]

    # Preparar customdata para tooltips enriquecidos
    tooltip_data = []
    for i, (season, team, goal, assist, match) in enumerate(
        zip(formatted_seasons, teams, goals, assists, matches)
    ):
        tooltip_data.append([season, team, goal, assist, match])

    customdata = np.array(tooltip_data)

    # Crear customdata específico para header del tooltip (temporada - equipo)
    header_customdata = [
        [season, team] for season, team in zip(formatted_seasons, teams)
    ]

    # Crear gráfico con múltiples líneas mejoradas
    fig = go.Figure()

    # Trace invisible para mostrar nombre del equipo (primera línea del tooltip)
    fig.add_trace(
        go.Scatter(
            x=x_positions,  # Usar posiciones numéricas
            y=[0] * len(formatted_seasons),  # En cero para ser invisible
            mode="markers",
            marker=dict(size=0, opacity=0, color="rgba(0,0,0,0)"),
            showlegend=False,
            name="",
            customdata=teams,  # Solo nombres de equipos
            hovertemplate="<b style='text-align:left'>%{customdata}</b><extra></extra>",
        )
    )

    # Línea de goles totales (original)
    fig.add_trace(
        go.Scatter(
            x=x_positions,  # Usar posiciones numéricas
            y=goals,
            mode="lines+markers",
            name="Goals (Total)",
            line=dict(color="#24DE84", width=3),
            marker=dict(size=8),
            customdata=customdata,
            hovertemplate="Goals (Total): %{y}<extra></extra>",
        )
    )

    # Línea de asistencias totales
    fig.add_trace(
        go.Scatter(
            x=x_positions,  # Usar posiciones numéricas
            y=assists,
            mode="lines+markers",
            name="Assists (Total)",
            line=dict(color="#FFA726", width=3),
            marker=dict(size=8),
            customdata=customdata,
            hovertemplate="Assists (Total): %{y}<extra></extra>",
        )
    )

    # Línea de expected goals si está disponible
    if any(xg > 0 for xg in expected_goals):
        fig.add_trace(
            go.Scatter(
                x=x_positions,  # Usar posiciones numéricas
                y=expected_goals,
                mode="lines+markers",
                name="Expected Goals (xG)",
                line=dict(color="#E57373", width=2, dash="dot"),
                marker=dict(size=6),
                customdata=customdata,
                hovertemplate="Expected Goals (xG): %{y:.2f}<extra></extra>",
            )
        )

    # Línea de partidos jugados (escalado x2.5 para rango 0-100)
    fig.add_trace(
        go.Scatter(
            x=x_positions,  # Usar posiciones numéricas
            y=matches_scaled,
            mode="lines+markers",
            name="Matches Played",
            line=dict(color="#42A5F5", width=2, dash="dash"),
            marker=dict(size=6),
            yaxis="y2",
            customdata=[
                [s, t, m, a, ma]
                for s, t, m, a, ma in zip(
                    formatted_seasons, teams, goals, assists, matches
                )
            ],
            hovertemplate="Matches Played: %{customdata[4]}<extra></extra>",  # Mostrar valor real
        )
    )

    # Línea de porcentaje de duelos ganados (escala secundaria)
    fig.add_trace(
        go.Scatter(
            x=x_positions,  # Usar posiciones numéricas
            y=duels_won_pct,
            mode="lines+markers",
            name="Duels Won %",
            line=dict(color="#AB47BC", width=2),
            marker=dict(size=6),
            yaxis="y2",
            customdata=customdata,
            hovertemplate="Duels Won: %{y:.1f}%<extra></extra>",
        )
    )

    # Línea de precisión de pases (escala secundaria)
    fig.add_trace(
        go.Scatter(
            x=x_positions,  # Usar posiciones numéricas
            y=pass_accuracy_pct,
            mode="lines+markers",
            name="Pass Accuracy %",
            line=dict(color="#EC407A", width=2),
            marker=dict(size=6),
            yaxis="y2",
            customdata=customdata,
            hovertemplate="Pass Accuracy: %{y:.1f}%<extra></extra>",
        )
    )

    # Línea de minutos jugados (normalizado /30 para rango 0-100)
    fig.add_trace(
        go.Scatter(
            x=x_positions,  # Usar posiciones numéricas
            y=minutes_normalized,
            mode="lines+markers",
            name="Minutes Played",
            line=dict(color="#26C6DA", width=2),
            marker=dict(size=6),
            yaxis="y2",  # Cambiado a yaxis2
            customdata=[
                [s, t, m, a, mi]
                for s, t, m, a, mi in zip(
                    formatted_seasons, teams, goals, assists, minutes
                )
            ],
            hovertemplate="Minutes Played: %{customdata[4]}<extra></extra>",  # Mostrar valor real
        )
    )

    # Añadir logos de equipos como imágenes de layout (si están disponibles)
    print(f"🔍 Processing {len(team_logos)} team logos for evolution chart")

    for i, (season, team, logo_url) in enumerate(
        zip(formatted_seasons, teams, team_logos)
    ):
        print(f"🏆 Season {season}: Team '{team}', Logo URL: '{logo_url}'")
        try:
            # Obtener logo local (descarga automáticamente si es necesario)
            local_logo_path = get_local_team_logo(team, logo_url)

            # Convertir a base64 para mejor compatibilidad
            base64_logo = load_logo_as_base64(local_logo_path)

            if base64_logo:
                print(f"🔄 Using base64 logo for {team}")
                # Posicionar logo cerca de líneas verticales de temporadas
                fig.add_layout_image(
                    source=base64_logo,
                    x=i,  # Usar índice numérico
                    y=0.95,  # Más cerca del área de plot
                    sizex=0.15,  # 15% del ancho (más grande y visible)
                    sizey=0.15,  # 15% de altura (más grande y visible)
                    sizing="contain",
                    layer="above",
                    xref="x",  # Coordenadas de datos X para alineación con temporadas
                    yref="paper",  # Coordenadas paper Y para posición fija
                    xanchor="center",
                    yanchor="middle",
                )
                print(f"✅ Base64 logo added for {team}")
            else:
                # Usar fallback icon cuando no hay logo disponible
                print(f"⚠️ No logo for {team}, using fallback icon")
                try:
                    # Bootstrap shield outline sin relleno
                    bootstrap_icon_svg = """
                    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="none" stroke="#24DE84" stroke-width="1.5" viewBox="0 0 16 16">
                        <path d="M8 0c-.69 0-1.843.265-2.928.56-1.11.3-2.229.655-2.887.87a1.54 1.54 0 0 0-1.044 1.262c-.596 4.477.787 7.795 2.465 9.99a11.777 11.777 0 0 0 2.517 2.453c.386.273.744.482 1.048.625.28.132.581.24.829.24s.548-.108.829-.24c.304-.143.662-.352 1.048-.625a11.777 11.777 0 0 0 2.517-2.453C13.22 10.343 14.603 7.025 14.007 2.548A1.54 1.54 0 0 0 12.963 1.286c-.658-.215-1.777-.57-2.887-.87C9.006.265 7.69 0 8 0z"/>
                    </svg>
                    """
                    import base64

                    fallback_base64 = f"data:image/svg+xml;base64,{base64.b64encode(bootstrap_icon_svg.encode()).decode()}"

                    fig.add_layout_image(
                        source=fallback_base64,
                        x=i,  # Usar índice numérico
                        y=0.95,  # Más cerca del área de plot
                        sizex=0.12,  # 12% del ancho (más visible)
                        sizey=0.12,  # 12% de altura (más visible)
                        sizing="contain",
                        layer="above",
                        xref="x",  # Coordenadas de datos X para alineación con temporadas
                        yref="paper",
                        xanchor="center",
                        yanchor="middle",
                    )
                    print(f"✅ Bootstrap fallback icon added for {team}")
                except Exception as fallback_error:
                    print(f"❌ Fallback icon failed for {team}: {fallback_error}")

        except Exception as e:
            print(f"❌ Error adding logo for {team}: {e}")
            # El fallback ya se maneja en el flujo principal (else del if base64_logo)

    # Layout mejorado con ejes múltiples
    fig.update_layout(
        yaxis=dict(
            title=dict(text="Goals/Assists/xG", font=dict(color="#FFFFFF", size=12)),
            tickfont=dict(color="#FFFFFF", size=10),
            gridcolor="rgba(255,255,255,0.1)",
            linecolor="rgba(255,255,255,0.2)",
            rangemode="tozero",  # Empezar desde 0
            range=[0, None],  # Base fija en 0, máximo auto
            domain=[0, 0.9],  # Reservar 10% del espacio para ejes derechos
        ),
        yaxis2=dict(
            title=dict(
                text="Normalized Metrics (0-100)", font=dict(color="#42A5F5", size=11)
            ),
            tickfont=dict(color="#42A5F5", size=9),
            overlaying="y",
            side="right",
            range=[0, 100],  # Rango 0-100 para todas las métricas normalizadas
            showgrid=False,  # Sin grid para evitar saturación
            anchor="x",  # Anclado al eje X, posición estándar derecha
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#FFFFFF"},
        legend=dict(
            orientation="h",  # Leyenda horizontal
            x=0.5,  # Centrado horizontalmente
            xanchor="center",  # Anclaje central
            y=1.08,  # Separado de los logos (logos en 0.95)
            yanchor="bottom",  # Anclaje inferior
            bgcolor="rgba(0,0,0,0.8)",
            bordercolor="rgba(36,222,132,0.3)",
            borderwidth=1,
            font=dict(color="white", size=10),
        ),
        height=450,
        autosize=True,  # Responsive width
        margin=dict(t=80, b=40, l=60, r=60),  # Márgenes equilibrados
        hovermode="x unified",  # Unified para mostrar todas las estadísticas juntas
        # Configurar cabecera unificada del tooltip
        xaxis=dict(
            title=dict(text="Season", font=dict(color="#FFFFFF")),
            tickfont=dict(color="#FFFFFF"),
            gridcolor="rgba(255,255,255,0.1)",
            linecolor="rgba(255,255,255,0.2)",
            # Configuración básica y funcional
            ticktext=formatted_seasons,  # Eje X muestra: "20-21", "21-22"
            tickvals=x_positions,  # Coordenadas numéricas: [0, 1, 2, ...]
            range=[
                -0.3,
                len(formatted_seasons) - 0.7,
            ],  # Padding para evitar cortes de elementos
            dtick=1,  # Ticks en posiciones enteras
            showticklabels=True,
            hoverformat="",  # Sin formato adicional
        ),
    )

    # Las etiquetas del eje X y tooltips ya están configurados en el layout principal

    return dcc.Graph(
        figure=fig, style={"height": "400px"}, config={"displayModeBar": False}
    )


def create_radar_chart(player_stats):
    """
    Crea radar chart híbrido avanzado con análisis temporal y comparativa real.

    Args:
        player_stats: Lista de diccionarios con estadísticas por temporada

    Returns:
        Componente con selector y radar chart interactivo
    """
    if not player_stats:
        return dbc.Alert("No statistical data available", color="warning")

    # Calcular métricas tanto para temporada actual como histórico
    latest_stats = player_stats[-1] if player_stats else {}
    current_season = latest_stats.get("season", "Current")

    # Calcular promedios históricos del jugador (todas las temporadas)
    def calculate_historical_avg(metric_key):
        """Calcula promedio histórico de una métrica."""
        values = [
            stat.get(metric_key, 0) or 0
            for stat in player_stats
            if stat.get(metric_key) is not None
        ]
        return sum(values) / len(values) if values else 0

    # Métricas simples universales para comparar jugadores de cualquier posición
    categories = [
        "Pass Acc %",  # pass_accuracy_pct
        "Duels Won %",  # duels_won_pct
        "Goals/90",  # goals_per_90
        "Assists/90",  # assists_per_90
        "Def Actions/90",  # defensive_actions_per_90
        "Availability %",  # matches_played / 30 * 100
    ]

    # Calcular métricas simples para temporada actual
    def calculate_current_metrics():
        pass_acc = latest_stats.get("pass_accuracy_pct", 0) or 0
        duels_won = latest_stats.get("duels_won_pct", 0) or 0
        goals_90 = latest_stats.get("goals_per_90", 0) or 0
        assists_90 = latest_stats.get("assists_per_90", 0) or 0
        def_actions_90 = latest_stats.get("defensive_actions_per_90", 0) or 0
        matches = latest_stats.get("matches_played", 0) or 0

        return {
            "pass_accuracy": min(100, pass_acc),  # 0-100 directo
            "duels_won": min(100, duels_won),  # 0-100 directo
            "goals_per_90": min(100, goals_90 * 80),  # 0-1.25 -> 0-100 (optimizado)
            "assists_per_90": min(100, assists_90 * 100),  # 0-1.0 -> 0-100 (optimizado)
            "defensive_actions": min(
                100, def_actions_90 * 10
            ),  # 0-10 -> 0-100 (optimizado)
            "availability": min(100, (matches / 30) * 100),  # 0-30 partidos -> 0-100
        }

    # Calcular métricas históricas simples (promedio de todas las temporadas)
    def calculate_historical_metrics():
        pass_acc_avg = calculate_historical_avg("pass_accuracy_pct")
        duels_won_avg = calculate_historical_avg("duels_won_pct")
        goals_90_avg = calculate_historical_avg("goals_per_90")
        assists_90_avg = calculate_historical_avg("assists_per_90")
        def_actions_90_avg = calculate_historical_avg("defensive_actions_per_90")
        matches_avg = calculate_historical_avg("matches_played")

        return {
            "pass_accuracy": min(100, pass_acc_avg),  # 0-100 directo
            "duels_won": min(100, duels_won_avg),  # 0-100 directo
            "goals_per_90": min(100, goals_90_avg * 80),  # 0-1.25 -> 0-100 (optimizado)
            "assists_per_90": min(
                100, assists_90_avg * 100
            ),  # 0-1.0 -> 0-100 (optimizado)
            "defensive_actions": min(
                100, def_actions_90_avg * 10
            ),  # 0-10 -> 0-100 (optimizado)
            "availability": min(
                100, (matches_avg / 30) * 100
            ),  # 0-30 partidos -> 0-100
        }

    current_metrics = calculate_current_metrics()
    historical_metrics = calculate_historical_metrics()

    # Valores de referencia de liga Thai League (promedio real)
    league_reference = {
        "pass_accuracy": 75,  # 75% promedio pass accuracy
        "duels_won": 50,  # 50% promedio duels won
        "goals_per_90": 32,  # ~0.4 goals/90 promedio -> 32/100 (con escala *80)
        "assists_per_90": 30,  # ~0.3 assists/90 promedio -> 30/100 (con escala *100)
        "defensive_actions": 50,  # ~5 acc def/90 promedio -> 50/100 (con escala *10)
        "availability": 70,  # ~21 partidos promedio -> 70/100
    }

    # Función auxiliar para preparar valores reales para tooltips
    def prepare_real_values(stats_dict, is_league_ref=False):
        """Prepara valores reales para mostrar en tooltips."""
        if is_league_ref:
            # Valores de referencia de liga (ya son reales)
            return [
                75.0,  # pass_accuracy_pct
                50.0,  # duels_won_pct
                0.4,  # goals_per_90
                0.3,  # assists_per_90
                5.0,  # defensive_actions_per_90
                21,  # matches_played (de 30)
            ]
        else:
            # Valores reales del jugador
            pass_acc = stats_dict.get("pass_accuracy_pct", 0) or 0
            duels_won = stats_dict.get("duels_won_pct", 0) or 0
            goals_90 = stats_dict.get("goals_per_90", 0) or 0
            assists_90 = stats_dict.get("assists_per_90", 0) or 0
            def_actions_90 = stats_dict.get("defensive_actions_per_90", 0) or 0
            matches = stats_dict.get("matches_played", 0) or 0

            return [pass_acc, duels_won, goals_90, assists_90, def_actions_90, matches]

    # Preparar datos para el gráfico
    metric_keys = [
        "pass_accuracy",
        "duels_won",
        "goals_per_90",
        "assists_per_90",
        "defensive_actions",
        "availability",
    ]
    current_values = [current_metrics[key] for key in metric_keys]
    historical_values = [historical_metrics[key] for key in metric_keys]
    league_values = [league_reference[key] for key in metric_keys]

    # Preparar valores reales para tooltips
    current_real_values = prepare_real_values(latest_stats)
    historical_real_values = prepare_real_values(
        {
            "pass_accuracy_pct": calculate_historical_avg("pass_accuracy_pct"),
            "duels_won_pct": calculate_historical_avg("duels_won_pct"),
            "goals_per_90": calculate_historical_avg("goals_per_90"),
            "assists_per_90": calculate_historical_avg("assists_per_90"),
            "defensive_actions_per_90": calculate_historical_avg(
                "defensive_actions_per_90"
            ),
            "matches_played": calculate_historical_avg("matches_played"),
        }
    )
    league_real_values = prepare_real_values({}, is_league_ref=True)

    # Función para crear tooltip customizado
    def create_custom_tooltip(metric_index, value, prefix=""):
        """Crea tooltip personalizado según la métrica."""
        metric_names = [
            "Pass Acc %",
            "Duels Won %",
            "Goals/90",
            "Assists/90",
            "Def Actions/90",
            "Availability %",
        ]
        metric_name = metric_names[metric_index]

        if metric_index in [0, 1]:  # Pass Acc %, Duels Won %
            return f"<b>{metric_name}</b><br>{prefix}: {value:.1f}%<extra></extra>"
        elif metric_index in [2, 3, 4]:  # Goals/90, Assists/90, Def Actions/90
            units = ["/90", "/90", "/90"]
            return f"<b>{metric_name}</b><br>{prefix}: {value:.1f}{units[metric_index-2]}<extra></extra>"
        else:  # Availability (matches)
            return f"<b>{metric_name}</b><br>{prefix}: {int(value)} of 30 matches<extra></extra>"

    # Crear tooltips personalizados para cada trace
    def create_trace_tooltips(real_values, prefix):
        """Crea array de tooltips para un trace completo."""
        return [
            create_custom_tooltip(i, val, prefix) for i, val in enumerate(real_values)
        ]

    # Crear radar chart híbrido
    fig = go.Figure()

    # Liga promedio (referencia) - Más visible
    fig.add_trace(
        go.Scatterpolar(
            r=league_values,
            theta=categories,
            fill="toself",
            fillcolor="rgba(255, 255, 255, 0.15)",
            line=dict(color="rgba(255, 255, 255, 0.8)", width=2, dash="solid"),
            name="Thai League Avg",
            customdata=league_real_values,
            hovertemplate=[
                create_custom_tooltip(i, val, "League Avg")
                for i, val in enumerate(league_real_values)
            ],
        )
    )

    # Promedio histórico del jugador
    if len(player_stats) > 1:
        fig.add_trace(
            go.Scatterpolar(
                r=historical_values,
                theta=categories,
                fill="toself",
                fillcolor="rgba(255, 165, 0, 0.15)",
                line=dict(color="#FFA500", width=2, dash="dash"),
                name=f"Career Average ({len(player_stats)} seasons)",
                customdata=historical_real_values,
                hovertemplate=[
                    create_custom_tooltip(i, val, "Career Avg")
                    for i, val in enumerate(historical_real_values)
                ],
            )
        )

    # Temporada actual (principal)
    fig.add_trace(
        go.Scatterpolar(
            r=current_values,
            theta=categories,
            fill="toself",
            fillcolor="rgba(36, 222, 132, 0.3)",
            line=dict(color="#24DE84", width=3),
            marker=dict(size=8, color="#24DE84"),
            name=f"Current Season ({current_season})",
            customdata=current_real_values,
            hovertemplate=[
                create_custom_tooltip(i, val, "Current")
                for i, val in enumerate(current_real_values)
            ],
        )
    )

    # Layout mejorado
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor="rgba(255,255,255,0.2)",
                linecolor="rgba(255,255,255,0.3)",
                tickfont=dict(color="white", size=9),
                tickvals=[20, 40, 60, 80, 100],  # Menos ticks para claridad
                ticktext=["20", "40", "60", "80", "100"],
            ),
            angularaxis=dict(
                gridcolor="rgba(255,255,255,0.3)",
                tickfont=dict(color="white", size=10, family="Inter"),
                rotation=0,
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        legend=dict(
            orientation="h",  # Leyenda horizontal
            x=0.5,  # Centrado horizontalmente
            xanchor="center",  # Anclaje central
            y=1.08,  # Posición donde estaba el título
            yanchor="bottom",  # Anclaje inferior
            bgcolor="rgba(0,0,0,0.8)",
            bordercolor="rgba(36,222,132,0.3)",
            borderwidth=1,
            font=dict(color="white", size=10),
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=450,
        margin=dict(t=40, b=40, l=60, r=60),  # Márgenes reducidos para maximizar radar
    )

    return dcc.Graph(
        figure=fig, style={"height": "450px"}, config={"displayModeBar": False}
    )


def create_performance_heatmap(player_stats):
    """
    Crea heatmap de rendimiento por categorías a lo largo de las temporadas.

    Args:
        player_stats: Lista de diccionarios con estadísticas por temporada

    Returns:
        Componente dcc.Graph con el heatmap
    """
    if not player_stats or len(player_stats) < 2:
        return dbc.Alert(
            "Need at least 2 seasons for heatmap analysis", color="warning"
        )

    # Extraer temporadas
    seasons = [stat["season"] for stat in player_stats]

    # Definir métricas para el heatmap
    metrics = [
        "Goals per 90",
        "Assists per 90",
        "Pass Accuracy %",
        "Defensive Actions",
        "Shots on Target %",
        "Duels Won %",
    ]

    # Crear matriz de datos normalizados
    heatmap_data = []
    for metric in metrics:
        metric_values = []
        for stat in player_stats:
            if metric == "Goals per 90":
                value = stat.get("goals_per_90", 0) or 0
                # Normalizar: 0-1.5 goles/90 -> 0-100
                normalized = min(100, value * 66.67)
            elif metric == "Assists per 90":
                value = stat.get("assists_per_90", 0) or 0
                # Normalizar: 0-1.0 asistencias/90 -> 0-100
                normalized = min(100, value * 100)
            elif metric == "Pass Accuracy %":
                value = stat.get("pass_accuracy_pct", 0) or 0
                normalized = min(100, value)
            elif metric == "Defensive Actions":
                value = stat.get("defensive_actions_per_90", 0) or 0
                # Normalizar: 0-15 acciones/90 -> 0-100
                normalized = min(100, value * 6.67)
            elif metric == "Shots on Target %":
                value = stat.get("shots_on_target_pct", 0) or 0
                normalized = min(100, value)
            elif metric == "Duels Won %":
                value = stat.get("duels_won_pct", 0) or 0
                normalized = min(100, value)
            else:
                normalized = 0

            metric_values.append(normalized)
        heatmap_data.append(metric_values)

    # Crear heatmap
    fig = go.Figure(
        data=go.Heatmap(
            z=heatmap_data,
            x=seasons,
            y=metrics,
            colorscale=[
                [0, "#1a1a1a"],  # Negro oscuro para valores bajos
                [0.3, "#FF6B6B"],  # Rojo para valores medio-bajos
                [0.5, "#FFA726"],  # Naranja para valores medios
                [0.7, "#66BB6A"],  # Verde claro para valores medio-altos
                [1, "#24DE84"],  # Verde brillante para valores altos
            ],
            hoverongaps=False,
            hovertemplate="<b>%{y}</b><br>"
            + "Season: %{x}<br>"
            + "Performance: %{z:.1f}/100<extra></extra>",
            zmin=0,
            zmax=100,
        )
    )

    fig.update_layout(
        xaxis_title="Season",
        yaxis_title="Performance Metrics",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#FFFFFF"},
        height=380,
        margin=dict(t=30, b=40, l=120, r=40),  # Reducir margen superior
    )

    return dcc.Graph(
        figure=fig, style={"height": "380px"}, config={"displayModeBar": False}
    )


def create_statistics_summary(player_stats):
    """
    Crea tabla resumida de estadísticas clave con comparación temporal.

    Args:
        player_stats: Lista de diccionarios con estadísticas por temporada

    Returns:
        Componente dbc.Table con estadísticas resumidas
    """
    if not player_stats:
        return dbc.Alert("No statistical data available", color="warning")

    # Usar la temporada más reciente y anterior para comparación
    current_stats = player_stats[-1] if player_stats else {}
    previous_stats = player_stats[-2] if len(player_stats) > 1 else {}

    current_season = current_stats.get("season", "N/A")
    previous_season = previous_stats.get("season", "N/A") if previous_stats else None

    def get_trend_indicator(current_val, previous_val, metric_format="number"):
        """Genera indicador de tendencia visual con variación porcentual para no-porcentajes."""
        if not previous_val or previous_val == 0:
            return html.Span("—", style={"color": "var(--color-white-faded)"})

        # Calcular diferencia absoluta y porcentual
        diff_absolute = current_val - previous_val
        diff_percentage = ((current_val - previous_val) / previous_val) * 100

        # Para métricas que no son porcentajes, mostrar variación porcentual entre paréntesis
        if metric_format != "percentage":
            if current_val > previous_val:
                return html.Span(
                    [
                        html.I(className="bi bi-trend-up me-1"),
                        f"+{diff_absolute:.1f} ({diff_percentage:+.1f}%)",
                    ],
                    style={"color": "var(--color-primary)", "font-weight": "bold"},
                )
            elif current_val < previous_val:
                return html.Span(
                    [
                        html.I(className="bi bi-trend-down me-1"),
                        f"{diff_absolute:.1f} ({diff_percentage:.1f}%)",
                    ],
                    style={"color": "#FF6B6B", "font-weight": "bold"},
                )
            else:
                return html.Span(
                    [html.I(className="bi bi-dash me-1"), "0.0 (0.0%)"],
                    style={"color": "var(--color-white-faded)"},
                )
        else:
            # Para porcentajes, mantener el formato original (solo diferencia absoluta)
            if current_val > previous_val:
                return html.Span(
                    [html.I(className="bi bi-trend-up me-1"), f"+{diff_absolute:.1f}"],
                    style={"color": "var(--color-primary)", "font-weight": "bold"},
                )
            elif current_val < previous_val:
                return html.Span(
                    [html.I(className="bi bi-trend-down me-1"), f"{diff_absolute:.1f}"],
                    style={"color": "#FF6B6B", "font-weight": "bold"},
                )
            else:
                return html.Span(
                    [html.I(className="bi bi-dash me-1"), "0.0"],
                    style={"color": "var(--color-white-faded)"},
                )

    def format_percentage(value):
        """Formatea porcentajes con color según rango."""
        if not value:
            return html.Span("—", style={"color": "var(--color-white-faded)"})

        color = (
            "var(--color-primary)"
            if value >= 70
            else "#FFA726" if value >= 50 else "#FF6B6B"
        )
        return html.Span(f"{value:.1f}%", style={"color": color, "font-weight": "bold"})

    # Métricas clave optimizadas para primera impresión del jugador
    key_metrics = [
        # === RENDIMIENTO OFENSIVO ===
        {
            "icon": "bi bi-trophy",
            "metric": "Goals per 90",
            "current": current_stats.get("goals_per_90", 0.0) or 0.0,
            "previous": (
                previous_stats.get("goals_per_90", 0.0) or 0.0
                if previous_stats
                else 0.0
            ),
            "format": "decimal",
            "category": "offensive",
        },
        {
            "icon": "bi bi-hand-thumbs-up",
            "metric": "Assists per 90",
            "current": current_stats.get("assists_per_90", 0.0) or 0.0,
            "previous": (
                previous_stats.get("assists_per_90", 0.0) or 0.0
                if previous_stats
                else 0.0
            ),
            "format": "decimal",
            "category": "offensive",
        },
        {
            "icon": "bi bi-bullseye",
            "metric": "Shots on Target %",
            "current": current_stats.get("shots_on_target_pct", 0.0) or 0.0,
            "previous": (
                previous_stats.get("shots_on_target_pct", 0.0) or 0.0
                if previous_stats
                else 0.0
            ),
            "format": "percentage",
            "category": "offensive",
        },
        # === TÉCNICA Y DISTRIBUCIÓN ===
        {
            "icon": "bi bi-check-circle",
            "metric": "Pass Accuracy %",
            "current": current_stats.get("pass_accuracy_pct", 0.0) or 0.0,
            "previous": (
                previous_stats.get("pass_accuracy_pct", 0.0) or 0.0
                if previous_stats
                else 0.0
            ),
            "format": "percentage",
            "category": "technical",
        },
        {
            "icon": "bi bi-lightning",
            "metric": "xG + xA per 90",
            "current": (current_stats.get("xg_per_90", 0.0) or 0.0)
            + (current_stats.get("xa_per_90", 0.0) or 0.0),
            "previous": (
                (
                    (previous_stats.get("xg_per_90", 0.0) or 0.0)
                    + (previous_stats.get("xa_per_90", 0.0) or 0.0)
                )
                if previous_stats
                else 0.0
            ),
            "format": "decimal",
            "category": "technical",
        },
        # === RENDIMIENTO DEFENSIVO ===
        {
            "icon": "bi bi-shield",
            "metric": "Defensive Actions per 90",
            "current": current_stats.get("defensive_actions_per_90", 0.0) or 0.0,
            "previous": (
                previous_stats.get("defensive_actions_per_90", 0.0) or 0.0
                if previous_stats
                else 0.0
            ),
            "format": "decimal",
            "category": "defensive",
        },
        {
            "icon": "bi bi-arrow-up-circle",
            "metric": "Aerial Duels Won %",
            "current": current_stats.get("aerial_duels_won_pct", 0.0) or 0.0,
            "previous": (
                previous_stats.get("aerial_duels_won_pct", 0.0) or 0.0
                if previous_stats
                else 0.0
            ),
            "format": "percentage",
            "category": "defensive",
        },
        # === DISPONIBILIDAD Y EFICIENCIA ===
        {
            "icon": "bi bi-calendar-check",
            "metric": "Matches Played",
            "current": current_stats.get("matches_played", 0) or 0,
            "previous": (
                previous_stats.get("matches_played", 0) or 0 if previous_stats else 0
            ),
            "format": "number",
            "category": "availability",
        },
        {
            "icon": "bi bi-clock",
            "metric": "Minutes per Match",
            "current": (current_stats.get("minutes_played", 0) or 0)
            / max(1, current_stats.get("matches_played", 1) or 1),
            "previous": (
                (previous_stats.get("minutes_played", 0) or 0)
                / max(1, previous_stats.get("matches_played", 1) or 1)
                if previous_stats
                else 0
            ),
            "format": "decimal",
            "category": "availability",
        },
    ]

    # Crear filas de la tabla con agrupación por categorías
    table_rows = []
    current_category = None

    for metric in key_metrics:
        # Añadir separador de categoría si es necesario
        if metric["category"] != current_category:
            current_category = metric["category"]

            # Añadir header de categoría más visible
            category_names = {
                "offensive": "OFFENSIVE",
                "technical": "TECHNICAL",
                "defensive": "DEFENSIVE",
                "availability": "AVAILABILITY",
            }
            category_colors = {
                "offensive": "#FF6B6B",
                "technical": "#24DE84",
                "defensive": "#4DABF7",
                "availability": "#FFA726",
            }
            category_icons = {
                "offensive": "bi-crosshair",
                "technical": "bi-gear",
                "defensive": "bi-shield",
                "availability": "bi-calendar-week",
            }

            table_rows.append(
                html.Tr(
                    [
                        html.Td(
                            [
                                html.Div(
                                    [
                                        html.I(
                                            className=f"{category_icons.get(metric['category'], 'bi-circle')} me-2",
                                            style={
                                                "color": category_colors.get(
                                                    metric["category"],
                                                    "var(--color-white-faded)",
                                                )
                                            },
                                        ),
                                        html.Span(
                                            category_names.get(
                                                metric["category"],
                                                metric["category"].upper(),
                                            ),
                                            style={
                                                "color": category_colors.get(
                                                    metric["category"],
                                                    "var(--color-white-faded)",
                                                ),
                                                "font-weight": "700",
                                                "font-size": "0.75rem",
                                                "letter-spacing": "1px",
                                                "text-transform": "uppercase",
                                            },
                                        ),
                                    ],
                                    style={
                                        "padding": "4px 8px",
                                        "background-color": "rgba(255,255,255,0.05)",
                                        "border-radius": "4px",
                                        "border-left": f"3px solid {category_colors.get(metric['category'], '#FFFFFF')}",
                                        "display": "flex",
                                        "align-items": "center",
                                    },
                                )
                            ],
                            colSpan=3,
                            style={"padding": "0.5rem 1rem", "border": "none"},
                        )
                    ]
                )
            )

        # Formatear valor actual según tipo
        if metric["format"] == "percentage":
            current_display = format_percentage(metric["current"])
        elif metric["format"] == "decimal":
            current_display = html.Span(
                f"{metric['current']:.2f}",
                style={"color": "var(--color-white-faded)", "font-weight": "bold"},
            )
        else:  # number
            current_display = html.Span(
                str(int(metric["current"])),
                style={"color": "var(--color-white-faded)", "font-weight": "bold"},
            )

        # Generar indicador de tendencia
        trend = (
            get_trend_indicator(metric["current"], metric["previous"], metric["format"])
            if previous_stats
            else html.Span("—", style={"color": "var(--color-white-faded)"})
        )

        table_rows.append(
            html.Tr(
                [
                    html.Td(
                        [
                            html.I(
                                className=f"{metric['icon']} me-2",
                                style={"color": "var(--color-primary)"},
                            ),
                            metric["metric"],
                        ],
                        style={"color": "var(--color-white-faded)"},
                    ),
                    html.Td(current_display, className="text-center"),
                    html.Td(trend, className="text-center"),
                ]
            )
        )

    # Crear tabla con headers
    table_header = html.Thead(
        [
            html.Tr(
                [
                    html.Th(
                        "Metric",
                        style={
                            "color": "var(--color-primary)",
                            "border-bottom": "2px solid var(--color-primary)",
                        },
                    ),
                    html.Th(
                        current_season,
                        className="text-center",
                        style={
                            "color": "var(--color-primary)",
                            "border-bottom": "2px solid var(--color-primary)",
                        },
                    ),
                    html.Th(
                        (
                            f"vs {previous_season}"
                            if previous_season and previous_season != "N/A"
                            else "Trend"
                        ),
                        className="text-center",
                        style={
                            "color": "var(--color-primary)",
                            "border-bottom": "2px solid var(--color-primary)",
                        },
                    ),
                ]
            )
        ]
    )

    table = dbc.Table(
        [table_header, html.Tbody(table_rows)],
        bordered=False,
        hover=True,
        responsive=True,
        style={
            "background-color": "transparent",
            "color": "var(--color-white-faded)",
            "margin-bottom": "0",
        },
        className="stats-summary-table",
    )

    return html.Div([table])


def create_comparison_bar_chart(player_stats):
    """
    Crea gráfico de barras comparativo entre temporadas.

    Args:
        player_stats: Lista de diccionarios con estadísticas por temporada

    Returns:
        Componente dcc.Graph con el gráfico de barras
    """
    if not player_stats:
        return dbc.Alert("No statistical data available", color="warning")

    # Extraer datos
    seasons = [stat["season"] for stat in player_stats]
    goals = [stat["goals"] or 0 for stat in player_stats]
    assists = [stat["assists"] or 0 for stat in player_stats]

    # Crear gráfico de barras agrupadas
    fig = go.Figure()

    # Barras de goles
    fig.add_trace(
        go.Bar(
            name="Goals",
            x=seasons,
            y=goals,
            marker_color="#24DE84",
            hovertemplate="<b>Season:</b> %{x}<br><b>Goals:</b> %{y}<extra></extra>",
            text=goals,
            textposition="auto",
            textfont=dict(color="white", size=12),
        )
    )

    # Barras de asistencias
    fig.add_trace(
        go.Bar(
            name="Assists",
            x=seasons,
            y=assists,
            marker_color="#FFA726",
            hovertemplate="<b>Season:</b> %{x}<br><b>Assists:</b> %{y}<extra></extra>",
            text=assists,
            textposition="auto",
            textfont=dict(color="white", size=12),
        )
    )

    # Barras de contribución total (Goals + Assists)
    total_contribution = [g + a for g, a in zip(goals, assists)]
    fig.add_trace(
        go.Bar(
            name="Total G+A",
            x=seasons,
            y=total_contribution,
            marker_color="#42A5F5",
            opacity=0.7,
            hovertemplate="<b>Season:</b> %{x}<br><b>Total G+A:</b> %{y}<extra></extra>",
            text=total_contribution,
            textposition="auto",
            textfont=dict(color="white", size=11),
        )
    )

    fig.update_layout(
        title={
            "text": "Goals & Assists Comparison by Season",
            "x": 0.5,
            "font": {"color": "#24DE84", "size": 14},
        },
        xaxis_title="Season",
        yaxis_title="Count",
        barmode="group",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#FFFFFF"},
        legend=dict(
            bgcolor="rgba(0,0,0,0.7)",
            bordercolor="rgba(36,222,132,0.3)",
            borderwidth=1,
            x=0.02,
            y=0.98,
        ),
        height=300,
        margin=dict(t=50, b=40, l=50, r=40),
    )

    return dcc.Graph(
        figure=fig, style={"height": "300px"}, config={"displayModeBar": False}
    )


def create_efficiency_metrics_chart(player_stats):
    """
    Crea gráfico de métricas de eficiencia avanzadas.

    Args:
        player_stats: Lista de diccionarios con estadísticas por temporada

    Returns:
        Componente dcc.Graph con métricas de eficiencia
    """
    if not player_stats:
        return dbc.Alert("No statistical data available", color="warning")

    seasons = [stat["season"] for stat in player_stats]

    # Calcular métricas de eficiencia
    goal_conversion = []
    assist_efficiency = []
    overall_rating = []

    for stat in player_stats:
        # Goal conversion rate (goals / shots)
        goals = stat.get("goals", 0) or 0
        shots = stat.get("shots", 0) or 0
        conversion = (goals / shots * 100) if shots > 0 else 0
        goal_conversion.append(conversion)

        # Assist efficiency (assists per 90)
        assists_per_90 = stat.get("assists_per_90", 0) or 0
        assist_efficiency.append(assists_per_90 * 100)  # Escalar para visualización

        # Overall rating (combinación ponderada)
        goals_per_90 = stat.get("goals_per_90", 0) or 0
        pass_acc = stat.get("pass_accuracy_pct", 0) or 0
        duels_won = stat.get("duels_won_pct", 0) or 0

        # Rating ponderado (escala 0-100)
        rating = (
            goals_per_90 * 20  # 20x weight for goals
            + assists_per_90 * 15  # 15x weight for assists
            + pass_acc * 0.4  # Direct percentage
            + duels_won * 0.3  # Direct percentage
        )
        overall_rating.append(min(100, rating))

    # Crear gráfico con múltiples métricas
    fig = go.Figure()

    # Goal conversion rate
    fig.add_trace(
        go.Scatter(
            x=seasons,
            y=goal_conversion,
            mode="lines+markers",
            name="Goal Conversion %",
            line=dict(color="#24DE84", width=3),
            marker=dict(size=8),
            hovertemplate="<b>Season:</b> %{x}<br><b>Conversion:</b> %{y:.1f}%<extra></extra>",
        )
    )

    # Assist efficiency
    fig.add_trace(
        go.Scatter(
            x=seasons,
            y=assist_efficiency,
            mode="lines+markers",
            name="Assist Efficiency (x100)",
            line=dict(color="#FFA726", width=3),
            marker=dict(size=8),
            hovertemplate="<b>Season:</b> %{x}<br><b>Efficiency:</b> %{y:.1f}<extra></extra>",
        )
    )

    # Overall rating
    fig.add_trace(
        go.Scatter(
            x=seasons,
            y=overall_rating,
            mode="lines+markers",
            name="Overall Rating",
            line=dict(color="#E57373", width=3),
            marker=dict(size=8),
            hovertemplate="<b>Season:</b> %{x}<br><b>Rating:</b> %{y:.1f}/100<extra></extra>",
        )
    )

    fig.update_layout(
        title={
            "text": "Efficiency Metrics Evolution",
            "x": 0.5,
            "font": {"color": "#24DE84", "size": 14},
        },
        xaxis_title="Season",
        yaxis_title="Efficiency Score",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#FFFFFF"},
        legend=dict(
            bgcolor="rgba(0,0,0,0.7)",
            bordercolor="rgba(36,222,132,0.3)",
            borderwidth=1,
            x=0.02,
            y=0.98,
        ),
        height=300,
        margin=dict(t=50, b=40, l=50, r=40),
        hovermode="x unified",
    )

    return dcc.Graph(
        figure=fig, style={"height": "300px"}, config={"displayModeBar": False}
    )


# === ML ENHANCED CHART FUNCTIONS - Phase 13.3 ===


def create_pdi_evolution_chart(player_id, seasons=None):
    """
    Crea gráfico de evolución del Player Development Index (PDI) usando PDI Calculator completo.

    MIGRADO: Usa PlayerAnalyzer integrado con PDI Calculator científico.
    """
    try:
        # Inicializar analyzer ML con PDI Calculator integrado
        player_analyzer = PlayerAnalyzer()

        if not seasons:
            # CORREGIDO: Obtener temporadas reales del jugador desde la base de datos
            seasons = player_analyzer.get_available_seasons_for_player(player_id)
            if not seasons:
                logger.warning(f"No se encontraron temporadas para jugador {player_id}")
                return dbc.Alert(
                    "No hay temporadas con datos profesionales para este jugador",
                    color="warning",
                )

        # Obtener métricas PDI solo para temporadas válidas
        pdi_data = []
        for season in seasons:
            try:
                # NUEVO: Validar que la temporada existe antes de calcular
                if not player_analyzer.validate_season_exists_for_player(
                    player_id, season
                ):
                    logger.debug(
                        f"Saltando temporada {season} - no tiene datos para jugador {player_id}"
                    )
                    continue

                # Calcular métricas PDI usando el calculador integrado
                ml_metrics = player_analyzer.calculate_or_update_pdi_metrics(
                    player_id, season, force_recalculate=False
                )

                if ml_metrics:
                    # Usar métricas del PDI Calculator científico (diccionario compatible)
                    pdi_data.append(
                        {
                            "season": season,
                            "pdi_overall": ml_metrics.get("pdi_overall", 0),
                            "pdi_universal": ml_metrics.get("pdi_universal", 0),
                            "pdi_zone": ml_metrics.get("pdi_zone", 0),
                            "pdi_position_specific": ml_metrics.get(
                                "pdi_position_specific", 0
                            ),
                            "technical_proficiency": ml_metrics.get(
                                "technical_proficiency", 0
                            ),
                            "tactical_intelligence": ml_metrics.get(
                                "tactical_intelligence", 0
                            ),
                            "physical_performance": ml_metrics.get(
                                "physical_performance", 0
                            ),
                            "consistency_index": ml_metrics.get("consistency_index", 0),
                            "position_analyzed": ml_metrics.get(
                                "position_analyzed", "CF"
                            ),
                        }
                    )
                    logger.info(
                        f"✅ PDI Calculator: Season {season}, PDI={ml_metrics.get('pdi_overall')}"
                    )

            except Exception as e:
                logger.error(
                    f"Error obteniendo métricas PDI para temporada {season}: {e}"
                )
                continue

        if not pdi_data:
            return dbc.Alert(
                "No PDI metrics available - Try calculating metrics first",
                color="warning",
            )

        # Crear gráfico PDI con métricas científicas
        fig = go.Figure()

        # PDI Overall (línea principal - compatible con MLMetrics)
        fig.add_trace(
            go.Scatter(
                x=[d["season"] for d in pdi_data],
                y=[d["pdi_overall"] for d in pdi_data],
                mode="lines+markers",
                name="PDI Overall",
                line=dict(color="#24DE84", width=4),
                marker=dict(size=10),
                hovertemplate="<b>PDI Overall</b><br>%{y:.1f}<br>Season: %{x}<extra></extra>",
            )
        )

        # Componentes PDI científicos (líneas secundarias)
        fig.add_trace(
            go.Scatter(
                x=[d["season"] for d in pdi_data],
                y=[d["pdi_universal"] for d in pdi_data],
                mode="lines+markers",
                name="Universal (40%)",
                line=dict(color="#1E3A8A", width=2, dash="dot"),
                marker=dict(size=6),
                hovertemplate="<b>Universal Metrics</b><br>%{y:.1f}<br>Season: %{x}<extra></extra>",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=[d["season"] for d in pdi_data],
                y=[d["pdi_zone"] for d in pdi_data],
                mode="lines+markers",
                name="Zone (35%)",
                line=dict(color="#F59E0B", width=2, dash="dash"),
                marker=dict(size=6),
                hovertemplate="<b>Zone Metrics</b><br>%{y:.1f}<br>Season: %{x}<extra></extra>",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=[d["season"] for d in pdi_data],
                y=[d["pdi_position_specific"] for d in pdi_data],
                mode="lines+markers",
                name="Position (25%)",
                line=dict(color="#10B981", width=2, dash="dashdot"),
                marker=dict(size=6),
                hovertemplate="<b>Position Specific</b><br>%{y:.1f}<br>Season: %{x}<extra></extra>",
            )
        )

        # Configurar layout con información dinámica
        fig.update_layout(
            title=dict(
                text=f"PDI Evolution - {len(pdi_data)} Seasons",
                font=dict(color="#24DE84", size=16),
            ),
            xaxis_title="Season",
            yaxis_title="PDI Score (0-100)",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#FFFFFF"),
            legend=dict(
                bgcolor="rgba(0,0,0,0.7)",
                bordercolor="rgba(36,222,132,0.3)",
                borderwidth=1,
                x=0.02,
                y=0.98,
            ),
            height=350,
            margin=dict(t=60, b=40, l=50, r=40),
            hovermode="x unified",
        )

        # Añadir líneas de referencia
        fig.add_hline(
            y=75,
            line_dash="solid",
            line_color="#10B981",
            annotation_text="Excellence (75+)",
            annotation_position="top right",
        )
        fig.add_hline(
            y=60,
            line_dash="solid",
            line_color="#F59E0B",
            annotation_text="Good (60+)",
            annotation_position="top right",
        )
        fig.add_hline(
            y=40,
            line_dash="solid",
            line_color="#EF4444",
            annotation_text="Needs Improvement (40+)",
            annotation_position="top right",
        )

        # Configurar ejes
        fig.update_yaxes(
            range=[0, 100], dtick=10, showgrid=True, gridcolor="rgba(255,255,255,0.1)"
        )
        fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")

        return dcc.Graph(
            figure=fig, style={"height": "350px"}, config={"displayModeBar": False}
        )

    except Exception as e:
        logger.error(f"Error creating PDI evolution chart: {e}")
        return dbc.Alert(f"Error creating PDI chart: {str(e)}", color="danger")


def create_ml_enhanced_radar_chart(player_id, seasons=None):
    """
    Crea radar chart mejorado con métricas PDI Calculator científicas usando todas las temporadas.

    MEJORADO: Usa todas las temporadas disponibles con promedios ponderados por recencia.
    MIGRADO: Usa PDI Calculator integrado con PlayerAnalyzer.
    """
    try:
        # Inicializar analyzer ML con PDI Calculator integrado
        player_analyzer = PlayerAnalyzer()

        if not seasons:
            # Obtener todas las temporadas disponibles del jugador
            seasons = player_analyzer.get_available_seasons_for_player(player_id)
            if not seasons:
                logger.warning(f"No se encontraron temporadas para jugador {player_id}")
                return dbc.Alert(
                    "No hay temporadas con datos profesionales para este jugador",
                    color="warning",
                )

        # Calcular métricas para todas las temporadas disponibles
        all_seasons_metrics = []
        for season in seasons:
            try:
                # Validar que la temporada existe antes de calcular
                if not player_analyzer.validate_season_exists_for_player(
                    player_id, season
                ):
                    logger.debug(
                        f"Saltando temporada {season} - no tiene datos para jugador {player_id}"
                    )
                    continue

                ml_metrics = player_analyzer.calculate_or_update_pdi_metrics(
                    player_id, season, force_recalculate=False
                )

                if ml_metrics:
                    all_seasons_metrics.append(
                        {"season": season, "metrics": ml_metrics}
                    )
                    logger.debug(f"✅ Radar Chart: Temporada {season} incluida")

            except Exception as e:
                logger.error(f"Error obteniendo métricas para temporada {season}: {e}")
                continue

        if not all_seasons_metrics:
            return dbc.Alert(
                "No PDI metrics available for radar chart", color="warning"
            )

        # Calcular promedios ponderados (más peso a temporadas recientes)
        weighted_metrics = {}
        metric_keys = [
            "technical_proficiency",
            "tactical_intelligence",
            "physical_performance",
            "consistency_index",
            "pdi_universal",
            "pdi_zone",
            "pdi_position_specific",
        ]

        total_weight = 0
        for i, season_data in enumerate(all_seasons_metrics):
            # Peso mayor para temporadas más recientes (última temporada peso 3, anterior peso 2, etc.)
            weight = len(all_seasons_metrics) - i
            total_weight += weight

            for metric_key in metric_keys:
                value = season_data["metrics"].get(metric_key, 0)
                if metric_key not in weighted_metrics:
                    weighted_metrics[metric_key] = 0
                weighted_metrics[metric_key] += value * weight

        # Calcular promedios finales
        for metric_key in weighted_metrics:
            weighted_metrics[metric_key] = (
                weighted_metrics[metric_key] / total_weight if total_weight > 0 else 0
            )

        # Definir métricas para radar chart usando promedios ponderados
        metrics_data = {
            "Technical Skills": weighted_metrics.get("technical_proficiency", 50),
            "Tactical Intelligence": weighted_metrics.get("tactical_intelligence", 50),
            "Physical Performance": weighted_metrics.get("physical_performance", 50),
            "Consistency": weighted_metrics.get("consistency_index", 50),
            "Universal Metrics": weighted_metrics.get("pdi_universal", 50),
            "Zone Metrics": weighted_metrics.get("pdi_zone", 50),
            "Position Specific": weighted_metrics.get("pdi_position_specific", 50),
        }

        # Obtener información de posición de la temporada más reciente
        latest_season_metrics = all_seasons_metrics[-1]["metrics"]
        position = latest_season_metrics.get("position_analyzed", "Unknown")

        logger.info(
            f"Radar chart para {position}: {len(all_seasons_metrics)} temporadas promediadas"
        )
        logger.info(
            f"Temporadas incluidas: {[s['season'] for s in all_seasons_metrics]}"
        )

        # Crear radar chart
        fig = go.Figure()

        # Crear hover personalizado con información detallada
        hover_data = []
        for metric, value in metrics_data.items():
            seasons_list = ", ".join([s["season"] for s in all_seasons_metrics])
            hover_info = (
                f"<b>{metric}</b><br>"
                f"Score: {value:.1f}/100<br>"
                f"<i>Promedio ponderado de {len(all_seasons_metrics)} temporadas</i><br>"
                f"<span style='font-size:10px'>Temporadas: {seasons_list}</span>"
            )
            hover_data.append(hover_info)

        fig.add_trace(
            go.Scatterpolar(
                r=list(metrics_data.values()),
                theta=list(metrics_data.keys()),
                fill="toself",
                name=f"ML Analysis ({len(all_seasons_metrics)} seasons)",
                fillcolor="rgba(36, 222, 132, 0.3)",
                line=dict(color="#24DE84", width=3),
                hovertemplate="%{customdata}<extra></extra>",
                customdata=hover_data,
            )
        )

        # Configurar layout con información contextual (igualado al radar chart original)
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    gridcolor="rgba(255,255,255,0.2)",
                    linecolor="rgba(255,255,255,0.3)",
                    tickcolor="rgba(255,255,255,0.5)",
                    tickfont=dict(color="#FFFFFF", size=9),
                    tickvals=[0, 25, 50, 75, 100],
                    ticktext=["0", "25", "50", "75", "100"],
                ),
                angularaxis=dict(
                    gridcolor="rgba(255,255,255,0.3)",
                    linecolor="rgba(255,255,255,0.3)",
                    tickcolor="rgba(255,255,255,0.5)",
                    tickfont=dict(color="#FFFFFF", size=11, family="Arial Black"),
                ),
                bgcolor="rgba(0,0,0,0)",
            ),
            showlegend=True,
            legend=dict(
                bgcolor="rgba(0,0,0,0.7)",
                bordercolor="rgba(36,222,132,0.3)",
                borderwidth=1,
                x=0.02,
                y=0.02,
                font=dict(color="#FFFFFF", size=10),
            ),
            title={
                "text": f"ML-Enhanced Performance Profile<br><span style='font-size:11px; color:#CCCCCC'>Análisis de {len(all_seasons_metrics)} temporadas con pesos por recencia</span>",
                "x": 0.5,
                "font": {"color": "#24DE84", "size": 14},
            },
            annotations=[
                dict(
                    text=f"Temporadas analizadas: {', '.join([s['season'] for s in all_seasons_metrics])}<br>"
                    f"Posición: {position}<br>"
                    f"Mayor peso a temporadas recientes",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.02,
                    y=0.98,
                    xanchor="left",
                    yanchor="top",
                    font=dict(size=9, color="#CCCCCC"),
                    bgcolor="rgba(0,0,0,0.6)",
                    bordercolor="rgba(36,222,132,0.3)",
                    borderwidth=1,
                    borderpad=4,
                )
            ],
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=400,
            margin=dict(t=60, b=40, l=40, r=40),
        )

        return dcc.Graph(
            figure=fig, style={"height": "400px"}, config={"displayModeBar": False}
        )

    except Exception as e:
        logger.error(f"Error creating ML radar chart: {e}")
        return dbc.Alert(f"Error creating radar chart: {str(e)}", color="danger")


def create_etl_management_interface():
    """
    Crea interfaz de gestión ETL para testear el ETL Coordinator CRISP-DM.

    NUEVO: Interface completa para pipeline ETL con metodología CRISP-DM.
    """
    try:
        from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer

        # Inicializar analyzer para obtener temporadas disponibles
        player_analyzer = PlayerAnalyzer()
        available_seasons = player_analyzer.get_available_seasons_for_etl()

        # Crear opciones de dropdown
        season_options = [
            {"label": f"{season} - {desc}", "value": season}
            for season, desc in available_seasons.items()
        ]

        if not season_options:
            season_options = [{"label": "No seasons available", "value": ""}]

        # Interface completa
        etl_interface = dbc.Card(
            [
                dbc.CardHeader(
                    [
                        html.H5(
                            [
                                html.I(
                                    className="bi bi-gear-fill me-2 text-primary",
                                ),
                                "ETL Coordinator - CRISP-DM Pipeline",
                            ],
                            className="mb-0 text-primary",
                        )
                    ]
                ),
                dbc.CardBody(
                    [
                        # Selector de temporada
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.Label(
                                            "Season:",
                                            className="form-label text-primary",
                                        ),
                                        dcc.Dropdown(
                                            id="etl-season-dropdown",
                                            options=season_options,
                                            value=(
                                                season_options[0]["value"]
                                                if season_options
                                                and season_options[0]["value"]
                                                else None
                                            ),
                                            placeholder="Select season to process",
                                        ),
                                    ],
                                    width=6,
                                ),
                                dbc.Col(
                                    [
                                        html.Label(
                                            "Matching Threshold:",
                                            className="form-label text-primary",
                                        ),
                                        dbc.Input(
                                            id="etl-threshold-input",
                                            type="number",
                                            value=85,
                                            min=70,
                                            max=100,
                                            step=5,
                                            style={
                                                "background-color": "#2B2B2B",
                                                "border-color": "#24DE84",
                                                "color": "#FFFFFF",
                                            },
                                        ),
                                    ],
                                    width=6,
                                ),
                            ],
                            className="mb-3",
                        ),
                        # Controles ETL
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            [
                                                html.I(
                                                    className="bi bi-play-fill me-2"
                                                ),
                                                "Execute CRISP-DM Pipeline",
                                            ],
                                            id="etl-execute-btn",
                                            color="success",
                                            className="me-2",
                                        ),
                                        dbc.Button(
                                            [
                                                html.I(
                                                    className="bi bi-arrow-clockwise me-2"
                                                ),
                                                "Check Status",
                                            ],
                                            id="etl-status-btn",
                                            color="info",
                                            className="me-2",
                                        ),
                                        dbc.Button(
                                            [
                                                html.I(className="bi bi-trash me-2"),
                                                "Cleanup & Reprocess",
                                            ],
                                            id="etl-cleanup-btn",
                                            color="warning",
                                        ),
                                    ],
                                    width=12,
                                )
                            ],
                            className="mb-3",
                        ),
                        # Checkbox opciones
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Checklist(
                                            options=[
                                                {
                                                    "label": " Calculate PDI Metrics",
                                                    "value": "pdi",
                                                },
                                                {
                                                    "label": " Force Reload Data",
                                                    "value": "force",
                                                },
                                            ],
                                            value=["pdi"],
                                            id="etl-options-checklist",
                                            inline=True,
                                        )
                                    ],
                                    width=12,
                                )
                            ],
                            className="mb-3",
                        ),
                        # Área de resultados
                        html.Div(
                            id="etl-results-area",
                            children=[
                                dbc.Alert(
                                    [
                                        html.I(className="bi bi-info-circle me-2"),
                                        "Select a season and click 'Execute CRISP-DM Pipeline' to start ETL processing.",
                                    ],
                                    color="info",
                                    className="mb-0",
                                )
                            ],
                        ),
                    ]
                ),
            ],
            style={
                "background-color": "#2B2B2B",
                "border-color": "rgba(36, 222, 132, 0.3)",
            },
        )

        return etl_interface

    except Exception as e:
        logger.error(f"Error creating ETL interface: {e}")
        return dbc.Alert(
            [
                html.I(className="bi bi-exclamation-triangle me-2"),
                f"Error loading ETL interface: {str(e)}",
            ],
            color="danger",
        )


def create_etl_status_display(etl_status: dict = None, season: str = ""):
    """
    Crea display detallado del estado ETL para una temporada.

    Args:
        etl_status: Estado del ETL
        season: Temporada

    Returns:
        Componente con información de estado
    """
    if not etl_status:
        return dbc.Alert("No ETL status available", color="warning")

    try:
        status = etl_status.get("status", "unknown")

        # Color según estado
        status_colors = {
            "completed": "success",
            "processing": "info",
            "error": "danger",
            "not_processed": "secondary",
        }
        color = status_colors.get(status, "secondary")

        # Iconos según estado
        status_icons = {
            "completed": "bi-check-circle-fill",
            "processing": "bi-arrow-repeat",
            "error": "bi-exclamation-triangle-fill",
            "not_processed": "bi-clock",
        }
        icon = status_icons.get(status, "bi-question-circle")

        status_display = dbc.Card(
            [
                dbc.CardHeader(
                    [
                        html.H6(
                            [html.I(className=f"{icon} me-2"), f"ETL Status: {season}"],
                            className="mb-0",
                        )
                    ]
                ),
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Badge(
                                            status.replace("_", " ").title(),
                                            color=color,
                                            className="mb-2",
                                        ),
                                        html.P(
                                            etl_status.get("message", "No message"),
                                            className="mb-2",
                                        ),
                                    ],
                                    width=12,
                                )
                            ]
                        ),
                        # Estadísticas detalladas
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.Small(
                                            "Total Records:",
                                            style={"color": "var(--color-white-faded)"},
                                        ),
                                        html.P(
                                            str(etl_status.get("total_records", 0)),
                                            className="mb-1 fw-bold text-primary",
                                        ),
                                    ],
                                    width=3,
                                ),
                                dbc.Col(
                                    [
                                        html.Small(
                                            "Imported:",
                                            style={"color": "var(--color-white-faded)"},
                                        ),
                                        html.P(
                                            str(etl_status.get("imported_records", 0)),
                                            className="mb-1 fw-bold text-success",
                                        ),
                                    ],
                                    width=3,
                                ),
                                dbc.Col(
                                    [
                                        html.Small(
                                            "Matched Players:",
                                            style={"color": "var(--color-white-faded)"},
                                        ),
                                        html.P(
                                            str(etl_status.get("matched_players", 0)),
                                            className="mb-1 fw-bold text-info",
                                        ),
                                    ],
                                    width=3,
                                ),
                                dbc.Col(
                                    [
                                        html.Small(
                                            "Errors:",
                                            style={"color": "var(--color-white-faded)"},
                                        ),
                                        html.P(
                                            str(etl_status.get("errors_count", 0)),
                                            className="mb-1 fw-bold text-danger",
                                        ),
                                    ],
                                    width=3,
                                ),
                            ]
                        ),
                        # Información adicional si disponible
                        html.Hr(),
                        html.Small(
                            [
                                f"Last Updated: {etl_status.get('last_updated', 'Never')}",
                                html.Br(),
                                f"CRISP-DM Phase: {etl_status.get('crisp_dm_phase', 'Unknown')}",
                            ],
                            style={"color": "var(--color-white-faded)"},
                        ),
                    ]
                ),
            ],
            style={
                "background-color": "#2B2B2B",
                "border-color": "rgba(36, 222, 132, 0.3)",
            },
        )

        return status_display

    except Exception as e:
        logger.error(f"Error creating ETL status display: {e}")
        return dbc.Alert(f"Error displaying status: {str(e)}", color="danger")


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
                                    "border": "3px solid var(--color-primary)",
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
                                        className="title-lg mb-3 text-primary",
                                    ),
                                    html.P(
                                        [
                                            html.I(
                                                className="bi bi-at me-2 text-primary",
                                            ),
                                            user.username,
                                        ],
                                        style={"color": "var(--color-white-faded)"},
                                        className="mb-2",
                                    ),
                                    html.P(
                                        [
                                            html.I(
                                                className="bi bi-envelope me-2 text-primary",
                                            ),
                                            user.email,
                                        ],
                                        style={"color": "var(--color-white-faded)"},
                                        className="mb-2",
                                    ),
                                    html.P(
                                        [
                                            html.I(
                                                className="bi bi-telephone me-2 text-primary"
                                            ),
                                            user.phone or "No phone",
                                        ],
                                        style={"color": "var(--color-white-faded)"},
                                        className="mb-2",
                                    ),
                                    html.P(
                                        [
                                            html.I(
                                                className="bi bi-calendar-date me-2 text-primary"
                                            ),
                                            f"Age: {stats.get('age', 'N/A')}",
                                        ],
                                        style={"color": "var(--color-white-faded)"},
                                        className="mb-2",
                                    ),
                                    html.P(
                                        [
                                            html.I(
                                                className="bi bi-briefcase me-2 text-primary"
                                            ),
                                            (
                                                f"Service: "
                                                f"{player.service or 'No service'}"
                                            ),
                                        ],
                                        style={"color": "var(--color-white-faded)"},
                                        className="mb-2",
                                    ),
                                    html.P(
                                        [
                                            html.I(
                                                className="bi bi-collection me-2 text-primary"
                                            ),
                                            f"Enrolled Sessions: {player.enrolment}",
                                        ],
                                        style={"color": "var(--color-white-faded)"},
                                        className="mb-2",
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
                                                className="text-center text-primary",
                                            ),
                                            html.H2(
                                                str(stats.get("completed", 0)),
                                                className="text-center",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                            ),
                                            html.P(
                                                "Completed",
                                                className="text-center",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
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
                                                className="text-center text-primary",
                                            ),
                                            html.H2(
                                                str(stats.get("scheduled", 0)),
                                                className="text-center",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                            ),
                                            html.P(
                                                "Scheduled",
                                                className="text-center",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
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
                                                className="text-center text-primary",
                                            ),
                                            html.H2(
                                                str(stats.get("remaining", 0)),
                                                className="text-center",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                            ),
                                            html.P(
                                                "Remaining",
                                                className="text-center",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
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
                                                className="text-center text-primary",
                                            ),
                                            html.H2(
                                                "Next",
                                                className="text-center",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                            ),
                                            html.P(
                                                stats.get(
                                                    "next_session", "No sessions"
                                                ),
                                                className="text-center",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
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
                            "color": "var(--color-primary)",
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
                                                    html.Div(
                                                        [
                                                            html.Span(
                                                                "Scheduled",
                                                                id="status-scheduled",
                                                                className="status-scheduled status-badge",
                                                            ),
                                                            html.Span(
                                                                "Completed",
                                                                id="status-completed",
                                                                className="status-completed status-badge",
                                                            ),
                                                            html.Span(
                                                                "Canceled",
                                                                id="status-canceled",
                                                                className="status-canceled status-badge",
                                                            ),
                                                        ],
                                                        className="status-badges-container",
                                                    ),
                                                ],
                                                className="status-filter-container",
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
                                    "color": "var(--color-primary)",
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
                                    "color": "var(--color-primary)",
                                    "font-size": "0.9rem",
                                },
                                label_class_name="text-base",
                            ),
                            dbc.Tab(
                                label="Notes",
                                tab_id="notes",
                                active_label_style={
                                    "color": "var(--color-primary)",
                                    "font-size": "0.9rem",
                                },
                                label_class_name="text-base",
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
                        style={"margin-bottom": "10px"},
                    ),
                    # Información del jugador en formato vertical centrado
                    html.Div(
                        [
                            html.P(
                                (
                                    f"Age: "
                                    f"{player_data['age'] if player_data['age'] else 'N/A'} "
                                    "years"
                                ),
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
                                (
                                    f"Next Session: "
                                    f"{player_data.get('next_session', 'To be confirmed')}"
                                ),
                                style={"color": "var(--color-white-faded)"},
                                className="text-center mb-3 text-sm fst-italic",
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
                                                html.I(className="bi bi-people"),
                                                className="text-center text-primary",
                                            ),
                                            html.H2(
                                                "0",
                                                className="text-center",
                                                id="total-players",
                                            ),
                                            html.P(
                                                "Total Players",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                                className="text-center",
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
                                                className="text-center text-primary",
                                            ),
                                            html.H2(
                                                "0",
                                                className="text-center",
                                                id="total-sessions",
                                            ),
                                            html.P(
                                                "Total Sessions",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                                className="text-center",
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
                                                className="text-center text-primary",
                                            ),
                                            html.H2(
                                                "0",
                                                className="text-center",
                                                id="completed-sessions",
                                            ),
                                            html.P(
                                                "Completed Sessions",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                                className="text-center",
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
                                                className="text-center text-primary",
                                            ),
                                            html.H2(
                                                "0",
                                                className="text-center",
                                                id="active-sessions",
                                            ),
                                            html.P(
                                                "Active Sessions",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                                className="text-center",
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
                                                className="card-title text-primary",
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
    """
    Función principal para mostrar el contenido de la sección Ballers -
    MIGRADA DE STREAMLIT.
    """

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
    # Obtener lista de métricas del controller usando la misma
    # lógica que Streamlit
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
                                style={"font-weight": "500"},
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
                            "color": "var(--color-primary)",
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
                                    "text": (
                                        "Select metrics to display performance evolution"
                                    ),
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
                            "color": "var(--color-primary)",
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
                    "color": "var(--color-primary)",
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
                className="mb-3 text-sm",
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
                className="custom-button text-base",  # Usar la clase CSS para los estilos
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

        # Placeholder para FullCalendar (future enhancement)
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
                            className="text-center",
                            style={"color": "var(--color-white-faded)"},
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
            className="text-danger text-center p-4",
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
                    "color": "var(--color-primary)",
                    "font-size": "0.9rem",
                },
                label_class_name="text-base",
            ),
            dbc.Tab(
                label="Stats",
                tab_id="professional-stats",
                active_label_style={
                    "color": "var(--color-primary)",
                    "font-size": "0.9rem",
                },
                label_class_name="text-base",
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
                    "color": "var(--color-primary)",
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
    return html.Div([])


def create_etl_status_indicator(data_quality_info, team_info):
    """
    Crea un indicador visual del estado del procesamiento ETL.

    Args:
        data_quality_info: Información de calidad de datos
        team_info: Información contextual del equipo

    Returns:
        Componente HTML con indicador de estado ETL
    """
    if not data_quality_info:
        return None

    status = data_quality_info.get("status", "unknown")
    quality_score = data_quality_info.get("quality_score", 0)

    # Determinar color e icono según estado
    if status == "completed":
        color = "#24DE84"
        icon = "bi bi-check-circle-fill"
        status_text = "Processed"
    elif status == "processing":
        color = "#FFA726"
        icon = "bi bi-gear-fill"
        status_text = "Processing"
    elif status == "error":
        color = "#E57373"
        icon = "bi bi-x-circle-fill"
        status_text = "Error"
    else:
        color = "#42A5F5"
        icon = "bi bi-info-circle-fill"
        status_text = "Ready"

    # Casos especiales como David Cuerva
    special_case_note = None
    if team_info and team_info.get("team_status") == "free_agent":
        special_case_note = html.P(
            [
                html.I(className="bi bi-lightbulb me-1 text-warning"),
                "Enhanced handling: Mid-season transfers and free agents processed with contextual logic",
            ],
            className="mb-0 text-xs text-muted",
        )

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H6(
                        [
                            html.I(className=icon, style={"color": color}),
                            f" ETL Status: {status_text}",
                        ],
                        className="mb-2",
                    ),
                    html.P(
                        [
                            (
                                f"Quality Score: {quality_score}/100"
                                if quality_score
                                else "Quality: Not evaluated"
                            ),
                            html.Br(),
                            f"Season: {data_quality_info.get('season', 'Unknown')}",
                        ],
                        className="mb-2 text-muted text-base",
                    ),
                    special_case_note,
                ]
            )
        ],
        style={
            "background-color": "rgba(66, 165, 245, 0.05)",
            "border": f"1px solid {color}",
            "border-radius": "8px",
            "margin-bottom": "15px",
        },
    )


def create_contextual_insights_card(contextual_analysis, team_info):
    """
    Crea una card con insights contextuales del análisis ETL.

    Args:
        contextual_analysis: Resultado del StatsAnalyzer
        team_info: Información del equipo actual

    Returns:
        Componente dbc.Card con insights contextuales
    """
    if not contextual_analysis or not contextual_analysis.get("summary"):
        return None

    summary = contextual_analysis["summary"]
    quality_score = summary.get("quality_assessment", {}).get("data_quality_score", 0)

    # Determinar color del score
    if quality_score >= 80:
        score_color = "#24DE84"  # Verde
        score_icon = "bi bi-check-circle-fill"
    elif quality_score >= 60:
        score_color = "#FFA726"  # Naranja
        score_icon = "bi bi-exclamation-triangle-fill"
    else:
        score_color = "#E57373"  # Rojo
        score_icon = "bi bi-x-circle-fill"

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H6(
                        [html.I(className="bi bi-graph-up me-2"), "Data Insights"],
                        className="text-primary mb-2",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.P(
                                        [
                                            html.I(
                                                className=score_icon,
                                                style={"color": score_color},
                                            ),
                                            f" Quality Score: {quality_score}/100",
                                        ],
                                        className="mb-1 text-base",
                                    ),
                                    html.P(
                                        [
                                            html.I(
                                                className="bi bi-calendar2-check me-1"
                                            ),
                                            f"Seasons Analyzed: {summary.get('data_overview', {}).get('total_records', 0)}",
                                        ],
                                        className="mb-0 text-muted",
                                        style={"font-size": "0.85rem"},
                                    ),
                                ],
                                width=12,
                            )
                        ]
                    ),
                ]
            )
        ],
        style={
            "background-color": "rgba(66, 165, 245, 0.1)",
            "border": "1px solid rgba(66, 165, 245, 0.3)",
            "margin-top": "10px",
        },
    )


def create_team_status_badge(team_info):
    """
    Crea badges contextuales para diferentes estados de equipo.

    Args:
        team_info: Información del equipo procesada por ETL

    Returns:
        Componente Badge o None
    """
    team_status = team_info.get("team_status", "unknown")
    has_transfer = team_info.get("has_transfer", False)
    is_current = team_info.get("is_current_season", False)

    badges = []

    # Badge para casos específicos como David Cuerva
    if team_status == "free_agent" and is_current:
        badges.append(
            dbc.Badge(
                "Season Ended",
                color="warning",
                className="ms-2 text-xs",
            )
        )
    elif team_status == "transferred" and has_transfer:
        badges.append(
            dbc.Badge(
                "Mid-Season Transfer",
                color="info",
                className="ms-2 text-xs",
            )
        )
    elif team_status == "active" and is_current:
        badges.append(
            dbc.Badge(
                "Active",
                color="success",
                className="ms-2 text-xs",
            )
        )

    # Badge ETL para indicar datos procesados
    badges.append(
        dbc.Badge(
            "ETL Processed",
            color="secondary",
            className="ms-2 text-xs",
        )
    )

    return badges if badges else None


def create_team_info_card(team_info):
    """
    Crea una card visual para mostrar información del equipo con logos e indicadores.
    ACTUALIZADA: Integra badges y contexto del nuevo pipeline ETL.

    Args:
        team_info: Diccionario con información del equipo del backend

    Returns:
        Componente dbc.Card con información visual del equipo
    """
    team_display = team_info.get("team_display", "Unknown")
    status_message = team_info.get("status_message", "")
    team_status = team_info.get("team_status", "unknown")
    logo_url = team_info.get("logo_url")
    has_transfer = team_info.get("has_transfer", False)
    is_current_season = team_info.get("is_current_season", False)

    # Definir iconos y colores por estado
    status_config = {
        "active": {
            "icon": "bi bi-check-circle-fill",
            "color": "#24DE84",
            "bg_color": "rgba(36, 222, 132, 0.1)",
            "border_color": "rgba(36, 222, 132, 0.3)",
        },
        "transferred": {
            "icon": "bi bi-arrow-left-right",
            "color": "#FFA726",
            "bg_color": "rgba(255, 167, 38, 0.1)",
            "border_color": "rgba(255, 167, 38, 0.3)",
        },
        "free_agent": {
            "icon": "bi bi-person-dash",
            "color": "#E57373",
            "bg_color": "rgba(229, 115, 115, 0.1)",
            "border_color": "rgba(229, 115, 115, 0.3)",
        },
        "historical": {
            "icon": "bi bi-clock-history",
            "color": "#42A5F5",
            "bg_color": "rgba(66, 165, 245, 0.1)",
            "border_color": "rgba(66, 165, 245, 0.3)",
        },
    }

    config = status_config.get(team_status, status_config["historical"])

    # Badge para temporada actual
    season_badge = None
    if is_current_season:
        season_badge = dbc.Badge(
            "Current Season",
            color="success",
            className="ms-2 text-sm align-middle",
        )

    # Badge para transferencia
    transfer_badge = None
    if has_transfer:
        transfer_badge = dbc.Badge(
            "Transfer",
            color="warning",
            className="ms-2 text-sm align-middle",
        )

    # Contenido del logo
    logo_content = html.Div(
        [
            (
                html.Img(
                    src=logo_url,
                    style={
                        "width": "40px",
                        "height": "40px",
                        "object-fit": "contain",
                        "border-radius": "8px",
                        "background-color": "rgba(255, 255, 255, 0.1)",
                        "padding": "4px",
                    },
                    className="me-3",
                )
                if logo_url
                else html.I(
                    className="bi bi-shield-fill",
                    style={
                        "font-size": "2rem",
                        "color": config["color"],
                        "margin-right": "15px",
                    },
                )
            )
        ]
    )

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [logo_content],
                                width="auto",
                                className="d-flex align-items-center",
                            ),
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className=config["icon"],
                                                        style={
                                                            "color": config["color"],
                                                            "margin-right": "8px",
                                                        },
                                                    ),
                                                    team_display,
                                                    season_badge,
                                                    transfer_badge,
                                                    # NUEVO: Badge para casos especiales como David Cuerva
                                                    dbc.Badge(
                                                        "Enhanced Data",
                                                        color="primary",
                                                        className="ms-2 text-xs",
                                                    ),
                                                ],
                                                className="mb-2",
                                            ),
                                            html.P(
                                                status_message,
                                                className="mb-0 text-muted text-base",
                                            ),
                                            # NUEVO: Información adicional para casos como David Cuerva
                                            (
                                                html.P(
                                                    [
                                                        html.I(
                                                            className="bi bi-info-circle me-1",
                                                            style={
                                                                "color": config["color"]
                                                            },
                                                        ),
                                                        "Processed via modular ETL pipeline",
                                                    ],
                                                    className="mb-0",
                                                    style={
                                                        "font-size": "0.75rem",
                                                        "color": "#888888",
                                                    },
                                                )
                                                if team_info.get("team_status")
                                                == "free_agent"
                                                else None
                                            ),
                                        ]
                                    )
                                ]
                            ),
                        ],
                        className="align-items-center",
                    )
                ]
            )
        ],
        style={
            "background-color": config["bg_color"],
            "border": f"1px solid {config['border_color']}",
            "margin-bottom": "10px",
            "position": "relative",
        },
    )


def create_professional_stats_content(player, user):
    """
    Crea contenido de la tab Stats para jugadores profesionales con sistema de tabs jerárquico.
    Implementa: Hero Section, Performance/Evolution/Position/AI Analytics tabs.

    Args:
        player: Objeto Player
        user: Objeto User

    Returns:
        dbc.Container: Sistema de tabs jerárquico con visualizaciones híbridas PDI+IEP
    """
    try:
        from controllers.db import get_db_session
        from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer
        from models.professional_stats_model import ProfessionalStats

        # Inicializar analyzer
        player_analyzer = PlayerAnalyzer()

        # Obtener estadísticas del jugador para la temporada actual
        player_id = player.player_id
        season = "2024-25"

        # Obtener todas las estadísticas del jugador usando PlayerAnalyzer
        all_stats = player_analyzer.get_player_stats(player_id)

        # Usar todas las temporadas disponibles para análisis temporal completo
        player_stats = all_stats if all_stats else []

        # Obtener la temporada más reciente para referencia
        seasons_available = list(
            set([stat.get("season") for stat in all_stats if stat.get("season")])
        )
        seasons_available.sort(reverse=True)  # Más reciente primero
        actual_season = seasons_available[0] if seasons_available else "2024-25"
        season = actual_season

        if not player_stats:
            return dbc.Container(
                [
                    dbc.Alert(
                        [
                            html.I(className="bi bi-exclamation-triangle me-2"),
                            "No se encontraron estadísticas profesionales para este jugador en las temporadas disponibles.",
                        ],
                        color="warning",
                    )
                ],
                fluid=True,
            )

        return dbc.Container(
            [
                # Main Tabs System
                dbc.Tabs(
                    [
                        dbc.Tab(
                            label="Performance Overview",
                            tab_id="performance-tab",
                            tab_style={"color": "var(--color-white-faded)"},
                        ),
                        dbc.Tab(
                            label="Evolution Analysis",
                            tab_id="evolution-tab",
                            tab_style={"color": "var(--color-white-faded)"},
                        ),
                        dbc.Tab(
                            label="Position Analysis",
                            tab_id="position-tab",
                            tab_style={"color": "var(--color-white-faded)"},
                        ),
                        dbc.Tab(
                            label="AI Analytics",
                            tab_id="ai-analytics-tab",
                            tab_style={"color": "var(--color-white-faded)"},
                        ),
                    ],
                    id="main-stats-tabs",
                    active_tab="performance-tab",
                    className="custom-tabs mb-4",
                ),
                # Dynamic Tab Content
                html.Div(id="main-tab-content", className="tab-content-area"),
                # Data Store for tab switching
                dcc.Store(
                    id="stats-player-data",
                    data={
                        "player_id": player_id,
                        "season": season,
                        "user_id": user.user_id,
                        "player_stats": player_stats if player_stats else [],
                    },
                ),
            ],
            fluid=True,
            className="p-0",
        )

    except Exception as e:
        import traceback

        print(f"Error in create_professional_stats_content: {e}")
        print(traceback.format_exc())
        return dbc.Alert(
            [
                html.I(className="bi bi-exclamation-triangle me-2"),
                f"Error cargando estadísticas profesionales: {str(e)}",
            ],
            color="danger",
        )


def create_sessions_table_dash(
    player_id=None, coach_id=None, from_date=None, to_date=None, status_filter=None
):
    """Crea la tabla de sesiones usando el controller existente - soporta player_id y coach_id"""

    print("🔍 DEBUG Sessions Table Creation:")
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
                        html.Td(format_name_with_del(session_data.get("Coach", ""))),
                        html.Td(format_name_with_del(session_data.get("Player", ""))),
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


# ============================================================================
# ADVANCED PDI + IEP VISUALIZATIONS - Sistema Híbrido
# ============================================================================


def create_pdi_temporal_heatmap(player_id, seasons=None):
    """
    Crea heat map temporal de rendimiento PDI por temporada.
    Visualización avanzada que complementa el gráfico de evolución existente.

    Args:
        player_id: ID del jugador
        seasons: Temporadas a analizar (opcional)

    Returns:
        Componente dcc.Graph con heat map temporal
    """
    try:
        logger.info(f"Creando heat map temporal PDI para jugador {player_id}")

        # Usar PlayerAnalyzer existente
        player_analyzer = PlayerAnalyzer()

        if not seasons:
            seasons = player_analyzer.get_available_seasons_for_player(player_id)

        if not seasons:
            return dbc.Alert(
                "No hay temporadas con datos para heat map temporal", color="warning"
            )

        # Recopilar métricas PDI por temporada
        heatmap_data = []

        for season in seasons:
            try:
                ml_metrics = player_analyzer.calculate_or_update_pdi_metrics(
                    player_id, season, force_recalculate=False
                )

                if ml_metrics:
                    season_metrics = {
                        "Season": season,
                        "PDI Overall": ml_metrics.get("pdi_overall", 0),
                        "Universal": ml_metrics.get("pdi_universal", 0),
                        "Zone": ml_metrics.get("pdi_zone", 0),
                        "Position": ml_metrics.get("pdi_position_specific", 0),
                        "Technical": ml_metrics.get("technical_proficiency", 0),
                        "Tactical": ml_metrics.get("tactical_intelligence", 0),
                        "Physical": ml_metrics.get("physical_performance", 0),
                        "Consistency": ml_metrics.get("consistency_index", 0),
                    }
                    heatmap_data.append(season_metrics)

            except Exception as e:
                logger.error(f"Error procesando temporada {season}: {e}")
                continue

        if not heatmap_data:
            return dbc.Alert(
                "No hay métricas PDI calculadas para heat map", color="warning"
            )

        # Preparar datos para heat map
        import pandas as pd

        df = pd.DataFrame(heatmap_data)
        df.set_index("Season", inplace=True)

        # Normalizar valores para mejor visualización (0-100)
        df_normalized = df.copy()
        for col in df.columns:
            max_val = df[col].max()
            if max_val > 0:
                df_normalized[col] = (df[col] / max_val) * 100

        # Crear heat map
        fig = go.Figure(
            data=go.Heatmap(
                z=df_normalized.values.T,
                x=df_normalized.index,
                y=df_normalized.columns,
                colorscale=[
                    [0, "#E57373"],  # Rojo para valores bajos
                    [0.3, "#FFCA28"],  # Amarillo para valores medios
                    [0.6, "#FFA726"],  # Naranja
                    [1, "#24DE84"],  # Verde Ballers para valores altos
                ],
                hoverongaps=False,
                hovertemplate="<b>%{y}</b><br>"
                + "Season: %{x}<br>"
                + "Score: %{z:.1f}/100<br>"
                + "<extra></extra>",
                colorbar=dict(
                    title=dict(
                        text="Performance Score", font=dict(color="#24DE84", size=12)
                    ),
                    tickfont=dict(color="white"),
                ),
            )
        )

        # Layout del heat map
        fig.update_layout(
            title={
                "text": "Performance Heat Map - Temporal Evolution",
                "x": 0.5,
                "font": {"color": "#24DE84", "size": 18},
            },
            xaxis_title="Season",
            yaxis_title="Performance Metrics",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", family="Inter, sans-serif"),
            height=500,
            margin=dict(l=120, r=80, t=80, b=80),
        )

        # Personalizar ejes
        fig.update_xaxes(
            tickangle=45,
            gridcolor="rgba(255,255,255,0.1)",
            tickfont=dict(color="white", size=10),
        )
        fig.update_yaxes(
            gridcolor="rgba(255,255,255,0.1)", tickfont=dict(color="white", size=10)
        )

        logger.info(f"✅ Heat map temporal creado: {len(heatmap_data)} temporadas")
        return dcc.Graph(figure=fig, className="chart-container")

    except Exception as e:
        logger.error(f"❌ Error creando heat map temporal: {e}")
        return dbc.Alert(f"Error generando heat map: {str(e)}", color="danger")


def create_league_comparative_radar(player_id, season="2024-25", position_filter=True):
    """
    Crea radar chart comparativo vs promedio de liga tailandesa.
    Utiliza datos reales de ProfessionalStats para comparación académica rigurosa.

    Args:
        player_id: ID del jugador
        season: Temporada a analizar
        position_filter: Si filtrar comparación por posición del jugador

    Returns:
        Componente dcc.Graph con radar comparativo
    """
    try:
        logger.info(f"Creando radar comparativo vs liga para jugador {player_id}")

        # Usar PlayerAnalyzer existente
        player_analyzer = PlayerAnalyzer()

        # Obtener métricas del jugador
        player_metrics = player_analyzer.calculate_or_update_pdi_metrics(
            player_id, season, force_recalculate=False
        )

        if not player_metrics:
            return dbc.Alert(
                "No hay métricas del jugador para radar comparativo", color="warning"
            )

        # Obtener posición del jugador
        player_position = player_metrics.get("position_analyzed", "CF")

        # Calcular promedios de liga
        league_averages = _calculate_league_averages(
            player_analyzer, season, player_position if position_filter else None
        )

        if not league_averages:
            return dbc.Alert("No hay datos de liga para comparación", color="warning")

        # Métricas para el radar
        metrics_for_radar = [
            ("Technical", "technical_proficiency"),
            ("Tactical", "tactical_intelligence"),
            ("Physical", "physical_performance"),
            ("Universal", "pdi_universal"),
            ("Zone", "pdi_zone"),
            ("Position", "pdi_position_specific"),
            ("Consistency", "consistency_index"),
            ("Overall PDI", "pdi_overall"),
        ]

        # Preparar datos para radar
        categories = []
        player_values = []
        league_values = []

        for label, metric_key in metrics_for_radar:
            player_val = player_metrics.get(metric_key, 0)
            league_val = league_averages.get(metric_key, 0)

            categories.append(label)
            player_values.append(min(100, max(0, player_val)))  # Clamp 0-100
            league_values.append(min(100, max(0, league_val)))  # Clamp 0-100

        # Cerrar el polígono
        categories_closed = categories + [categories[0]]
        player_values_closed = player_values + [player_values[0]]
        league_values_closed = league_values + [league_values[0]]

        # Crear radar chart
        fig = go.Figure()

        # Promedio de liga (área de referencia)
        fig.add_trace(
            go.Scatterpolar(
                r=league_values_closed,
                theta=categories_closed,
                fill="toself",
                fillcolor="rgba(255, 255, 255, 0.1)",
                line=dict(color="rgba(255, 255, 255, 0.5)", width=2, dash="dot"),
                name=f'Liga Thai {season} ({player_position if position_filter else "All"} Avg)',
                hovertemplate="<b>%{theta}</b><br>"
                + "Liga Avg: %{r:.1f}<br>"
                + "<extra></extra>",
            )
        )

        # Jugador (línea principal)
        fig.add_trace(
            go.Scatterpolar(
                r=player_values_closed,
                theta=categories_closed,
                fill="toself",
                fillcolor="rgba(36, 222, 132, 0.3)",  # Verde Ballers con transparencia
                line=dict(color="#24DE84", width=3),
                name="Player Performance",
                hovertemplate="<b>%{theta}</b><br>"
                + "Player: %{r:.1f}<br>"
                + "<extra></extra>",
            )
        )

        # Layout del radar
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    tickfont=dict(size=10, color="white"),
                    gridcolor="rgba(255, 255, 255, 0.2)",
                ),
                angularaxis=dict(
                    tickfont=dict(size=11, color="white"),
                    gridcolor="rgba(255, 255, 255, 0.2)",
                ),
                bgcolor="rgba(0, 0, 0, 0)",
            ),
            title={
                "text": f"Player vs Thai League Comparison - {season}",
                "x": 0.5,
                "font": {"color": "#24DE84", "size": 16},
            },
            showlegend=True,
            legend=dict(
                bgcolor="rgba(0, 0, 0, 0.8)",
                bordercolor="#24DE84",
                borderwidth=1,
                font=dict(color="white", size=10),
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", family="Inter, sans-serif"),
            height=600,
            margin=dict(l=80, r=80, t=100, b=80),
        )

        logger.info(f"✅ Radar comparativo creado exitosamente")
        return dcc.Graph(figure=fig, className="chart-container")

    except Exception as e:
        logger.error(f"❌ Error creando radar comparativo: {e}")
        return dbc.Alert(f"Error generando radar: {str(e)}", color="danger")


def create_iep_clustering_chart(position="CF", season="2024-25"):
    """
    Crea gráfico IEP (Índice Eficiencia Posicional) con clustering K-means.
    Sistema complementario no supervisado al PDI supervisado.

    Args:
        position: Posición a analizar
        season: Temporada para clustering

    Returns:
        Componente dcc.Graph con clustering IEP
    """
    try:
        logger.info(f"🧮 Creando análisis IEP clustering para {position} en {season}")

        # Importar IEPAnalyzer
        from ml_system.evaluation.analysis.iep_analyzer import IEPAnalyzer

        # Inicializar analizador IEP
        iep_analyzer = IEPAnalyzer()

        # Obtener análisis de clustering para la posición
        cluster_results = iep_analyzer.get_position_cluster_analysis(position, season)

        if "error" in cluster_results:
            error_msg = cluster_results.get("error", "Unknown error")
            if error_msg == "insufficient_data":
                player_count = cluster_results.get("player_count", 0)
                return dbc.Alert(
                    f"Datos insuficientes para clustering {position}: {player_count} jugadores (mínimo 10)",
                    color="warning",
                )
            else:
                return dbc.Alert(
                    f"Error en clustering IEP: {error_msg}", color="danger"
                )

        # Extraer datos para visualización
        players_data = cluster_results["players_data"]
        pca_analysis = cluster_results["pca_analysis"]

        if not players_data:
            return dbc.Alert(
                "No hay datos de jugadores para clustering", color="warning"
            )

        # Preparar datos por cluster
        colors = {
            "Elite Tier": "#24DE84",
            "Strong Tier": "#42A5F5",
            "Average Tier": "#FFCA28",
            "Development Tier": "#FFA726",
        }

        fig = go.Figure()

        # Agregar puntos por cluster
        clusters = {}
        for player in players_data:
            cluster_label = player["cluster_label"]
            if cluster_label not in clusters:
                clusters[cluster_label] = {
                    "x": [],
                    "y": [],
                    "names": [],
                    "iep_scores": [],
                }

            clusters[cluster_label]["x"].append(player["pca_components"][0])
            clusters[cluster_label]["y"].append(player["pca_components"][1])
            clusters[cluster_label]["names"].append(player["player_name"])
            clusters[cluster_label]["iep_scores"].append(player["iep_score"])

        # Añadir trazas por cluster
        for cluster_label, data in clusters.items():
            color = colors.get(cluster_label, "#FFA726")

            fig.add_trace(
                go.Scatter(
                    x=data["x"],
                    y=data["y"],
                    mode="markers",
                    name=cluster_label,
                    marker=dict(
                        size=[
                            max(8, min(20, score / 5)) for score in data["iep_scores"]
                        ],  # Tamaño por IEP
                        color=color,
                        opacity=0.7,
                        line=dict(width=1, color="white"),
                    ),
                    text=[
                        f"{name}<br>IEP: {iep:.1f}"
                        for name, iep in zip(data["names"], data["iep_scores"])
                    ],
                    hovertemplate="<b>%{text}</b><br>"
                    + "PC1: %{x:.2f}<br>"
                    + "PC2: %{y:.2f}<br>"
                    + "<extra></extra>",
                )
            )

        # Layout del gráfico
        pc1_var = (
            pca_analysis["explained_variance_ratio"][0]
            if len(pca_analysis["explained_variance_ratio"]) > 0
            else 0
        )
        pc2_var = (
            pca_analysis["explained_variance_ratio"][1]
            if len(pca_analysis["explained_variance_ratio"]) > 1
            else 0
        )

        fig.update_layout(
            title={
                "text": f"🧮 IEP Analysis - {position} K-means Clustering ({season})",
                "x": 0.5,
                "font": {"color": "#24DE84", "size": 16},
            },
            xaxis_title=f"PC1 - Performance Component ({pc1_var:.1%} variance)",
            yaxis_title=f"PC2 - Style Component ({pc2_var:.1%} variance)",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", family="Inter, sans-serif"),
            height=600,
            showlegend=True,
            legend=dict(
                bgcolor="rgba(0, 0, 0, 0.8)",
                bordercolor="#24DE84",
                borderwidth=1,
                font=dict(color="white", size=10),
            ),
            margin=dict(l=80, r=80, t=100, b=80),
        )

        # Personalizar ejes
        fig.update_xaxes(
            gridcolor="rgba(255, 255, 255, 0.1)",
            zeroline=True,
            zerolinecolor="rgba(255, 255, 255, 0.3)",
            tickfont=dict(color="white"),
        )
        fig.update_yaxes(
            gridcolor="rgba(255, 255, 255, 0.1)",
            zeroline=True,
            zerolinecolor="rgba(255, 255, 255, 0.3)",
            tickfont=dict(color="white"),
        )

        # Añadir información de clustering
        total_players = len(players_data)
        n_clusters = len(clusters)
        total_variance = sum(pca_analysis["explained_variance_ratio"])

        fig.add_annotation(
            text=f"{total_players} players • {n_clusters} clusters<br>"
            f"Total Variance Explained: {total_variance:.1%}",
            xref="paper",
            yref="paper",
            x=0.02,
            y=0.98,
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(0, 0, 0, 0.8)",
            bordercolor="#24DE84",
            borderwidth=1,
            font=dict(size=10, color="white"),
            showarrow=False,
        )

        logger.info(
            f"✅ IEP clustering creado: {total_players} jugadores, {n_clusters} clusters"
        )
        return dcc.Graph(figure=fig, className="chart-container")

    except Exception as e:
        logger.error(f"❌ Error creando IEP clustering: {e}")
        return dbc.Alert(f"Error generando IEP analysis: {str(e)}", color="danger")


# ============================================================================
# FUNCIONES AUXILIARES PARA SISTEMA HÍBRIDO DE TABS
# ============================================================================


def create_performance_tab_content(player_stats):
    """Crea contenido del tab Performance Overview."""
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-radar me-2"
                                                    ),
                                                    "Skills Profile",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [create_radar_chart(player_stats)],
                                        className="p-2",
                                        style={"height": "420px"},
                                    ),
                                ],
                                style={
                                    "background-color": "#2B2B2B",
                                    "border-color": "rgba(36, 222, 132, 0.3)",
                                },
                            )
                        ],
                        width=12,
                        lg=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-grid-3x3-gap me-2"
                                                    ),
                                                    "Performance Heatmap",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [create_performance_heatmap(player_stats)],
                                        className="p-2",
                                        style={"height": "420px"},
                                    ),
                                ],
                                style={
                                    "background-color": "#2B2B2B",
                                    "border-color": "rgba(36, 222, 132, 0.3)",
                                },
                            )
                        ],
                        width=12,
                        lg=6,
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-table me-2"
                                                    ),
                                                    "Statistics Summary",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [create_statistics_summary(player_stats)],
                                        className="p-3",
                                    ),
                                ],
                                style={
                                    "background-color": "#2B2B2B",
                                    "border-color": "rgba(36, 222, 132, 0.3)",
                                },
                            )
                        ],
                        width=12,
                    )
                ],
                className="mt-3",
            ),
        ],
        fluid=True,
    )


def create_evolution_tab_content(player, player_stats, player_analyzer):
    """Crea contenido del tab Evolution Analysis."""
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-graph-up me-2"
                                                    ),
                                                    "Performance Evolution",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
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
                            )
                        ],
                        width=12,
                    )
                ]
            ),
        ],
        fluid=True,
    )


def create_position_tab_content(player_stats):
    """Crea contenido del tab Position Analysis."""
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-bar-chart me-2"
                                                    ),
                                                    "Goals & Assists Comparison",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [create_comparison_bar_chart(player_stats)],
                                        className="p-2",
                                    ),
                                ],
                                style={
                                    "background-color": "#2B2B2B",
                                    "border-color": "rgba(36, 222, 132, 0.3)",
                                },
                            )
                        ],
                        width=12,
                        lg=8,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-list-columns me-2"
                                                    ),
                                                    "Position Metrics",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            # TODO: Implementar métricas específicas por posición
                                            html.P(
                                                "Position-specific metrics will be implemented here",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                            )
                                        ]
                                    ),
                                ],
                                style={
                                    "background-color": "#2B2B2B",
                                    "border-color": "rgba(36, 222, 132, 0.3)",
                                },
                            )
                        ],
                        width=12,
                        lg=4,
                    ),
                ]
            )
        ],
        fluid=True,
    )


def create_ai_analytics_content(player, player_stats):
    """
    Crea contenido del tab AI Analytics con sub-tabs para sistema híbrido.
    Integra las 3 visualizaciones avanzadas: PDI, IEP y League Comparison.
    """
    latest_stats = player_stats[-1] if player_stats else {}
    position = latest_stats.get("primary_position", "CF")
    season = latest_stats.get("season", "2024-25")

    return dbc.Container(
        [
            # Sub-tabs para AI Analytics
            dbc.Tabs(
                [
                    dbc.Tab(
                        [
                            html.I(className="bi bi-arrow-up-right me-2"),
                            "PDI Development",
                        ],
                        tab_id="pdi-development-tab",
                        tab_style={"color": "var(--color-white-faded)"},
                    ),
                    dbc.Tab(
                        [html.I(className="bi bi-diagram-3 me-2"), "IEP Clustering"],
                        tab_id="iep-clustering-tab",
                        tab_style={"color": "var(--color-white-faded)"},
                    ),
                    dbc.Tab(
                        [html.I(className="bi bi-trophy me-2"), "League Comparison"],
                        tab_id="league-comparison-tab",
                        tab_style={"color": "var(--color-white-faded)"},
                    ),
                ],
                id="ai-analytics-sub-tabs",
                active_tab="pdi-development-tab",
                className="mb-4",
            ),
            # Contenido dinámico de sub-tabs
            html.Div(id="ai-sub-tab-content"),
        ],
        fluid=True,
    )


def create_pdi_development_content(player):
    """Crea contenido del sub-tab PDI Development."""
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-graph-up me-2"
                                                    ),
                                                    "PDI Evolution Analysis",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [create_pdi_evolution_chart(player.player_id)],
                                        className="p-2",
                                    ),
                                ],
                                style={
                                    "background-color": "#2B2B2B",
                                    "border-color": "rgba(36, 222, 132, 0.3)",
                                },
                            )
                        ],
                        width=12,
                    )
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H6(
                                                [
                                                    html.I(className="bi bi-grid me-2"),
                                                    "PDI Temporal Heatmap",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [create_pdi_temporal_heatmap(player.player_id)],
                                        className="p-2",
                                    ),
                                ],
                                style={
                                    "background-color": "#2B2B2B",
                                    "border-color": "rgba(36, 222, 132, 0.3)",
                                },
                            )
                        ],
                        width=12,
                        lg=8,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-lightbulb me-2"
                                                    ),
                                                    "Development Insights",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.P(
                                                [
                                                    html.I(
                                                        className="bi bi-robot me-2 text-primary"
                                                    ),
                                                    "PDI Development Analysis",
                                                ],
                                                className="fw-bold mb-2",
                                            ),
                                            html.P(
                                                [
                                                    "• Supervised learning system",
                                                    html.Br(),
                                                    "• Academic rigor with predefined weights",
                                                    html.Br(),
                                                    "• Temporal evolution tracking",
                                                    html.Br(),
                                                    "• Performance trend identification",
                                                ],
                                                className="mb-3 text-base",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                            ),
                                            dbc.Alert(
                                                [
                                                    html.I(
                                                        className="bi bi-info-circle me-2"
                                                    ),
                                                    "PDI provides structured development assessment based on established football analytics methodologies.",
                                                ],
                                                color="info",
                                                className="mb-0",
                                            ),
                                        ]
                                    ),
                                ],
                                style={
                                    "background-color": "#2B2B2B",
                                    "border-color": "rgba(36, 222, 132, 0.3)",
                                },
                            )
                        ],
                        width=12,
                        lg=4,
                    ),
                ],
                className="mt-3",
            ),
        ],
        fluid=True,
    )


def create_iep_clustering_content(player, player_stats):
    """Crea contenido del sub-tab IEP Clustering."""
    # Obtener la temporada más reciente para referencia
    latest_stats = player_stats[-1] if player_stats else {}
    position = latest_stats.get("primary_position", "CF")
    season = latest_stats.get("season", "2024-25")

    # Nota: player_stats contiene todas las temporadas para análisis IEP completo

    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-diagram-3 me-2"
                                                    ),
                                                    "IEP Clustering Analysis",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [create_iep_clustering_chart(position, season)],
                                        className="p-2",
                                    ),
                                ],
                                style={
                                    "background-color": "#2B2B2B",
                                    "border-color": "rgba(36, 222, 132, 0.3)",
                                },
                            )
                        ],
                        width=12,
                        lg=8,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-pie-chart me-2"
                                                    ),
                                                    "Cluster Profile",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.P(
                                                [
                                                    html.I(
                                                        className="bi bi-diagram-3 me-2 text-primary"
                                                    ),
                                                    f"Position: {position}",
                                                ],
                                                className="fw-bold mb-2",
                                            ),
                                            html.P(
                                                [
                                                    html.I(
                                                        className="bi bi-calendar-date me-2 text-primary"
                                                    ),
                                                    f"Season: {season}",
                                                ],
                                                className="fw-bold mb-3",
                                            ),
                                            html.P(
                                                [
                                                    "• Unsupervised K-means clustering",
                                                    html.Br(),
                                                    "• Natural efficiency patterns",
                                                    html.Br(),
                                                    "• PCA dimensionality reduction",
                                                    html.Br(),
                                                    "• Position-specific tiers",
                                                ],
                                                className="mb-3 text-base",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                            ),
                                            dbc.Alert(
                                                [
                                                    html.I(
                                                        className="bi bi-info-circle me-2"
                                                    ),
                                                    "IEP discovers natural performance groups without predefined labels.",
                                                ],
                                                color="info",
                                                className="mb-0",
                                            ),
                                        ]
                                    ),
                                ],
                                style={
                                    "background-color": "#2B2B2B",
                                    "border-color": "rgba(36, 222, 132, 0.3)",
                                },
                            )
                        ],
                        width=12,
                        lg=4,
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H6(
                                                [
                                                    html.I(className="bi bi-gear me-2"),
                                                    "Efficiency Recommendations",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.P(
                                                [
                                                    html.I(
                                                        className="bi bi-cpu me-2 text-warning"
                                                    ),
                                                    "Machine Learning Insights",
                                                ],
                                                className="fw-bold mb-2",
                                            ),
                                            html.P(
                                                [
                                                    "Based on unsupervised analysis of positional efficiency patterns, "
                                                    "this system identifies natural performance clusters and provides "
                                                    "data-driven recommendations for player development."
                                                ],
                                                className="text-base",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                            ),
                                        ]
                                    ),
                                ],
                                style={
                                    "background-color": "#2B2B2B",
                                    "border-color": "rgba(36, 222, 132, 0.3)",
                                },
                            )
                        ],
                        width=12,
                    )
                ],
                className="mt-3",
            ),
        ],
        fluid=True,
    )


def create_league_comparison_content(player, player_stats):
    """Crea contenido del sub-tab League Comparison."""
    latest_stats = player_stats[-1] if player_stats else {}
    season = latest_stats.get("season", "2024-25")

    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-radar me-2"
                                                    ),
                                                    "League Comparative Radar",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            create_league_comparative_radar(
                                                player.player_id, season
                                            )
                                        ],
                                        className="p-2",
                                    ),
                                ],
                                style={
                                    "background-color": "#2B2B2B",
                                    "border-color": "rgba(36, 222, 132, 0.3)",
                                },
                            )
                        ],
                        width=12,
                        lg=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-trophy me-2"
                                                    ),
                                                    "League Position",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.P(
                                                [
                                                    html.I(
                                                        className="bi bi-globe me-2 text-primary"
                                                    ),
                                                    "Thai League Analysis",
                                                ],
                                                className="fw-bold mb-2",
                                            ),
                                            html.P(
                                                [
                                                    "• Real data comparison vs league averages",
                                                    html.Br(),
                                                    "• Position-specific benchmarking",
                                                    html.Br(),
                                                    "• Academic rigor in methodology",
                                                    html.Br(),
                                                    "• Statistical significance testing",
                                                ],
                                                className="mb-3 text-base",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                            ),
                                            dbc.Alert(
                                                [
                                                    html.I(
                                                        className="bi bi-info-circle me-2"
                                                    ),
                                                    "Based on real Thai League professional statistics from multiple seasons.",
                                                ],
                                                color="info",
                                                className="mb-0",
                                            ),
                                        ]
                                    ),
                                ],
                                style={
                                    "background-color": "#2B2B2B",
                                    "border-color": "rgba(36, 222, 132, 0.3)",
                                },
                            )
                        ],
                        width=12,
                        lg=6,
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-bar-chart me-2"
                                                    ),
                                                    "Percentile Rankings",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            # TODO: Implementar tabla de percentiles
                                            html.P(
                                                "Percentile rankings table will be implemented here",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                            )
                                        ]
                                    ),
                                ],
                                style={
                                    "background-color": "#2B2B2B",
                                    "border-color": "rgba(36, 222, 132, 0.3)",
                                },
                            )
                        ],
                        width=12,
                    )
                ],
                className="mt-3",
            ),
        ],
        fluid=True,
    )


# ============================================================================
# FUNCIONES AUXILIARES PARA VISUALIZACIONES
# ============================================================================


def _calculate_league_averages(player_analyzer, season, position=None):
    """Calcula promedios de liga para comparación radar."""
    try:
        from controllers.db import get_db_session
        from models.professional_stats_model import ProfessionalStats

        with get_db_session() as session:
            query = session.query(ProfessionalStats).filter(
                ProfessionalStats.season == season
            )

            if position:
                query = query.filter(ProfessionalStats.primary_position == position)

            stats_data = query.all()

            if not stats_data:
                return {}

            # Calcular métricas PDI promedio
            from ml_system.evaluation.metrics.pdi_calculator import PDICalculator

            pdi_calculator = PDICalculator()

            total_metrics = {
                "pdi_overall": 0,
                "pdi_universal": 0,
                "pdi_zone": 0,
                "pdi_position_specific": 0,
                "technical_proficiency": 0,
                "tactical_intelligence": 0,
                "physical_performance": 0,
                "consistency_index": 0,
            }

            valid_calculations = 0

            for stat in stats_data:
                try:
                    stat_dict = {
                        column.name: getattr(stat, column.name)
                        for column in stat.__table__.columns
                    }
                    pdi_result = pdi_calculator.calculate_comprehensive_pdi(stat_dict)

                    if pdi_result:
                        for key in total_metrics:
                            if key in pdi_result:
                                total_metrics[key] += pdi_result[key]
                        valid_calculations += 1

                except Exception as e:
                    logger.debug(f"Error calculando PDI para promedio: {e}")
                    continue

            # Calcular promedios
            if valid_calculations > 0:
                averages = {
                    key: total / valid_calculations
                    for key, total in total_metrics.items()
                }
                logger.info(
                    f"✅ Promedios calculados: {valid_calculations} jugadores válidos"
                )
                return averages

            return {}

    except Exception as e:
        logger.error(f"Error calculando promedios de liga: {e}")
        return {}


if __name__ == "__main__":
    # Para testing
    pass

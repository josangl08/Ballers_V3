# pages/ballers_dash.py - Migración visual de ballers.py a Dash
from __future__ import annotations

import base64
import datetime
import difflib
import logging
import os
import re

import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
import requests
from dash import Input, Output, State, dcc, html  # noqa: F401

from common.components.charts.comparison_charts import (
    create_comparison_bar_chart,
    create_efficiency_metrics_chart,
    create_iep_clustering_chart,
)

# Component Imports - Modular Architecture
from common.components.charts.evolution_charts import (
    create_evolution_chart,
    create_pdi_evolution_chart,
)
from common.components.charts.performance_charts import (
    create_pdi_temporal_heatmap,
    create_performance_heatmap,
)
from common.components.charts.radar_charts import (
    create_league_comparative_radar,
    create_ml_enhanced_radar_chart,
    create_radar_chart,
)
from common.components.shared.alerts import (
    create_error_alert,
    create_loading_alert,
    create_no_data_alert,
    create_success_alert,
    create_warning_alert,
)
from common.components.shared.cards import (
    create_comparison_card,
    create_info_card,
    create_metric_card,
    create_stats_card,
)
from common.components.shared.tables import create_statistics_summary
from common.datepicker_utils import create_auto_hide_datepicker
from common.format_utils import format_name_with_del
from common.notification_component import NotificationComponent
from controllers.player_controller import get_player_profile_data, get_players_for_list
from ml_system.data_processing.processors.position_mapper import (
    get_group_info,
    map_position,
)

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
        logger.error(f"Error descargando logo para {team_name}: {e}")
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
        logger.error(f"Error converting logo to base64: {e}")
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


# Función create_evolution_chart movida a common/components/charts/evolution_charts.py


# Función create_radar_chart movida a common/components/charts/radar_charts.py


# Función create_performance_heatmap movida a common/components/charts/performance_charts.py


# Función create_statistics_summary movida a common/components/shared/tables.py


def get_player_position_group_8_from_bd(player_id):
    """Obtiene el grupo posicional específico (8 grupos) del jugador desde BD"""
    try:
        from controllers.db import get_db_session
        from models.player_model import Player
        from models.professional_stats_model import ProfessionalStats

        with get_db_session() as session:
            player_record = (
                session.query(Player).filter(Player.player_id == player_id).first()
            )
            if player_record and player_record.is_professional:
                # Obtener posición más reciente
                latest_stats = (
                    session.query(ProfessionalStats)
                    .filter(ProfessionalStats.player_id == player_id)
                    .order_by(ProfessionalStats.season.desc())
                    .first()
                )

                if latest_stats and latest_stats.primary_position:
                    # REUTILIZAR el mapeo existente de position_analyzer (8 grupos)
                    from ml_system.evaluation.analysis.position_analyzer import (
                        PositionAnalyzer,
                    )

                    analyzer = PositionAnalyzer()
                    mapped_group = analyzer.position_mapping.get(
                        latest_stats.primary_position
                    )
                    logger.info(
                        f"Jugador {player_id}: {latest_stats.primary_position} → {mapped_group}"
                    )
                    return mapped_group
    except Exception as e:
        logger.error(
            f"Error obteniendo posición 8-grupos para jugador {player_id}: {e}"
        )
    return None


def get_player_full_name_from_bd(player_id):
    """Obtiene el nombre completo del jugador desde BD (ProfessionalStats.full_name)"""
    try:
        from controllers.db import get_db_session
        from models.player_model import Player
        from models.professional_stats_model import ProfessionalStats

        with get_db_session() as session:
            player_record = (
                session.query(Player).filter(Player.player_id == player_id).first()
            )
            if player_record and player_record.is_professional:
                # Obtener stats más recientes para nombre completo
                latest_stats = (
                    session.query(ProfessionalStats)
                    .filter(ProfessionalStats.player_id == player_id)
                    .order_by(ProfessionalStats.season.desc())
                    .first()
                )

                if latest_stats and latest_stats.full_name:
                    logger.info(
                        f"Jugador {player_id} full_name: {latest_stats.full_name}"
                    )
                    return latest_stats.full_name
    except Exception as e:
        logger.error(f"Error obteniendo nombre completo para jugador {player_id}: {e}")
    return None


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


# FUNCIÓN ELIMINADA: create_pdi_evolution_chart()
# RAZÓN: Función duplicada eliminada para usar la implementación superior
# UBICACIÓN: common/components/charts/evolution_charts.py (ya importada en línea 25)
# VENTAJA: Automáticamente usa la versión con colores corregidos y leyenda horizontal


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
            # Sistema de notificaciones (toast) para Ballers
            *NotificationComponent.create_toast_notification("ballers"),
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
                                    *create_auto_hide_datepicker(
                                        "ballers-filter-from-date",
                                        value=(
                                            datetime.date.today()
                                            - datetime.timedelta(days=7)
                                        ).isoformat(),
                                        placeholder="From date",
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
                                    *create_auto_hide_datepicker(
                                        "ballers-filter-to-date",
                                        value=(
                                            datetime.date.today()
                                            + datetime.timedelta(days=21)
                                        ).isoformat(),
                                        placeholder="To date",
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
                                style={"font-weight": "500", "color": "#FFFFFF"},
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


def create_iep_clustering_chart(
    position_or_group="CF", season="2024-25", current_player_id=None
):
    """
    Crea gráfico IEP (Índice Eficiencia Posicional) con clustering K-means.
    Sistema complementario no supervisado al PDI supervisado.

    Args:
        position_or_group: Posición específica o grupo de posiciones a analizar
        season: Temporada para clustering
        current_player_id: ID del jugador actual para destacar

    Returns:
        Componente dcc.Graph con clustering IEP
    """
    # Mapping de títulos para los 8 grupos específicos (usado en múltiples lugares)
    group_titles_8 = {
        "GK": "Goalkeepers",
        "CB": "Center Backs",
        "FB": "Full Backs",
        "DMF": "Defensive Midfielders",
        "CMF": "Central Midfielders",
        "AMF": "Attacking Midfielders",
        "W": "Wingers",
        "CF": "Center Forwards",
    }

    try:
        # Crear análisis IEP clustering

        # Determinar título según si es grupo de 8, grupo de 4, o posición específica
        if position_or_group in group_titles_8:
            analysis_title = group_titles_8[position_or_group]
        elif position_or_group in ["GK", "DEF", "MID", "FWD"]:
            group_info = get_group_info(position_or_group)
            analysis_title = group_info["name"] if group_info else position_or_group
        else:
            analysis_title = f"{position_or_group} Position"

        logger.info(
            f"🧮 Creando análisis IEP clustering para {position_or_group} en {season}"
        )

        # Importar IEPAnalyzer
        from ml_system.evaluation.analysis.iep_analyzer import IEPAnalyzer

        # Inicializar analizador IEP
        iep_analyzer = IEPAnalyzer()

        # Obtener análisis de clustering para la posición o grupo
        cluster_results = iep_analyzer.get_position_cluster_analysis(
            position_or_group, season, current_player_id=current_player_id
        )

        if "error" in cluster_results:
            error_msg = cluster_results.get("error", "Unknown error")
            if error_msg == "insufficient_data":
                player_count = cluster_results.get("player_count", 0)
                return dbc.Alert(
                    f"Datos insuficientes para clustering {analysis_title}: {player_count} jugadores (mínimo 10)",
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

        # Preparar datos por cluster (orden mejor->peor)
        # Orden específico para la leyenda: Elite, Strong, Average, Development
        cluster_order = [
            "Elite Tier",
            "Strong Tier",
            "Average Tier",
            "Development Tier",
        ]
        colors = {
            "Elite Tier": "#4CAF50",  # Verde - Mejor
            "Strong Tier": "#2196F3",  # Azul
            "Average Tier": "#FF9800",  # Amarillo
            "Development Tier": "#F44336",  # Rojo - Peor
        }

        # Los tamaños se basarán en IEP score individual (restaurado)

        fig = go.Figure()

        # Agregar puntos por cluster
        clusters = {}
        current_player_data = None

        # Función helper para obtener nombre exacto del jugador en CSV
        def get_csv_player_name_by_bd_id(player_id):
            """Obtiene el nombre exacto del jugador como aparece en CSV usando wyscout_id con búsqueda multi-temporada."""
            if not player_id:
                return None

            try:
                from controllers.csv_stats_controller import CSVStatsController
                from controllers.db import get_db_session
                from models.player_model import Player

                with get_db_session() as session:
                    player_record = (
                        session.query(Player)
                        .filter(Player.player_id == player_id)
                        .first()
                    )

                    if player_record and player_record.wyscout_id:
                        csv_controller = CSVStatsController()
                        available_seasons = csv_controller.get_available_seasons_list()

                        # Buscar en cada temporada empezando por la más reciente
                        for season in sorted(available_seasons, reverse=True):
                            df = csv_controller._load_season_data(season)

                            if df is not None and "Wyscout id" in df.columns:
                                bd_id = player_record.wyscout_id

                                # Buscar jugador por wyscout_id con fallbacks
                                csv_match = df[df["Wyscout id"] == bd_id]

                                # Fallback: intentar conversión de tipos si no se encuentra
                                if len(csv_match) == 0:
                                    try:
                                        csv_match = df[
                                            df["Wyscout id"].astype(int) == int(bd_id)
                                        ]
                                    except:
                                        try:
                                            csv_match = df[
                                                df["Wyscout id"].isin([bd_id])
                                            ]
                                        except:
                                            pass

                                if len(csv_match) > 0:
                                    # Usar 'Player' (abreviado) para matching exacto con datos de clustering
                                    player_name = csv_match.iloc[0].get(
                                        "Player",
                                        csv_match.iloc[0].get("Full name", "Unknown"),
                                    )
                                    return player_name

                        logger.warning(
                            f"❌ Jugador con wyscout_id {player_record.wyscout_id} no encontrado en ninguna temporada"
                        )

            except Exception as e:
                logger.error(
                    f"❌ Error obteniendo nombre CSV del jugador {player_id}: {e}"
                )

            return None

        # Obtener información básica del jugador actual
        current_player_csv_name = get_csv_player_name_by_bd_id(
            current_player_id
        )  # Nombre abreviado del CSV
        current_player_full_name = get_player_full_name_from_bd(
            current_player_id
        )  # Nombre completo de BD
        current_player_name = None
        current_player_position = None
        current_player_matches = 0
        current_player_minutes = 0

        if current_player_id:
            try:
                from controllers.db import get_db_session
                from models.player_model import Player
                from models.professional_stats_model import ProfessionalStats

                with get_db_session() as session:
                    player_record = (
                        session.query(Player)
                        .filter(Player.player_id == current_player_id)
                        .first()
                    )
                    if player_record:
                        current_player_name = player_record.user.name

                        # Obtener posición más reciente del jugador
                        latest_stats = (
                            session.query(ProfessionalStats)
                            .filter(ProfessionalStats.player_id == current_player_id)
                            .order_by(ProfessionalStats.season.desc())
                            .first()
                        )

                        if latest_stats:
                            current_player_position = latest_stats.primary_position
                            # Obtener información adicional para mensaje informativo
                            current_player_matches = latest_stats.matches_played or 0
                            current_player_minutes = latest_stats.minutes_played or 0

                            logger.info(f"🎯 Jugador actual: {current_player_name}")
                            logger.info(
                                f"   Partidos: {current_player_matches}, Minutos: {current_player_minutes}"
                            )
                        else:
                            current_player_matches = 0
                            current_player_minutes = 0
            except Exception as e:
                logger.error(f"Error obteniendo información del jugador: {e}")

        for i, player in enumerate(players_data):
            cluster_label = player["cluster_label"]
            if cluster_label not in clusters:
                clusters[cluster_label] = {
                    "x": [],
                    "y": [],
                    "names": [],
                    "iep_scores": [],
                    "player_ids": [],
                }

            clusters[cluster_label]["x"].append(player["pca_components"][0])
            clusters[cluster_label]["y"].append(player["pca_components"][1])
            clusters[cluster_label]["names"].append(player["player_name"])
            clusters[cluster_label]["iep_scores"].append(player["iep_score"])
            clusters[cluster_label]["player_ids"].append(player.get("player_id"))

            # Identificar jugador actual usando matching híbrido (nombre abreviado O completo)
            player_matches = False
            match_type = ""

            # Obtener nombre del clustering (sin equipo)
            cluster_player_name = player.get("player_name", "")
            if cluster_player_name and "(" in cluster_player_name:
                cluster_name_only = cluster_player_name.split("(")[0].strip()
            else:
                cluster_name_only = cluster_player_name.strip()

            # MATCHING HÍBRIDO: Probar nombre abreviado Y completo
            if (
                current_player_csv_name
                and current_player_csv_name.strip().lower() == cluster_name_only.lower()
            ):
                player_matches = True
                match_type = "abbreviated"
            elif (
                current_player_full_name
                and current_player_full_name.strip().lower()
                == cluster_name_only.lower()
            ):
                player_matches = True
                match_type = "full_name"

            if player_matches:
                current_player_data = {
                    "x": player["pca_components"][0],
                    "y": player["pca_components"][1],
                    "name": player["player_name"],
                    "team": player.get("team", "Unknown Team"),
                    "iep_score": player["iep_score"],
                    "cluster": cluster_label,
                }

        # Añadir trazas por cluster en orden específico para la leyenda
        for cluster_label in cluster_order:
            if cluster_label not in clusters:
                continue
            data = clusters[cluster_label]
            color = colors.get(cluster_label, "#FFA726")

            fig.add_trace(
                go.Scatter(
                    x=data["x"],
                    y=data["y"],
                    mode="markers",
                    name=cluster_label.replace(" Tier", ""),
                    marker=dict(
                        size=[
                            max(8, min(20, score / 5)) for score in data["iep_scores"]
                        ],  # Tamaño proporcional al IEP score
                        color=color,
                        opacity=0.7,
                        line=dict(width=1, color="white"),
                    ),
                    text=[
                        f"{name}<br>IEP: {iep:.1f}"
                        for name, iep in zip(data["names"], data["iep_scores"])
                    ],
                    hovertemplate="<b>%{text}</b><br>"
                    + "Performance Level: %{x:.2f}<br>"
                    + "Playing Style: %{y:.2f}<br>"
                    + "<extra></extra>",
                )
            )

        # Destacar jugador actual si existe
        if current_player_data:
            # Tamaño original basado en IEP (sin extra)
            player_size = max(8, min(20, current_player_data["iep_score"] / 5))

            fig.add_trace(
                go.Scatter(
                    x=[current_player_data["x"]],
                    y=[current_player_data["y"]],
                    mode="markers",
                    name=f"{current_player_name or 'Current Player'}",  # Usar nombre real del usuario desde BD
                    marker=dict(
                        size=player_size,
                        color="#8B5CF6",  # Color morado (purple-500)
                        opacity=0.9,
                        line=dict(
                            width=5, color="#EF4444"
                        ),  # Borde rojo vibrante (red-500)
                        symbol="circle",  # Círculo para consistencia visual
                    ),
                    text=[
                        f"{current_player_name or current_player_data.get('name', 'Current Player')} ({current_player_data.get('team', 'Unknown Team')})<br>IEP: {current_player_data['iep_score']:.1f}"
                    ],
                    hovertemplate="<b>%{text}</b><br>"
                    + "Performance Level: %{x:.2f}<br>"
                    + "Playing Style: %{y:.2f}<br>"
                    + "<extra></extra>",
                    showlegend=True,  # SÍ mostrar en leyenda
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

        # Crear título simplificado con mensaje informativo si el jugador tiene pocos partidos
        chart_title = analysis_title
        if (
            current_player_id
            and current_player_data
            and (current_player_matches < 5 or current_player_minutes < 500)
        ):
            chart_title += f"<br><span style='color:#FFA500; font-size:12px'>⚠️ Current player: {current_player_matches} matches, {current_player_minutes} minutes (limited data)</span>"

        fig.update_layout(
            xaxis_title=f"PC1 - Performance Level: goals, assists, accuracy ({pc1_var:.1%} variance)",
            yaxis_title=f"PC2 - Playing Style: role, positioning behavior ({pc2_var:.1%} variance)",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", family="Inter, sans-serif"),
            height=600,  # Altura normal
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=1.12,  # Encima del gráfico, con separación del título
                xanchor="right",
                x=1.0,  # Alineado con borde derecho del gráfico
                bgcolor="rgba(0, 0, 0, 0.8)",
                bordercolor="#24DE84",
                borderwidth=1,
                font=dict(color="white", size=10),
                orientation="h",  # Horizontal para mejor aprovechamiento del espacio
            ),
            margin=dict(
                l=70, r=30, t=120, b=50
            ),  # Márgenes optimizados para mejor aprovechamiento
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

        # Información de clustering: izquierda encima del gráfico, alineada con borde izquierdo
        fig.add_annotation(
            text=f"{total_players} players • {n_clusters} clusters<br>"
            f"Total Variance Explained: {total_variance:.1%}",
            xref="paper",
            yref="paper",
            x=0.0,  # Extremo izquierdo del gráfico
            y=1.12,  # Misma altura que la leyenda de tiers, posición final
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(0, 0, 0, 0.8)",
            bordercolor="#24DE84",
            borderwidth=1,
            font=dict(size=10, color="white"),
            showarrow=False,
        )

        # Agregar mensaje informativo si el jugador no está en los datos
        if not current_player_data and current_player_id:
            info_message = f"Current player not shown"

            # Mensajes específicos para grupos vs posiciones
            if current_player_position:
                # Para los 8 grupos específicos
                if position_or_group in [
                    "GK",
                    "CB",
                    "FB",
                    "DMF",
                    "CMF",
                    "AMF",
                    "W",
                    "CF",
                ]:
                    # Obtener grupo del jugador usando sistema de 8 grupos
                    player_group_8 = (
                        get_player_position_group_8_from_bd(current_player_id)
                        if current_player_id
                        else None
                    )
                    if player_group_8 and player_group_8 != position_or_group:
                        analysis_title_current = group_titles_8.get(
                            position_or_group, position_or_group
                        )
                        player_title = group_titles_8.get(
                            player_group_8, player_group_8
                        )
                        info_message += f"<br>({current_player_name} is {player_title}, showing {analysis_title_current} analysis)"
                    elif current_player_name:
                        info_message += (
                            f"<br>({current_player_name} not found in Thai League data)"
                        )
                # Para los 4 grupos tradicionales
                elif position_or_group in ["GK", "DEF", "MID", "FWD"]:
                    player_group = map_position(current_player_position)
                    if player_group != position_or_group:
                        group_info = get_group_info(position_or_group)
                        group_name = (
                            group_info["name"] if group_info else position_or_group
                        )
                        player_group_info = get_group_info(player_group)
                        player_group_name = (
                            player_group_info["name"]
                            if player_group_info
                            else player_group
                        )
                        info_message += f"<br>({current_player_name} is {player_group_name}, showing {group_name} analysis)"
                    elif current_player_name:
                        info_message += (
                            f"<br>({current_player_name} not found in Thai League data)"
                        )
            elif (
                current_player_position and current_player_position != position_or_group
            ):
                info_message += f"<br>(Position mismatch: {current_player_position} vs {position_or_group})"
            elif current_player_name:
                info_message += (
                    f"<br>({current_player_name} not found in Thai League data)"
                )

            fig.add_annotation(
                text=info_message,
                xref="paper",
                yref="paper",
                x=0.5,  # Centro del gráfico
                y=1.02,  # Justo encima del gráfico
                xanchor="center",
                yanchor="bottom",
                bgcolor="rgba(255, 165, 0, 0.8)",  # Color naranja para advertencia
                bordercolor="#FF8C00",
                borderwidth=1,
                font=dict(size=9, color="black"),
                showarrow=False,
            )

        # Añadir título como anotación posicionada para evitar superposición
        fig.add_annotation(
            text=chart_title,
            xref="paper",
            yref="paper",
            x=0.5,  # Centrado horizontalmente
            y=1.22,  # Posicionado arriba de las leyendas (y=1.12)
            xanchor="center",
            yanchor="middle",
            font=dict(color="#24DE84", size=16),
            showarrow=False,
        )

        logger.info(
            f"✅ IEP clustering creado: {total_players} jugadores, {n_clusters} clusters"
        )
        return dcc.Graph(
            figure=fig, className="chart-container", config={"displayModeBar": False}
        )

    except Exception as e:
        logger.error(f"❌ Error creando IEP clustering: {e}")
        return dbc.Alert(f"Error generando IEP analysis: {str(e)}", color="danger")


# ============================================================================
# FUNCIONES AUXILIARES PARA SISTEMA HÍBRIDO DE TABS
# ============================================================================


def create_performance_tab_content(player_id: int, season: str, player_stats: list):
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
                                                    "Hierarchical PDI Profile",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [create_radar_chart(player_id, season)],
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
    """
    Crea contenido del tab Evolution Analysis con layout vertical.

    NUEVA ESTRUCTURA: Statistics + PDI Development + PDI Heatmap
    CONSERVADOR: Reutiliza funciones existentes completas
    """
    return dbc.Container(
        [
            # GRÁFICO 1: Evolution Chart existente (INTOCABLE - team logos preserved)
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
                                                    "Statistical and Team Evolution",
                                                ],
                                                className="mb-0",
                                                style={"color": "#24DE84"},
                                            ),
                                            html.P(
                                                "Team progression with statistical metrics evolution",
                                                className="mb-0 small",
                                                style={"color": "#42A5F5"},
                                            ),
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            create_evolution_chart(
                                                player_stats
                                            )  # EXISTING - team logos preserved
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
                    )
                ],
                className="mb-4",
            ),
            # Separador visual elegante
            html.Hr(
                className="my-4", style={"border-color": "rgba(36, 222, 132, 0.3)"}
            ),
            # GRÁFICO 2: PDI Evolution (TRASLADADO desde AI Analytics)
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
                                                        className="bi bi-graph-up-arrow me-2"
                                                    ),
                                                    "Player Development Index (PDI)",
                                                ],
                                                className="mb-0",
                                                style={"color": "#24DE84"},
                                            ),
                                            html.P(
                                                "Scientific development index with 4 components",
                                                className="mb-0 small",
                                                style={"color": "#42A5F5"},
                                            ),
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            create_pdi_evolution_chart(
                                                player.player_id
                                            )  # EXISTING - 4 lines rich
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
                    )
                ],
                className="mb-4",
            ),
            # Explicación interpretativa del gráfico PDI
            dbc.Row(
                [dbc.Col([create_pdi_explanation_card()], width=12)], className="mb-4"
            ),
            # Separador visual elegante
            html.Hr(
                className="my-4", style={"border-color": "rgba(36, 222, 132, 0.3)"}
            ),
            # GRÁFICO 3: PDI Heatmap (TRASLADADO desde AI Analytics)
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
                                                        className="bi bi-grid-3x3-gap me-2"
                                                    ),
                                                    "Player Development Index Heatmap",
                                                ],
                                                className="mb-0",
                                                style={"color": "#24DE84"},
                                            ),
                                            html.P(
                                                "Temporal analysis of PDI components strengths/weaknesses",
                                                className="mb-0 small",
                                                style={"color": "#42A5F5"},
                                            ),
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            create_pdi_temporal_heatmap(
                                                player.player_id
                                            )  # EXISTING - complete
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
                    )
                ]
            ),
            # Separador visual elegante
            html.Hr(
                className="my-4", style={"border-color": "rgba(36, 222, 132, 0.3)"}
            ),
            # NUEVA SECCIÓN: Development Roadmap (TRASLADADO desde AI Analytics)
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
                                                    html.I(className="bi bi-map me-2"),
                                                    "Development Roadmap & Recommendations",
                                                ],
                                                className="mb-0",
                                                style={"color": "#24DE84"},
                                            ),
                                            html.P(
                                                "AI-driven development plan based on current PDI analysis",
                                                className="mb-0 small",
                                                style={"color": "#42A5F5"},
                                            ),
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            create_development_roadmap_content(
                                                player, player_stats
                                            )  # EXISTING function - complete roadmap
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
                    )
                ],
                style={"display": "none"}  # OCULTAR: Development Roadmap & Recommendations
            ),
        ],
        fluid=True,
    )


def create_position_tab_content(player, player_stats):
    """Crea contenido del tab Position Analysis con análisis específico por posición."""
    if not player_stats:
        return create_no_data_alert(
            "estadísticas del jugador",
            "Seleccione un jugador con estadísticas profesionales",
        )

    # Obtener información del jugador y posición para temporada actual (2024-25)
    current_season = "2024-25"

    # Buscar estadísticas específicas para la temporada actual
    current_stats = None
    for stat in player_stats:
        if stat.get("season") == current_season:
            current_stats = stat
            break

    # Si no hay datos para temporada actual, usar los más recientes
    if not current_stats:
        current_stats = player_stats[-1] if player_stats else {}
        current_season = current_stats.get("season", "2024-25")

    position = current_stats.get("primary_position", "CF")
    player_id = getattr(player, "player_id", None)
    season = current_season

    # Verificar si tenemos player_id
    if not player_id:
        return create_error_alert(
            "No se puede realizar el análisis posicional sin ID del jugador",
            "Error de Datos",
        )

    try:
        # Debug logging
        logger.info(
            f"Iniciando análisis posicional - Player ID: {player_id}, Position: {position}, Season: {season}"
        )

        # Use direct position analysis with integrated table and insights
        from common.components.professional_stats.position_components import (
            create_position_analysis_components_simplified,
        )

        # Call simplified position analysis with direct integration
        return dbc.Container(
            [
                create_position_analysis_components_simplified(
                    player_id=player_id,
                    season=season,
                    reference="league",  # Default reference
                )
            ],
            fluid=True,
        )

    except Exception as e:
        logger.error(f"Error creando análisis posicional: {e}")
        return create_error_alert(
            f"Error al generar el análisis posicional: {str(e)}", "Error del Sistema"
        )


def create_development_roadmap_content(player, player_stats):

    # Debug: verificar datos recibidos
    try:
        player_name = (
            player.user.name if hasattr(player, "user") and player.user else "Unknown"
        )
    except Exception as e:
        player_name = f"Unknown (error: {e})"

    # Obtener la temporada más reciente para referencia
    latest_stats = player_stats[-1] if player_stats else {}
    season = latest_stats.get("season", "2024-25")

    # Fallback robusto: Si player_stats está vacío, consultar BD directamente
    if not player_stats and player.player_id:
        try:
            from controllers.db import get_db_session
            from models.professional_stats_model import ProfessionalStats

            with get_db_session() as session:
                latest_bd_stats = (
                    session.query(ProfessionalStats)
                    .filter(ProfessionalStats.player_id == player.player_id)
                    .order_by(ProfessionalStats.season.desc())
                    .first()
                )

                if latest_bd_stats:
                    season = latest_bd_stats.season
                else:
                    logger.warning(
                        f"No se encontraron stats en BD para player {player.player_id}"
                    )
        except Exception as e:
            logger.error(f"Error en fallback BD: {e}")

    # Obtener posición con fallbacks inteligentes
    position = latest_stats.get("primary_position")

    # Si no hay posición en stats, intentar obtener de la BD
    if not position:
        try:
            from controllers.db import get_db_session
            from models.professional_stats_model import ProfessionalStats

            with get_db_session() as session:
                latest_db_stats = (
                    session.query(ProfessionalStats)
                    .filter(ProfessionalStats.player_id == player.player_id)
                    .order_by(ProfessionalStats.season.desc())
                    .first()
                )

                if latest_db_stats:
                    position = latest_db_stats.primary_position
        except Exception as e:
            logger.warning(f"Error obteniendo posición de BD: {e}")

    # Fallback final a posición neutral (MID es más común que CF)
    if not position:
        position = "CMF"  # Centro medio, mapea a MID
        logger.info(f"Usando posición fallback CMF para clustering")

    # Mapear posición específica a grupo para clustering
    # Para jugadores profesionales, usar el sistema de 8 grupos específicos
    if player.is_professional:
        position_group = get_player_position_group_8_from_bd(player.player_id)
        if not position_group:  # Fallback si falla la función específica
            position_group = map_position(position)
    else:
        position_group = map_position(position)

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
                                        [
                                            create_iep_clustering_chart(
                                                position_group, season, player.player_id
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
                        lg=8,
                    ),
                ]
            ),
            # Toggle explicativo para IEP
            create_iep_explanation_toggle(),
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


def create_pdi_deep_analysis_content(player, player_stats):
    """Crea contenido del sub-tab PDI Deep Analysis según Subfase 13.5.4."""
    latest_stats = player_stats[-1] if player_stats else {}
    season = latest_stats.get("season", "2024-25")

    return dbc.Container(
        [
            # Fila 1: Desglose de componentes PDI
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
                                                        className="bi bi-pie-chart me-2"
                                                    ),
                                                    "PDI Component Breakdown",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            # Universal Component (40%)
                                            html.Div(
                                                [
                                                    html.H6(
                                                        [
                                                            html.I(
                                                                className="bi bi-globe me-2",
                                                                style={
                                                                    "color": "#26C6DA"
                                                                },
                                                            ),
                                                            "Universal Component (40%)",
                                                        ],
                                                        className="mb-2",
                                                        style={"color": "#26C6DA"},
                                                    ),
                                                    html.P(
                                                        "Skills applicable to all positions: passing accuracy, first touch, "
                                                        "ball control, spatial awareness, decision making speed.",
                                                        className="small mb-3",
                                                        style={
                                                            "color": "var(--color-white-faded)"
                                                        },
                                                    ),
                                                ]
                                            ),
                                            # Zone Component (35%)
                                            html.Div(
                                                [
                                                    html.H6(
                                                        [
                                                            html.I(
                                                                className="bi bi-map me-2",
                                                                style={
                                                                    "color": "#AB47BC"
                                                                },
                                                            ),
                                                            "Zone Component (35%)",
                                                        ],
                                                        className="mb-2",
                                                        style={"color": "#AB47BC"},
                                                    ),
                                                    html.P(
                                                        "Performance in field zones: defensive actions, midfield transitions, "
                                                        "offensive contributions, pressing intensity by zone.",
                                                        className="small mb-3",
                                                        style={
                                                            "color": "var(--color-white-faded)"
                                                        },
                                                    ),
                                                ]
                                            ),
                                            # Position Component (25%)
                                            html.Div(
                                                [
                                                    html.H6(
                                                        [
                                                            html.I(
                                                                className="bi bi-person-badge me-2",
                                                                style={
                                                                    "color": "#FF9800"
                                                                },
                                                            ),
                                                            "Position Component (25%)",
                                                        ],
                                                        className="mb-2",
                                                        style={"color": "#FF9800"},
                                                    ),
                                                    html.P(
                                                        f"Role-specific skills for {latest_stats.get('primary_position', 'CF')}: "
                                                        f"specialized actions, tactical positioning, position-based metrics.",
                                                        className="small mb-0",
                                                        style={
                                                            "color": "var(--color-white-faded)"
                                                        },
                                                    ),
                                                ]
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
                                                    "Component Evolution",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            # Reutilizar componente PDI Temporal Heatmap existente
                                            create_pdi_temporal_heatmap(
                                                player.player_id,
                                                seasons=(
                                                    [
                                                        s.get("season")
                                                        for s in player_stats
                                                    ]
                                                    if player_stats
                                                    else None
                                                ),
                                            ),
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
                ]
            ),
            # Fila 2: Análisis detallado por componente
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
                                                    "Component Radar Analysis",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            # Reutilizar radar chart de posición existente
                                            html.Div(
                                                id="position-radar-chart",
                                                children=[
                                                    # Este contenido se actualiza via callback
                                                    html.P(
                                                        "Interactive radar chart will appear here",
                                                        className="text-center",
                                                        style={
                                                            "color": "var(--color-white-faded)"
                                                        },
                                                    )
                                                ],
                                            ),
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
                                                    "PDI Insights",
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
                                                        className="bi bi-cpu me-2 text-primary"
                                                    ),
                                                    "Machine Learning Analysis",
                                                ],
                                                className="fw-bold mb-2",
                                            ),
                                            html.P(
                                                [
                                                    "• Supervised learning with academic rigor",
                                                    html.Br(),
                                                    "• Component weights based on football analytics",
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
                                            # Reutilizar explicación PDI existente
                                            create_pdi_explanation_card(),
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


def create_development_roadmap_content(player, player_stats):
    """Crea contenido del sub-tab Development Roadmap según Subfase 13.5.4."""
    latest_stats = player_stats[-1] if player_stats else {}
    season = latest_stats.get("season", "2024-25")

    # Obtener posición real del jugador desde BD (no fallback genérico)
    position = get_player_position_group_8_from_bd(player.player_id) if player else "CF"

    # Calcular métricas PDI actuales para recomendaciones
    current_pdi = {}
    try:
        from ml_system.evaluation.metrics.pdi_calculator import PDICalculator

        pdi_calculator = PDICalculator()

        if latest_stats and player:
            # DEBUG: Información del jugador
            player_name = player.user.name if player.user else "Unknown"
            print(
                f"DEBUG Roadmap: player={player_name}, position={position}, season={season}"
            )
            print(
                f"DEBUG Roadmap: latest_stats keys={list(latest_stats.keys()) if latest_stats else 'None'}"
            )

            # Usar método correcto del PDICalculator
            ml_metrics = pdi_calculator.get_or_calculate_metrics(
                player.player_id, season
            )
            if ml_metrics:
                current_pdi = {
                    "pdi_overall": ml_metrics.pdi_overall,
                    "pdi_universal": ml_metrics.pdi_universal,
                    "pdi_zone": ml_metrics.pdi_zone,
                    "pdi_position_specific": ml_metrics.pdi_position_specific,
                }
                print(f"DEBUG Roadmap: current_pdi calculado={current_pdi}")
            else:
                print(
                    f"DEBUG Roadmap: No se pudieron calcular métricas PDI para {player_name}"
                )
    except Exception as e:
        print(f"Error calculating PDI for roadmap: {e}")

    return dbc.Container(
        [
            # Fila 1: Roadmap personalizado y prioridades
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
                                                    html.I(className="bi bi-map me-2"),
                                                    f"Development Roadmap - {player.user.name if player.user else 'Unknown'} ({position})",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        _generate_selective_priority_sections(
                                            current_pdi, position
                                        )
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
                                                        className="bi bi-target me-2"
                                                    ),
                                                    "Development Targets",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            # Target PDI Score
                                            html.Div(
                                                [
                                                    html.P(
                                                        "Target PDI Score",
                                                        className="fw-bold mb-1",
                                                        style={"color": "#24DE84"},
                                                    ),
                                                    html.H4(
                                                        f"{_calculate_target_pdi(current_pdi):.1f}",
                                                        className="mb-3",
                                                        style={"color": "#26C6DA"},
                                                    ),
                                                ]
                                            ),
                                            # Current vs Target Progress Bar
                                            html.Div(
                                                [
                                                    html.P(
                                                        "Progress to Target",
                                                        className="mb-2 small",
                                                        style={
                                                            "color": "var(--color-white-faded)"
                                                        },
                                                    ),
                                                    _create_progress_bar(current_pdi),
                                                ]
                                            ),
                                            # Timeline estimate
                                            html.Div(
                                                [
                                                    html.P(
                                                        "Estimated Timeline",
                                                        className="fw-bold mt-3 mb-1",
                                                        style={"color": "#24DE84"},
                                                    ),
                                                    html.P(
                                                        "6-12 months",
                                                        className="mb-0",
                                                        style={"color": "#42A5F5"},
                                                    ),
                                                    html.P(
                                                        "Based on current development trajectory",
                                                        className="small mb-0",
                                                        style={
                                                            "color": "var(--color-white-faded)"
                                                        },
                                                    ),
                                                ]
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
            # Fila 2: Training Focus y Metodología
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
                                                        className="bi bi-bullseye me-2"
                                                    ),
                                                    "Training Focus Areas",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            _generate_training_focus(
                                                position, current_pdi, latest_stats
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
                                                    html.I(className="bi bi-book me-2"),
                                                    "Methodology",
                                                ],
                                                className="text-primary mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            _create_methodology_content(
                                                player,
                                                latest_stats,
                                                current_pdi,
                                                position,
                                                season,
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
                        lg=6,
                    ),
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
                    # Usar método correcto del PDICalculator
                    ml_metrics = pdi_calculator.get_or_calculate_metrics(
                        stat.player_id, stat.season
                    )

                    if ml_metrics:
                        total_metrics["pdi_overall"] += ml_metrics.pdi_overall or 0
                        total_metrics["pdi_universal"] += ml_metrics.pdi_universal or 0
                        total_metrics["pdi_zone"] += ml_metrics.pdi_zone or 0
                        total_metrics["pdi_position_specific"] += (
                            ml_metrics.pdi_position_specific or 0
                        )
                        # Los otros campos técnicos no están en MLMetrics, los dejamos en 0
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


def create_pdi_explanation_card():
    """
    Crea card explicativo para interpretación del gráfico PDI.
    Diseñado para usuarios sin conocimiento técnico previo.
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.I(
                        className="bi bi-info-circle me-2", style={"color": "#42A5F5"}
                    ),
                    html.Span(
                        "How to Read This Chart",
                        style={"color": "#24DE84", "font-weight": "600"},
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-chevron-down")],
                        id="pdi-explanation-toggle",
                        size="sm",
                        color="link",
                        className="float-end p-1",
                        style={"color": "#42A5F5"},
                    ),
                ],
                style={"background-color": "rgba(36, 222, 132, 0.1)", "border": "none"},
            ),
            dbc.Collapse(
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.H6(
                                    [
                                        html.I(className="bi bi-bar-chart me-2"),
                                        "PDI Components:",
                                    ],
                                    className="mb-2",
                                    style={"color": "#42A5F5"},
                                ),
                                html.P(
                                    [
                                        html.Strong(
                                            "PDI Overall", style={"color": "#24DE84"}
                                        ),
                                        " (green line): Combined performance score using machine learning",
                                    ],
                                    className="mb-1 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.P(
                                    [
                                        html.Strong(
                                            "Universal", style={"color": "#26C6DA"}
                                        ),
                                        " (cyan): Skills applicable to all positions (40% weight)",
                                    ],
                                    className="mb-1 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.P(
                                    [
                                        html.Strong("Zone", style={"color": "#AB47BC"}),
                                        " (purple): Performance in defensive/midfield/offensive zones (35% weight)",
                                    ],
                                    className="mb-1 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.P(
                                    [
                                        html.Strong(
                                            "Position", style={"color": "#FF9800"}
                                        ),
                                        " (orange): Role-specific skills for your position (25% weight)",
                                    ],
                                    className="mb-3 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.H6(
                                    [
                                        html.I(className="bi bi-bullseye me-2"),
                                        "Reference Lines:",
                                    ],
                                    className="mb-2",
                                    style={"color": "#42A5F5"},
                                ),
                                html.P(
                                    [
                                        html.I(
                                            className="bi bi-circle-fill me-2",
                                            style={"color": "#24DE84"},
                                        ),
                                        html.Strong(
                                            "Excellent (75+)",
                                            style={"color": "#24DE84"},
                                        ),
                                        ": Top-tier professional performance",
                                    ],
                                    className="mb-1 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.P(
                                    [
                                        html.I(
                                            className="bi bi-circle-fill me-2",
                                            style={"color": "#FFA726"},
                                        ),
                                        html.Strong(
                                            "Good (60+)", style={"color": "#FFA726"}
                                        ),
                                        ": Solid professional standard",
                                    ],
                                    className="mb-1 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.P(
                                    [
                                        html.I(
                                            className="bi bi-circle-fill me-2",
                                            style={"color": "#E57373"},
                                        ),
                                        html.Strong(
                                            "Average (45+)", style={"color": "#E57373"}
                                        ),
                                        ": Room for improvement",
                                    ],
                                    className="mb-3 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.H6(
                                    [
                                        html.I(className="bi bi-search me-2"),
                                        "Interpretation:",
                                    ],
                                    className="mb-2",
                                    style={"color": "#42A5F5"},
                                ),
                                html.Ul(
                                    [
                                        html.Li(
                                            [
                                                html.Strong("Rising trends"),
                                                " = Player development progress",
                                            ],
                                            className="small mb-1",
                                            style={"color": "#E0E0E0"},
                                        ),
                                        html.Li(
                                            [
                                                html.Strong("Parallel lines"),
                                                " = Balanced skill development",
                                            ],
                                            className="small mb-1",
                                            style={"color": "#E0E0E0"},
                                        ),
                                        html.Li(
                                            [
                                                html.Strong("Diverging lines"),
                                                " = Specific strengths/weaknesses",
                                            ],
                                            className="small mb-1",
                                            style={"color": "#E0E0E0"},
                                        ),
                                    ],
                                    className="mb-0",
                                ),
                            ]
                        )
                    ],
                    style={"background-color": "rgba(66, 165, 245, 0.05)"},
                ),
                id="pdi-explanation-collapse",
                is_open=False,
            ),
        ],
        className="mt-3",
        style={
            "border": "1px solid rgba(66, 165, 245, 0.3)",
            "background-color": "rgba(0, 0, 0, 0.3)",
        },
    )


def create_iep_explanation_toggle():
    """
    Crea un componente toggle explicativo para el gráfico IEP Clustering.
    Similar al toggle PDI pero específico para análisis no supervisado.
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.I(
                        className="bi bi-info-circle me-2", style={"color": "#42A5F5"}
                    ),
                    html.Span(
                        "How to Read This Clustering Chart",
                        style={"color": "#24DE84", "font-weight": "600"},
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-chevron-down")],
                        id="iep-explanation-toggle",
                        size="sm",
                        color="link",
                        className="float-end p-1",
                        style={"color": "#42A5F5"},
                    ),
                ],
                style={"background-color": "rgba(36, 222, 132, 0.1)", "border": "none"},
            ),
            dbc.Collapse(
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.H6(
                                    [
                                        html.I(className="bi bi-diagram-3 me-2"),
                                        "IEP Clustering Method:",
                                    ],
                                    className="mb-2",
                                    style={"color": "#42A5F5"},
                                ),
                                html.P(
                                    [
                                        html.Strong(
                                            "Unsupervised K-Means",
                                            style={"color": "#24DE84"},
                                        ),
                                        " clustering discovers natural performance groups without predefined labels",
                                    ],
                                    className="mb-1 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.P(
                                    [
                                        html.Strong(
                                            "PCA Dimensionality",
                                            style={"color": "#26C6DA"},
                                        ),
                                        " reduces complex metrics to 2D visualization while preserving variance",
                                    ],
                                    className="mb-1 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.P(
                                    [
                                        html.Strong(
                                            "Position-Specific",
                                            style={"color": "#AB47BC"},
                                        ),
                                        " analysis considers only players in similar roles for fair comparison",
                                    ],
                                    className="mb-3 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.H6(
                                    [
                                        html.I(className="bi bi-palette me-2"),
                                        "Cluster Tiers:",
                                    ],
                                    className="mb-2",
                                    style={"color": "#42A5F5"},
                                ),
                                html.P(
                                    [
                                        html.I(
                                            className="bi bi-circle-fill me-2",
                                            style={"color": "#4CAF50"},
                                        ),
                                        html.Strong(
                                            "Elite Tier",
                                            style={"color": "#4CAF50"},
                                        ),
                                        ": Highest efficiency players in position",
                                    ],
                                    className="mb-1 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.P(
                                    [
                                        html.I(
                                            className="bi bi-circle-fill me-2",
                                            style={"color": "#2196F3"},
                                        ),
                                        html.Strong(
                                            "Strong Tier", style={"color": "#2196F3"}
                                        ),
                                        ": Solid professional performance level (4-cluster mode)",
                                    ],
                                    className="mb-1 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.P(
                                    [
                                        html.I(
                                            className="bi bi-circle-fill me-2",
                                            style={"color": "#FF9800"},
                                        ),
                                        html.Strong(
                                            "Average Tier", style={"color": "#FF9800"}
                                        ),
                                        ": League average performance standard",
                                    ],
                                    className="mb-1 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.P(
                                    [
                                        html.I(
                                            className="bi bi-circle-fill me-2",
                                            style={"color": "#F44336"},
                                        ),
                                        html.Strong(
                                            "Development Tier",
                                            style={"color": "#F44336"},
                                        ),
                                        ": Growth potential with specific focus areas",
                                    ],
                                    className="mb-3 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.H6(
                                    [
                                        html.I(className="bi bi-person-circle me-2"),
                                        "Current Player Highlight:",
                                    ],
                                    className="mb-2",
                                    style={"color": "#42A5F5"},
                                ),
                                html.P(
                                    [
                                        html.I(
                                            className="bi bi-circle-fill me-2",
                                            style={"color": "#8B5CF6"},
                                        ),
                                        html.Strong(
                                            "Selected Player",
                                            style={"color": "#8B5CF6"},
                                        ),
                                        ": Your player appears in purple with red border for easy identification",
                                    ],
                                    className="mb-1 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.P(
                                    [
                                        "• Shown with ",
                                        html.Strong(
                                            "thick red border",
                                            style={"color": "#EF4444"},
                                        ),
                                        " for visibility",
                                        html.Br(),
                                        "• Appears in legend with real player name",
                                        html.Br(),
                                        "• Size reflects IEP score like other players",
                                    ],
                                    className="mb-3 small",
                                    style={"color": "#E0E0E0"},
                                ),
                                html.H6(
                                    [
                                        html.I(className="bi bi-search me-2"),
                                        "How to Interpret:",
                                    ],
                                    className="mb-2",
                                    style={"color": "#42A5F5"},
                                ),
                                html.Ul(
                                    [
                                        html.Li(
                                            [
                                                html.Strong("Position on chart"),
                                                " = Natural efficiency grouping discovered by K-means algorithm",
                                            ],
                                            className="small mb-1",
                                            style={"color": "#E0E0E0"},
                                        ),
                                        html.Li(
                                            [
                                                html.Strong("Distance from center"),
                                                " = Uniqueness of playing style within position",
                                            ],
                                            className="small mb-1",
                                            style={"color": "#E0E0E0"},
                                        ),
                                        html.Li(
                                            [
                                                html.Strong("Cluster membership"),
                                                " = Similar performance profile to other players in same tier",
                                            ],
                                            className="small mb-1",
                                            style={"color": "#E0E0E0"},
                                        ),
                                        html.Li(
                                            [
                                                html.Strong("Dynamic clustering"),
                                                " = 4 tiers with sufficient data, 3 tiers when limited players",
                                            ],
                                            className="small mb-1",
                                            style={"color": "#E0E0E0"},
                                        ),
                                    ],
                                    className="mb-0",
                                ),
                            ]
                        )
                    ],
                    style={"background-color": "rgba(66, 165, 245, 0.05)"},
                ),
                id="iep-explanation-collapse",
                is_open=False,
            ),
        ],
        className="mt-3",
        style={
            "border": "1px solid rgba(66, 165, 245, 0.3)",
            "background-color": "rgba(0, 0, 0, 0.3)",
        },
    )


# ============================================================================
# FUNCIONES AUXILIARES PARA DEVELOPMENT ROADMAP
# ============================================================================


def _generate_selective_priority_sections(current_pdi, position):
    """
    Genera secciones de prioridad selectivas basadas en PDI actual del jugador.
    Solo muestra las secciones relevantes según el nivel de desarrollo.
    """
    if not current_pdi:
        return [
            html.P(
                "No PDI data available for priority analysis",
                className="text-center",
                style={"color": "var(--color-white-faded)"},
            )
        ]

    pdi_overall = current_pdi.get("pdi_overall", 0)
    sections = []

    # Lógica selectiva basada en PDI Overall
    if pdi_overall < 40:
        # Solo críticas para jugadores con PDI muy bajo (como Felipe: 34.86)
        sections.append(
            html.Div(
                [
                    html.H6(
                        [
                            html.I(
                                className="bi bi-exclamation-triangle me-2",
                                style={"color": "#FF5722"},
                            ),
                            "Critical Priority Areas",
                        ],
                        className="mb-2",
                        style={"color": "#FF5722"},
                    ),
                    _generate_priority_recommendations(current_pdi, "high", position),
                ],
                className="mb-4",
            )
        )
    elif pdi_overall < 65:
        # Críticas + moderadas para jugadores medios
        sections.extend(
            [
                html.Div(
                    [
                        html.H6(
                            [
                                html.I(
                                    className="bi bi-exclamation-triangle me-2",
                                    style={"color": "#FF5722"},
                                ),
                                "High Priority Areas",
                            ],
                            className="mb-2",
                            style={"color": "#FF5722"},
                        ),
                        _generate_priority_recommendations(
                            current_pdi, "high", position
                        ),
                    ],
                    className="mb-4",
                ),
                html.Div(
                    [
                        html.H6(
                            [
                                html.I(
                                    className="bi bi-arrow-up me-2",
                                    style={"color": "#FF9800"},
                                ),
                                "Medium Priority Areas",
                            ],
                            className="mb-2",
                            style={"color": "#FF9800"},
                        ),
                        _generate_priority_recommendations(
                            current_pdi, "medium", position
                        ),
                    ],
                    className="mb-4",
                ),
            ]
        )
    else:
        # Moderadas + fortalezas para jugadores buenos
        sections.extend(
            [
                html.Div(
                    [
                        html.H6(
                            [
                                html.I(
                                    className="bi bi-arrow-up me-2",
                                    style={"color": "#FF9800"},
                                ),
                                "Development Areas",
                            ],
                            className="mb-2",
                            style={"color": "#FF9800"},
                        ),
                        _generate_priority_recommendations(
                            current_pdi, "medium", position
                        ),
                    ],
                    className="mb-4",
                ),
                html.Div(
                    [
                        html.H6(
                            [
                                html.I(
                                    className="bi bi-check-circle me-2",
                                    style={"color": "#4CAF50"},
                                ),
                                "Strengths to Maintain",
                            ],
                            className="mb-2",
                            style={"color": "#4CAF50"},
                        ),
                        _generate_priority_recommendations(
                            current_pdi, "maintain", position
                        ),
                    ]
                ),
            ]
        )

    return sections


def _generate_priority_recommendations(current_pdi, priority_level, position):
    """Genera recomendaciones estratégicas basadas en análisis PDI (enfoque macro)."""
    if not current_pdi:
        return html.P(
            "No PDI data available for strategic analysis",
            className="small",
            style={"color": "var(--color-white-faded)"},
        )

    # Definir umbrales por nivel de prioridad
    thresholds = {
        "high": 45,  # Áreas críticas por debajo de 45
        "medium": 60,  # Áreas moderadas entre 45-60
        "maintain": 70,  # Fortalezas por encima de 70
    }

    # Generar recomendaciones estratégicas basadas en componentes PDI
    recommendations = []
    threshold = thresholds[priority_level]

    pdi_overall = current_pdi.get("pdi_overall", 0)
    pdi_universal = current_pdi.get("pdi_universal", 0)
    pdi_zone = current_pdi.get("pdi_zone", 0)
    pdi_position = current_pdi.get("pdi_position_specific", 0)

    if priority_level == "high":
        if pdi_overall < threshold:
            recommendations.append(
                f"• Overall Performance Index: {pdi_overall:.1f} - requires strategic focus"
            )
        if pdi_universal < threshold:
            recommendations.append(
                f"• Universal Skills Index: {pdi_universal:.1f} - fundamental development needed"
            )
        if pdi_zone < threshold:
            recommendations.append(
                f"• Zone Actions Index: {pdi_zone:.1f} - tactical understanding priority"
            )
        if pdi_position < threshold:
            recommendations.append(
                f"• Position-Specific Index: {pdi_position:.1f} - role specialization required"
            )

    elif priority_level == "medium":
        if threshold <= pdi_overall < 75:
            recommendations.append(
                f"• Overall Performance Index: {pdi_overall:.1f} - maintain development pace"
            )
        if threshold <= pdi_universal < 75:
            recommendations.append(
                f"• Universal Skills Index: {pdi_universal:.1f} - continue skill refinement"
            )
        if threshold <= pdi_zone < 75:
            recommendations.append(
                f"• Zone Actions Index: {pdi_zone:.1f} - enhance tactical execution"
            )

    else:  # maintain
        if pdi_overall >= threshold:
            recommendations.append(
                f"• Overall Performance Index: {pdi_overall:.1f} - excellent level achieved"
            )
        if pdi_universal >= threshold:
            recommendations.append(
                f"• Universal Skills Index: {pdi_universal:.1f} - maintain high standards"
            )
        if pdi_zone >= threshold:
            recommendations.append(
                f"• Zone Actions Index: {pdi_zone:.1f} - continue excellence"
            )

    # Si no hay recomendaciones específicas, análisis general del perfil PDI
    if not recommendations:
        recommendations = [
            f"• PDI Profile Analysis: Overall {pdi_overall:.1f}, Universal {pdi_universal:.1f}, Zone {pdi_zone:.1f}, Position {pdi_position:.1f}",
            "• Strategic Development: Focus on lowest scoring component for maximum impact",
        ]

    return html.P(
        [
            html.Span(rec, style={"display": "block"}) for rec in recommendations[:4]
        ],  # Máximo 4 para análisis completo
        className="small mb-0",
        style={"color": "var(--color-white-faded)"},
    )


def _calculate_target_pdi(current_pdi):
    """Calcula PDI objetivo basado en el PDI actual."""
    if not current_pdi:
        return 75.0  # Target por defecto

    current_overall = current_pdi.get("pdi_overall", 50)

    # Target es +15-20 puntos del actual, máximo 90
    target = min(current_overall + 18, 90)
    return target


def _create_progress_bar(current_pdi):
    """Crea barra de progreso hacia el target PDI."""
    if not current_pdi:
        current = 50
        target = 75
    else:
        current = current_pdi.get("pdi_overall", 50)
        target = _calculate_target_pdi(current_pdi)

    # Progreso como porcentaje hacia el target
    progress = min((current / target) * 100, 100)

    return dbc.Progress(
        value=progress,
        color=(
            "success" if progress >= 80 else "warning" if progress >= 60 else "danger"
        ),
        className="mb-2",
        style={"height": "8px"},
        animated=True,
    )


def _generate_training_focus(position, current_pdi, latest_stats):
    """
    Genera recomendaciones dinámicas de entrenamiento basadas en análisis de debilidades del jugador.
    Solo recomienda áreas que necesitan trabajo según métricas reales.
    """

    # Mapeo de métricas a ejercicios específicos
    METRIC_TO_EXERCISE = {
        "shots_on_target_pct": "Finishing accuracy drills",
        "shots_per_90": "Shot creation and positioning",
        "pass_accuracy_pct": "Passing under pressure drills",
        "assists_per_90": "Creative playmaking and vision",
        "defensive_actions_per_90": "Pressing and defensive positioning",
        "duels_won_pct": "Physical duels and aerial challenges",
        "goals_per_90": "Goal scoring opportunities",
        "expected_goals": "Movement in dangerous areas",
        "expected_assists": "Final pass execution",
    }

    # Thresholds por posición (critical, good, excellent)
    POSITION_THRESHOLDS = {
        "GK": {
            "pass_accuracy_pct": (60.0, 75.0, 85.0),
            "duels_won_pct": (40.0, 60.0, 75.0),
        },
        "CB": {
            "defensive_actions_per_90": (3.0, 6.0, 9.0),
            "duels_won_pct": (45.0, 65.0, 80.0),
            "pass_accuracy_pct": (60.0, 70.0, 80.0),
        },
        "FB": {
            "assists_per_90": (0.05, 0.2, 0.4),
            "defensive_actions_per_90": (2.0, 4.0, 6.5),
            "duels_won_pct": (35.0, 55.0, 70.0),
        },
        "CM": {
            "pass_accuracy_pct": (70.0, 80.0, 88.0),
            "assists_per_90": (0.05, 0.15, 0.35),
            "defensive_actions_per_90": (2.5, 4.0, 6.0),
        },
        "CF": {
            "shots_on_target_pct": (20.0, 35.0, 50.0),
            "shots_per_90": (1.5, 2.5, 4.0),
            "pass_accuracy_pct": (60.0, 70.0, 80.0),
            "assists_per_90": (0.03, 0.1, 0.25),
        },
    }

    def analyze_player_weaknesses():
        """Analiza métricas reales del jugador y genera recomendaciones específicas."""
        if not latest_stats:
            return ["No training data available - focus on fundamental skills"]

        recommendations = []
        position_metrics = POSITION_THRESHOLDS.get(position, POSITION_THRESHOLDS["CF"])

        # Analizar cada métrica relevante para la posición
        for metric, thresholds in position_metrics.items():
            metric_value = latest_stats.get(metric)
            if metric_value is not None:
                critical, good, excellent = thresholds
                exercise = METRIC_TO_EXERCISE.get(
                    metric, f"Work on {metric.replace('_', ' ')}"
                )

                # Solo recomendar si está por debajo del nivel "excellent"
                if metric_value < excellent:
                    recommendations.append(
                        add_context(exercise, metric, critical, good, excellent)
                    )

        # Si no hay recomendaciones específicas, dar consejos de posición
        if not recommendations:
            recommendations = [
                f"Continue excellent {position} performance - maintain current training intensity"
            ]

        # Máximo 4 recomendaciones para mantener foco
        return recommendations[:4]

    # Áreas de entrenamiento por posición con contexto de métricas reales y 4 niveles
    def add_context(
        area, metric_key, threshold_critical, threshold_good, threshold_excellent
    ):
        """
        Añade contexto de métrica específica con 4 niveles de prioridad y colores CSS.
        - Critical (rojo): < threshold_critical - URGENT
        - Moderate (amarillo): critical <= value < threshold_good - needs improvement
        - Good (verde): threshold_good <= value < threshold_excellent - good level
        - Strength (azul): >= threshold_excellent - leverage this advantage
        """
        if not latest_stats:
            return area

        metric_value = latest_stats.get(metric_key)
        if metric_value is not None and isinstance(metric_value, (int, float)):
            # Formatear número según el tipo de métrica
            if "pct" in metric_key or "per_90" in metric_key:
                value_str = f"{metric_value:.1f}"
            else:
                value_str = f"{metric_value:.0f}"

            # Determinar nivel y color según thresholds
            metric_display = metric_key.replace("_", " ")

            if metric_value < threshold_critical:
                context = html.Span(
                    f"({metric_display}: {value_str} - URGENT - needs immediate work)",
                    style={"color": "#dc3545", "font-weight": "500"},
                )
            elif metric_value < threshold_good:
                context = html.Span(
                    f"({metric_display}: {value_str} - needs improvement)",
                    style={"color": "#ffc107", "font-weight": "500"},
                )
            elif metric_value < threshold_excellent:
                context = html.Span(
                    f"({metric_display}: {value_str} - good level)",
                    style={"color": "#28a745", "font-weight": "500"},
                )
            else:
                context = html.Span(
                    [
                        html.I(
                            className="bi bi-star-fill me-1",
                            style={"font-size": "0.8em"},
                        ),
                        f"({metric_display}: {value_str} - STRENGTH - leverage this advantage)",
                    ],
                    style={"color": "#17a2b8", "font-weight": "500"},
                )

            return html.Span([area, " ", context])

        return area

    # Generar recomendaciones dinámicas basadas en análisis real del jugador
    focus_areas = analyze_player_weaknesses()

    return html.Div(
        [
            html.Div(
                [
                    html.I(
                        className="bi bi-arrow-right me-2",
                        style={"color": "var(--color-primary)"},
                    ),
                    area,
                ],
                className="d-flex align-items-center small mb-2",
                style={"color": "var(--color-white-faded)"},
            )
            for area in focus_areas
        ]
    )


def _create_methodology_content(player, latest_stats, current_pdi, position, season):
    """
    Crea contenido methodology personalizado combinando:
    1. Qué datos tenemos (Data Sources)
    2. Cómo se calcula (PDI Calculation)
    3. Con qué se compara (Benchmarks)
    """
    try:
        # Extraer datos específicos del jugador
        player_name = player.user.name if player.user else "Unknown"
        matches = latest_stats.get("matches_played", "N/A")
        minutes = latest_stats.get("minutes_played", "N/A")
        team = latest_stats.get("team", "Unknown")
        pdi_score = current_pdi.get("pdi_overall", 0) if current_pdi else 0

        return html.Div(
            [
                # DATA SOURCES
                html.H6(
                    [
                        html.I(
                            className="bi bi-database me-2",
                            style={"color": "var(--color-info)"},
                        ),
                        "Data Sources",
                    ],
                    className="text-info mb-2",
                ),
                html.P(
                    [
                        (
                            f"Season: {season} • Matches: {matches} • Minutes: {minutes:,}"
                            if isinstance(minutes, (int, float))
                            else f"Season: {season} • Matches: {matches} • Minutes: {minutes}"
                        ),
                        html.Br(),
                        "Statistical Indicators: 31+ metrics tracked from Thai League database",
                    ],
                    className="small mb-3",
                    style={"color": "var(--color-white-faded)"},
                ),
                # PDI CALCULATION
                html.H6(
                    [
                        html.I(
                            className="bi bi-calculator me-2",
                            style={"color": "var(--color-warning)"},
                        ),
                        "PDI Calculation Method",
                    ],
                    className="text-warning mb-2",
                ),
                html.P(
                    [
                        f"Universal Skills (40%) + Zone Actions (35%) + Position-Specific (25%)",
                        html.Br(),
                        (
                            f"Your PDI Score: {pdi_score:.1f}/100"
                            if pdi_score > 0
                            else "Your PDI Score: Calculating..."
                        ),
                    ],
                    className="small mb-3",
                    style={"color": "var(--color-white-faded)"},
                ),
                # BENCHMARKS
                html.H6(
                    [
                        html.I(
                            className="bi bi-graph-up me-2",
                            style={"color": "var(--color-success)"},
                        ),
                        "Benchmarking Context",
                    ],
                    className="text-success mb-2",
                ),
                html.P(
                    [
                        f"League: Thai League {season} • Position: {position} players",
                        html.Br(),
                        f"Team Context: {team} squad • Performance ranking vs. position group",
                    ],
                    className="small mb-0",
                    style={"color": "var(--color-white-faded)"},
                ),
            ]
        )

    except Exception as e:
        print(f"Error creating methodology content: {e}")
        return html.P(
            "Methodology information unavailable", className="small text-muted"
        )


def create_iep_clustering_content(player, player_stats):
    """Crea contenido del sub-tab IEP Clustering."""

    # Debug: verificar datos recibidos
    try:
        player_name = (
            player.user.name if hasattr(player, "user") and player.user else "Unknown"
        )
    except Exception as e:
        player_name = f"Unknown (error: {e})"

    # Obtener la temporada más reciente para referencia
    latest_stats = player_stats[-1] if player_stats else {}
    season = latest_stats.get("season", "2024-25")

    # Fallback robusto: Si player_stats está vacío, consultar BD directamente
    if not player_stats and player.player_id:
        try:
            from controllers.db import get_db_session
            from models.professional_stats_model import ProfessionalStats

            with get_db_session() as session:
                latest_bd_stats = (
                    session.query(ProfessionalStats)
                    .filter(ProfessionalStats.player_id == player.player_id)
                    .order_by(ProfessionalStats.season.desc())
                    .first()
                )

                if latest_bd_stats:
                    season = latest_bd_stats.season
                else:
                    logger.warning(
                        f"No se encontraron stats en BD para player {player.player_id}"
                    )
        except Exception as e:
            logger.error(f"Error en fallback BD: {e}")

    # Obtener posición con fallbacks inteligentes
    position = latest_stats.get("primary_position")

    # Si no hay posición en stats, intentar obtener de la BD
    if not position:
        try:
            from controllers.db import get_db_session
            from models.professional_stats_model import ProfessionalStats

            with get_db_session() as session:
                latest_db_stats = (
                    session.query(ProfessionalStats)
                    .filter(ProfessionalStats.player_id == player.player_id)
                    .order_by(ProfessionalStats.season.desc())
                    .first()
                )

                if latest_db_stats:
                    position = latest_db_stats.primary_position
        except Exception as e:
            logger.warning(f"Error obteniendo posición de BD: {e}")

    # Fallback final a posición neutral (MID es más común que CF)
    if not position:
        position = "CMF"  # Centro medio, mapea a MID
        logger.info(f"Usando posición fallback CMF para clustering")

    # Mapear posición específica a grupo para clustering
    # Para jugadores profesionales, usar el sistema de 8 grupos específicos
    if player.is_professional:
        position_group = get_player_position_group_8_from_bd(player.player_id)
        if not position_group:  # Fallback si falla la función específica
            position_group = map_position(position)
    else:
        position_group = map_position(position)

    # Nota: player_stats contiene todas las temporadas para análisis IEP completo

    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H6(
                        [
                            html.I(className="bi bi-diagram-3 me-2"),
                            "IEP Clustering Analysis",
                        ],
                        className="text-primary mb-0",
                    )
                ],
                style={
                    "background-color": "#2B2B2B",
                    "border-bottom": "1px solid rgba(255,255,255,0.2)",
                },
            ),
            dbc.CardBody(
                [create_iep_clustering_chart(position_group, season, player.player_id)],
                className="p-2",
            ),
        ],
        className="mb-4",
        style={
            "background-color": "#2B2B2B",
            "border-color": "rgba(36, 222, 132, 0.3)",
        },
    )


if __name__ == "__main__":
    # Para testing
    pass

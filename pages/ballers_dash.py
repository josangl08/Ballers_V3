# pages/ballers_dash.py - Migración visual de ballers.py a Dash
from __future__ import annotations

import datetime

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html  # noqa: F401

from common.format_utils import format_name_with_del
from controllers.etl_controller import ETLController
from controllers.player_controller import get_player_profile_data, get_players_for_list
from controllers.thai_league_controller import ThaiLeagueController
from models.user_model import UserType

# ML Pipeline Imports - Phase 13.3 Dashboard Integration
from controllers.ml.ml_metrics_controller import MLMetricsController
from controllers.ml.feature_engineer import FeatureEngineer
from controllers.ml.position_normalizer import PositionNormalizer


# Funciones simples para reemplazar cloud_utils removido
def is_streamlit_cloud():
    return False


def show_cloud_feature_limitation(feature_name):
    return f"Feature {feature_name} not available in local mode"


def show_cloud_mode_info():
    return "Running in local mode"


def create_evolution_chart(player_stats):
    """
    Crea gráfico de evolución temporal avanzado con métricas normalizadas.

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

    # Calcular métricas normalizadas por 90 minutos
    goals_per_90 = [stat.get("goals_per_90") or 0 for stat in player_stats]
    assists_per_90 = [stat.get("assists_per_90") or 0 for stat in player_stats]

    # Calcular expected goals si está disponible
    expected_goals = [stat.get("expected_goals") or 0 for stat in player_stats]

    # Crear gráfico con múltiples líneas mejoradas
    fig = go.Figure()

    # Línea de goles totales
    fig.add_trace(
        go.Scatter(
            x=seasons,
            y=goals,
            mode="lines+markers",
            name="Goals (Total)",
            line=dict(color="#24DE84", width=3),
            marker=dict(size=8),
            hovertemplate="<b>Season:</b> %{x}<br><b>Goals:</b> %{y}<extra></extra>",
        )
    )

    # Línea de asistencias totales
    fig.add_trace(
        go.Scatter(
            x=seasons,
            y=assists,
            mode="lines+markers",
            name="Assists (Total)",
            line=dict(color="#FFA726", width=3),
            marker=dict(size=8),
            hovertemplate="<b>Season:</b> %{x}<br><b>Assists:</b> %{y}<extra></extra>",
        )
    )

    # Línea de expected goals si está disponible
    if any(xg > 0 for xg in expected_goals):
        fig.add_trace(
            go.Scatter(
                x=seasons,
                y=expected_goals,
                mode="lines+markers",
                name="Expected Goals (xG)",
                line=dict(color="#E57373", width=2, dash="dot"),
                marker=dict(size=6),
                hovertemplate="<b>Season:</b> %{x}<br><b>xG:</b> %{y:.2f}<extra></extra>",
            )
        )

    # Línea de partidos jugados (escala secundaria)
    fig.add_trace(
        go.Scatter(
            x=seasons,
            y=matches,
            mode="lines+markers",
            name="Matches Played",
            line=dict(color="#42A5F5", width=2, dash="dash"),
            marker=dict(size=6),
            yaxis="y2",
            hovertemplate="<b>Season:</b> %{x}<br><b>Matches:</b> %{y}<extra></extra>",
        )
    )

    # Layout mejorado con dos ejes Y
    fig.update_layout(
        title={
            "text": "Performance Evolution by Season",
            "x": 0.5,
            "font": {"color": "#24DE84", "size": 16},
        },
        xaxis_title="Season",
        yaxis=dict(
            title=dict(text="Goals & Assists", font=dict(color="#FFFFFF")),
            tickfont=dict(color="#FFFFFF"),
            gridcolor="rgba(255,255,255,0.1)",
            linecolor="rgba(255,255,255,0.2)",
        ),
        yaxis2=dict(
            title=dict(text="Matches Played", font=dict(color="#42A5F5")),
            tickfont=dict(color="#42A5F5"),
            overlaying="y",
            side="right",
            gridcolor="rgba(66,165,245,0.1)",
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#FFFFFF"},
        legend=dict(
            bgcolor="rgba(0,0,0,0.7)",
            bordercolor="rgba(36,222,132,0.3)",
            borderwidth=1,
            x=0.01,
            y=0.99,
        ),
        height=400,
        hovermode="x unified",
    )

    return dcc.Graph(
        figure=fig, style={"height": "400px"}, config={"displayModeBar": False}
    )


def create_radar_chart(player_stats):
    """
    Crea radar chart avanzado de habilidades del jugador con múltiples métricas.

    Args:
        player_stats: Lista de diccionarios con estadísticas por temporada

    Returns:
        Componente dcc.Graph con el radar chart
    """
    if not player_stats:
        return dbc.Alert("No statistical data available", color="warning")

    # Usar la temporada más reciente
    latest_stats = player_stats[-1] if player_stats else {}

    # Definir categorías más específicas y realistas
    categories = [
        "Attacking",
        "Passing",
        "Defense",
        "Physical",
        "Accuracy",
        "Participation",
    ]

    # Calcular métricas más precisas usando datos reales del modelo
    goals_per_90 = latest_stats.get("goals_per_90", 0) or 0
    assists_per_90 = latest_stats.get("assists_per_90", 0) or 0
    pass_accuracy_pct = latest_stats.get("pass_accuracy_pct", 0) or 0
    defensive_actions_per_90 = latest_stats.get("defensive_actions_per_90", 0) or 0
    duels_won_pct = latest_stats.get("duels_won_pct", 0) or 0
    shots_on_target_pct = latest_stats.get("shots_on_target_pct", 0) or 0
    matches_played = latest_stats.get("matches_played", 0) or 0

    # Normalización más realista basada en percentiles de la liga
    # Attack: combina goles y asistencias por 90 min (escala 0-2.0 -> 0-100)
    attack_score = min(100, (goals_per_90 + assists_per_90) * 50)

    # Passing: directamente el porcentaje de precisión
    passing_score = min(100, pass_accuracy_pct)

    # Defense: acciones defensivas por 90 min (escala 0-15 -> 0-100)
    defense_score = min(100, defensive_actions_per_90 * 6.67)

    # Physical: porcentaje de duelos ganados
    physical_score = min(100, duels_won_pct)

    # Accuracy: precisión de tiros a portería
    accuracy_score = min(100, shots_on_target_pct)

    # Participation: partidos jugados sobre máximo de temporada (escala 0-35 -> 0-100)
    participation_score = min(100, matches_played * 2.86)

    values = [
        attack_score,
        passing_score,
        defense_score,
        physical_score,
        accuracy_score,
        participation_score,
    ]

    # Crear radar chart con diseño mejorado
    fig = go.Figure()

    # Añadir línea de referencia de liga promedio (estimado)
    reference_values = [30, 75, 40, 50, 35, 60]  # Valores promedio estimados
    fig.add_trace(
        go.Scatterpolar(
            r=reference_values,
            theta=categories,
            fill="toself",
            fillcolor="rgba(128, 128, 128, 0.1)",
            line=dict(color="#808080", width=1, dash="dash"),
            name="League Average",
        )
    )

    # Añadir datos del jugador
    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill="toself",
            fillcolor="rgba(36, 222, 132, 0.4)",
            line=dict(color="#24DE84", width=3),
            marker=dict(size=8, color="#24DE84"),
            name="Player Performance",
        )
    )

    # Layout mejorado con más detalles
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
            "text": f'Skills Profile - {latest_stats.get("season", "Current")}',
            "x": 0.5,
            "font": {"color": "#24DE84", "size": 14},
        },
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin=dict(t=60, b=40, l=40, r=40),
    )

    return dcc.Graph(
        figure=fig, style={"height": "400px"}, config={"displayModeBar": False}
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
            hovertemplate="<b>Season:</b> %{x}<br><b>Metric:</b> %{y}<br><b>Score:</b> %{z:.1f}/100<extra></extra>",
            zmin=0,
            zmax=100,
        )
    )

    fig.update_layout(
        title={
            "text": "Performance Heatmap by Season",
            "x": 0.5,
            "font": {"color": "#24DE84", "size": 14},
        },
        xaxis_title="Season",
        yaxis_title="Performance Metrics",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#FFFFFF"},
        height=350,
        margin=dict(t=50, b=40, l=120, r=40),
    )

    return dcc.Graph(
        figure=fig, style={"height": "350px"}, config={"displayModeBar": False}
    )


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
    Crea gráfico de evolución del Player Development Index (PDI).
    
    Integra datos ML del pipeline ETL con visualización avanzada.
    """
    try:
        # Inicializar controller ML
        ml_controller = MLMetricsController()
        
        if not seasons:
            # Últimas 3 temporadas por defecto
            current_year = datetime.datetime.now().year
            seasons = [
                f"{current_year-2}-{str(current_year-1)[-2:]}",
                f"{current_year-1}-{str(current_year)[-2:]}",
                f"{current_year}-{str(current_year+1)[-2:]}"
            ]
        
        # Obtener métricas ML por temporada
        pdi_data = []
        for season in seasons:
            try:
                analysis = ml_controller.get_enhanced_player_analysis(player_id, season)
                if "ml_metrics" in analysis and "raw" in analysis["ml_metrics"]:
                    ml_metrics = analysis["ml_metrics"]["raw"]
                    pdi_data.append({
                        "season": season,
                        "pdi_overall": ml_metrics.get("pdi_overall", 0),
                        "pdi_universal": ml_metrics.get("pdi_universal", 0),
                        "pdi_zone": ml_metrics.get("pdi_zone", 0),
                        "pdi_position": ml_metrics.get("pdi_position_specific", 0),
                        "technical": ml_metrics.get("technical_proficiency", 0),
                        "tactical": ml_metrics.get("tactical_intelligence", 0),
                        "physical": ml_metrics.get("physical_performance", 0),
                        "consistency": ml_metrics.get("consistency_index", 0)
                    })
            except Exception as e:
                print(f"Error obteniendo datos ML para temporada {season}: {e}")
                continue
        
        if not pdi_data:
            return dbc.Alert("No ML metrics available for PDI evolution", color="warning")
        
        # Crear gráfico PDI
        fig = go.Figure()
        
        # PDI Overall (línea principal)
        fig.add_trace(go.Scatter(
            x=[d["season"] for d in pdi_data],
            y=[d["pdi_overall"] for d in pdi_data],
            mode='lines+markers',
            name='PDI Overall',
            line=dict(color='#24DE84', width=4),
            marker=dict(size=10),
            hovertemplate='<b>PDI Overall</b><br>%{y:.1f}<br>Season: %{x}<extra></extra>'
        ))
        
        # Componentes PDI (líneas secundarias)
        fig.add_trace(go.Scatter(
            x=[d["season"] for d in pdi_data],
            y=[d["pdi_universal"] for d in pdi_data],
            mode='lines+markers',
            name='Universal (40%)',
            line=dict(color='#1E3A8A', width=2, dash='dot'),
            marker=dict(size=6),
            hovertemplate='<b>PDI Universal</b><br>%{y:.1f}<br>Season: %{x}<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=[d["season"] for d in pdi_data],
            y=[d["pdi_zone"] for d in pdi_data],
            mode='lines+markers',
            name='Zone (35%)',
            line=dict(color='#F59E0B', width=2, dash='dash'),
            marker=dict(size=6),
            hovertemplate='<b>PDI Zone</b><br>%{y:.1f}<br>Season: %{x}<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=[d["season"] for d in pdi_data],
            y=[d["pdi_position"] for d in pdi_data],
            mode='lines+markers',
            name='Position (25%)',
            line=dict(color='#10B981', width=2, dash='dashdot'),
            marker=dict(size=6),
            hovertemplate='<b>PDI Position</b><br>%{y:.1f}<br>Season: %{x}<extra></extra>'
        ))
        
        # Configurar layout
        fig.update_layout(
            title=dict(
                text="Player Development Index Evolution",
                font=dict(color="#24DE84", size=16)
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
            hovermode='x unified'
        )
        
        # Añadir líneas de referencia
        fig.add_hline(y=75, line_dash="solid", line_color="#10B981", 
                      annotation_text="Excellence (75+)", annotation_position="top right")
        fig.add_hline(y=60, line_dash="solid", line_color="#F59E0B",
                      annotation_text="Good (60+)", annotation_position="top right") 
        fig.add_hline(y=40, line_dash="solid", line_color="#EF4444",
                      annotation_text="Needs Improvement (40+)", annotation_position="top right")
        
        # Configurar ejes
        fig.update_yaxes(range=[0, 100], dtick=10, showgrid=True, gridcolor='rgba(255,255,255,0.1)')
        fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
        
        return dcc.Graph(
            figure=fig, 
            style={"height": "350px"}, 
            config={"displayModeBar": False}
        )
        
    except Exception as e:
        print(f"Error creating PDI evolution chart: {e}")
        return dbc.Alert(f"Error creating PDI chart: {str(e)}", color="danger")


def create_ml_enhanced_radar_chart(player_id, season="2024-25"):
    """
    Crea radar chart mejorado con métricas ML normalizadas.
    
    Combina traditional stats con análisis ML del pipeline.
    """
    try:
        # Inicializar controllers ML
        ml_controller = MLMetricsController()
        position_normalizer = PositionNormalizer()
        
        # Obtener análisis ML del jugador
        analysis = ml_controller.get_enhanced_player_analysis(player_id, season)
        
        if "error" in analysis:
            return dbc.Alert("No ML data available for radar chart", color="warning")
        
        # Extraer métricas normalizadas
        ml_metrics = analysis.get("ml_metrics", {}).get("raw", {})
        
        # Definir métricas para radar chart
        metrics_data = {
            'Technical Skills': ml_metrics.get('technical_proficiency', 50),
            'Tactical Intelligence': ml_metrics.get('tactical_intelligence', 50),
            'Physical Performance': ml_metrics.get('physical_performance', 50),
            'Consistency': ml_metrics.get('consistency_index', 50),
            'Universal Skills': ml_metrics.get('pdi_universal', 50),
            'Zone Performance': ml_metrics.get('pdi_zone', 50),
            'Position Specific': ml_metrics.get('pdi_position_specific', 50)
        }
        
        # Crear radar chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=list(metrics_data.values()),
            theta=list(metrics_data.keys()),
            fill='toself',
            name='ML Analysis',
            fillcolor='rgba(36, 222, 132, 0.3)',
            line=dict(color='#24DE84', width=3),
            hovertemplate='<b>%{theta}</b><br>Score: %{r:.1f}<extra></extra>'
        ))
        
        # Configurar layout
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    tickmode='linear',
                    dtick=20,
                    showticklabels=True,
                    ticks='outside',
                    tickcolor='#FFFFFF',
                    gridcolor='rgba(255,255,255,0.3)',
                    gridwidth=1
                ),
                angularaxis=dict(
                    tickfont=dict(size=12, color='#FFFFFF'),
                    rotation=90,
                    direction='counterclockwise'
                )
            ),
            showlegend=True,
            legend=dict(
                bgcolor="rgba(0,0,0,0.7)",
                bordercolor="rgba(36,222,132,0.3)",
                borderwidth=1,
                font=dict(color='#FFFFFF')
            ),
            title=dict(
                text="ML-Enhanced Performance Profile",
                font=dict(color="#24DE84", size=16)
            ),
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#FFFFFF")
        )
        
        return dcc.Graph(
            figure=fig,
            style={"height": "400px"},
            config={"displayModeBar": False}
        )
        
    except Exception as e:
        print(f"Error creating ML radar chart: {e}")
        return dbc.Alert(f"Error creating radar chart: {str(e)}", color="danger")


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
                                                className="text-center text-primary",
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
                                                className="text-center text-primary",
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
                                                className="text-center text-primary",
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
                                                className="text-center text-primary",
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
                                label_style={"font-size": "0.9rem"},
                            ),
                            dbc.Tab(
                                label="Notes",
                                tab_id="notes",
                                active_label_style={
                                    "color": "var(--color-primary)",
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
                                                className="text-center text-primary",
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
                                                className="text-center text-primary",
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
                                                className="text-center text-primary",
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
                                                className="text-center text-primary",
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
                    "color": "var(--color-primary)",
                    "font-size": "0.9rem",
                },
                label_style={"font-size": "0.9rem"},
            ),
            dbc.Tab(
                label="Stats",
                tab_id="professional-stats",
                active_label_style={
                    "color": "var(--color-primary)",
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
    return html.Div(
        [
            dbc.Alert(
                [
                    html.I(className="bi bi-info-circle me-2"),
                    f"Professional player view for {user.name}. ",
                    (
                        "Use the calendar and session controls below to manage "
                        "training sessions and view performance data."
                    ),
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
                html.I(className="bi bi-lightbulb me-1", style={"color": "#FFA726"}),
                "Enhanced handling: Mid-season transfers and free agents processed with contextual logic",
            ],
            className="mb-0",
            style={"font-size": "0.8rem", "color": "#CCCCCC"},
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
                        className="mb-2 text-muted",
                        style={"font-size": "0.9rem"},
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


def create_team_history_timeline(player_stats, controller):
    """
    Crea un timeline visual de la evolución de equipos del jugador.
    ACTUALIZADA: Integra lógica ETL mejorada para casos como David Cuerva.

    Args:
        player_stats: Lista de estadísticas por temporada
        controller: Instancia de ThaiLeagueController

    Returns:
        Componente HTML con timeline de equipos
    """
    if not player_stats:
        return html.P("No team history available", className="text-muted")

    timeline_items = []

    for i, season_stats in enumerate(player_stats):
        # INTEGRAR NUEVA LÓGICA ETL: Obtener información del equipo con contexto mejorado
        team_info = controller.get_team_info(season_stats)

        season = season_stats.get("season", "Unknown")
        team_display = team_info.get("team_display", "Unknown")
        team_status = team_info.get("team_status", "unknown")
        logo_url = team_info.get("logo_url")
        has_transfer = team_info.get("has_transfer", False)
        is_current = team_info.get("is_current_season", False)

        # Definir estilo según el estado
        if team_status == "active":
            border_color = "#24DE84"
            icon_color = "#24DE84"
            icon = "bi bi-check-circle-fill"
        elif team_status == "transferred":
            border_color = "#FFA726"
            icon_color = "#FFA726"
            icon = "bi bi-arrow-left-right"
        elif team_status == "free_agent":
            border_color = "#E57373"
            icon_color = "#E57373"
            icon = "bi bi-person-dash"
        else:  # historical
            border_color = "#42A5F5"
            icon_color = "#42A5F5"
            icon = "bi bi-clock-history"

        # Badge para temporada actual (mejorado con contexto ETL)
        current_badge = None
        if is_current:
            current_badge = dbc.Badge(
                "Current (ETL)",
                color="success",
                className="ms-2",
                style={"font-size": "0.6rem"},
            )

        # Badge para transferencia (casos como David Cuerva)
        transfer_badge = None
        if has_transfer:
            transfer_badge = dbc.Badge(
                "Mid-Season",
                color="warning",
                className="ms-2",
                style={"font-size": "0.6rem"},
            )
        elif team_status == "free_agent" and is_current:
            # Caso especial: David Cuerva (empezó en equipo, acabó sin equipo)
            transfer_badge = dbc.Badge(
                "Season Ended",
                color="secondary",
                className="ms-2",
                style={"font-size": "0.6rem"},
            )

        # Logo o icono
        team_logo = (
            html.Img(
                src=logo_url,
                style={
                    "width": "24px",
                    "height": "24px",
                    "object-fit": "contain",
                    "border-radius": "4px",
                    "margin-right": "8px",
                },
            )
            if logo_url
            else html.I(
                className="bi bi-shield",
                style={
                    "color": icon_color,
                    "margin-right": "8px",
                    "font-size": "1.2rem",
                },
            )
        )

        # Estadísticas de la temporada
        goals = season_stats.get("goals", 0) or 0
        assists = season_stats.get("assists", 0) or 0
        matches = season_stats.get("matches_played", 0) or 0

        # Item del timeline
        timeline_item = html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div(
                                    [
                                        html.I(
                                            className=icon,
                                            style={
                                                "color": icon_color,
                                                "font-size": "1.2rem",
                                            },
                                        )
                                    ],
                                    style={
                                        "width": "40px",
                                        "height": "40px",
                                        "border-radius": "50%",
                                        "background-color": f"{icon_color}20",
                                        "border": f"2px solid {border_color}",
                                        "display": "flex",
                                        "align-items": "center",
                                        "justify-content": "center",
                                    },
                                )
                            ],
                            width="auto",
                            className="pe-3",
                        ),
                        dbc.Col(
                            [
                                html.Div(
                                    [
                                        html.H6(
                                            [
                                                team_logo,
                                                team_display,
                                                current_badge,
                                                transfer_badge,
                                            ],
                                            style={"color": "#FFFFFF"},
                                            className="mb-1",
                                        ),
                                        html.P(
                                            [
                                                html.Strong(
                                                    season, style={"color": icon_color}
                                                ),
                                                f" | {goals}G {assists}A in {matches} matches",
                                            ],
                                            style={
                                                "color": "#CCCCCC",
                                                "font-size": "0.85rem",
                                            },
                                            className="mb-1",
                                        ),
                                        (
                                            html.P(
                                                team_info.get("status_message", ""),
                                                style={
                                                    "color": "#999999",
                                                    "font-size": "0.8rem",
                                                },
                                                className="mb-0",
                                            )
                                            if team_info.get("status_message")
                                            else None
                                        ),
                                        # NUEVO: Nota especial para casos como David Cuerva
                                        (
                                            html.P(
                                                [
                                                    html.I(
                                                        className="bi bi-info-circle me-1",
                                                        style={"color": "#42A5F5"},
                                                    ),
                                                    "Processed with enhanced ETL logic",
                                                ],
                                                style={
                                                    "color": "#42A5F5",
                                                    "font-size": "0.75rem",
                                                },
                                                className="mb-0 mt-1",
                                            )
                                            if team_status == "free_agent"
                                            else None
                                        ),
                                    ]
                                )
                            ]
                        ),
                    ],
                    className="align-items-center",
                ),
                # Línea conectora (excepto para el último item)
                (
                    html.Div(
                        style={
                            "width": "2px",
                            "height": "30px",
                            "background-color": border_color,
                            "margin-left": "19px",
                            "margin-top": "5px",
                            "opacity": "0.3",
                        }
                    )
                    if i < len(player_stats) - 1
                    else None
                ),
            ],
            className="mb-3",
        )

        timeline_items.append(timeline_item)

    return html.Div(timeline_items)


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
                                        className="mb-1",
                                        style={"font-size": "0.9rem"},
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
                className="ms-2",
                style={"font-size": "0.6rem"},
            )
        )
    elif team_status == "transferred" and has_transfer:
        badges.append(
            dbc.Badge(
                "Mid-Season Transfer",
                color="info",
                className="ms-2",
                style={"font-size": "0.6rem"},
            )
        )
    elif team_status == "active" and is_current:
        badges.append(
            dbc.Badge(
                "Active",
                color="success",
                className="ms-2",
                style={"font-size": "0.6rem"},
            )
        )

    # Badge ETL para indicar datos procesados
    badges.append(
        dbc.Badge(
            "ETL Processed",
            color="secondary",
            className="ms-2",
            style={"font-size": "0.55rem"},
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
            className="ms-2",
            style={"font-size": "0.7rem", "vertical-align": "middle"},
        )

    # Badge para transferencia
    transfer_badge = None
    if has_transfer:
        transfer_badge = dbc.Badge(
            "Transfer",
            color="warning",
            className="ms-2",
            style={"font-size": "0.7rem", "vertical-align": "middle"},
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
                                                        className="ms-2",
                                                        style={"font-size": "0.6rem"},
                                                    ),
                                                ],
                                                className="mb-2",
                                                style={"color": "#FFFFFF"},
                                            ),
                                            html.P(
                                                status_message,
                                                className="mb-0 text-muted",
                                                style={"font-size": "0.9rem"},
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
    Crea contenido de la tab Stats para jugadores profesionales.
    Integra la nueva lógica inteligente del backend para manejo de equipos.

    Args:
        player: Objeto Player
        user: Objeto User

    Returns:
        Contenido HTML con estadísticas profesionales y UI mejorada
    """
    try:
        # Verificar que el usuario sea de tipo profesional
        if user.user_type != UserType.player or not getattr(
            player, "is_professional", False
        ):
            return dbc.Container(
                [
                    dbc.Alert(
                        [
                            html.I(className="bi bi-info-circle me-2"),
                            "Professional statistics are only available for Professional users.",
                            html.Br(),
                            "Upgrade to Professional status to access advanced analytics and statistics.",
                        ],
                        color="info",
                        className="mb-3",
                    ),
                ],
                fluid=True,
                className="p-0",
            )

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

        # INTEGRAR NUEVA LÓGICA DEL BACKEND
        # Usar get_team_info() en lugar de acceso directo a 'team'
        team_info = controller.get_team_info(latest_season)
        current_team_display = team_info.get("team_display", "Unknown")

        # OBTENER INFORMACIÓN DE CALIDAD DE DATOS DEL ETL
        # Obtener la temporada más reciente para información de calidad
        latest_season_str = (
            latest_season.get("season", "2024-25") if latest_season else "2024-25"
        )

        try:
            etl_controller = ETLController()
            processing_status = etl_controller.get_processing_status(latest_season_str)

            # Mapear estado del ETL a estructura esperada por data_quality_info
            status_mapping = {
                "completed": "completed",
                "in_progress": "in_progress",
                "failed": "failed",
                "error": "failed",
                "not_processed": "failed",
            }

            # Calcular quality_score basado en métricas disponibles
            quality_score = 0
            if processing_status.get("status") == "completed":
                total_records = processing_status.get("total_records", 0)
                imported_records = processing_status.get("imported_records", 0)
                errors_count = processing_status.get("errors_count", 0)

                if total_records > 0:
                    import_rate = (imported_records / total_records) * 100
                    error_rate = (
                        (errors_count / total_records) * 100 if errors_count else 0
                    )
                    quality_score = max(0, min(100, import_rate - error_rate))
                else:
                    quality_score = 50  # Score neutro si no hay datos

            data_quality_info = {
                "status": status_mapping.get(
                    processing_status.get("status", "unknown"), "failed"
                ),
                "quality_score": int(quality_score),
                "season": latest_season_str,
                "last_updated": (
                    processing_status.get(
                        "last_updated", datetime.datetime.now()
                    ).strftime("%Y-%m-%d")
                    if processing_status.get("last_updated")
                    else datetime.datetime.now().strftime("%Y-%m-%d")
                ),
                "validation_errors": [],
                "total_records": processing_status.get("total_records", 0),
                "imported_records": processing_status.get("imported_records", 0),
                "matched_players": processing_status.get("matched_players", 0),
                "unmatched_players": processing_status.get("unmatched_players", 0),
            }

        except Exception as e:
            # Fallback seguro si el ETL no está disponible
            data_quality_info = {
                "status": "unknown",
                "quality_score": 0,
                "season": latest_season_str,
                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d"),
                "validation_errors": [f"ETL status unavailable: {str(e)}"],
            }

        # ANÁLISIS CONTEXTUAL (por ahora None hasta implementación completa)
        contextual_analysis = None

        return dbc.Container(
            [
                # Header mejorado con información del jugador e integración de equipo
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Alert(
                                    [
                                        html.I(className="bi bi-trophy me-2"),
                                        f"Professional Stats for {user.name}",
                                        html.Br(),
                                        f"WyscoutID: {player.wyscout_id or 'Not assigned'}",
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
                # Nueva sección: Información actual del equipo con UI mejorada
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H6(
                                    [
                                        html.I(className="bi bi-building me-2"),
                                        "Current Team Status",
                                    ],
                                    className="text-primary mb-3",
                                ),
                                create_team_info_card(team_info),
                                # NUEVO: Mostrar insights contextuales si están disponibles
                                (
                                    create_contextual_insights_card(
                                        contextual_analysis, team_info
                                    )
                                    if contextual_analysis
                                    else None
                                ),
                                # NUEVO: Indicador de estado ETL
                                create_etl_status_indicator(
                                    data_quality_info, team_info
                                ),
                            ],
                            width=12,
                            className="mb-4",
                        )
                    ]
                ),
                # Gráficos principales - Fila 1
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
                                                className="card-title mb-0 text-primary",
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
                                                className="card-title mb-0 text-primary",
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
                # Gráficos secundarios - Fila 2
                dbc.Row(
                    [
                        # Heatmap de rendimiento
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            html.H6(
                                                "Performance Heatmap",
                                                className="card-title mb-0 text-primary",
                                            )
                                        ),
                                        dbc.CardBody(
                                            [create_performance_heatmap(player_stats)],
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
                            lg=6,
                            className="mb-3",
                        ),
                        # Gráfico de barras comparativo
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            html.H6(
                                                "Goals & Assists Comparison",
                                                className="card-title mb-0 text-primary",
                                            )
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
                                ),
                            ],
                            width=12,
                            lg=6,
                            className="mb-3",
                        ),
                    ]
                ),
                # Gráficos de eficiencia - Fila 3
                dbc.Row(
                    [
                        # Métricas de eficiencia
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            html.H6(
                                                "Efficiency Metrics",
                                                className="card-title mb-0 text-primary",
                                            )
                                        ),
                                        dbc.CardBody(
                                            [
                                                create_efficiency_metrics_chart(
                                                    player_stats
                                                )
                                            ],
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
                            className="mb-3",
                        ),
                    ]
                ),
                # Nueva sección: Evolución de equipos a lo largo de las temporadas
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            html.H6(
                                                [
                                                    html.I(
                                                        className="bi bi-clock-history me-2"
                                                    ),
                                                    "Team History Evolution",
                                                ],
                                                className="card-title mb-0 text-primary",
                                            )
                                        ),
                                        dbc.CardBody(
                                            [
                                                create_team_history_timeline(
                                                    player_stats, controller
                                                )
                                            ],
                                            className="p-3",
                                        ),
                                    ],
                                    style={
                                        "background-color": "#2B2B2B",
                                        "border-color": "rgba(36, 222, 132, 0.3)",
                                    },
                                ),
                            ],
                            width=12,
                            className="mb-3",
                        )
                    ]
                ),
                # === NUEVA SECCIÓN: ML ANALYTICS DASHBOARD (Phase 13.3) ===
                html.Hr(style={"border-color": "rgba(36, 222, 132, 0.3)", "margin": "30px 0"}),
                html.H5(
                    [
                        html.I(className="bi bi-robot me-2"),
                        "AI-Powered Performance Analytics",
                        html.Span(
                            " (Machine Learning Pipeline)",
                            className="text-muted",
                            style={"font-size": "0.8rem"}
                        )
                    ],
                    className="text-primary mb-4",
                    style={"text-align": "center"}
                ),
                # ML Dashboard - Fila 1: PDI Evolution y ML Radar Chart
                dbc.Row(
                    [
                        # Gráfico evolución PDI
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            html.H6(
                                                [
                                                    html.I(className="bi bi-graph-up me-2"),
                                                    "Player Development Index (PDI) Evolution",
                                                ],
                                                className="card-title mb-0 text-primary",
                                            )
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
                                ),
                            ],
                            width=12,
                            lg=8,
                            className="mb-3",
                        ),
                        # ML Enhanced Radar Chart
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            html.H6(
                                                [
                                                    html.I(className="bi bi-radar me-2"),
                                                    "ML Performance Profile",
                                                ],
                                                className="card-title mb-0 text-primary",
                                            )
                                        ),
                                        dbc.CardBody(
                                            [create_ml_enhanced_radar_chart(player.player_id)],
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
                # ML Insights y Feature Analysis
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            html.H6(
                                                [
                                                    html.I(className="bi bi-lightbulb me-2"),
                                                    "AI Development Insights",
                                                ],
                                                className="card-title mb-0 text-primary",
                                            )
                                        ),
                                        dbc.CardBody(
                                            [
                                                html.P(
                                                    "🔸 Machine Learning Analysis powered by advanced Feature Engineering",
                                                    className="mb-2",
                                                    style={"color": "#FFFFFF", "font-size": "0.9rem"}
                                                ),
                                                html.P(
                                                    "🔸 PDI combines Universal (40%), Zone (35%), and Position-Specific (25%) metrics",
                                                    className="mb-2",
                                                    style={"color": "#FFFFFF", "font-size": "0.9rem"}
                                                ),
                                                html.P(
                                                    "🔸 Normalized against Thai League benchmarks for fair comparison",
                                                    className="mb-2",
                                                    style={"color": "#FFFFFF", "font-size": "0.9rem"}
                                                ),
                                                html.P(
                                                    "🔸 Real-time updates from professional statistics pipeline",
                                                    className="mb-0",
                                                    style={"color": "#FFFFFF", "font-size": "0.9rem"}
                                                ),
                                            ],
                                            className="p-3",
                                        ),
                                    ],
                                    style={
                                        "background-color": "#2B2B2B",
                                        "border-color": "rgba(36, 222, 132, 0.3)",
                                    },
                                ),
                            ],
                            width=12,
                            className="mb-4",
                        )
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
                                                    className="card-title text-primary",
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
                                                    className="card-title text-primary",
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
                                                    className="card-title text-primary",
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
                                                # Información adicional del equipo
                                                html.Hr(
                                                    style={
                                                        "border-color": "rgba(255,255,255,0.2)"
                                                    }
                                                ),
                                                html.P(
                                                    [
                                                        html.I(
                                                            className="bi bi-shield me-2",
                                                            style={"color": "#24DE84"},
                                                        ),
                                                        current_team_display,
                                                        # NUEVO: Badge ETL para casos especiales
                                                        *(
                                                            create_team_status_badge(
                                                                team_info
                                                            )
                                                            if create_team_status_badge(
                                                                team_info
                                                            )
                                                            else []
                                                        ),
                                                    ],
                                                    style={
                                                        "color": "#24DE84",
                                                        "font-weight": "bold",
                                                    },
                                                    className="mb-1",
                                                ),
                                                (
                                                    html.P(
                                                        team_info.get(
                                                            "status_message", ""
                                                        ),
                                                        style={
                                                            "color": "#CCCCCC",
                                                            "font-size": "0.85rem",
                                                        },
                                                        className="mb-0",
                                                    )
                                                    if team_info.get("status_message")
                                                    else html.Div()
                                                ),
                                                # NUEVO: Información de procesamiento ETL si está disponible
                                                (
                                                    html.Hr(
                                                        style={
                                                            "border-color": "rgba(255,255,255,0.1)"
                                                        }
                                                    )
                                                    if data_quality_info
                                                    else None
                                                ),
                                                (
                                                    html.P(
                                                        [
                                                            html.I(
                                                                className="bi bi-database me-2",
                                                                style={
                                                                    "color": "#42A5F5"
                                                                },
                                                            ),
                                                            f"Processed via ETL: {data_quality_info.get('last_updated', 'N/A')}",
                                                        ],
                                                        style={
                                                            "color": "#42A5F5",
                                                            "font-size": "0.8rem",
                                                        },
                                                        className="mb-0",
                                                    )
                                                    if data_quality_info
                                                    and data_quality_info.get(
                                                        "last_updated"
                                                    )
                                                    else None
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
        import traceback

        print(f"Error in create_professional_stats_content: {e}")
        print(traceback.format_exc())

        return dbc.Alert(
            [
                html.I(className="bi bi-exclamation-triangle me-2"),
                f"Error loading professional stats: {str(e)}",
                html.Br(),
                html.Small(
                    "Check console for detailed ETL pipeline logs.",
                    className="text-muted",
                ),
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


if __name__ == "__main__":
    # Para testing
    pass

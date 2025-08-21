"""
Componentes de gráficos de comparación y análisis.

Contiene funciones para crear gráficos de comparación entre temporadas,
métricas de eficiencia y análisis de clustering.
"""

import logging

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc

logger = logging.getLogger(__name__)


def create_comparison_bar_chart(player_stats):
    """
    Crea gráfico de barras comparativo entre temporadas.
    MOVIDO desde pages/ballers_dash.py

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
    MOVIDO desde pages/ballers_dash.py

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


def create_iep_clustering_chart(position="CF", season="2024-25"):
    """
    Crea gráfico IEP (Índice Eficiencia Posicional) con clustering K-means.
    MOVIDO desde pages/ballers_dash.py

    Sistema complementario no supervisado al PDI supervisado.

    Args:
        position: Posición a analizar
        season: Temporada para clustering

    Returns:
        Componente dcc.Graph con clustering IEP
    """
    try:
        # Importar aquí para evitar dependencias circulares
        from ml_system.evaluation.analysis.iep_analyzer import IEPAnalyzer

        logger.info(f"🧮 Creando análisis IEP clustering para {position} en {season}")

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
                    marker=dict(
                        color=color,
                        size=10,
                        line=dict(width=2, color="white"),
                        opacity=0.8,
                    ),
                    name=cluster_label,
                    text=data["names"],
                    customdata=data["iep_scores"],
                    hovertemplate="<b>%{text}</b><br>"
                    + f"Cluster: {cluster_label}<br>"
                    + "IEP Score: %{customdata:.1f}<br>"
                    + "PC1: %{x:.2f}<br>"
                    + "PC2: %{y:.2f}<extra></extra>",
                )
            )

        # Layout del gráfico
        fig.update_layout(
            title={
                "text": f"🧮 IEP Analysis - {position} K-means Clustering ({season})",
                "x": 0.5,
                "font": {"color": "#24DE84", "size": 16},
            },
            xaxis_title=f"PC1 ({pca_analysis['explained_variance'][0]:.1f}% variance)",
            yaxis_title=f"PC2 ({pca_analysis['explained_variance'][1]:.1f}% variance)",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", family="Inter, sans-serif"),
            legend=dict(
                bgcolor="rgba(0,0,0,0.8)",
                bordercolor="rgba(36,222,132,0.3)",
                borderwidth=1,
                font=dict(color="white", size=11),
                x=1.02,
                xanchor="left",
                y=1,
                yanchor="top",
            ),
            height=600,
            margin=dict(l=80, r=120, t=80, b=80),
            hovermode="closest",
        )

        # Personalizar ejes
        fig.update_xaxes(
            gridcolor="rgba(255,255,255,0.1)",
            tickfont=dict(color="white", size=10),
        )
        fig.update_yaxes(
            gridcolor="rgba(255,255,255,0.1)",
            tickfont=dict(color="white", size=10),
        )

        logger.info(f"✅ IEP clustering creado: {len(players_data)} jugadores")
        return dcc.Graph(figure=fig, className="chart-container")

    except Exception as e:
        logger.error(f"❌ Error creando IEP clustering: {e}")
        return dbc.Alert(f"Error generando clustering: {str(e)}", color="danger")

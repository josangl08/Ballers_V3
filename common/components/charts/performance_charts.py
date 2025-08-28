"""
Componentes de heatmaps y visualizaciones de rendimiento.

Contiene funciones para crear heatmaps de rendimiento temporal,
PDI temporal y otras visualizaciones de performance.
"""

import logging

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc

logger = logging.getLogger(__name__)


def create_performance_heatmap(player_stats):
    """
    Crea heatmap de rendimiento por categorías a lo largo de las temporadas.
    MOVIDO desde pages/ballers_dash.py

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


def create_pdi_temporal_heatmap(player_id, seasons=None):
    """
    Crea un heatmap temporal de los componentes del PDI Jerárquico.

    Args:
        player_id: ID del jugador.
        seasons: Temporadas a analizar (opcional).

    Returns:
        Componente dcc.Graph con el heatmap temporal.
    """
    try:
        from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer

        logger.info(
            f"Creando heatmap temporal de PDI Jerárquico para jugador {player_id}"
        )

        player_analyzer = PlayerAnalyzer()
        all_seasons_data = player_analyzer.get_all_seasons_hierarchical_pdi(player_id)

        if not all_seasons_data:
            return dbc.Alert(
                "No hay datos de PDI Jerárquico para el heatmap.", color="warning"
            )

        if seasons:
            all_seasons_data = [
                s for s in all_seasons_data if s.get("season") in seasons
            ]

        if not all_seasons_data:
            return dbc.Alert(
                "No hay datos para las temporadas seleccionadas.", color="info"
            )

        # Preparar datos para el heatmap
        import pandas as pd

        # Renombrar claves para que se vean mejor en el gráfico
        for row in all_seasons_data:
            row["Overall"] = row.pop("pdi_overall", 0)
            row["Attacking"] = row.pop("pdi_attacking", 0)
            row["Playmaking"] = row.pop("pdi_playmaking", 0)
            row["Defending"] = row.pop("pdi_defending", 0)
            row["Passing"] = row.pop("pdi_passing", 0)
            row["Physical"] = row.pop("pdi_physical", 0)

        df = pd.DataFrame(all_seasons_data)
        df.set_index("Season", inplace=True)
        df = df.T  # Transponer para que los dominios estén en el eje Y

        fig = go.Figure(
            data=go.Heatmap(
                z=df.values,
                x=df.columns,
                y=df.index,
                colorscale="Viridis",
                hoverongaps=False,
                hovertemplate="<b>%{y}</b><br>Season: %{x}<br>Score: %{z:.1f}<extra></extra>",
            )
        )

        fig.update_layout(
            title="Evolución de Dominios de Habilidad (PDI)",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font={"color": "#FFFFFF"},
            height=400,
            margin=dict(l=100, r=50, t=50, b=50),
        )

        return dcc.Graph(figure=fig, className="chart-container")

    except Exception as e:
        logger.error(f"❌ Error creando heat map temporal jerárquico: {e}")
        return dbc.Alert(f"Error generando heatmap: {str(e)}", color="danger")

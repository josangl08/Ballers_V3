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
    Crea heat map temporal de rendimiento PDI por temporada.
    MOVIDO desde pages/ballers_dash.py

    Visualización avanzada que complementa el gráfico de evolución existente.

    Args:
        player_id: ID del jugador
        seasons: Temporadas a analizar (opcional)

    Returns:
        Componente dcc.Graph con heat map temporal
    """
    try:
        # Importar aquí para evitar dependencias circulares
        from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer

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
                "text": "",  # Título vacío - se usa título externo en card header
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

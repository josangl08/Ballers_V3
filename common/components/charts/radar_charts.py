"""
Componentes de radar charts reutilizables.

Contiene funciones para crear diferentes tipos de radar charts:
- Radar básico con métricas universales
- ML Enhanced radar con PDI metrics
- League comparative radar
"""

import logging
from typing import Dict, List, Optional

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html

logger = logging.getLogger(__name__)


def create_radar_chart(player_stats):
    """
    Crea radar chart híbrido avanzado con análisis temporal y comparativa real.
    MOVIDO desde pages/ballers_dash.py

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


def create_ml_enhanced_radar_chart(player_id, seasons=None):
    """
    Crea radar chart mejorado con métricas PDI Calculator científicas usando todas las temporadas.
    MOVIDO desde pages/ballers_dash.py

    MEJORADO: Usa todas las temporadas disponibles con promedios ponderados por recencia.
    MIGRADO: Usa PDI Calculator integrado con PlayerAnalyzer.
    """
    try:
        # Importar aquí para evitar dependencias circulares
        from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer

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

        # Crear radar chart
        categories = list(metrics_data.keys())
        values = list(metrics_data.values())

        fig = go.Figure()

        # Línea del jugador
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=categories,
                fill="toself",
                fillcolor="rgba(36, 222, 132, 0.3)",
                line=dict(color="#24DE84", width=3),
                marker=dict(size=8, color="#24DE84"),
                name=f"Player ({len(all_seasons_metrics)} seasons avg)",
                hovertemplate="<b>%{theta}</b><br>Score: %{r:.1f}<extra></extra>",
            )
        )

        # Líneas de referencia
        fig.add_hline(
            y=75,
            line_dash="dash",
            line_color="rgba(36, 222, 132, 0.5)",
        )
        fig.add_hline(
            y=50,
            line_dash="dash",
            line_color="rgba(255, 255, 255, 0.3)",
        )

        # Layout
        fig.update_layout(
            title=dict(
                text=f"ML Enhanced Analysis - {position}",
                x=0.5,
                font=dict(color="#FFFFFF", size=14),
            ),
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    gridcolor="rgba(255,255,255,0.2)",
                    linecolor="rgba(255,255,255,0.3)",
                    tickfont=dict(color="white", size=9),
                    tickvals=[25, 50, 75, 100],
                    ticktext=["25", "50", "75", "100"],
                ),
                angularaxis=dict(
                    gridcolor="rgba(255,255,255,0.3)",
                    tickfont=dict(color="white", size=10),
                    rotation=0,
                ),
                bgcolor="rgba(0,0,0,0)",
            ),
            showlegend=True,
            legend=dict(
                x=0.5,
                xanchor="center",
                y=1.08,
                yanchor="bottom",
                orientation="h",
                bgcolor="rgba(0,0,0,0.8)",
                bordercolor="rgba(36,222,132,0.3)",
                borderwidth=1,
                font=dict(color="white", size=10),
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=400,
            margin=dict(t=60, b=40, l=60, r=60),
        )

        return dcc.Graph(
            figure=fig, style={"height": "400px"}, config={"displayModeBar": False}
        )

    except Exception as e:
        logger.error(f"Error creando ML enhanced radar chart: {e}")
        return dbc.Alert(f"Error generando radar ML: {str(e)}", color="danger")


def create_league_comparative_radar(player_id, season="2024-25", position_filter=True):
    """
    Crea radar chart comparativo vs promedio de liga tailandesa.

    REUTILIZACIÓN: Usa create_position_radar_chart() que ya implementa
    correctamente comparación CSV vs liga con datos reales (493 jugadores).

    Args:
        player_id: ID del jugador
        season: Temporada a analizar
        position_filter: Si filtrar comparación por posición del jugador

    Returns:
        Componente dcc.Graph con radar comparativo
    """
    try:
        logger.info(
            f"✅ Radar comparativo vs liga - reutilizando Position Analytics (CSV)"
        )

        # REUTILIZACIÓN: Usar función Position Analytics que ya funciona correctamente
        # create_position_radar_chart() ya usa CSVStatsController con datos reales
        return create_position_radar_chart(
            player_id=player_id,
            season=season,
            references=["league"],  # Solo comparación vs liga (493 jugadores CSV)
        )

    except Exception as e:
        logger.error(f"❌ Error en radar comparativo reutilizado: {e}")
        return dbc.Alert(f"Error generando radar comparativo: {str(e)}", color="danger")


def _calculate_league_averages(player_analyzer, season, position=None):
    """
    Calcula promedios de liga para comparación.
    MOVIDO desde pages/ballers_dash.py - función helper para league comparative radar
    """
    try:
        from sqlalchemy import func

        from controllers.db import get_db_session
        from models.professional_stats_model import ProfessionalStats

        with get_db_session() as session:
            # Query base
            query = session.query(
                func.avg(ProfessionalStats.goals_per_90).label("goals_per_90"),
                func.avg(ProfessionalStats.assists_per_90).label("assists_per_90"),
                func.avg(ProfessionalStats.pass_accuracy_pct).label(
                    "pass_accuracy_pct"
                ),
                func.avg(ProfessionalStats.duels_won_pct).label("duels_won_pct"),
                func.avg(ProfessionalStats.defensive_actions_per_90).label(
                    "defensive_actions_per_90"
                ),
            ).filter(ProfessionalStats.season == season)

            # Filtrar por posición si se especifica
            if position:
                query = query.filter(ProfessionalStats.primary_position == position)

            result = query.first()

            if not result:
                return {}

            # Retornar métricas promedio básicas (para compatibilidad)
            return {
                "goals_per_90": result.goals_per_90 or 0,
                "assists_per_90": result.assists_per_90 or 0,
                "pass_accuracy_pct": result.pass_accuracy_pct or 0,
                "duels_won_pct": result.duels_won_pct or 0,
                "defensive_actions_per_90": result.defensive_actions_per_90 or 0,
                # Valores por defecto para métricas ML
                "technical_proficiency": 50,
                "tactical_intelligence": 50,
                "physical_performance": 50,
                "pdi_universal": 50,
                "pdi_zone": 50,
                "pdi_position_specific": 0,
                "consistency_index": 50,
                "pdi_overall": 50,
            }

    except Exception as e:
        logger.error(f"Error calculando promedios de liga: {e}")
        return {}


def normalize_metric_to_percentile(
    player_value: float, league_values: List[float]
) -> float:
    """
    Normaliza el valor de un jugador a percentil 0-100 vs valores de la liga.

    Args:
        player_value: Valor del jugador para la métrica
        league_values: Lista de valores de la liga para esa métrica

    Returns:
        float: Percentil 0-100 (0=peor de liga, 100=mejor de liga)
    """
    if not league_values or len(league_values) == 0:
        return 50.0  # Default si no hay datos

    # Filtrar valores None/null
    valid_values = [v for v in league_values if v is not None]
    if not valid_values:
        return 50.0

    # Calcular percentil
    count_below_or_equal = sum(1 for v in valid_values if v <= player_value)
    percentile = (count_below_or_equal / len(valid_values)) * 100

    # Asegurar rango 0-100
    return min(100.0, max(0.0, percentile))


def create_position_radar_chart(
    player_id: int, season: str = "2024-25", references: List[str] = None
) -> html.Div:
    """
    Creates enhanced position radar chart with multiple references support.
    Uses CSVStatsController for consistent data source (same as position cards).

    MOVED from position_components.py to maintain architectural consistency.
    ENHANCED with multiple references and CSV data source.

    Args:
        player_id: Player ID
        season: Season to analyze
        references: List of reference types ['league', 'team', 'top25']

    Returns:
        html.Div: Container with enhanced radar chart
    """
    try:
        # Valores por defecto
        if references is None:
            references = ["league"]

        # Imports necesarios
        import plotly.graph_objects as go
        from dash import dcc, html

        from common.components.shared.alerts import (
            create_error_alert,
            create_no_data_alert,
        )
        from controllers.csv_stats_controller import CSVStatsController
        from controllers.db import get_db_session
        from ml_system.evaluation.analysis.position_analyzer import PositionAnalyzer
        from models.professional_stats_model import ProfessionalStats

        logger.info(
            f"🎯 Creating position radar: Player {player_id}, Season {season}, References {references}"
        )

        # QUERY DIRECTO: Obtener datos del jugador
        with get_db_session() as session:
            player_stats = (
                session.query(ProfessionalStats)
                .filter(
                    ProfessionalStats.player_id == player_id,
                    ProfessionalStats.season == season,
                )
                .first()
            )

            if not player_stats:
                return create_no_data_alert(f"statistics for season {season}")

            # MAPEAR POSICIÓN: Usar una de las 8 categorías
            analyzer = PositionAnalyzer()
            original_position = player_stats.primary_position or "CF"
            mapped_position = analyzer.position_mapping.get(
                original_position.upper(), "CF"
            )

            logger.info(
                f"📍 Position: {original_position} → {mapped_position} for season {season}"
            )

            # Obtener métricas primarias para esta posición
            position_metrics = analyzer.position_metrics_map.get(mapped_position, {})
            primary_metrics = position_metrics.get("primary_metrics", [])

            if not primary_metrics:
                return create_no_data_alert(f"metrics for position {mapped_position}")

            # Inicializar CSV Controller para datos consistentes
            csv_controller = CSVStatsController()

            # Construir datos del radar NORMALIZADOS con CSVStatsController
            metrics = []
            player_values_normalized = []
            reference_data_normalized = {
                ref: [] for ref in references
            }  # Un array por referencia

            # Obtener todos los valores de la liga para normalizar
            # Usar percentiles existentes como alternativa
            try:
                # Intentar obtener datos completos de la liga
                league_percentiles_data = csv_controller.get_league_percentiles(
                    position=mapped_position,
                    seasons=[season],
                    percentile=50.0,  # Mediana
                )
            except Exception as e:
                logger.warning(f"Error obteniendo datos de liga: {e}")
                league_percentiles_data = None

            for metric_key in primary_metrics[:6]:  # Máximo 6 para claridad
                field_name = analyzer._map_metric_to_field(metric_key)
                if not field_name or not hasattr(player_stats, field_name):
                    continue

                player_value = getattr(player_stats, field_name) or 0.0

                # SYNC: Use same display names as Cards (from PositionAnalyzer)
                position_config = analyzer.position_metrics_map.get(mapped_position, {})
                display_names_map = position_config.get("display_names", {})
                display_name = display_names_map.get(
                    metric_key, metric_key.replace("_", " ").title()
                )
                metrics.append(display_name)

                # UNIFIED SYSTEM: Use exact same percentiles as Cards/Insights/Table
                # This ensures radar chart reflects the same reality as other components
                percentiles_data = csv_controller.get_metric_percentiles(
                    position=mapped_position,
                    seasons=[season],
                    metric=metric_key,
                    player_value=player_value,  # Calculate exact percentile for this player
                )

                if percentiles_data and "player_percentile" in percentiles_data:
                    # Use EXACT percentile from unified system (0-100 scale perfect for radar)
                    player_percentile = percentiles_data["player_percentile"]
                    logger.info(
                        f"🎯 RADAR SYNC: {metric_key} = {player_value:.3f} → {player_percentile:.1f}% percentile"
                    )
                else:
                    # Fallback to median if no data
                    player_percentile = 50.0
                    logger.warning(
                        f"⚠️ RADAR: No percentile data for {metric_key}, using 50%"
                    )

                player_values_normalized.append(player_percentile)

                # Calcular percentiles de referencia simplificados
                for ref in references:
                    if ref == "league":
                        # Promedio de liga = percentil 50 por definición
                        ref_percentile = 50.0

                    elif ref == "team":
                        # Promedio del equipo normalizado
                        team_data = csv_controller.get_team_averages(
                            team=player_stats.team,
                            position=mapped_position,
                            seasons=[season],
                        )
                        if (
                            team_data
                            and "averages" in team_data
                            and metric_key in team_data["averages"]
                            and league_avg_data
                            and "averages" in league_avg_data
                            and metric_key in league_avg_data["averages"]
                        ):

                            team_avg_value = team_data["averages"][metric_key]["value"]
                            league_avg = league_avg_data["averages"][metric_key][
                                "value"
                            ]

                            # Normalizar promedio de equipo usando misma lógica
                            if team_avg_value <= league_avg:
                                if league_avg > 0:
                                    ref_percentile = (team_avg_value / league_avg) * 50
                                else:
                                    ref_percentile = 50
                            else:
                                if league_p75 > league_avg:
                                    ratio = (team_avg_value - league_avg) / (
                                        league_p75 - league_avg
                                    )
                                    ref_percentile = 50 + (ratio * 25)
                                    ref_percentile = min(75, ref_percentile)
                                else:
                                    ref_percentile = 60

                            ref_percentile = min(100, max(0, ref_percentile))
                        else:
                            ref_percentile = 50.0

                    else:  # top25
                        # Calcular MEDIA REAL del top 25% mejores jugadores
                        top25_data = csv_controller.get_top25_averages(
                            position=mapped_position, seasons=[season]
                        )
                        if (
                            top25_data
                            and "averages" in top25_data
                            and metric_key in top25_data["averages"]
                            and league_avg_data
                            and "averages" in league_avg_data
                            and metric_key in league_avg_data["averages"]
                        ):

                            top25_value = top25_data["averages"][metric_key]["value"]
                            league_avg = league_avg_data["averages"][metric_key][
                                "value"
                            ]

                            # Normalizar promedio top25 usando misma lógica que equipo
                            if top25_value <= league_avg:
                                if league_avg > 0:
                                    ref_percentile = (top25_value / league_avg) * 50
                                else:
                                    ref_percentile = 50
                            else:
                                if (
                                    league_p75_data
                                    and "percentiles" in league_p75_data
                                    and metric_key in league_p75_data["percentiles"]
                                ):
                                    league_p75 = league_p75_data["percentiles"][
                                        metric_key
                                    ]["value"]
                                    if league_p75 > league_avg:
                                        ratio = (top25_value - league_avg) / (
                                            league_p75 - league_avg
                                        )
                                        ref_percentile = 50 + (ratio * 25)
                                        # Top 25% debería estar típicamente sobre percentil 75
                                        if top25_value >= league_p75:
                                            excess_ratio = (
                                                top25_value - league_p75
                                            ) / (league_p75 * 0.5)
                                            ref_percentile = 75 + min(
                                                25, excess_ratio * 25
                                            )
                                    else:
                                        ref_percentile = 80  # Top 25% estimado
                                else:
                                    ref_percentile = (
                                        80  # Top 25% estimado sin datos p75
                                    )

                            ref_percentile = min(100, max(0, ref_percentile))
                            logger.info(
                                f"📊 Top25 real value for {metric_key}: {top25_value:.2f} → P{ref_percentile:.0f}"
                            )
                        else:
                            ref_percentile = 75.0  # Fallback al percentil fijo

                    reference_data_normalized[ref].append(ref_percentile)
                    logger.info(
                        f"📊 {metric_key}: Player={player_value:.2f} (P{player_percentile:.0f}), {ref.title()}=P{ref_percentile:.0f}"
                    )

            if not player_values_normalized:
                return create_no_data_alert("valid metrics for this player")

            # Crear figura del radar con múltiples referencias
            fig = go.Figure()

            # Colores para diferentes referencias
            reference_colors = {
                "league": {"color": "#42A5F5", "name": "League Avg."},
                "team": {"color": "#FFA726", "name": "Team Avg."},
                "top25": {"color": "#E57373", "name": "Top 25%"},
            }

            # Agregar líneas de referencia primero (fondo)
            for ref in references:
                if ref in reference_data_normalized and reference_data_normalized[ref]:
                    color_info = reference_colors.get(
                        ref, {"color": "#888888", "name": ref.title()}
                    )
                    # Convertir color hex a RGB para fillcolor
                    hex_color = color_info["color"].lstrip("#")
                    rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

                    # Tooltip personalizado basado en Evolution Analysis
                    if ref == "league":
                        tooltip_template = (
                            "<b>%{theta}</b><br>Liga Avg.: %{r:.0f}<br><extra></extra>"
                        )
                    elif ref == "team":
                        tooltip_template = "<b>%{theta}</b><br>Equipo Avg.: %{r:.0f}<br><extra></extra>"
                    else:  # top25
                        tooltip_template = (
                            "<b>%{theta}</b><br>Top 25%: %{r:.0f}<br><extra></extra>"
                        )

                    fig.add_trace(
                        go.Scatterpolar(
                            r=reference_data_normalized[ref],
                            theta=metrics,
                            fill="toself",
                            name=color_info["name"],
                            line=dict(color=color_info["color"], width=2, dash="dot"),
                            fillcolor=f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.1)",
                            hovertemplate=tooltip_template,
                        )
                    )

            # Línea del jugador (principal, al frente)
            fig.add_trace(
                go.Scatterpolar(
                    r=player_values_normalized,
                    theta=metrics,
                    fill="toself",
                    name=player_stats.player_name,
                    line=dict(color="#24DE84", width=3),
                    fillcolor="rgba(36, 222, 132, 0.25)",
                    hovertemplate="<b>%{theta}</b><br>Jugador: %{r:.0f}<br><extra></extra>",
                )
            )

            # Layout con escala fija 0-100 (percentiles)
            # Todos los valores están normalizados a percentiles

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100],  # Escala fija 0-100 (percentiles)
                        dtick=20,  # Marcas cada 20 percentiles
                        gridcolor="rgba(255,255,255,0.2)",
                        linecolor="rgba(255,255,255,0.3)",
                        tickfont=dict(color="white", size=9),
                        ticksuffix="",  # Sin sufijo, son percentiles
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
                    orientation="h",
                    x=0.5,
                    xanchor="center",
                    y=1.08,
                    yanchor="bottom",
                    bgcolor="rgba(0,0,0,0.8)",
                    bordercolor="rgba(36,222,132,0.3)",
                    borderwidth=1,
                    font=dict(color="white", size=10),
                ),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white", family="Inter, sans-serif"),
                height=450,
                margin=dict(
                    t=40, b=40, l=60, r=60
                ),  # Reducido margen superior sin título
            )

            # Retornar componente con gráfico mejorado y clase CSS consistente
            return dcc.Graph(
                figure=fig,
                className="chart-container",
                config={"displayModeBar": False},
            )

    except Exception as e:
        logger.error(f"❌ Error creando radar chart posicional: {e}")
        return create_error_alert(
            f"Error creando radar chart: {str(e)}", "Error de Visualización"
        )

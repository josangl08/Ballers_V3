"""
Componentes específicos para análisis posicional de jugadores profesionales.

Contiene funciones para crear visualizaciones y análisis específicos por posición,
incluyendo comparaciones duales (liga vs equipo) y métricas posicionales.
"""

import logging
from typing import Dict, List, Optional

import dash_bootstrap_components as dbc
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html

from common.components.shared.alerts import (
    create_error_alert,
    create_loading_alert,
    create_no_data_alert,
)
from common.components.shared.cards import (
    create_comparison_card,
    create_info_card,
    create_metric_card,
)
from controllers.db import get_db_session
from ml_system.evaluation.analysis.position_analyzer import PositionAnalyzer
from models.professional_stats_model import ProfessionalStats

logger = logging.getLogger(__name__)


def get_metric_icon(metric_key: str) -> str:
    """
    Returns specific icon for metric like Performance Overview.

    Args:
        metric_key: Metric identifier

    Returns:
        str: Bootstrap icon class
    """
    metric_icons = {
        "goals_per_90": "bi bi-trophy",
        "assists_per_90": "bi bi-hand-thumbs-up",
        "shots_on_target_pct": "bi bi-bullseye",
        "pass_accuracy_pct": "bi bi-check-circle",
        "xg_per_90": "bi bi-lightning",
        "xa_per_90": "bi bi-lightning",
        "defensive_actions_per_90": "bi bi-shield",
        "aerial_duels_won_pct": "bi bi-arrow-up-circle",
        "tackles_per_90": "bi bi-shield-check",
        "interceptions_per_90": "bi bi-shield-plus",
        "clearances_per_90": "bi bi-shield-slash",
        "blocks_per_90": "bi bi-shield-fill",
        "fouls_committed_per_90": "bi bi-exclamation-triangle",
        "yellow_cards_per_90": "bi bi-square-fill",
        "red_cards_per_90": "bi bi-stop-fill",
        "saves_per_90": "bi bi-hand-index",
        "save_percentage": "bi bi-hand-index-thumb",
        "goals_conceded_per_90": "bi bi-dash-circle",
        "clean_sheets": "bi bi-award",
        "minutes_played": "bi bi-clock",
        "matches_played": "bi bi-calendar-check",
        "dribbles_completed_per_90": "bi bi-arrow-through-heart",
        "dribbles_success_pct": "bi bi-arrow-through-heart",
        "crosses_per_90": "bi bi-arrow-up-right",
        "corners_per_90": "bi bi-triangle",
        "offsides_per_90": "bi bi-flag",
        "progressive_passes_per_90": "bi bi-arrow-right",
        "key_passes_per_90": "bi bi-key",
        "ball_recoveries_per_90": "bi bi-arrow-clockwise",
        "defensive_duels_won_pct": "bi bi-shield-check",
        "touches_in_box_per_90": "bi bi-square",
    }

    return metric_icons.get(metric_key, "bi bi-graph-up")  # Default icon


# === SIMPLIFIED CONFIGURATION PANEL (NEW ARCHITECTURE) ===


def get_available_seasons_for_player(player_id: int) -> List[str]:
    """
    Obtiene las temporadas disponibles para un jugador específico.
    Solo devuelve temporadas que tengan datos reales del jugador.

    Args:
        player_id: ID del jugador

    Returns:
        List[str]: Lista de temporadas ordenadas (más reciente primero)
    """
    try:
        from controllers.db import get_db_session
        from models.professional_stats_model import ProfessionalStats

        with get_db_session() as session:
            # Query directo para obtener temporadas con datos
            seasons = (
                session.query(ProfessionalStats.season)
                .filter(ProfessionalStats.player_id == player_id)
                .distinct()
                .all()
            )

            # Extraer y ordenar temporadas (descendente: 2024-25 → 2023-24)
            season_list = [s[0] for s in seasons if s[0]]
            season_list.sort(
                reverse=True
            )  # Más reciente primero: 2024-25, 2023-24, etc.

            logger.info(f"📅 Player {player_id} has data for seasons: {season_list}")
            return season_list

    except Exception as e:
        logger.error(f"Error getting seasons for player {player_id}: {e}")
        return ["2024-25"]  # Fallback


def create_position_config_panel(player_id: int = None) -> html.Div:
    """
    Creates SIMPLIFIED configuration panel: Season tabs + Reference radio.
    UX Profesional: Una temporada + una referencia a la vez.
    ENHANCED: Dropdown temporadas dinámico basado en datos del jugador.

    RESPONSABILIDAD: UI de selección simplificada (tabs + radio)
    ARQUITECTURA: Una temporada + una referencia simultánea

    Args:
        player_id: ID del jugador para filtrar temporadas disponibles

    Returns:
        html.Div: Simplified configuration panel
    """
    # Obtener temporadas disponibles para el jugador
    if player_id:
        available_seasons = get_available_seasons_for_player(player_id)
    else:
        # Temporadas por defecto si no hay player_id
        available_seasons = ["2024-25", "2023-24", "2022-23", "2021-22", "2020-21"]

    # Crear opciones para dropdown
    season_options = [
        {"label": season, "value": season} for season in available_seasons
    ]
    return html.Div(
        [
            html.H5(
                [html.I(className="bi bi-sliders me-2"), "Analysis Configuration"],
                className="text-primary mb-3",
            ),
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    # Season Selectbox (Solo una temporada)
                                    dbc.Col(
                                        [
                                            html.Label(
                                                "Season:",
                                                className="form-label fw-bold mb-2",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                            ),
                                            dcc.Dropdown(
                                                id="season-selectbox",
                                                options=season_options,  # Dinámico basado en datos
                                                value=(
                                                    available_seasons[0]
                                                    if available_seasons
                                                    else "2024-25"
                                                ),
                                                clearable=False,
                                                searchable=False,
                                                className="mb-3",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    # Reference Multi-Selectbox (Múltiples referencias)
                                    dbc.Col(
                                        [
                                            html.Label(
                                                "Comparison:",
                                                className="form-label fw-bold mb-2",
                                                style={
                                                    "color": "var(--color-white-faded)"
                                                },
                                            ),
                                            dcc.Dropdown(
                                                id="reference-selectbox",
                                                options=[
                                                    {
                                                        "label": "League Avg.",
                                                        "value": "league",
                                                    },
                                                    {
                                                        "label": "Team Avg.",
                                                        "value": "team",
                                                    },
                                                    {
                                                        "label": "Top 25%",
                                                        "value": "top25",
                                                    },
                                                ],
                                                value=[
                                                    "league"
                                                ],  # Default: solo league
                                                multi=True,  # Múltiple selección
                                                clearable=False,
                                                searchable=False,
                                                className="mb-3",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ]
                            )
                        ]
                    )
                ],
                style={
                    "background-color": "#2B2B2B",
                    "border-color": "rgba(36, 222, 132, 0.3)",
                },
                className="position-config-card mb-4",
            ),
        ]
    )


# === LEGACY POSITION METRICS COMPONENTS ===
# NOTA: Estas funciones siguen usando el sistema de comparison_data
# Marcadas para eventual refactoring al sistema simplificado


def create_position_metrics_cards(player_id: int, season: str) -> html.Div:
    """
    Creates position-specific metrics cards with comparisons.
    Shows 6 primary metrics for the specified season with league comparisons.
    Uses direct query instead of PlayerAnalyzer for better performance.

    Args:
        player_id: Player ID
        season: Season to analyze (e.g., "2024-25")

    Returns:
        html.Div: Container with metrics cards
    """
    try:
        with get_db_session() as session:
            # Obtener datos del jugador directamente de BD
            player_stats = (
                session.query(ProfessionalStats)
                .filter(
                    ProfessionalStats.player_id == player_id,
                    ProfessionalStats.season == season,
                )
                .first()
            )

            if not player_stats:
                return create_no_data_alert(
                    f"statistics for season {season}",
                    "Try selecting a different season",
                )

            # Get PRIMARY POSITION from database (directamente de BD)
            primary_position = player_stats.primary_position or "CF"

            # Initialize analyzer to get position-specific metrics for organized cards
            analyzer = PositionAnalyzer()

            # Get mapped position and metrics priority using PRIMARY POSITION
            original_position = (
                primary_position.upper() if primary_position else "UNKNOWN"
            )
            if original_position not in analyzer.position_mapping:
                logger.warning(
                    f"🚨 Metrics cards: Primary position '{primary_position}' not found in mapping. Using CF fallback."
                )
                mapped_position = "CF"
            else:
                mapped_position = analyzer.position_mapping[original_position]

            position_config = analyzer.position_metrics_map.get(
                mapped_position, analyzer.position_metrics_map["CF"]
            )
            primary_metrics = position_config.get("primary_metrics", [])

            # Obtener promedios de liga desde CSV usando CSVStatsController
            from controllers.csv_stats_controller import CSVStatsController

            csv_controller = CSVStatsController()

            # Obtener promedios de liga para la posición mapeada en la temporada específica
            # Usar las métricas optimizadas del PositionAnalyzer
            league_averages_data = csv_controller.get_league_averages(
                position=mapped_position,
                seasons=[season],
                min_matches=5,  # Mínimo 5 partidos jugados para ser considerado
                custom_metrics=primary_metrics[:6],  # Usar las 6 métricas optimizadas
            )

            # Calcular comparaciones usando datos del CSV completo de la liga
            comparisons = {}

            # Debug de datos de liga desde CSV
            if league_averages_data and "averages" in league_averages_data:
                league_averages = league_averages_data["averages"]
                players_analyzed = league_averages_data.get("players_analyzed", 0)
                logger.info(
                    f"   League players analyzed from CSV: {players_analyzed} for position {mapped_position}"
                )

                if players_analyzed == 0:
                    logger.warning(
                        f"      ⚠️ No league players found in CSV for position {mapped_position} in {season}"
                    )
                elif players_analyzed < 10:
                    logger.warning(
                        f"      ⚠️ Only {players_analyzed} league players found in CSV - comparisons may have limited reliability"
                    )
                for i, metric_key in enumerate(
                    primary_metrics[:6], 1
                ):  # Solo 6 métricas principales
                    field_name = analyzer._map_metric_to_field(metric_key)

                    if not field_name:
                        logger.warning(f"      ⚠️ No field mapping for {metric_key}")
                        continue

                    if not hasattr(player_stats, field_name):
                        logger.warning(
                            f"      ⚠️ Field {field_name} not found in player_stats"
                        )
                        continue

                    player_value = getattr(player_stats, field_name) or 0.0
                    display_name = position_config["display_names"].get(
                        metric_key, metric_key.replace("_", " ").title()
                    )

                    # Obtener promedio de liga desde CSV
                    if metric_key in league_averages:
                        league_data = league_averages[metric_key]
                        league_avg = league_data["value"]
                        sample_size = league_data["sample_size"]

                        # Calculate vs league percentage
                        if league_avg > 0.001:
                            vs_league_pct = (
                                (player_value - league_avg) / league_avg
                            ) * 100
                        else:
                            vs_league_pct = 0  # Si promedio es casi 0, no comparar

                        comparisons[metric_key] = {
                            "display_name": display_name,
                            "player_value": player_value,
                            "league_average": league_avg,
                            "vs_league_pct": vs_league_pct,
                        }
                    else:
                        logger.warning(
                            f"      ⚠️ No league average found for {metric_key} in CSV data"
                        )
                        # Fallback sin comparación
                        comparisons[metric_key] = {
                            "display_name": display_name,
                            "player_value": player_value,
                            "league_average": 0.0,
                            "vs_league_pct": 0,
                        }
            else:
                logger.error(
                    f"Failed to load league averages from CSV for {mapped_position} in {season}"
                )
                # Fallback: crear comparaciones sin datos de liga
                for i, metric_key in enumerate(primary_metrics[:6], 1):
                    field_name = analyzer._map_metric_to_field(metric_key)
                    if field_name and hasattr(player_stats, field_name):
                        player_value = getattr(player_stats, field_name) or 0.0
                        display_name = position_config["display_names"].get(
                            metric_key, metric_key.replace("_", " ").title()
                        )

                        comparisons[metric_key] = {
                            "display_name": display_name,
                            "player_value": player_value,
                            "league_average": 0.0,
                            "vs_league_pct": 0,
                        }

            # Verificar que tenemos comparaciones
            if not comparisons:
                return create_no_data_alert(
                    "positional metrics",
                    f"Verify that the player has statistics for season {season}",
                )

            # Warning if position was mapped to fallback
            position_warning = (
                f" ⚠️ (Original: {primary_position})"
                if mapped_position == "CF" and primary_position != "CF"
                else ""
            )

            # Obtener tamaño de muestra para información del header
            position_sample_size = csv_controller.get_position_sample_size(
                position=mapped_position, seasons=[season]
            )

            # Header with dark background using existing info card function
            header_content = html.Div(
                [
                    html.P(
                        [
                            html.Span(
                                f"Player: {player_stats.player_name}", className="me-3"
                            ),
                            html.Span(f"Team: {player_stats.team}", className="me-3"),
                            html.Span(
                                f"Position: {mapped_position} ({position_sample_size} pl.){position_warning}",
                                className="me-3",
                            ),
                            html.Span(f"Season: {season}"),
                        ],
                        className="mb-0",
                        style={"color": "var(--color-white-faded)"},
                    )
                ]
            )

            header_info = create_info_card(
                title=f"Position Analysis - {mapped_position}",
                content=header_content,
                icon="bi bi-geo-alt",
                color="primary",
            )

            cards = [header_info]
            # Get primary metrics for mapped position (already calculated above)
            # Filter comparisons to show only the 6 primary metrics for cards
            primary_comparisons = [
                (metric_key, comparisons[metric_key])
                for metric_key in primary_metrics[:6]
                if metric_key in comparisons
            ]

            # Create individual metric cards with improved layout (limited to 6 primary metrics)
            metrics_rows = []

            # Group primary metrics in rows of 3 for better visual organization
            for i in range(0, len(primary_comparisons), 3):
                row_metrics = primary_comparisons[i : i + 3]
                row_cards = []

                for metric_key, metric_data in row_metrics:
                    display_name = metric_data.get("display_name", metric_key)
                    player_value = metric_data.get("player_value", 0)
                    vs_league_pct = metric_data.get("vs_league_pct", 0)

                    # Determine performance color and dynamic icon based on league comparison
                    if vs_league_pct > 10:
                        color = "success"
                        icon = "bi bi-arrow-up-circle"  # Verde - mejor que liga
                        performance_class = "excellent"
                    elif vs_league_pct > -10:
                        color = "warning"
                        icon = "bi bi-dash-circle"  # Naranja - similar a liga
                        performance_class = "average"
                    else:
                        color = "danger"
                        icon = "bi bi-arrow-down-circle"  # Rojo - peor que liga
                        performance_class = "below-average"

                    # Format value based on metric type
                    if "pct" in metric_key or "percentage" in metric_key:
                        formatted_value = f"{player_value:.1f}%"
                    else:
                        formatted_value = f"{player_value:.2f}"

                    # Subtitle with league comparison only
                    subtitle = f"vs League: {vs_league_pct:+.1f}%"

                    # Create metric card using existing function (ensures consistent styling)
                    metric_card = create_metric_card(
                        title=display_name,
                        value=formatted_value,
                        icon=icon,
                        color=color,
                        subtitle=subtitle,
                    )

                    row_cards.append(
                        dbc.Col(metric_card, width=12, md=6, lg=4, className="mb-3")
                    )

                metrics_rows.append(dbc.Row(row_cards))

            # Structure: header (standalone) + cards with proper spacing
            return html.Div(
                [
                    # Header with mb-4 margin
                    html.Div(header_info, className="mb-4"),
                    # Cards section
                    html.Div(metrics_rows, className="position-metrics-cards"),
                ],
                className="position-metrics-container mb-4",
            )

    except Exception as e:
        logger.error(f"Error creating position metrics cards: {e}")
        return create_error_alert(f"Error en cards: {str(e)}", "Error de Cards")


# create_position_radar_chart MOVED to common/components/charts/radar_charts.py
# for architectural consistency with other chart components


# === LEGACY COMPARISON TABLE ===


def create_position_comparison_table(player_id: int, season: str) -> html.Div:
    """
    Creates multi-season comparison table with latest season + references.
    Includes: Latest season, vs Previous, League, Team, Top 25% comparisons.

    Args:
        player_id: Player ID
        season: Season to analyze (latest available)

    Returns:
        html.Div: Table without card wrapper for consistent background
    """
    try:
        # Imports necesarios
        from controllers.csv_stats_controller import CSVStatsController
        from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer
        from ml_system.evaluation.analysis.position_analyzer import PositionAnalyzer

        analyzer = PositionAnalyzer()
        csv_controller = CSVStatsController()
        player_analyzer = PlayerAnalyzer()

        # Obtener todas las temporadas disponibles del jugador
        available_seasons = player_analyzer.get_available_seasons_for_player(player_id)
        if not available_seasons:
            return create_no_data_alert("No seasons available for this player")

        # Usar SIEMPRE la temporada más actual (ignorar parameter season)
        reference_season = available_seasons[0]  # Más reciente con datos
        previous_season = available_seasons[1] if len(available_seasons) > 1 else None

        with get_db_session() as session:
            # Obtener datos de la temporada de referencia (más actual)
            reference_stats = (
                session.query(ProfessionalStats)
                .filter(
                    ProfessionalStats.player_id == player_id,
                    ProfessionalStats.season == reference_season,
                )
                .first()
            )

            if not reference_stats:
                return create_no_data_alert(
                    f"statistics for reference season {reference_season}"
                )

            # Obtener datos de temporada anterior si existe
            previous_stats = None
            if previous_season:
                previous_stats = (
                    session.query(ProfessionalStats)
                    .filter(
                        ProfessionalStats.player_id == player_id,
                        ProfessionalStats.season == previous_season,
                    )
                    .first()
                )

            # Get PRIMARY POSITION from reference season
            primary_position = reference_stats.primary_position or "CF"
            original_position = (
                primary_position.upper() if primary_position else "UNKNOWN"
            )

            if original_position not in analyzer.position_mapping:
                logger.warning(
                    f"🚨 Comparison table: Primary position '{primary_position}' not found in mapping. Using CF fallback."
                )
                mapped_position = "CF"
            else:
                mapped_position = analyzer.position_mapping[original_position]

            position_config = analyzer.position_metrics_map.get(
                mapped_position, analyzer.position_metrics_map["CF"]
            )
            primary_metrics = position_config.get("primary_metrics", [])
            secondary_metrics = position_config.get("secondary_metrics", [])

            # Tabla muestra primary + secondary, necesitamos promedios liga para TODAS
            all_table_metrics = primary_metrics + [
                m for m in secondary_metrics if m not in primary_metrics
            ]

            # Obtener referencias para la temporada de referencia
            # FIXED: Use ALL metrics that table will show, not just primary
            league_averages_data = csv_controller.get_league_averages(
                position=mapped_position,
                seasons=[reference_season],
                min_matches=5,
                custom_metrics=all_table_metrics,  # FIXED: All metrics displayed in table
            )

            team_averages_data = csv_controller.get_team_averages(
                team=reference_stats.team,
                position=mapped_position,
                seasons=[reference_season],
            )

            top25_averages_data = csv_controller.get_top25_averages(
                position=mapped_position, seasons=[reference_season]
            )

            # Extraer datos de referencias
            league_averages = (
                league_averages_data.get("averages", {}) if league_averages_data else {}
            )
            team_averages = (
                team_averages_data.get("averages", {}) if team_averages_data else {}
            )
            top25_averages = (
                top25_averages_data.get("averages", {}) if top25_averages_data else {}
            )

            # Obtener tamaño de muestra para información del header
            position_sample_size = csv_controller.get_position_sample_size(
                position=mapped_position, seasons=[reference_season]
            )

            # Función helper para formatear valores
            def format_metric_value(value, metric_key):
                if "pct" in metric_key or "percentage" in metric_key:
                    return f"{value:.1f}%"
                else:
                    return f"{value:.2f}"

            # Función helper para formatear comparaciones (diferencias + porcentaje)
            def format_comparison_value(
                player_value,
                reference_value,
                metric_key,
                position=None,
                seasons=None,
                stats_controller=None,
            ):
                """Formatea valor como diferencia + porcentaje vs referencia con contexto estadístico."""
                # Caso 1: Sin datos de referencia (None, NaN, etc.)
                if reference_value is None or str(reference_value).lower() in [
                    "nan",
                    "null",
                    "",
                ]:
                    return "Sin datos"

                # Caso 2: Referencia es 0 (valor legítimo para algunas métricas)
                if reference_value == 0:
                    if player_value == 0:
                        return "0.0 (=)"
                    else:
                        # Obtener contexto estadístico: cuántos jugadores tienen valor 0
                        zero_context = ""
                        if position and seasons and stats_controller:
                            try:
                                zero_count = stats_controller.get_zero_count_for_metric(
                                    position, seasons, metric_key
                                )
                                if zero_count > 0:
                                    zero_context = f" ({zero_count} pl. 0)"
                                else:
                                    zero_context = (
                                        " (vs 0)"  # Fallback si no se puede calcular
                                    )
                            except Exception as e:
                                logger.warning(
                                    f"Error getting zero count for {metric_key}: {e}"
                                )
                                zero_context = " (vs 0)"  # Fallback si hay error
                        else:
                            zero_context = " (vs 0)"  # Fallback si no hay contexto

                        if "pct" in metric_key or "percentage" in metric_key:
                            return f"+{player_value:.1f}%{zero_context}"
                        else:
                            return f"+{player_value:.2f}{zero_context}"

                # Caso 3: Cálculo ESTÁNDAR - misma fórmula que insights
                diff_absolute = player_value - reference_value

                # FÓRMULA ESTÁNDAR: (jugador - referencia) / referencia * 100
                # Igual que insights para consistencia perfecta
                # UNIFIED CONDITION: Same as Cards and Insights
                if reference_value > 0.001:
                    diff_percentage = (diff_absolute / reference_value) * 100
                else:
                    return "Sin datos (ref ≈0)"

                # Limitar porcentajes extremos solo si es necesario
                if abs(diff_percentage) > 500:
                    diff_percentage = 500 if diff_percentage > 0 else -500
                    extreme_indicator = ">" if diff_percentage > 0 else "<"

                    if "pct" in metric_key or "percentage" in metric_key:
                        return f"{diff_absolute:+.1f}% ({extreme_indicator}{diff_percentage:+.0f}%)"
                    else:
                        return f"{diff_absolute:+.2f} ({extreme_indicator}{diff_percentage:+.0f}%)"

                # Formato normal - AHORA CONSISTENTE CON INSIGHTS
                if "pct" in metric_key or "percentage" in metric_key:
                    return f"{diff_absolute:+.1f}% ({diff_percentage:+.1f}%)"
                else:
                    return f"{diff_absolute:+.2f} ({diff_percentage:+.1f}%)"

            # Función helper para crear html.Span con colores (como Performance Overview)
            def get_comparison_span(text, current, previous):
                """Crea html.Span con colores según comparación (verde=mejor, rojo=peor, naranja=similar)."""
                # Casos especiales: Sin datos, vs 0, o igualdad
                if text in ["Sin datos", "N/A"]:
                    return html.Span(
                        text,
                        style={
                            "color": "var(--color-white-faded)",
                            "font-style": "italic",
                        },
                    )

                if "pl. 0" in text or "vs 0" in text:
                    # Comparación vs referencia cero con contexto - mostrar en azul como informativo
                    return html.Span(
                        text, style={"color": "#4DABF7", "font-weight": "bold"}
                    )

                if "(=)" in text:
                    # Valores iguales - mostrar en gris
                    return html.Span(text, style={"color": "var(--color-white-faded)"})

                # Casos especiales para porcentajes extremos
                if ">+500%" in text or "<-500%" in text:
                    # Diferencias extremas - color especial para destacar
                    if ">+500%" in text:
                        return html.Span(
                            text,
                            style={
                                "color": "var(--color-primary)",
                                "font-weight": "bold",
                                "text-shadow": "0 0 3px rgba(36, 222, 132, 0.5)",
                            },
                        )
                    else:
                        return html.Span(
                            text,
                            style={
                                "color": "#FF6B6B",
                                "font-weight": "bold",
                                "text-shadow": "0 0 3px rgba(255, 107, 107, 0.5)",
                            },
                        )

                # Cálculo normal de colores basado en diferencia
                if not previous or previous == 0:
                    return html.Span(text, style={"color": "var(--color-white-faded)"})

                change_pct = ((current - previous) / previous) * 100

                if change_pct > 5:
                    return html.Span(
                        text,
                        style={"color": "var(--color-primary)", "font-weight": "bold"},
                    )
                elif change_pct < -5:
                    return html.Span(
                        text, style={"color": "#FF6B6B", "font-weight": "bold"}
                    )
                else:
                    return html.Span(
                        text, style={"color": "#FFA726", "font-weight": "bold"}
                    )

            # Construir filas organizadas con separadores
            table_rows = []

            # Organizador de métricas por prioridad
            organized_metrics = []

            # Process primary metrics
            for metric_key in primary_metrics:
                field_name = analyzer._map_metric_to_field(metric_key)
                if field_name and hasattr(reference_stats, field_name):
                    reference_value = getattr(reference_stats, field_name) or 0.0
                    previous_value = (
                        getattr(previous_stats, field_name)
                        if previous_stats and hasattr(previous_stats, field_name)
                        else None
                    )

                    display_name = position_config["display_names"].get(
                        metric_key, metric_key.replace("_", " ").title()
                    )

                    organized_metrics.append(
                        (
                            metric_key,
                            {
                                "display_name": display_name,
                                "reference_value": reference_value,
                                "previous_value": previous_value,
                            },
                            "primary",
                        )
                    )

            # Process secondary metrics
            secondary_metrics = position_config.get("secondary_metrics", [])
            for metric_key in secondary_metrics:
                if metric_key not in primary_metrics:
                    field_name = analyzer._map_metric_to_field(metric_key)
                    if field_name and hasattr(reference_stats, field_name):
                        reference_value = getattr(reference_stats, field_name) or 0.0
                        previous_value = (
                            getattr(previous_stats, field_name)
                            if previous_stats and hasattr(previous_stats, field_name)
                            else None
                        )

                        display_name = position_config["display_names"].get(
                            metric_key, metric_key.replace("_", " ").title()
                        )

                        organized_metrics.append(
                            (
                                metric_key,
                                {
                                    "display_name": display_name,
                                    "reference_value": reference_value,
                                    "previous_value": previous_value,
                                },
                                "secondary",
                            )
                        )

            # Start with primary metrics separator
            primary_separator = html.Tr(
                [
                    html.Td(
                        [
                            html.Div(
                                [
                                    html.I(
                                        className="bi bi-star-fill me-2",
                                        style={"color": "#24DE84"},
                                    ),
                                    html.Span(
                                        "PRIMARY METRICS",
                                        style={
                                            "color": "#24DE84",
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
                                    "border-left": "3px solid #24DE84",
                                    "display": "flex",
                                    "align-items": "center",
                                },
                            )
                        ],
                        colSpan=6,
                        style={"padding": "0.5rem 1rem", "border": "none"},
                    )
                ]
            )
            table_rows.append(primary_separator)

            # Process organized metrics with separators
            current_priority = None
            for metric_key, metric_data, priority in organized_metrics:
                # Add secondary separator
                if current_priority == "primary" and priority == "secondary":
                    secondary_separator = html.Tr(
                        [
                            html.Td(
                                [
                                    html.Div(
                                        [
                                            html.I(
                                                className="bi bi-plus-circle me-2",
                                                style={"color": "#4DABF7"},
                                            ),
                                            html.Span(
                                                "POSITIONAL METRICS",
                                                style={
                                                    "color": "#4DABF7",
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
                                            "border-left": "3px solid #4DABF7",
                                            "display": "flex",
                                            "align-items": "center",
                                        },
                                    )
                                ],
                                colSpan=6,
                                style={"padding": "0.5rem 1rem", "border": "none"},
                            )
                        ]
                    )
                    table_rows.append(secondary_separator)

                current_priority = priority
                display_name = metric_data["display_name"]
                reference_value = metric_data["reference_value"]
                previous_value = metric_data["previous_value"]

                # Referencias (liga, equipo, top25)
                league_value = (
                    league_averages.get(metric_key, {}).get("value", 0.0)
                    if metric_key in league_averages
                    else 0.0
                )
                team_value = (
                    team_averages.get(metric_key, {}).get("value", 0.0)
                    if metric_key in team_averages
                    else 0.0
                )
                top25_value = (
                    top25_averages.get(metric_key, {}).get("value", 0.0)
                    if metric_key in top25_averages
                    else 0.0
                )

                # Formatear valores - Reference sin colores (datos absolutos)
                reference_formatted = format_metric_value(reference_value, metric_key)
                reference_span = html.Span(
                    reference_formatted, style={"color": "white", "font-weight": "bold"}
                )

                # Columna vs anterior - crear html.Span con colores
                if previous_value is not None and previous_value > 0:
                    change = reference_value - previous_value
                    change_pct = (change / previous_value) * 100
                    if "pct" in metric_key:
                        vs_previous_formatted = f"{change:+.1f}% ({change_pct:+.1f}%)"
                    else:
                        vs_previous_formatted = f"{change:+.2f} ({change_pct:+.1f}%)"
                    vs_previous_span = get_comparison_span(
                        vs_previous_formatted, reference_value, previous_value
                    )
                else:
                    vs_previous_span = html.Span(
                        "N/A", style={"color": "var(--color-white-faded)"}
                    )

                # Formatear referencias como comparaciones (diferencias + porcentaje) - crear html.Span
                league_formatted = format_comparison_value(
                    reference_value,
                    league_value,
                    metric_key,
                    mapped_position,
                    [reference_season],
                    csv_controller,
                )
                league_span = get_comparison_span(
                    league_formatted, reference_value, league_value
                )

                team_formatted = format_comparison_value(
                    reference_value,
                    team_value,
                    metric_key,
                    mapped_position,
                    [reference_season],
                    csv_controller,
                )
                team_span = get_comparison_span(
                    team_formatted, reference_value, team_value
                )

                top25_formatted = format_comparison_value(
                    reference_value,
                    top25_value,
                    metric_key,
                    mapped_position,
                    [reference_season],
                    csv_controller,
                )
                top25_span = get_comparison_span(
                    top25_formatted, reference_value, top25_value
                )

                # Crear fila con html.Span (método Performance Overview)
                metric_icon = get_metric_icon(metric_key)
                row = html.Tr(
                    [
                        html.Td(
                            [
                                html.I(
                                    className=f"{metric_icon} me-2",
                                    style={"color": "var(--color-primary)"},
                                ),
                                display_name,
                            ],
                            style={"color": "var(--color-white-faded)"},
                        ),
                        html.Td(reference_span, className="text-center"),
                        html.Td(vs_previous_span, className="text-center"),
                        html.Td(league_span, className="text-center"),
                        html.Td(team_span, className="text-center"),
                        html.Td(top25_span, className="text-center"),
                    ]
                )
                table_rows.append(row)

            # Create table header con nuevas columnas incluyendo información de muestra
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
                                f"Reference ({position_sample_size} pl.) - {reference_season}",
                                className="text-center",
                                style={
                                    "color": "var(--color-primary)",
                                    "border-bottom": "2px solid var(--color-primary)",
                                },
                            ),
                            html.Th(
                                f"vs Previous ({previous_season or 'N/A'})",
                                className="text-center",
                                style={
                                    "color": "var(--color-primary)",
                                    "border-bottom": "2px solid var(--color-primary)",
                                },
                            ),
                            html.Th(
                                "vs League",
                                className="text-center",
                                style={
                                    "color": "var(--color-primary)",
                                    "border-bottom": "2px solid var(--color-primary)",
                                },
                            ),
                            html.Th(
                                "vs Team",
                                className="text-center",
                                style={
                                    "color": "var(--color-primary)",
                                    "border-bottom": "2px solid var(--color-primary)",
                                },
                            ),
                            html.Th(
                                "vs Top 25%",
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

            # Create table with same styling as performance overview (transparent, no borders)
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
                className="stats-summary-table",  # Same class as Performance Overview
            )

            # Return only table div (same structure as Performance Overview)
            return html.Div([table])

    except Exception as e:
        logger.error(f"Error creating comparison table: {e}")
        return create_error_alert(f"Error en tabla: {str(e)}", "Error de Tabla")


# === LEGACY INSIGHTS PANEL ===


def create_position_insights_panel(player_id: int, season: str) -> html.Div:
    """
    Creates insights panel with PERFECT SYNC to comparison table.
    ALWAYS uses the most recent season with data (ignores season parameter).
    Uses exact same logic as create_position_comparison_table for consistency.

    Args:
        player_id: Player ID
        season: Season parameter (IGNORED - always use most recent)

    Returns:
        html.Div: Panel with insights synchronized to comparison table
    """
    try:
        # SYNC LOGIC: Same as comparison table - get most recent season
        from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer

        player_analyzer = PlayerAnalyzer()
        available_seasons = player_analyzer.get_available_seasons_for_player(player_id)
        if not available_seasons:
            return create_no_data_alert("No seasons available for this player")

        # CRITICAL: Use SAME logic as comparison table
        reference_season = available_seasons[0]  # Most recent with data

        with get_db_session() as session:
            # Obtener datos de la temporada de referencia (MISMA que tabla)
            player_stats = (
                session.query(ProfessionalStats)
                .filter(
                    ProfessionalStats.player_id == player_id,
                    ProfessionalStats.season == reference_season,
                )
                .first()
            )

            if not player_stats:
                return create_no_data_alert(
                    f"statistics for reference season {reference_season}"
                )

            # Get PRIMARY POSITION from database
            primary_position = player_stats.primary_position or "CF"

            # Initialize analyzer to get position-specific metrics for organized analysis
            analyzer = PositionAnalyzer()

            # Get mapped position and metrics priority using PRIMARY POSITION
            original_position = (
                primary_position.upper() if primary_position else "UNKNOWN"
            )
            if original_position not in analyzer.position_mapping:
                logger.warning(
                    f"🚨 Insights panel: Primary position '{primary_position}' not found in mapping. Using CF fallback."
                )
                mapped_position = "CF"
            else:
                mapped_position = analyzer.position_mapping[original_position]

            position_config = analyzer.position_metrics_map.get(
                mapped_position, analyzer.position_metrics_map["CF"]
            )
            primary_metrics = position_config.get("primary_metrics", [])
            secondary_metrics = position_config.get("secondary_metrics", [])

            # Obtener referencias usando CSVStatsController (same as comparison table)
            from controllers.csv_stats_controller import CSVStatsController

            csv_controller = CSVStatsController()

            # Use same method as Cards and table
            league_averages_data = csv_controller.get_league_averages(
                position=mapped_position, seasons=[reference_season], min_matches=5
            )

            team_averages_data = csv_controller.get_team_averages(
                team=player_stats.team,
                position=mapped_position,
                seasons=[reference_season],
            )

            top25_averages_data = csv_controller.get_top25_averages(
                position=mapped_position, seasons=[reference_season]
            )

            # Extract averages data
            league_averages = (
                league_averages_data.get("averages", {}) if league_averages_data else {}
            )
            team_averages = (
                team_averages_data.get("averages", {}) if team_averages_data else {}
            )
            top25_averages = (
                top25_averages_data.get("averages", {}) if top25_averages_data else {}
            )

            # Calculate comparisons using CSV data (more precise than DB queries)
            comparisons = {}
            all_metrics = primary_metrics + secondary_metrics

            for metric_key in all_metrics:
                field_name = analyzer._map_metric_to_field(metric_key)
                if field_name and hasattr(player_stats, field_name):
                    player_value = getattr(player_stats, field_name) or 0.0
                    display_name = position_config["display_names"].get(
                        metric_key, metric_key.replace("_", " ").title()
                    )

                    # Use CSV data for more precise comparisons (same as comparison table)
                    league_avg = 0.0
                    team_avg = 0.0
                    top25_avg = 0.0

                    if metric_key in league_averages:
                        league_avg = league_averages[metric_key]["value"]
                    if metric_key in team_averages:
                        team_avg = team_averages[metric_key]["value"]
                    if metric_key in top25_averages:
                        top25_avg = top25_averages[metric_key]["value"]

                    # Calculate percentages using CSV data
                    vs_league_pct = (
                        ((player_value - league_avg) / league_avg) * 100
                        if league_avg > 0.001
                        else 0
                    )

                    vs_team_pct = (
                        ((player_value - team_avg) / team_avg) * 100
                        if team_avg > 0
                        else 0
                    )
                    vs_top25_pct = (
                        ((player_value - top25_avg) / top25_avg) * 100
                        if top25_avg > 0
                        else 0
                    )

                    comparisons[metric_key] = {
                        "display_name": display_name,
                        "player_value": player_value,
                        "league_average": league_avg,
                        "team_average": team_avg,
                        "top25_average": top25_avg,
                        "vs_league_pct": vs_league_pct,
                        "vs_team_pct": vs_team_pct,
                        "vs_top25_pct": vs_top25_pct,
                    }

            # ENHANCED ANALYSIS: Multi-reference percentile system
            strengths = []
            weaknesses = []
            elite_strengths = []
            critical_weaknesses = []
            exceptional_elite = []

            # Get percentiles from CSV data for advanced classification WITH EXACT PLAYER PERCENTILES
            percentile_data = {}
            for metric_key in comparisons.keys():
                try:
                    # Get player value for this metric
                    field_name = analyzer._map_metric_to_field(metric_key)
                    player_metric_value = (
                        getattr(player_stats, field_name) or 0.0
                        if field_name and hasattr(player_stats, field_name)
                        else 0.0
                    )

                    # Calculate percentiles INCLUDING exact player percentile
                    percentiles = csv_controller.get_metric_percentiles(
                        position=mapped_position,
                        seasons=[reference_season],
                        metric=metric_key,
                        player_value=player_metric_value,
                    )
                    percentile_data[metric_key] = percentiles
                except Exception as e:
                    logger.warning(f"Could not get percentiles for {metric_key}: {e}")
                    percentile_data[metric_key] = None

            for metric_key, metric_data in comparisons.items():
                display_name = metric_data.get("display_name", metric_key)
                player_value = metric_data.get("player_value", 0)
                vs_league_pct = metric_data.get("vs_league_pct", 0)
                vs_team_pct = metric_data.get("vs_team_pct", 0)
                vs_top25_pct = metric_data.get("vs_top25_pct", 0)

                # Calculate exact player percentile
                percentiles = percentile_data.get(metric_key)
                player_percentile = None

                if percentiles and player_value > 0:
                    try:
                        # Get exact percentile calculated by CSV controller
                        player_percentile = percentiles.get("player_percentile")
                        # Usar percentil exacto si está disponible
                    except Exception as e:
                        logger.warning(
                            f"Error getting exact percentile for {metric_key}: {e}"
                        )
                        player_percentile = None

                # ENHANCED PERFORMANCE CLASSIFICATION
                # Combine multiple criteria for more accurate assessment

                # Exceptional Elite (Top 5% + multiple reference dominance)
                if (player_percentile and player_percentile >= 95) or (
                    vs_league_pct > 100 and vs_top25_pct > 50 and vs_team_pct > 75
                ):
                    exceptional_elite.append(
                        (
                            display_name,
                            vs_league_pct,
                            "Exceptional",
                            (
                                f"Top {100-player_percentile:.1f}%"
                                if player_percentile
                                else "World Class"
                            ),
                        )
                    )

                # Elite Performance (Top 10-25% or strong multi-reference performance)
                elif (player_percentile and player_percentile >= 82) or (
                    vs_league_pct > 50 or (vs_top25_pct > 25 and vs_team_pct > 30)
                ):
                    elite_strengths.append(
                        (
                            display_name,
                            vs_league_pct,
                            "Elite",
                            (
                                f"Top {100-player_percentile:.1f}%"
                                if player_percentile
                                else "Elite Level"
                            ),
                        )
                    )

                # Strong Performance (Above average with solid references)
                elif (player_percentile and player_percentile >= 62) or (
                    vs_league_pct > 20 or vs_team_pct > 25
                ):
                    strengths.append(
                        (
                            display_name,
                            vs_league_pct,
                            "Strong",
                            (
                                f"Top {100-player_percentile:.1f}%"
                                if player_percentile
                                else "Above Average"
                            ),
                        )
                    )

                # Critical Weaknesses (Bottom 10% or severe multi-reference underperformance)
                elif (player_percentile and player_percentile <= 15) or (
                    vs_league_pct < -40 or (vs_top25_pct < -60 and vs_team_pct < -50)
                ):
                    critical_weaknesses.append(
                        (
                            display_name,
                            vs_league_pct,
                            "Critical",
                            (
                                f"Bottom {100-player_percentile:.1f}%"
                                if player_percentile
                                else "Critical Gap"
                            ),
                        )
                    )

                # Areas for Improvement (Below median or consistent underperformance)
                elif (player_percentile and player_percentile <= 37) or (
                    vs_league_pct < -15 or vs_team_pct < -20
                ):
                    weaknesses.append(
                        (
                            display_name,
                            vs_league_pct,
                            "Improvement",
                            (
                                f"Bottom {100-player_percentile:.1f}%"
                                if player_percentile
                                else "Below Expected"
                            ),
                        )
                    )

        # Sort by impact (enhanced with percentile consideration)
        exceptional_elite.sort(key=lambda x: x[1], reverse=True)
        elite_strengths.sort(key=lambda x: x[1], reverse=True)
        strengths.sort(key=lambda x: x[1], reverse=True)
        critical_weaknesses.sort(key=lambda x: x[1])
        weaknesses.sort(key=lambda x: x[1])

        # Create enhanced insights content
        insights_content = []

        # ENHANCED PERFORMANCE SUMMARY with percentile insights
        total_metrics = len(comparisons)
        above_average = len(
            [m for m in comparisons.values() if m.get("vs_league_pct", 0) > 0]
        )
        exceptional_count = len(exceptional_elite)
        elite_count = len(elite_strengths)
        critical_count = len(critical_weaknesses)
        performance_pct = (
            (above_average / total_metrics) * 100 if total_metrics > 0 else 0
        )

        # Calculate percentile distribution
        top_tier_count = exceptional_count + elite_count  # Top 25%
        development_count = len(weaknesses) + critical_count  # Bottom 50%
        balanced_count = total_metrics - top_tier_count - development_count

        insights_content.append(
            html.Div(
                [
                    html.H6(
                        "Advanced Performance Summary", className="text-primary mb-2"
                    ),
                    html.P(
                        f"Above league average: {above_average}/{total_metrics} metrics ({performance_pct:.0f}%)",
                        style={
                            "color": "var(--color-white-faded)",
                            "margin-bottom": "6px",
                        },
                    ),
                    html.P(
                        f"Percentile distribution: Top tier {top_tier_count} | Balanced {balanced_count} | Development {development_count}",
                        style={
                            "color": "var(--color-white-faded)",
                            "margin-bottom": "6px",
                            "font-size": "0.85rem",
                        },
                    ),
                    html.P(
                        f"Exceptional: {exceptional_count} | Elite: {elite_count} | Critical: {critical_count}",
                        style={
                            "color": "var(--color-white-faded)",
                            "margin-bottom": "15px",
                            "font-size": "0.9rem",
                        },
                    ),
                ]
            )
        )

        # Exceptional Elite Performance (if any)
        if exceptional_elite:
            insights_content.append(
                html.Hr(style={"border-color": "rgba(255,255,255,0.2)"})
            )
            insights_content.append(
                html.Div(
                    [
                        html.H6(
                            [
                                html.I(
                                    className="bi bi-award-fill me-2",
                                    style={
                                        "color": "#FFD700",
                                        "text-shadow": "0 0 10px rgba(255,215,0,0.5)",
                                    },
                                ),
                                "Exceptional Performance",
                            ],
                            style={
                                "color": "#FFD700",
                                "margin-bottom": "10px",
                                "text-shadow": "0 0 10px rgba(255,215,0,0.3)",
                            },
                        ),
                        html.Ul(
                            [
                                html.Li(
                                    f"{name}: +{pct:.1f}% vs league ({context})",
                                    style={
                                        "color": "white",
                                        "margin-bottom": "6px",
                                        "font-weight": "500",
                                    },
                                )
                                for name, pct, level, context in exceptional_elite[
                                    :2
                                ]  # Top 2 exceptional
                            ],
                            style={"padding-left": "20px"},
                        ),
                    ]
                )
            )

        # Elite Strengths (if any)
        if elite_strengths:
            insights_content.append(
                html.Hr(style={"border-color": "rgba(255,255,255,0.2)"})
            )
            insights_content.append(
                html.Div(
                    [
                        html.H6(
                            [
                                html.I(
                                    className="bi bi-star-fill me-2",
                                    style={"color": "var(--color-primary)"},
                                ),
                                "Elite Performance",
                            ],
                            style={
                                "color": "var(--color-primary)",
                                "margin-bottom": "10px",
                            },
                        ),
                        html.Ul(
                            [
                                html.Li(
                                    f"{name}: +{pct:.1f}% vs league ({context})",
                                    style={"color": "white", "margin-bottom": "5px"},
                                )
                                for name, pct, level, context in elite_strengths[
                                    :3
                                ]  # Top 3 elite
                            ],
                            style={"padding-left": "20px"},
                        ),
                    ]
                )
            )

        # Key Strengths
        if strengths:
            insights_content.append(
                html.Hr(style={"border-color": "rgba(255,255,255,0.2)"})
            )
            insights_content.append(
                html.Div(
                    [
                        html.H6(
                            [
                                html.I(
                                    className="bi bi-trophy me-2",
                                    style={"color": "var(--color-success)"},
                                ),
                                "Key Strengths",
                            ],
                            style={
                                "color": "var(--color-success)",
                                "margin-bottom": "10px",
                            },
                        ),
                        html.Ul(
                            [
                                html.Li(
                                    f"{name}: +{pct:.1f}% vs league ({context})",
                                    style={"color": "white", "margin-bottom": "5px"},
                                )
                                for name, pct, level, context in strengths[
                                    :3
                                ]  # Top 3 strengths
                            ],
                            style={"padding-left": "20px"},
                        ),
                    ]
                )
            )

        # Critical Weaknesses (if any)
        if critical_weaknesses:
            insights_content.append(
                html.Hr(style={"border-color": "rgba(255,255,255,0.2)"})
            )
            insights_content.append(
                html.Div(
                    [
                        html.H6(
                            [
                                html.I(
                                    className="bi bi-exclamation-triangle-fill me-2",
                                    style={"color": "#FF4444"},
                                ),
                                "Critical Areas",
                            ],
                            style={"color": "#FF4444", "margin-bottom": "10px"},
                        ),
                        html.Ul(
                            [
                                html.Li(
                                    f"{name}: {pct:.1f}% vs league ({context})",
                                    style={"color": "white", "margin-bottom": "5px"},
                                )
                                for name, pct, level, context in critical_weaknesses[
                                    :2
                                ]  # Top 2 critical
                            ],
                            style={"padding-left": "20px"},
                        ),
                    ]
                )
            )

        # Areas for Improvement
        if weaknesses:
            insights_content.append(
                html.Hr(style={"border-color": "rgba(255,255,255,0.2)"})
            )
            insights_content.append(
                html.Div(
                    [
                        html.H6(
                            [
                                html.I(
                                    className="bi bi-arrow-up-circle me-2",
                                    style={"color": "var(--color-warning)"},
                                ),
                                "Areas for Improvement",
                            ],
                            style={
                                "color": "var(--color-warning)",
                                "margin-bottom": "10px",
                            },
                        ),
                        html.Ul(
                            [
                                html.Li(
                                    f"{name}: {pct:.1f}% vs league ({context})",
                                    style={"color": "white", "margin-bottom": "5px"},
                                )
                                for name, pct, level, context in weaknesses[
                                    :3
                                ]  # Top 3 weaknesses
                            ],
                            style={"padding-left": "20px"},
                        ),
                    ]
                )
            )

        # RECOMENDACIONES ELIMINADAS: Solo mostrar análisis objetivo sin recomendaciones
        # Usuario solicitó remover completamente las recomendaciones del panel de insights

        # Create final insights container with CSS classes
        insights_card = html.Div(
            [
                html.H5(
                    [
                        html.I(className="bi bi-graph-up-arrow me-2"),
                        f"Performance Insights - {mapped_position} ({reference_season})",
                    ],
                    className="text-info mb-3",
                ),
                html.Div(insights_content),
            ],
            className="position-table-container p-3 mb-4",
        )  # Reusing table container style

        return insights_card

    except Exception as e:
        logger.error(f"Error creando panel de insights: {e}")
        return create_error_alert(
            f"Error generando insights: {str(e)}", "Error de Análisis"
        )


def _get_position_recommendations(
    position: str, strengths: List, weaknesses: List
) -> List[str]:
    """
    Genera recomendaciones específicas según la posición del jugador.

    Args:
        position: Posición del jugador
        strengths: Lista de fortalezas
        weaknesses: Lista de debilidades

    Returns:
        List[str]: Lista de recomendaciones
    """
    recommendations = []

    # Position-specific recommendations (English interface)
    position_specific = {
        "GK": [
            "Work on distribution with feet to initiate attacks",
            "Improve positioning on aerial balls",
            "Develop communication with defense",
        ],
        "CB": [
            "Train ball distribution and long passes",
            "Improve anticipation in aerial duels",
            "Work on reaction speed",
        ],
        "FB": [
            "Develop attacking combinations down the flank",
            "Improve crosses and assists",
            "Balance defensive and offensive responsibilities",
        ],
        "DMF": [
            "Improve distribution and progressive passes",
            "Develop game vision and anticipation",
            "Work on ball recovery",
        ],
        "CMF": [
            "Balance offensive and defensive responsibilities",
            "Improve box arrival timing",
            "Develop creativity in key passes",
        ],
        "AMF": [
            "Maximize goal-scoring opportunity creation",
            "Improve finishing in opposing area",
            "Develop connection with forwards",
        ],
        "W": [  # Unified for wingers (LW/RW)
            "Improve finishing and goal conversion",
            "Develop dribbling in tight spaces",
            "Work on crosses and assists",
        ],
        "CF": [
            "Improve movement in opposing area",
            "Develop finishing efficiency",
            "Work on back-to-goal play and link-up",
        ],
    }

    base_recommendations = position_specific.get(
        position,
        [
            "Continue developing individual technique",
            "Improve tactical understanding of the game",
            "Maintain consistency in performance",
        ],
    )

    # Add recommendations based on weaknesses
    if weaknesses:
        weakness_name = weaknesses[0][0].lower()
        if "pass" in weakness_name or "distribution" in weakness_name:
            recommendations.append("Focus on passing accuracy in training sessions")
        elif "goal" in weakness_name or "shot" in weakness_name:
            recommendations.append("Dedicate extra time to finishing practice")
        elif "defensive" in weakness_name or "tackle" in weakness_name:
            recommendations.append("Improve defensive aspects and ball recovery")

    # Combine recommendations
    recommendations.extend(base_recommendations[:2])  # Maximum 4 recommendations total

    return recommendations[:4]


# FUNCIÓN ELIMINADA: _get_enhanced_position_recommendations
# Usuario solicitó remover recomendaciones del panel de insights


# === LEGACY FUNCTIONS CLEANED ===
# Funciones orquestadoras problemáticas eliminadas - conservadas solo table, insights y recommendations


# === SIMPLIFIED POSITION ANALYSIS FUNCTIONS (NEW ARCHITECTURE) ===
# RESPONSABILIDAD: Funciones principales del sistema simplificado
# ARQUITECTURA: Usa función original mejorada + UX profesional (tabs + radio)
# REEMPLAZAN: Sistema complejo multi-select anterior


def create_position_analysis_components_simplified(
    player_id: int, season: str, reference: str
) -> html.Div:
    """
    SIMPLIFIED position analysis: Una temporada + una referencia.
    Arquitectura simplificada sin lógica compleja multi-select.

    RESPONSABILIDAD: Coordinar componentes del análisis simplificado
    ARQUITECTURA: Función principal que orquesta cards + radar chart + futuras extensiones
    USO: Llamada desde callback simplificado (season-tabs + reference-radio)

    Args:
        player_id: Player identifier
        season: Single season to analyze
        reference: Single reference type ('league', 'team', 'top25')

    Returns:
        Single component with simplified position analysis
    """
    try:
        # 1. Crear cards de métricas (SIEMPRE última temporada con datos)
        with get_db_session() as session:
            # Encontrar la última temporada con datos
            latest_season_data = (
                session.query(ProfessionalStats)
                .filter(ProfessionalStats.player_id == player_id)
                .order_by(ProfessionalStats.season.desc())
                .first()
            )

            if not latest_season_data:
                return create_no_data_alert(
                    "professional statistics",
                    "This player has no professional data available",
                )

            latest_season = latest_season_data.season

        metrics_cards = create_position_metrics_cards(player_id, latest_season)

        # 2. Crear radar chart para la temporada seleccionada
        from common.components.charts.radar_charts import create_position_radar_chart

        radar_chart = create_position_radar_chart(
            player_id, season, [reference]
        )  # Nueva signatura con lista

        # 3. Crear tabla detallada y insights (próximos componentes)
        # Estos se agregarán al contenido dinámico del callback

        # Obtener datos del jugador para IEP reutilización
        from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer

        with get_db_session() as session:
            from models.player_model import Player

            player_obj = (
                session.query(Player).filter(Player.player_id == player_id).first()
            )
            if player_obj:
                # Obtener player stats usando PlayerAnalyzer
                player_analyzer = PlayerAnalyzer()
                all_stats = player_analyzer.get_player_stats(player_id)
                player_stats_list = all_stats if all_stats else []

                # Reutilizar función IEP de AI Analytics
                try:
                    from pages.ballers_dash import create_iep_clustering_content

                    iep_section = create_iep_clustering_content(
                        player_obj, player_stats_list
                    )
                except Exception as e:
                    logger.warning(f"No se pudo cargar IEP clustering: {e}")
                    iep_section = None
            else:
                iep_section = None

        return html.Div(
            [
                # Cards de métricas (última temporada)
                metrics_cards,
                html.Hr(className="my-4"),
                # Panel de configuración con temporadas dinámicas
                create_position_config_panel(player_id),
                # Radar chart con ID fijo para actualización dinámica
                dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                html.H5(
                                    [
                                        html.I(className="bi bi-radar me-2"),
                                        "Performance Radar",
                                    ],
                                    className="mb-3 text-primary",
                                ),
                                html.Div(
                                    id="position-radar-chart", children=[radar_chart]
                                ),
                            ]
                        )
                    ],
                    className="mb-4",
                    style={
                        "background-color": "#2B2B2B",
                        "border-color": "rgba(36, 222, 132, 0.3)",
                    },
                ),
                # IEP Clustering Analysis (REUTILIZADO de AI Analytics)
                iep_section if iep_section else html.Div(),
                # Panel de insights y recomendaciones (moved before detailed table)
                create_position_insights_panel(player_id, season),
                # Tabla de comparación detallada (moved after insights)
                dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                html.H5(
                                    [
                                        html.I(className="bi bi-table me-2"),
                                        "Detailed Comparison",
                                    ],
                                    className="mb-3 text-primary",
                                ),
                                create_position_comparison_table(player_id, season),
                            ]
                        )
                    ],
                    className="mb-4",
                    style={
                        "background-color": "#2B2B2B",
                        "border-color": "rgba(36, 222, 132, 0.3)",
                    },
                ),
            ]
        )

    except Exception as e:
        logger.error(f"Error creating simplified position analysis: {e}")
        import traceback

        traceback.print_exc()
        return create_error_alert(
            f"Error in position analysis: {str(e)}", "System Error"
        )

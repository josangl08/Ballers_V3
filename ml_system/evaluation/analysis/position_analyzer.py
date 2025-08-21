"""
Position Analyzer - Análisis específico por posición de jugadores.

Este módulo proporciona análisis especializado según la posición del jugador,
incluyendo métricas específicas, comparaciones con promedio del equipo y liga,
y insights posicionales.
"""

import logging
from typing import Dict, Optional, Tuple

from controllers.db import get_db_session
from models.professional_stats_model import ProfessionalStats

logger = logging.getLogger(__name__)


class PositionAnalyzer:
    """
    Analizador especializado en análisis por posición.

    Proporciona métricas específicas para cada posición, comparaciones duales
    (liga vs equipo) y análisis de distribución por zona del campo.
    """

    def __init__(self):
        """Inicializa el analizador con mapeos de métricas por posición."""
        # Importar CSV Controller para promedios reales
        from controllers.csv_stats_controller import CSVStatsController

        self.csv_controller = CSVStatsController()

        # Mapeo completo: 27 posiciones Thai League → 8 grupos científicos (idéntico a PDICalculator)
        self.position_mapping = {
            # Porteros
            "GK": "GK",
            # Defensas centrales
            "CB": "CB",
            "LCB": "CB",
            "RCB": "CB",
            "LCB3": "CB",
            "RCB3": "CB",
            # Laterales
            "LB": "FB",
            "RB": "FB",
            "LB5": "FB",
            "RB5": "FB",
            "LWB": "FB",
            "RWB": "FB",
            # Mediocentros defensivos
            "DMF": "DMF",
            "LDMF": "DMF",
            "RDMF": "DMF",
            # Mediocentros
            "LCMF": "CMF",
            "RCMF": "CMF",
            "LCMF3": "CMF",
            "RCMF3": "CMF",
            # Mediocentros ofensivos
            "AMF": "AMF",
            "LAMF": "AMF",
            "RAMF": "AMF",
            # Extremos
            "LW": "W",
            "RW": "W",
            "LWF": "W",
            "RWF": "W",
            # Delanteros
            "CF": "CF",
        }

        # Mapeo de métricas específicas por grupo posicional (8 grupos granulares)
        self.position_metrics_map = {
            "GK": {
                "primary_metrics": [
                    "defensive_actions_per_90",
                    "aerial_duels_won_pct",
                    "pass_accuracy_pct",
                    "progressive_passes_per_90",
                    "long_passes_accuracy_pct",
                    "fouls_per_90",
                ],
                "secondary_metrics": [
                    "defensive_actions_per_90",
                    "progressive_passes_per_90",
                    "crosses_per_90",
                    "key_passes_per_90",
                    "assists_per_90",
                    "goals_per_90",
                    "shots_on_target_pct",
                    "dribbles_success_pct",
                ],
                "display_names": {
                    "defensive_actions_per_90": "Saves & Stops/90",
                    "aerial_duels_won_pct": "Aerial Command %",
                    "pass_accuracy_pct": "Distribution %",
                    "progressive_passes_per_90": "Progressive Passes/90",
                    "long_passes_accuracy_pct": "Long Pass Accuracy %",
                    "fouls_per_90": "Fouls Conceded/90",
                    "progressive_passes_per_90": "Progressive Passes/90",
                    "crosses_per_90": "Long Passes/90",
                    "key_passes_per_90": "Key Passes/90",
                    "assists_per_90": "Assists/90",
                    "goals_per_90": "Goals/90",
                    "shots_on_target_pct": "Shots on Target %",
                    "dribbles_success_pct": "Dribbles %",
                },
                "good_ranges": {
                    "save_percentage": (70, 100),
                    "goals_conceded_per_90": (0, 1.0),  # Lower is better
                    "pass_accuracy_pct": (60, 100),
                    "aerial_duels_won_pct": (50, 100),
                    "clean_sheets": (8, 20),
                    "defensive_actions_per_90": (5.0, 15.0),
                    "progressive_passes_per_90": (3.0, 12.0),
                    "crosses_per_90": (5.0, 15.0),
                    "key_passes_per_90": (0.1, 2.0),
                    "assists_per_90": (0.0, 0.3),
                    "goals_per_90": (0.0, 0.1),
                    "shots_on_target_pct": (30, 80),
                    "dribbles_success_pct": (40, 80),
                },
            },
            "CB": {
                "primary_metrics": [
                    "aerial_duels_won_pct",
                    "defensive_duels_won_pct",
                    "interceptions_per_90",
                    "sliding_tackles_per_90",
                    "pass_accuracy_pct",
                    "progressive_passes_per_90",
                ],
                "secondary_metrics": [
                    "defensive_actions_per_90",
                    "tackles_per_90",
                    "ball_recoveries_per_90",
                    "key_passes_per_90",
                    "assists_per_90",
                    "goals_per_90",
                    "crosses_per_90",
                    "dribbles_success_pct",
                ],
                "display_names": {
                    "aerial_duels_won_pct": "Aerial Dominance %",
                    "defensive_duels_won_pct": "Defensive Duels %",
                    "interceptions_per_90": "Interceptions/90",
                    "sliding_tackles_per_90": "Tackles/90",
                    "pass_accuracy_pct": "Pass Accuracy %",
                    "progressive_passes_per_90": "Progressive Passes/90",
                    "defensive_actions_per_90": "Defensive Actions/90",
                    "tackles_per_90": "Tackles/90",
                    "ball_recoveries_per_90": "Ball Recoveries/90",
                    "key_passes_per_90": "Key Passes/90",
                    "assists_per_90": "Assists/90",
                    "goals_per_90": "Goals/90",
                    "crosses_per_90": "Long Balls/90",
                    "dribbles_success_pct": "Dribbles %",
                },
                "good_ranges": {
                    "aerial_duels_won_pct": (55, 100),
                    "interceptions_per_90": (1.5, 6.0),
                    "defensive_duels_won_pct": (60, 100),
                    "pass_accuracy_pct": (80, 100),
                    "progressive_passes_per_90": (3.0, 10.0),
                    "defensive_actions_per_90": (8.0, 20.0),
                    "tackles_per_90": (1.0, 4.0),
                    "ball_recoveries_per_90": (5.0, 15.0),
                    "key_passes_per_90": (0.1, 1.5),
                    "assists_per_90": (0.0, 0.2),
                    "goals_per_90": (0.0, 0.3),
                    "crosses_per_90": (2.0, 8.0),
                    "dribbles_success_pct": (50, 85),
                },
            },
            "FB": {  # Full Backs (laterales)
                "primary_metrics": [
                    "long_passes_per_90",
                    "assists_per_90",
                    "defensive_duels_won_pct",
                    "dribbles_success_pct",
                    "key_passes_per_90",
                    "sliding_tackles_per_90",
                ],
                "secondary_metrics": [
                    "cross_accuracy_pct",
                    "tackles_per_90",
                    "key_passes_per_90",
                    "goals_per_90",
                    "dribbles_success_pct",
                    "aerial_duels_won_pct",
                    "interceptions_per_90",
                    "ball_recoveries_per_90",
                ],
                "display_names": {
                    "long_passes_per_90": "Crosses & Long Balls/90",
                    "assists_per_90": "Assists/90",
                    "defensive_duels_won_pct": "Defensive Duels %",
                    "dribbles_success_pct": "Dribbles Success %",
                    "key_passes_per_90": "Key Passes/90",
                    "sliding_tackles_per_90": "Tackles/90",
                    "pass_accuracy_pct": "Pass Accuracy %",
                    "cross_accuracy_pct": "Cross Accuracy %",
                    "tackles_per_90": "Tackles/90",
                    "key_passes_per_90": "Key Passes/90",
                    "goals_per_90": "Goals/90",
                    "dribbles_success_pct": "Dribbles %",
                    "aerial_duels_won_pct": "Aerial Duels %",
                    "interceptions_per_90": "Interceptions/90",
                    "ball_recoveries_per_90": "Ball Recoveries/90",
                },
                "good_ranges": {
                    "crosses_per_90": (2.0, 8.0),
                    "assists_per_90": (0.1, 0.6),
                    "defensive_duels_won_pct": (50, 80),
                    "progressive_passes_per_90": (4.0, 12.0),
                    "pass_accuracy_pct": (75, 95),
                    "cross_accuracy_pct": (25, 50),
                    "tackles_per_90": (1.5, 4.0),
                    "key_passes_per_90": (0.3, 2.0),
                    "goals_per_90": (0.0, 0.3),
                    "dribbles_success_pct": (55, 85),
                    "aerial_duels_won_pct": (40, 75),
                    "interceptions_per_90": (1.0, 4.0),
                    "ball_recoveries_per_90": (4.0, 10.0),
                },
            },
            "DMF": {  # Mediocentros defensivos
                "primary_metrics": [
                    "defensive_actions_per_90",
                    "interceptions_per_90",
                    "sliding_tackles_per_90",
                    "pass_accuracy_pct",
                    "progressive_passes_per_90",
                    "defensive_duels_won_pct",
                ],
                "secondary_metrics": [
                    "tackles_per_90",
                    "key_passes_per_90",
                    "assists_per_90",
                    "goals_per_90",
                    "aerial_duels_won_pct",
                    "dribbles_success_pct",
                    "crosses_per_90",
                    "shots_on_target_pct",
                ],
                "display_names": {
                    "defensive_actions_per_90": "Defensive Actions/90",
                    "interceptions_per_90": "Interceptions/90",
                    "sliding_tackles_per_90": "Tackles/90",
                    "pass_accuracy_pct": "Pass Accuracy %",
                    "progressive_passes_per_90": "Progressive Passes/90",
                    "defensive_duels_won_pct": "Defensive Duels %",
                    "key_passes_per_90": "Key Passes/90",
                    "assists_per_90": "Assists/90",
                    "goals_per_90": "Goals/90",
                    "aerial_duels_won_pct": "Aerial Duels %",
                    "dribbles_success_pct": "Dribbles %",
                    "crosses_per_90": "Long Passes/90",
                    "shots_on_target_pct": "Shots on Target %",
                },
                "good_ranges": {
                    "pass_accuracy_pct": (85, 100),
                    "ball_recoveries_per_90": (5.0, 12.0),
                    "interceptions_per_90": (1.0, 4.0),
                    "progressive_passes_per_90": (8.0, 20.0),
                    "defensive_duels_won_pct": (55, 85),
                    "tackles_per_90": (2.0, 5.0),
                    "key_passes_per_90": (0.5, 3.0),
                    "assists_per_90": (0.0, 0.4),
                    "goals_per_90": (0.0, 0.3),
                    "aerial_duels_won_pct": (45, 80),
                    "dribbles_success_pct": (60, 90),
                    "crosses_per_90": (3.0, 10.0),
                    "shots_on_target_pct": (30, 70),
                },
            },
            "CMF": {  # Mediocentros
                "primary_metrics": [
                    "pass_accuracy_pct",
                    "key_passes_per_90",
                    "progressive_passes_per_90",
                    "assists_per_90",
                    "dribbles_success_pct",
                    "goals_per_90",
                ],
                "secondary_metrics": [
                    "goals_per_90",
                    "ball_recoveries_per_90",
                    "tackles_per_90",
                    "interceptions_per_90",
                    "crosses_per_90",
                    "aerial_duels_won_pct",
                    "defensive_duels_won_pct",
                    "shots_on_target_pct",
                ],
                "display_names": {
                    "pass_accuracy_pct": "Pass Accuracy %",
                    "key_passes_per_90": "Key Passes/90",
                    "progressive_passes_per_90": "Progressive Passes/90",
                    "assists_per_90": "Assists/90",
                    "dribbles_success_pct": "Dribbles %",
                    "goals_per_90": "Goals/90",
                    "ball_recoveries_per_90": "Ball Recoveries/90",
                    "tackles_per_90": "Tackles/90",
                    "interceptions_per_90": "Interceptions/90",
                    "crosses_per_90": "Long Passes/90",
                    "aerial_duels_won_pct": "Aerial Duels %",
                    "defensive_duels_won_pct": "Defensive Duels %",
                    "shots_on_target_pct": "Shots on Target %",
                },
                "good_ranges": {
                    "pass_accuracy_pct": (80, 100),
                    "key_passes_per_90": (1.0, 4.0),
                    "progressive_passes_per_90": (5.0, 15.0),
                    "assists_per_90": (0.1, 0.8),
                    "dribbles_success_pct": (60, 90),
                    "goals_per_90": (0.1, 0.5),
                    "ball_recoveries_per_90": (3.0, 8.0),
                    "tackles_per_90": (1.0, 3.5),
                    "interceptions_per_90": (0.5, 3.0),
                    "crosses_per_90": (2.0, 8.0),
                    "aerial_duels_won_pct": (40, 75),
                    "defensive_duels_won_pct": (50, 80),
                    "shots_on_target_pct": (35, 70),
                },
            },
            "AMF": {  # Mediocentros ofensivos
                "primary_metrics": [
                    "key_passes_per_90",
                    "assists_per_90",
                    "goals_per_90",
                    "dribbles_success_pct",
                    "shots_on_target_pct",
                    "touches_in_box_per_90",
                ],
                "secondary_metrics": [
                    "shot_assists_per_90",
                    "shots_on_target_pct",
                    "pass_accuracy_pct",
                    "crosses_per_90",
                    "ball_recoveries_per_90",
                    "tackles_per_90",
                    "aerial_duels_won_pct",
                    "touches_in_box_per_90",
                ],
                "display_names": {
                    "key_passes_per_90": "Key Passes/90",
                    "assists_per_90": "Assists/90",
                    "goals_per_90": "Goals/90",
                    "dribbles_success_pct": "Dribbles %",
                    "progressive_passes_per_90": "Progressive Passes/90",
                    "shot_assists_per_90": "Shot Assists/90",
                    "shots_on_target_pct": "Shots on Target %",
                    "pass_accuracy_pct": "Pass Accuracy %",
                    "crosses_per_90": "Through Balls/90",
                    "ball_recoveries_per_90": "Ball Recoveries/90",
                    "tackles_per_90": "Tackles/90",
                    "aerial_duels_won_pct": "Aerial Duels %",
                    "touches_in_box_per_90": "Box Touches/90",
                },
                "good_ranges": {
                    "key_passes_per_90": (1.5, 5.0),
                    "assists_per_90": (0.2, 1.0),
                    "goals_per_90": (0.2, 0.8),
                    "dribbles_success_pct": (60, 90),
                    "progressive_passes_per_90": (4.0, 12.0),
                    "shot_assists_per_90": (1.0, 4.0),
                    "shots_on_target_pct": (40, 75),
                    "pass_accuracy_pct": (75, 95),
                    "crosses_per_90": (1.0, 5.0),
                    "ball_recoveries_per_90": (2.0, 6.0),
                    "tackles_per_90": (0.5, 2.5),
                    "aerial_duels_won_pct": (35, 70),
                    "touches_in_box_per_90": (2.0, 6.0),
                },
            },
            "W": {  # Extremos/Wings
                "primary_metrics": [
                    "goals_per_90",
                    "assists_per_90",
                    "dribbles_success_pct",
                    "long_passes_per_90",
                    "shots_on_target_pct",
                    "touches_in_box_per_90",
                ],
                "secondary_metrics": [
                    "shots_on_target_pct",
                    "progressive_passes_per_90",
                    "pass_accuracy_pct",
                    "touches_in_box_per_90",
                    "shot_assists_per_90",
                    "ball_recoveries_per_90",
                    "tackles_per_90",
                    "aerial_duels_won_pct",
                ],
                "display_names": {
                    "goals_per_90": "Goals/90",
                    "assists_per_90": "Assists/90",
                    "dribbles_success_pct": "Dribbles Success %",
                    "long_passes_per_90": "Crosses & Wide Passes/90",
                    "shots_on_target_pct": "Shots on Target %",
                    "touches_in_box_per_90": "Box Touches/90",
                    "shots_on_target_pct": "Shots on Target %",
                    "progressive_passes_per_90": "Progressive Passes/90",
                    "pass_accuracy_pct": "Pass Accuracy %",
                    "touches_in_box_per_90": "Box Touches/90",
                    "shot_assists_per_90": "Shot Assists/90",
                    "ball_recoveries_per_90": "Ball Recoveries/90",
                    "tackles_per_90": "Tackles/90",
                    "aerial_duels_won_pct": "Aerial Duels %",
                },
                "good_ranges": {
                    "goals_per_90": (0.2, 1.0),
                    "assists_per_90": (0.1, 0.8),
                    "dribbles_success_pct": (60, 90),
                    "key_passes_per_90": (0.8, 3.5),
                    "crosses_per_90": (2.0, 6.0),
                    "shots_on_target_pct": (30, 60),
                    "progressive_passes_per_90": (3.0, 9.0),
                    "pass_accuracy_pct": (70, 90),
                    "touches_in_box_per_90": (2.0, 7.0),
                    "shot_assists_per_90": (0.5, 3.0),
                    "ball_recoveries_per_90": (2.0, 6.0),
                    "tackles_per_90": (0.5, 2.5),
                    "aerial_duels_won_pct": (30, 65),
                },
            },
            "CF": {  # Delanteros centro
                "primary_metrics": [
                    "goals_per_90",
                    "shots_on_target_pct",
                    "aerial_duels_won_pct",
                    "touches_in_box_per_90",
                    "goal_conversion_pct",
                    "assists_per_90",
                ],
                "secondary_metrics": [
                    "key_passes_per_90",
                    "dribbles_success_pct",
                    "progressive_passes_per_90",
                    "pass_accuracy_pct",
                    "shot_assists_per_90",
                    "crosses_per_90",
                    "ball_recoveries_per_90",
                    "tackles_per_90",
                ],
                "display_names": {
                    "goals_per_90": "Goals/90",
                    "shots_on_target_pct": "Shots on Target %",
                    "aerial_duels_won_pct": "Aerial Duels %",
                    "touches_in_box_per_90": "Box Touches/90",
                    "goal_conversion_pct": "Goal Conversion %",
                    "assists_per_90": "Assists/90",
                    "dribbles_success_pct": "Dribbles %",
                    "progressive_passes_per_90": "Progressive Passes/90",
                    "pass_accuracy_pct": "Pass Accuracy %",
                    "shot_assists_per_90": "Shot Assists/90",
                    "crosses_per_90": "Hold-up Play/90",
                    "ball_recoveries_per_90": "Ball Recoveries/90",
                    "tackles_per_90": "Pressing/90",
                },
                "good_ranges": {
                    "goals_per_90": (0.4, 1.5),
                    "shots_on_target_pct": (40, 70),
                    "touches_in_box_per_90": (3.0, 8.0),
                    "aerial_duels_won_pct": (45, 80),
                    "assists_per_90": (0.1, 0.5),
                    "key_passes_per_90": (0.5, 2.5),
                    "dribbles_success_pct": (55, 85),
                    "progressive_passes_per_90": (2.0, 7.0),
                    "pass_accuracy_pct": (65, 85),
                    "shot_assists_per_90": (0.3, 2.0),
                    "crosses_per_90": (1.0, 4.0),
                    "ball_recoveries_per_90": (1.5, 5.0),
                    "tackles_per_90": (0.5, 2.0),
                },
            },
        }

    def get_position_specific_metrics(
        self, player_id: int, position: str, season: str = "2024-25"
    ) -> Dict:
        """
        Obtiene métricas específicas para una posición determinada.

        Args:
            player_id: ID del jugador
            position: Posición específica (ej: RDMF, LCMF3, RW)
            season: Temporada a analizar

        Returns:
            Dict con las métricas específicas de la posición
        """
        try:
            # Normalizar posición específica y mapear a grupo granular
            position = position.upper()
            mapped_position = self.position_mapping.get(position, "CF")

            if mapped_position not in self.position_metrics_map:
                logger.warning(
                    f"Posición mapeada {mapped_position} no reconocida, usando CF por defecto"
                )
                mapped_position = "CF"

            position_config = self.position_metrics_map[mapped_position]

            with get_db_session() as session:
                # Obtener estadísticas del jugador
                player_stats = (
                    session.query(ProfessionalStats)
                    .filter(
                        ProfessionalStats.player_id == player_id,
                        ProfessionalStats.season == season,
                    )
                    .first()
                )

                if not player_stats:
                    logger.warning(
                        f"No se encontraron estadísticas para jugador {player_id} en temporada {season}"
                    )
                    return {}

                # Extraer métricas específicas de la posición (primarias y secundarias)
                metrics = {}

                # Incluir métricas primarias
                for metric_key in position_config["primary_metrics"]:
                    field_name = self._map_metric_to_field(metric_key)
                    value = getattr(player_stats, field_name, 0) or 0

                    metrics[metric_key] = {
                        "value": value,
                        "display_name": position_config["display_names"][metric_key],
                        "good_range": position_config["good_ranges"][metric_key],
                        "percentile": self._calculate_percentile(
                            value, position_config["good_ranges"][metric_key]
                        ),
                        "priority": "primary",
                    }

                # Incluir métricas secundarias para detail comparison
                for metric_key in position_config["secondary_metrics"]:
                    field_name = self._map_metric_to_field(metric_key)
                    value = getattr(player_stats, field_name, 0) or 0

                    # Debug logging for key metrics
                    if metric_key in [
                        "goals_per_90",
                        "assists_per_90",
                        "key_passes_per_90",
                    ]:
                        logger.info(
                            f"🔍 METRIC DEBUG - {metric_key}: field_name='{field_name}', value={value}, raw_value={getattr(player_stats, field_name, 'NOT_FOUND')}"
                        )

                    metrics[metric_key] = {
                        "value": value,
                        "display_name": position_config["display_names"][metric_key],
                        "good_range": position_config["good_ranges"][metric_key],
                        "percentile": self._calculate_percentile(
                            value, position_config["good_ranges"][metric_key]
                        ),
                        "priority": "secondary",
                    }

                return {
                    "position": mapped_position,
                    "original_position": position,
                    "primary_position": player_stats.primary_position,  # REAL position from BD
                    "player_id": player_id,
                    "season": season,
                    "metrics": metrics,
                    "team": player_stats.team,
                    "player_name": player_stats.player_name,
                }

        except Exception as e:
            logger.error(f"Error obteniendo métricas posicionales: {e}")
            return {}

    # Método eliminado - usar CSV Controller para promedios reales
    # def calculate_team_position_averages() - DEPRECATED

    # Método eliminado - usar CSV Controller para promedios reales
    # def calculate_league_position_averages() - DEPRECATED

    # Método eliminado - será reemplazado por compare_dynamic con CSV Controller
    # def compare_player_vs_team_and_league() - DEPRECATED

    def _map_metric_to_field(self, metric_key: str) -> str:
        """
        Mapea nombres de métricas a campos de la base de datos.

        Args:
            metric_key: Clave de la métrica

        Returns:
            Nombre del campo en la base de datos
        """
        # Mapeo de métricas a campos de base de datos (ACTUALIZADO para métricas optimizadas)
        field_mapping = {
            # === MÉTRICAS OPTIMIZADAS NUEVAS ===
            # GK optimizadas
            "defensive_actions_per_90": "defensive_actions_per_90",
            "aerial_duels_won_pct": "aerial_duels_won_pct",
            "pass_accuracy_pct": "pass_accuracy_pct",
            "progressive_passes_per_90": "progressive_passes_per_90",
            "long_passes_accuracy_pct": "long_passes_accuracy_pct",
            "fouls_per_90": "fouls_per_90",
            # CB optimizadas
            "sliding_tackles_per_90": "sliding_tackles_per_90",
            "interceptions_per_90": "interceptions_per_90",
            "defensive_duels_won_pct": "defensive_duels_won_pct",
            "duels_won_pct": "duels_won_pct",
            # FB optimizadas
            "long_passes_per_90": "long_passes_per_90",
            "assists_per_90": "assists_per_90",
            "dribbles_success_pct": "dribbles_success_pct",
            "key_passes_per_90": "key_passes_per_90",
            # CMF/AMF/W/CF optimizadas
            "goals_per_90": "goals_per_90",
            "shots_on_target_pct": "shots_on_target_pct",
            "touches_in_box_per_90": "touches_in_box_per_90",
            "goal_conversion_pct": "goal_conversion_pct",  # CORREGIDO: mapeo directo
            "xg_per_90": "xg_per_90",
            "xa_per_90": "xa_per_90",
            # === MÉTRICAS LEGACY (mantener compatibilidad) ===
            "save_percentage": "defensive_actions_per_90",  # Aproximación
            "clean_sheets_pct": "defensive_actions_per_90",  # Aproximación
            "goals_conceded_per_90": "fouls_per_90",  # Aproximación invertida
            "distribution_accuracy": "pass_accuracy_pct",
            "cross_stop_pct": "aerial_duels_won_pct",
            "tackles_success_pct": "defensive_duels_won_pct",
            "clearances_per_90": "defensive_actions_per_90",
            "crosses_per_90": "long_passes_per_90",  # Aproximación
            "cross_accuracy_pct": "long_passes_accuracy_pct",  # Aproximación
            "tackles_per_90": "sliding_tackles_per_90",  # Aproximación
            "ball_recoveries_per_90": "defensive_actions_per_90",  # Aproximación
            "shot_assists_per_90": "key_passes_per_90",  # Aproximación
        }

        return field_mapping.get(metric_key, metric_key)

    def _calculate_percentile(
        self, value: float, good_range: Tuple[float, float]
    ) -> float:
        """
        Calcula percentil basado en el rango bueno para la métrica.

        Args:
            value: Valor actual
            good_range: Rango (mín, máx) considerado bueno

        Returns:
            Percentil de 0 a 100
        """
        min_good, max_good = good_range

        if value <= min_good:
            return 25.0
        elif value >= max_good:
            return 95.0
        else:
            # Interpolación lineal entre 25 y 95
            range_size = max_good - min_good
            position_in_range = value - min_good
            return 25.0 + (position_in_range / range_size) * 70.0

    def compare_dynamic(self, player_id: int, position: str, config: Dict) -> Dict:
        """
        Realiza comparación dinámica basada en configuración personalizable.

        Args:
            player_id: ID del jugador
            position: Posición específica (ej: RDMF, LCMF3, RW)
            config: Configuración de comparación {
                'seasons': ['2023-24'],
                'show_team_avg': True,
                'show_league_avg': True,
                'show_top25': False,
                'aggregation': 'latest'
            }

        Returns:
            Dict con comparación dinámica completa
        """
        try:
            # Obtener métricas del jugador
            seasons = config.get("seasons", ["2024-25"])
            latest_season = seasons[0] if seasons else "2024-25"

            player_metrics = self.get_position_specific_metrics(
                player_id, position, latest_season
            )

            if not player_metrics:
                logger.warning(f"No se encontraron métricas para jugador {player_id}")
                return {}

            team = player_metrics["team"]
            mapped_position = player_metrics["position"]

            # Crear estructura de comparación
            comparison_result = {
                "player": player_metrics,
                "config": config,
                "comparisons": {},
                "references": {},
            }

            # Obtener referencias según configuración
            if config.get("show_league_avg", True):
                logger.info(
                    f"Obteniendo promedios de liga para posición: {mapped_position}, temporadas: {seasons}"
                )
                league_averages = self.csv_controller.get_league_averages(
                    mapped_position, seasons
                )
                logger.info(
                    f"Liga averages type: {type(league_averages)}, keys: {list(league_averages.keys()) if isinstance(league_averages, dict) else 'NOT DICT'}"
                )
                comparison_result["references"]["league_averages"] = league_averages

            if config.get("show_team_avg", True):
                logger.info(
                    f"Obteniendo promedios de equipo: {team}, posición: {mapped_position}, temporadas: {seasons}"
                )
                team_averages = self.csv_controller.get_team_averages(
                    team, mapped_position, seasons
                )
                logger.info(
                    f"Team averages type: {type(team_averages)}, keys: {list(team_averages.keys()) if isinstance(team_averages, dict) else 'NOT DICT'}"
                )
                comparison_result["references"]["team_averages"] = team_averages

            if config.get("show_top25", False):
                logger.debug(
                    f"Obteniendo percentiles top25 para posición: {mapped_position}, temporadas: {seasons}"
                )
                top25_percentiles = self.csv_controller.get_league_percentiles(
                    mapped_position, seasons, 75.0
                )
                logger.debug(f"Top25 percentiles type: {type(top25_percentiles)}")
                comparison_result["references"]["top25_percentiles"] = top25_percentiles

            # Generar comparaciones por métrica
            player_metrics_data = player_metrics.get("metrics", {})

            for metric_key, player_data in player_metrics_data.items():
                logger.info(
                    f"Procesando métrica: {metric_key}, player_data type: {type(player_data)}"
                )

                if not isinstance(player_data, dict):
                    logger.error(
                        f"player_data no es dict para métrica {metric_key}: {player_data}"
                    )
                    continue

                player_value = player_data.get("value", 0)
                display_name = player_data.get("display_name", metric_key)

                metric_comparison = {
                    "player_value": player_value,
                    "display_name": display_name,
                }

                # Comparar con referencias disponibles
                references = comparison_result["references"]

                if "league_averages" in references:
                    league_data = references["league_averages"]
                    if isinstance(league_data, dict) and "averages" in league_data:
                        league_avg_data = league_data["averages"].get(metric_key, {})
                        if isinstance(league_avg_data, dict):
                            league_avg = league_avg_data.get("value", 0)
                            if league_avg > 0:
                                metric_comparison["league_average"] = league_avg
                                metric_comparison["vs_league_pct"] = (
                                    (player_value - league_avg) / league_avg * 100
                                )

                if "team_averages" in references:
                    team_data = references["team_averages"]
                    if isinstance(team_data, dict) and "averages" in team_data:
                        team_avg_data = team_data["averages"].get(metric_key, {})
                        if isinstance(team_avg_data, dict):
                            team_avg = team_avg_data.get("value", 0)
                            if team_avg > 0:
                                metric_comparison["team_average"] = team_avg
                                metric_comparison["vs_team_pct"] = (
                                    (player_value - team_avg) / team_avg * 100
                                )

                if "top25_percentiles" in references:
                    top25_data = references["top25_percentiles"]
                    if isinstance(top25_data, dict) and "percentiles" in top25_data:
                        top25_val_data = top25_data["percentiles"].get(metric_key, {})
                        if isinstance(top25_val_data, dict):
                            top25_val = top25_val_data.get("value", 0)
                            if top25_val > 0:
                                metric_comparison["top25_value"] = top25_val
                                metric_comparison["vs_top25_pct"] = (
                                    (player_value - top25_val) / top25_val * 100
                                )

                comparison_result["comparisons"][metric_key] = metric_comparison

            return comparison_result

        except Exception as e:
            import traceback

            logger.error(f"Error en comparación dinámica: {e}")
            logger.error(f"Config recibido: {config}")
            logger.error(f"Player ID: {player_id}, Position: {position}")
            logger.error(f"Traceback completo: {traceback.format_exc()}")
            return {}

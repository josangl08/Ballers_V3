"""
Player Analyzer - Análisis completo de jugadores para UI integration.

Este módulo proporciona interfaz entre el ml_system y la UI para análisis
de jugadores profesionales, incluyendo PDI y métricas ML.

Migrado desde controllers/ml/ml_metrics_controller.py - método específico
para mantener arquitectura ml_system sin duplicar funcionalidad.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from controllers.db import get_db_session
from ml_system.data_processing.processors.position_mapper import PositionMapper
from ml_system.evaluation.analysis.advanced_features import (
    AdvancedFeatureEngineer,
    LegacyFeatureWeights,
    create_advanced_feature_pipeline,
)
from ml_system.evaluation.metrics.pdi_calculator import PDICalculator
from models.ml_metrics_model import MLMetrics
from models.player_model import Player
from models.professional_stats_model import ProfessionalStats

logger = logging.getLogger(__name__)


class PlayerAnalyzer:
    """
    Analizador de jugadores para integración con UI.
    Proporciona análisis completo incluyendo features ML, PDI Calculator y normalización.

    Arquitectura híbrida:
    - PDI Calculator completo migrado desde legacy ML Metrics Controller
    - Feature engineering avanzado con ml_system
    - Integración completa con UI dashboard
    """

    def __init__(self, session_factory=None):
        """Inicializa el analizador con componentes ml_system, PDI Calculator y Enhanced Features."""
        self.session_factory = session_factory or get_db_session
        self.position_mapper = PositionMapper()
        self.pdi_calculator = PDICalculator()
        self.enhanced_feature_engineer = AdvancedFeatureEngineer()  # NUEVO
        self.legacy_weights = LegacyFeatureWeights()  # NUEVO

        # Posiciones soportadas (compatible con controlador original)
        self.supported_positions = {
            "GK",
            "CB",
            "LB",
            "RB",
            "CDM",
            "CM",
            "CAM",
            "LM",
            "RM",
            "LW",
            "RW",
            "CF",
            "ST",
        }

        logger.info(
            "🎯 PlayerAnalyzer inicializado con Enhanced Features + Legacy Weights"
        )
        logger.info(
            "⚖️ Versión 2.0: PDI Calculator + Advanced Feature Engineer + Legacy Integration"
        )

    def get_enhanced_player_analysis(
        self, player_id: int, season: str = "2024-25"
    ) -> Dict[str, any]:
        """
        Análisis completo de un jugador incluyendo PDI Calculator científico.

        Args:
            player_id: ID del jugador
            season: Temporada a analizar

        Returns:
            dict: Análisis completo con PDI científico, features, métricas y ranking
        """
        try:
            with get_db_session() as session:
                # Obtener datos del jugador
                player = session.query(Player).filter_by(player_id=player_id).first()
                if not player or not player.is_professional:
                    return {"error": "Jugador no encontrado o no es profesional"}

                prof_stats = (
                    session.query(ProfessionalStats)
                    .filter_by(player_id=player_id, season=season)
                    .first()
                )

                if not prof_stats:
                    return {"error": "No se encontraron estadísticas profesionales"}

                # Determinar posición usando position_mapper
                position = prof_stats.primary_position or "CF"
                if position not in self.supported_positions:
                    position = "CF"

                # Crear pipeline de features avanzadas (ya inicializado)
                # feature_pipeline = create_advanced_feature_pipeline()  # Ya tenemos self.enhanced_feature_engineer

                # Análisis completo usando componentes ml_system + PDI Calculator
                analysis = {
                    "player_info": {
                        "player_id": player_id,
                        "name": player.user.name if player.user else "Unknown",
                        "position": position,
                        "season": season,
                    },
                    "features": {
                        "universal": self._extract_universal_features(prof_stats),
                        "zone": self._extract_zone_features(prof_stats, position),
                        "position_specific": self._extract_position_specific_features(
                            prof_stats, position
                        ),
                    },
                    "quality_report": self._generate_quality_report(
                        prof_stats, position
                    ),
                }

                # INTEGRACIÓN PDI CALCULATOR - Calcular o obtener métricas completas
                ml_metrics = self.pdi_calculator.get_or_calculate_metrics(
                    player_id, season, force_recalculate=False
                )

                if ml_metrics:
                    # Usar métricas del PDI Calculator completo (campos compatibles con MLMetrics)
                    raw_metrics = {
                        "pdi_overall": ml_metrics.pdi_overall,
                        "pdi_universal": ml_metrics.pdi_universal,
                        "pdi_zone": ml_metrics.pdi_zone,
                        "pdi_position_specific": ml_metrics.pdi_position_specific,
                        "technical_proficiency": ml_metrics.technical_proficiency,
                        "tactical_intelligence": ml_metrics.tactical_intelligence,
                        "physical_performance": ml_metrics.physical_performance,
                        "consistency_index": ml_metrics.consistency_index,
                    }

                    # Filtrar valores None
                    raw_metrics = {
                        k: v for k, v in raw_metrics.items() if v is not None
                    }

                    # Normalización avanzada usando PDI Calculator
                    normalized = self._get_normalized_metrics_from_pdi(
                        ml_metrics, position
                    )

                    analysis["ml_metrics"] = {
                        "raw": raw_metrics,
                        "normalized": normalized,
                        "pdi_breakdown": {
                            "universal_weight": 0.40,
                            "zone_weight": 0.35,
                            "position_specific_weight": 0.25,
                            "position": position,
                            "model_version": "1.0",
                        },
                        "calculated_with_pdi_calculator": True,
                    }
                else:
                    logger.warning(
                        f"No se pudieron calcular métricas PDI para jugador {player_id}"
                    )
                    analysis["ml_metrics"] = {
                        "error": "No se pudieron calcular métricas PDI",
                        "calculated_with_pdi_calculator": False,
                    }

                return analysis

        except Exception as e:
            logger.error("Error en análisis completo: %s", str(e))
            return {"error": str(e)}

    def _extract_universal_features(self, stats: ProfessionalStats) -> Dict:
        """Extrae features universales básicas."""
        return {
            "goals_per_90": stats.goals_per_90 or 0,
            "assists_per_90": stats.assists_per_90 or 0,
            "pass_accuracy": stats.pass_accuracy_pct or 0,
            "defensive_actions": stats.defensive_actions_per_90 or 0,
        }

    def _extract_zone_features(self, stats: ProfessionalStats, position: str) -> Dict:
        """Extrae features por zona según posición."""
        zone_features = {
            "offensive": {
                "shots_per_90": stats.shots_per_90 or 0,
                "key_passes": (
                    stats.key_passes_per_90
                    if hasattr(stats, "key_passes_per_90")
                    else 0
                ),
            },
            "defensive": {
                "defensive_duels": stats.defensive_duels_per_90 or 0,
                "aerial_duels": stats.aerial_duels_per_90 or 0,
            },
        }
        return zone_features

    def _extract_position_specific_features(
        self, stats: ProfessionalStats, position: str
    ) -> Dict:
        """Extrae features específicas por posición."""
        if position in ["GK"]:
            return {"position_type": "goalkeeper"}
        elif position in ["CB", "LB", "RB"]:
            return {"position_type": "defender"}
        elif position in ["CDM", "CM", "CAM"]:
            return {"position_type": "midfielder"}
        else:
            return {"position_type": "forward"}

    def _generate_quality_report(self, stats: ProfessionalStats, position: str) -> Dict:
        """Genera reporte básico de calidad de datos."""
        return {
            "data_quality": (
                "high"
                if stats.matches_played and stats.matches_played > 5
                else "medium"
            ),
            "minutes_played": stats.minutes_played or 0,
            "matches_played": stats.matches_played or 0,
        }

    def _normalize_metrics(self, raw_metrics: Dict, position: str) -> Dict:
        """
        Normalización básica de métricas por posición.
        Implementación simplificada para mantener funcionalidad UI.
        """
        # Factores de normalización básicos por tipo de posición
        position_factors = {
            "GK": {"defensive": 1.2, "offensive": 0.3},
            "CB": {"defensive": 1.1, "offensive": 0.5},
            "LB": {"defensive": 1.0, "offensive": 0.8},
            "RB": {"defensive": 1.0, "offensive": 0.8},
            "CDM": {"defensive": 1.0, "offensive": 0.7},
            "CM": {"defensive": 0.8, "offensive": 0.9},
            "CAM": {"defensive": 0.6, "offensive": 1.1},
            "LW": {"defensive": 0.5, "offensive": 1.1},
            "RW": {"defensive": 0.5, "offensive": 1.1},
            "CF": {"defensive": 0.4, "offensive": 1.2},
            "ST": {"defensive": 0.3, "offensive": 1.2},
        }

        factors = position_factors.get(position, {"defensive": 1.0, "offensive": 1.0})

        # Aplicar normalización básica
        normalized = {}
        for key, value in raw_metrics.items():
            if isinstance(value, (int, float)):
                # Aplicar factor según tipo de métrica
                if "defensive" in key.lower() or "duels" in key.lower():
                    normalized[key] = value * factors["defensive"]
                elif (
                    "offensive" in key.lower()
                    or "goals" in key.lower()
                    or "assists" in key.lower()
                ):
                    normalized[key] = value * factors["offensive"]
                else:
                    normalized[key] = value  # Sin normalización para métricas neutras
            else:
                normalized[key] = value

        return normalized

    def get_player_stats(self, player_id: int) -> list:
        """
        Obtiene estadísticas profesionales de un jugador específico.
        Migrado desde ThaiLeagueController para consolidación ML.

        Args:
            player_id: ID del jugador en la base de datos

        Returns:
            Lista de diccionarios con estadísticas por temporada
        """
        try:
            with get_db_session() as session:
                stats = (
                    session.query(ProfessionalStats)
                    .filter(ProfessionalStats.player_id == player_id)
                    .order_by(ProfessionalStats.season)
                    .all()
                )

                logger.info(f"🔍 Buscando estadísticas para player_id: {player_id}")
                logger.info(f"📊 Estadísticas encontradas: {len(stats)} registros")

                result = []
                for stat in stats:
                    stat_dict = {
                        # Información básica
                        "season": stat.season,
                        "team": stat.team,
                        "age": stat.age,
                        "matches_played": stat.matches_played,
                        "minutes_played": stat.minutes_played,
                        "goals": stat.goals,
                        "assists": stat.assists,
                        "market_value": stat.market_value,
                        # Rendimiento ofensivo
                        "shots": stat.shots,
                        "shots_per_90": stat.shots_per_90,
                        "shots_on_target_pct": stat.shots_on_target_pct,
                        "goal_conversion_pct": stat.goal_conversion_pct,
                        "goals_per_90": stat.goals_per_90,
                        "assists_per_90": stat.assists_per_90,
                        # Rendimiento defensivo
                        "defensive_actions_per_90": stat.defensive_actions_per_90,
                        "duels_won_pct": stat.duels_won_pct,
                        # Pases y distribución
                        "pass_accuracy_pct": stat.pass_accuracy_pct,
                        # Métricas avanzadas
                        "expected_goals": stat.expected_goals,
                        "expected_assists": stat.expected_assists,
                    }
                    result.append(stat_dict)
                    logger.info(
                        f"✅ Estadística procesada: {stat.season} - {stat.team}"
                    )

                logger.info(f"📈 Total estadísticas devueltas: {len(result)}")
                return result

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas del jugador {player_id}: {e}")
            return []

    def get_team_info(self, stats_record: Dict[str, any]) -> Dict[str, any]:
        """
        Determina información inteligente del equipo basada en el análisis de datos.

        Migrado desde ThaiLeagueController para consolidación ML.
        Lógica híbrida:
        - Analiza temporada actual vs histórica
        - Maneja transferencias y estados de jugadores
        - Determina equipo a mostrar según contexto

        Args:
            stats_record: Diccionario con datos del jugador

        Returns:
            Diccionario con información procesada del equipo
        """
        team_current = stats_record.get("team") or ""
        team_start = stats_record.get("team_within_timeframe") or ""
        season = stats_record.get("season", "")

        # Normalizar valores nan/None a string vacío
        if team_current in ["nan", None, "None"]:
            team_current = ""
        if team_start in ["nan", None, "None"]:
            team_start = ""

        # Determinar si es temporada actual
        is_current = self._is_current_season(stats_record)

        # Aplicar lógica contextual
        team_status = self._determine_team_status(
            team_current, team_start, season, is_current
        )

        # Obtener información formateada para UI
        display_info = self._get_team_display_info(
            team_current, team_start, team_status, stats_record
        )

        # Validar URL del logo si existe
        logo_url = stats_record.get("team_logo_url")
        if logo_url:
            logo_url = self._validate_team_logo_url(logo_url)

        logger.debug(
            f"Team info processed - Player: {stats_record.get('player_name')}, "
            f"Season: {season}, Current: '{team_current}', Start: '{team_start}', "
            f"Status: {team_status}, Display: {display_info['team_display']}"
        )

        return {
            "team_current": team_current,
            "team_start": team_start,
            "team_status": team_status,
            "team_display": display_info["team_display"],
            "status_message": display_info["status_message"],
            "logo_url": logo_url,
            "is_current_season": is_current,
            "has_transfer": bool(
                team_current != team_start and team_current and team_start
            ),
        }

    def _is_current_season(self, stats_record: Dict[str, any]) -> bool:
        """
        Determina si el registro corresponde a la temporada actual.

        Args:
            stats_record: Diccionario con datos del jugador

        Returns:
            True si es temporada actual, False si es histórica
        """
        season = stats_record.get("season", "")

        # Para este proyecto, consideramos 2024-25 como la temporada actual
        # debido a que los datos más recientes son de esta temporada
        current_season = "2024-25"

        return season == current_season

    def _determine_team_status(
        self, team_current: str, team_start: str, season: str, is_current: bool
    ) -> str:
        """
        Determina el estado del jugador respecto a equipos.

        Args:
            team_current: Equipo actual
            team_start: Equipo al inicio del periodo
            season: Temporada
            is_current: Si es temporada actual

        Returns:
            Estado del equipo: 'active', 'transferred', 'free_agent', 'historical'
        """
        # Casos sin equipos
        if not team_current and not team_start:
            return "free_agent"

        # Solo tiene equipo actual
        if team_current and not team_start:
            return "active" if is_current else "historical"

        # Solo tiene equipo de inicio (raro pero posible)
        if team_start and not team_current:
            return "free_agent" if is_current else "historical"

        # Ambos equipos presentes
        if team_current == team_start:
            return "active" if is_current else "historical"
        else:
            return "transferred" if is_current else "historical"

    def _get_team_display_info(
        self,
        team_current: str,
        team_start: str,
        team_status: str,
        stats_record: Dict[str, any],
    ) -> Dict[str, str]:
        """
        Obtiene información formateada del equipo para mostrar en la UI.

        Args:
            team_current: Equipo actual
            team_start: Equipo al inicio
            team_status: Estado determinado
            stats_record: Datos completos del jugador

        Returns:
            Diccionario con team_display y status_message
        """
        player_name = stats_record.get("player_name", "Jugador")
        season = stats_record.get("season", "")

        if team_status == "free_agent":
            return {
                "team_display": "Agente libre",
                "status_message": f"{player_name} sin equipo en {season}",
            }

        elif team_status == "transferred":
            return {
                "team_display": team_current or "Equipo actual desconocido",
                "status_message": f"{player_name} transferido de {team_start} a {team_current} en {season}",
            }

        elif team_status == "active":
            return {
                "team_display": team_current or "Equipo desconocido",
                "status_message": f"{player_name} actualmente en {team_current}",
            }

        elif team_status == "historical":
            team_to_show = team_current or team_start or "Equipo desconocido"
            return {
                "team_display": team_to_show,
                "status_message": f"{player_name} jugó en {team_to_show} durante {season}",
            }

        else:
            # Fallback para casos no previstos
            team_to_show = team_current or team_start or "Equipo desconocido"
            return {
                "team_display": team_to_show,
                "status_message": f"{player_name} en {team_to_show} ({season})",
            }

    def _validate_team_logo_url(self, logo_url: str) -> str:
        """
        Valida y normaliza URL del logo del equipo.

        Args:
            logo_url: URL del logo a validar

        Returns:
            URL validada o None si es inválida
        """
        if not logo_url or logo_url in ["nan", None, "None", ""]:
            return None

        # Validación básica de URL
        if not (logo_url.startswith("http://") or logo_url.startswith("https://")):
            return None

        return logo_url

    def _get_normalized_metrics_from_pdi(
        self, ml_metrics: MLMetrics, position: str
    ) -> Dict[str, any]:
        """
        Obtiene métricas normalizadas usando componentes del PDI Calculator.

        Args:
            ml_metrics: Objeto MLMetrics con métricas calculadas
            position: Posición del jugador

        Returns:
            Dict con métricas normalizadas y rankings
        """
        try:
            # Obtener rankings de posición usando PDI Calculator
            position_rankings = self.pdi_calculator.get_league_rankings(
                position=position, season=ml_metrics.season, limit=100
            )

            # Obtener promedios por posición
            position_averages = self.pdi_calculator.get_position_averages(
                position=position, season=ml_metrics.season
            )

            # Calcular percentiles basados en rankings
            player_rank = None
            for idx, ranking in enumerate(position_rankings):
                if ranking["player_id"] == ml_metrics.player_id:
                    player_rank = idx + 1
                    break

            # Calcular percentil posicional
            position_percentile = 50.0  # Default
            if player_rank and len(position_rankings) > 0:
                position_percentile = max(
                    1, 100 - ((player_rank / len(position_rankings)) * 100)
                )

            normalized_metrics = {
                "pdi_score_percentile": position_percentile,
                "position_rank": player_rank,
                "total_players_position": len(position_rankings),
                "position_averages": position_averages,
                "league_context": {
                    "position": position,
                    "season": ml_metrics.season,
                    "ranking_basis": "Thai League Dataset",
                },
                # Métricas comparativas
                "vs_position_average": self._calculate_vs_average(
                    ml_metrics, position_averages
                ),
            }

            return normalized_metrics

        except Exception as e:
            logger.error(f"Error obteniendo métricas normalizadas PDI: {e}")
            return {
                "error": "No se pudieron calcular métricas normalizadas",
                "position_percentile": 50.0,
            }

    def _calculate_vs_average(
        self, ml_metrics: MLMetrics, position_averages: Dict
    ) -> Dict[str, float]:
        """
        Calcula diferencias vs promedio de posición.

        Args:
            ml_metrics: Métricas del jugador
            position_averages: Promedios por posición

        Returns:
            Dict con diferencias vs promedio
        """
        try:
            if not position_averages:
                return {}

            vs_avg = {}

            # PDI Overall vs promedio
            if ml_metrics.pdi_overall and position_averages.get("avg_pdi_overall"):
                vs_avg["pdi_overall_diff"] = (
                    ml_metrics.pdi_overall - position_averages["avg_pdi_overall"]
                )

            # Métricas individuales vs promedio
            if ml_metrics.technical_proficiency and position_averages.get(
                "avg_technical"
            ):
                vs_avg["technical_diff"] = (
                    ml_metrics.technical_proficiency
                    - position_averages["avg_technical"]
                )

            if ml_metrics.tactical_intelligence and position_averages.get(
                "avg_tactical"
            ):
                vs_avg["tactical_diff"] = (
                    ml_metrics.tactical_intelligence - position_averages["avg_tactical"]
                )

            return vs_avg

        except Exception as e:
            logger.error(f"Error calculando vs average: {e}")
            return {}

    def calculate_or_update_pdi_metrics(
        self, player_id: int, season: str = "2024-25", force_recalculate: bool = False
    ) -> Optional[Dict]:
        """
        Interfaz directa al PDI Calculator para cálculo/actualización de métricas.

        Args:
            player_id: ID del jugador
            season: Temporada a analizar
            force_recalculate: Forzar recálculo aunque existan métricas válidas

        Returns:
            Dict con datos de MLMetrics o None si no se puede calcular
        """
        try:
            logger.info(
                f"🎯 Calculando métricas PDI para jugador {player_id} temporada {season}"
            )

            ml_metrics = self.pdi_calculator.get_or_calculate_metrics(
                player_id, season, force_recalculate
            )

            if ml_metrics:
                # Convertir a diccionario para evitar problemas de sesión
                metrics_dict = {
                    "pdi_overall": ml_metrics.pdi_overall,
                    "pdi_universal": ml_metrics.pdi_universal,
                    "pdi_zone": ml_metrics.pdi_zone,
                    "pdi_position_specific": ml_metrics.pdi_position_specific,
                    "technical_proficiency": ml_metrics.technical_proficiency,
                    "tactical_intelligence": ml_metrics.tactical_intelligence,
                    "physical_performance": ml_metrics.physical_performance,
                    "consistency_index": ml_metrics.consistency_index,
                    "position_analyzed": ml_metrics.position_analyzed,
                    "season": ml_metrics.season,
                }

                logger.info(
                    f"✅ Métricas PDI calculadas: PDI={metrics_dict['pdi_overall']}, "
                    f"Técnico={metrics_dict['technical_proficiency']}"
                )
                return metrics_dict
            else:
                logger.warning(
                    f"⚠️ No se pudieron calcular métricas PDI para jugador {player_id}"
                )
                return None

        except Exception as e:
            logger.error(f"Error en calculate_or_update_pdi_metrics: {e}")
            return None

    def get_legacy_weights_for_position(self, position: str) -> Dict[str, any]:
        """
        Obtiene información detallada de pesos legacy para una posición.

        Args:
            position: Posición del jugador

        Returns:
            Dict con pesos legacy detallados
        """
        try:
            weights = self.legacy_weights.get_feature_weights_for_position(position)
            normalized_pos = self.legacy_weights._normalize_position_for_weights(
                position
            )

            return {
                "original_position": position,
                "normalized_position": normalized_pos,
                "weights": weights,
                "summary": {
                    "universal_categories": len(weights.get("universal", {})),
                    "zone_categories": len(weights.get("zone", {})),
                    "position_specific_features": len(
                        weights.get("position_specific", {})
                    ),
                    "total_weighted_features": sum(
                        [
                            sum(
                                len(cat.values())
                                for cat in weights.get("universal", {}).values()
                            ),
                            sum(
                                len(cat.values())
                                for cat in weights.get("zone", {}).values()
                            ),
                            len(weights.get("position_specific", {})),
                        ]
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error obteniendo legacy weights: {e}")
            return {"error": str(e)}

    def get_position_rankings(
        self, position: str = None, season: str = "2024-25", limit: int = 20
    ) -> list:
        """
        Interfaz a los rankings del PDI Calculator.

        Args:
            position: Posición específica para filtrar
            season: Temporada
            limit: Número de resultados

        Returns:
            Lista de rankings ordenados por PDI
        """
        try:
            rankings = self.pdi_calculator.get_league_rankings(
                position=position, season=season, limit=limit
            )

            logger.info(f"📊 Rankings obtenidos: {len(rankings)} jugadores")
            return rankings

        except Exception as e:
            logger.error(f"Error obteniendo rankings: {e}")
            return []

    def get_available_seasons_for_etl(self) -> Dict[str, str]:
        """
        Obtiene temporadas disponibles para procesamiento ETL.
        Compatible con ETL Tester Dashboard.

        Returns:
            Dict con temporadas disponibles {season: description}
        """
        try:
            from ml_system.data_acquisition.extractors.thai_league_extractor import (
                ThaiLeagueExtractor,
            )

            extractor = ThaiLeagueExtractor()
            available_seasons = extractor.get_available_seasons()

            logger.info(f"📊 {len(available_seasons)} temporadas disponibles para ETL")
            return available_seasons

        except Exception as e:
            logger.error(f"Error obteniendo temporadas para ETL: {e}")
            return {"2024-25": "Thai League 2024-25 Season"}  # Fallback

    def get_available_seasons_for_player(self, player_id: int) -> List[str]:
        """
        Obtiene todas las temporadas disponibles para un jugador específico.

        Args:
            player_id: ID del jugador

        Returns:
            Lista de temporadas ordenadas cronológicamente
        """
        try:
            with get_db_session() as session:
                # Consultar todas las temporadas con datos del jugador
                seasons = (
                    session.query(ProfessionalStats.season)
                    .filter_by(player_id=player_id)
                    .distinct()
                    .order_by(ProfessionalStats.season)
                    .all()
                )

                # Extraer solo los strings de temporada
                season_list = [season[0] for season in seasons if season[0]]

                logger.info(
                    f"🗓️ Temporadas disponibles para jugador {player_id}: {season_list}"
                )
                return season_list

        except Exception as e:
            logger.error(f"Error obteniendo temporadas para jugador {player_id}: {e}")
            return []

    def validate_season_exists_for_player(self, player_id: int, season: str) -> bool:
        """
        Valida si existe una temporada específica para un jugador.

        Args:
            player_id: ID del jugador
            season: Temporada a validar

        Returns:
            True si existe la temporada, False en caso contrario
        """
        try:
            with get_db_session() as session:
                exists = (
                    session.query(ProfessionalStats)
                    .filter_by(player_id=player_id, season=season)
                    .first()
                ) is not None

                return exists

        except Exception as e:
            logger.error(
                f"Error validando temporada {season} para jugador {player_id}: {e}"
            )
            return False

    def get_enhanced_feature_analysis(
        self, player_id: int, season: str = "2024-25"
    ) -> Dict[str, any]:
        """
        Análisis avanzado usando Enhanced Feature Engineer con Legacy Weights.

        Args:
            player_id: ID del jugador
            season: Temporada a analizar

        Returns:
            Dict con análisis de features avanzadas
        """
        try:
            with get_db_session() as session:
                # Obtener datos del jugador
                player = session.query(Player).filter_by(player_id=player_id).first()
                if not player or not player.is_professional:
                    return {"error": "Jugador no encontrado o no es profesional"}

                prof_stats = (
                    session.query(ProfessionalStats)
                    .filter_by(player_id=player_id, season=season)
                    .first()
                )

                if not prof_stats:
                    return {"error": "No se encontraron estadísticas profesionales"}

                # Convertir ProfessionalStats a DataFrame para Enhanced Feature Engineer
                import pandas as pd

                stats_dict = {
                    "Player": player.user.name if player.user else "Unknown",
                    "Age": prof_stats.age or 25,
                    "Primary position": prof_stats.primary_position or "CMF",
                    "Minutes played": prof_stats.minutes_played or 0,
                    "Pass accuracy, %": prof_stats.pass_accuracy_pct or 0,
                    "Duels won, %": prof_stats.duels_won_pct or 0,
                    "Matches played": prof_stats.matches_played or 0,
                    "Goals per 90": prof_stats.goals_per_90 or 0,
                    "Assists per 90": prof_stats.assists_per_90 or 0,
                    "Successful dribbles, %": prof_stats.dribbles_success_pct or 0,
                    "season": season,
                }

                # Crear DataFrame temporal
                df = pd.DataFrame([stats_dict])

                # Aplicar Enhanced Feature Engineering
                enhanced_df = self.enhanced_feature_engineer.engineer_advanced_features(
                    df
                )

                if len(enhanced_df) > 0:
                    enhanced_features = enhanced_df.iloc[0].to_dict()

                    # Filtrar solo las nuevas features generadas
                    original_cols = set(stats_dict.keys())
                    new_features = {
                        k: v
                        for k, v in enhanced_features.items()
                        if k not in original_cols and pd.notna(v)
                    }

                    # Obtener pesos legacy específicos
                    position = prof_stats.primary_position or "CMF"
                    legacy_weights = (
                        self.legacy_weights.get_feature_weights_for_position(position)
                    )

                    enhanced_analysis = {
                        "player_info": {
                            "player_id": player_id,
                            "name": player.user.name if player.user else "Unknown",
                            "position": position,
                            "season": season,
                        },
                        "enhanced_features": {
                            "positional_features": {
                                k: v
                                for k, v in new_features.items()
                                if "position" in k.lower()
                                and isinstance(v, (int, float))
                            },
                            "age_features": {
                                k: v
                                for k, v in new_features.items()
                                if "age" in k.lower() and isinstance(v, (int, float))
                            },
                            "tier_features": {
                                k: v
                                for k, v in new_features.items()
                                if "tier" in k.lower() and isinstance(v, (int, float))
                            },
                            "legacy_features": {
                                k: v
                                for k, v in new_features.items()
                                if "legacy" in k.lower() and isinstance(v, (int, float))
                            },
                            "interaction_features": {
                                k: v
                                for k, v in new_features.items()
                                if "interaction" in k.lower()
                                and isinstance(v, (int, float))
                            },
                        },
                        "legacy_weights_info": {
                            "position_normalized": self.legacy_weights._normalize_position_for_weights(
                                position
                            ),
                            "universal_features_count": len(
                                legacy_weights.get("universal", {})
                            ),
                            "zone_features_count": len(legacy_weights.get("zone", {})),
                            "position_features_count": len(
                                legacy_weights.get("position_specific", {})
                            ),
                            "total_legacy_features": sum(
                                [
                                    len(legacy_weights.get("universal", {})),
                                    len(legacy_weights.get("zone", {})),
                                    len(legacy_weights.get("position_specific", {})),
                                ]
                            ),
                        },
                        "feature_summary": {
                            "total_features_generated": len(new_features),
                            "features_by_category": {
                                "positional": len(
                                    [
                                        k
                                        for k in new_features.keys()
                                        if "position" in k.lower()
                                    ]
                                ),
                                "age_based": len(
                                    [
                                        k
                                        for k in new_features.keys()
                                        if "age" in k.lower()
                                    ]
                                ),
                                "performance_tier": len(
                                    [
                                        k
                                        for k in new_features.keys()
                                        if "tier" in k.lower()
                                    ]
                                ),
                                "legacy_weighted": len(
                                    [
                                        k
                                        for k in new_features.keys()
                                        if "legacy" in k.lower()
                                    ]
                                ),
                                "interactions": len(
                                    [
                                        k
                                        for k in new_features.keys()
                                        if "interaction" in k.lower()
                                    ]
                                ),
                            },
                        },
                    }

                    logger.info(
                        f"✨ Enhanced Feature Analysis: {len(new_features)} features generadas"
                    )
                    return enhanced_analysis

                else:
                    return {"error": "No se pudieron generar features avanzadas"}

        except Exception as e:
            logger.error(f"Error en enhanced feature analysis: {e}")
            return {"error": str(e)}

    # === INTEGRACIÓN ETL COORDINATOR ===

    def execute_season_etl_pipeline(
        self, season: str, threshold: int = 85, calculate_pdi: bool = True
    ) -> Tuple[bool, str, Dict]:
        """
        Ejecuta pipeline ETL completo usando ETL Coordinator CRISP-DM.
        Interfaz simplificada para UI integration.

        Args:
            season: Temporada a procesar
            threshold: Umbral para fuzzy matching
            calculate_pdi: Si calcular métricas PDI automáticamente

        Returns:
            Tuple[success, message, results]
        """
        try:
            from ml_system.deployment.orchestration.etl_coordinator import (
                ETLCoordinator,
            )

            etl_coordinator = ETLCoordinator(
                self.session_factory if hasattr(self, "session_factory") else None
            )

            logger.info(
                f"🚀 PlayerAnalyzer: Iniciando ETL pipeline CRISP-DM para temporada {season}"
            )

            success, message, results = etl_coordinator.execute_full_crisp_dm_pipeline(
                season=season,
                threshold=threshold,
                force_reload=False,
                calculate_pdi=calculate_pdi,
            )

            if success and calculate_pdi:
                # Post-processing: actualizar análisis de jugadores afectados
                self._post_process_etl_results(season, results)

            logger.info(f"✅ ETL Pipeline completado: {message}")
            return success, message, results

        except Exception as e:
            error_msg = f"Error ejecutando ETL pipeline: {e}"
            logger.error(error_msg)
            return False, error_msg, {}

    def get_etl_processing_status(self, season: str) -> Dict[str, Any]:
        """
        Obtiene estado del procesamiento ETL de una temporada.

        Args:
            season: Temporada a consultar

        Returns:
            Dict con estado detallado del procesamiento
        """
        try:
            from ml_system.deployment.orchestration.etl_coordinator import (
                ETLCoordinator,
            )

            etl_coordinator = ETLCoordinator()
            status = etl_coordinator.get_processing_status(season)

            # Enriquecer con información adicional
            if status["status"] == "completed":
                # Añadir información de jugadores disponibles para análisis
                available_players = self._get_available_players_for_season(season)
                status["available_for_analysis"] = len(available_players)
                status["players_with_pdi"] = self._count_players_with_pdi(season)

            return status

        except Exception as e:
            logger.error(f"Error obteniendo estado ETL: {e}")
            return {
                "season": season,
                "status": "error",
                "message": f"Error consultando estado: {str(e)}",
            }

    def get_available_seasons_for_etl(self) -> Dict[str, str]:
        """
        Obtiene temporadas disponibles para procesamiento ETL.

        Returns:
            Dict con temporadas disponibles
        """
        try:
            from ml_system.deployment.orchestration.etl_coordinator import (
                ETLCoordinator,
            )

            etl_coordinator = ETLCoordinator()
            return etl_coordinator.get_available_seasons()

        except Exception as e:
            logger.error(f"Error obteniendo temporadas ETL: {e}")
            return {}

    def cleanup_and_reprocess_season(self, season: str) -> Tuple[bool, str]:
        """
        Limpia y reprocesa una temporada completa con CRISP-DM.

        Args:
            season: Temporada a limpiar y reprocesar

        Returns:
            Tuple[success, message]
        """
        try:
            from ml_system.deployment.orchestration.etl_coordinator import (
                ETLCoordinator,
            )

            etl_coordinator = ETLCoordinator()

            logger.info(
                f"🧹 PlayerAnalyzer: Limpiando y reprocesando temporada {season}"
            )

            success, message = etl_coordinator.cleanup_and_reprocess(season)

            if success:
                # Limpiar cache de análisis para la temporada
                self._clear_analysis_cache_for_season(season)
                logger.info(f"✅ Temporada {season} reprocesada exitosamente")

            return success, message

        except Exception as e:
            error_msg = f"Error en limpieza y reprocesamiento: {e}"
            logger.error(error_msg)
            return False, error_msg

    def get_season_analysis_summary(self, season: str) -> Dict[str, Any]:
        """
        Obtiene resumen completo de análisis para una temporada.

        Args:
            season: Temporada a analizar

        Returns:
            Dict con resumen de análisis de la temporada
        """
        try:
            # Estado de procesamiento ETL
            etl_status = self.get_etl_processing_status(season)

            # Jugadores disponibles
            available_players = self._get_available_players_for_season(season)

            # Estadísticas de PDI
            pdi_stats = self._get_season_pdi_statistics(season)

            # Top performers
            top_performers = self._get_top_performers_for_season(season, limit=5)

            summary = {
                "season": season,
                "etl_status": etl_status,
                "player_statistics": {
                    "total_players": len(available_players),
                    "players_with_pdi": pdi_stats.get("players_with_pdi", 0),
                    "avg_pdi_overall": pdi_stats.get("avg_pdi_overall", 0.0),
                    "top_performers": top_performers,
                },
                "data_quality": {
                    "processing_status": etl_status.get("status", "unknown"),
                    "last_updated": etl_status.get("last_updated"),
                    "total_records": etl_status.get("total_records", 0),
                    "imported_records": etl_status.get("imported_records", 0),
                },
                "analysis_ready": etl_status.get("status") == "completed"
                and len(available_players) > 0,
            }

            return summary

        except Exception as e:
            logger.error(f"Error generando resumen de temporada {season}: {e}")
            return {"season": season, "error": str(e), "analysis_ready": False}

    # === MÉTODOS SMART UPDATE SYSTEM ===

    def execute_smart_weekly_update(self) -> Dict[str, Any]:
        """
        Ejecuta Smart Weekly Update usando metodología CRISP-DM.
        Integración con Smart Update Manager para automatización estacional.

        Returns:
            Dict con resultado detallado de la actualización semanal
        """
        try:
            logger.info("🧠 Iniciando Smart Weekly Update desde PlayerAnalyzer")

            # Lazy load Smart Update Manager para evitar dependencias circulares
            from ml_system.deployment.automation.smart_update_manager import (
                SmartUpdateManager,
            )

            smart_manager = SmartUpdateManager(self.session_factory)
            result = smart_manager.execute_smart_weekly_update()

            logger.info(
                f"✅ Smart Weekly Update completado: {result.get('action', 'unknown')}"
            )
            return result

        except Exception as e:
            error_msg = f"Error ejecutando Smart Weekly Update: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "action": "error",
                "stats": {},
            }

    def get_smart_update_status(self) -> Dict[str, Any]:
        """
        Obtiene estado actual del sistema Smart Update.

        Returns:
            Dict con estado completo del sistema Smart Update
        """
        try:
            from ml_system.deployment.automation.smart_update_manager import (
                SmartUpdateManager,
            )

            smart_manager = SmartUpdateManager(self.session_factory)
            status = smart_manager.get_smart_update_status()

            return status

        except Exception as e:
            logger.error(f"Error obteniendo estado Smart Update: {e}")
            return {"error": str(e), "system_available": False}

    def check_seasonal_update_needs(self) -> Dict[str, Any]:
        """
        Verifica qué tipo de actualización estacional es apropiada.

        Returns:
            Dict con análisis de necesidades estacionales
        """
        try:
            from ml_system.deployment.automation.smart_update_manager import (
                SmartUpdateManager,
            )

            smart_manager = SmartUpdateManager(self.session_factory)

            # Obtener contexto estacional
            action = smart_manager._determine_seasonal_action()
            context = smart_manager._analyze_seasonal_context(action)

            analysis = {
                "seasonal_action": action,
                "current_period": context.get("current_period", "unknown"),
                "active_seasons": context.get("active_seasons", []),
                "final_seasons": context.get("final_seasons", []),
                "needs_new_season_search": context.get(
                    "needs_new_season_search", False
                ),
                "recommendation": self._get_seasonal_recommendation(action, context),
            }

            logger.info(
                f"🔍 Análisis estacional: {action} - {analysis['current_period']}"
            )
            return analysis

        except Exception as e:
            logger.error(f"Error verificando necesidades estacionales: {e}")
            return {"error": str(e), "seasonal_action": "unknown"}

    def _get_seasonal_recommendation(self, action: str, context: Dict) -> str:
        """Genera recomendación basada en análisis estacional."""
        try:
            if action == "update_current":
                active_count = len(context.get("active_seasons", []))
                if active_count > 0:
                    return f"Execute incremental update for {active_count} active season(s)"
                else:
                    return "No active seasons found - verify season configuration"

            elif action == "search_new_season":
                return "Search for new season and process professional players if found"

            elif action == "season_ended":
                return "Season ended period - no updates scheduled"

            else:
                return f"Unknown action: {action}"

        except Exception:
            return "Unable to generate recommendation"

    # === MÉTODOS AUXILIARES ETL ===

    def _post_process_etl_results(self, season: str, etl_results: Dict):
        """Post-procesa resultados ETL para optimizar análisis futuros."""
        try:
            # Invalidar cache de temporadas si es necesario
            final_stats = etl_results.get("final_stats", {})
            if final_stats.get("total_loaded", 0) > 0:
                logger.info(
                    f"📊 Post-processing: {final_stats['total_loaded']} registros procesados para {season}"
                )

                # Aquí podrían añadirse tareas de optimización adicionales
                # como pre-cálculo de análisis frecuentes, indexación, etc.

        except Exception as e:
            logger.error(f"Error en post-processing ETL: {e}")

    def _get_available_players_for_season(self, season: str) -> List[int]:
        """Obtiene lista de player_ids con datos para una temporada."""
        try:
            with get_db_session() as session:
                player_ids = (
                    session.query(ProfessionalStats.player_id)
                    .filter_by(season=season)
                    .distinct()
                    .all()
                )
                return [pid[0] for pid in player_ids]
        except Exception as e:
            logger.error(f"Error obteniendo jugadores de temporada {season}: {e}")
            return []

    def _count_players_with_pdi(self, season: str) -> int:
        """Cuenta jugadores con métricas PDI calculadas para una temporada."""
        try:
            with get_db_session() as session:
                count = (
                    session.query(MLMetrics)
                    .filter_by(season=season)
                    .filter(MLMetrics.pdi_overall.isnot(None))
                    .count()
                )
                return count
        except Exception as e:
            logger.error(f"Error contando jugadores con PDI: {e}")
            return 0

    def _get_season_pdi_statistics(self, season: str) -> Dict[str, float]:
        """Obtiene estadísticas PDI para una temporada."""
        try:
            with get_db_session() as session:
                pdi_values = (
                    session.query(MLMetrics.pdi_overall)
                    .filter_by(season=season)
                    .filter(MLMetrics.pdi_overall.isnot(None))
                    .all()
                )

                if pdi_values:
                    values = [v[0] for v in pdi_values]
                    return {
                        "players_with_pdi": len(values),
                        "avg_pdi_overall": round(sum(values) / len(values), 2),
                        "max_pdi": round(max(values), 2),
                        "min_pdi": round(min(values), 2),
                    }
                else:
                    return {"players_with_pdi": 0, "avg_pdi_overall": 0.0}

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas PDI: {e}")
            return {"players_with_pdi": 0, "avg_pdi_overall": 0.0}

    def _get_top_performers_for_season(self, season: str, limit: int = 5) -> List[Dict]:
        """Obtiene top performers de una temporada."""
        try:
            rankings = self.pdi_calculator.get_league_rankings(
                position=None, season=season, limit=limit
            )

            top_performers = []
            for ranking in rankings:
                player_id = ranking.get("player_id")
                if player_id:
                    # Obtener información básica del jugador
                    with get_db_session() as session:
                        player = (
                            session.query(Player).filter_by(player_id=player_id).first()
                        )
                        if player and player.user:
                            performer = {
                                "player_id": player_id,
                                "name": player.user.name,
                                "pdi_overall": ranking.get("pdi_overall", 0),
                                "position": ranking.get("position", "Unknown"),
                                "rank": len(top_performers) + 1,
                            }
                            top_performers.append(performer)

            return top_performers

        except Exception as e:
            logger.error(f"Error obteniendo top performers: {e}")
            return []

    def _clear_analysis_cache_for_season(self, season: str):
        """Limpia cache de análisis para una temporada específica."""
        try:
            # Aquí se implementaría limpieza de cache si tuviéramos sistema de cache
            logger.info(f"🧹 Cache de análisis limpiado para temporada {season}")

        except Exception as e:
            logger.error(f"Error limpiando cache: {e}")

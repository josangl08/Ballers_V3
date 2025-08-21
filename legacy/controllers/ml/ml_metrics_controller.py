"""
MLMetricsController - Controlador principal para métricas de Machine Learning.

Este módulo implementa el Player Development Index (PDI) siguiendo metodología CRISP-DM
con un modelo unificado híbrido que combina:
- Métricas universales (40%): Aplicables a todas las posiciones
- Métricas por zona (35%): Defensivas, mediocampo, ofensivas
- Métricas específicas (25%): Por posición particular

Arquitectura:
- Shared encoder para features comunes
- Position heads especializados por posición
- Normalización posicional para comparaciones justas
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from controllers.db import get_db_session

# Import directo para evitar circular imports
from models.ml_metrics_model import MLMetrics
from models.player_model import Player
from models.professional_stats_model import ProfessionalStats

from .feature_engineer import FeatureEngineer
from .position_normalizer import PositionNormalizer

# Configurar logging
logger = logging.getLogger(__name__)


class MLMetricsController:
    """
    Controlador principal para cálculo y gestión de métricas ML.

    Responsabilidades:
    - Cálculo del Player Development Index (PDI)
    - Gestión de cache y recálculos
    - Normalización por posición
    - Integración con sistema existente
    """

    def __init__(self):
        """Inicializa el controlador con configuraciones por defecto."""
        self.model_version = "1.0"
        self.cache_duration_days = 7

        # Pesos para componentes PDI (arquitectura híbrida)
        self.pdi_weights = {
            "universal": 0.40,  # Métricas universales
            "zone": 0.35,  # Métricas por zona
            "position_specific": 0.25,  # Específicas por posición
        }

        # Posiciones soportadas
        self.supported_positions = {
            "GK": "Goalkeeper",
            "CB": "Centre-Back",
            "FB": "Full-Back",
            "DMF": "Defensive Midfielder",
            "CMF": "Central Midfielder",
            "AMF": "Attacking Midfielder",
            "W": "Winger",
            "CF": "Centre-Forward",
        }

        # Inicializar componentes del pipeline ETL ML
        self.feature_engineer = FeatureEngineer()
        self.position_normalizer = PositionNormalizer()

        logger.info(
            "MLMetricsController inicializado con modelo v%s", self.model_version
        )

    def get_or_calculate_metrics(
        self, player_id: int, season: str = "2024-25", force_recalculate: bool = False
    ) -> Optional[MLMetrics]:
        """
        Obtiene métricas ML existentes o las calcula si no existen/están obsoletas.

        Args:
            player_id: ID del jugador
            season: Temporada a analizar
            force_recalculate: Forzar recálculo aunque existan métricas válidas

        Returns:
            MLMetrics: Métricas ML calculadas o None si no se puede calcular
        """
        try:
            with get_db_session() as session:
                # Verificar si el jugador existe y es profesional
                player = session.query(Player).filter_by(player_id=player_id).first()
                if not player or not player.is_professional:
                    logger.warning(
                        "Jugador %d no existe o no es profesional", player_id
                    )
                    return None

                # Buscar métricas existentes
                existing_metrics = (
                    session.query(MLMetrics)
                    .filter_by(player_id=player_id, season=season)
                    .first()
                )

                # Verificar si necesita recálculo
                if (
                    not force_recalculate
                    and existing_metrics
                    and not existing_metrics.is_stale
                ):
                    logger.debug(
                        "Usando métricas ML existentes para jugador %d", player_id
                    )
                    return existing_metrics

                # Calcular nuevas métricas
                logger.info(
                    "Calculando métricas ML para jugador %d temporada %s",
                    player_id,
                    season,
                )

                new_metrics = self._calculate_pdi_metrics(session, player, season)
                if not new_metrics:
                    logger.error("Error calculando métricas para jugador %d", player_id)
                    return None

                # Guardar en base de datos
                if existing_metrics:
                    # Actualizar existente
                    for key, value in new_metrics.items():
                        setattr(existing_metrics, key, value)
                    existing_metrics.last_calculated = datetime.utcnow()
                    existing_metrics.updated_at = datetime.utcnow()
                    session.commit()
                    logger.info("Métricas ML actualizadas para jugador %d", player_id)
                    return existing_metrics
                else:
                    # Crear nuevo registro
                    ml_metrics = MLMetrics(
                        player_id=player_id,
                        season=season,
                        model_version=self.model_version,
                        **new_metrics,
                    )
                    session.add(ml_metrics)
                    session.commit()
                    logger.info("Nuevas métricas ML creadas para jugador %d", player_id)
                    return ml_metrics

        except Exception as e:
            logger.error("Error en get_or_calculate_metrics: %s", str(e))
            return None

    def _calculate_pdi_metrics(
        self, session: Session, player: Player, season: str
    ) -> Optional[Dict]:
        """
        Calcula métricas PDI para un jugador específico.

        Args:
            session: Sesión de base de datos
            player: Objeto Player
            season: Temporada a analizar

        Returns:
            dict: Métricas calculadas o None si falla
        """
        try:
            # Obtener estadísticas profesionales
            prof_stats = (
                session.query(ProfessionalStats)
                .filter_by(player_id=player.player_id, season=season)
                .first()
            )

            if not prof_stats:
                logger.warning(
                    "No se encontraron stats profesionales para "
                    "jugador %d temporada %s",
                    player.player_id,
                    season,
                )
                return None

            # Determinar posición principal
            position = prof_stats.primary_position or "CF"  # Default fallback
            if position not in self.supported_positions:
                logger.warning("Posición %s no soportada, usando CF", position)
                position = "CF"

            # Extraer features usando FeatureEngineer
            logger.debug("Extrayendo features con FeatureEngineer")
            universal_features = self.feature_engineer.extract_universal_features(
                prof_stats
            )
            zone_features = self.feature_engineer.extract_zone_features(
                prof_stats, position
            )
            specific_features = (
                self.feature_engineer.extract_position_specific_features(
                    prof_stats, position
                )
            )

            # Obtener scores de features extraídas
            universal_score = universal_features.get("universal_composite_score", 50.0)
            zone_score = zone_features.get("zone_composite_score", 50.0)
            specific_score = specific_features.get(
                "position_specific_composite_score", 50.0
            )

            # PDI Overall con pesos híbridos
            pdi_overall = (
                universal_score * self.pdi_weights["universal"]
                + zone_score * self.pdi_weights["zone"]
                + specific_score * self.pdi_weights["position_specific"]
            )

            # Calcular métricas de desarrollo
            technical = self._calculate_technical_proficiency(prof_stats)
            tactical = self._calculate_tactical_intelligence(prof_stats)
            physical = self._calculate_physical_performance(prof_stats)
            consistency = self._calculate_consistency_index(prof_stats)

            # Normalizar métricas usando PositionNormalizer
            logger.debug("Normalizando métricas por posición")
            raw_metrics = {
                "pdi_overall": pdi_overall,
                "pdi_universal": universal_score,
                "pdi_zone": zone_score,
                "pdi_position_specific": specific_score,
                "technical_proficiency": technical,
                "tactical_intelligence": tactical,
                "physical_performance": physical,
                "consistency_index": consistency,
            }

            normalized_metrics = self.position_normalizer.normalize_player_metrics(
                raw_metrics, position, season
            )

            # Extraer percentiles normalizados
            position_percentile = normalized_metrics.get("pdi_overall_percentile", 50.0)
            league_percentile = position_percentile * 0.9  # Approximation

            return {
                "pdi_overall": round(pdi_overall, 2),
                "pdi_universal": round(universal_score, 2),
                "pdi_zone": round(zone_score, 2),
                "pdi_position_specific": round(specific_score, 2),
                "technical_proficiency": round(technical, 2),
                "tactical_intelligence": round(tactical, 2),
                "physical_performance": round(physical, 2),
                "consistency_index": round(consistency, 2),
                "position_percentile": round(position_percentile, 2),
                "league_percentile": round(league_percentile, 2),
                "position_analyzed": position,
                "features_used": 45,  # Placeholder
                "last_calculated": datetime.utcnow(),
            }

        except Exception as e:
            logger.error("Error calculando métricas PDI: %s", str(e))
            return None

    def _calculate_universal_metrics(self, stats: ProfessionalStats) -> float:
        """
        Calcula métricas universales (40% del PDI).

        Métricas aplicables a todas las posiciones:
        - Precisión de pase
        - Duelos ganados
        - Distancia recorrida (normalizada)
        - Disciplina

        Args:
            stats: Estadísticas del jugador

        Returns:
            float: Score universal (0-100)
        """
        try:
            metrics = []

            # Precisión de pase (30% peso)
            if stats.accurate_passes_pct:
                pass_score = min(
                    100, stats.accurate_passes_pct * 1.2
                )  # Boost ligeramente
                metrics.append(("pass_accuracy", pass_score, 0.30))

            # Duelos ganados (25% peso)
            if stats.duels_won_pct:
                duel_score = min(
                    100, stats.duels_won_pct * 1.5
                )  # Boost para importancia
                metrics.append(("duels", duel_score, 0.25))

            # Actividad física - minutos jugados (20% peso)
            if stats.minutes_played and stats.matches_played:
                avg_minutes = stats.minutes_played / stats.matches_played
                activity_score = min(100, (avg_minutes / 90) * 100)
                metrics.append(("activity", activity_score, 0.20))

            # Disciplina - inversa de tarjetas (25% peso)
            discipline_score = 100.0  # Start perfect
            if stats.yellow_cards and stats.matches_played:
                yellow_rate = stats.yellow_cards / stats.matches_played
                discipline_score = max(0, 100 - (yellow_rate * 50))
            metrics.append(("discipline", discipline_score, 0.25))

            # Promedio ponderado
            if not metrics:
                return 50.0  # Default si no hay datos

            weighted_sum = sum(score * weight for _, score, weight in metrics)
            total_weight = sum(weight for _, _, weight in metrics)

            return weighted_sum / total_weight if total_weight > 0 else 50.0

        except Exception as e:
            logger.error("Error en métricas universales: %s", str(e))
            return 50.0

    def _calculate_zone_metrics(self, stats: ProfessionalStats, position: str) -> float:
        """
        Calcula métricas por zona (35% del PDI).

        Pesos por posición:
        - GK: 80% defensivas, 20% distribución
        - CB/FB: 60% defensivas, 40% distribución
        - DMF: 40% defensivas, 60% mediocampo
        - CMF: 20% defensivas, 80% mediocampo
        - AMF: 10% defensivas, 50% mediocampo, 40% ofensivas
        - W/CF: 70% ofensivas, 30% mediocampo

        Args:
            stats: Estadísticas del jugador
            position: Posición del jugador

        Returns:
            float: Score por zona (0-100)
        """
        try:
            # Calcular scores por zona
            defensive_score = self._calculate_defensive_zone(stats)
            midfield_score = self._calculate_midfield_zone(stats)
            offensive_score = self._calculate_offensive_zone(stats)

            # Pesos específicos por posición
            zone_weights = {
                "GK": {"defensive": 0.8, "midfield": 0.2, "offensive": 0.0},
                "CB": {"defensive": 0.6, "midfield": 0.4, "offensive": 0.0},
                "FB": {"defensive": 0.5, "midfield": 0.3, "offensive": 0.2},
                "DMF": {"defensive": 0.4, "midfield": 0.6, "offensive": 0.0},
                "CMF": {"defensive": 0.2, "midfield": 0.8, "offensive": 0.0},
                "AMF": {"defensive": 0.1, "midfield": 0.5, "offensive": 0.4},
                "W": {"defensive": 0.0, "midfield": 0.3, "offensive": 0.7},
                "CF": {"defensive": 0.0, "midfield": 0.2, "offensive": 0.8},
            }

            weights = zone_weights.get(position, zone_weights["CMF"])  # Default CMF

            zone_score = (
                defensive_score * weights["defensive"]
                + midfield_score * weights["midfield"]
                + offensive_score * weights["offensive"]
            )

            return zone_score

        except Exception as e:
            logger.error("Error en métricas por zona: %s", str(e))
            return 50.0

    def _calculate_defensive_zone(self, stats: ProfessionalStats) -> float:
        """Calcula score defensivo."""
        try:
            metrics = []

            if stats.defensive_duels_won_pct:
                metrics.append(stats.defensive_duels_won_pct * 1.2)
            if stats.successful_defensive_actions_per_90:
                # Normalizar acciones defensivas (asumiendo max ~15 por partido)
                action_score = min(
                    100, (stats.successful_defensive_actions_per_90 / 15) * 100
                )
                metrics.append(action_score)
            if stats.interceptions_per_90:
                # Normalizar intercepciones (asumiendo max ~8 por partido)
                intercept_score = min(100, (stats.interceptions_per_90 / 8) * 100)
                metrics.append(intercept_score)

            return sum(metrics) / len(metrics) if metrics else 50.0

        except Exception as e:
            logger.error("Error en zona defensiva: %s", str(e))
            return 50.0

    def _calculate_midfield_zone(self, stats: ProfessionalStats) -> float:
        """Calcula score de mediocampo."""
        try:
            metrics = []

            if stats.passes_per_90:
                # Normalizar pases (asumiendo max ~100 por partido)
                pass_volume = min(100, (stats.passes_per_90 / 100) * 100)
                metrics.append(pass_volume)
            if stats.progressive_passes_per_90:
                # Normalizar pases progresivos (asumiendo max ~20 por partido)
                prog_score = min(100, (stats.progressive_passes_per_90 / 20) * 100)
                metrics.append(prog_score)
            if stats.key_passes_per_90:
                # Normalizar pases clave (asumiendo max ~5 por partido)
                key_score = min(100, (stats.key_passes_per_90 / 5) * 100)
                metrics.append(key_score)

            return sum(metrics) / len(metrics) if metrics else 50.0

        except Exception as e:
            logger.error("Error en zona mediocampo: %s", str(e))
            return 50.0

    def _calculate_offensive_zone(self, stats: ProfessionalStats) -> float:
        """Calcula score ofensivo."""
        try:
            metrics = []

            if stats.goals_per_90:
                # Normalizar goles (asumiendo max ~1.5 por partido para delanteros)
                goal_score = min(100, (stats.goals_per_90 / 1.5) * 100)
                metrics.append(goal_score)
            if stats.assists_per_90:
                # Normalizar asistencias (asumiendo max ~1 por partido)
                assist_score = min(100, (stats.assists_per_90 / 1.0) * 100)
                metrics.append(assist_score)
            if stats.shots_on_target_pct:
                metrics.append(stats.shots_on_target_pct)

            return sum(metrics) / len(metrics) if metrics else 50.0

        except Exception as e:
            logger.error("Error en zona ofensiva: %s", str(e))
            return 50.0

    def _calculate_position_specific_metrics(
        self, stats: ProfessionalStats, position: str
    ) -> float:
        """
        Calcula métricas específicas por posición (25% del PDI).

        Args:
            stats: Estadísticas del jugador
            position: Posición específica

        Returns:
            float: Score específico (0-100)
        """
        try:
            if position == "GK":
                return self._calculate_gk_specific(stats)
            elif position in ["CB", "FB"]:
                return self._calculate_defender_specific(stats)
            elif position in ["DMF", "CMF", "AMF"]:
                return self._calculate_midfielder_specific(stats, position)
            elif position in ["W", "CF"]:
                return self._calculate_forward_specific(stats)
            else:
                return 50.0  # Default

        except Exception as e:
            logger.error("Error en métricas específicas: %s", str(e))
            return 50.0

    def _calculate_gk_specific(self, stats: ProfessionalStats) -> float:
        """Métricas específicas para porteros."""
        # Placeholder - en futura iteración con datos específicos de porteros
        return 50.0

    def _calculate_defender_specific(self, stats: ProfessionalStats) -> float:
        """Métricas específicas para defensas."""
        try:
            metrics = []

            if stats.aerial_duels_won_pct:
                metrics.append(stats.aerial_duels_won_pct)
            if stats.long_passes_accuracy_pct:
                metrics.append(stats.long_passes_accuracy_pct)

            return sum(metrics) / len(metrics) if metrics else 50.0

        except Exception:
            return 50.0

    def _calculate_midfielder_specific(
        self, stats: ProfessionalStats, position: str
    ) -> float:
        """Métricas específicas para mediocampistas."""
        try:
            metrics = []

            # Común para todos los mediocampistas
            if stats.ball_recoveries_per_90:
                recovery_score = min(100, (stats.ball_recoveries_per_90 / 15) * 100)
                metrics.append(recovery_score)

            # Específico por sub-posición
            if position == "AMF" and stats.assists_per_90:
                assist_score = min(100, (stats.assists_per_90 / 0.8) * 100)
                metrics.append(assist_score)

            return sum(metrics) / len(metrics) if metrics else 50.0

        except Exception:
            return 50.0

    def _calculate_forward_specific(self, stats: ProfessionalStats) -> float:
        """Métricas específicas para delanteros."""
        try:
            metrics = []

            if stats.goal_conversion_pct:
                metrics.append(stats.goal_conversion_pct)
            if stats.touches_in_box_per_90:
                touch_score = min(100, (stats.touches_in_box_per_90 / 8) * 100)
                metrics.append(touch_score)

            return sum(metrics) / len(metrics) if metrics else 50.0

        except Exception:
            return 50.0

    def _calculate_technical_proficiency(self, stats: ProfessionalStats) -> float:
        """Calcula habilidades técnicas."""
        try:
            metrics = []

            if stats.successful_dribbles_pct:
                metrics.append(stats.successful_dribbles_pct)
            if stats.accurate_passes_pct:
                metrics.append(stats.accurate_passes_pct)
            if stats.first_touch_success_rate:
                metrics.append(stats.first_touch_success_rate)

            return sum(metrics) / len(metrics) if metrics else 50.0

        except Exception:
            return 50.0

    def _calculate_tactical_intelligence(self, stats: ProfessionalStats) -> float:
        """Calcula inteligencia táctica."""
        try:
            metrics = []

            if stats.progressive_passes_per_90:
                prog_score = min(100, (stats.progressive_passes_per_90 / 15) * 100)
                metrics.append(prog_score)
            if stats.key_passes_per_90:
                key_score = min(100, (stats.key_passes_per_90 / 4) * 100)
                metrics.append(key_score)

            return sum(metrics) / len(metrics) if metrics else 50.0

        except Exception:
            return 50.0

    def _calculate_physical_performance(self, stats: ProfessionalStats) -> float:
        """Calcula rendimiento físico."""
        try:
            metrics = []

            if stats.duels_won_pct:
                metrics.append(stats.duels_won_pct)
            if stats.accelerations_per_90:
                accel_score = min(100, (stats.accelerations_per_90 / 30) * 100)
                metrics.append(accel_score)

            return sum(metrics) / len(metrics) if metrics else 50.0

        except Exception:
            return 50.0

    def _calculate_consistency_index(self, stats: ProfessionalStats) -> float:
        """Calcula índice de consistencia."""
        try:
            # Base score
            consistency = 80.0

            # Penalizar por tarjetas
            if stats.yellow_cards and stats.matches_played:
                yellow_rate = stats.yellow_cards / stats.matches_played
                consistency -= yellow_rate * 20

            # Bonus por minutos jugados
            if stats.minutes_played and stats.matches_played:
                avg_minutes = stats.minutes_played / stats.matches_played
                if avg_minutes > 75:  # Jugador regular
                    consistency += 10

            return max(0, min(100, consistency))

        except Exception:
            return 50.0

    def get_league_rankings(
        self, season: str = "2024-25", limit: int = 50
    ) -> List[Dict]:
        """
        Obtiene ranking de liga por PDI.

        Args:
            season: Temporada a consultar
            limit: Número máximo de resultados

        Returns:
            list: Lista de jugadores ordenados por PDI
        """
        try:
            with get_db_session() as session:
                rankings = (
                    session.query(MLMetrics, Player)
                    .join(Player, MLMetrics.player_id == Player.player_id)
                    .filter(MLMetrics.season == season)
                    .order_by(MLMetrics.pdi_overall.desc())
                    .limit(limit)
                    .all()
                )

                return [
                    {
                        "player_id": ml_metrics.player_id,
                        "player_name": player.user.name if player.user else "Unknown",
                        "pdi_overall": ml_metrics.pdi_overall,
                        "position": ml_metrics.position_analyzed,
                        "league_rank": idx + 1,
                    }
                    for idx, (ml_metrics, player) in enumerate(rankings)
                ]

        except Exception as e:
            logger.error("Error obteniendo rankings: %s", str(e))
            return []

    def get_position_averages(self, position: str, season: str = "2024-25") -> Dict:
        """
        Calcula promedios por posición para benchmarking.

        Args:
            position: Posición a analizar
            season: Temporada

        Returns:
            dict: Promedios por posición
        """
        try:
            with get_db_session() as session:
                metrics = (
                    session.query(MLMetrics)
                    .filter_by(position_analyzed=position, season=season)
                    .all()
                )

                if not metrics:
                    return {}

                return {
                    "count": len(metrics),
                    "pdi_overall_avg": sum(m.pdi_overall or 0 for m in metrics)
                    / len(metrics),
                    "technical_avg": sum(m.technical_proficiency or 0 for m in metrics)
                    / len(metrics),
                    "tactical_avg": sum(m.tactical_intelligence or 0 for m in metrics)
                    / len(metrics),
                    "physical_avg": sum(m.physical_performance or 0 for m in metrics)
                    / len(metrics),
                    "consistency_avg": sum(m.consistency_index or 0 for m in metrics)
                    / len(metrics),
                }

        except Exception as e:
            logger.error("Error calculando promedios por posición: %s", str(e))
            return {}

    def generate_feature_quality_report(
        self, player_id: int, season: str = "2024-25"
    ) -> Dict[str, any]:
        """
        Genera reporte de calidad de features para un jugador.

        Args:
            player_id: ID del jugador
            season: Temporada a analizar

        Returns:
            dict: Reporte de calidad de features
        """
        try:
            with get_db_session() as session:
                # Obtener estadísticas del jugador
                prof_stats = (
                    session.query(ProfessionalStats)
                    .filter_by(player_id=player_id, season=season)
                    .first()
                )

                if not prof_stats:
                    return {
                        "error": "No se encontraron estadísticas profesionales",
                        "player_id": player_id,
                        "season": season,
                    }

                # Determinar posición
                position = prof_stats.primary_position or "CF"
                if position not in self.supported_positions:
                    position = "CF"

                # Generar reporte usando FeatureEngineer
                report = self.feature_engineer.generate_feature_quality_report(
                    prof_stats, position
                )

                return report

        except Exception as e:
            logger.error("Error generando reporte de calidad: %s", str(e))
            return {"error": str(e)}

    def get_position_rankings_normalized(
        self, position: str, season: str = "2024-25", limit: int = 50
    ) -> List[Dict[str, any]]:
        """
        Obtiene rankings normalizados por posición usando PositionNormalizer.

        Args:
            position: Posición para ranking
            season: Temporada a analizar
            limit: Número máximo de jugadores

        Returns:
            list: Lista de jugadores con métricas normalizadas
        """
        try:
            return self.position_normalizer.calculate_position_rankings(
                position, season, limit
            )

        except Exception as e:
            logger.error("Error obteniendo rankings normalizados: %s", str(e))
            return []

    def update_all_position_benchmarks(
        self, seasons: List[str] = None
    ) -> Dict[str, int]:
        """
        Actualiza benchmarks para todas las posiciones.

        Args:
            seasons: Lista de temporadas para incluir

        Returns:
            dict: Resumen de benchmarks actualizados
        """
        try:
            return self.position_normalizer.update_position_benchmarks(seasons)

        except Exception as e:
            logger.error("Error actualizando benchmarks: %s", str(e))
            return {}

    def get_enhanced_player_analysis(
        self, player_id: int, season: str = "2024-25"
    ) -> Dict[str, any]:
        """
        Análisis completo de un jugador incluyendo features y normalización.

        Args:
            player_id: ID del jugador
            season: Temporada a analizar

        Returns:
            dict: Análisis completo con features, métricas y ranking
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

                # Determinar posición
                position = prof_stats.primary_position or "CF"
                if position not in self.supported_positions:
                    position = "CF"

                # Análisis completo
                analysis = {
                    "player_info": {
                        "player_id": player_id,
                        "name": player.user.name if player.user else "Unknown",
                        "position": position,
                        "season": season,
                    },
                    "features": {
                        "universal": self.feature_engineer.extract_universal_features(
                            prof_stats
                        ),
                        "zone": self.feature_engineer.extract_zone_features(
                            prof_stats, position
                        ),
                        "position_specific": self.feature_engineer.extract_position_specific_features(
                            prof_stats, position
                        ),
                    },
                    "quality_report": self.feature_engineer.generate_feature_quality_report(
                        prof_stats, position
                    ),
                }

                # Obtener métricas ML existentes si están disponibles
                ml_metrics = (
                    session.query(MLMetrics)
                    .filter_by(player_id=player_id, season=season)
                    .first()
                )

                if ml_metrics:
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

                    # Normalizar métricas
                    normalized = self.position_normalizer.normalize_player_metrics(
                        raw_metrics, position, season
                    )

                    analysis["ml_metrics"] = {
                        "raw": raw_metrics,
                        "normalized": normalized,
                        "pdi_breakdown": ml_metrics.pdi_breakdown,
                    }

                return analysis

        except Exception as e:
            logger.error("Error en análisis completo: %s", str(e))
            return {"error": str(e)}

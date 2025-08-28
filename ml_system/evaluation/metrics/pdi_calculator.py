"""
PDI Calculator - Sistema completo de cálculo de Player Development Index.

Migrado desde controllers/ml/ml_metrics_controller.py manteniendo toda la lógica
científica y de negocio. Implementa arquitectura híbrida:
- Métricas universales (40%): Aplicables a todas las posiciones
- Métricas por zona (35%): Defensivas, mediocampo, ofensivas
- Métricas específicas (25%): Por posición particular
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

# Imports desde el sistema principal
from controllers.db import get_db_session

# NUEVO: Import del Enhanced Feature Engineer con Legacy Weights
from ml_system.evaluation.analysis.advanced_features import LegacyFeatureWeights
from models.ml_metrics_model import MLMetrics
from models.player_model import Player
from models.professional_stats_model import ProfessionalStats

logger = logging.getLogger(__name__)


class PDICalculator:
    """
    Calculador completo del Player Development Index (PDI) con lógica científica.

    Implementa sistema híbrido con pesos específicos por posición y zona:
    - 40% Universal: Métricas aplicables a todas las posiciones
    - 35% Zone: Métricas por zona según posición
    - 25% Position-specific: Métricas específicas por posición

    Soporta 8 posiciones: GK, CB, FB, DMF, CMF, AMF, W, CF
    """

    def __init__(self):
        """Inicializa el calculador PDI con configuraciones científicas y legacy weights."""
        self.model_version = "1.1"  # Incrementar versión por Legacy Integration
        self.cache_duration_days = 7

        # NUEVO: Legacy Feature Weights Integration
        self.legacy_weights = LegacyFeatureWeights()

        # Pesos para componentes PDI (arquitectura híbrida científica)
        self.pdi_weights = {
            "universal": 0.40,  # Métricas universales
            "zone": 0.35,  # Métricas por zona
            "position_specific": 0.25,  # Específicas por posición
        }

        # Posiciones científicas principales (8 grupos)
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

        # Mapeo completo: 27 posiciones Thai League → 8 grupos científicos
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

        # Pesos por zona específicos por posición científica (8 grupos)
        self.zone_weights = {
            "GK": {"defensive": 0.8, "midfield": 0.2, "offensive": 0.0},
            "CB": {"defensive": 0.6, "midfield": 0.4, "offensive": 0.0},
            "FB": {"defensive": 0.5, "midfield": 0.3, "offensive": 0.2},
            "DMF": {"defensive": 0.4, "midfield": 0.6, "offensive": 0.0},
            "CMF": {"defensive": 0.2, "midfield": 0.8, "offensive": 0.0},
            "AMF": {"defensive": 0.1, "midfield": 0.5, "offensive": 0.4},
            "W": {"defensive": 0.0, "midfield": 0.3, "offensive": 0.7},
            "CF": {"defensive": 0.0, "midfield": 0.2, "offensive": 0.8},
        }

        logger.info(
            "🎯 PDI Calculator inicializado con Legacy Feature Weights Integration"
        )
        logger.info(
            "⚖️ Versión 1.1: 8 grupos científicos + Pesos Legacy específicos por posición"
        )

    def _calculate_hierarchical_pdi(self, stats: ProfessionalStats) -> Optional[Dict]:
        """
        Calcula el PDI Jerárquico basado en dominios de habilidad y pesos por posición.
        Este es el nuevo método de cálculo que reemplaza la lógica anterior.

        Args:
            stats: Objeto ProfessionalStats con las estadísticas del jugador.

        Returns:
            dict: Un diccionario con el PDI general y el desglose por dominios.
        """
        logger.debug(
            f"Iniciando cálculo de PDI Jerárquico para jugador {stats.player_id}"
        )

        # 1. Definición de Dominios de Habilidad y las métricas que los componen
        SKILL_DOMAINS = {
            "attacking": {
                "goals_per_90": {"weight": 0.3, "range": (0, 1)},
                "expected_goals": {"weight": 0.3, "range": (0, 1)},
                "shots_on_target_pct": {"weight": 0.2, "range": (0, 100)},
                "goal_conversion_pct": {"weight": 0.2, "range": (0, 100)},
            },
            "playmaking": {
                "assists_per_90": {"weight": 0.3, "range": (0, 1)},
                "expected_assists": {"weight": 0.3, "range": (0, 1)},
                "key_passes_per_90": {"weight": 0.2, "range": (0, 5)},
                "progressive_passes_per_90": {"weight": 0.2, "range": (0, 20)},
            },
            "defending": {
                "defensive_duels_won_pct": {"weight": 0.4, "range": (0, 100)},
                "interceptions_per_90": {"weight": 0.3, "range": (0, 10)},
                "successful_defensive_actions_per_90": {
                    "weight": 0.3,
                    "range": (0, 15),
                },
            },
            "passing": {
                "pass_accuracy_pct": {"weight": 0.5, "range": (50, 100)},
                "long_passes_accuracy_pct": {"weight": 0.2, "range": (40, 100)},
                "accurate_passes_to_final_third_pct": {
                    "weight": 0.3,
                    "range": (50, 100),
                },
            },
            "physical": {
                "duels_won_pct": {"weight": 0.4, "range": (40, 100)},
                "aerial_duels_won_pct": {"weight": 0.3, "range": (30, 100)},
                "minutes_played": {
                    "weight": 0.3,
                    "range": (0, 3000),
                },  # As a proxy for stamina/availability
            },
        }

        # 2. Definición de Pesos por Posición (usando los 8 grupos científicos)
        POSITION_WEIGHTS = {
            "GK": {
                "defending": 0.5,
                "passing": 0.4,
                "physical": 0.1,
                "attacking": 0.0,
                "playmaking": 0.0,
            },
            "CB": {
                "defending": 0.6,
                "physical": 0.2,
                "passing": 0.2,
                "attacking": 0.0,
                "playmaking": 0.0,
            },
            "FB": {
                "defending": 0.4,
                "physical": 0.2,
                "passing": 0.2,
                "playmaking": 0.1,
                "attacking": 0.1,
            },
            "DMF": {
                "defending": 0.4,
                "passing": 0.3,
                "physical": 0.2,
                "playmaking": 0.1,
                "attacking": 0.0,
            },
            "CMF": {
                "passing": 0.4,
                "playmaking": 0.3,
                "physical": 0.1,
                "defending": 0.1,
                "attacking": 0.1,
            },
            "AMF": {
                "playmaking": 0.4,
                "attacking": 0.3,
                "passing": 0.2,
                "physical": 0.1,
                "defending": 0.0,
            },
            "W": {
                "attacking": 0.4,
                "playmaking": 0.4,
                "physical": 0.1,
                "passing": 0.1,
                "defending": 0.0,
            },
            "CF": {
                "attacking": 0.6,
                "physical": 0.2,
                "playmaking": 0.1,
                "passing": 0.1,
                "defending": 0.0,
            },
        }

        # Función helper para normalizar un valor
        def normalize(value, min_val, max_val):
            if value is None:
                return 0
            # Clamp the value to be within the expected range
            value = max(min_val, min(value, max_val))
            # Normalize to 0-100 scale
            return (
                ((value - min_val) / (max_val - min_val)) * 100
                if (max_val - min_val) != 0
                else 0
            )

        # 3. Calcular el score para cada dominio
        domain_scores = {}
        for domain, metrics in SKILL_DOMAINS.items():
            total_score = 0
            total_weight = 0
            for metric, config in metrics.items():
                value = getattr(stats, metric, None)
                if value is not None:
                    min_val, max_val = config["range"]
                    weight = config["weight"]
                    normalized_score = normalize(value, min_val, max_val)
                    total_score += normalized_score * weight
                    total_weight += weight

            domain_scores[domain] = (
                total_score / total_weight if total_weight > 0 else 0
            )
            logger.debug(f"Dominio '{domain}' score: {domain_scores[domain]:.2f}")

        # 4. Calcular el PDI final usando los pesos de la posición
        position = self._normalize_position(stats.primary_position)
        position_weights = POSITION_WEIGHTS.get(
            position, POSITION_WEIGHTS["CMF"]
        )  # Fallback to CMF

        final_pdi_score = 0
        for domain, score in domain_scores.items():
            final_pdi_score += score * position_weights.get(domain, 0)

        logger.info(
            f"PDI Jerárquico calculado para {stats.player_id} en posición {position}: {final_pdi_score:.2f}"
        )

        # 5. Devolver el resultado completo
        result = {f"pdi_{domain}": score for domain, score in domain_scores.items()}
        result["pdi_overall"] = final_pdi_score

        return result

    def _normalize_position(self, original_position: str) -> str:
        """
        Normaliza posición original (27 variantes) a grupo científico (8 grupos).

        Args:
            original_position: Posición específica del dataset Thai League

        Returns:
            str: Grupo científico para cálculos ML (GK, CB, FB, DMF, CMF, AMF, W, CF)
        """
        if not original_position:
            return "CF"  # Default fallback

        # Mapear usando diccionario completo
        normalized = self.position_mapping.get(original_position)

        if not normalized:
            logger.warning(f"Posición '{original_position}' no mapeada, usando CF")
            return "CF"

        logger.debug(f"Posición normalizada: {original_position} → {normalized}")
        return normalized

        logger.info("🎯 PDICalculator inicializado con modelo v%s", self.model_version)

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

                # NUEVO: Validar que existe la temporada antes de procesar
                prof_stats_check = (
                    session.query(ProfessionalStats)
                    .filter_by(player_id=player_id, season=season)
                    .first()
                )

                if not prof_stats_check:
                    logger.warning(
                        "No se encontraron stats profesionales para jugador %d temporada %s - Temporada no válida",
                        player_id,
                        season,
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

                    # Refrescar objeto para asegurar datos actualizados
                    session.refresh(existing_metrics)
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

                    # Refrescar objeto para asegurar datos actualizados
                    session.refresh(ml_metrics)
                    logger.info("Nuevas métricas ML creadas para jugador %d", player_id)
                    return ml_metrics

        except Exception as e:
            logger.error("Error en get_or_calculate_metrics: %s", str(e))
            return None

    def _calculate_pdi_metrics(
        self, session: Session, player: Player, season: str
    ) -> Optional[Dict]:
        """
        Calcula métricas PDI para un jugador específico usando lógica científica.

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
                    "No se encontraron stats profesionales para jugador %d temporada %s",
                    player.player_id,
                    season,
                )
                return None

            # Determinar y normalizar posición (27 variantes → 8 grupos científicos)
            original_position = prof_stats.primary_position or "CF"
            position = self._normalize_position(original_position)

            # NUEVO: Obtener pesos legacy específicos por posición
            position_weights = self.legacy_weights.get_feature_weights_for_position(
                original_position
            )

            # Calcular componentes PDI con pesos legacy mejorados
            logger.debug(
                "Calculando componentes PDI para posición %s con legacy weights",
                position,
            )

            universal_score = self._calculate_universal_metrics_enhanced(
                prof_stats, position_weights["universal"]
            )
            zone_score = self._calculate_zone_metrics_enhanced(
                prof_stats, position, position_weights["zone"]
            )
            specific_score = self._calculate_position_specific_metrics_enhanced(
                prof_stats, position, position_weights["position_specific"]
            )

            # Cálculo PDI final con pesos híbridos
            pdi_score = (
                universal_score * self.pdi_weights["universal"]
                + zone_score * self.pdi_weights["zone"]
                + specific_score * self.pdi_weights["position_specific"]
            )

            # Métricas adicionales de calidad
            technical_score = self._calculate_technical_proficiency(prof_stats)
            tactical_score = self._calculate_tactical_intelligence(prof_stats)
            physical_score = self._calculate_physical_performance(prof_stats)
            consistency_score = self._calculate_consistency_index(prof_stats)

            # Retornar métricas completas (compatible con MLMetrics model)
            return {
                "pdi_overall": round(pdi_score, 2),  # Usar nombre compatible con modelo
                "pdi_universal": round(universal_score, 2),
                "pdi_zone": round(zone_score, 2),
                "pdi_position_specific": round(specific_score, 2),
                "technical_proficiency": round(technical_score, 2),
                "tactical_intelligence": round(tactical_score, 2),
                "physical_performance": round(physical_score, 2),
                "consistency_index": round(consistency_score, 2),
                "position_analyzed": f"{original_position} ({position})",  # Mostrar original + grupo
                "last_calculated": datetime.utcnow(),
            }

        except Exception as e:
            logger.error("Error calculando PDI metrics: %s", str(e))
            return None

    # === MÉTODOS ENHANCED CON LEGACY WEIGHTS ===

    def _calculate_universal_metrics_enhanced(
        self, stats: ProfessionalStats, legacy_weights: Dict
    ) -> float:
        """
        Calcula métricas universales usando pesos legacy específicos.

        Args:
            stats: Estadísticas del jugador
            legacy_weights: Pesos legacy para features universales

        Returns:
            float: Score universal enhanced (0-100)
        """
        try:
            if not legacy_weights:
                # Fallback al método original
                return self._calculate_universal_metrics(stats)

            total_score = 0.0
            total_weight = 0.0

            # Mapeo de campos legacy a ProfessionalStats model
            field_mapping = {
                "accurate_passes_pct": "pass_accuracy_pct",
                "duels_won_pct": "duels_won_pct",
                "defensive_duels_won_pct": "defensive_duels_won_pct",
                "yellow_cards_per_90": "yellow_cards",  # Necesitará conversión per_90
            }

            for category, features in legacy_weights.items():
                for feature_name, config in features.items():
                    mapped_field = field_mapping.get(feature_name)
                    if mapped_field and hasattr(stats, mapped_field):
                        value = getattr(stats, mapped_field)
                        if value is not None and value >= 0:
                            weight = config.get("weight", 0.1)
                            expected_range = config.get("expected_range", (0, 100))

                            # Conversión especial para yellow cards per 90
                            if (
                                feature_name == "yellow_cards_per_90"
                                and stats.matches_played
                            ):
                                value = (
                                    (value / stats.matches_played)
                                    * 90
                                    / stats.minutes_played
                                    if stats.minutes_played > 0
                                    else 0
                                )
                                # Inverse normalization para tarjetas (menos es mejor)
                                normalized_value = max(
                                    0, 100 - (value / expected_range[1]) * 100
                                )
                            else:
                                # Normalización estándar
                                min_val, max_val = expected_range
                                normalized_value = max(
                                    0,
                                    min(
                                        100,
                                        ((value - min_val) / (max_val - min_val)) * 100,
                                    ),
                                )

                            total_score += normalized_value * weight
                            total_weight += weight

            enhanced_score = total_score / total_weight if total_weight > 0 else 50.0

            # Blend con score original (70% enhanced, 30% original para estabilidad)
            original_score = self._calculate_universal_metrics(stats)
            final_score = enhanced_score * 0.7 + original_score * 0.3

            logger.debug(
                f"Universal enhanced: {enhanced_score:.1f} -> final: {final_score:.1f}"
            )
            return final_score

        except Exception as e:
            logger.error("Error en universal metrics enhanced: %s", str(e))
            return self._calculate_universal_metrics(stats)  # Fallback

    def _calculate_zone_metrics_enhanced(
        self, stats: ProfessionalStats, position: str, legacy_weights: Dict
    ) -> float:
        """
        Calcula métricas por zona usando pesos legacy específicos.

        Args:
            stats: Estadísticas del jugador
            position: Posición normalizada
            legacy_weights: Pesos legacy para features por zona

        Returns:
            float: Score por zona enhanced (0-100)
        """
        try:
            if not legacy_weights:
                # Fallback al método original
                return self._calculate_zone_metrics(stats, position)

            zone_scores = {}

            # Calcular score por cada zona usando legacy weights
            for zone_name, zone_features in legacy_weights.items():
                zone_score = self._calculate_legacy_zone_score(
                    stats, zone_features, zone_name
                )
                zone_scores[zone_name] = zone_score

            # Aplicar pesos por posición (del sistema original)
            position_zone_weights = self.zone_weights.get(
                position, self.zone_weights["CMF"]
            )

            # Weighted average usando pesos por posición
            weighted_score = (
                zone_scores.get("defensive", 50.0)
                * position_zone_weights.get("defensive", 0.3)
                + zone_scores.get("midfield", 50.0)
                * position_zone_weights.get("midfield", 0.4)
                + zone_scores.get("offensive", 50.0)
                * position_zone_weights.get("offensive", 0.3)
            )

            # Blend con score original
            original_score = self._calculate_zone_metrics(stats, position)
            final_score = weighted_score * 0.7 + original_score * 0.3

            logger.debug(
                f"Zone enhanced para {position}: {weighted_score:.1f} -> final: {final_score:.1f}"
            )
            return final_score

        except Exception as e:
            logger.error("Error en zone metrics enhanced: %s", str(e))
            return self._calculate_zone_metrics(stats, position)  # Fallback

    def _calculate_position_specific_metrics_enhanced(
        self, stats: ProfessionalStats, position: str, legacy_weights: Dict
    ) -> float:
        """
        Calcula métricas específicas por posición usando pesos legacy.

        Args:
            stats: Estadísticas del jugador
            position: Posición normalizada
            legacy_weights: Pesos legacy específicos por posición

        Returns:
            float: Score específico enhanced (0-100)
        """
        try:
            if not legacy_weights:
                # Fallback al método original
                return self._calculate_position_specific_metrics(stats, position)

            total_score = 0.0
            total_weight = 0.0

            # Mapeo de campos legacy a ProfessionalStats
            field_mapping = {
                "aerial_duels_won_pct": "aerial_duels_won_pct",
                "successful_dribbles_pct": "dribbles_success_pct",
                "goals_per_90": "goals_per_90",
                "assists_per_90": "assists_per_90",
                "goal_conversion_pct": "goal_conversion_pct",
                "touches_in_box_per_90": "touches_in_box_per_90",
                "crosses_per_90": "crosses_per_90",
                "long_passes_accuracy_pct": "long_passes_accuracy_pct",
            }

            for feature_name, config in legacy_weights.items():
                mapped_field = field_mapping.get(feature_name)
                if mapped_field and hasattr(stats, mapped_field):
                    value = getattr(stats, mapped_field)
                    if value is not None and value >= 0:
                        weight = config.get("weight", 0.1)
                        expected_range = config.get("expected_range", (0, 100))

                        # Normalización
                        min_val, max_val = expected_range
                        normalized_value = max(
                            0, min(100, ((value - min_val) / (max_val - min_val)) * 100)
                        )

                        total_score += normalized_value * weight
                        total_weight += weight

            enhanced_score = total_score / total_weight if total_weight > 0 else 50.0

            # Blend con score original
            original_score = self._calculate_position_specific_metrics(stats, position)
            final_score = enhanced_score * 0.7 + original_score * 0.3

            logger.debug(
                f"Position-specific enhanced para {position}: {enhanced_score:.1f} -> final: {final_score:.1f}"
            )
            return final_score

        except Exception as e:
            logger.error("Error en position-specific metrics enhanced: %s", str(e))
            return self._calculate_position_specific_metrics(
                stats, position
            )  # Fallback

    def _calculate_legacy_zone_score(
        self, stats: ProfessionalStats, zone_features: Dict, zone_name: str
    ) -> float:
        """Calcula score para una zona específica usando legacy features."""
        try:
            total_score = 0.0
            total_weight = 0.0

            # Mapeo específico por zona
            field_mappings = {
                # Offensive zone
                "goals_per_90": "goals_per_90",
                "assists_per_90": "assists_per_90",
                "shots_on_target_pct": "shots_on_target_pct",
                # Midfield zone
                "progressive_passes_per_90": "progressive_passes_per_90",
                "key_passes_per_90": "key_passes_per_90",
                "ball_recoveries_per_90": "ball_recoveries_per_90",
                # Defensive zone
                "successful_defensive_actions_per_90": "defensive_actions_per_90",
                "interceptions_per_90": "interceptions_per_90",
                "clearances_per_90": "clearances_per_90",
            }

            for feature_name, config in zone_features.items():
                mapped_field = field_mappings.get(feature_name)
                if mapped_field and hasattr(stats, mapped_field):
                    value = getattr(stats, mapped_field)
                    if value is not None and value >= 0:
                        weight = config.get("weight", 0.1)
                        expected_range = config.get("expected_range", (0, 10))

                        # Normalización
                        min_val, max_val = expected_range
                        normalized_value = max(
                            0, min(100, ((value - min_val) / (max_val - min_val)) * 100)
                        )

                        total_score += normalized_value * weight
                        total_weight += weight

            return total_score / total_weight if total_weight > 0 else 50.0

        except Exception as e:
            logger.error(f"Error calculando zone score para {zone_name}: {e}")
            return 50.0

    def _calculate_universal_metrics(self, stats: ProfessionalStats) -> float:
        """
        Calcula métricas universales (40% del PDI).

        Métricas aplicables a todas las posiciones con pesos científicos:
        - Precisión de pase (30% peso)
        - Duelos ganados (25% peso)
        - Actividad física - minutos jugados (20% peso)
        - Disciplina - inversa de tarjetas (25% peso)

        Args:
            stats: Estadísticas del jugador

        Returns:
            float: Score universal (0-100)
        """
        try:
            metrics = []

            # Precisión de pase (30% peso) con boost inteligente
            if stats.pass_accuracy_pct:
                pass_score = min(
                    100, stats.pass_accuracy_pct * 1.2
                )  # Boost ligeramente
                metrics.append(("pass_accuracy", pass_score, 0.30))

            # Duelos ganados (25% peso) con boost por importancia
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

            # Promedio ponderado con fallback inteligente
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

        Pesos específicos por posición basados en lógica futbolística:
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

            # Obtener pesos específicos por posición
            weights = self.zone_weights.get(
                position, self.zone_weights["CMF"]
            )  # Default CMF

            # Cálculo ponderado por zona
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
        """Calcula métricas defensivas con pesos específicos."""
        try:
            metrics = []

            # Acciones defensivas per 90 (40% peso)
            if stats.defensive_actions_per_90:
                def_score = min(
                    100, stats.defensive_actions_per_90 * 4
                )  # Escala apropiada
                metrics.append(("defensive_actions", def_score, 0.40))

            # Duelos defensivos ganados (35% peso)
            if stats.defensive_duels_won_pct:
                def_duels_score = min(100, stats.defensive_duels_won_pct * 1.3)
                metrics.append(("defensive_duels", def_duels_score, 0.35))

            # Duelos aéreos (25% peso)
            if stats.aerial_duels_won_pct:
                aerial_score = min(100, stats.aerial_duels_won_pct * 1.2)
                metrics.append(("aerial_duels", aerial_score, 0.25))

            # Promedio ponderado
            if not metrics:
                return 50.0

            weighted_sum = sum(score * weight for _, score, weight in metrics)
            total_weight = sum(weight for _, _, weight in metrics)

            return weighted_sum / total_weight if total_weight > 0 else 50.0

        except Exception as e:
            logger.error("Error en zona defensiva: %s", str(e))
            return 50.0

    def _calculate_midfield_zone(self, stats: ProfessionalStats) -> float:
        """Calcula métricas de mediocampo con énfasis en distribución."""
        try:
            metrics = []

            # Pases per 90 (30% peso)
            if stats.passes_per_90:
                passes_score = min(100, stats.passes_per_90 / 6)  # Escala apropiad
                metrics.append(("passes", passes_score, 0.30))

            # Precisión de pases progresivos (35% peso)
            if stats.progressive_passes_accuracy_pct:
                prog_score = min(100, stats.progressive_passes_accuracy_pct * 1.1)
                metrics.append(("progressive_passes", prog_score, 0.35))

            # Pases clave per 90 (35% peso)
            if stats.key_passes_per_90:
                key_score = min(
                    100, stats.key_passes_per_90 * 25
                )  # Boost por importancia
                metrics.append(("key_passes", key_score, 0.35))

            # Promedio ponderado
            if not metrics:
                return 50.0

            weighted_sum = sum(score * weight for _, score, weight in metrics)
            total_weight = sum(weight for _, _, weight in metrics)

            return weighted_sum / total_weight if total_weight > 0 else 50.0

        except Exception as e:
            logger.error("Error en zona mediocampo: %s", str(e))
            return 50.0

    def _calculate_offensive_zone(self, stats: ProfessionalStats) -> float:
        """Calcula métricas ofensivas con énfasis en productividad."""
        try:
            metrics = []

            # Goles per 90 (40% peso)
            if stats.goals_per_90:
                goals_score = min(100, stats.goals_per_90 * 50)  # Boost por importancia
                metrics.append(("goals", goals_score, 0.40))

            # Asistencias per 90 (30% peso)
            if stats.assists_per_90:
                assists_score = min(100, stats.assists_per_90 * 40)
                metrics.append(("assists", assists_score, 0.30))

            # Expected Goals (30% peso)
            if stats.expected_goals:
                xg_score = min(100, stats.expected_goals * 20)
                metrics.append(("xg", xg_score, 0.30))

            # Promedio ponderado
            if not metrics:
                return 50.0

            weighted_sum = sum(score * weight for _, score, weight in metrics)
            total_weight = sum(weight for _, _, weight in metrics)

            return weighted_sum / total_weight if total_weight > 0 else 50.0

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
            float: Score específico por posición (0-100)
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
                logger.warning("Posición %s no reconocida, usando default", position)
                return 50.0

        except Exception as e:
            logger.error("Error en métricas específicas: %s", str(e))
            return 50.0

    def _calculate_gk_specific(self, stats: ProfessionalStats) -> float:
        """Métricas específicas para porteros."""
        # Para porteros, usar métricas defensivas como aproximación
        return self._calculate_defensive_zone(stats)

    def _calculate_defender_specific(self, stats: ProfessionalStats) -> float:
        """Métricas específicas para defensores (CB, FB)."""
        try:
            metrics = []

            # Intercepciones per 90 (40% peso)
            if stats.interceptions_per_90:
                int_score = min(100, stats.interceptions_per_90 * 10)
                metrics.append(("interceptions", int_score, 0.40))

            # Tackles sliding per 90 (30% peso)
            if stats.sliding_tackles_per_90:
                tackle_score = min(100, stats.sliding_tackles_per_90 * 20)
                metrics.append(("sliding_tackles", tackle_score, 0.30))

            # Duelos aéreos won % (30% peso)
            if stats.aerial_duels_won_pct:
                aerial_score = min(100, stats.aerial_duels_won_pct * 1.2)
                metrics.append(("aerial_duels", aerial_score, 0.30))

            if not metrics:
                return 50.0

            weighted_sum = sum(score * weight for _, score, weight in metrics)
            total_weight = sum(weight for _, _, weight in metrics)

            return weighted_sum / total_weight if total_weight > 0 else 50.0

        except Exception as e:
            logger.error("Error en métricas defender: %s", str(e))
            return 50.0

    def _calculate_midfielder_specific(
        self, stats: ProfessionalStats, position: str
    ) -> float:
        """Métricas específicas para mediocampistas según tipo."""
        try:
            metrics = []

            if position == "DMF":
                # DMF: Énfasis defensivo + distribución
                if stats.defensive_actions_per_90:
                    def_score = min(100, stats.defensive_actions_per_90 * 4)
                    metrics.append(("defensive_actions", def_score, 0.50))

                if stats.passes_per_90:
                    passes_score = min(100, stats.passes_per_90 / 6)
                    metrics.append(("passes", passes_score, 0.50))

            elif position == "CMF":
                # CMF: Distribución + versatilidad
                if stats.progressive_passes_per_90:
                    prog_score = min(100, stats.progressive_passes_per_90 * 8)
                    metrics.append(("progressive_passes", prog_score, 0.60))

                if stats.duels_won_pct:
                    duels_score = min(100, stats.duels_won_pct * 1.3)
                    metrics.append(("duels", duels_score, 0.40))

            elif position == "AMF":
                # AMF: Creatividad + finalización
                if stats.key_passes_per_90:
                    key_score = min(100, stats.key_passes_per_90 * 25)
                    metrics.append(("key_passes", key_score, 0.60))

                if stats.expected_assists:
                    xa_score = min(100, stats.expected_assists * 30)
                    metrics.append(("expected_assists", xa_score, 0.40))

            if not metrics:
                return 50.0

            weighted_sum = sum(score * weight for _, score, weight in metrics)
            total_weight = sum(weight for _, _, weight in metrics)

            return weighted_sum / total_weight if total_weight > 0 else 50.0

        except Exception as e:
            logger.error("Error en métricas midfielder: %s", str(e))
            return 50.0

    def _calculate_forward_specific(self, stats: ProfessionalStats) -> float:
        """Métricas específicas para delanteros (W, CF)."""
        try:
            metrics = []

            # Conversión de goles (40% peso)
            if stats.goal_conversion_pct:
                conv_score = min(100, stats.goal_conversion_pct * 2)  # Boost conversión
                metrics.append(("goal_conversion", conv_score, 0.40))

            # Toques en área per 90 (30% peso)
            if stats.touches_in_box_per_90:
                box_score = min(100, stats.touches_in_box_per_90 * 8)
                metrics.append(("touches_in_box", box_score, 0.30))

            # Shot assists per 90 (30% peso)
            if stats.shot_assists_per_90:
                shot_assists_score = min(100, stats.shot_assists_per_90 * 15)
                metrics.append(("shot_assists", shot_assists_score, 0.30))

            if not metrics:
                return 50.0

            weighted_sum = sum(score * weight for _, score, weight in metrics)
            total_weight = sum(weight for _, _, weight in metrics)

            return weighted_sum / total_weight if total_weight > 0 else 50.0

        except Exception as e:
            logger.error("Error en métricas forward: %s", str(e))
            return 50.0

    def _calculate_technical_proficiency(self, stats: ProfessionalStats) -> float:
        """Calcula índice de competencia técnica."""
        try:
            metrics = []

            # Precisión de pase (30% peso)
            if stats.pass_accuracy_pct:
                pass_score = min(100, stats.pass_accuracy_pct * 1.1)
                metrics.append(("pass_accuracy", pass_score, 0.30))

            # Dribbles exitosos (25% peso)
            if stats.dribbles_success_pct:
                dribble_score = min(100, stats.dribbles_success_pct * 1.2)
                metrics.append(("dribbles", dribble_score, 0.25))

            # Precisión de pases largos (25% peso)
            if stats.long_passes_accuracy_pct:
                long_score = min(100, stats.long_passes_accuracy_pct * 1.1)
                metrics.append(("long_passes", long_score, 0.25))

            # Toques y control (20% peso)
            if stats.touches_in_box_per_90:
                touch_score = min(100, stats.touches_in_box_per_90 * 5)
                metrics.append(("touches", touch_score, 0.20))

            if not metrics:
                return 50.0

            weighted_sum = sum(score * weight for _, score, weight in metrics)
            total_weight = sum(weight for _, _, weight in metrics)

            return weighted_sum / total_weight if total_weight > 0 else 50.0

        except Exception as e:
            logger.error("Error en competencia técnica: %s", str(e))
            return 50.0

    def _calculate_tactical_intelligence(self, stats: ProfessionalStats) -> float:
        """Calcula índice de inteligencia táctica."""
        try:
            metrics = []

            # Pases progresivos (40% peso)
            if stats.progressive_passes_per_90:
                prog_score = min(100, stats.progressive_passes_per_90 * 6)
                metrics.append(("progressive_passes", prog_score, 0.40))

            # Carreras progresivas (30% peso)
            if stats.progressive_runs_per_90:
                runs_score = min(100, stats.progressive_runs_per_90 * 15)
                metrics.append(("progressive_runs", runs_score, 0.30))

            # Posicionamiento - duelos ganados (30% peso)
            if stats.duels_won_pct:
                positioning_score = min(100, stats.duels_won_pct * 1.2)
                metrics.append(("positioning", positioning_score, 0.30))

            if not metrics:
                return 50.0

            weighted_sum = sum(score * weight for _, score, weight in metrics)
            total_weight = sum(weight for _, _, weight in metrics)

            return weighted_sum / total_weight if total_weight > 0 else 50.0

        except Exception as e:
            logger.error("Error en inteligencia táctica: %s", str(e))
            return 50.0

    def _calculate_physical_performance(self, stats: ProfessionalStats) -> float:
        """Calcula índice de rendimiento físico."""
        try:
            metrics = []

            # Duelos físicos ganados (40% peso)
            if stats.offensive_duels_won_pct:
                physical_score = min(100, stats.offensive_duels_won_pct * 1.3)
                metrics.append(("physical_duels", physical_score, 0.40))

            # Intensidad - carreras progresivas (35% peso)
            if stats.progressive_runs_per_90:
                intensity_score = min(100, stats.progressive_runs_per_90 * 12)
                metrics.append(("intensity", intensity_score, 0.35))

            # Resistencia - minutos jugados (25% peso)
            if stats.minutes_played and stats.matches_played:
                avg_minutes = stats.minutes_played / stats.matches_played
                endurance_score = min(100, (avg_minutes / 90) * 100)
                metrics.append(("endurance", endurance_score, 0.25))

            if not metrics:
                return 50.0

            weighted_sum = sum(score * weight for _, score, weight in metrics)
            total_weight = sum(weight for _, _, weight in metrics)

            return weighted_sum / total_weight if total_weight > 0 else 50.0

        except Exception as e:
            logger.error("Error en rendimiento físico: %s", str(e))
            return 50.0

    def _calculate_consistency_index(self, stats: ProfessionalStats) -> float:
        """Calcula índice de consistencia basado en disciplina y rendimiento."""
        try:
            metrics = []

            # Disciplina - inversa de tarjetas (50% peso)
            discipline_score = 100.0
            if stats.yellow_cards and stats.matches_played:
                yellow_rate = stats.yellow_cards / stats.matches_played
                discipline_score = max(
                    0, 100 - (yellow_rate * 60)
                )  # Penalización por indisciplina
            metrics.append(("discipline", discipline_score, 0.50))

            # Regularidad - minutos jugados (30% peso)
            if stats.minutes_played and stats.matches_played:
                avg_minutes = stats.minutes_played / stats.matches_played
                regularity_score = min(100, (avg_minutes / 90) * 100)
                metrics.append(("regularity", regularity_score, 0.30))

            # Eficiencia - ratio rendimiento (20% peso)
            efficiency_score = 70.0  # Base score
            if stats.pass_accuracy_pct:
                efficiency_score = min(100, stats.pass_accuracy_pct * 1.1)
            metrics.append(("efficiency", efficiency_score, 0.20))

            if not metrics:
                return 50.0

            weighted_sum = sum(score * weight for _, score, weight in metrics)
            total_weight = sum(weight for _, _, weight in metrics)

            return weighted_sum / total_weight if total_weight > 0 else 50.0

        except Exception as e:
            logger.error("Error en índice de consistencia: %s", str(e))
            return 50.0

    def get_league_rankings(
        self, position: str = None, season: str = "2024-25", limit: int = 20
    ) -> List[Dict]:
        """
        Obtiene rankings de liga normalizados por posición.

        Args:
            position: Posición específica para filtrar
            season: Temporada
            limit: Número de resultados

        Returns:
            List[Dict]: Rankings ordenados por PDI
        """
        try:
            with get_db_session() as session:
                query = session.query(MLMetrics).filter_by(season=season)

                if position:
                    query = query.filter_by(position=position)

                rankings = (
                    query.order_by(MLMetrics.pdi_overall.desc()).limit(limit).all()
                )

                return [
                    {
                        "player_id": metric.player_id,
                        "position": metric.position_analyzed,
                        "pdi_score": metric.pdi_overall,
                        "rank": idx + 1,
                    }
                    for idx, metric in enumerate(rankings)
                ]

        except Exception as e:
            logger.error("Error obteniendo rankings: %s", str(e))
            return []

    def get_position_averages(self, position: str, season: str = "2024-25") -> Dict:
        """
        Obtiene promedios por posición para benchmarking.

        Args:
            position: Posición específica
            season: Temporada

        Returns:
            Dict: Promedios por posición
        """
        try:
            with get_db_session() as session:
                metrics = (
                    session.query(MLMetrics)
                    .filter_by(season=season)
                    .filter(MLMetrics.position_analyzed.contains(position))
                    .all()
                )

                if not metrics:
                    return {}

                # Calcular promedios
                total_count = len(metrics)

                averages = {
                    "position": position,
                    "season": season,
                    "sample_size": total_count,
                    "avg_pdi_overall": sum(m.pdi_overall or 0 for m in metrics)
                    / total_count,
                    "avg_universal": sum(m.pdi_universal or 0 for m in metrics)
                    / total_count,
                    "avg_zone": sum(m.pdi_zone or 0 for m in metrics) / total_count,
                    "avg_specific": sum(m.pdi_position_specific or 0 for m in metrics)
                    / total_count,
                    "avg_technical": sum(m.technical_proficiency or 0 for m in metrics)
                    / total_count,
                    "avg_tactical": sum(m.tactical_intelligence or 0 for m in metrics)
                    / total_count,
                }

                return averages

        except Exception as e:
            logger.error("Error calculando promedios: %s", str(e))
            return {}

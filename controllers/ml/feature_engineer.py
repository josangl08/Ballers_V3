"""
FeatureEngineer - Módulo de ingeniería de features para ML.

Este módulo implementa la extracción y transformación de features por tiers:
- Universal (40%): Métricas aplicables a todas las posiciones
- Zone (35%): Métricas agrupadas por zonas del campo
- Position-Specific (25%): Métricas específicas por posición

Sigue metodología CRISP-DM y se integra con el MLMetricsController
para el cálculo del Player Development Index (PDI).
"""

import logging
from typing import Dict, List, Tuple

from models import ProfessionalStats

# Configurar logging
logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Ingeniería de features por tiers para análisis ML.

    Responsabilidades:
    - Extracción de features por niveles (Universal/Zone/Specific)
    - Transformación y normalización de estadísticas
    - Validación de calidad de datos
    - Generación de features derivadas
    """

    def __init__(self):
        """Inicializa el feature engineer con configuraciones por defecto."""
        self.min_matches_threshold = 3  # Mínimo de partidos para análisis válido
        self.confidence_threshold = 0.7  # Umbral de confianza para features

        # Definir features por tier
        self._initialize_feature_tiers()

        logger.info("FeatureEngineer inicializado con tiers definidos")

    def _initialize_feature_tiers(self):
        """Inicializa la definición de features por tiers."""

        # TIER 1: Universal Features (40% peso PDI)
        # Métricas aplicables a todas las posiciones
        self.universal_features = {
            "passing": {
                "accurate_passes_pct": {
                    "weight": 0.30,
                    "normalization": "percentage",
                    "expected_range": (60, 95),
                },
                "passes_per_90": {
                    "weight": 0.20,
                    "normalization": "per_90_scaled",
                    "expected_range": (20, 120),
                },
            },
            "dueling": {
                "duels_won_pct": {
                    "weight": 0.25,
                    "normalization": "percentage",
                    "expected_range": (40, 70),
                },
                "defensive_duels_won_pct": {
                    "weight": 0.15,
                    "normalization": "percentage",
                    "expected_range": (45, 80),
                },
            },
            "discipline": {
                "yellow_cards_per_90": {
                    "weight": 0.10,
                    "normalization": "inverse_per_90",
                    "expected_range": (0, 0.5),
                },
            },
        }

        # TIER 2: Zone Features (35% peso PDI)
        # Métricas agrupadas por zonas del campo
        self.zone_features = {
            "defensive": {
                "successful_defensive_actions_per_90": {
                    "weight": 0.25,
                    "normalization": "per_90_scaled",
                    "expected_range": (3, 20),
                },
                "interceptions_per_90": {
                    "weight": 0.20,
                    "normalization": "per_90_scaled",
                    "expected_range": (0.5, 10),
                },
                "clearances_per_90": {
                    "weight": 0.15,
                    "normalization": "per_90_scaled",
                    "expected_range": (1, 15),
                },
            },
            "midfield": {
                "progressive_passes_per_90": {
                    "weight": 0.30,
                    "normalization": "per_90_scaled",
                    "expected_range": (2, 25),
                },
                "key_passes_per_90": {
                    "weight": 0.25,
                    "normalization": "per_90_scaled",
                    "expected_range": (0.2, 8),
                },
                "ball_recoveries_per_90": {
                    "weight": 0.20,
                    "normalization": "per_90_scaled",
                    "expected_range": (3, 20),
                },
            },
            "offensive": {
                "goals_per_90": {
                    "weight": 0.35,
                    "normalization": "per_90_scaled",
                    "expected_range": (0, 2.0),
                },
                "assists_per_90": {
                    "weight": 0.30,
                    "normalization": "per_90_scaled",
                    "expected_range": (0, 1.5),
                },
                "shots_on_target_pct": {
                    "weight": 0.20,
                    "normalization": "percentage",
                    "expected_range": (25, 70),
                },
            },
        }

        # TIER 3: Position-Specific Features (25% peso PDI)
        # Métricas específicas por posición
        self.position_features = {
            "GK": {
                "saves_per_90": {
                    "weight": 0.40,
                    "normalization": "per_90_scaled",
                    "expected_range": (2, 8),
                },
                "save_pct": {
                    "weight": 0.35,
                    "normalization": "percentage",
                    "expected_range": (60, 90),
                },
                "clean_sheets_pct": {
                    "weight": 0.25,
                    "normalization": "percentage",
                    "expected_range": (20, 60),
                },
            },
            "CB": {
                "aerial_duels_won_pct": {
                    "weight": 0.35,
                    "normalization": "percentage",
                    "expected_range": (50, 85),
                },
                "long_passes_accuracy_pct": {
                    "weight": 0.30,
                    "normalization": "percentage",
                    "expected_range": (60, 90),
                },
                "blocks_per_90": {
                    "weight": 0.20,
                    "normalization": "per_90_scaled",
                    "expected_range": (0.5, 3),
                },
            },
            "FB": {
                "crosses_per_90": {
                    "weight": 0.30,
                    "normalization": "per_90_scaled",
                    "expected_range": (1, 8),
                },
                "crosses_accuracy_pct": {
                    "weight": 0.25,
                    "normalization": "percentage",
                    "expected_range": (20, 50),
                },
                "tackles_per_90": {
                    "weight": 0.25,
                    "normalization": "per_90_scaled",
                    "expected_range": (1, 6),
                },
            },
            "DMF": {
                "ball_recoveries_per_90": {
                    "weight": 0.40,
                    "normalization": "per_90_scaled",
                    "expected_range": (5, 18),
                },
                "passes_per_90": {
                    "weight": 0.30,
                    "normalization": "per_90_scaled",
                    "expected_range": (40, 120),
                },
                "interceptions_per_90": {
                    "weight": 0.30,
                    "normalization": "per_90_scaled",
                    "expected_range": (2, 8),
                },
            },
            "CMF": {
                "progressive_passes_per_90": {
                    "weight": 0.35,
                    "normalization": "per_90_scaled",
                    "expected_range": (5, 20),
                },
                "accurate_passes_pct": {
                    "weight": 0.30,
                    "normalization": "percentage",
                    "expected_range": (80, 95),
                },
                "key_passes_per_90": {
                    "weight": 0.25,
                    "normalization": "per_90_scaled",
                    "expected_range": (1, 6),
                },
            },
            "AMF": {
                "assists_per_90": {
                    "weight": 0.40,
                    "normalization": "per_90_scaled",
                    "expected_range": (0.2, 1.2),
                },
                "key_passes_per_90": {
                    "weight": 0.35,
                    "normalization": "per_90_scaled",
                    "expected_range": (2, 8),
                },
                "successful_dribbles_pct": {
                    "weight": 0.25,
                    "normalization": "percentage",
                    "expected_range": (50, 80),
                },
            },
            "W": {
                "successful_dribbles_pct": {
                    "weight": 0.35,
                    "normalization": "percentage",
                    "expected_range": (50, 75),
                },
                "crosses_per_90": {
                    "weight": 0.30,
                    "normalization": "per_90_scaled",
                    "expected_range": (2, 10),
                },
                "accelerations_per_90": {
                    "weight": 0.20,
                    "normalization": "per_90_scaled",
                    "expected_range": (15, 40),
                },
            },
            "CF": {
                "goals_per_90": {
                    "weight": 0.45,
                    "normalization": "per_90_scaled",
                    "expected_range": (0.2, 2.0),
                },
                "goal_conversion_pct": {
                    "weight": 0.30,
                    "normalization": "percentage",
                    "expected_range": (10, 30),
                },
                "touches_in_box_per_90": {
                    "weight": 0.25,
                    "normalization": "per_90_scaled",
                    "expected_range": (3, 12),
                },
            },
        }

    def extract_universal_features(self, stats: ProfessionalStats) -> Dict[str, float]:
        """
        Extrae features universales aplicables a todas las posiciones.

        Args:
            stats: Estadísticas del jugador

        Returns:
            dict: Features universales con scores normalizados (0-100)
        """
        try:
            features = {}

            # Validar datos mínimos
            if not self._validate_minimum_data(stats):
                logger.warning(
                    "Datos insuficientes para player_id=%s",
                    getattr(stats, "player_id", "unknown"),
                )
                return self._get_default_universal_features()

            # Extraer features de passing
            passing_scores = self._extract_passing_features(stats)
            features.update(passing_scores)

            # Extraer features de dueling
            dueling_scores = self._extract_dueling_features(stats)
            features.update(dueling_scores)

            # Extraer features de disciplina
            discipline_scores = self._extract_discipline_features(stats)
            features.update(discipline_scores)

            # Calcular score universal compuesto
            universal_score = self._calculate_weighted_average(
                features, self.universal_features
            )
            features["universal_composite_score"] = universal_score

            logger.debug("Features universales extraídas: %d features", len(features))
            return features

        except Exception as e:
            logger.error("Error extrayendo features universales: %s", str(e))
            return self._get_default_universal_features()

    def extract_zone_features(
        self, stats: ProfessionalStats, position: str
    ) -> Dict[str, float]:
        """
        Extrae features por zona según la posición del jugador.

        Args:
            stats: Estadísticas del jugador
            position: Posición del jugador (GK, CB, FB, etc.)

        Returns:
            dict: Features por zona con scores normalizados (0-100)
        """
        try:
            features = {}

            # Determinar pesos por zona según posición
            zone_weights = self._get_zone_weights_by_position(position)

            # Extraer features por cada zona
            if zone_weights["defensive"] > 0:
                defensive_features = self._extract_defensive_zone_features(stats)
                features.update(
                    {f"defensive_{k}": v for k, v in defensive_features.items()}
                )

            if zone_weights["midfield"] > 0:
                midfield_features = self._extract_midfield_zone_features(stats)
                features.update(
                    {f"midfield_{k}": v for k, v in midfield_features.items()}
                )

            if zone_weights["offensive"] > 0:
                offensive_features = self._extract_offensive_zone_features(stats)
                features.update(
                    {f"offensive_{k}": v for k, v in offensive_features.items()}
                )

            # Calcular score compuesto por zona
            zone_score = self._calculate_zone_composite_score(features, zone_weights)
            features["zone_composite_score"] = zone_score

            logger.debug(
                "Features por zona extraídas para posición %s: %d features",
                position,
                len(features),
            )
            return features

        except Exception as e:
            logger.error("Error extrayendo features por zona: %s", str(e))
            return self._get_default_zone_features()

    def extract_position_specific_features(
        self, stats: ProfessionalStats, position: str
    ) -> Dict[str, float]:
        """
        Extrae features específicos por posición.

        Args:
            stats: Estadísticas del jugador
            position: Posición específica del jugador

        Returns:
            dict: Features específicos con scores normalizados (0-100)
        """
        try:
            features = {}

            # Verificar si tenemos definición para esta posición
            if position not in self.position_features:
                logger.warning("Posición %s no tiene features específicos", position)
                return self._get_default_position_features()

            position_config = self.position_features[position]

            # Extraer cada feature específico
            for feature_name, config in position_config.items():
                raw_value = getattr(stats, feature_name, None)

                if raw_value is not None:
                    normalized_score = self._normalize_feature_value(raw_value, config)
                    features[feature_name] = normalized_score
                else:
                    # Usar valor por defecto si no existe la estadística
                    features[feature_name] = 50.0  # Neutral score

            # Calcular score compuesto específico
            specific_score = self._calculate_weighted_average(
                features, {position: position_config}
            )
            features["position_specific_composite_score"] = specific_score

            logger.debug(
                "Features específicos extraídas para posición %s: %d features",
                position,
                len(features),
            )
            return features

        except Exception as e:
            logger.error("Error extrayendo features específicos: %s", str(e))
            return self._get_default_position_features()

    def generate_feature_quality_report(
        self, stats: ProfessionalStats, position: str
    ) -> Dict[str, any]:
        """
        Genera reporte de calidad de features para análisis.

        Args:
            stats: Estadísticas del jugador
            position: Posición del jugador

        Returns:
            dict: Reporte de calidad y completitud de features
        """
        try:
            report = {
                "player_id": stats.player_id,
                "position": position,
                "matches_played": stats.matches_played,
                "minutes_played": stats.minutes_played,
                "data_quality": {},
                "feature_coverage": {},
                "confidence_score": 0.0,
            }

            # Evaluar calidad por tier
            universal_coverage = self._evaluate_tier_coverage(
                stats, self.universal_features
            )
            zone_coverage = self._evaluate_zone_coverage(stats, position)
            position_coverage = self._evaluate_position_coverage(stats, position)

            report["feature_coverage"] = {
                "universal": universal_coverage,
                "zone": zone_coverage,
                "position_specific": position_coverage,
            }

            # Calcular score de confianza global
            confidence = self._calculate_confidence_score(
                stats, [universal_coverage, zone_coverage, position_coverage]
            )
            report["confidence_score"] = confidence

            # Evaluar calidad de datos
            report["data_quality"] = self._evaluate_data_quality(stats)

            return report

        except Exception as e:
            logger.error("Error generando reporte de calidad: %s", str(e))
            return {"error": str(e), "confidence_score": 0.0}

    # === MÉTODOS PRIVADOS DE EXTRACCIÓN ===

    def _extract_passing_features(self, stats: ProfessionalStats) -> Dict[str, float]:
        """Extrae features de passing."""
        features = {}

        if stats.accurate_passes_pct:
            features["passing_accuracy"] = self._normalize_percentage(
                stats.accurate_passes_pct, (60, 95)
            )

        if stats.passes_per_90:
            features["passing_volume"] = self._normalize_per_90(
                stats.passes_per_90, (20, 120)
            )

        return features

    def _extract_dueling_features(self, stats: ProfessionalStats) -> Dict[str, float]:
        """Extrae features de duelos."""
        features = {}

        if stats.duels_won_pct:
            features["dueling_success"] = self._normalize_percentage(
                stats.duels_won_pct, (40, 70)
            )

        if stats.defensive_duels_won_pct:
            features["defensive_dueling"] = self._normalize_percentage(
                stats.defensive_duels_won_pct, (45, 80)
            )

        return features

    def _extract_discipline_features(
        self, stats: ProfessionalStats
    ) -> Dict[str, float]:
        """Extrae features de disciplina."""
        features = {}

        if stats.yellow_cards and stats.matches_played:
            yellow_rate = stats.yellow_cards / stats.matches_played
            # Invertir: menos tarjetas = mejor score
            features["discipline_score"] = max(0, min(100, 100 - (yellow_rate * 100)))
        else:
            features["discipline_score"] = 90.0  # Default alto si no hay tarjetas

        return features

    def _extract_defensive_zone_features(
        self, stats: ProfessionalStats
    ) -> Dict[str, float]:
        """Extrae features de zona defensiva."""
        features = {}

        if stats.successful_defensive_actions_per_90:
            features["defensive_actions"] = self._normalize_per_90(
                stats.successful_defensive_actions_per_90, (3, 20)
            )

        if stats.interceptions_per_90:
            features["interceptions"] = self._normalize_per_90(
                stats.interceptions_per_90, (0.5, 10)
            )

        return features

    def _extract_midfield_zone_features(
        self, stats: ProfessionalStats
    ) -> Dict[str, float]:
        """Extrae features de zona de mediocampo."""
        features = {}

        if stats.progressive_passes_per_90:
            features["progressive_passing"] = self._normalize_per_90(
                stats.progressive_passes_per_90, (2, 25)
            )

        if stats.key_passes_per_90:
            features["key_passing"] = self._normalize_per_90(
                stats.key_passes_per_90, (0.2, 8)
            )

        if stats.ball_recoveries_per_90:
            features["ball_recoveries"] = self._normalize_per_90(
                stats.ball_recoveries_per_90, (3, 20)
            )

        return features

    def _extract_offensive_zone_features(
        self, stats: ProfessionalStats
    ) -> Dict[str, float]:
        """Extrae features de zona ofensiva."""
        features = {}

        if stats.goals_per_90:
            features["goal_scoring"] = self._normalize_per_90(
                stats.goals_per_90, (0, 2.0)
            )

        if stats.assists_per_90:
            features["assist_creation"] = self._normalize_per_90(
                stats.assists_per_90, (0, 1.5)
            )

        if stats.shots_on_target_pct:
            features["shooting_accuracy"] = self._normalize_percentage(
                stats.shots_on_target_pct, (25, 70)
            )

        return features

    # === MÉTODOS DE NORMALIZACIÓN ===

    def _normalize_feature_value(self, value: float, config: Dict[str, any]) -> float:
        """Normaliza un valor de feature según su configuración."""
        normalization_type = config.get("normalization", "standard")
        expected_range = config.get("expected_range", (0, 100))

        if normalization_type == "percentage":
            return self._normalize_percentage(value, expected_range)
        elif normalization_type == "per_90_scaled":
            return self._normalize_per_90(value, expected_range)
        elif normalization_type == "inverse_per_90":
            return self._normalize_inverse_per_90(value, expected_range)
        else:
            return self._normalize_standard(value, expected_range)

    def _normalize_percentage(
        self, value: float, range_tuple: Tuple[float, float]
    ) -> float:
        """Normaliza un valor porcentual a escala 0-100."""
        min_val, max_val = range_tuple
        normalized = ((value - min_val) / (max_val - min_val)) * 100
        return max(0, min(100, normalized))

    def _normalize_per_90(
        self, value: float, range_tuple: Tuple[float, float]
    ) -> float:
        """Normaliza un valor por-90-minutos a escala 0-100."""
        min_val, max_val = range_tuple
        normalized = ((value - min_val) / (max_val - min_val)) * 100
        return max(0, min(100, normalized))

    def _normalize_inverse_per_90(
        self, value: float, range_tuple: Tuple[float, float]
    ) -> float:
        """Normaliza inversamente (menor valor = mejor score)."""
        min_val, max_val = range_tuple
        if value <= min_val:
            return 100.0
        elif value >= max_val:
            return 0.0
        else:
            # Invertir la escala
            normalized = ((max_val - value) / (max_val - min_val)) * 100
            return max(0, min(100, normalized))

    def _normalize_standard(
        self, value: float, range_tuple: Tuple[float, float]
    ) -> float:
        """Normalización estándar lineal."""
        min_val, max_val = range_tuple
        normalized = ((value - min_val) / (max_val - min_val)) * 100
        return max(0, min(100, normalized))

    # === MÉTODOS DE UTILIDAD ===

    def _validate_minimum_data(self, stats: ProfessionalStats) -> bool:
        """Valida que existan datos mínimos para análisis."""
        if (
            not stats.matches_played
            or stats.matches_played < self.min_matches_threshold
        ):
            return False
        if not stats.minutes_played or stats.minutes_played < (
            self.min_matches_threshold * 45
        ):
            return False
        return True

    def _get_zone_weights_by_position(self, position: str) -> Dict[str, float]:
        """Obtiene pesos por zona según la posición."""
        weights = {
            "GK": {"defensive": 0.8, "midfield": 0.2, "offensive": 0.0},
            "CB": {"defensive": 0.7, "midfield": 0.3, "offensive": 0.0},
            "FB": {"defensive": 0.5, "midfield": 0.3, "offensive": 0.2},
            "DMF": {"defensive": 0.4, "midfield": 0.6, "offensive": 0.0},
            "CMF": {"defensive": 0.2, "midfield": 0.8, "offensive": 0.0},
            "AMF": {"defensive": 0.1, "midfield": 0.5, "offensive": 0.4},
            "W": {"defensive": 0.0, "midfield": 0.3, "offensive": 0.7},
            "CF": {"defensive": 0.0, "midfield": 0.2, "offensive": 0.8},
        }
        return weights.get(position, weights["CMF"])

    def _calculate_weighted_average(
        self, features: Dict[str, float], weights_config: Dict
    ) -> float:
        """Calcula promedio ponderado de features."""
        if not features:
            return 50.0

        total_weighted = 0.0
        total_weight = 0.0

        # Iterar sobre configuración de pesos
        for category, category_features in weights_config.items():
            if isinstance(category_features, dict):
                for feature_name, feature_config in category_features.items():
                    if feature_name in features:
                        weight = feature_config.get("weight", 1.0)
                        total_weighted += features[feature_name] * weight
                        total_weight += weight

        return total_weighted / total_weight if total_weight > 0 else 50.0

    def _calculate_zone_composite_score(
        self, features: Dict[str, float], zone_weights: Dict[str, float]
    ) -> float:
        """Calcula score compuesto por zonas."""
        zone_scores = {}

        # Agrupar features por zona
        for feature_name, score in features.items():
            if feature_name.startswith("defensive_"):
                zone_scores.setdefault("defensive", []).append(score)
            elif feature_name.startswith("midfield_"):
                zone_scores.setdefault("midfield", []).append(score)
            elif feature_name.startswith("offensive_"):
                zone_scores.setdefault("offensive", []).append(score)

        # Calcular promedio por zona y aplicar pesos
        composite_score = 0.0
        for zone, weight in zone_weights.items():
            if zone in zone_scores and zone_scores[zone]:
                zone_avg = sum(zone_scores[zone]) / len(zone_scores[zone])
                composite_score += zone_avg * weight

        return composite_score

    def _evaluate_tier_coverage(
        self, stats: ProfessionalStats, tier_config: Dict
    ) -> Dict[str, any]:
        """Evalúa cobertura de features para un tier."""
        total_features = 0
        available_features = 0

        for category, features in tier_config.items():
            for feature_name in features.keys():
                total_features += 1
                if (
                    hasattr(stats, feature_name)
                    and getattr(stats, feature_name) is not None
                ):
                    available_features += 1

        coverage_pct = (
            (available_features / total_features) * 100 if total_features > 0 else 0
        )

        return {
            "total_features": total_features,
            "available_features": available_features,
            "coverage_percentage": coverage_pct,
        }

    def _evaluate_zone_coverage(
        self, stats: ProfessionalStats, position: str
    ) -> Dict[str, any]:
        """Evalúa cobertura de features por zona."""
        zone_weights = self._get_zone_weights_by_position(position)
        return {
            "position": position,
            "zone_weights": zone_weights,
            "coverage_percentage": 75.0,  # Placeholder - calcular basado en disponibilidad
        }

    def _evaluate_position_coverage(
        self, stats: ProfessionalStats, position: str
    ) -> Dict[str, any]:
        """Evalúa cobertura de features específicos."""
        if position not in self.position_features:
            return {"coverage_percentage": 0.0, "reason": "Position not supported"}

        position_config = self.position_features[position]
        total = len(position_config)
        available = sum(
            1
            for feature_name in position_config.keys()
            if hasattr(stats, feature_name) and getattr(stats, feature_name) is not None
        )

        return {
            "total_features": total,
            "available_features": available,
            "coverage_percentage": (available / total) * 100 if total > 0 else 0,
        }

    def _calculate_confidence_score(
        self, stats: ProfessionalStats, coverage_reports: List[Dict]
    ) -> float:
        """Calcula score de confianza global."""
        # Factor base: número de partidos
        matches_factor = (
            min(1.0, stats.matches_played / 10.0) if stats.matches_played else 0
        )

        # Factor de cobertura promedio
        coverage_scores = [
            report.get("coverage_percentage", 0) / 100 for report in coverage_reports
        ]
        coverage_factor = (
            sum(coverage_scores) / len(coverage_scores) if coverage_scores else 0
        )

        # Score de confianza combinado
        confidence = (matches_factor * 0.4 + coverage_factor * 0.6) * 100

        return max(0, min(100, confidence))

    def _evaluate_data_quality(self, stats: ProfessionalStats) -> Dict[str, any]:
        """Evalúa calidad general de los datos."""
        quality_indicators = {
            "has_sufficient_matches": stats.matches_played
            >= self.min_matches_threshold,
            "has_sufficient_minutes": stats.minutes_played
            >= (self.min_matches_threshold * 45),
            "has_basic_stats": all(
                [
                    stats.accurate_passes_pct is not None,
                    stats.duels_won_pct is not None,
                ]
            ),
            "data_recency": "recent",  # Placeholder
        }

        quality_score = (
            sum(
                1
                for indicator in quality_indicators.values()
                if indicator is True or indicator == "recent"
            )
            / len(quality_indicators)
            * 100
        )

        return {
            "indicators": quality_indicators,
            "quality_score": quality_score,
        }

    # === VALORES POR DEFECTO ===

    def _get_default_universal_features(self) -> Dict[str, float]:
        """Devuelve features universales por defecto."""
        return {
            "passing_accuracy": 50.0,
            "passing_volume": 50.0,
            "dueling_success": 50.0,
            "defensive_dueling": 50.0,
            "discipline_score": 75.0,
            "universal_composite_score": 55.0,
        }

    def _get_default_zone_features(self) -> Dict[str, float]:
        """Devuelve features por zona por defecto."""
        return {
            "zone_composite_score": 50.0,
        }

    def _get_default_position_features(self) -> Dict[str, float]:
        """Devuelve features específicos por defecto."""
        return {
            "position_specific_composite_score": 50.0,
        }

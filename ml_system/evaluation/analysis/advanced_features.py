#!/usr/bin/env python3
"""
Advanced Feature Engineering - Sistema Avanzado de Ingeniería de Características
Fase 2: Feature Engineering por Tiers para Player Development Index (PDI)

Este módulo implementa técnicas avanzadas de feature engineering siguiendo metodología
CRISP-DM con rigor académico. Construye sobre el baseline validado (MAE 0.774)
para mejorar la predicción del PDI mediante características sofisticadas.

Características implementadas:
1. Normalización específica por posición
2. Métricas ajustadas por edad
3. Clasificación por tiers de rendimiento
4. Estadísticas rolling multi-temporada
5. Features de interacción position × age × tier

Objetivo académico: Superar baseline con MAE < 0.700

Autor: Proyecto Fin de Máster - Python Aplicado al Deporte
Fecha: Agosto 2025
Dataset: Liga Tailandesa (2,359 registros, 5 temporadas)
"""

import logging
import warnings
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import RobustScaler, StandardScaler

# Configurar logging
logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


class PositionalNormalizationEngine:
    """
    Motor de normalización específica por posición.

    Implementa benchmarks posicionales para fair comparison entre jugadores
    de diferentes posiciones basado en percentiles históricos de Liga Tailandesa.
    """

    def __init__(self):
        """Inicializa motor con benchmarks posicionales."""
        self.position_benchmarks = {}
        self.position_weights = {}
        self.scaler = RobustScaler()
        self._initialize_position_mappings()

    def _initialize_position_mappings(self):
        """Inicializa mapeos y pesos específicos por posición."""

        # Mapeo de posiciones principales (Thai League format)
        self.position_groups = {
            "GK": ["GK", "Goalkeeper"],
            "CB": ["CB", "Centre-Back", "Sweeper"],
            "FB": ["LB", "RB", "Left-Back", "Right-Back", "WB", "LWB", "RWB"],
            "DMF": ["DMF", "Defensive Midfield", "DM"],
            "CMF": ["CMF", "Central Midfield", "CM", "Box-to-Box Midfield"],
            "AMF": ["AMF", "Attacking Midfield", "AM", "Playmaker"],
            "W": ["LW", "RW", "Left Winger", "Right Winger", "Wing"],
            "CF": ["CF", "Centre-Forward", "ST", "Striker"],
        }

        # Pesos específicos por posición para diferentes métricas
        self.position_metric_weights = {
            "GK": {
                "defensive": 0.7,
                "possession": 0.2,
                "attacking": 0.0,
                "goalkeeping": 1.0,
            },
            "CB": {
                "defensive": 0.6,
                "possession": 0.25,
                "attacking": 0.1,
                "physical": 0.05,
            },
            "FB": {
                "defensive": 0.45,
                "possession": 0.25,
                "attacking": 0.25,
                "physical": 0.05,
            },
            "DMF": {
                "defensive": 0.4,
                "possession": 0.4,
                "attacking": 0.15,
                "physical": 0.05,
            },
            "CMF": {
                "defensive": 0.25,
                "possession": 0.45,
                "attacking": 0.25,
                "physical": 0.05,
            },
            "AMF": {
                "defensive": 0.1,
                "possession": 0.4,
                "attacking": 0.45,
                "creativity": 0.05,
            },
            "W": {"defensive": 0.1, "possession": 0.3, "attacking": 0.55, "pace": 0.05},
            "CF": {
                "defensive": 0.05,
                "possession": 0.2,
                "attacking": 0.7,
                "finishing": 0.05,
            },
        }

    def normalize_player_by_position(
        self, player_data: pd.Series, position: str, historical_data: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Normaliza métricas de jugador específicas por su posición.

        Args:
            player_data: Serie con datos del jugador
            position: Posición del jugador
            historical_data: DataFrame con datos históricos para benchmarks

        Returns:
            Dict con métricas normalizadas por posición
        """
        try:
            # Mapear posición a grupo principal
            main_position = self._map_to_main_position(position)
            if not main_position:
                main_position = "CMF"  # Default fallback

            # Filtrar datos históricos por posición
            position_data = historical_data[
                historical_data["Primary position"].isin(
                    self.position_groups.get(main_position, [position])
                )
            ]

            if len(position_data) < 10:
                logger.warning(f"Pocos datos históricos para posición {main_position}")
                position_data = historical_data  # Fallback a todos los datos

            # Calcular percentiles por posición para métricas clave
            metrics_to_normalize = [
                "Pass accuracy, %",
                "Duels won, %",
                "Successful dribbles, %",
                "Minutes played",
                "Matches played",
                "Age",
            ]

            normalized_features = {}

            for metric in metrics_to_normalize:
                if metric in player_data.index and metric in position_data.columns:
                    player_value = player_data[metric]

                    if (
                        pd.notna(player_value)
                        and len(position_data[metric].dropna()) > 0
                    ):
                        # Calcular percentil del jugador dentro de su posición
                        position_values = position_data[metric].dropna()
                        percentile = stats.percentileofscore(
                            position_values, player_value
                        )

                        # Normalizar a escala 0-100
                        normalized_features[f"{metric}_position_percentile"] = (
                            percentile
                        )

                        # Z-score dentro de la posición
                        if len(position_values) > 1:
                            z_score = (
                                player_value - position_values.mean()
                            ) / position_values.std()
                            normalized_features[f"{metric}_position_zscore"] = min(
                                max(z_score, -3), 3
                            )

                        # Feature de élite (top 10% en su posición)
                        threshold_90 = np.percentile(position_values, 90)
                        normalized_features[f"{metric}_position_elite"] = (
                            1.0 if player_value >= threshold_90 else 0.0
                        )

            # Agregar features de caracterización posicional
            normalized_features["position_defensive_weight"] = (
                self.position_metric_weights.get(main_position, {}).get(
                    "defensive", 0.3
                )
            )

            normalized_features["position_attacking_weight"] = (
                self.position_metric_weights.get(main_position, {}).get(
                    "attacking", 0.3
                )
            )

            normalized_features["position_possession_weight"] = (
                self.position_metric_weights.get(main_position, {}).get(
                    "possession", 0.4
                )
            )

            return normalized_features

        except Exception as e:
            logger.error(f"Error normalizando por posición: {e}")
            return {}

    def _map_to_main_position(self, position: str) -> Optional[str]:
        """Mapea posición específica a grupo principal."""
        if pd.isna(position):
            return None

        position = str(position).strip()
        for main_pos, variations in self.position_groups.items():
            if position in variations or any(
                var.lower() in position.lower() for var in variations
            ):
                return main_pos

        return None


class AgeAdjustmentEngine:
    """
    Motor de ajuste por edad para métricas de rendimiento.

    Implementa curvas de rendimiento esperado por edad específicas para cada posición,
    permitiendo comparación fair entre jugadores de diferentes edades.
    """

    def __init__(self):
        """Inicializa motor con curvas edad-rendimiento."""
        self.age_curves = {}
        self.age_benchmarks = {}
        self._initialize_age_models()

    def _initialize_age_models(self):
        """Inicializa modelos de rendimiento por edad."""

        # Curvas de rendimiento por edad (basadas en literatura deportiva)
        self.position_age_curves = {
            "GK": {"peak_age": 30, "decline_rate": 0.02},  # Porteros maduran tarde
            "CB": {
                "peak_age": 28,
                "decline_rate": 0.025,
            },  # Defensas centrales experiencia
            "FB": {
                "peak_age": 26,
                "decline_rate": 0.03,
            },  # Laterales requieren velocidad
            "DMF": {
                "peak_age": 28,
                "decline_rate": 0.02,
            },  # Mediocentros defensivos maduran
            "CMF": {"peak_age": 27, "decline_rate": 0.025},  # Mediocentros balance
            "AMF": {"peak_age": 26, "decline_rate": 0.025},  # Creativos peak temprano
            "W": {"peak_age": 25, "decline_rate": 0.04},  # Extremos dependen velocidad
            "CF": {
                "peak_age": 27,
                "decline_rate": 0.03,
            },  # Delanteros experiencia+físico
        }

    def calculate_age_adjusted_metrics(
        self, player_data: pd.Series, historical_data: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Calcula métricas ajustadas por edad para el jugador.

        Args:
            player_data: Serie con datos del jugador
            historical_data: DataFrame histórico para benchmarks por edad

        Returns:
            Dict con métricas ajustadas por edad
        """
        try:
            age = player_data.get("Age")
            position = player_data.get("Primary position", "CMF")

            if pd.isna(age) or age < 16 or age > 45:
                logger.warning(f"Edad inválida: {age}")
                return {}

            age = int(age)

            # Mapear posición
            main_position = self._get_main_position(position)

            # Obtener curva de edad para la posición
            age_curve = self.position_age_curves.get(
                main_position, {"peak_age": 27, "decline_rate": 0.03}
            )

            # Calcular factor de ajuste por edad
            peak_age = age_curve["peak_age"]
            decline_rate = age_curve["decline_rate"]

            if age <= peak_age:
                # Antes del peak: crecimiento progresivo
                age_factor = 0.7 + (0.3 * (age - 18) / (peak_age - 18))
            else:
                # Después del peak: decline
                years_past_peak = age - peak_age
                age_factor = 1.0 - (decline_rate * years_past_peak)

            age_factor = max(0.4, min(1.0, age_factor))  # Bounded entre 0.4 y 1.0

            adjusted_features = {}

            # Métricas a ajustar por edad
            metrics_to_adjust = [
                "Pass accuracy, %",
                "Duels won, %",
                "Successful dribbles, %",
            ]

            for metric in metrics_to_adjust:
                if metric in player_data.index and pd.notna(player_data[metric]):
                    raw_value = player_data[metric]

                    # Calcular valor esperado para su edad
                    age_peers = historical_data[
                        (historical_data["Age"] >= age - 2)
                        & (historical_data["Age"] <= age + 2)
                    ]

                    if len(age_peers) > 10 and metric in age_peers.columns:
                        expected_value = age_peers[metric].mean()

                        if expected_value > 0:
                            # Ratio vs esperado para su edad
                            age_ratio = raw_value / expected_value
                            adjusted_features[f"{metric}_age_adjusted_ratio"] = (
                                age_ratio
                            )

                            # Performance vs peak teórico
                            theoretical_peak = raw_value / age_factor
                            adjusted_features[f"{metric}_theoretical_peak"] = (
                                theoretical_peak
                            )

                    # Features categóricas de edad
                    adjusted_features["age_category"] = self._categorize_age(age)
                    adjusted_features["years_to_peak"] = peak_age - age
                    adjusted_features["age_factor"] = age_factor
                    adjusted_features["is_prime_age"] = (
                        1.0 if abs(age - peak_age) <= 2 else 0.0
                    )

            return adjusted_features

        except Exception as e:
            logger.error(f"Error en ajuste por edad: {e}")
            return {}

    def _get_main_position(self, position: str) -> str:
        """Mapea posición a grupo principal para curva de edad."""
        if pd.isna(position):
            return "CMF"

        position_str = str(position).upper()

        # Mapeo simple
        if "GK" in position_str or "GOAL" in position_str:
            return "GK"
        elif "CB" in position_str or "CENTRE-BACK" in position_str:
            return "CB"
        elif any(x in position_str for x in ["LB", "RB", "WB", "BACK"]):
            return "FB"
        elif "DMF" in position_str or "DEFENSIVE MID" in position_str:
            return "DMF"
        elif any(x in position_str for x in ["AMF", "ATTACKING MID", "PLAYMAKER"]):
            return "AMF"
        elif any(x in position_str for x in ["WINGER", "WING", "LW", "RW"]):
            return "W"
        elif any(x in position_str for x in ["CF", "STRIKER", "FORWARD"]):
            return "CF"
        else:
            return "CMF"  # Default

    def _categorize_age(self, age: int) -> float:
        """Categoriza edad en escalas numéricas."""
        if age <= 21:
            return 1.0  # Young prospect
        elif age <= 25:
            return 2.0  # Developing
        elif age <= 29:
            return 3.0  # Prime
        elif age <= 33:
            return 4.0  # Experienced
        else:
            return 5.0  # Veteran


class PerformanceTierEngine:
    """
    Motor de clasificación por tiers de rendimiento.

    Clasifica jugadores en tiers basado en múltiples métricas de rendimiento
    y crea features específicas para cada tier.
    """

    def __init__(self):
        """Inicializa engine de tiers."""
        self.tier_thresholds = {}
        self.tier_features = {}

    def classify_performance_tier(
        self, player_data: pd.Series, historical_data: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Clasifica jugador en tier de rendimiento y genera features específicas.

        Args:
            player_data: Serie con datos del jugador
            historical_data: DataFrame histórico para benchmarks

        Returns:
            Dict con features de tier de rendimiento
        """
        try:
            # Métricas clave para clasificación de tier
            key_metrics = [
                "Minutes played",
                "Pass accuracy, %",
                "Duels won, %",
                "Successful dribbles, %",
                "Matches played",
            ]

            # Calcular score compuesto
            composite_score = 0
            valid_metrics = 0

            for metric in key_metrics:
                if metric in player_data.index and metric in historical_data.columns:
                    player_value = player_data[metric]

                    if pd.notna(player_value):
                        # Percentil en dataset histórico
                        all_values = historical_data[metric].dropna()
                        if len(all_values) > 0:
                            percentile = stats.percentileofscore(
                                all_values, player_value
                            )
                            composite_score += percentile
                            valid_metrics += 1

            if valid_metrics == 0:
                return {"performance_tier": 1.0, "tier_confidence": 0.0}

            # Score promedio
            avg_score = composite_score / valid_metrics

            # Clasificar en tiers
            if avg_score >= 90:
                tier = 5.0  # Elite
                tier_name = "Elite"
            elif avg_score >= 75:
                tier = 4.0  # High
                tier_name = "High"
            elif avg_score >= 50:
                tier = 3.0  # Medium
                tier_name = "Medium"
            elif avg_score >= 25:
                tier = 2.0  # Basic
                tier_name = "Basic"
            else:
                tier = 1.0  # Developing
                tier_name = "Developing"

            # Generar features específicas del tier
            tier_features = {
                "performance_tier": tier,
                "tier_composite_score": avg_score,
                "tier_confidence": min(valid_metrics / len(key_metrics), 1.0),
                # Features binarias por tier
                "is_elite_tier": 1.0 if tier == 5.0 else 0.0,
                "is_high_tier": 1.0 if tier == 4.0 else 0.0,
                "is_medium_tier": 1.0 if tier == 3.0 else 0.0,
                "is_basic_tier": 1.0 if tier == 2.0 else 0.0,
                "is_developing_tier": 1.0 if tier == 1.0 else 0.0,
                # Features de interacción con minutos
                "tier_minutes_interaction": tier
                * player_data.get("Minutes played", 0)
                / 1000,
                # Stability score (basado en consistencia de métricas)
                "tier_stability": self._calculate_stability_score(
                    player_data, key_metrics
                ),
            }

            logger.info(
                f"Jugador clasificado en tier {tier_name} (score: {avg_score:.1f})"
            )

            return tier_features

        except Exception as e:
            logger.error(f"Error en clasificación de tier: {e}")
            return {"performance_tier": 3.0, "tier_confidence": 0.0}

    def _calculate_stability_score(
        self, player_data: pd.Series, metrics: List[str]
    ) -> float:
        """Calcula score de estabilidad basado en variabilidad de métricas."""
        try:
            values = []
            for metric in metrics:
                if metric in player_data.index and pd.notna(player_data[metric]):
                    values.append(float(player_data[metric]))

            if len(values) < 3:
                return 0.5  # Neutral cuando hay pocos datos

            # Calcular coeficiente de variación (normalizado)
            cv = np.std(values) / np.mean(values) if np.mean(values) > 0 else 1.0

            # Convertir a stability score (menor CV = mayor estabilidad)
            stability = max(0.0, min(1.0, 1.0 - cv))

            return stability

        except Exception:
            return 0.5


class LegacyFeatureWeights:
    """
    Sistema de pesos de features migrado desde controllers/ml/feature_engineer.py.

    Implementa los 3 tiers de features con pesos científicos específicos:
    - Universal (40%): Aplicables a todas las posiciones
    - Zone (35%): Agrupadas por zonas del campo
    - Position-Specific (25%): Específicas por posición
    """

    def __init__(self):
        """Inicializa los pesos de features desde legacy controller."""
        self.min_matches_threshold = 3
        self.confidence_threshold = 0.7
        self._initialize_legacy_tiers()
        logger.info("🔧 LegacyFeatureWeights inicializado con tiers científicos")

    def _initialize_legacy_tiers(self):
        """Inicializa definición exacta de features por tiers desde legacy."""

        # TIER 1: Universal Features (40% peso PDI) - MIGRADO EXACTO
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

        # TIER 2: Zone Features (35% peso PDI) - MIGRADO EXACTO
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

        # TIER 3: Position-Specific Features (25% peso PDI) - MIGRADO EXACTO
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

    def get_feature_weights_for_position(self, position: str) -> Dict[str, Dict]:
        """Obtiene pesos de features específicos para una posición."""
        normalized_position = self._normalize_position_for_weights(position)
        return {
            "universal": self.universal_features,
            "zone": self.zone_features,
            "position_specific": self.position_features.get(normalized_position, {}),
        }

    def _normalize_position_for_weights(self, position: str) -> str:
        """Normaliza posición para obtener pesos."""
        if not position or pd.isna(position):
            return "CMF"

        pos = str(position).upper()

        # Mapeo exacto del legacy
        if "GK" in pos or "GOAL" in pos:
            return "GK"
        elif "CB" in pos or "CENTRE-BACK" in pos:
            return "CB"
        elif any(x in pos for x in ["LB", "RB", "WB", "BACK"]):
            return "FB"
        elif "DMF" in pos or "DEFENSIVE MID" in pos:
            return "DMF"
        elif any(x in pos for x in ["AMF", "ATTACKING MID"]):
            return "AMF"
        elif any(x in pos for x in ["WINGER", "WING", "LW", "RW"]):
            return "W"
        elif any(x in pos for x in ["CF", "STRIKER", "FORWARD"]):
            return "CF"
        else:
            return "CMF"  # Default


class AdvancedFeatureEngineer:
    """
    Motor principal de Feature Engineering Avanzado con Legacy Integration.

    Combina los engines especializados existentes con los pesos científicos
    del legacy feature_engineer.py para generar conjunto completo de features.
    """

    def __init__(self):
        """Inicializa el motor de feature engineering avanzado con legacy integration."""
        self.positional_engine = PositionalNormalizationEngine()
        self.age_engine = AgeAdjustmentEngine()
        self.tier_engine = PerformanceTierEngine()
        self.legacy_weights = LegacyFeatureWeights()  # NUEVO: Legacy weights

        self.feature_cache = {}
        self.scaler = StandardScaler()

        logger.info("🚀 AdvancedFeatureEngineer inicializado con Legacy Integration")

    def engineer_advanced_features(
        self, df: pd.DataFrame, target_mode: str = "current"
    ) -> pd.DataFrame:
        """
        Genera conjunto completo de features avanzadas sin data leakage.

        Args:
            df: DataFrame con datos de jugadores (formato Thai League CSV)
            target_mode: 'current' para PDI actual, 'future' para predicción temporal

        Returns:
            DataFrame con features avanzadas añadidas
        """
        try:
            logger.info(
                f"🔧 Feature engineering avanzado ({target_mode} mode) para {len(df)} registros"
            )

            df_enhanced = df.copy()

            # 1. Features posicionales (sin circularidad)
            logger.info("📊 Generando features posicionales...")
            positional_features = self._generate_positional_features_v2(df_enhanced)

            # 2. Features temporales (si hay columna season)
            logger.info("⏱️ Generando features temporales...")
            temporal_features = self._generate_temporal_features_v2(
                df_enhanced, target_mode
            )

            # 3. Features de desarrollo de jugador
            logger.info("🎯 Generando features de desarrollo...")
            development_features = self._generate_development_features(df_enhanced)

            # 4. Features de interacción mejorados
            logger.info("🔗 Generando features de interacción mejorados...")
            interaction_features = self._generate_interaction_features_v2(df_enhanced)

            # 5. Features de consistencia y estabilidad
            logger.info("🎯 Generando features de consistencia...")
            consistency_features = self._generate_consistency_features(df_enhanced)

            # 6. Legacy Feature Weights optimizados
            logger.info("⚖️ Generando legacy feature weights optimizados...")
            legacy_features = self._generate_legacy_weighted_features_v2(df_enhanced)

            # Combinar todos los features
            all_features = [
                positional_features,
                temporal_features,
                development_features,
                interaction_features,
                consistency_features,
                legacy_features,
            ]

            for features_df in all_features:
                if features_df is not None and len(features_df) > 0:
                    df_enhanced = pd.concat([df_enhanced, features_df], axis=1)

            # Post-processing: eliminar features con alta correlación o bajo valor
            df_enhanced = self._post_process_features(df_enhanced, target_mode)

            logger.info(
                f"✅ Feature engineering completado: {len(df_enhanced.columns)} columnas totales"
            )

            return df_enhanced

        except Exception as e:
            logger.error(f"❌ Error en feature engineering avanzado: {e}")
            return df

    def _generate_positional_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Genera features de normalización posicional."""
        try:
            positional_data = []

            for idx, row in df.iterrows():
                position = row.get("Primary position", "CMF")
                pos_features = self.positional_engine.normalize_player_by_position(
                    row, position, df
                )
                positional_data.append(pos_features)

            return pd.DataFrame(positional_data, index=df.index)

        except Exception as e:
            logger.error(f"Error generando features posicionales: {e}")
            return pd.DataFrame()

    def _generate_positional_features_v2(self, df: pd.DataFrame) -> pd.DataFrame:
        """Features posicionales mejorados sin circularidad."""
        try:
            positional_data = []

            for idx, row in df.iterrows():
                features = {}
                position = row.get("Primary position", "CMF")

                # Normalizar posición a grupos principales
                pos_normalized = self.legacy_weights._normalize_position_for_weights(
                    position
                )
                features["position_normalized"] = pos_normalized

                # One-hot encoding para posiciones principales
                for pos in ["GK", "CB", "FB", "DMF", "CMF", "AMF", "W", "CF"]:
                    features[f"pos_is_{pos}"] = 1.0 if pos_normalized == pos else 0.0

                # Métricas específicas por posición (sin usar PDI)
                age = row.get("Age", 25)
                minutes = row.get("Minutes played", 0)

                # Factor de experiencia por posición
                if pos_normalized in ["GK", "CB"]:
                    experience_factor = min(1.0, (age - 18) / 12)  # Mejoran con edad
                else:
                    experience_factor = max(0.3, 1.0 - ((age - 26) * 0.02))  # Peak ~26

                features["position_experience_factor"] = experience_factor

                # Factor de actividad por posición
                if minutes > 0:
                    if pos_normalized in ["W", "CF"]:
                        activity_factor = min(
                            1.0, minutes / 2000
                        )  # Requieren más descanso
                    else:
                        activity_factor = min(1.0, minutes / 2500)
                else:
                    activity_factor = 0.0

                features["position_activity_factor"] = activity_factor

                positional_data.append(features)

            return pd.DataFrame(positional_data, index=df.index)

        except Exception as e:
            logger.error(f"Error en features posicionales v2: {e}")
            return pd.DataFrame()

    def _generate_temporal_features_v2(
        self, df: pd.DataFrame, target_mode: str
    ) -> pd.DataFrame:
        """Features temporales mejorados sin data leakage."""
        try:
            if "season" not in df.columns:
                return pd.DataFrame(index=df.index)

            temporal_data = []

            # Convertir seasons a años numéricos
            def season_to_year(season_str):
                try:
                    return int(str(season_str).split("-")[0])
                except:
                    return None

            df_with_year = df.copy()
            df_with_year["season_year"] = df_with_year["season"].apply(season_to_year)

            for idx, row in df_with_year.iterrows():
                features = {}

                current_year = row.get("season_year")
                if pd.isna(current_year):
                    features["career_stage"] = 0.5
                    features["season_experience"] = 0.0
                    features["temporal_trend"] = 0.0
                    temporal_data.append(features)
                    continue

                # Etapa de carrera basada en edad
                age = row.get("Age", 25)
                if age < 22:
                    features["career_stage"] = 0.2  # Joven/desarrollo
                elif age < 27:
                    features["career_stage"] = 0.8  # Prime
                elif age < 32:
                    features["career_stage"] = 1.0  # Experiencia
                else:
                    features["career_stage"] = 0.6  # Veterano

                temporal_data.append(features)

            return pd.DataFrame(temporal_data, index=df.index)

        except Exception as e:
            logger.error(f"Error en features temporales v2: {e}")
            return pd.DataFrame()

    def _generate_age_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Genera features de ajuste por edad."""
        try:
            age_data = []

            for idx, row in df.iterrows():
                age_features = self.age_engine.calculate_age_adjusted_metrics(row, df)
                age_data.append(age_features)

            return pd.DataFrame(age_data, index=df.index)

        except Exception as e:
            logger.error(f"Error generando features de edad: {e}")
            return pd.DataFrame()

    def _generate_tier_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Genera features de tier de rendimiento."""
        try:
            tier_data = []

            for idx, row in df.iterrows():
                tier_features = self.tier_engine.classify_performance_tier(row, df)
                tier_data.append(tier_features)

            return pd.DataFrame(tier_data, index=df.index)

        except Exception as e:
            logger.error(f"Error generando features de tier: {e}")
            return pd.DataFrame()

    def _generate_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Genera features de interacción entre variables."""
        try:
            interaction_data = []

            for idx, row in df.iterrows():
                interactions = {}

                # Interactions básicas
                age = row.get("Age", 25)
                minutes = row.get("Minutes played", 0)
                pass_acc = row.get("Pass accuracy, %", 0)
                duels_won = row.get("Duels won, %", 0)

                if pd.notna(age) and pd.notna(minutes):
                    interactions["age_minutes_interaction"] = age * (minutes / 1000)

                if pd.notna(pass_acc) and pd.notna(duels_won):
                    interactions["pass_duels_interaction"] = (
                        pass_acc * duels_won / 10000
                    )

                if pd.notna(age) and pd.notna(pass_acc):
                    interactions["age_passing_interaction"] = age * pass_acc / 100

                # Feature de experiencia (edad * minutos jugados)
                if pd.notna(age) and pd.notna(minutes) and minutes > 0:
                    interactions["experience_factor"] = (age - 18) * np.log1p(minutes)

                interaction_data.append(interactions)

            return pd.DataFrame(interaction_data, index=df.index)

        except Exception as e:
            logger.error(f"Error generando features de interacción: {e}")
            return pd.DataFrame()

    def _generate_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Genera features rolling si hay múltiples temporadas."""
        try:
            if "season" not in df.columns:
                logger.info("No hay columna 'season', omitiendo features rolling")
                return pd.DataFrame(index=df.index)

            rolling_data = []

            # Agrupar por jugador (si hay columna Player)
            if "Player" in df.columns:
                for player in df["Player"].unique():
                    player_data = df[df["Player"] == player].sort_values("season")

                    if len(player_data) > 1:
                        # Calcular métricas rolling
                        for idx in player_data.index:
                            current_season_idx = list(player_data.index).index(idx)

                            rolling_features = {}

                            if current_season_idx > 0:
                                # Features de temporadas anteriores
                                prev_data = player_data.iloc[:current_season_idx]

                                # Trend de minutos jugados
                                if "Minutes played" in prev_data.columns:
                                    minutes_trend = (
                                        prev_data["Minutes played"].pct_change().mean()
                                    )
                                    rolling_features["minutes_trend"] = (
                                        minutes_trend
                                        if pd.notna(minutes_trend)
                                        else 0.0
                                    )

                                # Consistencia de pass accuracy
                                if "Pass accuracy, %" in prev_data.columns:
                                    pass_std = prev_data["Pass accuracy, %"].std()
                                    rolling_features["pass_consistency"] = (
                                        1 / (1 + pass_std)
                                        if pd.notna(pass_std)
                                        else 0.5
                                    )
                            else:
                                rolling_features["minutes_trend"] = 0.0
                                rolling_features["pass_consistency"] = 0.5

                            rolling_data.append((idx, rolling_features))

            # Crear DataFrame con índices correctos
            if rolling_data:
                rolling_dict = {idx: features for idx, features in rolling_data}
                return pd.DataFrame.from_dict(rolling_dict, orient="index")
            else:
                return pd.DataFrame(index=df.index)

        except Exception as e:
            logger.error(f"Error generando features rolling: {e}")
            return pd.DataFrame(index=df.index)

    def _generate_legacy_weighted_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Genera features con pesos del sistema legacy."""
        try:
            legacy_data = []

            for idx, row in df.iterrows():
                position = row.get("Primary position", "CMF")
                legacy_features = {}

                # Obtener pesos específicos por posición
                position_weights = self.legacy_weights.get_feature_weights_for_position(
                    position
                )

                # Universal Features Score
                universal_score = self._calculate_universal_score(
                    row, position_weights["universal"]
                )
                legacy_features["legacy_universal_score"] = universal_score

                # Zone Features Score
                zone_score = self._calculate_zone_score(row, position_weights["zone"])
                legacy_features["legacy_zone_score"] = zone_score

                # Position-Specific Features Score
                position_score = self._calculate_position_specific_score(
                    row, position_weights["position_specific"]
                )
                legacy_features["legacy_position_score"] = position_score

                # Composite Legacy Score (usando pesos PDI: 40% + 35% + 25%)
                composite_score = (
                    universal_score * 0.40 + zone_score * 0.35 + position_score * 0.25
                )
                legacy_features["legacy_composite_score"] = composite_score

                # Feature weights metadata
                legacy_features["legacy_position_normalized"] = (
                    self.legacy_weights._normalize_position_for_weights(position)
                )
                legacy_features["legacy_universal_weight"] = 0.40
                legacy_features["legacy_zone_weight"] = 0.35
                legacy_features["legacy_position_weight"] = 0.25

                legacy_data.append(legacy_features)

            return pd.DataFrame(legacy_data, index=df.index)

        except Exception as e:
            logger.error(f"Error generando legacy weighted features: {e}")
            return pd.DataFrame()

    def _calculate_universal_score(self, row: pd.Series, weights: Dict) -> float:
        """Calcula score universal usando pesos legacy."""
        try:
            total_score = 0.0
            total_weight = 0.0

            # Mapear campos del dataset a features legacy
            field_mapping = {
                "accurate_passes_pct": "Pass accuracy, %",
                "duels_won_pct": "Duels won, %",
                "passes_per_90": "Passes per 90",  # Si existe
            }

            for category, features in weights.items():
                for feature_name, config in features.items():
                    mapped_field = field_mapping.get(feature_name)
                    if mapped_field and mapped_field in row.index:
                        value = row[mapped_field]
                        if pd.notna(value) and value > 0:
                            weight = config.get("weight", 0.1)
                            normalized_value = self._normalize_feature_value(
                                value, config.get("expected_range", (0, 100))
                            )
                            total_score += normalized_value * weight
                            total_weight += weight

            return total_score / total_weight if total_weight > 0 else 50.0

        except Exception:
            return 50.0

    def _calculate_zone_score(self, row: pd.Series, weights: Dict) -> float:
        """Calcula score por zona usando pesos legacy."""
        try:
            zone_scores = {}

            # Defensive zone
            def_score = self._calculate_zone_subscore(
                row, weights.get("defensive", {}), "defensive"
            )
            zone_scores["defensive"] = def_score

            # Midfield zone
            mid_score = self._calculate_zone_subscore(
                row, weights.get("midfield", {}), "midfield"
            )
            zone_scores["midfield"] = mid_score

            # Offensive zone
            off_score = self._calculate_zone_subscore(
                row, weights.get("offensive", {}), "offensive"
            )
            zone_scores["offensive"] = off_score

            # Promedio ponderado (cada zona tiene peso igual por ahora)
            avg_score = (
                sum(zone_scores.values()) / len(zone_scores) if zone_scores else 50.0
            )
            return avg_score

        except Exception:
            return 50.0

    def _calculate_zone_subscore(
        self, row: pd.Series, zone_weights: Dict, zone_type: str
    ) -> float:
        """Calcula subscore para una zona específica."""
        try:
            total_score = 0.0
            total_weight = 0.0

            # Mapeo básico de campos
            field_mappings = {
                "goals_per_90": "Goals per 90",
                "assists_per_90": "Assists per 90",
                "shots_on_target_pct": "Shots on target, %",
                "progressive_passes_per_90": "Progressive passes per 90",
                "key_passes_per_90": "Key passes per 90",
            }

            for feature_name, config in zone_weights.items():
                mapped_field = field_mappings.get(feature_name, feature_name)
                if mapped_field in row.index:
                    value = row[mapped_field]
                    if pd.notna(value) and value >= 0:
                        weight = config.get("weight", 0.1)
                        normalized_value = self._normalize_feature_value(
                            value, config.get("expected_range", (0, 10))
                        )
                        total_score += normalized_value * weight
                        total_weight += weight

            return total_score / total_weight if total_weight > 0 else 50.0

        except Exception:
            return 50.0

    def _calculate_position_specific_score(
        self, row: pd.Series, weights: Dict
    ) -> float:
        """Calcula score específico por posición."""
        try:
            if not weights:
                return 50.0  # Default si no hay pesos específicos

            total_score = 0.0
            total_weight = 0.0

            for feature_name, config in weights.items():
                # Mapeo básico - expandir según necesidades
                field_mappings = {
                    "aerial_duels_won_pct": "Aerial duels won, %",
                    "successful_dribbles_pct": "Successful dribbles, %",
                    "goals_per_90": "Goals per 90",
                    "assists_per_90": "Assists per 90",
                }

                mapped_field = field_mappings.get(feature_name, feature_name)
                if mapped_field in row.index:
                    value = row[mapped_field]
                    if pd.notna(value) and value >= 0:
                        weight = config.get("weight", 0.1)
                        normalized_value = self._normalize_feature_value(
                            value, config.get("expected_range", (0, 100))
                        )
                        total_score += normalized_value * weight
                        total_weight += weight

            return total_score / total_weight if total_weight > 0 else 50.0

        except Exception:
            return 50.0

    def _normalize_feature_value(
        self, value: float, expected_range: Tuple[float, float]
    ) -> float:
        """Normaliza valor de feature a escala 0-100."""
        try:
            min_val, max_val = expected_range
            if max_val <= min_val:
                return 50.0

            # Normalizar a 0-100
            normalized = ((value - min_val) / (max_val - min_val)) * 100
            return max(0.0, min(100.0, normalized))

        except Exception:
            return 50.0


def create_advanced_feature_pipeline():
    """
    Factory function para crear pipeline de feature engineering avanzado.

    Returns:
        AdvancedFeatureEngineer configurado y listo para uso
    """
    logger.info("🏭 Creando pipeline de feature engineering avanzado")

    engineer = AdvancedFeatureEngineer()

    logger.info("✅ Pipeline de feature engineering avanzado creado exitosamente")

    return engineer


# Funciones de utilidad para testing y validación
def validate_advanced_features(
    df_original: pd.DataFrame, df_enhanced: pd.DataFrame
) -> Dict[str, Any]:
    """
    Valida que el feature engineering se haya ejecutado correctamente.

    Args:
        df_original: DataFrame original
        df_enhanced: DataFrame con features avanzadas

    Returns:
        Dict con estadísticas de validación
    """
    try:
        validation_results = {
            "original_features": len(df_original.columns),
            "enhanced_features": len(df_enhanced.columns),
            "new_features_added": len(df_enhanced.columns) - len(df_original.columns),
            "records_processed": len(df_enhanced),
            "feature_completeness": {},
        }

        # Verificar completitud de nuevos features
        new_columns = [
            col for col in df_enhanced.columns if col not in df_original.columns
        ]

        for col in new_columns:
            completeness = (df_enhanced[col].notna().sum() / len(df_enhanced)) * 100
            validation_results["feature_completeness"][col] = completeness

        # Estadísticas generales
        avg_completeness = np.mean(
            list(validation_results["feature_completeness"].values())
        )
        validation_results["avg_feature_completeness"] = avg_completeness

        # Status
        if avg_completeness > 80:
            validation_results["status"] = "Excelente"
        elif avg_completeness > 60:
            validation_results["status"] = "Bueno"
        else:
            validation_results["status"] = "Requiere revisión"

        return validation_results

    except Exception as e:
        logger.error(f"Error validando features avanzadas: {e}")
        return {"status": "Error", "error": str(e)}

    def _generate_development_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Features de potencial y desarrollo de jugador."""
        try:
            development_data = []

            for idx, row in df.iterrows():
                features = {}

                age = row.get("Age", 25)
                minutes = row.get("Minutes played", 0)
                matches = row.get("Matches played", 0)

                # Potencial de desarrollo basado en edad
                if age < 21:
                    features["development_potential"] = 1.0
                elif age < 25:
                    features["development_potential"] = 0.8
                elif age < 28:
                    features["development_potential"] = 0.5
                else:
                    features["development_potential"] = 0.2

                # Regularidad y estabilidad
                if matches > 0 and minutes > 0:
                    avg_minutes_per_match = minutes / matches
                    features["playing_regularity"] = min(
                        1.0, avg_minutes_per_match / 90
                    )
                    features["match_involvement"] = min(1.0, matches / 35)
                else:
                    features["playing_regularity"] = 0.0
                    features["match_involvement"] = 0.0

                development_data.append(features)

            return pd.DataFrame(development_data, index=df.index)

        except Exception as e:
            logger.error(f"Error en features de desarrollo: {e}")
            return pd.DataFrame()

    def _generate_interaction_features_v2(self, df: pd.DataFrame) -> pd.DataFrame:
        """Features de interacción mejorados."""
        try:
            interaction_data = []

            for idx, row in df.iterrows():
                features = {}

                age = row.get("Age", 25)
                minutes = row.get("Minutes played", 0)
                pass_acc = row.get("Pass accuracy, %", 0)
                duels_won = row.get("Duels won, %", 0)

                features["age_experience_combo"] = (
                    age * (minutes / 2500) if minutes > 0 else 0
                )
                features["efficiency_volume_combo"] = (
                    (pass_acc / 100) * (minutes / 2500)
                    if pass_acc > 0 and minutes > 0
                    else 0
                )
                features["technical_physical_balance"] = (
                    (pass_acc + duels_won) / 200 if pass_acc > 0 or duels_won > 0 else 0
                )

                interaction_data.append(features)

            return pd.DataFrame(interaction_data, index=df.index)

        except Exception as e:
            logger.error(f"Error en features de interacción v2: {e}")
            return pd.DataFrame()

    def _generate_consistency_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Features de consistencia y estabilidad."""
        try:
            consistency_data = []

            for idx, row in df.iterrows():
                features = {}

                yellow_cards = row.get("Yellow cards", 0)
                red_cards = row.get("Red cards", 0)
                matches = max(1, row.get("Matches played", 1))

                discipline_score = max(
                    0, 1.0 - ((yellow_cards + red_cards * 3) / matches)
                )
                features["discipline_consistency"] = discipline_score

                minutes = row.get("Minutes played", 0)
                if matches > 0:
                    availability_score = (matches / 35) * (minutes / (matches * 90))
                    features["availability_score"] = min(1.0, availability_score)
                else:
                    features["availability_score"] = 0.0

                consistency_data.append(features)

            return pd.DataFrame(consistency_data, index=df.index)

        except Exception as e:
            logger.error(f"Error en features de consistencia: {e}")
            return pd.DataFrame()

    def _generate_legacy_weighted_features_v2(self, df: pd.DataFrame) -> pd.DataFrame:
        """Legacy features optimizados."""
        try:
            base_features = self._generate_legacy_weighted_features(df)

            if base_features.empty:
                return pd.DataFrame()

            enhanced_data = []

            for idx, row in df.iterrows():
                enhanced = (
                    base_features.loc[idx].to_dict()
                    if idx in base_features.index
                    else {}
                )

                universal_score = enhanced.get("legacy_universal_score", 50)
                zone_score = enhanced.get("legacy_zone_score", 50)
                position_score = enhanced.get("legacy_position_score", 50)

                optimized_score = (
                    universal_score * 0.35 + zone_score * 0.40 + position_score * 0.25
                )
                enhanced["legacy_optimized_score"] = optimized_score

                enhanced_data.append(enhanced)

            return pd.DataFrame(enhanced_data, index=df.index)

        except Exception as e:
            logger.error(f"Error en legacy features v2: {e}")
            return pd.DataFrame()

    def _post_process_features(
        self, df: pd.DataFrame, target_mode: str
    ) -> pd.DataFrame:
        """Post-procesa features eliminando correlaciones altas."""
        try:
            # Identificar features numéricos nuevos
            original_cols = [
                "Player",
                "Age",
                "Minutes played",
                "Goals per 90",
                "Pass accuracy, %",
            ]
            numeric_features = df.select_dtypes(include=[np.number]).columns
            new_features = [
                col
                for col in numeric_features
                if col not in original_cols and col in df.columns
            ]

            if len(new_features) == 0:
                return df

            # Eliminar features con varianza muy baja
            low_variance_features = []
            for feature in new_features:
                if feature in df.columns and df[feature].var() < 1e-6:
                    low_variance_features.append(feature)

            if low_variance_features:
                logger.info(
                    f"Eliminando {len(low_variance_features)} features con baja varianza"
                )
                df = df.drop(columns=low_variance_features)

            return df

        except Exception as e:
            logger.error(f"Error en post-processing: {e}")
            return df


if __name__ == "__main__":
    # Test básico del sistema
    print("🧪 Testing AdvancedFeatureEngineer...")

    # Datos de prueba
    test_data = pd.DataFrame(
        {
            "Player": ["Test Player 1", "Test Player 2"],
            "Age": [25, 28],
            "Primary position": ["CMF", "CF"],
            "Minutes played": [2000, 1500],
            "Pass accuracy, %": [85, 78],
            "Duels won, %": [65, 70],
            "Matches played": [25, 20],
            "season": ["2023", "2023"],
        }
    )

    engineer = create_advanced_feature_pipeline()
    enhanced_data = engineer.engineer_advanced_features(test_data)

    print(f"✅ Test completado: {len(enhanced_data.columns)} features generadas")
    print(f"🔧 Nuevos features: {len(enhanced_data.columns) - len(test_data.columns)}")

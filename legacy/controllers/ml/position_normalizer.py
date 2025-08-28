"""
PositionNormalizer - Módulo de normalización posicional para fair comparison.

Este módulo implementa la normalización de métricas ML por posición,
permitiendo comparaciones justas entre jugadores de diferentes posiciones.
Utiliza percentiles históricos y benchmarks de la Thai League para crear
scores normalizados que respeten las características específicas de cada posición.
"""

import logging
from typing import Dict, List

from sqlalchemy.orm import Session

from controllers.db import get_db_session
# Import directo para evitar circular imports
from models.ml_metrics_model import MLMetrics

# Configurar logging
logger = logging.getLogger(__name__)


class PositionNormalizer:
    """
    Normalizador posicional para métricas ML.

    Responsabilidades:
    - Cálculo de percentiles por posición
    - Normalización basada en benchmarks posicionales
    - Generación de rankings justos
    - Mantenimiento de estadísticas históricas por posición
    """

    def __init__(self):
        """Inicializa el normalizador con configuraciones por defecto."""
        self.min_sample_size = 10  # Mínimo de jugadores por posición para normalización
        self.percentile_windows = [5, 10, 25, 50, 75, 90, 95]  # Percentiles a calcular
        self.seasons_for_benchmark = ["2023-24", "2024-25"]  # Temporadas para benchmark

        # Cache para evitar recálculos frecuentes
        self._position_benchmarks_cache = {}
        self._cache_timestamp = {}

        logger.info("PositionNormalizer inicializado")

    def normalize_player_metrics(
        self, player_metrics: Dict[str, float], position: str, season: str = "2024-25"
    ) -> Dict[str, float]:
        """
        Normaliza métricas de un jugador según su posición.

        Args:
            player_metrics: Métricas del jugador a normalizar
            position: Posición del jugador
            season: Temporada para benchmarking

        Returns:
            dict: Métricas normalizadas con percentiles posicionales
        """
        try:
            # Obtener benchmarks posicionales
            position_benchmarks = self._get_position_benchmarks(position, season)

            if not position_benchmarks:
                logger.warning(
                    "No se encontraron benchmarks para posición %s", position
                )
                return self._apply_default_normalization(player_metrics)

            normalized_metrics = {}

            # Normalizar cada métrica
            for metric_name, value in player_metrics.items():
                if metric_name in position_benchmarks:
                    benchmark_data = position_benchmarks[metric_name]

                    # Calcular percentil del jugador
                    percentile = self._calculate_percentile(value, benchmark_data)

                    # Normalizar a escala 0-100 basado en percentil
                    normalized_score = self._percentile_to_normalized_score(
                        percentile, metric_name
                    )

                    normalized_metrics[f"{metric_name}_normalized"] = normalized_score
                    normalized_metrics[f"{metric_name}_percentile"] = percentile
                else:
                    # Si no hay benchmark, mantener valor original
                    normalized_metrics[f"{metric_name}_normalized"] = value
                    normalized_metrics[f"{metric_name}_percentile"] = 50.0

            # Calcular métricas agregadas normalizadas
            normalized_metrics.update(
                self._calculate_normalized_aggregates(normalized_metrics, position)
            )

            logger.debug(
                "Métricas normalizadas para posición %s: %d métricas",
                position,
                len(normalized_metrics),
            )

            return normalized_metrics

        except Exception as e:
            logger.error("Error normalizando métricas: %s", str(e))
            return self._apply_default_normalization(player_metrics)

    def calculate_position_rankings(
        self, position: str, season: str = "2024-25", limit: int = 100
    ) -> List[Dict[str, any]]:
        """
        Calcula rankings normalizados por posición.

        Args:
            position: Posición para ranking
            season: Temporada a analizar
            limit: Número máximo de jugadores en ranking

        Returns:
            list: Lista de jugadores ordenados por PDI normalizado
        """
        try:
            with get_db_session() as session:
                # Obtener todos los jugadores de la posición
                position_players = (
                    session.query(MLMetrics)
                    .filter_by(position_analyzed=position, season=season)
                    .filter(MLMetrics.pdi_overall.isnot(None))
                    .all()
                )

                if len(position_players) < 2:
                    logger.warning(
                        "Insuficientes jugadores para ranking posición %s", position
                    )
                    return []

                # Normalizar métricas de todos los jugadores
                normalized_players = []
                for player_metrics in position_players:
                    raw_metrics = {
                        "pdi_overall": player_metrics.pdi_overall,
                        "pdi_universal": player_metrics.pdi_universal,
                        "pdi_zone": player_metrics.pdi_zone,
                        "pdi_position_specific": player_metrics.pdi_position_specific,
                        "technical_proficiency": player_metrics.technical_proficiency,
                        "tactical_intelligence": player_metrics.tactical_intelligence,
                        "physical_performance": player_metrics.physical_performance,
                        "consistency_index": player_metrics.consistency_index,
                    }

                    # Remover valores None
                    raw_metrics = {
                        k: v for k, v in raw_metrics.items() if v is not None
                    }

                    normalized = self.normalize_player_metrics(
                        raw_metrics, position, season
                    )

                    normalized_players.append(
                        {
                            "player_id": player_metrics.player_id,
                            "raw_pdi": player_metrics.pdi_overall,
                            "normalized_pdi": normalized.get(
                                "pdi_overall_normalized", 0
                            ),
                            "position_percentile": normalized.get(
                                "pdi_overall_percentile", 50
                            ),
                            "metrics_breakdown": normalized,
                        }
                    )

                # Ordenar por PDI normalizado
                sorted_players = sorted(
                    normalized_players, key=lambda x: x["normalized_pdi"], reverse=True
                )

                # Asignar rankings
                rankings = []
                for idx, player_data in enumerate(sorted_players[:limit]):
                    rankings.append(
                        {
                            **player_data,
                            "position_rank": idx + 1,
                            "position": position,
                            "season": season,
                        }
                    )

                logger.info(
                    "Rankings calculados para posición %s: %d jugadores",
                    position,
                    len(rankings),
                )

                return rankings

        except Exception as e:
            logger.error("Error calculando rankings por posición: %s", str(e))
            return []

    def generate_position_benchmark_report(
        self, position: str, season: str = "2024-25"
    ) -> Dict[str, any]:
        """
        Genera reporte de benchmarks por posición.

        Args:
            position: Posición a analizar
            season: Temporada para análisis

        Returns:
            dict: Reporte completo de benchmarks posicionales
        """
        try:
            benchmarks = self._get_position_benchmarks(position, season)

            if not benchmarks:
                return {
                    "position": position,
                    "season": season,
                    "error": "No se encontraron benchmarks",
                    "sample_size": 0,
                }

            # Construir reporte
            report = {
                "position": position,
                "season": season,
                "sample_size": benchmarks.get("_meta", {}).get("sample_size", 0),
                "last_updated": benchmarks.get("_meta", {}).get("last_updated"),
                "benchmarks": {},
            }

            # Procesar cada métrica
            for metric_name, benchmark_data in benchmarks.items():
                if metric_name.startswith("_"):  # Skip metadata
                    continue

                if isinstance(benchmark_data, dict) and "percentiles" in benchmark_data:
                    report["benchmarks"][metric_name] = {
                        "mean": benchmark_data.get("mean", 0),
                        "std": benchmark_data.get("std", 0),
                        "median": benchmark_data["percentiles"].get(50, 0),
                        "p25": benchmark_data["percentiles"].get(25, 0),
                        "p75": benchmark_data["percentiles"].get(75, 0),
                        "p90": benchmark_data["percentiles"].get(90, 0),
                        "p95": benchmark_data["percentiles"].get(95, 0),
                        "sample_count": benchmark_data.get("sample_count", 0),
                    }

            return report

        except Exception as e:
            logger.error("Error generando reporte de benchmarks: %s", str(e))
            return {"error": str(e)}

    def update_position_benchmarks(self, seasons: List[str] = None) -> Dict[str, int]:
        """
        Actualiza benchmarks posicionales desde la base de datos.

        Args:
            seasons: Lista de temporadas para incluir (default: últimas 2)

        Returns:
            dict: Resumen de benchmarks actualizados por posición
        """
        try:
            if not seasons:
                seasons = self.seasons_for_benchmark

            updated_positions = {}

            with get_db_session() as session:
                # Obtener todas las posiciones con datos
                positions_with_data = (
                    session.query(MLMetrics.position_analyzed)
                    .filter(MLMetrics.season.in_(seasons))
                    .filter(MLMetrics.position_analyzed.isnot(None))
                    .distinct()
                    .all()
                )

                for (position,) in positions_with_data:
                    if position:
                        benchmark_count = self._calculate_position_benchmarks(
                            session, position, seasons
                        )
                        updated_positions[position] = benchmark_count

                logger.info(
                    "Benchmarks actualizados para %d posiciones", len(updated_positions)
                )

            return updated_positions

        except Exception as e:
            logger.error("Error actualizando benchmarks: %s", str(e))
            return {}

    # === MÉTODOS PRIVADOS ===

    def _get_position_benchmarks(self, position: str, season: str) -> Dict[str, any]:
        """
        Obtiene benchmarks para una posición específica.

        Utiliza cache para evitar recálculos frecuentes.
        """
        cache_key = f"{position}_{season}"

        # Verificar cache
        if (
            cache_key in self._position_benchmarks_cache
            and cache_key in self._cache_timestamp
        ):
            # Cache válido por 1 hora
            cache_age = (
                __import__("datetime").datetime.now() - self._cache_timestamp[cache_key]
            ).seconds
            if cache_age < 3600:
                return self._position_benchmarks_cache[cache_key]

        # Recalcular benchmarks
        with get_db_session() as session:
            benchmarks = self._calculate_position_benchmarks(
                session, position, [season]
            )

            # Actualizar cache
            self._position_benchmarks_cache[cache_key] = benchmarks
            self._cache_timestamp[cache_key] = __import__("datetime").datetime.now()

            return benchmarks

    def _calculate_position_benchmarks(
        self, session: Session, position: str, seasons: List[str]
    ) -> Dict[str, any]:
        """Calcula benchmarks estadísticos para una posición."""
        try:
            # Obtener todas las métricas para la posición
            position_metrics = (
                session.query(MLMetrics)
                .filter_by(position_analyzed=position)
                .filter(MLMetrics.season.in_(seasons))
                .all()
            )

            if len(position_metrics) < self.min_sample_size:
                logger.warning(
                    "Insuficientes datos para benchmarks posición %s: %d samples",
                    position,
                    len(position_metrics),
                )
                return {}

            benchmarks = {
                "_meta": {
                    "sample_size": len(position_metrics),
                    "last_updated": __import__("datetime").datetime.now().isoformat(),
                    "seasons": seasons,
                }
            }

            # Métricas a procesar
            metrics_to_process = [
                "pdi_overall",
                "pdi_universal",
                "pdi_zone",
                "pdi_position_specific",
                "technical_proficiency",
                "tactical_intelligence",
                "physical_performance",
                "consistency_index",
            ]

            for metric_name in metrics_to_process:
                values = [
                    getattr(m, metric_name)
                    for m in position_metrics
                    if getattr(m, metric_name) is not None
                ]

                if len(values) >= 5:  # Mínimo para estadísticas significativas
                    benchmarks[metric_name] = self._calculate_metric_benchmarks(values)

            return benchmarks

        except Exception as e:
            logger.error(
                "Error calculando benchmarks para posición %s: %s", position, str(e)
            )
            return {}

    def _calculate_metric_benchmarks(self, values: List[float]) -> Dict[str, any]:
        """Calcula estadísticas de benchmark para una métrica."""
        import numpy as np

        try:
            np_values = np.array(values)

            # Estadísticas básicas
            mean_val = float(np.mean(np_values))
            std_val = float(np.std(np_values))
            median_val = float(np.median(np_values))

            # Percentiles
            percentiles = {}
            for p in self.percentile_windows:
                percentiles[p] = float(np.percentile(np_values, p))

            return {
                "mean": mean_val,
                "std": std_val,
                "median": median_val,
                "percentiles": percentiles,
                "sample_count": len(values),
                "min": float(np.min(np_values)),
                "max": float(np.max(np_values)),
            }

        except Exception as e:
            logger.error("Error calculando estadísticas de métrica: %s", str(e))
            return {
                "mean": 50.0,
                "std": 15.0,
                "median": 50.0,
                "percentiles": {p: 50.0 for p in self.percentile_windows},
                "sample_count": len(values),
            }

    def _calculate_percentile(
        self, value: float, benchmark_data: Dict[str, any]
    ) -> float:
        """Calcula el percentil de un valor basado en benchmarks."""
        try:
            percentiles = benchmark_data.get("percentiles", {})

            # Buscar percentil más cercano
            if not percentiles:
                return 50.0  # Default si no hay datos

            # Interpolación entre percentiles
            sorted_percentiles = sorted(percentiles.items())

            # Si está por debajo del mínimo
            if value <= sorted_percentiles[0][1]:
                return sorted_percentiles[0][0]

            # Si está por encima del máximo
            if value >= sorted_percentiles[-1][1]:
                return sorted_percentiles[-1][0]

            # Interpolación lineal entre percentiles
            for i in range(len(sorted_percentiles) - 1):
                p1, v1 = sorted_percentiles[i]
                p2, v2 = sorted_percentiles[i + 1]

                if v1 <= value <= v2:
                    if v2 == v1:
                        return p1

                    # Interpolación lineal
                    ratio = (value - v1) / (v2 - v1)
                    interpolated_percentile = p1 + (p2 - p1) * ratio
                    return interpolated_percentile

            return 50.0  # Fallback

        except Exception as e:
            logger.error("Error calculando percentil: %s", str(e))
            return 50.0

    def _percentile_to_normalized_score(
        self, percentile: float, metric_name: str
    ) -> float:
        """
        Convierte percentil a score normalizado (0-100).

        Aplica curvas de transformación específicas según el tipo de métrica.
        """
        try:
            # Para la mayoría de métricas, percentil directo
            if metric_name.endswith("_pct") or "accuracy" in metric_name.lower():
                # Métricas porcentuales: transformación lineal suavizada
                return min(100, max(0, percentile * 1.1))

            elif "consistency" in metric_name.lower():
                # Consistencia: curva logarítmica (valorar más la consistencia alta)
                import math

                normalized = 100 * (1 - math.exp(-percentile / 30))
                return min(100, max(0, normalized))

            elif any(
                x in metric_name.lower() for x in ["goals", "assists", "key_passes"]
            ):
                # Métricas ofensivas: curva exponencial (valorar excepcionalidad)
                if percentile >= 90:
                    return 85 + (percentile - 90) * 1.5  # Boost para top 10%
                elif percentile >= 75:
                    return 70 + (percentile - 75) * 1.0
                else:
                    return percentile * 0.93

            else:
                # Transformación estándar: ligero boost a percentiles altos
                if percentile >= 80:
                    return percentile * 1.05
                else:
                    return percentile

        except Exception as e:
            logger.error("Error normalizando percentil: %s", str(e))
            return percentile

    def _calculate_normalized_aggregates(
        self, normalized_metrics: Dict[str, float], position: str
    ) -> Dict[str, float]:
        """Calcula métricas agregadas normalizadas."""
        try:
            aggregates = {}

            # PDI Overall normalizado (promedio ponderado de componentes)
            pdi_components = [
                ("pdi_universal_normalized", 0.40),
                ("pdi_zone_normalized", 0.35),
                ("pdi_position_specific_normalized", 0.25),
            ]

            pdi_total = 0.0
            pdi_weight_total = 0.0

            for component_name, weight in pdi_components:
                if component_name in normalized_metrics:
                    pdi_total += normalized_metrics[component_name] * weight
                    pdi_weight_total += weight

            if pdi_weight_total > 0:
                aggregates["pdi_overall_normalized"] = pdi_total / pdi_weight_total

            # Score de desarrollo general
            development_metrics = [
                "technical_proficiency_normalized",
                "tactical_intelligence_normalized",
                "physical_performance_normalized",
                "consistency_index_normalized",
            ]

            available_dev_scores = [
                normalized_metrics[m]
                for m in development_metrics
                if m in normalized_metrics
            ]

            if available_dev_scores:
                aggregates["development_score_normalized"] = sum(
                    available_dev_scores
                ) / len(available_dev_scores)

            # Score posicional específico (más peso a métricas relevantes por posición)
            position_weights = self._get_position_specific_weights(position)
            weighted_score = 0.0
            total_weight = 0.0

            for metric, weight in position_weights.items():
                normalized_metric = f"{metric}_normalized"
                if normalized_metric in normalized_metrics:
                    weighted_score += normalized_metrics[normalized_metric] * weight
                    total_weight += weight

            if total_weight > 0:
                aggregates["position_weighted_score"] = weighted_score / total_weight

            return aggregates

        except Exception as e:
            logger.error("Error calculando agregados normalizados: %s", str(e))
            return {}

    def _get_position_specific_weights(self, position: str) -> Dict[str, float]:
        """Obtiene pesos específicos por posición para agregados."""
        weights = {
            "GK": {
                "technical_proficiency": 0.20,
                "tactical_intelligence": 0.25,
                "physical_performance": 0.30,
                "consistency_index": 0.25,
            },
            "CB": {
                "technical_proficiency": 0.25,
                "tactical_intelligence": 0.35,
                "physical_performance": 0.25,
                "consistency_index": 0.15,
            },
            "FB": {
                "technical_proficiency": 0.30,
                "tactical_intelligence": 0.25,
                "physical_performance": 0.30,
                "consistency_index": 0.15,
            },
            "DMF": {
                "technical_proficiency": 0.25,
                "tactical_intelligence": 0.40,
                "physical_performance": 0.20,
                "consistency_index": 0.15,
            },
            "CMF": {
                "technical_proficiency": 0.35,
                "tactical_intelligence": 0.35,
                "physical_performance": 0.15,
                "consistency_index": 0.15,
            },
            "AMF": {
                "technical_proficiency": 0.40,
                "tactical_intelligence": 0.30,
                "physical_performance": 0.15,
                "consistency_index": 0.15,
            },
            "W": {
                "technical_proficiency": 0.40,
                "tactical_intelligence": 0.20,
                "physical_performance": 0.25,
                "consistency_index": 0.15,
            },
            "CF": {
                "technical_proficiency": 0.35,
                "tactical_intelligence": 0.25,
                "physical_performance": 0.25,
                "consistency_index": 0.15,
            },
        }

        return weights.get(position, weights["CMF"])  # Default CMF

    def _apply_default_normalization(
        self, player_metrics: Dict[str, float]
    ) -> Dict[str, float]:
        """Aplica normalización por defecto cuando no hay benchmarks."""
        normalized = {}

        for metric_name, value in player_metrics.items():
            normalized[f"{metric_name}_normalized"] = value  # Sin transformación
            normalized[f"{metric_name}_percentile"] = 50.0  # Percentil neutral

        return normalized

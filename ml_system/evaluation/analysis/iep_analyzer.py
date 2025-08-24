"""
IEP Analyzer - Interface para análisis de Índice Eficiencia Posicional (IEP).

Interface unificada entre el IEPCalculator y la UI para análisis de eficiencia
posicional usando clustering no supervisado. Proporciona métodos consistentes
con PlayerAnalyzer para integración limpia.

Responsabilidades:
- Interface limpia para UI consumption
- Gestión de outputs estructurados (results/reports/logs)
- Caching y optimización de consultas
- Integración con sistema de logging académico

Autor: Proyecto Fin de Máster - Python Aplicado al Deporte
Fecha: Agosto 2025
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ml_system.evaluation.metrics.iep_calculator import IEPCalculator

logger = logging.getLogger(__name__)


class IEPAnalyzer:
    """
    Analizador de Índice Eficiencia Posicional (IEP) - Interface para UI.

    Proporciona interface consistente con PlayerAnalyzer para análisis
    de eficiencia posicional usando clustering no supervisado.

    Arquitectura paralela a PlayerAnalyzer:
    - Métodos similares para consistencia UI
    - Output management estructurado
    - Caching inteligente para performance
    - Logging académico detallado
    """

    def __init__(self, output_base_path: Optional[str] = None):
        """
        Inicializa el analizador IEP.

        Args:
            output_base_path: Ruta base para outputs (opcional)
        """
        # Inicializar calculadora IEP
        self.iep_calculator = IEPCalculator()

        # Configurar paths para outputs estructurados
        if output_base_path:
            self.base_path = Path(output_base_path)
        else:
            # Usar path relativo al ml_system
            current_file = Path(__file__).resolve()
            ml_system_root = current_file.parent.parent.parent
            self.base_path = ml_system_root / "outputs"

        # Crear estructura de directorios
        self.results_path = self.base_path / "results" / "iep_analysis"
        self.reports_path = self.base_path / "reports" / "iep_reports"
        self.logs_path = self.base_path / "logs"

        # Asegurar que existen los directorios
        for path in [self.results_path, self.reports_path, self.logs_path]:
            path.mkdir(parents=True, exist_ok=True)

        # Cache para optimizar consultas
        self._cluster_cache = {}
        self._last_cache_update = {}

        logger.info(f"🎯 IEPAnalyzer inicializado - Outputs: {self.base_path}")

    def analyze_player_efficiency_tier(
        self, player_id: int, season: str = "2024-25", save_results: bool = False
    ) -> Dict:
        """
        Analiza tier de eficiencia para un jugador específico.
        Método paralelo a PlayerAnalyzer para consistencia UI.

        Args:
            player_id: ID del jugador
            season: Temporada a analizar
            save_results: Si guardar resultados en outputs

        Returns:
            Dict con análisis completo de eficiencia
        """
        try:
            logger.info(f"🎯 Analizando tier eficiencia jugador {player_id} ({season})")

            # Calcular IEP individual usando calculadora
            iep_results = self.iep_calculator.calculate_player_iep(player_id, season)

            if "error" in iep_results:
                logger.warning(f"Error en análisis IEP: {iep_results['error']}")
                return iep_results

            # Enriquecer con análisis adicional
            enhanced_results = self._enhance_player_analysis(iep_results)

            # Guardar resultados si se solicita
            if save_results:
                self._save_player_analysis(enhanced_results, player_id, season)

            logger.info(
                f"✅ Análisis IEP completado - Score: {enhanced_results['iep_metrics']['iep_score']}, Tier: {enhanced_results['iep_metrics']['cluster_tier']}"
            )

            return enhanced_results

        except Exception as e:
            logger.error(f"❌ Error analizando eficiencia jugador {player_id}: {e}")
            return {"error": str(e), "player_id": player_id, "season": season}

    def get_position_cluster_analysis(
        self,
        position: str,
        season: str = "2024-25",
        use_cache: bool = True,
        save_results: bool = False,
        current_player_id: int = None,
    ) -> Dict:
        """
        Obtiene análisis completo de clustering por posición.

        Args:
            position: Posición a analizar
            season: Temporada
            use_cache: Si usar cache para optimizar
            save_results: Si guardar resultados
            current_player_id: ID del jugador actual (siempre incluido independiente del min_matches)

        Returns:
            Dict con análisis completo de clustering posicional
        """
        try:
            logger.info(f"📊 Obteniendo análisis clustering {position} ({season})")
            if current_player_id:
                logger.info(
                    f"🎯 Jugador actual incluido forzosamente: {current_player_id}"
                )

            # Verificar cache (deshabilitado si hay current_player_id para evitar inconsistencias)
            cache_key = f"{position}_{season}"
            if use_cache and not current_player_id and cache_key in self._cluster_cache:
                cache_age = datetime.now() - self._last_cache_update.get(
                    cache_key, datetime.min
                )
                if cache_age.seconds < 3600:  # Cache válido por 1 hora
                    logger.info(f"✅ Usando cache para {cache_key}")
                    return self._cluster_cache[cache_key]

            # Calcular clustering usando calculadora
            cluster_results = self.iep_calculator.calculate_position_clusters(
                position, season, current_player_id=current_player_id
            )

            if "error" in cluster_results:
                logger.warning(
                    f"Error en clustering posicional: {cluster_results['error']}"
                )
                return cluster_results

            # Enriquecer con análisis adicional
            enhanced_results = self._enhance_cluster_analysis(cluster_results)

            # Actualizar cache
            if use_cache:
                self._cluster_cache[cache_key] = enhanced_results
                self._last_cache_update[cache_key] = datetime.now()

            # Guardar resultados
            if save_results:
                self._save_cluster_analysis(enhanced_results, position, season)

            logger.info(
                f"✅ Análisis clustering completado - {enhanced_results['data_quality']['total_players']} jugadores, {enhanced_results['clustering_results']['n_clusters']} clusters"
            )

            return enhanced_results

        except Exception as e:
            logger.error(f"❌ Error en análisis clustering {position}: {e}")
            return {"error": str(e), "position": position, "season": season}

    def generate_league_efficiency_benchmarks(
        self,
        season: str = "2024-25",
        positions: Optional[List[str]] = None,
        save_results: bool = False,
    ) -> Dict:
        """
        Genera benchmarks de eficiencia por liga y posición.

        Args:
            season: Temporada a analizar
            positions: Posiciones específicas (opcional)
            save_results: Si guardar benchmarks

        Returns:
            Dict con benchmarks completos por posición
        """
        try:
            logger.info(f"🏆 Generando benchmarks eficiencia liga ({season})")

            # Posiciones por defecto si no se especifican
            if not positions:
                positions = [
                    "GK",
                    "CB",
                    "LB",
                    "RB",
                    "DMF",
                    "CMF",
                    "AMF",
                    "LW",
                    "RW",
                    "CF",
                ]

            benchmarks = {
                "season": season,
                "analysis_date": datetime.now().isoformat(),
                "positions_analyzed": positions,
                "league_benchmarks": {},
                "summary_stats": {},
            }

            # Procesar cada posición
            all_players_count = 0
            all_clusters_count = 0

            for position in positions:
                logger.info(f"📊 Procesando benchmarks para {position}")

                # Obtener clustering de la posición
                cluster_analysis = self.get_position_cluster_analysis(
                    position, season, use_cache=True, save_results=False
                )

                if "error" in cluster_analysis:
                    logger.warning(
                        f"Saltando {position} - error: {cluster_analysis['error']}"
                    )
                    continue

                # Extraer benchmarks por posición
                position_benchmarks = {
                    "total_players": cluster_analysis["data_quality"]["total_players"],
                    "clusters": cluster_analysis["clustering_results"]["n_clusters"],
                    "silhouette_score": cluster_analysis["clustering_results"][
                        "silhouette_score"
                    ],
                    "variance_explained": cluster_analysis["pca_analysis"][
                        "total_variance_explained"
                    ],
                    "tier_distribution": {},
                    "performance_ranges": {},
                }

                # Calcular estadísticas por tier
                iep_scores_by_tier = {}
                for player in cluster_analysis["players_data"]:
                    tier = player["cluster_label"]
                    if tier not in iep_scores_by_tier:
                        iep_scores_by_tier[tier] = []
                    iep_scores_by_tier[tier].append(player["iep_score"])

                # Generar ranges por tier
                for tier, scores in iep_scores_by_tier.items():
                    position_benchmarks["tier_distribution"][tier] = len(scores)
                    position_benchmarks["performance_ranges"][tier] = {
                        "min": float(min(scores)),
                        "max": float(max(scores)),
                        "mean": float(sum(scores) / len(scores)),
                        "median": float(sorted(scores)[len(scores) // 2]),
                    }

                benchmarks["league_benchmarks"][position] = position_benchmarks
                all_players_count += position_benchmarks["total_players"]
                all_clusters_count += position_benchmarks["clusters"]

            # Estadísticas generales
            benchmarks["summary_stats"] = {
                "total_players_analyzed": all_players_count,
                "total_positions": len(
                    [p for p in positions if p in benchmarks["league_benchmarks"]]
                ),
                "average_clusters_per_position": round(
                    all_clusters_count / max(1, len(benchmarks["league_benchmarks"])), 1
                ),
                "analysis_quality": self._assess_benchmark_quality(benchmarks),
            }

            # Guardar benchmarks
            if save_results:
                self._save_league_benchmarks(benchmarks, season)

            logger.info(
                f"✅ Benchmarks generados - {all_players_count} jugadores, {len(benchmarks['league_benchmarks'])} posiciones"
            )

            return benchmarks

        except Exception as e:
            logger.error(f"❌ Error generando benchmarks liga: {e}")
            return {"error": str(e), "season": season}

    def get_available_positions_for_season(self, season: str = "2024-25") -> List[str]:
        """
        Obtiene posiciones disponibles con suficientes datos para análisis IEP.
        Método paralelo a PlayerAnalyzer para consistencia.

        Args:
            season: Temporada a verificar

        Returns:
            Lista de posiciones con datos suficientes
        """
        try:
            # Usar datos del calculadora para verificar posiciones
            available_positions = []

            # Posiciones estándar a verificar
            standard_positions = [
                "GK",
                "CB",
                "LB",
                "RB",
                "DMF",
                "CMF",
                "AMF",
                "LW",
                "RW",
                "CF",
            ]

            for position in standard_positions:
                # Verificar datos sin ejecutar clustering completo
                position_data = self.iep_calculator._get_position_data(
                    position, season, min_matches=5
                )

                if len(position_data) >= 10:  # Mínimo para clustering
                    available_positions.append(position)

            logger.info(
                f"📊 Posiciones disponibles para {season}: {available_positions}"
            )
            return available_positions

        except Exception as e:
            logger.error(f"Error obteniendo posiciones disponibles: {e}")
            return []

    # ============================================================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ============================================================================

    def _enhance_player_analysis(self, iep_results: Dict) -> Dict:
        """Enriquece análisis individual con contexto adicional."""
        try:
            enhanced = iep_results.copy()

            # Agregar interpretaciones textuales
            iep_score = enhanced["iep_metrics"]["iep_score"]
            cluster_tier = enhanced["iep_metrics"]["cluster_tier"]

            enhanced["interpretations"] = {
                "efficiency_level": self._interpret_iep_score(iep_score),
                "tier_meaning": self._interpret_cluster_tier(cluster_tier),
                "development_recommendations": self._generate_development_recommendations(
                    enhanced
                ),
            }

            # Agregar contexto temporal si es posible
            enhanced["temporal_context"] = {
                "current_season": enhanced.get("season"),
                "analysis_timestamp": datetime.now().isoformat(),
                "data_freshness": "current",  # TODO: Implementar análisis temporal
            }

            return enhanced

        except Exception as e:
            logger.error(f"Error enriqueciendo análisis jugador: {e}")
            return iep_results

    def _enhance_cluster_analysis(self, cluster_results: Dict) -> Dict:
        """Enriquece análisis de clustering con insights adicionales."""
        try:
            enhanced = cluster_results.copy()

            # Agregar insights de clustering
            enhanced["clustering_insights"] = {
                "quality_assessment": self._assess_cluster_quality(cluster_results),
                "tier_recommendations": self._generate_tier_insights(cluster_results),
                "position_characteristics": self._analyze_position_patterns(
                    cluster_results
                ),
            }

            # Agregar métricas comparativas
            enhanced["comparative_metrics"] = {
                "vs_other_positions": "pending",  # TODO: Implementar comparaciones
                "seasonal_stability": "pending",  # TODO: Implementar estabilidad temporal
                "league_context": "thai_league_professional",
            }

            return enhanced

        except Exception as e:
            logger.error(f"Error enriqueciendo análisis clustering: {e}")
            return cluster_results

    def _assess_benchmark_quality(self, benchmarks: Dict) -> str:
        """Evalúa calidad de benchmarks generados."""
        try:
            total_players = benchmarks["summary_stats"]["total_players_analyzed"]
            positions_count = benchmarks["summary_stats"]["total_positions"]

            if total_players > 1000 and positions_count >= 8:
                return "excellent"
            elif total_players > 500 and positions_count >= 6:
                return "good"
            elif total_players > 200 and positions_count >= 4:
                return "acceptable"
            else:
                return "limited"

        except:
            return "unknown"

    def _interpret_iep_score(self, score: float) -> str:
        """Interpreta score IEP en lenguaje descriptivo."""
        if score >= 80:
            return "Elite efficiency - Top tier performance"
        elif score >= 65:
            return "Strong efficiency - Above average performance"
        elif score >= 45:
            return "Average efficiency - Standard league performance"
        else:
            return "Development needed - Below average efficiency"

    def _interpret_cluster_tier(self, tier: str) -> str:
        """Interpreta tier de cluster en contexto deportivo."""
        interpretations = {
            "Elite Tier": "Jugador de élite en su posición - Referencias del mercado",
            "Strong Tier": "Jugador sólido - Rendimiento consistente por encima del promedio",
            "Average Tier": "Jugador estándar - Rendimiento típico de la liga",
            "Development Tier": "Jugador en desarrollo - Potencial de mejora significativo",
        }
        return interpretations.get(tier, "Tier de eficiencia específico de la posición")

    def _generate_development_recommendations(self, player_data: Dict) -> List[str]:
        """Genera recomendaciones de desarrollo basadas en IEP."""
        recommendations = []

        try:
            iep_score = player_data["iep_metrics"]["iep_score"]
            key_features = player_data.get("key_performance_features", {})

            # Recomendaciones basadas en score
            if iep_score < 50:
                recommendations.append(
                    "Focus on fundamental technical skills improvement"
                )
                recommendations.append("Increase training intensity and consistency")
            elif iep_score < 70:
                recommendations.append("Develop tactical awareness and positioning")
                recommendations.append(
                    "Work on consistency across different match scenarios"
                )
            else:
                recommendations.append("Maintain current performance level")
                recommendations.append("Focus on leadership and team coordination")

            # Recomendaciones específicas por features
            if key_features.get("pass_accuracy_pct", 0) < 80:
                recommendations.append(
                    "Improve passing accuracy through targeted drills"
                )

            if key_features.get("duels_won_pct", 0) < 50:
                recommendations.append(
                    "Strengthen physical preparation and duel technique"
                )

        except Exception as e:
            logger.debug(f"Error generando recomendaciones: {e}")
            recommendations.append(
                "Continuar desarrollo integral según plan de entrenamiento"
            )

        return recommendations

    def _assess_cluster_quality(self, cluster_data: Dict) -> str:
        """Evalúa calidad del clustering realizado."""
        try:
            silhouette = cluster_data["clustering_results"]["silhouette_score"]
            variance = cluster_data["pca_analysis"]["total_variance_explained"]
            players = cluster_data["data_quality"]["total_players"]

            if silhouette > 0.5 and variance > 0.7 and players > 50:
                return "excellent"
            elif silhouette > 0.3 and variance > 0.6 and players > 30:
                return "good"
            elif silhouette > 0.2 and variance > 0.5 and players > 15:
                return "acceptable"
            else:
                return "limited"

        except:
            return "unknown"

    def _generate_tier_insights(self, cluster_data: Dict) -> List[str]:
        """Genera insights sobre los tiers encontrados."""
        insights = []

        try:
            cluster_analysis = cluster_data.get("cluster_analysis", {})

            for cluster_id, analysis in cluster_analysis.items():
                tier_label = analysis["label"]
                percentage = analysis["percentage"]

                if percentage > 40:
                    insights.append(
                        f"{tier_label} dominates the position ({percentage}% of players)"
                    )
                elif percentage < 15:
                    insights.append(
                        f"{tier_label} is rare in this position ({percentage}% of players)"
                    )
                else:
                    insights.append(f"{tier_label} represents {percentage}% of players")

        except Exception as e:
            logger.debug(f"Error generando tier insights: {e}")

        return insights or ["Standard tier distribution for position"]

    def _analyze_position_patterns(self, cluster_data: Dict) -> List[str]:
        """Analiza patrones específicos de la posición."""
        patterns = []

        try:
            position = cluster_data.get("position", "Unknown")

            # Análisis básico por posición
            if position in ["CF", "RW", "LW"]:
                patterns.append(
                    "Offensive position - Goal and assist contribution critical"
                )
            elif position in ["CMF", "AMF", "DMF"]:
                patterns.append(
                    "Midfield position - Passing and creativity key factors"
                )
            elif position in ["CB", "LB", "RB"]:
                patterns.append(
                    "Defensive position - Tackling and clearances essential"
                )
            elif position == "GK":
                patterns.append(
                    "Goalkeeper position - Save rate and distribution crucial"
                )

            # Análisis de componentes PCA si disponible
            variance_ratio = cluster_data.get("pca_analysis", {}).get(
                "explained_variance_ratio", []
            )
            if len(variance_ratio) >= 2:
                if variance_ratio[0] > 0.5:
                    patterns.append("Strong primary performance component identified")
                if variance_ratio[1] > 0.2:
                    patterns.append("Secondary playing style component significant")

        except Exception as e:
            logger.debug(f"Error analizando patrones posición: {e}")

        return patterns or ["Standard positional performance patterns"]

    # ============================================================================
    # MÉTODOS DE GUARDADO Y PERSISTENCIA
    # ============================================================================

    def _save_player_analysis(self, analysis: Dict, player_id: int, season: str):
        """Guarda análisis individual en outputs estructurados."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"iep_player_analysis_{player_id}_{season}_{timestamp}.json"
            filepath = self.results_path / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Análisis jugador guardado: {filename}")

        except Exception as e:
            logger.error(f"Error guardando análisis jugador: {e}")

    def _save_cluster_analysis(self, analysis: Dict, position: str, season: str):
        """Guarda análisis de clustering en outputs estructurados."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"iep_clusters_{position}_{season}_{timestamp}.json"
            filepath = self.results_path / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Análisis clustering guardado: {filename}")

        except Exception as e:
            logger.error(f"Error guardando análisis clustering: {e}")

    def _save_league_benchmarks(self, benchmarks: Dict, season: str):
        """Guarda benchmarks de liga en outputs estructurados."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Guardar JSON detallado
            json_filename = f"iep_league_benchmarks_{season}_{timestamp}.json"
            json_filepath = self.results_path / json_filename

            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(benchmarks, f, indent=2, ensure_ascii=False)

            # Guardar CSV resumen
            csv_filename = f"iep_benchmarks_summary_{season}_{timestamp}.csv"
            csv_filepath = self.results_path / csv_filename

            self._export_benchmarks_csv(benchmarks, csv_filepath)

            logger.info(
                f"💾 Benchmarks liga guardados: {json_filename}, {csv_filename}"
            )

        except Exception as e:
            logger.error(f"Error guardando benchmarks liga: {e}")

    def _export_benchmarks_csv(self, benchmarks: Dict, filepath: Path):
        """Exporta benchmarks a formato CSV para análisis externo."""
        try:
            import csv

            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)

                # Header
                writer.writerow(
                    [
                        "Position",
                        "Total_Players",
                        "Clusters",
                        "Silhouette_Score",
                        "Variance_Explained",
                        "Elite_Count",
                        "Elite_Avg_Score",
                        "Strong_Count",
                        "Strong_Avg_Score",
                        "Average_Count",
                        "Average_Avg_Score",
                    ]
                )

                # Data rows
                for position, data in benchmarks["league_benchmarks"].items():
                    row = [
                        position,
                        data["total_players"],
                        data["clusters"],
                        data["silhouette_score"],
                    ]
                    row.append(round(data["variance_explained"], 3))

                    # Add tier data if available
                    tiers = ["Elite Tier", "Strong Tier", "Average Tier"]
                    for tier in tiers:
                        count = data["tier_distribution"].get(tier, 0)
                        avg_score = (
                            data["performance_ranges"].get(tier, {}).get("mean", 0)
                        )
                        row.extend([count, round(avg_score, 1)])

                    writer.writerow(row)

        except Exception as e:
            logger.error(f"Error exportando CSV benchmarks: {e}")


# ============================================================================
# LOGGING Y CONFIGURACIÓN
# ============================================================================

logger.info(
    "🎯 Módulo IEPAnalyzer cargado - Interface para análisis de eficiencia posicional"
)

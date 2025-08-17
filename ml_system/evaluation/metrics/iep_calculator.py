"""
IEP Calculator - Índice Eficiencia Posicional (No Supervisado).

Sistema complementario al PDI que utiliza clustering y análisis de componentes principales
para identificar tiers de eficiencia natural en jugadores por posición.

Metodología:
- Clustering K-means por posición (Elite, Strong, Average, Development)
- PCA para identificar componentes principales de eficiencia
- IEP Score derivado de posición en clusters (0-100)

Diferenciación vs PDI:
- PDI: Supervisado, pesos académicos predefinidos
- IEP: No supervisado, patrones naturales de eficiencia

Autor: Proyecto Fin de Máster - Python Aplicado al Deporte
Fecha: Agosto 2025
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from controllers.db import get_db_session
from models.professional_stats_model import ProfessionalStats

logger = logging.getLogger(__name__)


class IEPCalculator:
    """
    Calculadora del Índice Eficiencia Posicional (IEP).

    Sistema no supervisado que descubre patrones naturales de eficiencia
    en jugadores profesionales usando clustering K-means y PCA.

    Arquitectura:
    - Feature extraction por posición
    - Normalización y scaling
    - K-means clustering (3-4 clusters)
    - PCA analysis (2 componentes principales)
    - IEP score derivado (0-100)
    """

    def __init__(self, session_factory=None):
        """
        Inicializa el calculador IEP.

        Args:
            session_factory: Factory para sesiones de BD (opcional)
        """
        self.session_factory = session_factory or get_db_session

        # Componentes ML para análisis no supervisado
        self.scaler = StandardScaler()
        self.kmeans = None  # Se inicializa por posición
        self.pca = PCA(n_components=2)

        # Features base para análisis IEP por posición
        self.base_features = [
            "goals_per_90",
            "assists_per_90",
            "pass_accuracy_pct",
            "duels_won_pct",
            "shots_per_90",
            "interceptions_per_90",
            "tackles_per_90",
            "clearances_per_90",
            "minutes_played",
        ]

        # Configuración clustering por posición
        self.position_cluster_config = {
            "GK": {"n_clusters": 3, "features_weight": "defensive"},
            "CB": {"n_clusters": 3, "features_weight": "defensive"},
            "LB": {"n_clusters": 3, "features_weight": "balanced"},
            "RB": {"n_clusters": 3, "features_weight": "balanced"},
            "DMF": {"n_clusters": 4, "features_weight": "balanced"},
            "CMF": {"n_clusters": 4, "features_weight": "creative"},
            "AMF": {"n_clusters": 4, "features_weight": "creative"},
            "LW": {"n_clusters": 3, "features_weight": "offensive"},
            "RW": {"n_clusters": 3, "features_weight": "offensive"},
            "CF": {"n_clusters": 4, "features_weight": "offensive"},
        }

        logger.info("🧮 IEPCalculator inicializado - Sistema no supervisado")

    def calculate_position_clusters(
        self, position: str, season: str = "2024-25", min_matches: int = 5
    ) -> Dict:
        """
        Realiza clustering K-means para una posición específica.

        Args:
            position: Posición a analizar (ej: 'CF', 'CMF')
            season: Temporada para análisis
            min_matches: Mínimo de partidos para incluir jugador

        Returns:
            Dict con resultados de clustering y análisis
        """
        try:
            logger.info(f"🎯 Iniciando clustering IEP para {position} en {season}")

            # Obtener datos de liga para la posición
            position_data = self._get_position_data(position, season, min_matches)

            if not position_data or len(position_data) < 10:
                logger.warning(
                    f"Datos insuficientes para clustering {position}: {len(position_data) if position_data else 0} jugadores"
                )
                return {
                    "error": "insufficient_data",
                    "player_count": len(position_data) if position_data else 0,
                }

            # Preparar features para clustering
            feature_matrix, player_info = self._prepare_features_matrix(
                position_data, position
            )

            if feature_matrix.shape[0] < 10:
                logger.warning(
                    f"Features insuficientes después de limpieza: {feature_matrix.shape[0]} jugadores"
                )
                return {
                    "error": "insufficient_features",
                    "player_count": feature_matrix.shape[0],
                }

            # Normalizar features
            normalized_features = self.scaler.fit_transform(feature_matrix)

            # Configurar clustering por posición
            config = self.position_cluster_config.get(
                position, {"n_clusters": 3, "features_weight": "balanced"}
            )
            n_clusters = min(
                config["n_clusters"], len(position_data) // 3
            )  # Ajustar por datos disponibles

            # Aplicar K-means clustering
            self.kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = self.kmeans.fit_predict(normalized_features)

            # Aplicar PCA para componentes principales
            pca_components = self.pca.fit_transform(normalized_features)

            # Calcular métricas de calidad clustering
            silhouette_avg = silhouette_score(normalized_features, cluster_labels)
            inertia = self.kmeans.inertia_

            # Calcular IEP scores por jugador
            iep_scores = self._calculate_iep_scores(
                normalized_features, cluster_labels, pca_components, n_clusters
            )

            # Analizar clusters (caracterización)
            cluster_analysis = self._analyze_clusters(
                feature_matrix, cluster_labels, player_info, position
            )

            # Preparar resultados completos
            results = {
                "success": True,
                "position": position,
                "season": season,
                "analysis_date": datetime.now().isoformat(),
                "data_quality": {
                    "total_players": len(position_data),
                    "valid_for_clustering": feature_matrix.shape[0],
                    "features_used": feature_matrix.shape[1],
                    "min_matches_filter": min_matches,
                },
                "clustering_results": {
                    "n_clusters": n_clusters,
                    "silhouette_score": round(silhouette_avg, 3),
                    "inertia": round(inertia, 2),
                    "cluster_distribution": {
                        int(i): int(np.sum(cluster_labels == i))
                        for i in range(n_clusters)
                    },
                },
                "pca_analysis": {
                    "explained_variance_ratio": [
                        float(r) for r in self.pca.explained_variance_ratio_
                    ],
                    "total_variance_explained": float(
                        sum(self.pca.explained_variance_ratio_)
                    ),
                    "components": self.pca.components_.tolist(),
                },
                "players_data": [],
            }

            # Agregar datos individuales de jugadores
            for i, info in enumerate(player_info):
                player_result = {
                    "player_name": info["name"],
                    "team": info["team"],
                    "cluster_id": int(cluster_labels[i]),
                    "cluster_label": self._get_cluster_label(
                        cluster_labels[i], n_clusters
                    ),
                    "iep_score": round(iep_scores[i], 1),
                    "pca_components": [
                        float(pca_components[i, 0]),
                        float(pca_components[i, 1]),
                    ],
                    "key_features": {
                        feature: float(feature_matrix[i, j])
                        for j, feature in enumerate(self.base_features)
                        if j < feature_matrix.shape[1]
                    },
                }
                results["players_data"].append(player_result)

            # Agregar análisis de clusters
            results["cluster_analysis"] = cluster_analysis

            # Log resultado
            logger.info(f"✅ Clustering IEP completado para {position}:")
            logger.info(f"   📊 {len(position_data)} jugadores, {n_clusters} clusters")
            logger.info(
                f"   🎯 Silhouette: {silhouette_avg:.3f}, Varianza PCA: {sum(self.pca.explained_variance_ratio_):.1%}"
            )

            return results

        except Exception as e:
            logger.error(f"❌ Error en clustering IEP para {position}: {e}")
            return {"error": str(e), "position": position, "season": season}

    def calculate_player_iep(
        self, player_id: int, season: str = "2024-25", position: Optional[str] = None
    ) -> Dict:
        """
        Calcula IEP individual para un jugador específico.

        Args:
            player_id: ID del jugador
            season: Temporada a analizar
            position: Posición específica (opcional, se detecta automáticamente)

        Returns:
            Dict con IEP individual y contexto de cluster
        """
        try:
            logger.info(f"🎯 Calculando IEP individual para jugador {player_id}")

            # Obtener datos del jugador
            with self.session_factory() as session:
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
                        f"No se encontraron datos para jugador {player_id} en {season}"
                    )
                    return {
                        "error": "no_player_data",
                        "player_id": player_id,
                        "season": season,
                    }

                # Detectar posición si no se especifica
                if not position:
                    position = player_stats.primary_position

                if not position:
                    logger.warning(
                        f"No se pudo determinar posición para jugador {player_id}"
                    )
                    return {"error": "no_position", "player_id": player_id}

            # Obtener clustering de la posición
            cluster_results = self.calculate_position_clusters(position, season)

            if "error" in cluster_results:
                logger.warning(
                    f"Error en clustering posicional: {cluster_results['error']}"
                )
                return {"error": "clustering_failed", "details": cluster_results}

            # Buscar jugador en resultados de clustering
            player_data = None
            for player in cluster_results["players_data"]:
                # Comparar por nombre o ID (aquí usamos nombre por simplicidad)
                if str(player_id) in player["player_name"] or player["player_name"] in (
                    player_stats.full_name or ""
                ):
                    player_data = player
                    break

            if not player_data:
                logger.warning(
                    f"Jugador {player_id} no encontrado en clustering de {position}"
                )
                return {
                    "error": "player_not_in_cluster",
                    "player_id": player_id,
                    "position": position,
                }

            # Preparar resultado individual
            individual_result = {
                "success": True,
                "player_id": player_id,
                "season": season,
                "position": position,
                "analysis_date": datetime.now().isoformat(),
                "iep_metrics": {
                    "iep_score": player_data["iep_score"],
                    "cluster_tier": player_data["cluster_label"],
                    "cluster_id": player_data["cluster_id"],
                    "percentile_in_position": self._calculate_percentile(
                        player_data["iep_score"],
                        [p["iep_score"] for p in cluster_results["players_data"]],
                    ),
                },
                "efficiency_components": {
                    "principal_component_1": player_data["pca_components"][0],
                    "principal_component_2": player_data["pca_components"][1],
                    "explained_variance": cluster_results["pca_analysis"][
                        "total_variance_explained"
                    ],
                },
                "position_context": {
                    "total_players_analyzed": len(cluster_results["players_data"]),
                    "cluster_distribution": cluster_results["clustering_results"][
                        "cluster_distribution"
                    ],
                    "silhouette_score": cluster_results["clustering_results"][
                        "silhouette_score"
                    ],
                },
                "key_performance_features": player_data["key_features"],
            }

            logger.info(
                f"✅ IEP individual calculado: Score {player_data['iep_score']}, Tier {player_data['cluster_label']}"
            )
            return individual_result

        except Exception as e:
            logger.error(f"❌ Error calculando IEP individual: {e}")
            return {"error": str(e), "player_id": player_id, "season": season}

    # ============================================================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ============================================================================

    def _get_position_data(
        self, position: str, season: str, min_matches: int
    ) -> List[Dict]:
        """Obtiene datos de liga para una posición específica."""
        try:
            with self.session_factory() as session:
                # Query jugadores de la posición con filtros de calidad
                stats_query = session.query(ProfessionalStats).filter(
                    ProfessionalStats.season == season,
                    ProfessionalStats.primary_position == position,
                    ProfessionalStats.matches_played >= min_matches,
                )

                stats_data = stats_query.all()

                # Convertir a formato para análisis
                position_data = []
                for stat in stats_data:
                    # Calcular clearances como combinación de duelos aéreos ganados + interceptaciones
                    clearances_estimate = (stat.aerial_duels_per_90 or 0) * (
                        stat.aerial_duels_won_pct or 0
                    ) / 100 + (  # Aéreos ganados
                        stat.interceptions_per_90 or 0
                    )  # Interceptaciones

                    player_dict = {
                        "player_name": f"{stat.full_name or 'Unknown'} ({stat.team or 'N/A'})",
                        "team": stat.team or "Unknown",
                        "goals_per_90": stat.goals_per_90 or 0,
                        "assists_per_90": stat.assists_per_90 or 0,
                        "pass_accuracy_pct": stat.pass_accuracy_pct or 0,
                        "duels_won_pct": stat.duels_won_pct or 0,
                        "shots_per_90": stat.shots_per_90 or 0,
                        "interceptions_per_90": stat.interceptions_per_90 or 0,
                        "tackles_per_90": stat.sliding_tackles_per_90
                        or 0,  # Mapeo: sliding_tackles como proxy para tackles totales
                        "clearances_per_90": clearances_estimate,  # Calculado: aerial duels won + interceptions
                        "minutes_played": stat.minutes_played or 0,
                        "matches_played": stat.matches_played or 0,
                    }
                    position_data.append(player_dict)

                logger.info(
                    f"📊 Datos obtenidos para {position}: {len(position_data)} jugadores"
                )
                return position_data

        except Exception as e:
            logger.error(f"Error obteniendo datos posición {position}: {e}")
            return []

    def _prepare_features_matrix(
        self, position_data: List[Dict], position: str
    ) -> Tuple[np.ndarray, List[Dict]]:
        """Prepara matriz de features para clustering."""
        try:
            features_list = []
            player_info = []

            for player in position_data:
                # Extraer features base
                feature_row = []
                valid_features = True

                for feature in self.base_features:
                    value = player.get(feature, 0)
                    if pd.isna(value) or value is None:
                        value = 0

                    feature_row.append(float(value))

                # Validar que el jugador tenga datos mínimos
                if sum(feature_row) == 0 or player.get("minutes_played", 0) < 90:
                    continue

                features_list.append(feature_row)
                player_info.append(
                    {"name": player["player_name"], "team": player["team"]}
                )

            # Convertir a numpy array
            feature_matrix = np.array(features_list)

            logger.info(f"✅ Matriz features preparada: {feature_matrix.shape}")
            return feature_matrix, player_info

        except Exception as e:
            logger.error(f"Error preparando features matrix: {e}")
            return np.array([]), []

    def _calculate_iep_scores(
        self,
        normalized_features: np.ndarray,
        cluster_labels: np.ndarray,
        pca_components: np.ndarray,
        n_clusters: int,
    ) -> np.ndarray:
        """Calcula scores IEP basados en posición en clusters y componentes PCA."""
        try:
            iep_scores = []

            # Calcular centroides de clusters para referencia
            cluster_centers = []
            for i in range(n_clusters):
                cluster_mask = cluster_labels == i
                if np.any(cluster_mask):
                    center = np.mean(pca_components[cluster_mask], axis=0)
                    cluster_centers.append(center)
                else:
                    cluster_centers.append([0, 0])

            # Ordenar clusters por calidad (primer componente PCA)
            cluster_quality_order = sorted(
                range(n_clusters), key=lambda i: cluster_centers[i][0], reverse=True
            )

            for i in range(len(normalized_features)):
                cluster_id = cluster_labels[i]
                pca_pos = pca_components[i]

                # Score base por tier de cluster (0-100)
                cluster_rank = cluster_quality_order.index(cluster_id)
                base_score = 85 - (
                    cluster_rank * 20
                )  # Elite: 85, Strong: 65, Average: 45, Dev: 25

                # Ajuste por posición dentro del cluster (±15 puntos)
                pc1_adjustment = min(
                    15, max(-15, pca_pos[0] * 10)
                )  # Principal component influence
                pc2_adjustment = min(
                    5, max(-5, pca_pos[1] * 3)
                )  # Secondary component influence

                # IEP Score final (0-100)
                iep_score = base_score + pc1_adjustment + pc2_adjustment
                iep_score = max(0, min(100, iep_score))  # Clamp al rango

                iep_scores.append(iep_score)

            return np.array(iep_scores)

        except Exception as e:
            logger.error(f"Error calculando IEP scores: {e}")
            return np.zeros(len(normalized_features))

    def _analyze_clusters(
        self,
        feature_matrix: np.ndarray,
        cluster_labels: np.ndarray,
        player_info: List[Dict],
        position: str,
    ) -> Dict:
        """Analiza y caracteriza cada cluster."""
        try:
            analysis = {}
            n_clusters = len(np.unique(cluster_labels))

            for cluster_id in range(n_clusters):
                cluster_mask = cluster_labels == cluster_id
                cluster_features = feature_matrix[cluster_mask]
                cluster_players = [
                    player_info[i] for i in range(len(player_info)) if cluster_mask[i]
                ]

                if len(cluster_features) == 0:
                    continue

                # Calcular estadísticas del cluster
                cluster_stats = {}
                for j, feature in enumerate(self.base_features):
                    if j < feature_matrix.shape[1]:
                        cluster_stats[feature] = {
                            "mean": float(np.mean(cluster_features[:, j])),
                            "std": float(np.std(cluster_features[:, j])),
                            "median": float(np.median(cluster_features[:, j])),
                        }

                # Caracterización del cluster
                cluster_label = self._get_cluster_label(cluster_id, n_clusters)

                analysis[cluster_id] = {
                    "label": cluster_label,
                    "player_count": len(cluster_players),
                    "percentage": round(
                        len(cluster_players) / len(player_info) * 100, 1
                    ),
                    "top_players": [p["name"] for p in cluster_players[:5]],  # Top 5
                    "performance_profile": cluster_stats,
                    "characteristics": self._get_cluster_characteristics(
                        cluster_stats, position
                    ),
                }

            return analysis

        except Exception as e:
            logger.error(f"Error analizando clusters: {e}")
            return {}

    def _get_cluster_label(self, cluster_id: int, n_clusters: int) -> str:
        """Obtiene etiqueta descriptiva para cluster."""
        if n_clusters == 3:
            labels = ["Elite Tier", "Average Tier", "Development Tier"]
        elif n_clusters == 4:
            labels = ["Elite Tier", "Strong Tier", "Average Tier", "Development Tier"]
        else:
            return f"Cluster {cluster_id + 1}"

        return labels[min(cluster_id, len(labels) - 1)]

    def _get_cluster_characteristics(
        self, cluster_stats: Dict, position: str
    ) -> List[str]:
        """Genera características descriptivas del cluster."""
        characteristics = []

        try:
            # Análisis por posición
            if position in ["CF", "RW", "LW"]:  # Ofensivos
                if cluster_stats.get("goals_per_90", {}).get("mean", 0) > 0.5:
                    characteristics.append("High goal scoring rate")
                if cluster_stats.get("assists_per_90", {}).get("mean", 0) > 0.3:
                    characteristics.append("Strong assist contribution")
                if cluster_stats.get("shots_per_90", {}).get("mean", 0) > 3:
                    characteristics.append("High shot frequency")

            elif position in ["CMF", "AMF", "DMF"]:  # Mediocampistas
                if cluster_stats.get("pass_accuracy_pct", {}).get("mean", 0) > 85:
                    characteristics.append("Excellent passing accuracy")
                if cluster_stats.get("assists_per_90", {}).get("mean", 0) > 0.2:
                    characteristics.append("Creative playmaker")
                if cluster_stats.get("interceptions_per_90", {}).get("mean", 0) > 1:
                    characteristics.append("Strong ball recovery")

            elif position in ["CB", "LB", "RB"]:  # Defensivos
                if cluster_stats.get("tackles_per_90", {}).get("mean", 0) > 2:
                    characteristics.append("High tackling activity")
                if cluster_stats.get("clearances_per_90", {}).get("mean", 0) > 3:
                    characteristics.append("Strong aerial/clearance game")
                if cluster_stats.get("duels_won_pct", {}).get("mean", 0) > 60:
                    characteristics.append("Dominant in duels")

            # Características generales
            if cluster_stats.get("minutes_played", {}).get("mean", 0) > 2000:
                characteristics.append("High playing time")

            if not characteristics:
                characteristics.append("Balanced performance profile")

        except Exception as e:
            logger.debug(f"Error generando características: {e}")
            characteristics = ["Standard performance profile"]

        return characteristics

    def _calculate_percentile(
        self, player_score: float, all_scores: List[float]
    ) -> float:
        """Calcula percentil del jugador en la posición."""
        try:
            sorted_scores = sorted(all_scores)
            position = sorted_scores.index(player_score)
            percentile = (position / len(sorted_scores)) * 100
            return round(percentile, 1)
        except:
            return 50.0  # Fallback a mediana


# ============================================================================
# LOGGING Y CONFIGURACIÓN
# ============================================================================

logger.info(
    "🧮 Módulo IEPCalculator cargado - Sistema no supervisado para análisis de eficiencia posicional"
)

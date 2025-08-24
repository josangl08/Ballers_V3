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
            # Posiciones específicas
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
            # Grupos de posiciones (para análisis por grupos)
            "GK": {"n_clusters": 3, "features_weight": "defensive"},
            "DEF": {"n_clusters": 4, "features_weight": "defensive"},
            "MID": {"n_clusters": 4, "features_weight": "balanced"},
            "FWD": {"n_clusters": 4, "features_weight": "offensive"},
        }

        logger.info("🧮 IEPCalculator inicializado - Sistema no supervisado")

    def calculate_position_clusters(
        self,
        position: str,
        season: str = "2024-25",
        min_matches: int = 5,
        current_player_id: int = None,
    ) -> Dict:
        """
        Realiza clustering K-means para una posición específica.

        Args:
            position: Posición a analizar (ej: 'CF', 'CMF')
            season: Temporada para análisis
            min_matches: Mínimo de partidos para incluir jugador
            current_player_id: ID del jugador actual (siempre incluido independiente del min_matches)

        Returns:
            Dict con resultados de clustering y análisis
        """
        try:
            logger.info(f"🎯 Iniciando clustering IEP para {position} en {season}")
            if current_player_id:
                logger.info(
                    f"🎯 Jugador actual incluido forzosamente: {current_player_id}"
                )

            # Obtener datos de liga para la posición
            position_data = self._get_position_data(
                position, season, min_matches, current_player_id
            )

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

            # Configurar clustering por posición (default a 4 clusters para mejor granularidad)
            config = self.position_cluster_config.get(
                position, {"n_clusters": 4, "features_weight": "balanced"}
            )
            # Ajustar clusters por datos disponibles (mínimo 2 jugadores por cluster)
            n_clusters = min(config["n_clusters"], max(2, len(position_data) // 2))

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
                        cluster_labels[i], n_clusters, iep_scores, cluster_labels
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
        self,
        position: str,
        season: str,
        min_matches: int,
        current_player_id: int = None,
    ) -> List[Dict]:
        """
        Obtiene datos de liga para una posición específica.

        MODIFICADO: Usa CSV (493 jugadores) en lugar de BD (5 jugadores)
        para clustering con datos reales de liga.
        """
        try:
            # CAMBIO: Usar CSV en lugar de BD para datos completos
            from controllers.csv_stats_controller import CSVStatsController

            # 🎯 DEBUG: Logging detallado de filtros
            logger.info(f"🔍 IEP _get_position_data INICIADO:")
            logger.info(f"   - position: '{position}'")
            logger.info(f"   - season: '{season}'")
            logger.info(f"   - min_matches: {min_matches}")

            csv_controller = CSVStatsController()
            df = csv_controller._load_season_data(season)

            if df is None:
                logger.warning(f"No se pudo cargar datos CSV para temporada {season}")
                return []

            # 🔍 DEBUG: Total jugadores en CSV
            logger.info(f"🔍 Total jugadores en CSV {season}: {len(df)}")

            # Filtrar por posición o grupo (mapear columnas CSV → BD)
            position_df = self._filter_by_position_or_group(df, position)

            # 🔍 DEBUG: Después de filtro posición
            logger.info(
                f"🔍 Jugadores después de filtro posición '{position}': {len(position_df)}"
            )

            # Filtrar por mínimo de partidos (usar "Matches played" del CSV)
            if "Matches played" in position_df.columns:
                position_df_filtered = position_df[
                    position_df["Matches played"] >= min_matches
                ]

                # 🔍 DEBUG: Después de filtro mínimo partidos
                logger.info(
                    f"🔍 Jugadores después de filtro ≥{min_matches} partidos: {len(position_df_filtered)}"
                )

                # Si hay current_player_id, verificar si necesita ser agregado manualmente
                if current_player_id:
                    # Buscar el jugador actual en la BD para obtener su wyscout_id
                    from controllers.db import get_db_session
                    from models.player_model import Player

                    with get_db_session() as session:
                        current_player = (
                            session.query(Player)
                            .filter(Player.player_id == current_player_id)
                            .first()
                        )
                        if current_player and current_player.wyscout_id:
                            current_wyscout_id = str(current_player.wyscout_id)
                            logger.info(
                                f"🔍 Buscando jugador actual en CSV - Wyscout ID: {current_wyscout_id}"
                            )

                            # Verificar si el jugador actual ya está en los datos filtrados
                            current_in_filtered = (
                                position_df_filtered["Wyscout id"]
                                .astype(str)
                                .str.contains(current_wyscout_id, na=False)
                                .any()
                            )

                            if not current_in_filtered:
                                # Verificar si está en los datos de la posición (antes del filtro de partidos)
                                current_in_position = (
                                    position_df["Wyscout id"]
                                    .astype(str)
                                    .str.contains(current_wyscout_id, na=False)
                                    .any()
                                )

                                if current_in_position:
                                    # Obtener los datos del jugador actual
                                    current_player_row = position_df[
                                        position_df["Wyscout id"]
                                        .astype(str)
                                        .str.contains(current_wyscout_id, na=False)
                                    ]
                                    if not current_player_row.empty:
                                        matches_played = current_player_row.iloc[0].get(
                                            "Matches played", 0
                                        )
                                        logger.info(
                                            f"🎯 AGREGANDO jugador actual forzosamente: {current_player.user.name} (Partidos: {matches_played}, Min requerido: {min_matches})"
                                        )

                                        # Agregar al jugador actual a los datos filtrados
                                        position_df = pd.concat(
                                            [position_df_filtered, current_player_row],
                                            ignore_index=True,
                                        )
                                    else:
                                        logger.warning(
                                            f"❌ No se pudo obtener datos del jugador actual del CSV"
                                        )
                                        position_df = position_df_filtered
                                else:
                                    logger.warning(
                                        f"❌ Jugador actual no encontrado en posición {position}"
                                    )
                                    position_df = position_df_filtered
                            else:
                                logger.info(
                                    f"✅ Jugador actual ya incluido en filtro de partidos"
                                )
                                position_df = position_df_filtered
                        else:
                            logger.warning(
                                f"❌ No se pudo obtener wyscout_id del jugador actual"
                            )
                            position_df = position_df_filtered
                else:
                    position_df = position_df_filtered

            else:
                position_df = position_df

            if len(position_df) == 0:
                logger.warning(
                    f"❌ No hay jugadores {position} después de todos los filtros en {season}"
                )
                return []

            # 🔍 DEBUG: Mostrar algunos jugadores que quedaron
            logger.info(f"🔍 JUGADORES QUE PASARON TODOS LOS FILTROS (primeros 5):")
            for i, (idx, row) in enumerate(position_df.head().iterrows()):
                player_name = row.get("Player", "NO_NAME")
                matches = row.get("Matches played", 0)
                wyscout_id = row.get("Wyscout id", "NO_ID")
                logger.info(
                    f"   [{i}] {player_name} (Matches: {matches}, Wyscout: {wyscout_id})"
                )

            # Convertir a formato para análisis (mapear columnas CSV → formato esperado)
            position_data = []

            for idx, row in position_df.iterrows():
                # Calcular clearances usando columnas disponibles en CSV
                clearances_estimate = row.get("Aerial duels per 90", 0) * row.get(
                    "Aerial duels won, %", 0
                ) / 100 + row.get("Interceptions per 90", 0)

                player_dict = {
                    "player_name": f"{row.get('Player', 'Unknown')} ({row.get('Team', 'N/A')})",
                    "team": row.get("Team", "Unknown"),
                    "goals_per_90": row.get("Goals per 90", 0) or 0,
                    "assists_per_90": row.get("Assists per 90", 0) or 0,
                    "pass_accuracy_pct": row.get("Pass accuracy, %", 0) or 0,
                    "duels_won_pct": row.get("Duels won, %", 0) or 0,
                    "shots_per_90": row.get("Shots per 90", 0) or 0,
                    "interceptions_per_90": row.get("Interceptions per 90", 0) or 0,
                    "tackles_per_90": row.get("Sliding tackles per 90", 0) or 0,
                    "clearances_per_90": clearances_estimate,
                    "minutes_played": row.get("Minutes played", 0) or 0,
                    "matches_played": row.get("Matches played", 0) or 0,
                }
                position_data.append(player_dict)

            logger.info(
                f"✅ CSV: Datos obtenidos para {position} en {season}: {len(position_data)} jugadores (vs BD: ~0-5)"
            )

            return position_data

        except Exception as e:
            logger.error(f"❌ Error obteniendo datos CSV de posición: {e}")
            # Fallback a método original BD si CSV falla
            logger.info("🔄 Fallback: Intentando datos BD como respaldo...")
            return self._get_position_data_bd_fallback(
                position, season, min_matches, current_player_id
            )

    def _get_position_data_bd_fallback(
        self,
        position: str,
        season: str,
        min_matches: int,
        current_player_id: int = None,
    ) -> List[Dict]:
        """
        Fallback al método original BD si CSV falla.

        Nota: current_player_id está disponible pero no implementado aquí
        porque el fallback BD se usa raramente y tiene datos limitados.
        """
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
                    f"📊 BD Fallback: Datos obtenidos para {position}: {len(position_data)} jugadores"
                )
                return position_data

        except Exception as e:
            logger.error(f"Error en BD fallback: {e}")
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

    def _get_cluster_label(
        self,
        cluster_id: int,
        n_clusters: int,
        iep_scores: List[float] = None,
        cluster_labels: List[int] = None,
    ) -> str:
        """
        Obtiene etiqueta descriptiva para cluster basada en rendimiento real.

        Args:
            cluster_id: ID del cluster
            n_clusters: Número total de clusters
            iep_scores: Puntuaciones IEP de todos los jugadores (opcional)
            cluster_labels: Labels de cluster de todos los jugadores (opcional)

        Returns:
            Etiqueta descriptiva del cluster
        """
        # Si no tenemos datos de IEP, usar asignación simple (fallback)
        if iep_scores is None or cluster_labels is None:
            if n_clusters == 3:
                labels = ["Elite Tier", "Average Tier", "Development Tier"]
            elif n_clusters == 4:
                labels = [
                    "Elite Tier",
                    "Strong Tier",
                    "Average Tier",
                    "Development Tier",
                ]
            else:
                return f"Cluster {cluster_id + 1}"
            return labels[min(cluster_id, len(labels) - 1)]

        # Calcular IEP promedio por cluster para asignación coherente
        import numpy as np

        cluster_averages = {}
        for i in range(n_clusters):
            cluster_mask = [label == i for label in cluster_labels]
            cluster_iep_scores = [
                iep_scores[j]
                for j, is_in_cluster in enumerate(cluster_mask)
                if is_in_cluster
            ]
            if cluster_iep_scores:
                cluster_averages[i] = np.mean(cluster_iep_scores)
            else:
                cluster_averages[i] = 0

        # Ordenar clusters por rendimiento (mejor → peor)
        sorted_clusters = sorted(
            cluster_averages.items(), key=lambda x: x[1], reverse=True
        )

        # Determinar nombres de tiers según número de clusters
        if n_clusters == 3:
            tier_names = ["Elite Tier", "Average Tier", "Development Tier"]
        elif n_clusters == 4:
            tier_names = [
                "Elite Tier",
                "Strong Tier",
                "Average Tier",
                "Development Tier",
            ]
        else:
            tier_names = [f"Tier {i+1}" for i in range(n_clusters)]

        # Encontrar ranking del cluster actual
        cluster_rank = next(
            i for i, (cid, _) in enumerate(sorted_clusters) if cid == cluster_id
        )

        return tier_names[min(cluster_rank, len(tier_names) - 1)]

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

    def _filter_by_position_or_group(self, df, position_or_group):
        """
        Filtra DataFrame por posición específica o grupo de 8 posiciones específicas.

        Args:
            df: DataFrame con datos de jugadores
            position_or_group: Posición específica (ej: "CF") o grupo de 8 (ej: "CB", "AMF")

        Returns:
            DataFrame filtrado
        """
        try:
            # Importar mapper de 8 grupos desde position_analyzer
            from ml_system.evaluation.analysis.position_analyzer import PositionAnalyzer

            analyzer = PositionAnalyzer()

            # Verificar si es uno de los 8 grupos específicos
            if position_or_group in ["GK", "CB", "FB", "DMF", "CMF", "AMF", "W", "CF"]:
                # Obtener todas las posiciones específicas que mapean a este grupo
                specific_positions = [
                    pos
                    for pos, group in analyzer.position_mapping.items()
                    if group == position_or_group
                ]

                # Filtrar por cualquier posición específica del grupo
                position_df = df[df["Primary position"].isin(specific_positions)].copy()
                logger.info(
                    f"Filtrando por grupo {position_or_group}: {specific_positions} → {len(position_df)} jugadores"
                )
            else:
                # Es una posición específica - usar filtro original
                position_df = df[df["Primary position"] == position_or_group].copy()
                logger.info(
                    f"Filtrando por posición específica {position_or_group} → {len(position_df)} jugadores"
                )

            return position_df

        except Exception as e:
            logger.error(
                f"Error filtrando por grupo 8-posiciones {position_or_group}: {e}"
            )
            # Fallback a filtro original
            return df[df["Primary position"] == position_or_group].copy()


# ============================================================================
# LOGGING Y CONFIGURACIÓN
# ============================================================================

logger.info(
    "🧮 Módulo IEPCalculator cargado - Sistema no supervisado para análisis de eficiencia posicional"
)

"""
CSV Stats Controller - Manejo eficiente de datos CSV de la liga tailandesa.

Proporciona acceso rápido y cacheado a estadísticas de liga y equipo usando
los archivos CSV procesados de la liga tailandesa. Integrado con el sistema
de mapeo posicional de PositionAnalyzer.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class CSVStatsController:
    """
    Controlador para acceso eficiente a datos CSV de la liga tailandesa.

    Proporciona cálculos de promedios de liga y equipo con cache inteligente
    y reutilización del mapeo posicional existente.
    """

    def __init__(self):
        """Inicializa el controlador con paths y cache."""
        self.base_path = Path(__file__).parent.parent / "data" / "thai_league_processed"
        self.cached_data = {}  # Cache por temporada
        self.available_seasons = []

        # Mapeo posicional granular (copiado desde PDICalculator)
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

        # Métricas por posición (simplificado)
        self.position_metrics_map = {
            "GK": {
                "primary_metrics": [
                    "save_percentage",
                    "goals_conceded_per_90",
                    "pass_accuracy_pct",
                    "aerial_duels_won_pct",
                    "defensive_actions_per_90",
                ]
            },
            "CB": {
                "primary_metrics": [
                    "aerial_duels_won_pct",
                    "interceptions_per_90",
                    "defensive_duels_won_pct",
                    "defensive_actions_per_90",
                    "pass_accuracy_pct",
                ]
            },
            "FB": {
                "primary_metrics": [
                    "crosses_per_90",
                    "cross_accuracy_pct",
                    "tackles_per_90",
                    "defensive_duels_won_pct",
                    "assists_per_90",
                ]
            },
            "DMF": {
                "primary_metrics": [
                    "pass_accuracy_pct",
                    "progressive_passes_per_90",
                    "ball_recoveries_per_90",
                    "tackles_per_90",
                    "interceptions_per_90",
                ]
            },
            "CMF": {
                "primary_metrics": [
                    "pass_accuracy_pct",
                    "key_passes_per_90",
                    "progressive_passes_per_90",
                    "dribbles_success_pct",
                    "assists_per_90",
                ]
            },
            "AMF": {
                "primary_metrics": [
                    "key_passes_per_90",
                    "assists_per_90",
                    "goals_per_90",
                    "shot_assists_per_90",
                    "dribbles_success_pct",
                ]
            },
            "W": {
                "primary_metrics": [
                    "goals_per_90",
                    "assists_per_90",
                    "dribbles_success_pct",
                    "crosses_per_90",
                    "shots_on_target_pct",
                ]
            },
            "CF": {
                "primary_metrics": [
                    "goals_per_90",
                    "shots_on_target_pct",
                    "touches_in_box_per_90",
                    "aerial_duels_won_pct",
                    "assists_per_90",
                ]
            },
        }

        # Mapeo de nombres de columnas CSV a nombres de métricas
        self.csv_field_mapping = {
            # Métricas básicas
            "goals_per_90": "Goals per 90",
            "assists_per_90": "Assists per 90",
            "pass_accuracy_pct": "Accurate passes, %",
            "shots_on_target_pct": "Shots on target, %",
            # Métricas defensivas
            "defensive_actions_per_90": "Successful defensive actions per 90",
            "defensive_duels_won_pct": "Defensive duels won, %",
            "aerial_duels_won_pct": "Aerial duels won, %",
            "interceptions_per_90": "Interceptions per 90",
            "tackles_per_90": "Sliding tackles per 90",
            "sliding_tackles_per_90": "Sliding tackles per 90",  # Alias para métricas optimizadas
            "fouls_per_90": "Fouls per 90",
            # Métricas de mediocampo
            "progressive_passes_per_90": "Progressive passes per 90",
            "key_passes_per_90": "Key passes per 90",
            "ball_recoveries_per_90": "Successful defensive actions per 90",  # Aproximación
            # Métricas ofensivas
            "dribbles_success_pct": "Successful dribbles, %",
            "crosses_per_90": "Crosses per 90",
            "cross_accuracy_pct": "Accurate crosses, %",
            "touches_in_box_per_90": "Touches in box per 90",
            "shot_assists_per_90": "Shot assists per 90",
            # Métricas de pases (previamente faltantes - causa raíz del problema)
            "passes_per_90": "Passes per 90",
            "accurate_passes_per_90": "Accurate passes per 90",
            "long_passes_per_90": "Long passes per 90",
            "accurate_long_passes_per_90": "Accurate long passes per 90",
            "long_passes_accuracy_pct": "Accurate long passes, %",
            "short_medium_passes_per_90": "Short / medium passes per 90",
            "accurate_short_medium_passes_per_90": "Accurate short / medium passes per 90",
            "short_medium_passes_accuracy_pct": "Short / medium passes accuracy, %",
            "forward_passes_per_90": "Forward passes per 90",
            "accurate_forward_passes_per_90": "Accurate forward passes per 90",
            "back_passes_per_90": "Back passes per 90",
            "accurate_back_passes_per_90": "Accurate back passes per 90",
            "lateral_passes_per_90": "Lateral passes per 90",
            "accurate_lateral_passes_per_90": "Accurate lateral passes per 90",
            "passes_to_final_third_per_90": "Passes to final third per 90",
            "accurate_passes_to_final_third_per_90": "Accurate passes to final third per 90",
            "passes_to_penalty_area_per_90": "Passes to penalty area per 90",
            "accurate_passes_to_penalty_area_per_90": "Accurate passes to penalty area per 90",
            "average_pass_length_m": "Average pass length, m",
            "average_long_pass_length_m": "Average long pass length, m",
            "received_passes_per_90": "Received passes per 90",
            "received_long_passes_per_90": "Received long passes per 90",
            # Métricas de duelos y toques
            "dribbles_per_90": "Dribbles per 90",
            "successful_dribbles_per_90": "Successful dribbles per 90",
            "offensive_duels_per_90": "Offensive duels per 90",
            "touches_per_90": "Touches per 90",
            "lost_balls_per_90": "Lost balls per 90",
            "lost_balls_own_half_per_90": "Lost balls in own half per 90",
            "fouls_suffered_per_90": "Fouls suffered per 90",
            "offsides_per_90": "Offsides per 90",
            # Métricas de portero
            "save_percentage": "Save rate, %",
            "goals_conceded_per_90": "Conceded goals per 90",
            "clean_sheets": "Clean sheets",
        }

        self._discover_available_seasons()
        logger.info(
            f"CSVStatsController inicializado con {len(self.available_seasons)} temporadas"
        )

    def _discover_available_seasons(self):
        """Descubre qué temporadas están disponibles en los archivos CSV."""
        try:
            if not self.base_path.exists():
                logger.warning(f"Directorio CSV no encontrado: {self.base_path}")
                return

            for csv_file in self.base_path.glob("processed_*.csv"):
                filename = csv_file.stem
                if (
                    filename.startswith("processed_")
                    and filename != "processed_complete"
                ):
                    season = filename.replace("processed_", "")
                    self.available_seasons.append(season)

            self.available_seasons.sort(reverse=True)  # Más reciente primero
            logger.info(f"Temporadas disponibles: {self.available_seasons}")

        except Exception as e:
            logger.error(f"Error descubriendo temporadas: {e}")

    def _load_season_data(self, season: str) -> Optional[pd.DataFrame]:
        """
        Carga datos de una temporada específica con cache.

        Args:
            season: Temporada a cargar (ej: "2023-24")

        Returns:
            DataFrame con datos de la temporada o None
        """
        if season in self.cached_data:
            return self.cached_data[season]

        try:
            csv_path = self.base_path / f"processed_{season}.csv"

            if not csv_path.exists():
                logger.warning(f"Archivo CSV no encontrado: {csv_path}")
                return None

            # Cargar CSV con manejo de encoding
            df = pd.read_csv(csv_path, encoding="utf-8")

            # Validar columnas esenciales
            required_cols = ["Primary position", "Team", "Goals per 90"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"Columnas faltantes en {season}: {missing_cols}")
                return None

            # Cache y return
            self.cached_data[season] = df
            logger.info(f"Datos cargados para {season}: {len(df)} jugadores")
            return df

        except Exception as e:
            logger.error(f"Error cargando datos de {season}: {e}")
            return None

    def get_league_averages(
        self,
        position: str,
        seasons: List[str],
        min_matches: int = 10,
        custom_metrics: Optional[List[str]] = None,
    ) -> Dict:
        """
        Calcula promedios de liga para una posición específica.

        Args:
            position: Grupo posicional (GK, CB, FB, DMF, CMF, AMF, W, CF)
            seasons: Lista de temporadas a incluir
            min_matches: Mínimo de partidos jugados
            custom_metrics: Lista de métricas específicas a calcular (opcional)

        Returns:
            Dict con promedios de liga
        """
        try:
            all_players = []

            # Combinar datos de múltiples temporadas
            for season in seasons:
                df = self._load_season_data(season)
                if df is not None:
                    all_players.append(df)

            if not all_players:
                logger.warning(f"No se encontraron datos para temporadas: {seasons}")
                return {}

            # Concatenar todas las temporadas
            combined_df = pd.concat(all_players, ignore_index=True)

            # Obtener posiciones específicas que mapean al grupo
            specific_positions = [
                pos for pos, grp in self.position_mapping.items() if grp == position
            ]

            # Filtrar por posición y partidos mínimos
            position_players = combined_df[
                (combined_df["Primary position"].isin(specific_positions))
                & (combined_df["Matches played"] >= min_matches)
            ]

            if position_players.empty:
                logger.warning(f"No se encontraron jugadores para posición {position}")
                return {}

            # Determinar qué métricas usar (custom o por defecto)
            position_config = self.position_metrics_map.get(
                position, {}
            )  # Siempre definir position_config
            if custom_metrics:
                metrics_to_process = custom_metrics
                logger.info(f"Usando métricas personalizadas: {metrics_to_process}")
            else:
                # CAMBIO CRÍTICO: Si no hay custom_metrics, usar TODAS las métricas que tengan mapeo
                # En lugar de solo las primary_metrics de la posición
                metrics_to_process = list(self.csv_field_mapping.keys())

            averages = {}
            for metric_key in metrics_to_process:
                csv_field = self.csv_field_mapping.get(metric_key)
                if csv_field and csv_field in position_players.columns:
                    # Eliminar valores nulos y calcular promedio
                    valid_values = position_players[csv_field].dropna()
                    if len(valid_values) > 0:
                        avg_value = valid_values.mean()
                        averages[metric_key] = {
                            "value": avg_value,
                            "display_name": position_config.get(
                                "display_names", {}
                            ).get(metric_key, metric_key.replace("_", " ").title()),
                            "sample_size": len(valid_values),
                        }

            return {
                "position": position,
                "seasons": seasons,
                "averages": averages,
                "players_analyzed": len(position_players),
                "data_source": "CSV",
            }

        except Exception as e:
            logger.error(f"Error calculando promedios de liga: {e}")
            return {}

    def get_team_averages(self, team: str, position: str, seasons: List[str]) -> Dict:
        """
        Calcula promedios de equipo para una posición específica.

        Args:
            team: Nombre del equipo
            position: Grupo posicional (GK, CB, FB, DMF, CMF, AMF, W, CF)
            seasons: Lista de temporadas a incluir

        Returns:
            Dict con promedios del equipo
        """
        try:
            all_players = []

            # Combinar datos de múltiples temporadas
            for season in seasons:
                df = self._load_season_data(season)
                if df is not None:
                    all_players.append(df)

            if not all_players:
                return {}

            combined_df = pd.concat(all_players, ignore_index=True)

            # Obtener posiciones específicas que mapean al grupo
            specific_positions = [
                pos for pos, grp in self.position_mapping.items() if grp == position
            ]

            # Filtrar por equipo y posición
            team_players = combined_df[
                (combined_df["Team"] == team)
                & (combined_df["Primary position"].isin(specific_positions))
            ]

            if team_players.empty:
                logger.warning(
                    f"No se encontraron jugadores del equipo {team} en posición {position}"
                )
                # Retornar promedios de liga como fallback
                return self.get_league_averages(position, seasons)

            # Calcular promedios para TODAS las métricas disponibles
            position_config = self.position_metrics_map.get(position, {})
            # CAMBIO: Usar todas las métricas que tengan mapeo
            all_metrics = list(self.csv_field_mapping.keys())

            averages = {}
            for metric_key in all_metrics:
                csv_field = self.csv_field_mapping.get(metric_key)
                if csv_field and csv_field in team_players.columns:
                    valid_values = team_players[csv_field].dropna()
                    if len(valid_values) > 0:
                        avg_value = valid_values.mean()
                        averages[metric_key] = {
                            "value": avg_value,
                            "display_name": position_config.get(
                                "display_names", {}
                            ).get(metric_key, metric_key),
                            "sample_size": len(valid_values),
                        }

            return {
                "team": team,
                "position": position,
                "seasons": seasons,
                "averages": averages,
                "players_analyzed": len(team_players),
                "data_source": "CSV",
            }

        except Exception as e:
            logger.error(f"Error calculando promedios de equipo: {e}")
            return {}

    def get_league_percentiles(
        self, position: str, seasons: List[str], percentile: float = 75.0
    ) -> Dict:
        """
        Calcula percentiles de liga para una posición específica.

        Args:
            position: Grupo posicional
            seasons: Lista de temporadas
            percentile: Percentil a calcular (75.0 = top 25%)

        Returns:
            Dict con valores de percentil
        """
        try:
            all_players = []

            for season in seasons:
                df = self._load_season_data(season)
                if df is not None:
                    all_players.append(df)

            if not all_players:
                return {}

            combined_df = pd.concat(all_players, ignore_index=True)
            specific_positions = [
                pos for pos, grp in self.position_mapping.items() if grp == position
            ]

            position_players = combined_df[
                (combined_df["Primary position"].isin(specific_positions))
                & (combined_df["Matches played"] >= 10)
            ]

            if position_players.empty:
                return {}

            position_config = self.position_metrics_map.get(position, {})
            primary_metrics = position_config.get("primary_metrics", [])

            percentiles = {}
            for metric_key in primary_metrics:
                csv_field = self.csv_field_mapping.get(metric_key)
                if csv_field and csv_field in position_players.columns:
                    valid_values = position_players[csv_field].dropna()
                    if len(valid_values) > 0:
                        percentile_value = valid_values.quantile(percentile / 100)
                        percentiles[metric_key] = {
                            "value": percentile_value,
                            "display_name": position_config.get(
                                "display_names", {}
                            ).get(metric_key, metric_key),
                            "percentile": percentile,
                            "sample_size": len(valid_values),
                        }

            return {
                "position": position,
                "seasons": seasons,
                "percentiles": percentiles,
                "percentile_level": percentile,
                "players_analyzed": len(position_players),
                "data_source": "CSV",
            }

        except Exception as e:
            logger.error(f"Error calculando percentiles de liga: {e}")
            return {}

    def get_top25_averages(self, position: str, seasons: List[str]) -> Dict:
        """
        Calcula la media real del 25% mejores jugadores para una posición específica.

        Args:
            position: Grupo posicional
            seasons: Lista de temporadas

        Returns:
            Dict con valores promedio del top 25% de jugadores
        """
        try:
            all_players = []

            for season in seasons:
                df = self._load_season_data(season)
                if df is not None:
                    all_players.append(df)

            if not all_players:
                return {}

            combined_df = pd.concat(all_players, ignore_index=True)
            specific_positions = [
                pos for pos, grp in self.position_mapping.items() if grp == position
            ]

            position_players = combined_df[
                (combined_df["Primary position"].isin(specific_positions))
                & (combined_df["Matches played"] >= 10)
            ]

            if position_players.empty:
                return {}

            position_config = self.position_metrics_map.get(position, {})
            # CAMBIO: Usar todas las métricas que tengan mapeo
            all_metrics = list(self.csv_field_mapping.keys())

            top25_averages = {}
            for metric_key in all_metrics:
                csv_field = self.csv_field_mapping.get(metric_key)
                if csv_field and csv_field in position_players.columns:
                    valid_values = position_players[csv_field].dropna()
                    if len(valid_values) > 0:
                        # Calcular percentil 75 (umbral del top 25%)
                        p75_threshold = valid_values.quantile(0.75)

                        # Filtrar jugadores en el top 25% (≥ percentil 75)
                        top25_players = valid_values[valid_values >= p75_threshold]

                        if len(top25_players) > 0:
                            # Calcular la media real del top 25%
                            top25_average = top25_players.mean()

                            top25_averages[metric_key] = {
                                "value": top25_average,
                                "display_name": position_config.get(
                                    "display_names", {}
                                ).get(metric_key, metric_key),
                                "p75_threshold": p75_threshold,
                                "top25_sample_size": len(top25_players),
                                "total_sample_size": len(valid_values),
                            }

            return {
                "position": position,
                "seasons": seasons,
                "averages": top25_averages,
                "players_analyzed": len(position_players),
                "data_source": "CSV",
                "calculation_method": "top25_mean",
            }

        except Exception as e:
            logger.error(f"Error calculando promedios top 25%: {e}")
            return {}

    def get_available_seasons_list(self) -> List[str]:
        """Retorna lista de temporadas disponibles."""
        return self.available_seasons.copy()

    def get_position_sample_size(self, position: str, seasons: List[str]) -> int:
        """Retorna el número total de jugadores para una posición en las temporadas especificadas."""
        try:
            all_players = []

            # Obtener posiciones específicas que mapean al grupo
            specific_positions = [
                pos for pos, grp in self.position_mapping.items() if grp == position
            ]

            for season in seasons:
                df = self._load_season_data(season)
                if df is not None:
                    # Filtrar por posición usando Primary position (como en CSV)
                    position_players = df[
                        df["Primary position"].isin(specific_positions)
                    ]
                    all_players.append(position_players)

            if all_players:
                combined_df = pd.concat(all_players, ignore_index=True)
                return len(combined_df)

            return 0

        except Exception as e:
            logger.error(f"Error obteniendo tamaño de muestra para {position}: {e}")
            return 0

    def get_zero_count_for_metric(
        self, position: str, seasons: List[str], metric_key: str
    ) -> int:
        """Retorna cuántos jugadores tienen valor 0 para una métrica específica."""
        try:
            csv_field = self.csv_field_mapping.get(metric_key)
            if not csv_field:
                return 0

            all_players = []

            # Obtener posiciones específicas que mapean al grupo
            specific_positions = [
                pos for pos, grp in self.position_mapping.items() if grp == position
            ]

            for season in seasons:
                df = self._load_season_data(season)
                if df is not None:
                    # Filtrar por posición usando Primary position (como en CSV)
                    position_players = df[
                        df["Primary position"].isin(specific_positions)
                    ]
                    all_players.append(position_players)

            if all_players:
                combined_df = pd.concat(all_players, ignore_index=True)

                if csv_field in combined_df.columns:
                    # Contar jugadores con valor exactamente 0 (no NaN)
                    zero_count = (combined_df[csv_field] == 0.0).sum()
                    return int(zero_count)

            return 0

        except Exception as e:
            logger.error(f"Error contando ceros para {metric_key} en {position}: {e}")
            return 0

    def get_metric_percentiles(
        self,
        position: str,
        seasons: List[str],
        metric: str,
        player_value: Optional[float] = None,
    ) -> Optional[Dict]:
        """
        Calcula percentiles (P10, P25, P50, P75, P90) para una métrica específica.
        Opcionalmente calcula el percentil exacto de un jugador específico.

        Args:
            position: Grupo posicional (GK, CB, FB, DMF, CMF, AMF, W, CF)
            seasons: Lista de temporadas a incluir
            metric: Métrica a calcular percentiles
            player_value: Valor del jugador para calcular su percentil exacto (opcional)

        Returns:
            Dict con percentiles y opcionalmente player_percentile o None si no hay datos
        """
        try:
            csv_field = self.csv_field_mapping.get(metric)
            if not csv_field:
                logger.warning(f"Métrica no mapeada: {metric}")
                return None

            all_players = []

            # Obtener posiciones específicas que mapean al grupo
            specific_positions = [
                pos for pos, grp in self.position_mapping.items() if grp == position
            ]

            # Combinar datos de múltiples temporadas
            for season in seasons:
                df = self._load_season_data(season)
                if df is not None:
                    # Filtrar por posición usando Primary position
                    position_players = df[
                        df["Primary position"].isin(specific_positions)
                    ]
                    all_players.append(position_players)

            if not all_players:
                logger.warning(f"No data found for percentiles: {position}, {metric}")
                return None

            # Concatenar todas las temporadas
            combined_df = pd.concat(all_players, ignore_index=True)

            # Verificar que existe la columna
            if csv_field not in combined_df.columns:
                logger.warning(f"Columna CSV no encontrada: {csv_field}")
                return None

            # Filtrar valores válidos (no NaN, mayores que 0 para la mayoría de métricas)
            metric_values = combined_df[csv_field].dropna()

            if (
                len(metric_values) < 10
            ):  # Mínimo 10 jugadores para percentiles confiables
                logger.warning(
                    f"Muestra muy pequeña para percentiles: {len(metric_values)} jugadores"
                )
                return None

            # Calcular percentiles
            percentiles = {
                "p10": float(metric_values.quantile(0.10)),
                "p25": float(metric_values.quantile(0.25)),
                "p50": float(metric_values.quantile(0.50)),  # Mediana
                "p75": float(metric_values.quantile(0.75)),
                "p90": float(metric_values.quantile(0.90)),
                "sample_size": len(metric_values),
                "min": float(metric_values.min()),
                "max": float(metric_values.max()),
            }

            # Calcular percentil exacto del jugador si se proporciona player_value
            if player_value is not None:
                player_percentile = self._calculate_exact_percentile(
                    player_value, metric_values
                )
                percentiles["player_percentile"] = player_percentile
                logger.info(
                    f"Percentil del jugador: {player_percentile:.1f}% para valor {player_value}"
                )

            logger.info(
                f"Percentiles calculados para {metric} en {position}: "
                f"P50={percentiles['p50']:.2f}, P75={percentiles['p75']:.2f}, P90={percentiles['p90']:.2f}"
            )

            return percentiles

        except Exception as e:
            logger.error(
                f"Error calculando percentiles para {metric} en {position}: {e}"
            )
            return None

    def _calculate_exact_percentile(self, player_value: float, all_values) -> float:
        """
        Calcula el percentil exacto de un jugador basado en todos los valores de la métrica.

        Args:
            player_value: Valor del jugador
            all_values: Serie pandas con todos los valores de la métrica

        Returns:
            float: Percentil exacto (0.0-100.0)
        """
        try:
            # Contar cuántos jugadores están por debajo del valor del jugador
            values_below = (all_values <= player_value).sum()
            total_players = len(all_values)

            # Calcular percentil: (jugadores por debajo / total) * 100
            percentile = (values_below / total_players) * 100

            # Limitar entre 0.1% y 99.9% para evitar extremos
            return max(0.1, min(99.9, percentile))

        except Exception as e:
            logger.warning(f"Error calculating exact percentile: {e}")
            return 50.0  # Retornar mediana como fallback

    def clear_cache(self):
        """Limpia el cache de datos."""
        self.cached_data.clear()
        logger.info("Cache de CSV Stats Controller limpiado")

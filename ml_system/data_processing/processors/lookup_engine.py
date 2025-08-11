#!/usr/bin/env python3
"""
LookupEngine - Motor de búsqueda O(1) para CSVs procesados
Sistema de búsqueda ultrarrápida con cache inteligente y índices optimizados.

Este módulo implementa el sistema final de búsquedas instantáneas:
1. Indices HashMap O(1) para jugadores, temporadas, posiciones
2. Cache LRU inteligente con invalidación automática
3. Búsquedas fuzzy con aproximación para typos
4. Integración perfecta con BatchProcessor y SeasonMonitor
5. Soporte completo para el sistema de CSVs duales (RAW + PROCESSED)

Arquitectura de rendimiento extremo sin duplicar funcionalidad.

Autor: Proyecto Fin de Máster - Python Aplicado al Deporte
Fecha: Agosto 2025
"""

import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Configurar path del proyecto
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import numpy as np
import pandas as pd

# Importar utilidades consolidadas
from ml_system.deployment.utils.script_utils import (
    format_execution_time,
    print_header,
    setup_analysis_logging,
)

# Importar otros preprocessors del sistema
from .batch_processor import BatchProcessor
from .season_monitor import SeasonMonitor

logger = logging.getLogger(__name__)

# Configuración de cache global
CACHE_CONFIG = {
    "max_size": 10000,  # Máximo items en cache LRU
    "ttl_hours": 24,  # TTL por defecto
    "fuzzy_threshold": 0.8,  # Threshold para fuzzy matching
}


class LookupEngine:
    """
    Motor de búsqueda O(1) que proporciona acceso instantáneo a CSVs procesados.

    Características:
    - Búsquedas HashMap O(1) por jugador, temporada, posición
    - Cache LRU con invalidación inteligente
    - Fuzzy matching para nombres con typos
    - Integración con BatchProcessor/SeasonMonitor existentes
    - Soporte CSV dual (RAW + PROCESSED)
    """

    def __init__(self, max_cache_size: int = 10000):
        """
        Inicializa LookupEngine con indices optimizados.

        Args:
            max_cache_size: Tamaño máximo del cache LRU
        """
        # Configuración
        self.max_cache_size = max_cache_size
        self.project_root = project_root
        self.processed_dir = self.project_root / "data" / "thai_league_processed"

        # Integración con otros preprocessors (NO duplicar)
        self.batch_processor = BatchProcessor()
        self.season_monitor = SeasonMonitor()

        # Índices HashMap O(1)
        self.player_index = {}  # player_name -> [records]
        self.season_index = {}  # season -> DataFrame
        self.position_index = {}  # position -> [player_names]
        self.team_index = {}  # team -> [player_names]

        # Cache de consultas frecuentes
        self.query_cache = {}
        self.cache_timestamps = {}

        # Metadatos de indexación
        self.index_metadata = {
            "last_indexed": None,
            "total_records": 0,
            "total_players": 0,
            "available_seasons": [],
            "index_version": "1.0",
        }

        # Configurar logging
        self.logger = setup_analysis_logging("lookup_engine")

        logger.info("🔍 LookupEngine inicializado con cache LRU optimizado")

        # Inicializar índices automáticamente
        self._initialize_indexes()

    def lookup_player_instantly(
        self, player_name: str, fuzzy: bool = True, season_filter: str = None
    ) -> Dict[str, Any]:
        """
        Búsqueda instantánea O(1) de un jugador específico.

        Args:
            player_name: Nombre del jugador a buscar
            fuzzy: Si activar búsqueda fuzzy para typos
            season_filter: Filtrar por temporada específica (opcional)

        Returns:
            Dict con datos del jugador y estadísticas
        """
        try:
            start_time = datetime.now()
            cache_key = f"player_{player_name}_{season_filter}_{fuzzy}"

            # Verificar cache primero
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                self.logger.debug(f"⚡ Cache hit para {player_name}")
                return {
                    "success": True,
                    "player": player_name,
                    "data": cached_result,
                    "source": "cache",
                    "lookup_time_ms": format_execution_time(start_time, unit="ms"),
                }

            # Búsqueda directa en índice O(1)
            exact_matches = self.player_index.get(player_name, [])

            # Si no hay match exacto y fuzzy está activado
            if not exact_matches and fuzzy:
                fuzzy_matches = self._fuzzy_player_search(player_name)
                if fuzzy_matches:
                    exact_matches = self.player_index.get(fuzzy_matches[0][0], [])
                    self.logger.info(
                        f"🔍 Fuzzy match: '{player_name}' → '{fuzzy_matches[0][0]}'"
                    )

            if not exact_matches:
                return {
                    "success": False,
                    "player": player_name,
                    "error": "Jugador no encontrado",
                    "suggestions": self._get_player_suggestions(player_name),
                    "lookup_time_ms": format_execution_time(start_time, unit="ms"),
                }

            # Filtrar por temporada si se especifica
            if season_filter:
                exact_matches = [
                    r for r in exact_matches if r.get("season") == season_filter
                ]

            # Procesar datos del jugador
            player_data = self._process_player_data(exact_matches, player_name)

            # Guardar en cache
            self._save_to_cache(cache_key, player_data)

            result = {
                "success": True,
                "player": player_name,
                "data": player_data,
                "source": "index",
                "lookup_time_ms": format_execution_time(start_time, unit="ms"),
            }

            return result

        except Exception as e:
            self.logger.error(f"Error en lookup de {player_name}: {e}")
            return {
                "success": False,
                "player": player_name,
                "error": str(e),
                "lookup_time_ms": format_execution_time(start_time, unit="ms"),
            }

    def lookup_season_instantly(
        self, season: str, include_stats: bool = True
    ) -> Dict[str, Any]:
        """
        Búsqueda instantánea O(1) de temporada completa.

        Args:
            season: Temporada a buscar
            include_stats: Si incluir estadísticas agregadas

        Returns:
            Dict con DataFrame de la temporada y estadísticas
        """
        try:
            start_time = datetime.now()
            cache_key = f"season_{season}_{include_stats}"

            # Verificar cache
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                self.logger.debug(f"⚡ Cache hit para temporada {season}")
                return {
                    "success": True,
                    "season": season,
                    "data": cached_result,
                    "source": "cache",
                    "lookup_time_ms": format_execution_time(start_time, unit="ms"),
                }

            # Búsqueda O(1) en índice de temporadas
            season_df = self.season_index.get(season)

            if season_df is None:
                return {
                    "success": False,
                    "season": season,
                    "error": "Temporada no encontrada",
                    "available_seasons": list(self.season_index.keys()),
                    "lookup_time_ms": format_execution_time(start_time, unit="ms"),
                }

            result_data = {
                "dataframe": season_df,
                "records_count": len(season_df),
                "columns_count": len(season_df.columns),
                "unique_players": (
                    season_df["Player"].nunique()
                    if "Player" in season_df.columns
                    else 0
                ),
                "date_range": {
                    "season": season,
                    "processed_date": (
                        season_df.get("processing_date", [None]).iloc[0]
                        if "processing_date" in season_df.columns and len(season_df) > 0
                        else None
                    ),
                },
            }

            # Incluir estadísticas agregadas si se solicita
            if include_stats:
                result_data["stats"] = self._calculate_season_stats(season_df)

            # Guardar en cache
            self._save_to_cache(cache_key, result_data)

            return {
                "success": True,
                "season": season,
                "data": result_data,
                "source": "index",
                "lookup_time_ms": format_execution_time(start_time, unit="ms"),
            }

        except Exception as e:
            self.logger.error(f"Error en lookup de temporada {season}: {e}")
            return {
                "success": False,
                "season": season,
                "error": str(e),
                "lookup_time_ms": format_execution_time(start_time, unit="ms"),
            }

    def lookup_by_position_instantly(
        self, position: str, season_filter: str = None, limit: int = 100
    ) -> Dict[str, Any]:
        """
        Búsqueda instantánea O(1) por posición.

        Args:
            position: Posición a buscar
            season_filter: Filtrar por temporada específica
            limit: Límite de resultados

        Returns:
            Dict con jugadores de la posición especificada
        """
        try:
            start_time = datetime.now()
            cache_key = f"position_{position}_{season_filter}_{limit}"

            # Verificar cache
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                return {
                    "success": True,
                    "position": position,
                    "data": cached_result,
                    "source": "cache",
                    "lookup_time_ms": format_execution_time(start_time, unit="ms"),
                }

            # Búsqueda O(1) en índice de posiciones
            player_names = self.position_index.get(position, [])

            if not player_names:
                return {
                    "success": False,
                    "position": position,
                    "error": "Posición no encontrada",
                    "available_positions": list(self.position_index.keys()),
                    "lookup_time_ms": format_execution_time(start_time, unit="ms"),
                }

            # Obtener datos de jugadores
            position_players = []
            for player_name in player_names[:limit]:
                player_records = self.player_index.get(player_name, [])

                # Filtrar por temporada si se especifica
                if season_filter:
                    player_records = [
                        r for r in player_records if r.get("season") == season_filter
                    ]

                if player_records:
                    # Tomar el record más reciente o promedio
                    player_summary = self._create_player_summary(
                        player_records, player_name
                    )
                    position_players.append(player_summary)

            result_data = {
                "position": position,
                "total_players": len(position_players),
                "players": position_players,
                "season_filter": season_filter,
            }

            # Guardar en cache
            self._save_to_cache(cache_key, result_data)

            return {
                "success": True,
                "position": position,
                "data": result_data,
                "source": "index",
                "lookup_time_ms": format_execution_time(start_time, unit="ms"),
            }

        except Exception as e:
            self.logger.error(f"Error en lookup de posición {position}: {e}")
            return {
                "success": False,
                "position": position,
                "error": str(e),
                "lookup_time_ms": format_execution_time(start_time, unit="ms"),
            }

    def search_players_advanced(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Búsqueda avanzada combinando múltiples criterios.

        Args:
            query: Dict con criterios de búsqueda
                   {"name": str, "position": str, "age_range": [min, max],
                    "season": str, "min_minutes": int, etc.}

        Returns:
            Dict con resultados de búsqueda avanzada
        """
        try:
            start_time = datetime.now()
            cache_key = f"advanced_{hash(str(sorted(query.items())))}"

            # Verificar cache
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                return {
                    "success": True,
                    "query": query,
                    "data": cached_result,
                    "source": "cache",
                    "lookup_time_ms": format_execution_time(start_time, unit="ms"),
                }

            # Ejecutar búsqueda avanzada
            matching_players = []

            # Determinar estrategia de búsqueda basada en query
            if "position" in query:
                # Comenzar con jugadores de posición específica
                candidate_players = self.position_index.get(query["position"], [])
            else:
                # Usar todos los jugadores (menos eficiente)
                candidate_players = list(self.player_index.keys())

            # Filtrar candidatos por criterios
            for player_name in candidate_players:
                player_records = self.player_index.get(player_name, [])

                # Aplicar filtros
                filtered_records = self._apply_query_filters(player_records, query)

                if filtered_records:
                    player_summary = self._create_player_summary(
                        filtered_records, player_name
                    )
                    matching_players.append(player_summary)

            # Ordenar resultados (por defecto por minutos jugados)
            sort_key = query.get("sort_by", "minutes_played")
            reverse_sort = query.get("sort_desc", True)

            try:
                matching_players.sort(
                    key=lambda x: x.get(sort_key, 0) or 0, reverse=reverse_sort
                )
            except (KeyError, TypeError):
                # Fallback a orden por nombre
                matching_players.sort(key=lambda x: x.get("player_name", ""))

            # Aplicar límite
            limit = query.get("limit", 100)
            matching_players = matching_players[:limit]

            result_data = {
                "query_criteria": query,
                "total_matches": len(matching_players),
                "players": matching_players,
                "execution_strategy": (
                    "position_filtered" if "position" in query else "full_scan"
                ),
            }

            # Guardar en cache
            self._save_to_cache(cache_key, result_data)

            return {
                "success": True,
                "query": query,
                "data": result_data,
                "source": "index",
                "lookup_time_ms": format_execution_time(start_time, unit="ms"),
            }

        except Exception as e:
            self.logger.error(f"Error en búsqueda avanzada: {e}")
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "lookup_time_ms": format_execution_time(start_time, unit="ms"),
            }

    def rebuild_indexes(self, force: bool = False) -> Dict[str, Any]:
        """
        Reconstruye todos los índices desde CSVs procesados.

        Args:
            force: Si forzar reconstrucción incluso si están actualizados

        Returns:
            Dict con resultado de la reconstrucción
        """
        try:
            start_time = datetime.now()
            print_header("🔧 RECONSTRUCCIÓN DE ÍNDICES LOOKUP ENGINE", "=", 70)

            self.logger.info("Iniciando reconstrucción de índices")

            # Verificar si necesita reconstrucción
            if not force and not self._indexes_need_rebuild():
                self.logger.info("⚡ Índices actualizados, omitiendo reconstrucción")
                return {
                    "success": True,
                    "message": "Índices ya actualizados",
                    "rebuild_time_ms": format_execution_time(start_time, unit="ms"),
                    "skipped": True,
                }

            # Limpiar índices existentes
            self._clear_indexes()

            # Reconstruir desde archivos procesados
            rebuild_stats = {
                "files_processed": 0,
                "records_indexed": 0,
                "players_indexed": 0,
                "seasons_indexed": 0,
                "errors": [],
            }

            # Procesar cada archivo CSV procesado
            for season_file in self.processed_dir.glob("processed_*.csv"):
                try:
                    self.logger.info(f"📊 Indexando {season_file.name}")

                    # Cargar CSV
                    df = pd.read_csv(season_file)
                    season = self._extract_season_from_filename(season_file.name)

                    # Indexar temporada
                    self.season_index[season] = df

                    # Indexar por jugador
                    for idx, row in df.iterrows():
                        player_name = row.get("Player", "")
                        if player_name:
                            if player_name not in self.player_index:
                                self.player_index[player_name] = []

                            # Convertir row a dict y añadir metadatos
                            player_record = row.to_dict()
                            player_record["_season"] = season
                            player_record["_file_source"] = season_file.name

                            self.player_index[player_name].append(player_record)

                            # Indexar por posición
                            position = row.get("Primary position", "")
                            if position:
                                if position not in self.position_index:
                                    self.position_index[position] = []
                                if player_name not in self.position_index[position]:
                                    self.position_index[position].append(player_name)

                            # Indexar por equipo (si existe)
                            team = row.get("Team", "")
                            if team:
                                if team not in self.team_index:
                                    self.team_index[team] = []
                                if player_name not in self.team_index[team]:
                                    self.team_index[team].append(player_name)

                    rebuild_stats["files_processed"] += 1
                    rebuild_stats["records_indexed"] += len(df)
                    rebuild_stats["seasons_indexed"] += 1

                    self.logger.info(f"✅ {season}: {len(df)} registros indexados")

                except Exception as e:
                    error_msg = f"Error indexando {season_file.name}: {e}"
                    rebuild_stats["errors"].append(error_msg)
                    self.logger.error(error_msg)

            rebuild_stats["players_indexed"] = len(self.player_index)

            # Actualizar metadatos
            self._update_index_metadata(rebuild_stats)

            # Limpiar cache (ya no válido)
            self._clear_cache()

            execution_time = format_execution_time(start_time)

            # Mostrar resumen
            print_header("✅ RECONSTRUCCIÓN COMPLETADA", "=", 70)
            print(f"⏱️  Tiempo total: {execution_time}")
            print(f"📁 Archivos procesados: {rebuild_stats['files_processed']}")
            print(f"📊 Registros indexados: {rebuild_stats['records_indexed']:,}")
            print(f"👥 Jugadores únicos: {rebuild_stats['players_indexed']:,}")
            print(f"⚽ Temporadas: {rebuild_stats['seasons_indexed']}")

            if rebuild_stats["errors"]:
                print(f"❌ Errores: {len(rebuild_stats['errors'])}")
                for error in rebuild_stats["errors"]:
                    print(f"   • {error}")

            return {
                "success": True,
                "rebuild_stats": rebuild_stats,
                "rebuild_time_ms": format_execution_time(start_time, unit="ms"),
                "execution_time": execution_time,
            }

        except Exception as e:
            self.logger.error(f"Error crítico en reconstrucción de índices: {e}")
            return {
                "success": False,
                "error": str(e),
                "rebuild_time_ms": format_execution_time(start_time, unit="ms"),
            }

    def get_engine_status(self) -> Dict[str, Any]:
        """
        Obtiene estado completo del LookupEngine.

        Returns:
            Dict con estadísticas y estado del motor
        """
        try:
            status = {
                "engine_info": {
                    "version": "1.0",
                    "cache_size": len(self.query_cache),
                    "max_cache_size": self.max_cache_size,
                    "cache_hit_ratio": self._calculate_cache_hit_ratio(),
                },
                "indexes": {
                    "players_indexed": len(self.player_index),
                    "seasons_indexed": len(self.season_index),
                    "positions_indexed": len(self.position_index),
                    "teams_indexed": len(self.team_index),
                },
                "metadata": self.index_metadata,
                "cache_health": {
                    "active_entries": len(self.query_cache),
                    "expired_entries": len(
                        [
                            k
                            for k, v in self.cache_timestamps.items()
                            if self._is_cache_expired(k)
                        ]
                    ),
                    "memory_usage_estimate": self._estimate_cache_memory(),
                },
                "performance": {
                    "avg_lookup_time_ms": self._get_average_lookup_time(),
                    "total_queries": getattr(self, "_total_queries", 0),
                    "cache_hits": getattr(self, "_cache_hits", 0),
                },
            }

            return status

        except Exception as e:
            self.logger.error(f"Error obteniendo estado del engine: {e}")
            return {"error": str(e)}

    # Métodos privados de implementación

    def _initialize_indexes(self):
        """Inicializa índices automáticamente al crear el engine."""
        try:
            self.logger.info("🔄 Inicializando índices automáticamente")

            # Verificar si existen archivos procesados
            processed_files = list(self.processed_dir.glob("processed_*.csv"))

            if not processed_files:
                self.logger.warning("⚠️ No se encontraron archivos procesados")
                self.logger.info("💡 Ejecuta BatchProcessor primero para generar datos")
                return

            # Reconstruir índices automáticamente
            result = self.rebuild_indexes()

            if result["success"]:
                self.logger.info("✅ Índices inicializados correctamente")
            else:
                self.logger.error("❌ Error inicializando índices")

        except Exception as e:
            self.logger.error(f"Error en inicialización automática: {e}")

    def _fuzzy_player_search(
        self, query: str, threshold: float = 0.8
    ) -> List[Tuple[str, float]]:
        """Búsqueda fuzzy para nombres con typos."""
        try:
            from difflib import SequenceMatcher

            matches = []
            query_lower = query.lower()

            for player_name in self.player_index.keys():
                similarity = SequenceMatcher(
                    None, query_lower, player_name.lower()
                ).ratio()

                if similarity >= threshold:
                    matches.append((player_name, similarity))

            # Ordenar por similitud descendente
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[:5]  # Top 5 matches

        except ImportError:
            self.logger.warning("difflib no disponible, fuzzy search deshabilitado")
            return []
        except Exception as e:
            self.logger.error(f"Error en fuzzy search: {e}")
            return []

    def _get_player_suggestions(self, query: str) -> List[str]:
        """Obtiene sugerencias de jugadores similares."""
        try:
            suggestions = []
            query_lower = query.lower()

            # Sugerencias por coincidencias parciales
            for player_name in self.player_index.keys():
                if query_lower in player_name.lower() or player_name.lower().startswith(
                    query_lower
                ):
                    suggestions.append(player_name)

                if len(suggestions) >= 5:
                    break

            return suggestions

        except Exception as e:
            self.logger.error(f"Error obteniendo sugerencias: {e}")
            return []

    def _process_player_data(
        self, records: List[Dict], player_name: str
    ) -> Dict[str, Any]:
        """Procesa datos de jugador desde múltiples registros."""
        try:
            if not records:
                return {}

            # Si solo hay un registro, devolverlo directamente
            if len(records) == 1:
                return {
                    "player_name": player_name,
                    "total_records": 1,
                    "seasons": [records[0].get("_season", "unknown")],
                    "latest_record": records[0],
                    "career_summary": records[0],
                }

            # Múltiples registros - crear resumen de carrera
            seasons = list(set(r.get("_season", "unknown") for r in records))
            latest_record = max(records, key=lambda x: x.get("_season", ""))

            # Calcular promedios de métricas numéricas
            career_summary = {"player_name": player_name}
            numeric_fields = []

            for field in records[0].keys():
                if field.startswith("_"):
                    continue

                # Intentar calcular promedio para campos numéricos
                try:
                    values = [r.get(field) for r in records if r.get(field) is not None]
                    if values and all(isinstance(v, (int, float)) for v in values):
                        career_summary[f"avg_{field}"] = np.mean(values)
                        career_summary[f"total_{field}"] = np.sum(values)
                        numeric_fields.append(field)
                except (TypeError, ValueError):
                    pass

            return {
                "player_name": player_name,
                "total_records": len(records),
                "seasons": sorted(seasons),
                "latest_record": latest_record,
                "career_summary": career_summary,
                "numeric_fields_averaged": numeric_fields,
            }

        except Exception as e:
            self.logger.error(f"Error procesando datos de {player_name}: {e}")
            return {"player_name": player_name, "error": str(e)}

    def _calculate_season_stats(self, season_df: pd.DataFrame) -> Dict[str, Any]:
        """Calcula estadísticas agregadas de temporada."""
        try:
            stats = {
                "basic_stats": {
                    "total_players": (
                        season_df["Player"].nunique()
                        if "Player" in season_df.columns
                        else 0
                    ),
                    "total_records": len(season_df),
                    "unique_positions": (
                        season_df["Primary position"].nunique()
                        if "Primary position" in season_df.columns
                        else 0
                    ),
                    "unique_teams": (
                        season_df["Team"].nunique()
                        if "Team" in season_df.columns
                        else 0
                    ),
                }
            }

            # Estadísticas por posición
            if "Primary position" in season_df.columns:
                position_stats = season_df["Primary position"].value_counts().to_dict()
                stats["position_distribution"] = position_stats

            # Promedios de métricas clave
            key_metrics = ["Age", "Minutes played", "Goals", "Assists"]
            numeric_stats = {}

            for metric in key_metrics:
                if metric in season_df.columns:
                    try:
                        values = pd.to_numeric(
                            season_df[metric], errors="coerce"
                        ).dropna()
                        if len(values) > 0:
                            numeric_stats[metric] = {
                                "mean": float(values.mean()),
                                "median": float(values.median()),
                                "std": float(values.std()),
                                "min": float(values.min()),
                                "max": float(values.max()),
                            }
                    except Exception as e:
                        self.logger.warning(
                            f"Error calculando stats para {metric}: {e}"
                        )

            stats["numeric_stats"] = numeric_stats

            return stats

        except Exception as e:
            self.logger.error(f"Error calculando estadísticas de temporada: {e}")
            return {"error": str(e)}

    def _create_player_summary(
        self, records: List[Dict], player_name: str
    ) -> Dict[str, Any]:
        """Crea resumen de jugador para resultados de búsqueda."""
        try:
            if not records:
                return {"player_name": player_name, "error": "No records"}

            # Usar el registro más reciente como base
            latest = max(records, key=lambda x: x.get("_season", ""))

            summary = {
                "player_name": player_name,
                "primary_position": latest.get("Primary position", ""),
                "age": latest.get("Age"),
                "team": latest.get("Team", ""),
                "season": latest.get("_season", ""),
                "minutes_played": latest.get("Minutes played"),
                "goals": latest.get("Goals"),
                "assists": latest.get("Assists"),
                "total_seasons": len(set(r.get("_season", "") for r in records)),
            }

            # Limpiar None values
            summary = {k: v for k, v in summary.items() if v is not None}

            return summary

        except Exception as e:
            self.logger.error(f"Error creando resumen de {player_name}: {e}")
            return {"player_name": player_name, "error": str(e)}

    def _apply_query_filters(
        self, records: List[Dict], query: Dict[str, Any]
    ) -> List[Dict]:
        """Aplica filtros de query avanzada a registros."""
        try:
            filtered = records

            # Filtro por nombre
            if "name" in query:
                name_query = query["name"].lower()
                filtered = [
                    r for r in filtered if name_query in r.get("Player", "").lower()
                ]

            # Filtro por temporada
            if "season" in query:
                filtered = [r for r in filtered if r.get("_season") == query["season"]]

            # Filtro por rango de edad
            if "age_range" in query:
                min_age, max_age = query["age_range"]
                filtered = [
                    r for r in filtered if min_age <= r.get("Age", 0) <= max_age
                ]

            # Filtro por minutos mínimos
            if "min_minutes" in query:
                min_minutes = query["min_minutes"]
                filtered = [
                    r for r in filtered if r.get("Minutes played", 0) >= min_minutes
                ]

            # Filtro por equipo
            if "team" in query:
                team_query = query["team"].lower()
                filtered = [
                    r for r in filtered if team_query in r.get("Team", "").lower()
                ]

            return filtered

        except Exception as e:
            self.logger.error(f"Error aplicando filtros: {e}")
            return records

    def _get_from_cache(self, cache_key: str) -> Any:
        """Obtiene item del cache con validación TTL."""
        try:
            if cache_key not in self.query_cache:
                return None

            if self._is_cache_expired(cache_key):
                self._remove_from_cache(cache_key)
                return None

            # Estadísticas
            if hasattr(self, "_cache_hits"):
                self._cache_hits += 1
            else:
                self._cache_hits = 1

            return self.query_cache[cache_key]

        except Exception as e:
            self.logger.error(f"Error obteniendo cache {cache_key}: {e}")
            return None

    def _save_to_cache(self, cache_key: str, data: Any):
        """Guarda item en cache con gestión LRU."""
        try:
            # Verificar límite de cache
            if len(self.query_cache) >= self.max_cache_size:
                self._evict_lru_items()

            self.query_cache[cache_key] = data
            self.cache_timestamps[cache_key] = datetime.now()

        except Exception as e:
            self.logger.error(f"Error guardando en cache {cache_key}: {e}")

    def _is_cache_expired(self, cache_key: str) -> bool:
        """Verifica si un item del cache ha expirado."""
        try:
            if cache_key not in self.cache_timestamps:
                return True

            cache_time = self.cache_timestamps[cache_key]
            ttl_hours = CACHE_CONFIG["ttl_hours"]

            return datetime.now() - cache_time > timedelta(hours=ttl_hours)

        except Exception as e:
            self.logger.error(f"Error verificando expiración {cache_key}: {e}")
            return True

    def _remove_from_cache(self, cache_key: str):
        """Elimina item específico del cache."""
        self.query_cache.pop(cache_key, None)
        self.cache_timestamps.pop(cache_key, None)

    def _evict_lru_items(self):
        """Elimina items menos usados del cache."""
        try:
            # Eliminar 25% más antiguos
            items_to_remove = max(1, len(self.query_cache) // 4)

            # Ordenar por timestamp
            sorted_items = sorted(self.cache_timestamps.items(), key=lambda x: x[1])

            for cache_key, _ in sorted_items[:items_to_remove]:
                self._remove_from_cache(cache_key)

            self.logger.debug(f"🧹 Cache LRU: eliminados {items_to_remove} items")

        except Exception as e:
            self.logger.error(f"Error en eviction LRU: {e}")

    def _clear_cache(self):
        """Limpia completamente el cache."""
        self.query_cache.clear()
        self.cache_timestamps.clear()
        self.logger.info("🧹 Cache completamente limpio")

    def _clear_indexes(self):
        """Limpia todos los índices."""
        self.player_index.clear()
        self.season_index.clear()
        self.position_index.clear()
        self.team_index.clear()
        self.logger.info("🧹 Índices limpiados")

    def _indexes_need_rebuild(self) -> bool:
        """Determina si los índices necesitan reconstrucción."""
        try:
            # Si no hay metadatos, necesita rebuild
            if not self.index_metadata.get("last_indexed"):
                return True

            # Verificar archivos más recientes que último rebuild
            last_indexed = datetime.fromisoformat(self.index_metadata["last_indexed"])

            for season_file in self.processed_dir.glob("processed_*.csv"):
                file_time = datetime.fromtimestamp(season_file.stat().st_mtime)
                if file_time > last_indexed:
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Error verificando necesidad de rebuild: {e}")
            return True

    def _extract_season_from_filename(self, filename: str) -> str:
        """Extrae temporada del nombre de archivo."""
        try:
            # processed_2023-24.csv → 2023-24
            return filename.replace("processed_", "").replace(".csv", "")
        except Exception as e:
            self.logger.error(f"Error extrayendo temporada de {filename}: {e}")
            return "unknown"

    def _update_index_metadata(self, rebuild_stats: Dict):
        """Actualiza metadatos de índices."""
        try:
            self.index_metadata.update(
                {
                    "last_indexed": datetime.now().isoformat(),
                    "total_records": rebuild_stats["records_indexed"],
                    "total_players": rebuild_stats["players_indexed"],
                    "available_seasons": list(self.season_index.keys()),
                    "files_processed": rebuild_stats["files_processed"],
                    "last_rebuild_errors": rebuild_stats["errors"],
                }
            )
        except Exception as e:
            self.logger.error(f"Error actualizando metadatos: {e}")

    def _calculate_cache_hit_ratio(self) -> float:
        """Calcula ratio de cache hits."""
        try:
            total_queries = getattr(self, "_total_queries", 0)
            cache_hits = getattr(self, "_cache_hits", 0)

            if total_queries == 0:
                return 0.0

            return cache_hits / total_queries

        except Exception as e:
            return 0.0

    def _estimate_cache_memory(self) -> str:
        """Estima uso de memoria del cache."""
        try:
            import sys

            total_size = sys.getsizeof(self.query_cache)
            for key, value in self.query_cache.items():
                total_size += sys.getsizeof(key) + sys.getsizeof(value)

            # Convertir a MB
            size_mb = total_size / (1024 * 1024)
            return f"{size_mb:.2f} MB"

        except Exception as e:
            return "Unknown"

    def _get_average_lookup_time(self) -> float:
        """Obtiene tiempo promedio de lookup."""
        # Placeholder - implementar con métricas reales
        return 0.0


# Funciones de conveniencia para uso directo
def lookup_player(
    player_name: str, season: str = None, fuzzy: bool = True
) -> Dict[str, Any]:
    """
    Función de conveniencia para búsqueda instantánea de jugador.

    Args:
        player_name: Nombre del jugador
        season: Filtrar por temporada específica
        fuzzy: Activar búsqueda fuzzy

    Returns:
        Dict con resultados de búsqueda
    """
    engine = LookupEngine()
    return engine.lookup_player_instantly(
        player_name, fuzzy=fuzzy, season_filter=season
    )


def lookup_season(season: str, include_stats: bool = True) -> Dict[str, Any]:
    """
    Función de conveniencia para búsqueda instantánea de temporada.

    Args:
        season: Temporada a buscar
        include_stats: Si incluir estadísticas agregadas

    Returns:
        Dict con datos de temporada
    """
    engine = LookupEngine()
    return engine.lookup_season_instantly(season, include_stats=include_stats)


def search_by_position(
    position: str, season: str = None, limit: int = 100
) -> Dict[str, Any]:
    """
    Función de conveniencia para búsqueda por posición.

    Args:
        position: Posición a buscar
        season: Filtrar por temporada específica
        limit: Límite de resultados

    Returns:
        Dict con jugadores de la posición
    """
    engine = LookupEngine()
    return engine.lookup_by_position_instantly(
        position, season_filter=season, limit=limit
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="LookupEngine - Motor de búsqueda O(1)"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Reconstruir índices desde CSVs procesados",
    )
    parser.add_argument(
        "--status", action="store_true", help="Mostrar estado del motor de búsqueda"
    )
    parser.add_argument("--player", type=str, help="Buscar jugador específico")
    parser.add_argument("--season", type=str, help="Buscar temporada específica")
    parser.add_argument("--position", type=str, help="Buscar por posición")
    parser.add_argument(
        "--fuzzy", action="store_true", help="Activar búsqueda fuzzy (para --player)"
    )
    parser.add_argument("--limit", type=int, default=10, help="Límite de resultados")

    args = parser.parse_args()

    engine = LookupEngine()

    if args.status:
        print("🔍 Estado del LookupEngine:")
        status = engine.get_engine_status()
        if "error" not in status:
            print(f"   • Jugadores indexados: {status['indexes']['players_indexed']:,}")
            print(f"   • Temporadas indexadas: {status['indexes']['seasons_indexed']}")
            print(
                f"   • Cache activo: {status['cache_health']['active_entries']} entries"
            )
            print(
                f"   • Último rebuild: {status['metadata'].get('last_indexed', 'Nunca')}"
            )

    elif args.rebuild:
        print("🔧 Reconstruyendo índices...")
        result = engine.rebuild_indexes(force=True)
        if result["success"]:
            print("✅ Índices reconstruidos exitosamente")
        else:
            print(f"❌ Error: {result['error']}")

    elif args.player:
        print(f"🔍 Buscando jugador: {args.player}")
        result = lookup_player(args.player, args.season, args.fuzzy)

        if result["success"]:
            data = result["data"]
            print(f"✅ Encontrado: {data['player_name']}")
            print(f"   • Temporadas: {len(data.get('seasons', []))}")
            print(f"   • Registros: {data.get('total_records', 0)}")
            print(f"   • Tiempo: {result['lookup_time_ms']}")
        else:
            print(f"❌ No encontrado: {result['error']}")
            if result.get("suggestions"):
                print(f"   💡 Sugerencias: {', '.join(result['suggestions'])}")

    elif args.season:
        print(f"🔍 Buscando temporada: {args.season}")
        result = lookup_season(args.season)

        if result["success"]:
            data = result["data"]
            print(f"✅ Temporada encontrada:")
            print(f"   • Registros: {data['records_count']:,}")
            print(f"   • Jugadores únicos: {data['unique_players']:,}")
            print(f"   • Tiempo: {result['lookup_time_ms']}")
        else:
            print(f"❌ Temporada no encontrada: {result['error']}")
            if result.get("available_seasons"):
                print(f"   📅 Disponibles: {', '.join(result['available_seasons'])}")

    elif args.position:
        print(f"🔍 Buscando posición: {args.position}")
        result = search_by_position(args.position, args.season, args.limit)

        if result["success"]:
            data = result["data"]
            print(f"✅ Posición encontrada:")
            print(f"   • Jugadores: {data['total_players']}")
            print(f"   • Tiempo: {result['lookup_time_ms']}")

            # Mostrar algunos jugadores
            for i, player in enumerate(data["players"][:5], 1):
                print(
                    f"   {i}. {player['player_name']} ({player.get('age', '?')} años)"
                )
        else:
            print(f"❌ Posición no encontrada: {result['error']}")

    else:
        print("🔍 LookupEngine - Motor de búsqueda O(1)")
        print(
            "Uso: --rebuild, --status, --player NOMBRE, --season TEMPORADA, --position POSICION"
        )
        print("Ejemplo: python lookup_engine.py --player 'Messi' --fuzzy")

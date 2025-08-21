"""
Thai League Controller - Sistema de extracción y procesamiento de datos
Maneja la descarga, limpieza y matching de estadísticas de la liga tailandesa
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import pytz
import requests
from fuzzywuzzy import fuzz
from unidecode import unidecode

from config import DATABASE_PATH
from controllers.db import get_db_session
from models import (
    ImportStatus,
    Player,
    ProfessionalStats,
    ThaiLeagueSeason,
    User,
    UserType,
)

logger = logging.getLogger(__name__)


class ThaiLeagueController:
    """
    Controlador principal para manejo de datos de la liga tailandesa.
    Incluye descarga, procesamiento, matching y actualización de estadísticas.
    """

    # URLs base del repositorio GitHub
    GITHUB_BASE_URL = (
        "https://raw.githubusercontent.com/griffisben/Wyscout_Prospect_Research"
    )
    COMMIT_HASH = "4931dedc4eb50af49dae6cb8f9a16f119c1aab1a"

    # Temporadas disponibles
    AVAILABLE_SEASONS = {
        "2020-21": "Thai League 1 20-21.csv",
        "2021-22": "Thai League 1 21-22.csv",
        "2022-23": "Thai League 1 22-23.csv",
        "2023-24": "Thai League 1 23-24.csv",
        "2024-25": "Thai League 1 24-25.csv",
    }

    # Mapping de columnas CSV a modelo de base de datos
    COLUMN_MAPPING = {
        # === INFORMACIÓN BÁSICA ===
        "Player": "player_name",
        "Full name": "full_name",
        "Wyscout id": "wyscout_id",
        "Team": "team",
        "Team within selected timeframe": "team_within_timeframe",
        "Team logo": "team_logo_url",
        "Competition": "competition",
        "Age": "age",
        "Birthday": "birthday",
        "Birth country": "birth_country",
        "Passport country": "passport_country",
        "Primary position": "primary_position",
        "Secondary position": "secondary_position",
        "Third position": "third_position",
        "Height": "height",
        "Weight": "weight",
        "Foot": "foot",
        "Matches played": "matches_played",
        "Minutes played": "minutes_played",
        "Market value": "market_value",
        # === RENDIMIENTO OFENSIVO ===
        "Goals": "goals",
        "Assists": "assists",
        "xG": "expected_goals",
        "xA": "expected_assists",
        "Goals per 90": "goals_per_90",
        "Assists per 90": "assists_per_90",
        "xG per 90": "xg_per_90",
        "xA per 90": "xa_per_90",
        "Shots": "shots",
        "Shots per 90": "shots_per_90",
        "Shots on target, %": "shots_on_target_pct",
        "Goal conversion, %": "goal_conversion_pct",
        "Touches in box per 90": "touches_in_box_per_90",
        "Shot assists per 90": "shot_assists_per_90",
        # === RENDIMIENTO DEFENSIVO ===
        "Successful defensive actions per 90": "defensive_actions_per_90",
        "Defensive duels per 90": "defensive_duels_per_90",
        "Defensive duels won, %": "defensive_duels_won_pct",
        "Aerial duels per 90": "aerial_duels_per_90",
        "Aerial duels won, %": "aerial_duels_won_pct",
        "Sliding tackles per 90": "sliding_tackles_per_90",
        "Interceptions per 90": "interceptions_per_90",
        # === PASES Y DISTRIBUCIÓN ===
        "Passes per 90": "passes_per_90",
        "Accurate passes, %": "pass_accuracy_pct",
        "Forward passes per 90": "forward_passes_per_90",
        "Accurate forward passes, %": "forward_passes_accuracy_pct",
        "Back passes per 90": "back_passes_per_90",
        "Accurate back passes, %": "back_passes_accuracy_pct",
        "Long passes per 90": "long_passes_per_90",
        "Accurate long passes, %": "long_passes_accuracy_pct",
        "Progressive passes per 90": "progressive_passes_per_90",
        "Accurate progressive passes, %": "progressive_passes_accuracy_pct",
        "Key passes per 90": "key_passes_per_90",
        # === DUELOS Y FÍSICO ===
        "Duels per 90": "duels_per_90",
        "Duels won, %": "duels_won_pct",
        "Offensive duels per 90": "offensive_duels_per_90",
        "Offensive duels won, %": "offensive_duels_won_pct",
        "Dribbles per 90": "dribbles_per_90",
        "Successful dribbles, %": "dribbles_success_pct",
        "Progressive runs per 90": "progressive_runs_per_90",
        # === DISCIPLINA ===
        "Yellow cards": "yellow_cards",
        "Red cards": "red_cards",
        "Yellow cards per 90": "yellow_cards_per_90",
        "Red cards per 90": "red_cards_per_90",
        "Fouls per 90": "fouls_per_90",
        "Fouls suffered per 90": "fouls_suffered_per_90",
    }

    def __init__(self):
        self.session_factory = get_db_session
        self.cache_dir = self._get_cache_directory()
        self._ensure_cache_directory()

        # Configurar timezone basado en entorno
        from config import DATABASE_PATH

        if DATABASE_PATH and "data/ballers_app.db" in str(DATABASE_PATH):
            # Entorno local/master - España
            self.timezone = pytz.timezone("Europe/Madrid")
        else:
            # Entorno producción - Tailandia
            self.timezone = pytz.timezone("Asia/Bangkok")

        # Inicializar el nuevo pipeline ETL modular (lazy loading)
        self._etl_controller = None

    def _get_current_datetime(self) -> datetime:
        """Obtiene datetime actual en el timezone configurado."""
        return datetime.now(self.timezone)

    def _get_cache_directory(self) -> Path:
        """
        Determina el directorio de cache según el entorno.

        Returns:
            Path del directorio de cache
        """
        if DATABASE_PATH and "data/ballers_app.db" in str(DATABASE_PATH):
            # Entorno local - usar directorio data/thai_league_cache
            return Path("data/thai_league_cache")
        else:
            # Entorno producción - usar directorio temporal
            import tempfile

            return Path(tempfile.gettempdir()) / "thai_league_cache"

    def _ensure_cache_directory(self):
        """Asegura que el directorio de cache existe."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_file_path(self, season: str) -> Path:
        """
        Obtiene la ruta del archivo de cache para una temporada.

        Args:
            season: Temporada en formato "2024-25"

        Returns:
            Path del archivo de cache
        """
        return self.cache_dir / f"thai_league_{season}.csv"

    def _is_cache_valid(self, season: str, current_hash: str) -> bool:
        """
        Verifica si el cache local es válido comparando con el hash actual.

        Args:
            season: Temporada en formato "2024-25"
            current_hash: Hash actual del contenido remoto

        Returns:
            True si el cache es válido
        """
        cache_file = self._get_cache_file_path(season)
        if not cache_file.exists():
            return False

        # Verificar hash almacenado vs actual
        with self.session_factory() as session:
            season_obj = (
                session.query(ThaiLeagueSeason)
                .filter(ThaiLeagueSeason.season == season)
                .first()
            )

            if not season_obj or not season_obj.file_hash:
                return False

            return season_obj.file_hash == current_hash

    def _save_to_cache(self, season: str, content: str, file_hash: str):
        """
        Guarda contenido CSV en cache local.

        Args:
            season: Temporada en formato "2024-25"
            content: Contenido CSV
            file_hash: Hash MD5 del contenido
        """
        try:
            cache_file = self._get_cache_file_path(season)
            cache_file.write_text(content, encoding="utf-8")

            # Actualizar hash en base de datos
            with self.session_factory() as session:
                season_obj = (
                    session.query(ThaiLeagueSeason)
                    .filter(ThaiLeagueSeason.season == season)
                    .first()
                )

                if not season_obj:
                    season_obj = ThaiLeagueSeason(season=season)
                    session.add(season_obj)

                season_obj.file_hash = file_hash
                season_obj.last_updated = datetime.now(timezone.utc)
                session.commit()

            logger.info(f"📁 CSV guardado en cache: {cache_file}")

        except Exception as e:
            logger.warning(f"⚠️ Error guardando cache para {season}: {str(e)}")

    def _load_from_cache(self, season: str) -> Optional[str]:
        """
        Carga contenido CSV desde cache local.

        Args:
            season: Temporada en formato "2024-25"

        Returns:
            Contenido CSV o None si no existe
        """
        try:
            cache_file = self._get_cache_file_path(season)
            if cache_file.exists():
                content = cache_file.read_text(encoding="utf-8")
                logger.info(f"📁 CSV cargado desde cache: {cache_file}")
                return content
            return None
        except Exception as e:
            logger.warning(f"⚠️ Error cargando cache para {season}: {str(e)}")
            return None

    def download_season_data(
        self, season: str
    ) -> Tuple[bool, Optional[pd.DataFrame], str]:
        """
        Descarga datos de una temporada específica desde GitHub con cache inteligente.

        Args:
            season: Temporada en formato "2024-25"

        Returns:
            Tuple[success, dataframe, message]
        """
        if season not in self.AVAILABLE_SEASONS:
            return False, None, f"Temporada {season} no disponible"

        filename = self.AVAILABLE_SEASONS[season]
        url = (
            f"{self.GITHUB_BASE_URL}/{self.COMMIT_HASH}/Main App/"
            f"{filename.replace(' ', '%20')}"
        )

        try:
            # Paso 1: Verificar si tenemos cache válido (sin descargar)
            logger.info(f"🔍 Verificando cache para temporada {season}...")
            cached_content = self._load_from_cache(season)

            # Paso 2: Si tenemos cache, verificar si es relativamente reciente
            if cached_content:
                with self.session_factory() as session:
                    season_obj = (
                        session.query(ThaiLeagueSeason)
                        .filter(ThaiLeagueSeason.season == season)
                        .first()
                    )

                    # Si el archivo fue actualizado en las últimas 24 horas, usar cache
                    if season_obj and season_obj.last_updated:
                        # Asegurar que ambos datetimes tienen timezone
                        now_utc = datetime.now(timezone.utc)
                        last_updated = season_obj.last_updated
                        if last_updated.tzinfo is None:
                            last_updated = last_updated.replace(tzinfo=timezone.utc)

                        if (now_utc - last_updated).days < 1:
                            logger.info(
                                f"⚡ Usando cache reciente para temporada {season}"
                            )
                            csv_content = StringIO(cached_content)
                            df = pd.read_csv(csv_content)
                            return True, df, f"Cache cargado: {len(df)} registros"

            # Paso 3: Descargar y actualizar cache
            logger.info(f"📥 Descargando datos para temporada {season} desde {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Guardar en cache para próximas consultas
            file_hash = self.calculate_file_hash(response.text)
            self._save_to_cache(season, response.text, file_hash)

            # Procesar CSV
            csv_content = StringIO(response.text)
            df = pd.read_csv(csv_content)

            logger.info(
                f"✅ Descarga exitosa: {len(df)} registros para temporada {season}"
            )
            return True, df, f"Descarga exitosa: {len(df)} registros"

        except requests.RequestException as e:
            # Fallback: intentar cargar desde cache aunque no sea válido
            cached_content = self._load_from_cache(season)
            if cached_content:
                logger.warning(f"⚠️ Error de red, usando cache obsoleto para {season}")
                csv_content = StringIO(cached_content)
                df = pd.read_csv(csv_content)
                return True, df, f"Cache obsoleto: {len(df)} registros (sin conexión)"

            error_msg = f"Error al descargar datos de {season}: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except pd.errors.EmptyDataError as e:
            error_msg = f"Archivo CSV vacío para temporada {season}: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Error inesperado al procesar {season}: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    def clean_and_normalize_data(self, df: pd.DataFrame, season: str) -> pd.DataFrame:
        """
        Limpia y normaliza los datos del CSV.

        Args:
            df: DataFrame con datos crudos
            season: Temporada para agregar a los datos

        Returns:
            DataFrame limpio y normalizado
        """
        logger.info(f"Iniciando limpieza de datos para temporada {season}")

        # Crear copia para no modificar el original
        clean_df = df.copy()

        # Añadir columna de temporada
        clean_df["season"] = season

        # Limpiar nombres de columnas (remover espacios extra, etc.)
        clean_df.columns = clean_df.columns.str.strip()

        # Normalizar nombres de jugadores
        if "Full name" in clean_df.columns:
            clean_df["Full name"] = clean_df["Full name"].apply(self._normalize_name)
        if "Player" in clean_df.columns:
            clean_df["Player"] = clean_df["Player"].apply(self._normalize_name)

        # Convertir tipos de datos
        numeric_columns = [
            "Age",
            "Matches played",
            "Minutes played",
            "Goals",
            "Assists",
            "Market value",
            "Defensive actions",
            "Shots",
            "Yellow cards",
            "Red cards",
        ]

        for col in numeric_columns:
            if col in clean_df.columns:
                clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce")

        # Convertir fechas de nacimiento
        if "Birthday" in clean_df.columns:
            clean_df["Birthday"] = pd.to_datetime(clean_df["Birthday"], errors="coerce")

        # Limpiar valores nulos y infinitos
        clean_df = clean_df.replace([float("inf"), float("-inf")], None)

        logger.info(f"Limpieza completada: {len(clean_df)} registros procesados")
        return clean_df

    def _normalize_name(self, name: Union[str, None]) -> Optional[str]:
        """
        Normaliza nombres para matching consistente.

        Args:
            name: Nombre a normalizar

        Returns:
            Nombre normalizado o None
        """
        if pd.isna(name) or not isinstance(name, str):
            return None

        # Remover acentos y caracteres especiales
        normalized = unidecode(name)

        # Convertir a minúsculas y remover espacios extra
        normalized = re.sub(r"\s+", " ", normalized.lower().strip())

        # Remover caracteres no alfabéticos excepto espacios y guiones
        normalized = re.sub(r"[^a-z\s\-]", "", normalized)

        return normalized if normalized else None

    def find_matching_players(
        self, df: pd.DataFrame, threshold: int = 85
    ) -> Dict[str, List[Dict]]:
        """
        Encuentra jugadores coincidentes usando fuzzy matching.

        Args:
            df: DataFrame con datos de jugadores
            threshold: Umbral de similitud (0-100)

        Returns:
            Diccionario con sugerencias de matching
        """
        logger.info(f"Iniciando matching de jugadores con threshold {threshold}")
        logger.info(f"📊 DataFrame recibido: {len(df)} registros")

        # Obtener jugadores profesionales existentes
        with self.session_factory() as session:
            existing_players = (
                session.query(Player, User)
                .join(User, Player.user_id == User.user_id)
                .filter(
                    Player.is_professional == True, User.user_type == UserType.player
                )
                .all()
            )

            logger.info(f"👥 Jugadores profesionales en BD: {len(existing_players)}")

        results = {
            "exact_matches": [],
            "fuzzy_matches": [],
            "no_matches": [],
            "multiple_matches": [],
        }

        for _, row in df.iterrows():
            full_name = row.get("Full name")
            wyscout_id = int(row.get("Wyscout id", 0))

            if not full_name:
                continue

            # Buscar matching exacto por WyscoutID
            exact_wyscout = self._find_by_wyscout_id(existing_players, wyscout_id)
            if exact_wyscout:
                results["exact_matches"].append(
                    {
                        "csv_player": full_name,
                        "wyscout_id": wyscout_id,
                        "matched_player": exact_wyscout,
                        "confidence": 100,
                        "match_type": "wyscout_id",
                    }
                )
                continue

            # Buscar matching exacto por nombre
            exact_name = self._find_by_exact_name(existing_players, full_name)
            if exact_name:
                results["exact_matches"].append(
                    {
                        "csv_player": full_name,
                        "wyscout_id": wyscout_id,
                        "matched_player": exact_name,
                        "confidence": 100,
                        "match_type": "exact_name",
                    }
                )
                continue

            # Buscar matching fuzzy
            fuzzy_matches = self._find_by_fuzzy_name(
                existing_players, full_name, threshold
            )

            if len(fuzzy_matches) == 1:
                results["fuzzy_matches"].append(
                    {
                        "csv_player": full_name,
                        "wyscout_id": wyscout_id,
                        "matched_player": fuzzy_matches[0]["player"],
                        "confidence": fuzzy_matches[0]["confidence"],
                        "match_type": "fuzzy_name",
                    }
                )
            elif len(fuzzy_matches) > 1:
                results["multiple_matches"].append(
                    {
                        "csv_player": full_name,
                        "wyscout_id": wyscout_id,
                        "candidates": fuzzy_matches,
                        "match_type": "multiple_fuzzy",
                    }
                )
            else:
                results["no_matches"].append(
                    {
                        "csv_player": full_name,
                        "wyscout_id": wyscout_id,
                        "match_type": "no_match",
                    }
                )

        logger.info(
            f"Matching completado: {len(results['exact_matches'])} exactos, "
            f"{len(results['fuzzy_matches'])} fuzzy, "
            f"{len(results['multiple_matches'])} múltiples, "
            f"{len(results['no_matches'])} sin match"
        )

        return results

    def _find_by_wyscout_id(
        self, players: List[Tuple[Player, User]], wyscout_id
    ) -> Optional[Dict]:
        """Busca jugador por WyscoutID exacto (maneja tanto str como int)."""
        if not wyscout_id:
            return None

        # Convertir a int para comparación consistente
        try:
            wyscout_id_int = int(wyscout_id) if wyscout_id else None
        except (ValueError, TypeError):
            return None

        if not wyscout_id_int:
            return None

        for player, user in players:
            try:
                player_wyscout_id_int = (
                    int(player.wyscout_id) if player.wyscout_id else None
                )
                if player_wyscout_id_int == wyscout_id_int:
                    return {
                        "player_id": player.player_id,
                        "user_id": user.user_id,
                        "name": user.name,
                        "wyscout_id": player.wyscout_id,
                    }
            except (ValueError, TypeError):
                continue
        return None

    def _find_by_exact_name(
        self, players: List[Tuple[Player, User]], name: str
    ) -> Optional[Dict]:
        """Busca jugador por nombre exacto."""
        normalized_name = self._normalize_name(name)
        if not normalized_name:
            return None

        for player, user in players:
            user_normalized = self._normalize_name(user.name)
            if user_normalized == normalized_name:
                return {
                    "player_id": player.player_id,
                    "user_id": user.user_id,
                    "name": user.name,
                    "wyscout_id": player.wyscout_id,
                }
        return None

    def _find_by_fuzzy_name(
        self, players: List[Tuple[Player, User]], name: str, threshold: int
    ) -> List[Dict]:
        """Busca jugadores por nombre usando fuzzy matching."""
        normalized_name = self._normalize_name(name)
        if not normalized_name:
            return []

        candidates = []
        for player, user in players:
            user_normalized = self._normalize_name(user.name)
            if not user_normalized:
                continue

            confidence = fuzz.ratio(normalized_name, user_normalized)
            if confidence >= threshold:
                candidates.append(
                    {
                        "player": {
                            "player_id": player.player_id,
                            "user_id": user.user_id,
                            "name": user.name,
                            "wyscout_id": player.wyscout_id,
                        },
                        "confidence": confidence,
                    }
                )

        # Ordenar por confianza descendente
        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        return candidates

    def calculate_file_hash(self, content: str) -> str:
        """
        Calcula hash MD5 del contenido para detectar cambios.

        Args:
            content: Contenido del archivo

        Returns:
            Hash MD5 del contenido
        """
        return hashlib.md5(content.encode("utf-8"), usedforsecurity=False).hexdigest()

    def get_season_status(self, season: str) -> Optional[ThaiLeagueSeason]:
        """
        Obtiene el estado actual de una temporada.

        Args:
            season: Temporada en formato "2024-25"

        Returns:
            Objeto ThaiLeagueSeason o None si no existe
        """
        with self.session_factory() as session:
            return (
                session.query(ThaiLeagueSeason)
                .filter(ThaiLeagueSeason.season == season)
                .first()
            )

    def create_or_update_season(self, season: str, **kwargs) -> ThaiLeagueSeason:
        """
        Crea o actualiza registro de temporada.

        Args:
            season: Temporada en formato "2024-25"
            **kwargs: Campos adicionales a actualizar

        Returns:
            Objeto ThaiLeagueSeason creado o actualizado
        """
        with self.session_factory() as session:
            season_obj = (
                session.query(ThaiLeagueSeason)
                .filter(ThaiLeagueSeason.season == season)
                .first()
            )

            if not season_obj:
                # Crear nueva temporada
                season_obj = ThaiLeagueSeason(season=season)
                session.add(season_obj)

            # Actualizar campos
            for key, value in kwargs.items():
                if hasattr(season_obj, key):
                    setattr(season_obj, key, value)

            session.commit()
            session.refresh(season_obj)
            return season_obj

    def import_season_data(
        self, season: str, df: pd.DataFrame, matching_results: Dict
    ) -> Tuple[bool, str, Dict]:
        """
        Importa datos de una temporada a la base de datos.

        Args:
            season: Temporada en formato "2024-25"
            df: DataFrame con datos limpios
            matching_results: Resultados del matching de jugadores

        Returns:
            Tuple[success, message, statistics]
        """
        logger.info(f"Iniciando importación de datos para temporada {season}")

        stats = {
            "total_records": len(df),
            "imported_records": 0,
            "matched_players": 0,
            "unmatched_players": 0,
            "errors": 0,
            "error_details": [],
        }

        try:
            with self.session_factory() as session:
                # Marcar temporada como en progreso
                season_obj = self.create_or_update_season(
                    season,
                    import_status=ImportStatus.in_progress,
                    last_import_attempt=datetime.now(timezone.utc),
                )
                session.commit()

                # Procesar matches exactos y fuzzy
                all_matches = (
                    matching_results["exact_matches"]
                    + matching_results["fuzzy_matches"]
                )

                for match in all_matches:
                    try:
                        # Buscar datos del jugador en el CSV
                        player_data = df[df["Full name"] == match["csv_player"]].iloc[0]

                        # Crear registro de estadísticas
                        prof_stats = self._create_professional_stats_record(
                            player_data, season, match["matched_player"]["player_id"]
                        )

                        # Verificar si ya existe para evitar duplicados
                        existing = (
                            session.query(ProfessionalStats)
                            .filter(
                                ProfessionalStats.player_id
                                == match["matched_player"]["player_id"],
                                ProfessionalStats.season == season,
                                ProfessionalStats.wyscout_id
                                == int(player_data.get("Wyscout id", 0)),
                            )
                            .first()
                        )

                        if existing:
                            # Actualizar registro existente
                            for field, value in prof_stats.items():
                                if hasattr(existing, field) and value is not None:
                                    setattr(existing, field, value)
                            logger.debug(
                                f"Actualizado jugador existente: {match['csv_player']}"
                            )
                        else:
                            # Crear nuevo registro
                            new_stats = ProfessionalStats(**prof_stats)
                            session.add(new_stats)
                            logger.debug(
                                f"Creado nuevo registro: {match['csv_player']}"
                            )

                        stats["imported_records"] += 1
                        stats["matched_players"] += 1

                        # Actualizar WyscoutID del jugador si no lo tiene
                        player = (
                            session.query(Player)
                            .filter(
                                Player.player_id == match["matched_player"]["player_id"]
                            )
                            .first()
                        )

                        if player and not player.wyscout_id:
                            player.wyscout_id = int(player_data.get("Wyscout id", 0))

                    except Exception as e:
                        error_msg = f"Error importando {match['csv_player']}: {str(e)}"
                        logger.error(error_msg)
                        stats["errors"] += 1
                        stats["error_details"].append(error_msg)

                # Contar jugadores sin match
                stats["unmatched_players"] = len(matching_results["no_matches"]) + len(
                    matching_results["multiple_matches"]
                )

                # Actualizar estadísticas de la temporada
                season_obj.update_import_stats(
                    total=stats["total_records"],
                    imported=stats["imported_records"],
                    matched=stats["matched_players"],
                    unmatched=stats["unmatched_players"],
                    errors=stats["errors"],
                )

                if stats["errors"] == 0:
                    season_obj.mark_completed()
                    message = (
                        f"Importación exitosa para {season}: "
                        f"{stats['imported_records']} registros"
                    )
                else:
                    season_obj.import_status = (
                        ImportStatus.completed
                    )  # Completado con errores
                    message = (
                        f"Importación completada con {stats['errors']} errores "
                        f"para {season}"
                    )

                session.commit()
                logger.info(message)
                return True, message, stats

        except Exception as e:
            error_msg = f"Error crítico importando temporada {season}: {str(e)}"
            logger.error(error_msg)

            # Marcar temporada como fallida
            try:
                with self.session_factory() as session:
                    season_obj = (
                        session.query(ThaiLeagueSeason)
                        .filter(ThaiLeagueSeason.season == season)
                        .first()
                    )
                    if season_obj:
                        season_obj.mark_failed(error_msg)
                        session.commit()
            except Exception as e:
                logging.warning(f"No se pudo actualizar estado de temporada: {e}")

            return False, error_msg, stats

    def _create_professional_stats_record(
        self, player_data: pd.Series, season: str, player_id: int
    ) -> Dict:
        """
        Crea diccionario con datos para ProfessionalStats.

        Args:
            player_data: Fila del DataFrame con datos del jugador
            season: Temporada
            player_id: ID del jugador en la base de datos

        Returns:
            Diccionario con datos mapeados para el modelo
        """
        record = {"player_id": player_id, "season": season}

        # Mapear columnas del CSV al modelo
        for csv_col, db_field in self.COLUMN_MAPPING.items():
            if csv_col in player_data.index:
                value = player_data[csv_col]

                # Convertir NaN a None
                if pd.isna(value):
                    value = None
                # Convertir fechas
                elif csv_col == "Birthday" and value is not None:
                    try:
                        if isinstance(value, str):
                            value = datetime.strptime(value, "%Y-%m-%d").date()
                        elif hasattr(value, "date"):
                            value = value.date()
                    except (ValueError, AttributeError):
                        value = None
                # Convertir números flotantes a enteros donde corresponde
                elif (
                    db_field
                    in [
                        "wyscout_id",
                        "age",
                        "height",
                        "weight",
                        "matches_played",
                        "minutes_played",
                        "goals",
                        "assists",
                        "shots",
                        "yellow_cards",
                        "red_cards",
                        "market_value",
                    ]
                    and value is not None
                ):
                    try:
                        value = int(float(value)) if not pd.isna(value) else None
                    except (ValueError, TypeError):
                        value = None

                record[db_field] = value

        # Lógica de fallback para campo team (requerido por el modelo)
        if not record.get("team") and record.get("team_within_timeframe"):
            record["team"] = record["team_within_timeframe"]
            logger.info(
                f"🔧 Usando team_within_timeframe como fallback para team: {record['team']}"
            )
        elif not record.get("team"):
            record["team"] = "Unknown Team"
            logger.warning(f"⚠️ Usando valor por defecto para team: {record['team']}")

        # Aplicar lógica inteligente de equipos
        record = self.process_team_data_with_intelligence(record)

        return record

    def get_player_stats(self, player_id: int) -> List[Dict]:
        """
        Obtiene estadísticas profesionales de un jugador específico.

        Args:
            player_id: ID del jugador en la base de datos

        Returns:
            Lista de diccionarios con estadísticas por temporada
        """
        try:
            with self.session_factory() as session:
                stats = (
                    session.query(ProfessionalStats)
                    .filter(ProfessionalStats.player_id == player_id)
                    .order_by(ProfessionalStats.season)
                    .all()
                )

                logger.info(f"🔍 Buscando estadísticas para player_id: {player_id}")
                logger.info(f"📊 Estadísticas encontradas: {len(stats)} registros")

                result = []
                for stat in stats:
                    stat_dict = {
                        # Información básica
                        "season": stat.season,
                        "team": stat.team,
                        "age": stat.age,
                        "matches_played": stat.matches_played,
                        "minutes_played": stat.minutes_played,
                        "goals": stat.goals,
                        "assists": stat.assists,
                        "market_value": stat.market_value,
                        # Rendimiento ofensivo (usando nombres correctos del modelo)
                        "shots": stat.shots,
                        "shots_per_90": stat.shots_per_90,
                        "shots_on_target_pct": stat.shots_on_target_pct,
                        "goal_conversion_pct": stat.goal_conversion_pct,
                        "goals_per_90": stat.goals_per_90,
                        "assists_per_90": stat.assists_per_90,
                        # Rendimiento defensivo
                        "defensive_actions_per_90": stat.defensive_actions_per_90,
                        "duels_won_pct": stat.duels_won_pct,
                        # Pases y distribución
                        "pass_accuracy_pct": stat.pass_accuracy_pct,
                        # Métricas avanzadas
                        "expected_goals": stat.expected_goals,
                        "expected_assists": stat.expected_assists,
                    }
                    result.append(stat_dict)
                    logger.info(
                        f"✅ Estadística procesada: {stat.season} - {stat.team}"
                    )

                logger.info(f"📈 Total estadísticas devueltas: {len(result)}")
                return result

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas del jugador {player_id}: {e}")
            return []

    def search_player_by_name(
        self, player_name: str, threshold: int = 75
    ) -> List[Dict]:
        """
        Busca jugadores por nombre en la base de datos de estadísticas profesionales.

        Args:
            player_name: Nombre del jugador a buscar
            threshold: Umbral de similitud para fuzzy matching (0-100)

        Returns:
            Lista de jugadores ordenada por confidence score
        """
        try:
            if not player_name or not player_name.strip():
                return []

            # Normalizar el nombre de búsqueda
            search_name = self._normalize_name(player_name.strip())
            if not search_name:
                return []

            with self.session_factory() as session:
                # Obtener jugadores únicos con su temporada más reciente
                subquery = (
                    session.query(
                        ProfessionalStats.wyscout_id,
                        ProfessionalStats.full_name,
                        ProfessionalStats.player_name,
                        ProfessionalStats.team,
                        ProfessionalStats.season,
                        ProfessionalStats.goals,
                        ProfessionalStats.assists,
                        ProfessionalStats.matches_played,
                        ProfessionalStats.primary_position,
                    )
                    .order_by(ProfessionalStats.season.desc())
                    .distinct(ProfessionalStats.wyscout_id)
                    .subquery()
                )

                # Obtener todos los jugadores únicos
                unique_players = session.query(subquery).all()

                matches = []
                for player_stats in unique_players:
                    # Calcular similitud con el nombre completo
                    full_name_normalized = self._normalize_name(
                        player_stats.full_name or ""
                    )
                    player_name_normalized = self._normalize_name(
                        player_stats.player_name or ""
                    )

                    # Probar múltiples algoritmos de fuzzy matching para mayor precisión
                    confidence_full = 0
                    confidence_player = 0

                    if full_name_normalized:
                        # Usar múltiples algoritmos y tomar el mejor score
                        ratio_full = fuzz.ratio(search_name, full_name_normalized)
                        partial_full = fuzz.partial_ratio(
                            search_name, full_name_normalized
                        )
                        token_set_full = fuzz.token_set_ratio(
                            search_name, full_name_normalized
                        )
                        confidence_full = max(ratio_full, partial_full, token_set_full)

                    if player_name_normalized:
                        # Usar múltiples algoritmos y tomar el mejor score
                        ratio_player = fuzz.ratio(search_name, player_name_normalized)
                        partial_player = fuzz.partial_ratio(
                            search_name, player_name_normalized
                        )
                        token_set_player = fuzz.token_set_ratio(
                            search_name, player_name_normalized
                        )
                        confidence_player = max(
                            ratio_player, partial_player, token_set_player
                        )

                    # Usar el mejor confidence score
                    best_confidence = max(confidence_full, confidence_player)
                    best_match_name = (
                        player_stats.full_name
                        if confidence_full >= confidence_player
                        else player_stats.player_name
                    )

                    # Solo incluir si supera el threshold
                    if best_confidence >= threshold:
                        matches.append(
                            {
                                "wyscout_id": player_stats.wyscout_id,
                                "player_name": best_match_name,
                                "full_name": player_stats.full_name,
                                "team_name": player_stats.team,
                                "season": player_stats.season,
                                "position": player_stats.primary_position,
                                "goals": player_stats.goals or 0,
                                "assists": player_stats.assists or 0,
                                "matches": player_stats.matches_played or 0,
                                "confidence": best_confidence,
                            }
                        )

                # Ordenar por confidence score (mayor a menor)
                matches.sort(key=lambda x: x["confidence"], reverse=True)

                logger.info(
                    f"Búsqueda '{player_name}': {len(matches)} matches encontrados"
                )
                return matches

        except Exception as e:
            logger.error(f"Error buscando jugador por nombre '{player_name}': {e}")
            return []

    def search_players_in_csv(
        self, player_name: str, threshold: int = 60
    ) -> List[Dict]:
        """
        Busca jugadores directamente en el archivo CSV más reciente.
        Útil para encontrar jugadores que aún no están importados en la base de datos.

        Args:
            player_name: Nombre del jugador a buscar
            threshold: Umbral de similitud para fuzzy matching (0-100)

        Returns:
            Lista de jugadores ordenada por confidence score
        """
        try:
            if not player_name or not player_name.strip():
                return []

            # Normalizar el nombre de búsqueda
            search_name = self._normalize_name(player_name.strip())
            if not search_name:
                return []

            # Buscar el archivo CSV más reciente
            csv_file = self.cache_dir / "thai_league_2024-25.csv"
            if not csv_file.exists():
                logger.warning(f"Archivo CSV no encontrado: {csv_file}")
                return []

            # Leer y limpiar datos del CSV
            df = pd.read_csv(csv_file)

            # Limpiar datos nulos y normalizar nombres
            df["Player"] = df["Player"].fillna("").astype(str)
            df["Full name"] = df["Full name"].fillna("").astype(str)
            df["Team"] = df["Team"].fillna("").astype(str)
            df["Wyscout id"] = df["Wyscout id"].fillna(0).astype(int)
            df["Position"] = df["Position"].fillna("").astype(str)
            df["Birthday"] = df["Birthday"].fillna("").astype(str)

            # Eliminar filas completamente vacías
            df = df[(df["Player"] != "") | (df["Full name"] != "")]

            matches = []
            for _, row in df.iterrows():
                # Normalizar nombres para comparación
                player_name_norm = self._normalize_name(row["Player"] or "")
                full_name_norm = self._normalize_name(row["Full name"] or "")

                if not player_name_norm and not full_name_norm:
                    continue

                # Calcular similitud con múltiples algoritmos
                confidences = []

                # Fuzzy matching con nombre del jugador
                if player_name_norm:
                    confidences.extend(
                        [
                            fuzz.ratio(search_name, player_name_norm),
                            fuzz.partial_ratio(search_name, player_name_norm),
                            fuzz.token_set_ratio(search_name, player_name_norm),
                            fuzz.token_sort_ratio(search_name, player_name_norm),
                        ]
                    )

                # Fuzzy matching con nombre completo
                if full_name_norm:
                    confidences.extend(
                        [
                            fuzz.ratio(search_name, full_name_norm),
                            fuzz.partial_ratio(search_name, full_name_norm),
                            fuzz.token_set_ratio(search_name, full_name_norm),
                            fuzz.token_sort_ratio(search_name, full_name_norm),
                        ]
                    )

                # Tomar la mejor puntuación
                if confidences:
                    max_confidence = max(confidences)

                    if max_confidence >= threshold:
                        matches.append(
                            {
                                "wyscout_id": int(row["Wyscout id"]),
                                "player_name": row["Player"],
                                "full_name": row["Full name"],
                                "team_name": row["Team"],
                                "position": row["Position"],
                                "birthday": row["Birthday"],
                                "confidence": max_confidence,
                                "season": "2024-25",
                            }
                        )

            # Ordenar por confidence score descendente
            matches.sort(key=lambda x: x["confidence"], reverse=True)

            logger.info(f"Búsqueda CSV para '{player_name}': {len(matches)} resultados")
            return matches

        except Exception as e:
            logger.error(f"Error buscando en CSV para '{player_name}': {e}")
            return []

    def check_for_updates(self, season: str = None) -> List[Dict]:
        """
        Verifica qué temporadas necesitan actualización.

        Args:
            season: Temporada específica a verificar, o None para todas

        Returns:
            Lista de temporadas que necesitan actualización
        """
        seasons_to_check = [season] if season else list(self.AVAILABLE_SEASONS.keys())
        updates_needed = []

        with self.session_factory() as session:
            for season_name in seasons_to_check:
                season_obj = (
                    session.query(ThaiLeagueSeason)
                    .filter(ThaiLeagueSeason.season == season_name)
                    .first()
                )

                needs_update = False
                reason = ""

                if not season_obj:
                    needs_update = True
                    reason = "Primera importación"
                elif season_obj.needs_update:
                    needs_update = True
                    days_since_update = (
                        datetime.now(timezone.utc) - season_obj.last_import_attempt
                    ).days
                    reason = f"Última actualización hace {days_since_update} días"
                elif season_obj.import_status == ImportStatus.failed:
                    needs_update = True
                    reason = "Importación anterior falló"

                if needs_update:
                    updates_needed.append(
                        {
                            "season": season_name,
                            "reason": reason,
                            "last_update": (
                                season_obj.last_import_attempt if season_obj else None
                            ),
                            "status": (
                                season_obj.import_status
                                if season_obj
                                else ImportStatus.pending
                            ),
                            "is_current_season": self._is_current_season(season_name),
                        }
                    )

        logger.info(
            f"Verificación de actualizaciones: {len(updates_needed)} "
            f"temporadas necesitan actualización"
        )
        return updates_needed

    def _is_current_season(self, season: str) -> bool:
        """Determina si es la temporada actual."""
        current_year = datetime.now().year
        season_years = season.split("-")
        if len(season_years) == 2:
            start_year = int(f"20{season_years[0]}")
            return start_year == current_year or start_year == current_year - 1
        return False

    def auto_update_current_season(self) -> Tuple[bool, str, Dict]:
        """
        Actualización automática de la temporada actual.
        Función principal para el scheduler semanal.

        Returns:
            Tuple[success, message, details]
        """
        logger.info("Iniciando actualización automática de temporada actual")

        try:
            # Identificar temporada actual
            current_season = None
            for season in self.AVAILABLE_SEASONS.keys():
                if self._is_current_season(season):
                    current_season = season
                    break

            if not current_season:
                return False, "No se pudo identificar la temporada actual", {}

            # Verificar si necesita actualización
            updates_needed = self.check_for_updates(current_season)
            if not updates_needed:
                return True, f"Temporada {current_season} ya está actualizada", {}

            # Descargar datos
            success, df, message = self.download_season_data(current_season)
            if not success:
                return False, f"Error descargando {current_season}: {message}", {}

            # Limpiar datos
            clean_df = self.clean_and_normalize_data(df, current_season)

            # Hacer matching
            matching_results = self.find_matching_players(clean_df)

            # Importar datos
            import_success, import_message, stats = self.import_season_data(
                current_season, clean_df, matching_results
            )

            result_details = {
                "season": current_season,
                "stats": stats,
                "matching_summary": {
                    "exact_matches": len(matching_results["exact_matches"]),
                    "fuzzy_matches": len(matching_results["fuzzy_matches"]),
                    "no_matches": len(matching_results["no_matches"]),
                    "multiple_matches": len(matching_results["multiple_matches"]),
                },
            }

            if import_success:
                logger.info(f"Actualización automática exitosa para {current_season}")
                return True, import_message, result_details
            else:
                logger.error(f"Error en actualización automática: {import_message}")
                return False, import_message, result_details

        except Exception as e:
            error_msg = f"Error crítico en actualización automática: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, {}

    def get_import_summary(self) -> Dict:
        """
        Obtiene resumen del estado de todas las temporadas.

        Returns:
            Diccionario con resumen de importaciones
        """
        with self.session_factory() as session:
            seasons = session.query(ThaiLeagueSeason).all()

            summary = {
                "total_seasons": len(self.AVAILABLE_SEASONS),
                "imported_seasons": 0,
                "pending_seasons": 0,
                "failed_seasons": 0,
                "total_players": 0,
                "total_records": 0,
                "seasons_detail": [],
            }

            for season_name in self.AVAILABLE_SEASONS.keys():
                season_obj = next((s for s in seasons if s.season == season_name), None)

                if season_obj:
                    detail = {
                        "season": season_name,
                        "status": season_obj.import_status.value,
                        "last_updated": (
                            season_obj.last_updated.isoformat()
                            if season_obj.last_updated
                            else None
                        ),
                        "total_records": season_obj.total_records or 0,
                        "imported_records": season_obj.imported_records or 0,
                        "matched_players": season_obj.matched_players or 0,
                        "errors_count": season_obj.errors_count or 0,
                        "needs_update": season_obj.needs_update,
                    }

                    if season_obj.import_status == ImportStatus.completed:
                        summary["imported_seasons"] += 1
                    elif season_obj.import_status == ImportStatus.failed:
                        summary["failed_seasons"] += 1
                    else:
                        summary["pending_seasons"] += 1

                    summary["total_records"] += season_obj.total_records or 0
                    summary["total_players"] += season_obj.matched_players or 0
                else:
                    detail = {
                        "season": season_name,
                        "status": "not_imported",
                        "last_updated": None,
                        "total_records": 0,
                        "imported_records": 0,
                        "matched_players": 0,
                        "errors_count": 0,
                        "needs_update": True,
                    }
                    summary["pending_seasons"] += 1

                summary["seasons_detail"].append(detail)

            return summary

    def clear_cache(self, season: str = None) -> Tuple[bool, str]:
        """
        Limpia cache de CSV para una temporada específica o todas.

        Args:
            season: Temporada específica o None para todas

        Returns:
            Tuple[success, message]
        """
        try:
            if season:
                # Limpiar temporada específica
                cache_file = self._get_cache_file_path(season)
                if cache_file.exists():
                    cache_file.unlink()
                    logger.info(f"🗑️ Cache eliminado para temporada {season}")
                    return True, f"Cache eliminado para temporada {season}"
                else:
                    return True, f"No hay cache para temporada {season}"
            else:
                # Limpiar todo el cache
                deleted_count = 0
                if self.cache_dir.exists():
                    for cache_file in self.cache_dir.glob("thai_league_*.csv"):
                        cache_file.unlink()
                        deleted_count += 1

                logger.info(f"🗑️ Cache limpiado: {deleted_count} archivos eliminados")
                return True, f"Cache limpiado: {deleted_count} archivos eliminados"

        except Exception as e:
            error_msg = f"Error limpiando cache: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_cache_info(self) -> Dict:
        """
        Obtiene información sobre el estado del cache.

        Returns:
            Diccionario con información del cache
        """
        try:
            cache_info = {
                "cache_directory": str(self.cache_dir),
                "directory_exists": self.cache_dir.exists(),
                "cached_seasons": [],
                "total_size_mb": 0.0,
            }

            if self.cache_dir.exists():
                total_size = 0
                for cache_file in self.cache_dir.glob("thai_league_*.csv"):
                    size = cache_file.stat().st_size
                    total_size += size

                    season = cache_file.stem.replace("thai_league_", "")
                    cache_info["cached_seasons"].append(
                        {
                            "season": season,
                            "file_size_mb": round(size / (1024 * 1024), 2),
                            "last_modified": datetime.fromtimestamp(
                                cache_file.stat().st_mtime
                            ).isoformat(),
                        }
                    )

                cache_info["total_size_mb"] = round(total_size / (1024 * 1024), 2)

            return cache_info

        except Exception as e:
            logger.error(f"Error obteniendo info de cache: {str(e)}")
            return {"error": str(e)}

    # === FUNCIONES PARA CARGA INCREMENTAL ===

    def get_registered_professional_players(self) -> List[int]:
        """
        Obtiene lista de wyscout_ids de jugadores profesionales registrados.

        Returns:
            Lista de wyscout_ids (enteros) de jugadores profesionales
        """
        try:
            with self.session_factory() as session:
                professional_players = (
                    session.query(Player.wyscout_id)
                    .filter(
                        Player.is_professional == True,
                        Player.wyscout_id.isnot(None),
                        Player.wyscout_id != "",
                    )
                    .all()
                )

                # Convertir a enteros para matching con CSV
                wyscout_ids = []
                for player in professional_players:
                    try:
                        wyscout_id_int = (
                            int(player.wyscout_id) if player.wyscout_id else None
                        )
                        if wyscout_id_int:
                            wyscout_ids.append(wyscout_id_int)
                    except (ValueError, TypeError):
                        logger.warning(f"WyscoutID inválido: {player.wyscout_id}")

                logger.info(
                    f"Encontrados {len(wyscout_ids)} jugadores profesionales registrados"
                )
                return wyscout_ids

        except Exception as e:
            logger.error(f"Error obteniendo jugadores profesionales: {str(e)}")
            return []

    def process_season_for_registered_players(
        self, season: str, registered_wyscout_ids: List[int]
    ) -> Tuple[bool, str, Dict]:
        """
        Procesa una temporada solo para jugadores profesionales registrados.
        Flujo: Descargar → Limpiar → Filtrar → Procesar

        Args:
            season: Temporada en formato "2024-25"
            registered_wyscout_ids: Lista de wyscout_ids a procesar

        Returns:
            Tupla (success, message, stats)
        """
        try:
            logger.info(
                f"Procesando temporada {season} para {len(registered_wyscout_ids)} jugadores"
            )

            # 1. Descargar datos de la temporada (reutiliza función existente)
            success, df, message = self.download_season_data(season)
            if not success or df is None:
                return False, f"Error descargando {season}: {message}", {}

            # 2. Limpiar y normalizar datos ANTES del filtrado (reutiliza función existente)
            df_clean = self.clean_and_normalize_data(df, season)
            logger.info(f"Datos limpiados: {len(df_clean)} registros válidos")

            # 3. Filtrar solo jugadores registrados para optimizar procesamiento
            if registered_wyscout_ids:
                original_count = len(df_clean)
                df_filtered = df_clean[
                    df_clean["Wyscout id"].isin(registered_wyscout_ids)
                ]
                logger.info(
                    f"Filtrados {len(df_filtered)} de {original_count} registros para jugadores registrados"
                )
            else:
                logger.warning(
                    "No hay jugadores profesionales registrados, omitiendo procesamiento"
                )
                return (
                    True,
                    f"Temporada {season}: sin jugadores profesionales registrados",
                    {"processed": 0},
                )

            if df_filtered.empty:
                return (
                    True,
                    f"Temporada {season}: no hay datos para jugadores registrados",
                    {"processed": 0},
                )

            # 4. Procesar matching solo para jugadores filtrados (reutiliza función existente)
            matching_results = self.find_matching_players(df_filtered, threshold=85)

            # 5. Importar datos (reutiliza función existente)
            import_success, import_message, import_stats = self.import_season_data(
                season, df_filtered, matching_results
            )

            return import_success, import_message, import_stats

        except Exception as e:
            error_msg = f"Error procesando temporada {season}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, {}

    def load_historical_seasons(
        self, seasons: Optional[List[str]] = None
    ) -> Dict[str, Tuple[bool, str, Dict]]:
        """
        Carga múltiples temporadas históricas para jugadores profesionales registrados.
        Procesamiento simple y secuencial para mantener control y simplicidad.

        Args:
            seasons: Lista de temporadas a procesar. Si None, procesa todas las disponibles

        Returns:
            Diccionario con resultados por temporada
        """
        if seasons is None:
            seasons = list(self.AVAILABLE_SEASONS.keys())

        logger.info(f"Iniciando carga histórica de {len(seasons)} temporadas")

        # Obtener jugadores profesionales registrados una sola vez
        registered_wyscout_ids = self.get_registered_professional_players()

        if not registered_wyscout_ids:
            logger.warning("No hay jugadores profesionales registrados")
            return {
                season: (
                    True,
                    "Sin jugadores profesionales registrados",
                    {"processed": 0},
                )
                for season in seasons
            }

        results = {}

        for season in seasons:
            logger.info(f"Procesando temporada {season}...")

            try:
                # Verificar si la temporada ya está importada
                with self.session_factory() as session:
                    season_record = (
                        session.query(ThaiLeagueSeason).filter_by(season=season).first()
                    )

                    if (
                        season_record
                        and season_record.import_status == ImportStatus.completed
                    ):
                        logger.info(f"Temporada {season} ya está completada, omitiendo")
                        results[season] = (
                            True,
                            f"Temporada {season} ya importada",
                            {"skipped": True},
                        )
                        continue

                # Procesar temporada
                success, message, stats = self.process_season_for_registered_players(
                    season, registered_wyscout_ids
                )

                results[season] = (success, message, stats)

                if success:
                    logger.info(f"✅ Temporada {season} procesada exitosamente")
                else:
                    logger.error(f"❌ Error en temporada {season}: {message}")

            except Exception as e:
                error_msg = f"Error crítico procesando {season}: {str(e)}"
                logger.error(error_msg)
                results[season] = (False, error_msg, {})

        logger.info(
            f"Carga histórica completada. Resultados: {len([r for r in results.values() if r[0]])} exitosas"
        )
        return results

    def trigger_stats_import_for_player(
        self, player_id: int, wyscout_id: int
    ) -> Tuple[bool, str, Dict]:
        """
        Trigger automático para importar estadísticas cuando se asigna WyscoutID a un jugador.

        Args:
            player_id: ID del jugador en la base de datos
            wyscout_id: WyscoutID asignado al jugador

        Returns:
            Tuple[success, message, statistics]
        """
        logger.info(
            f"🎯 Trigger automático: importando estadísticas para player_id={player_id}, wyscout_id={wyscout_id}"
        )

        stats = {
            "seasons_processed": 0,
            "records_imported": 0,
            "records_skipped": 0,
            "errors": 0,
            "seasons_with_data": [],
        }

        try:
            # Convertir wyscout_id a entero para comparaciones
            wyscout_id_int = int(wyscout_id) if wyscout_id else None
            if not wyscout_id_int:
                return False, f"WyscoutID inválido: {wyscout_id}", stats

            # Obtener todas las temporadas disponibles
            available_seasons = list(self.AVAILABLE_SEASONS.keys())
            logger.info(f"Procesando {len(available_seasons)} temporadas disponibles")

            for season in available_seasons:
                try:
                    stats["seasons_processed"] += 1
                    logger.info(
                        f"🔍 Procesando temporada {season} para WyscoutID {wyscout_id_int}"
                    )

                    # Verificar si ya existe el registro para evitar duplicados
                    with self.session_factory() as session:
                        existing = (
                            session.query(ProfessionalStats)
                            .filter_by(player_id=player_id, season=season)
                            .first()
                        )

                        if existing:
                            logger.info(
                                f"⏭️ Registro ya existe para {season}, omitiendo"
                            )
                            stats["records_skipped"] += 1
                            continue

                    # Cargar datos de la temporada desde cache o GitHub
                    success, season_data, message = self.download_season_data(season)
                    if not success or season_data is None or season_data.empty:
                        logger.warning(
                            f"⚠️ No se pudieron cargar datos para temporada {season}: {message}"
                        )
                        continue

                    # Limpiar y normalizar datos
                    clean_data = self.clean_and_normalize_data(season_data, season)

                    # Buscar jugador específico por WyscoutID
                    player_rows = clean_data[clean_data["Wyscout id"] == wyscout_id_int]

                    if player_rows.empty:
                        logger.info(
                            f"🔍 WyscoutID {wyscout_id_int} no encontrado en temporada {season}"
                        )
                        continue

                    # Procesar cada fila del jugador (normalmente debería ser 1)
                    for _, player_data in player_rows.iterrows():
                        try:
                            # Crear registro de estadísticas usando función existente
                            record_data = self._create_professional_stats_record(
                                player_data, season, player_id
                            )

                            # Guardar en base de datos
                            with self.session_factory() as session:
                                new_record = ProfessionalStats(**record_data)
                                session.add(new_record)
                                session.commit()

                                stats["records_imported"] += 1
                                stats["seasons_with_data"].append(season)
                                logger.info(
                                    f"✅ Estadísticas importadas para temporada {season}"
                                )

                        except Exception as e:
                            stats["errors"] += 1
                            logger.error(
                                f"❌ Error importando registro de temporada {season}: {str(e)}"
                            )

                except Exception as e:
                    stats["errors"] += 1
                    logger.error(f"❌ Error procesando temporada {season}: {str(e)}")

            # Generar mensaje de resultado
            if stats["records_imported"] > 0:
                success_msg = (
                    f"Estadísticas importadas automáticamente: {stats['records_imported']} registros "
                    f"de {len(stats['seasons_with_data'])} temporadas para WyscoutID {wyscout_id}"
                )
                logger.info(f"✅ {success_msg}")
                return True, success_msg, stats
            elif stats["records_skipped"] > 0:
                skip_msg = f"Estadísticas ya existían para WyscoutID {wyscout_id} ({stats['records_skipped']} registros omitidos)"
                logger.info(f"ℹ️ {skip_msg}")
                return True, skip_msg, stats
            else:
                no_data_msg = f"No se encontraron estadísticas para WyscoutID {wyscout_id} en ninguna temporada"
                logger.warning(f"⚠️ {no_data_msg}")
                return False, no_data_msg, stats

        except Exception as e:
            error_msg = f"Error crítico en trigger de importación para player_id {player_id}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, stats

    # === FUNCIONES DE SINCRONIZACIÓN AUTOMATIZADA ===

    def sync_season_status_from_real_data(self) -> Tuple[bool, str, Dict]:
        """
        Sincroniza automáticamente el estado de temporadas basándose en datos reales
        en professional_stats. Actualiza contadores y estados automáticamente.

        Returns:
            Tupla (success, message, sync_details)
        """
        logger.info("🔄 Iniciando sincronización automatizada de temporadas")

        try:
            sync_results = {
                "seasons_updated": 0,
                "seasons_analyzed": 0,
                "discrepancies_fixed": 0,
                "details": {},
            }

            with self.session_factory() as session:
                # 1. Obtener datos reales por temporada desde professional_stats
                from sqlalchemy import func

                real_stats = (
                    session.query(
                        ProfessionalStats.season,
                        func.count(ProfessionalStats.stat_id).label("real_count"),
                        func.count(func.distinct(ProfessionalStats.wyscout_id)).label(
                            "unique_players"
                        ),
                    )
                    .group_by(ProfessionalStats.season)
                    .all()
                )

                real_data_by_season = {
                    season: {"count": count, "players": players}
                    for season, count, players in real_stats
                }

                logger.info(
                    f"📊 Datos reales encontrados: {len(real_data_by_season)} temporadas"
                )

                # 2. Obtener registros de temporadas existentes
                season_records = session.query(ThaiLeagueSeason).all()

                # 3. Sincronizar cada temporada
                for season_record in season_records:
                    sync_results["seasons_analyzed"] += 1
                    season_name = season_record.season

                    # Obtener datos reales para esta temporada
                    real_data = real_data_by_season.get(
                        season_name, {"count": 0, "players": 0}
                    )
                    real_count = real_data["count"]
                    real_players = real_data["players"]

                    # Variables para tracking de cambios
                    changes_made = []
                    was_discrepancy = False

                    # Verificar y corregir status
                    if (
                        real_count > 0
                        and season_record.import_status == ImportStatus.in_progress
                    ):
                        season_record.import_status = ImportStatus.completed
                        changes_made.append(f"status: in_progress → completed")
                        was_discrepancy = True

                    # Verificar y corregir contadores
                    if season_record.imported_records != real_count:
                        old_count = season_record.imported_records or 0
                        season_record.imported_records = real_count
                        changes_made.append(
                            f"imported_records: {old_count} → {real_count}"
                        )
                        was_discrepancy = True

                    if season_record.matched_players != real_players:
                        old_players = season_record.matched_players or 0
                        season_record.matched_players = real_players
                        changes_made.append(
                            f"matched_players: {old_players} → {real_players}"
                        )
                        was_discrepancy = True

                    # Actualizar timestamp si hubo cambios
                    if changes_made:
                        season_record.last_updated = datetime.now(timezone.utc)
                        sync_results["seasons_updated"] += 1

                        if was_discrepancy:
                            sync_results["discrepancies_fixed"] += 1

                    # Guardar detalles del proceso
                    sync_results["details"][season_name] = {
                        "real_records": real_count,
                        "real_players": real_players,
                        "changes_made": changes_made,
                        "current_status": season_record.import_status.value,
                        "had_discrepancy": was_discrepancy,
                    }

                    logger.info(
                        f"  📋 {season_name}: {real_count} registros, {len(changes_made)} cambios"
                    )

                # 4. Commit todos los cambios
                session.commit()

                success_msg = (
                    f"Sincronización completada: {sync_results['seasons_updated']} temporadas actualizadas, "
                    f"{sync_results['discrepancies_fixed']} discrepancias corregidas"
                )
                logger.info(f"✅ {success_msg}")

                return True, success_msg, sync_results

        except Exception as e:
            error_msg = f"Error en sincronización automatizada: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, {}

    def auto_generate_source_urls(self) -> Tuple[bool, str, Dict]:
        """
        Genera automáticamente las URLs fuente de GitHub para todas las temporadas.

        Returns:
            Tupla (success, message, url_details)
        """
        logger.info("🔗 Generando URLs fuente automáticamente")

        try:
            url_results = {"urls_generated": 0, "urls_updated": 0, "details": {}}

            with self.session_factory() as session:
                season_records = session.query(ThaiLeagueSeason).all()

                for season_record in season_records:
                    season_name = season_record.season

                    # Generar URL basada en temporada y patrón del repositorio
                    if season_name in self.AVAILABLE_SEASONS:
                        filename = self.AVAILABLE_SEASONS[season_name]
                        source_url = f"{self.GITHUB_BASE_URL}/{self.COMMIT_HASH}/Main App/{filename.replace(' ', '%20')}"

                        # Actualizar si no existe o es diferente
                        if (
                            not season_record.source_url
                            or season_record.source_url != source_url
                        ):
                            old_url = season_record.source_url or "N/A"
                            season_record.source_url = source_url
                            season_record.last_updated = datetime.now(timezone.utc)

                            if old_url == "N/A":
                                url_results["urls_generated"] += 1
                            else:
                                url_results["urls_updated"] += 1

                            url_results["details"][season_name] = {
                                "old_url": old_url,
                                "new_url": source_url,
                                "action": (
                                    "generated" if old_url == "N/A" else "updated"
                                ),
                            }

                            logger.info(
                                f"  🔗 {season_name}: URL {'generada' if old_url == 'N/A' else 'actualizada'}"
                            )
                    else:
                        logger.warning(
                            f"  ⚠️ {season_name}: no está en AVAILABLE_SEASONS"
                        )

                session.commit()

                total_changes = (
                    url_results["urls_generated"] + url_results["urls_updated"]
                )
                success_msg = f"URLs procesadas: {url_results['urls_generated']} generadas, {url_results['urls_updated']} actualizadas"
                logger.info(f"✅ {success_msg}")

                return True, success_msg, url_results

        except Exception as e:
            error_msg = f"Error generando URLs automáticamente: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, {}

    def collect_comprehensive_season_data(self, season: str) -> Dict:
        """
        Recopila datos completos de una temporada incluyendo tamaños de archivo,
        conteos totales y análisis de matching.

        Args:
            season: Temporada en formato "2024-25"

        Returns:
            Dict con datos completos de la temporada
        """
        logger.info(f"📊 Recopilando datos completos para temporada {season}")

        data = {
            "file_size": None,
            "total_records": 0,
            "matched_players": 0,
            "unmatched_players": 0,
            "errors_count": 0,
            "cache_exists": False,
        }

        try:
            # 1. Obtener datos del archivo cache
            cache_file = self._get_cache_file_path(season)
            if cache_file.exists():
                data["cache_exists"] = True
                data["file_size"] = self.bytes_to_mb(cache_file.stat().st_size)

                # Leer CSV para contar registros totales
                try:
                    import pandas as pd

                    df = pd.read_csv(cache_file)
                    data["total_records"] = len(df)
                    logger.info(
                        f"  📁 Archivo cache: {data['file_size']} bytes, {data['total_records']} registros"
                    )
                except Exception as e:
                    logger.warning(f"  ⚠️ Error leyendo CSV: {e}")
                    data["errors_count"] += 1
            else:
                logger.warning(f"  ⚠️ Archivo cache no existe para {season}")

            # 2. Obtener datos reales de matching desde professional_stats
            with self.session_factory() as session:
                from sqlalchemy import func

                real_stats = (
                    session.query(
                        func.count(ProfessionalStats.stat_id).label("matched_count"),
                        func.count(func.distinct(ProfessionalStats.wyscout_id)).label(
                            "unique_players"
                        ),
                    )
                    .filter(ProfessionalStats.season == season)
                    .first()
                )

                if real_stats:
                    data["matched_players"] = real_stats.unique_players or 0
                    logger.info(
                        f"  👥 Jugadores coincidentes: {data['matched_players']}"
                    )

                # 3. Calcular unmatched (total - matched)
                if data["total_records"] > 0 and data["matched_players"] > 0:
                    data["unmatched_players"] = (
                        data["total_records"] - data["matched_players"]
                    )
                    logger.info(
                        f"  ❌ Jugadores no coincidentes: {data['unmatched_players']}"
                    )

            return data

        except Exception as e:
            logger.error(f"Error recopilando datos de {season}: {str(e)}")
            data["errors_count"] += 1
            return data

    def generate_import_logs(
        self, season: str, stats: Dict, errors: List = None
    ) -> Tuple[str, str]:
        """
        Genera logs estructurados para import_log y error_log.

        Args:
            season: Temporada procesada
            stats: Diccionario con estadísticas del import
            errors: Lista de errores ocurridos

        Returns:
            Tupla (import_log, error_log)
        """
        from datetime import datetime

        # Generar import_log estructurado
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        import_log_lines = [
            f"=== IMPORT LOG - {season.upper()} ===",
            f"Timestamp: {timestamp}",
            f"Total records processed: {stats.get('total_records', 0)}",
            f"Matched players: {stats.get('matched_players', 0)}",
            f"Unmatched players: {stats.get('unmatched_players', 0)}",
            f"Successfully imported: {stats.get('imported_records', 0)}",
            f"Errors encountered: {stats.get('errors_count', 0)}",
            f"File size: {stats.get('file_size', 'N/A')} bytes",
        ]

        # Añadir detalles específicos si están disponibles
        if stats.get("cache_exists"):
            import_log_lines.append(f"Cache file: Available")
        else:
            import_log_lines.append(f"Cache file: Missing")

        import_log = "\n".join(import_log_lines)

        # Generar error_log si hay errores
        error_log = ""
        if errors and len(errors) > 0:
            error_log_lines = [
                f"=== ERROR LOG - {season.upper()} ===",
                f"Timestamp: {timestamp}",
                f"Total errors: {len(errors)}",
                "",
                "Error details:",
            ]

            for i, error in enumerate(errors, 1):
                error_log_lines.append(f"{i}. {error}")

            error_log = "\n".join(error_log_lines)

        return import_log, error_log

    def format_file_size(self, size_mb: float) -> str:
        """
        Formatea MB a string legible con unidades apropiadas.

        Args:
            size_mb: Tamaño en MB (Float)

        Returns:
            String formateado (ej: "0.33 MB", "1.20 GB")
        """
        if size_mb is None or size_mb == 0:
            return "0.00 MB"
        elif size_mb < 1024:
            return f"{size_mb:.2f} MB"
        else:
            gb = size_mb / 1024
            return f"{gb:.2f} GB"

    def bytes_to_mb(self, size_bytes: int) -> float:
        """
        Convierte bytes a MB para almacenar en base de datos.

        Args:
            size_bytes: Tamaño en bytes

        Returns:
            Tamaño en MB (Float redondeado a 2 decimales)
        """
        if size_bytes is None or size_bytes == 0:
            return 0.00
        return round(size_bytes / (1024 * 1024), 2)

    def _parse_season_year(self, season: str) -> int:
        """
        Parse season string to get actual start year correctly.

        Args:
            season: Season string like "20-21", "23-24", "24-25"

        Returns:
            Actual year as integer (2020, 2023, 2024, etc.)
        """
        try:
            year_part = season.split("-")[0]

            if len(year_part) == 2:
                year_num = int(year_part)
                # Para temporadas de fútbol: años 00-99 se mapean a 2000-2099
                # Asumimos que todas las temporadas son del siglo XXI
                return 2000 + year_num
            elif len(year_part) == 4:
                # Si ya viene con 4 dígitos, usar directamente
                return int(year_part)
            else:
                logger.warning(f"Formato de temporada inválido: {season}")
                return 2024  # Fallback a año actual

        except (ValueError, IndexError) as e:
            logger.warning(f"Error parseando año de temporada '{season}': {e}")
            return 2024  # Fallback a año actual

    def configure_completion_settings(self, season: str, is_completed: bool) -> Dict:
        """
        Configura settings apropiados para temporadas según su estado de completitud.

        Args:
            season: Temporada a configurar
            is_completed: Si la temporada está completada

        Returns:
            Dict con configuraciones a aplicar
        """
        logger.info(
            f"⚙️ Configurando settings para {season} (completed: {is_completed})"
        )

        # Determinar si es temporada histórica (usar función corregida)
        season_start_year = self._parse_season_year(season)
        is_historical = season_start_year < 2024

        logger.debug(
            f"  📅 {season}: año_inicio={season_start_year}, histórica={is_historical}"
        )

        # Configurar según estado y tipo de temporada
        if is_completed and is_historical:
            # Temporadas históricas completadas: deshabilitar auto-update
            config = {
                "auto_update_enabled": False,
                "update_frequency_days": 0,
                "notes": f"Historical season {season} - Auto-update disabled",
            }
            logger.info(f"  📚 {season}: Configuración histórica (auto-update OFF)")
        elif is_completed and not is_historical:
            # Temporada actual completada pero podría necesitar updates
            config = {
                "auto_update_enabled": True,
                "update_frequency_days": 30,  # Mensual para temporada actual
                "notes": f"Current season {season} - Monthly updates enabled",
            }
            logger.info(f"  🔄 {season}: Configuración actual (auto-update mensual)")
        else:
            # Temporadas en progreso o fallidas
            config = {
                "auto_update_enabled": True,
                "update_frequency_days": 7,  # Semanal para temporadas activas
                "notes": f"Active season {season} - Weekly updates enabled",
            }
            logger.info(f"  ⏱️ {season}: Configuración activa (auto-update semanal)")

        return config

    def configure_auto_update_by_season_type(self) -> Tuple[bool, str, Dict]:
        """
        Configura automáticamente el auto_update basándose en el tipo de temporada:
        - Temporadas históricas (<=2023-24): auto_update = False
        - Temporada actual/futura (>=2024-25): auto_update = True

        Returns:
            Tupla (success, message, config_details)
        """
        logger.info("⚙️ Configurando auto_update por tipo de temporada")

        try:
            config_results = {
                "historical_seasons_disabled": 0,
                "current_seasons_enabled": 0,
                "no_changes_needed": 0,
                "details": {},
            }

            # Determinar temporada actual (2024-25 es el punto de corte)
            current_year = datetime.now().year
            cutoff_season = "2024-25"  # Temporadas >= a esta son "actuales"

            with self.session_factory() as session:
                season_records = session.query(ThaiLeagueSeason).all()

                for season_record in season_records:
                    season_name = season_record.season

                    # Determinar si es temporada histórica o actual/futura (usar función corregida)
                    season_start_year = self._parse_season_year(season_name)
                    is_historical = season_start_year < 2024  # 2024 es el año de corte

                    # Configurar auto_update apropiadamente
                    desired_auto_update = (
                        not is_historical
                    )  # False para históricas, True para actuales

                    # También configurar la frecuencia según el tipo
                    desired_frequency = (
                        0 if is_historical else 7
                    )  # 0 para históricas, 7 para actuales

                    changes_made = []
                    old_setting = season_record.auto_update_enabled
                    old_frequency = season_record.update_frequency_days

                    if season_record.auto_update_enabled != desired_auto_update:
                        season_record.auto_update_enabled = desired_auto_update
                        changes_made.append(
                            f"auto_update: {old_setting} → {desired_auto_update}"
                        )

                    if season_record.update_frequency_days != desired_frequency:
                        season_record.update_frequency_days = desired_frequency
                        changes_made.append(
                            f"frequency: {old_frequency} → {desired_frequency}"
                        )

                    if changes_made:
                        season_record.last_updated = datetime.now(timezone.utc)

                        if is_historical:
                            config_results["historical_seasons_disabled"] += 1
                            action = "disabled (historical)"
                        else:
                            config_results["current_seasons_enabled"] += 1
                            action = "enabled (current/future)"

                        config_results["details"][season_name] = {
                            "season_type": (
                                "historical" if is_historical else "current/future"
                            ),
                            "changes_made": changes_made,
                            "current_auto_update": desired_auto_update,
                            "current_frequency": desired_frequency,
                            "action": action,
                        }

                        logger.info(
                            f"  ⚙️ {season_name}: {action} ({', '.join(changes_made)})"
                        )
                    else:
                        config_results["no_changes_needed"] += 1
                        config_results["details"][season_name] = {
                            "season_type": (
                                "historical" if is_historical else "current/future"
                            ),
                            "auto_update": season_record.auto_update_enabled,
                            "frequency": season_record.update_frequency_days,
                            "action": "no change needed",
                        }

                session.commit()

                success_msg = (
                    f"Auto-update configurado: {config_results['historical_seasons_disabled']} históricas deshabilitadas, "
                    f"{config_results['current_seasons_enabled']} actuales habilitadas"
                )
                logger.info(f"✅ {success_msg}")

                return True, success_msg, config_results

        except Exception as e:
            error_msg = f"Error configurando auto_update: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, {}

    # === FUNCIONES PARA ACTUALIZACIONES INCREMENTALES ===

    def check_for_season_updates(self, season: str = None) -> Dict[str, any]:
        """
        Verifica si hay actualizaciones disponibles para una temporada.

        Args:
            season: Temporada a verificar. Si None, verifica temporada actual.

        Returns:
            Dict con información de actualización disponible
        """
        if season is None:
            # Determinar temporada actual basándose en la fecha (timezone configurado)
            current_dt = self._get_current_datetime()
            current_year = current_dt.year
            current_month = current_dt.month

            # Temporada tailandesa va aproximadamente de Feb a Oct
            if current_month >= 2:
                season = f"{current_year}-{str(current_year + 1)[-2:]}"
            else:
                season = f"{current_year - 1}-{str(current_year)[-2:]}"

        try:
            logger.info(f"Verificando actualizaciones para temporada {season}")

            # 1. Obtener hash remoto del archivo
            if season not in self.AVAILABLE_SEASONS:
                return {
                    "season": season,
                    "update_available": False,
                    "error": f"Temporada {season} no disponible en repositorio",
                }

            filename = self.AVAILABLE_SEASONS[season]
            remote_url = f"{self.GITHUB_BASE_URL}/{self.COMMIT_HASH}/Main App/{filename.replace(' ', '%20')}"

            response = requests.head(remote_url, timeout=10)
            if response.status_code != 200:
                return {
                    "season": season,
                    "update_available": False,
                    "error": f"No se pudo acceder al archivo remoto: {response.status_code}",
                }

            # 2. Verificar información local de la temporada
            with self.session_factory() as session:
                season_record = (
                    session.query(ThaiLeagueSeason).filter_by(season=season).first()
                )

                # Si no existe registro local, hay actualización disponible
                if not season_record:
                    return {
                        "season": season,
                        "update_available": True,
                        "reason": "Nueva temporada sin importar",
                        "local_hash": None,
                        "remote_url": remote_url,
                    }

                # 3. Comparar con cache local si existe
                cache_file = self._get_cache_file_path(season)
                if cache_file.exists():
                    # Obtener hash del archivo actual
                    with open(cache_file, "rb") as f:
                        current_content = f.read()
                        local_hash = hashlib.md5(current_content, usedforsecurity=False).hexdigest()

                    # Verificar si el archivo remoto ha cambiado (simplificado)
                    # En una implementación completa, compararías ETags o Last-Modified
                    current_dt = self._get_current_datetime()
                    file_age_hours = (
                        current_dt.timestamp() - cache_file.stat().st_mtime
                    ) / 3600

                    update_needed = (
                        season_record.import_status != ImportStatus.completed
                        or file_age_hours > 168  # Más de una semana
                    )

                    return {
                        "season": season,
                        "update_available": update_needed,
                        "reason": (
                            "Verificación periódica"
                            if update_needed
                            else "Cache actual"
                        ),
                        "local_hash": local_hash,
                        "file_age_hours": round(file_age_hours, 1),
                        "last_import": (
                            season_record.last_import_attempt.isoformat()
                            if season_record.last_import_attempt
                            else None
                        ),
                    }
                else:
                    return {
                        "season": season,
                        "update_available": True,
                        "reason": "Archivo cache no existe",
                        "local_hash": None,
                    }

        except Exception as e:
            logger.error(f"Error verificando actualizaciones para {season}: {str(e)}")
            return {"season": season, "update_available": False, "error": str(e)}

    def perform_incremental_update(self, season: str = None) -> Tuple[bool, str, Dict]:
        """
        Realiza actualización incremental de una temporada si es necesario.

        Args:
            season: Temporada a actualizar. Si None, actualiza temporada actual.

        Returns:
            Tupla (success, message, stats)
        """
        try:
            # 1. Verificar si hay actualización disponible
            update_info = self.check_for_season_updates(season)

            if not update_info.get("update_available", False):
                return (
                    True,
                    f"Temporada {update_info['season']}: no requiere actualización",
                    {
                        "season": update_info["season"],
                        "updated": False,
                        "reason": update_info.get("reason", "No hay cambios"),
                    },
                )

            season = update_info["season"]
            logger.info(f"Realizando actualización incremental de temporada {season}")

            # 2. Obtener jugadores profesionales registrados
            registered_wyscout_ids = self.get_registered_professional_players()

            if not registered_wyscout_ids:
                return (
                    True,
                    f"Temporada {season}: sin jugadores profesionales para actualizar",
                    {
                        "season": season,
                        "updated": False,
                        "reason": "Sin jugadores profesionales registrados",
                    },
                )

            # 3. Procesar temporada (forzar descarga nueva)
            success, message, stats = self.process_season_for_registered_players(
                season, registered_wyscout_ids
            )

            if success:
                # 4. Actualizar registro de temporada
                with self.session_factory() as session:
                    season_record = (
                        session.query(ThaiLeagueSeason).filter_by(season=season).first()
                    )
                    if season_record:
                        season_record.last_updated = datetime.now(timezone.utc)
                        if stats.get("imported_records", 0) > 0:
                            season_record.import_status = ImportStatus.updated
                        session.commit()

                logger.info(f"✅ Actualización incremental exitosa para {season}")
                return (
                    True,
                    f"Temporada {season} actualizada exitosamente",
                    {"season": season, "updated": True, **stats},
                )
            else:
                logger.error(
                    f"❌ Error en actualización incremental de {season}: {message}"
                )
                return False, f"Error actualizando {season}: {message}", stats

        except Exception as e:
            error_msg = f"Error en actualización incremental: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, {}

    def auto_update_all_seasons(self) -> Dict[str, Tuple[bool, str, Dict]]:
        """
        Realiza actualización automática de todas las temporadas que lo requieran.
        Función diseñada para ejecución programada (cron job).

        Returns:
            Diccionario con resultados por temporada
        """
        logger.info("Iniciando actualización automática de temporadas")

        results = {}

        # Lista de temporadas a verificar (actual + 2 anteriores)
        seasons_to_check = list(self.AVAILABLE_SEASONS.keys())[
            -3:
        ]  # Últimas 3 temporadas

        for season in seasons_to_check:
            try:
                logger.info(f"Verificando temporada {season}...")

                success, message, stats = self.perform_incremental_update(season)
                results[season] = (success, message, stats)

                if success and stats.get("updated", False):
                    logger.info(f"✅ {season}: {message}")
                else:
                    logger.info(f"⏭️ {season}: {message}")

            except Exception as e:
                error_msg = f"Error procesando {season}: {str(e)}"
                logger.error(error_msg)
                results[season] = (False, error_msg, {})

        successful_updates = len(
            [r for r in results.values() if r[0] and r[2].get("updated", False)]
        )
        logger.info(
            f"Actualización automática completada: {successful_updates} temporadas actualizadas"
        )

        return results

    # === FUNCIONES PARA LÓGICA ESTACIONAL ===

    def get_last_csv_update_date(self, season: str = None) -> datetime:
        """
        Obtiene la fecha de última actualización del CSV de una temporada.

        Args:
            season: Temporada a verificar. Si None, usa temporada actual.

        Returns:
            Fecha de última modificación del archivo cache
        """
        if season is None:
            # Determinar temporada actual (timezone configurado)
            current_dt = self._get_current_datetime()
            current_year = current_dt.year
            current_month = current_dt.month

            if current_month >= 8:  # Agosto-Diciembre
                season = f"{current_year}-{str(current_year + 1)[-2:]}"
            else:  # Enero-Julio
                season = f"{current_year - 1}-{str(current_year)[-2:]}"

        try:
            cache_file = self._get_cache_file_path(season)
            if cache_file.exists():
                return datetime.fromtimestamp(cache_file.stat().st_mtime)
            else:
                # Si no existe cache, considerar muy antigua
                return datetime(2020, 1, 1)

        except Exception as e:
            logger.error(
                f"Error obteniendo fecha de actualización para {season}: {str(e)}"
            )
            return datetime(2020, 1, 1)

    def csv_updated_recently(
        self, season: str = None, days_threshold: int = 30
    ) -> bool:
        """
        Verifica si el CSV de una temporada se actualizó recientemente.

        Args:
            season: Temporada a verificar. Si None, usa temporada actual.
            days_threshold: Umbral en días para considerar "reciente"

        Returns:
            True si se actualizó en los últimos días_threshold días
        """
        try:
            last_update = self.get_last_csv_update_date(season)
            current_dt = self._get_current_datetime()
            days_since_update = (current_dt - last_update).days

            logger.debug(
                f"CSV {season}: última actualización hace {days_since_update} días"
            )
            return days_since_update <= days_threshold

        except Exception as e:
            logger.error(f"Error verificando actualización reciente: {str(e)}")
            return False

    def determine_season_action(self) -> str:
        """
        Determina qué acción tomar basándose en el mes actual y actividad de temporada.

        Returns:
            'update_current' | 'search_new_season' | 'season_ended'
        """
        current_month = self._get_current_datetime().month

        try:
            if current_month in [7, 8]:
                # Julio-Agosto: Buscar nueva temporada
                logger.info(
                    f"Mes {current_month}: Período de búsqueda de nueva temporada"
                )
                return "search_new_season"

            elif current_month in [4, 5]:
                # Abril-Mayo: Verificar actividad antes de decidir
                if self.csv_updated_recently(days_threshold=30):
                    logger.info(f"Mes {current_month}: Temporada actual aún activa")
                    return "update_current"
                else:
                    logger.info(
                        f"Mes {current_month}: Temporada inactiva por >30 días, marcando como terminada"
                    )
                    return "season_ended"

            elif current_month == 6:
                # Junio: Período muerto
                logger.info(
                    f"Mes {current_month}: Período de descanso entre temporadas"
                )
                return "season_ended"

            else:
                # Agosto-Marzo: Temporada activa
                logger.info(f"Mes {current_month}: Período de temporada activa")
                return "update_current"

        except Exception as e:
            logger.error(f"Error determinando acción estacional: {str(e)}")
            # Fallback seguro
            return "update_current"

    def search_for_new_season(self) -> Tuple[bool, str, Optional[str]]:
        """
        Busca nueva temporada en el repositorio GitHub.

        Returns:
            Tupla (found, message, new_season)
        """
        try:
            current_year = self._get_current_datetime().year

            # Generar posibles nombres de nueva temporada
            possible_seasons = [
                f"{current_year}-{str(current_year + 1)[-2:]}",  # 2025-26
                f"{current_year + 1}-{str(current_year + 2)[-2:]}",  # 2026-27
            ]

            logger.info(f"Buscando nuevas temporadas: {possible_seasons}")

            for season in possible_seasons:
                if season in self.AVAILABLE_SEASONS:
                    # Verificar si esta temporada ya está en nuestra BD
                    with self.session_factory() as session:
                        season_record = (
                            session.query(ThaiLeagueSeason)
                            .filter_by(season=season)
                            .first()
                        )

                        if (
                            not season_record
                            or season_record.import_status != ImportStatus.completed
                        ):
                            logger.info(f"✅ Nueva temporada encontrada: {season}")
                            return True, f"Nueva temporada disponible: {season}", season
                        else:
                            logger.info(f"⏭️ Temporada {season} ya importada")

                else:
                    # Verificar si existe en el repositorio (para temporadas no listadas)
                    filename = f"Thai League 1 {season.replace('-', '-')}.csv"
                    test_url = f"{self.GITHUB_BASE_URL}/{self.COMMIT_HASH}/Main App/{filename.replace(' ', '%20')}"

                    try:
                        response = requests.head(test_url, timeout=5)
                        if response.status_code == 200:
                            logger.info(
                                f"🆕 Nueva temporada descubierta en repositorio: {season}"
                            )
                            # Añadir a temporadas disponibles
                            self.AVAILABLE_SEASONS[season] = filename
                            return (
                                True,
                                f"Nueva temporada descubierta: {season}",
                                season,
                            )
                    except requests.RequestException:
                        continue

            return False, "No se encontraron nuevas temporadas", None

        except Exception as e:
            logger.error(f"Error buscando nueva temporada: {str(e)}")
            return False, f"Error en búsqueda: {str(e)}", None

    def smart_weekly_update(self) -> Dict[str, any]:
        """
        Función principal para actualización semanal inteligente.
        Combina lógica estacional con detección de actividad.

        Returns:
            Dict con resultado de la operación
        """
        logger.info("=== INICIANDO ACTUALIZACIÓN SEMANAL INTELIGENTE ===")

        try:
            # Determinar acción basada en período del año
            action = self.determine_season_action()

            if action == "update_current":
                # Actualizar temporada actual
                success, message, stats = self.perform_incremental_update()
                return {
                    "action": action,
                    "success": success,
                    "message": message,
                    "stats": stats,
                }

            elif action == "search_new_season":
                # Buscar nueva temporada
                found, message, new_season = self.search_for_new_season()

                if found and new_season:
                    # Procesar nueva temporada encontrada
                    registered_ids = self.get_registered_professional_players()
                    if registered_ids:
                        success, import_message, stats = (
                            self.process_season_for_registered_players(
                                new_season, registered_ids
                            )
                        )
                        return {
                            "action": action,
                            "success": success,
                            "message": f"Nueva temporada {new_season}: {import_message}",
                            "new_season": new_season,
                            "stats": stats,
                        }
                    else:
                        return {
                            "action": action,
                            "success": True,
                            "message": f"Nueva temporada {new_season} encontrada, pero sin jugadores profesionales registrados",
                            "new_season": new_season,
                            "stats": {"processed": 0},
                        }
                else:
                    return {
                        "action": action,
                        "success": True,
                        "message": message,
                        "stats": {},
                    }

            elif action == "season_ended":
                # Temporada terminada, no hacer nada
                return {
                    "action": action,
                    "success": True,
                    "message": "Temporada terminada, sin acciones programadas",
                    "stats": {},
                }

        except Exception as e:
            error_msg = f"Error en actualización semanal inteligente: {str(e)}"
            logger.error(error_msg)
            return {
                "action": "error",
                "success": False,
                "message": error_msg,
                "stats": {},
            }

    def sync_all_seasons_data(self) -> Tuple[bool, str, Dict]:
        """
        Sincronizador maestro que ejecuta todas las funciones de sincronización automatizada.
        Función principal para mantenimiento automatizado del sistema.

        Returns:
            Tupla (success, message, comprehensive_results)
        """
        logger.info("🚀 Iniciando sincronización maestra de todas las temporadas")

        master_results = {
            "sync_steps_completed": 0,
            "total_sync_steps": 3,
            "overall_success": True,
            "steps_results": {},
        }

        try:
            # Paso 1: Sincronizar estados y contadores basándose en datos reales
            logger.info("📊 Paso 1/3: Sincronizando estados y contadores")
            success_1, message_1, details_1 = self.sync_season_status_from_real_data()
            master_results["steps_results"]["status_sync"] = {
                "success": success_1,
                "message": message_1,
                "details": details_1,
            }
            if success_1:
                master_results["sync_steps_completed"] += 1
            else:
                master_results["overall_success"] = False

            # Paso 2: Generar URLs fuente automáticamente
            logger.info("🔗 Paso 2/3: Generando URLs fuente")
            success_2, message_2, details_2 = self.auto_generate_source_urls()
            master_results["steps_results"]["url_generation"] = {
                "success": success_2,
                "message": message_2,
                "details": details_2,
            }
            if success_2:
                master_results["sync_steps_completed"] += 1
            else:
                master_results["overall_success"] = False

            # Paso 3: Configurar auto_update por tipo de temporada
            logger.info("⚙️ Paso 3/3: Configurando auto_update")
            success_3, message_3, details_3 = (
                self.configure_auto_update_by_season_type()
            )
            master_results["steps_results"]["auto_update_config"] = {
                "success": success_3,
                "message": message_3,
                "details": details_3,
            }
            if success_3:
                master_results["sync_steps_completed"] += 1
            else:
                master_results["overall_success"] = False

            # Generar resumen final
            if master_results["overall_success"]:
                final_message = f"Sincronización maestra completada: {master_results['sync_steps_completed']}/{master_results['total_sync_steps']} pasos exitosos"
                logger.info(f"✅ {final_message}")
            else:
                final_message = f"Sincronización maestra con errores: {master_results['sync_steps_completed']}/{master_results['total_sync_steps']} pasos exitosos"
                logger.warning(f"⚠️ {final_message}")

            # Agregar resumen consolidado
            master_results["summary"] = {
                "total_seasons_processed": len(details_1.get("details", {})),
                "discrepancies_fixed": details_1.get("discrepancies_fixed", 0),
                "urls_generated": details_2.get("urls_generated", 0),
                "urls_updated": details_2.get("urls_updated", 0),
                "historical_seasons_disabled": details_3.get(
                    "historical_seasons_disabled", 0
                ),
                "current_seasons_enabled": details_3.get("current_seasons_enabled", 0),
            }

            return master_results["overall_success"], final_message, master_results

        except Exception as e:
            error_msg = f"Error crítico en sincronización maestra: {str(e)}"
            logger.error(error_msg)
            master_results["overall_success"] = False
            master_results["error"] = error_msg
            return False, error_msg, master_results

    def sync_all_comprehensive_data(self) -> Tuple[bool, str, Dict]:
        """
        Sincronización maestra extendida que incluye TODOS los campos de thai_league_seasons.
        Versión completa que actualiza file_size, total_records, unmatched_players, logs, etc.

        Returns:
            Tupla (success, message, comprehensive_results)
        """
        logger.info("🚀 Iniciando sincronización COMPLETA de todas las temporadas")

        comprehensive_results = {
            "sync_steps_completed": 0,
            "total_sync_steps": 4,
            "overall_success": True,
            "steps_results": {},
            "comprehensive_summary": {},
        }

        try:
            # Paso 1: Sincronizar estados y contadores básicos (función existente)
            logger.info("📊 Paso 1/4: Sincronizando estados y contadores básicos")
            success_1, message_1, details_1 = self.sync_season_status_from_real_data()
            comprehensive_results["steps_results"]["basic_sync"] = {
                "success": success_1,
                "message": message_1,
                "details": details_1,
            }
            if success_1:
                comprehensive_results["sync_steps_completed"] += 1
            else:
                comprehensive_results["overall_success"] = False

            # Paso 2: Recopilar y actualizar datos completos de cada temporada
            logger.info(
                "📁 Paso 2/4: Recopilando datos completos (file_size, total_records, etc.)"
            )
            comprehensive_sync_results = {
                "seasons_updated": 0,
                "total_file_size": 0,
                "total_csv_records": 0,
                "details": {},
            }

            with self.session_factory() as session:
                season_records = session.query(ThaiLeagueSeason).all()

                for season_record in season_records:
                    season_name = season_record.season
                    logger.info(f"  📋 Procesando {season_name}...")

                    # Recopilar datos completos
                    comprehensive_data = self.collect_comprehensive_season_data(
                        season_name
                    )

                    # Variables para tracking de cambios
                    changes_made = []

                    # Actualizar file_size
                    if (
                        comprehensive_data["file_size"]
                        and season_record.file_size != comprehensive_data["file_size"]
                    ):
                        old_size = season_record.file_size or 0
                        season_record.file_size = comprehensive_data["file_size"]
                        changes_made.append(
                            f"file_size: {old_size} → {comprehensive_data['file_size']}"
                        )
                        comprehensive_sync_results[
                            "total_file_size"
                        ] += comprehensive_data["file_size"]

                    # Actualizar total_records
                    if (
                        season_record.total_records
                        != comprehensive_data["total_records"]
                    ):
                        old_total = season_record.total_records or 0
                        season_record.total_records = comprehensive_data[
                            "total_records"
                        ]
                        changes_made.append(
                            f"total_records: {old_total} → {comprehensive_data['total_records']}"
                        )
                        comprehensive_sync_results[
                            "total_csv_records"
                        ] += comprehensive_data["total_records"]

                    # Actualizar unmatched_players
                    if (
                        season_record.unmatched_players
                        != comprehensive_data["unmatched_players"]
                    ):
                        old_unmatched = season_record.unmatched_players or 0
                        season_record.unmatched_players = comprehensive_data[
                            "unmatched_players"
                        ]
                        changes_made.append(
                            f"unmatched_players: {old_unmatched} → {comprehensive_data['unmatched_players']}"
                        )

                    # Actualizar errors_count si hay errores nuevos
                    if comprehensive_data["errors_count"] > 0:
                        season_record.errors_count = comprehensive_data["errors_count"]
                        changes_made.append(
                            f"errors_count: → {comprehensive_data['errors_count']}"
                        )

                    # Generar y actualizar logs
                    import_log, error_log = self.generate_import_logs(
                        season_name, comprehensive_data
                    )

                    if (
                        not season_record.import_log
                        or len(season_record.import_log) < 10
                    ):
                        season_record.import_log = import_log
                        changes_made.append("import_log: generado")

                    if error_log and not season_record.error_log:
                        season_record.error_log = error_log
                        changes_made.append("error_log: generado")

                    # Configurar settings de completitud
                    is_completed = season_record.import_status == ImportStatus.completed
                    completion_config = self.configure_completion_settings(
                        season_name, is_completed
                    )

                    for config_key, config_value in completion_config.items():
                        if hasattr(season_record, config_key):
                            old_value = getattr(season_record, config_key)
                            if old_value != config_value:
                                setattr(season_record, config_key, config_value)
                                changes_made.append(
                                    f"{config_key}: {old_value} → {config_value}"
                                )

                    # Actualizar timestamp si hubo cambios
                    if changes_made:
                        season_record.last_updated = datetime.now(timezone.utc)
                        comprehensive_sync_results["seasons_updated"] += 1

                    # Guardar detalles
                    comprehensive_sync_results["details"][season_name] = {
                        "file_size": comprehensive_data["file_size"],
                        "total_records": comprehensive_data["total_records"],
                        "matched_players": comprehensive_data["matched_players"],
                        "unmatched_players": comprehensive_data["unmatched_players"],
                        "changes_made": changes_made,
                        "cache_exists": comprehensive_data["cache_exists"],
                    }

                session.commit()

            comprehensive_results["steps_results"]["comprehensive_sync"] = {
                "success": True,
                "message": f"Datos completos actualizados: {comprehensive_sync_results['seasons_updated']} temporadas",
                "details": comprehensive_sync_results,
            }
            comprehensive_results["sync_steps_completed"] += 1

            # Paso 3: Generar URLs fuente (función existente)
            logger.info("🔗 Paso 3/4: Generando URLs fuente")
            success_3, message_3, details_3 = self.auto_generate_source_urls()
            comprehensive_results["steps_results"]["url_generation"] = {
                "success": success_3,
                "message": message_3,
                "details": details_3,
            }
            if success_3:
                comprehensive_results["sync_steps_completed"] += 1
            else:
                comprehensive_results["overall_success"] = False

            # Paso 4: Validación final
            logger.info("✅ Paso 4/4: Validación final del sistema")
            validation_results = self._validate_comprehensive_sync()
            comprehensive_results["steps_results"]["validation"] = {
                "success": validation_results["all_valid"],
                "message": f"Validación completada: {validation_results['valid_seasons']}/{validation_results['total_seasons']} temporadas válidas",
                "details": validation_results,
            }
            if validation_results["all_valid"]:
                comprehensive_results["sync_steps_completed"] += 1
            else:
                comprehensive_results["overall_success"] = False

            # Generar resumen final
            if comprehensive_results["overall_success"]:
                final_message = f"Sincronización COMPLETA exitosa: {comprehensive_results['sync_steps_completed']}/{comprehensive_results['total_sync_steps']} pasos completados"
                logger.info(f"✅ {final_message}")
            else:
                final_message = f"Sincronización COMPLETA con errores: {comprehensive_results['sync_steps_completed']}/{comprehensive_results['total_sync_steps']} pasos completados"
                logger.warning(f"⚠️ {final_message}")

            # Agregar resumen consolidado extendido
            comprehensive_results["comprehensive_summary"] = {
                "seasons_processed": len(details_1.get("details", {})),
                "discrepancies_fixed": details_1.get("discrepancies_fixed", 0),
                "comprehensive_updates": comprehensive_sync_results["seasons_updated"],
                "total_file_size_mb": round(
                    comprehensive_sync_results["total_file_size"] / (1024 * 1024), 2
                ),
                "total_csv_records": comprehensive_sync_results["total_csv_records"],
                "urls_generated": details_3.get("urls_generated", 0),
                "urls_updated": details_3.get("urls_updated", 0),
                "validation_passed": validation_results["all_valid"],
            }

            return (
                comprehensive_results["overall_success"],
                final_message,
                comprehensive_results,
            )

        except Exception as e:
            error_msg = f"Error crítico en sincronización completa: {str(e)}"
            logger.error(error_msg)
            comprehensive_results["overall_success"] = False
            comprehensive_results["error"] = error_msg
            return False, error_msg, comprehensive_results

    def _validate_comprehensive_sync(self) -> Dict:
        """
        Valida que todos los campos críticos estén correctamente poblados.

        Returns:
            Dict con resultados de validación
        """
        validation_results = {
            "total_seasons": 0,
            "valid_seasons": 0,
            "all_valid": True,
            "validation_details": {},
        }

        try:
            with self.session_factory() as session:
                seasons = session.query(ThaiLeagueSeason).all()
                validation_results["total_seasons"] = len(seasons)

                for season in seasons:
                    season_name = season.season
                    issues = []

                    # Validar campos críticos
                    if not season.file_size or season.file_size == 0:
                        issues.append("file_size missing")

                    if not season.total_records or season.total_records == 0:
                        issues.append("total_records missing")

                    if not season.source_url or len(season.source_url) < 10:
                        issues.append("source_url missing")

                    if not season.import_log or len(season.import_log) < 10:
                        issues.append("import_log missing")

                    # Contar como válida si no hay issues críticos
                    if len(issues) == 0:
                        validation_results["valid_seasons"] += 1
                    else:
                        validation_results["all_valid"] = False

                    validation_results["validation_details"][season_name] = {
                        "valid": len(issues) == 0,
                        "issues": issues,
                    }

                logger.info(
                    f"📊 Validación: {validation_results['valid_seasons']}/{validation_results['total_seasons']} temporadas válidas"
                )

        except Exception as e:
            logger.error(f"Error en validación: {str(e)}")
            validation_results["all_valid"] = False
            validation_results["error"] = str(e)

        return validation_results

    # === FUNCIONES DE LÓGICA ESTACIONAL ===

    def apply_seasonal_logic(self) -> Dict[str, Any]:
        """
        Aplica lógica estacional específica de Thai League:
        - Mayo-Junio: Marcar temporadas como completadas si >30 días sin actualizar
        - Julio-Agosto: Buscar nueva temporada en GitHub
        - Resto del año: Mantener configuración actual

        Returns:
            Dict con resultados de la aplicación de lógica estacional
        """
        try:
            current_date = datetime.now(timezone.utc)
            current_month = current_date.month

            results = {
                "month": current_month,
                "season_completed": [],
                "new_season_found": None,
                "actions_taken": [],
            }

            logger.info(
                f"🗓️ Aplicando lógica estacional Thai League - Mes actual: {current_month}"
            )

            # Mayo-Junio: Marcar temporadas como completadas
            if current_month in [5, 6]:  # Mayo y Junio
                logger.info(
                    "📅 Periodo de finalización (Mayo-Junio): evaluando temporadas"
                )
                completed_seasons = self._mark_seasons_completed_if_stale()
                results["season_completed"] = completed_seasons
                results["actions_taken"].append(
                    f"Evaluated season completion (month {current_month})"
                )

            # Julio-Agosto: Buscar nueva temporada
            elif current_month in [7, 8]:  # Julio y Agosto
                logger.info(
                    "🔍 Periodo de búsqueda (Julio-Agosto): buscando nueva temporada"
                )
                new_season = self._search_for_new_season()
                results["new_season_found"] = new_season
                results["actions_taken"].append(
                    f"Searched for new season (month {current_month})"
                )

            else:
                logger.info(
                    f"⏸️ Mes {current_month}: sin acciones estacionales específicas"
                )
                results["actions_taken"].append(
                    f"No seasonal actions for month {current_month}"
                )

            return results

        except Exception as e:
            error_msg = f"Error aplicando lógica estacional: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def _mark_seasons_completed_if_stale(self) -> List[str]:
        """
        Marca temporadas como completadas si llevan >30 días sin actualizar.
        Solo en meses de mayo y junio.
        Incluye lógica específica para temporada 2024-25 en agosto 2025.

        Returns:
            Lista de temporadas marcadas como completadas
        """
        completed_seasons = []

        try:
            with self.session_factory() as session:
                # Buscar temporadas que podrían necesitar ser marcadas como completadas
                seasons = (
                    session.query(ThaiLeagueSeason)
                    .filter(
                        ThaiLeagueSeason.import_status.in_(
                            [
                                ImportStatus.in_progress,
                                ImportStatus.updated,
                                ImportStatus.completed,
                            ]
                        ),
                        ThaiLeagueSeason.auto_update_enabled == True,
                    )
                    .all()
                )

                current_date = datetime.now(timezone.utc)
                current_year = current_date.year
                current_month = current_date.month

                for season in seasons:
                    should_mark_completed = False
                    reason = ""

                    # Lógica específica para temporada 2024-25
                    if season.season in ["24-25", "2024-25"] and current_year == 2025:
                        if (
                            current_month >= 7
                        ):  # Julio o después - temporada terminó hace >60 días
                            should_mark_completed = True
                            reason = "2024-25 season ended in May/June, auto-update should be disabled"

                    # Lógica general de >30 días
                    elif season.last_updated:
                        days_since_update = (current_date - season.last_updated).days
                        if days_since_update > 30:
                            should_mark_completed = True
                            reason = f"No updates for {days_since_update} days"

                    if should_mark_completed:
                        # Marcar como completada y deshabilitar auto-update
                        season.import_status = ImportStatus.completed
                        season.auto_update_enabled = False
                        season.update_frequency_days = 0
                        season.notes = self.generate_contextual_notes(season.season)
                        season.last_updated = current_date

                        completed_seasons.append(season.season)
                        logger.info(
                            f"✅ Temporada {season.season} marcada como completada: {reason}"
                        )

                if completed_seasons:
                    session.commit()
                    logger.info(
                        f"💾 Guardadas {len(completed_seasons)} temporadas como completadas"
                    )

        except Exception as e:
            logger.error(f"Error marcando temporadas completadas: {str(e)}")

        return completed_seasons

    def _search_for_new_season(self) -> Optional[str]:
        """
        Busca nueva temporada en GitHub con patrón 'Thai League 1 XX-XX'.
        Solo en meses de julio y agosto.

        Returns:
            Nombre de la nueva temporada si se encuentra, None en caso contrario
        """
        try:
            # Determinar qué temporada buscar (siguiente año)
            current_year = datetime.now().year
            next_season_start = str(current_year + 1)[-2:]  # Últimos 2 dígitos
            next_season_end = str(current_year + 2)[-2:]  # Últimos 2 dígitos
            next_season = f"{next_season_start}-{next_season_end}"

            logger.info(f"🔍 Buscando temporada: {next_season}")

            # Verificar si ya existe en BD
            with self.session_factory() as session:
                existing = (
                    session.query(ThaiLeagueSeason)
                    .filter(ThaiLeagueSeason.season == next_season)
                    .first()
                )

                if existing:
                    logger.info(f"⚠️ Temporada {next_season} ya existe en BD")
                    return None

            # Buscar en GitHub usando patrón "Thai League 1 XX-XX"
            expected_filename = f"Thai League 1 {next_season}"
            success, df, message = self.download_season_data(next_season)

            if success and df is not None:
                # Nueva temporada encontrada - crear registro
                with self.session_factory() as session:
                    new_season_record = ThaiLeagueSeason(
                        season=next_season,
                        import_status=ImportStatus.pending,
                        source_url=self._generate_github_url(next_season),
                        notes=f"New season detected automatically in search period",
                        auto_update_enabled=True,
                        update_frequency_days=7,
                    )

                    session.add(new_season_record)
                    session.commit()

                    logger.info(
                        f"🎉 Nueva temporada {next_season} detectada y registrada"
                    )
                    return next_season
            else:
                logger.info(f"🔍 Temporada {next_season} aún no disponible en GitHub")
                return None

        except Exception as e:
            logger.error(f"Error buscando nueva temporada: {str(e)}")
            return None

    def generate_contextual_notes(self, season: str) -> str:
        """
        Genera notas contextuales para una temporada basándose en su estado real.
        Considera específicamente el calendario Thai League y la regla de >30 días.

        Args:
            season: Temporada en formato "XX-XX"

        Returns:
            Nota contextual apropiada
        """
        try:
            season_year = self._parse_season_year(season)
            current_year = datetime.now().year
            current_month = datetime.now().month
            current_date = datetime.now(timezone.utc)

            # Lógica específica para temporada 2024-25
            if season == "24-25" or season == "2024-25":
                # Thai League 2024-25 terminó en mayo/junio 2025
                # En agosto 2025, ya han pasado >60 días desde finalización
                if current_year == 2025 and current_month >= 7:  # Julio o después
                    return "Completed season - finished in May/June 2025, auto-update disabled"
                elif current_year == 2025 and current_month >= 5:  # Mayo-Junio
                    return "Completed season - ending period, auto-update disabled"
                else:
                    return "Current season 2024-25 - in progress"

            # Lógica general de temporada Thai League (Feb-Oct)
            thai_league_start_month = 2  # Febrero
            thai_league_end_month = 10  # Octubre

            if season_year < current_year - 1:
                return f"Historical season {season} - auto-update disabled"
            elif season_year == current_year - 1:
                # Temporada del año anterior (ej: 2024 cuando estamos en 2025)
                if (
                    current_month >= 7
                ):  # Julio o después, temporada definitivamente terminada
                    return f"Completed season {season} - finished last year, auto-update disabled"
                elif current_month >= thai_league_end_month:  # Oct-Dic
                    return f"Completed season {season} - recently finished"
                else:
                    return f"Historical season {season} - auto-update disabled"
            elif season_year == current_year:
                # Temporada del año actual
                if current_month < thai_league_start_month:  # Antes de Feb
                    return f"Pending season {season} - not yet started"
                elif current_month <= thai_league_end_month:  # Feb-Oct
                    return f"Current season {season} - in progress"
                else:  # Nov-Dic
                    return f"Completed season {season} - ended this year"
            else:  # season_year > current_year
                return f"Future season {season} - upcoming"

        except Exception as e:
            logger.error(f"Error generando notas contextuales: {str(e)}")
            return "Season status unknown"

    def sync_seasonal_data(self) -> Dict[str, Any]:
        """
        Función master que ejecuta sincronización completa con lógica estacional.
        Combina todas las correcciones y mejoras implementadas.

        Returns:
            Dict con resultados completos de la sincronización
        """
        try:
            logger.info("🔄 Iniciando sincronización estacional Thai League")

            results = {
                "seasonal_logic": {},
                "file_sizes_updated": 0,
                "notes_updated": 0,
                "comprehensive_sync": {},
                "success": True,
                "message": "",
            }

            # 1. Aplicar lógica estacional específica
            logger.info("📅 Aplicando lógica estacional")
            seasonal_results = self.apply_seasonal_logic()
            results["seasonal_logic"] = seasonal_results

            # File sizes ya migrados a formato MB en base de datos

            # 3. Actualizar notas contextuales
            logger.info("📝 Actualizando notas contextuales")
            notes_updated = self._update_contextual_notes()
            results["notes_updated"] = notes_updated

            # 4. Ejecutar sincronización comprehensiva existente
            logger.info("🔄 Ejecutando sincronización comprehensiva")
            comprehensive_results = self.sync_all_comprehensive_data()
            results["comprehensive_sync"] = comprehensive_results

            # 5. Aplicar correcciones específicas a temporada 2024-25 (DESPUÉS de sync comprehensivo)
            logger.info(
                "🔧 Aplicando correcciones específicas a temporada 2024-25 (paso final)"
            )
            corrections_2024_result = self.apply_2024_25_corrections()
            results["2024_25_corrections"] = corrections_2024_result

            # 6. Generar mensaje de resumen
            summary_parts = []
            if corrections_2024_result.get("corrections_applied"):
                summary_parts.append(
                    f"2024-25 corrections: {len(corrections_2024_result['corrections_applied'])}"
                )
            if seasonal_results.get("season_completed"):
                summary_parts.append(
                    f"{len(seasonal_results['season_completed'])} seasons completed"
                )
            if seasonal_results.get("new_season_found"):
                summary_parts.append(
                    f"new season {seasonal_results['new_season_found']} detected"
                )
            if results["file_sizes_updated"] > 0:
                summary_parts.append(f"{results['file_sizes_updated']} file sizes updated")
            if results["notes_updated"] > 0:
                summary_parts.append(f"{results['notes_updated']} notes updated")

            if summary_parts:
                results["message"] = (
                    f"Seasonal sync completed: {', '.join(summary_parts)}"
                )
            else:
                results["message"] = "Seasonal sync completed: no changes required"

            logger.info(
                f"✅ Sincronización estacional completada: {results['message']}"
            )
            return results

        except Exception as e:
            error_msg = f"Error en sincronización estacional: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _update_contextual_notes(self) -> int:
        """
        Actualiza las notas de todas las temporadas con contenido contextual apropiado.

        Returns:
            Número de registros actualizados
        """
        updated_count = 0

        try:
            with self.session_factory() as session:
                seasons = session.query(ThaiLeagueSeason).all()

                for season in seasons:
                    # Generar nota contextual apropiada
                    new_note = self.generate_contextual_notes(season.season)

                    # Verificar si necesita actualización
                    if season.notes != new_note:
                        season.notes = new_note
                        updated_count += 1
                        logger.debug(
                            f"Actualizada nota para {season.season}: '{new_note}'"
                        )

                if updated_count > 0:
                    session.commit()
                    logger.info(f"✅ Actualizadas {updated_count} notas contextuales")

        except Exception as e:
            logger.error(f"Error actualizando notas contextuales: {str(e)}")

        return updated_count

    def apply_2024_25_corrections(self) -> Dict[str, Any]:
        """
        Aplica correcciones específicas a la temporada 2024-25 basándose en el feedback del usuario:
        - Notas deben indicar que la temporada terminó
        - Auto-update debe estar OFF (terminó hace >2 meses)
        - Frecuencia debe ser 0

        Returns:
            Dict con resultado de las correcciones
        """
        try:
            current_date = datetime.now(timezone.utc)
            current_year = current_date.year
            current_month = current_date.month

            corrections_applied = []

            with self.session_factory() as session:
                # Buscar temporada 2024-25
                season = (
                    session.query(ThaiLeagueSeason)
                    .filter(ThaiLeagueSeason.season.in_(["24-25", "2024-25"]))
                    .first()
                )

                if not season:
                    return {
                        "success": False,
                        "message": "Temporada 2024-25 no encontrada",
                    }

                logger.info(
                    f"🔧 Aplicando correcciones específicas a temporada {season.season}"
                )

                # Corrección 1: Notas contextuales correctas
                old_notes = season.notes
                new_notes = self.generate_contextual_notes(season.season)
                if old_notes != new_notes:
                    season.notes = new_notes
                    corrections_applied.append(f"Notes: '{old_notes}' → '{new_notes}'")

                # Corrección 2: Auto-update debe estar OFF para temporada terminada
                if season.auto_update_enabled:
                    season.auto_update_enabled = False
                    corrections_applied.append("Auto-update: ON → OFF")

                # Corrección 3: Frecuencia debe ser 0 para temporada terminada
                if season.update_frequency_days != 0:
                    old_freq = season.update_frequency_days
                    season.update_frequency_days = 0
                    corrections_applied.append(f"Frequency: {old_freq} days → 0 days")

                # Corrección 4: Estado debe ser completed
                if season.import_status != ImportStatus.completed:
                    old_status = season.import_status.value
                    season.import_status = ImportStatus.completed
                    corrections_applied.append(f"Status: {old_status} → completed")

                # Actualizar timestamp
                season.last_updated = current_date

                if corrections_applied:
                    session.commit()
                    logger.info(
                        f"✅ Aplicadas {len(corrections_applied)} correcciones a temporada {season.season}"
                    )
                    for correction in corrections_applied:
                        logger.info(f"   - {correction}")
                else:
                    logger.info(
                        f"ℹ️ Temporada {season.season} ya tiene configuración correcta"
                    )

                return {
                    "success": True,
                    "season": season.season,
                    "corrections_applied": corrections_applied,
                    "message": (
                        f"Temporada {season.season}: {len(corrections_applied)} correcciones aplicadas"
                        if corrections_applied
                        else f"Temporada {season.season} ya configurada correctamente"
                    ),
                }

        except Exception as e:
            error_msg = f"Error aplicando correcciones a temporada 2024-25: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def smart_weekly_update(self) -> Dict[str, Any]:
        """
        Actualización inteligente semanal que incluye lógica estacional.
        Esta función es llamada por el scheduler desde sync_coordinator.

        Returns:
            Dict con resultado de la actualización
        """
        try:
            logger.info(
                "🔄 Ejecutando actualización semanal inteligente con lógica estacional"
            )

            # Ejecutar sincronización estacional completa
            results = self.sync_seasonal_data()

            # Formatear respuesta para el scheduler
            if results.get("success", True):
                return {
                    "action": "seasonal_sync",
                    "success": True,
                    "message": results.get("message", "Seasonal sync completed"),
                    "stats": {
                        "seasonal_actions": len(
                            results.get("seasonal_logic", {}).get("actions_taken", [])
                        ),
                        "file_sizes_updated": results.get("file_sizes_updated", 0),
                        "notes_updated": results.get("notes_updated", 0),
                        "seasons_completed": len(
                            results.get("seasonal_logic", {}).get(
                                "season_completed", []
                            )
                        ),
                        "new_season_found": results.get("seasonal_logic", {}).get(
                            "new_season_found"
                        )
                        is not None,
                    },
                }
            else:
                return {
                    "action": "seasonal_sync_error",
                    "success": False,
                    "message": results.get("error", "Unknown error in seasonal sync"),
                    "stats": {},
                }

        except Exception as e:
            error_msg = f"Error en actualización semanal: {str(e)}"
            logger.error(error_msg)
            return {
                "action": "weekly_update_error",
                "success": False,
                "message": error_msg,
                "stats": {},
            }

    # === LÓGICA INTELIGENTE DE DETERMINACIÓN DE ESTADO DE EQUIPOS ===

    def get_team_info(self, stats_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determina información inteligente del equipo basada en el análisis de datos.

        Lógica híbrida:
        - Analiza temporada actual vs histórica
        - Maneja transferencias y estados de jugadores
        - Determina equipo a mostrar según contexto

        Args:
            stats_record: Diccionario con datos del jugador

        Returns:
            Diccionario con información procesada del equipo
        """
        team_current = stats_record.get("team") or ""
        team_start = stats_record.get("team_within_timeframe") or ""
        season = stats_record.get("season", "")

        # Normalizar valores nan/None a string vacío
        if team_current in ["nan", None, "None"]:
            team_current = ""
        if team_start in ["nan", None, "None"]:
            team_start = ""

        # Determinar si es temporada actual
        is_current = self.is_current_season(stats_record)

        # Aplicar lógica contextual
        team_status = self.determine_team_status(
            team_current, team_start, season, is_current
        )

        # Obtener información formateada para UI
        display_info = self.get_team_display_info(
            team_current, team_start, team_status, stats_record
        )

        # Validar URL del logo si existe
        logo_url = stats_record.get("team_logo_url")
        if logo_url:
            logo_url = self.validate_team_logo_url(logo_url)

        logger.debug(
            f"Team info processed - Player: {stats_record.get('player_name')}, "
            f"Season: {season}, Current: '{team_current}', Start: '{team_start}', "
            f"Status: {team_status}, Display: {display_info['team_display']}"
        )

        return {
            "team_current": team_current,
            "team_start": team_start,
            "team_status": team_status,
            "team_display": display_info["team_display"],
            "status_message": display_info["status_message"],
            "logo_url": logo_url,
            "is_current_season": is_current,
            "has_transfer": bool(
                team_current != team_start and team_current and team_start
            ),
        }

    def is_current_season(self, stats_record: Dict[str, Any]) -> bool:
        """
        Determina si el registro corresponde a la temporada actual.

        Args:
            stats_record: Diccionario con datos del jugador

        Returns:
            True si es temporada actual, False si es histórica
        """
        season = stats_record.get("season", "")

        # Para este proyecto, consideramos 2024-25 como la temporada actual
        # debido a que los datos más recientes son de esta temporada
        current_season = "2024-25"

        # Alternativamente, se puede calcular dinámicamente:
        # current_date = self._get_current_datetime()
        # current_year = current_date.year
        # if current_date.month >= 8:  # Agosto en adelante
        #     current_season = f"{current_year}-{str(current_year + 1)[-2:]}"
        # else:  # Enero a Julio
        #     current_season = f"{current_year - 1}-{str(current_year)[-2:]}"

        return season == current_season

    def determine_team_status(
        self, team_current: str, team_start: str, season: str, is_current: bool
    ) -> str:
        """
        Determina el estado del jugador respecto a equipos.

        Args:
            team_current: Equipo actual
            team_start: Equipo al inicio del periodo
            season: Temporada
            is_current: Si es temporada actual

        Returns:
            Estado del equipo: 'active', 'transferred', 'free_agent', 'historical'
        """
        # Casos sin equipos
        if not team_current and not team_start:
            return "free_agent"

        # Solo tiene equipo actual
        if team_current and not team_start:
            return "active" if is_current else "historical"

        # Solo tiene equipo de inicio (raro pero posible)
        if team_start and not team_current:
            return "free_agent" if is_current else "historical"

        # Ambos equipos presentes
        if team_current == team_start:
            return "active" if is_current else "historical"
        else:
            return "transferred" if is_current else "historical"

    def get_team_display_info(
        self,
        team_current: str,
        team_start: str,
        team_status: str,
        stats_record: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Obtiene información formateada del equipo para mostrar en la UI.

        Args:
            team_current: Equipo actual
            team_start: Equipo al inicio
            team_status: Estado determinado
            stats_record: Datos completos del jugador

        Returns:
            Diccionario con team_display y status_message
        """
        player_name = stats_record.get("player_name", "Jugador")
        season = stats_record.get("season", "")

        if team_status == "free_agent":
            return {
                "team_display": "Agente libre",
                "status_message": f"{player_name} sin equipo en {season}",
            }

        elif team_status == "transferred":
            return {
                "team_display": team_current,
                "status_message": f"{player_name} transferido de {team_start} a {team_current}",
            }

        elif team_status == "active":
            display_team = team_current or team_start
            return {
                "team_display": display_team,
                "status_message": f"{player_name} activo en {display_team}",
            }

        else:  # historical
            display_team = team_current or team_start
            return {
                "team_display": display_team,
                "status_message": f"{player_name} histórico en {display_team} ({season})",
            }

    def validate_team_logo_url(self, url: str) -> Optional[str]:
        """
        Valida y normaliza URL del logo del equipo.

        Args:
            url: URL a validar

        Returns:
            URL válida o None si no es válida
        """
        if not url or url in ["nan", "None", "null"]:
            return None

        # Normalizar URL
        url = url.strip()

        # Validación básica de formato URL
        if not url.startswith(("http://", "https://")):
            # Asumir https si no tiene protocolo
            url = f"https://{url}"

        # Validar extensiones de imagen comunes
        valid_extensions = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
        if not any(url.lower().endswith(ext) for ext in valid_extensions):
            logger.warning(f"Logo URL might not be an image: {url}")

        return url

    def process_team_data_with_intelligence(
        self, stats_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Procesa datos de equipo aplicando lógica inteligente.
        Solo actualiza campos que existen en el modelo ProfessionalStats.

        Args:
            stats_record: Registro de estadísticas del jugador

        Returns:
            Registro actualizado con información de equipos (solo campos del modelo)
        """
        # Obtener información inteligente del equipo
        team_info = self.get_team_info(stats_record)

        # Solo actualizar campos que existen en el modelo ProfessionalStats
        # Los campos calculados (team_status, has_transfer, etc.) se procesan
        # dinámicamente cuando se necesitan para visualización

        # Si team_within_timeframe no está ya en el record, usar el team_display
        if (
            "team_within_timeframe" not in stats_record
            or not stats_record["team_within_timeframe"]
        ):
            stats_record["team_within_timeframe"] = team_info.get("team_display")

        return stats_record

    # =====================================================================
    # NUEVO PIPELINE ETL MODULAR - MÉTODOS DE INTEGRACIÓN
    # =====================================================================

    @property
    def etl_controller(self):
        """Lazy loading del controlador ETL."""
        if self._etl_controller is None:
            from controllers.etl_controller import ETLController

            self._etl_controller = ETLController(self.session_factory)
        return self._etl_controller

    def process_season_with_modular_etl(
        self, season: str, threshold: int = 85, force_reload: bool = False
    ) -> Tuple[bool, str, Dict]:
        """
        Procesa una temporada usando el nuevo pipeline ETL modular.

        Esta es la nueva implementación que resuelve los problemas identificados:
        - David Cuerva Team="" → Team=None consistente
        - Validación robusta antes de inserción BD
        - Pipeline separado: Extract → Transform → Load → Validate → Analyze

        Args:
            season: Temporada a procesar (ej: "2024-25")
            threshold: Umbral para fuzzy matching (0-100)
            force_reload: Si forzar recarga aunque existan datos

        Returns:
            Tuple[success, message, comprehensive_results]
        """
        logger.info(
            f"🚀 Procesando {season} con pipeline ETL modular (threshold={threshold})"
        )

        try:
            # Ejecutar pipeline ETL completo
            success, message, results = self.etl_controller.execute_full_pipeline(
                season, threshold, force_reload
            )

            if success:
                logger.info(f"✅ Pipeline ETL exitoso para {season}: {message}")
            else:
                logger.error(f"❌ Pipeline ETL falló para {season}: {message}")

            return success, message, results

        except Exception as e:
            error_msg = (
                f"Error inesperado en pipeline ETL modular para {season}: {str(e)}"
            )
            logger.error(error_msg)
            return False, error_msg, {"errors": [error_msg]}

    def get_season_processing_status(self, season: str) -> Dict:
        """
        Obtiene el estado de procesamiento de una temporada.

        Args:
            season: Temporada a consultar

        Returns:
            Dict con estado del procesamiento
        """
        return self.etl_controller.get_processing_status(season)

    def get_available_seasons_for_etl(self) -> Dict[str, str]:
        """
        Obtiene temporadas disponibles para procesamiento ETL.

        Returns:
            Dict con temporadas disponibles
        """
        return self.etl_controller.get_available_seasons()

    def cleanup_and_reprocess_season(self, season: str) -> Tuple[bool, str]:
        """
        Limpia datos existentes y reprocesa una temporada.

        Args:
            season: Temporada a limpiar y reprocesar

        Returns:
            Tuple[success, message]
        """
        return self.etl_controller.cleanup_and_reprocess(season)

    def validate_season_data_quality(self, season: str) -> Dict:
        """
        Ejecuta validación de calidad de datos para una temporada.

        Args:
            season: Temporada a validar

        Returns:
            Dict con resultados de validación
        """
        try:
            # Descargar datos
            success, df, message = self.download_season_data(season)
            if not success:
                return {"error": f"No se pudieron descargar datos: {message}"}

            # Ejecutar validación usando el nuevo validator
            validator = self.etl_controller.validator
            is_valid, errors, stats = validator.validate_dataframe(df, season)

            return {
                "season": season,
                "is_valid": is_valid,
                "errors": errors,
                "stats": stats,
                "message": f"Validación completada: {stats['valid_records']}/{stats['total_records']} válidos",
            }

        except Exception as e:
            return {"error": f"Error en validación: {str(e)}"}

    # =====================================================================
    # MÉTODO DE TRANSICIÓN - COMPATIBILIDAD HACIA ATRÁS
    # =====================================================================

    def process_season_data_enhanced(
        self, season: str, use_modular_etl: bool = True, **kwargs
    ) -> Tuple[bool, str, Dict]:
        """
        Método de transición que permite usar el pipeline ETL modular o el legacy.

        Args:
            season: Temporada a procesar
            use_modular_etl: Si usar el nuevo pipeline ETL (por defecto True)
            **kwargs: Argumentos adicionales

        Returns:
            Tuple[success, message, results]
        """
        if use_modular_etl:
            logger.info(f"🔄 Usando pipeline ETL modular para {season}")
            return self.process_season_with_modular_etl(
                season,
                threshold=kwargs.get("threshold", 85),
                force_reload=kwargs.get("force_reload", False),
            )
        else:
            logger.info(f"⚠️ Usando pipeline legacy para {season}")
            # Aquí iría la llamada al método legacy original
            # Por ahora, redirigir al modular
            return self.process_season_with_modular_etl(season, **kwargs)

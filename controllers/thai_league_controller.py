"""
Thai League Controller - Sistema de extracción y procesamiento de datos
Maneja la descarga, limpieza y matching de estadísticas de la liga tailandesa
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
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
        "Player": "player_name",
        "Full name": "full_name",
        "Wyscout id": "wyscout_id",
        "Team": "team",
        "Competition": "competition",
        "Age": "age",
        "Birthday": "birthday",
        "Birth country": "birth_country",
        "Passport country": "passport_country",
        "Primary position": "primary_position",
        "Secondary position": "secondary_position",
        "Third position": "third_position",
        "Matches played": "matches_played",
        "Minutes played": "minutes_played",
        "Goals": "goals",
        "Assists": "assists",
        "Market value": "market_value",
        "Defensive actions": "defensive_actions",
        "Defensive duels": "defensive_duels",
        "Defensive duels won": "defensive_duels_won",
        "Aerial duels": "aerial_duels",
        "Aerial duels won": "aerial_duels_won",
        "Sliding tackles": "sliding_tackles",
        "Interceptions": "interceptions",
        "Fouls": "fouls",
        "Shots": "shots",
        "Shots on target": "shots_on_target",
        "Shot accuracy": "shot_accuracy",
        "Goal conversion": "goal_conversion",
        "Dribbles": "dribbles",
        "Dribbles successful": "dribbles_successful",
        "Progressive runs": "progressive_runs",
        "Passes": "passes",
        "Passes accurate": "passes_accurate",
        "Pass accuracy": "pass_accuracy",
        "Forward passes": "forward_passes",
        "Back passes": "back_passes",
        "Long passes": "long_passes",
        "Long passes accurate": "long_passes_accurate",
        "Expected goals": "expected_goals",
        "Expected assists": "expected_assists",
        "Progressive passes": "progressive_passes",
        "Key passes": "key_passes",
        "Crosses": "crosses",
        "Crosses accurate": "crosses_accurate",
        "Yellow cards": "yellow_cards",
        "Red cards": "red_cards",
    }

    def __init__(self):
        self.session_factory = get_db_session
        self.cache_dir = self._get_cache_directory()
        self._ensure_cache_directory()

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

        # Obtener jugadores profesionales existentes
        with self.session_factory() as session:
            existing_players = (
                session.query(Player, User)
                .join(User, Player.user_id == User.user_id)
                .filter(
                    Player.is_professional is True, User.user_type == UserType.player
                )
                .all()
            )

        results = {
            "exact_matches": [],
            "fuzzy_matches": [],
            "no_matches": [],
            "multiple_matches": [],
        }

        for _, row in df.iterrows():
            full_name = row.get("Full name")
            wyscout_id = str(row.get("Wyscout id", ""))

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
        self, players: List[Tuple[Player, User]], wyscout_id: str
    ) -> Optional[Dict]:
        """Busca jugador por WyscoutID exacto."""
        if not wyscout_id:
            return None

        for player, user in players:
            if player.wyscout_id == wyscout_id:
                return {
                    "player_id": player.player_id,
                    "user_id": user.user_id,
                    "name": user.name,
                    "wyscout_id": player.wyscout_id,
                }
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
                                == str(player_data.get("Wyscout id", "")),
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
                            player.wyscout_id = str(player_data.get("Wyscout id", ""))

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
                        "age",
                        "matches_played",
                        "minutes_played",
                        "goals",
                        "assists",
                        "shots",
                        "yellow_cards",
                        "red_cards",
                    ]
                    and value is not None
                ):
                    try:
                        value = int(float(value)) if not pd.isna(value) else None
                    except (ValueError, TypeError):
                        value = None

                record[db_field] = value

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

                result = []
                for stat in stats:
                    result.append(
                        {
                            "season": stat.season,
                            "team": stat.team,
                            "age": stat.age,
                            "matches_played": stat.matches_played,
                            "minutes_played": stat.minutes_played,
                            "goals": stat.goals,
                            "assists": stat.assists,
                            "shots": stat.shots,
                            "shots_on_target": stat.shots_on_target,
                            "shot_accuracy": stat.shot_accuracy,
                            "pass_accuracy": stat.pass_accuracy,
                            "defensive_actions": stat.defensive_actions,
                            "interceptions": stat.interceptions,
                            "expected_goals": stat.expected_goals,
                            "expected_assists": stat.expected_assists,
                            "market_value": stat.market_value,
                        }
                    )

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
            df["Wyscout id"] = df["Wyscout id"].fillna("").astype(str)
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
                                "wyscout_id": str(row["Wyscout id"]),
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
                            "file_size_kb": round(size / 1024, 2),
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

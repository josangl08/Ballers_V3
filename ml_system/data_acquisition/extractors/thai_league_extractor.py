"""
Extractor Module - Maneja la descarga de datos desde fuentes externas
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
from models import Player, ProfessionalStats, ThaiLeagueSeason

logger = logging.getLogger(__name__)


class ThaiLeagueExtractor:
    """
    Extractor para datos de la liga tailandesa desde GitHub.
    Maneja descarga, cache y validación de archivos fuente.
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

    def __init__(self, session_factory=None):
        """
        Inicializa el extractor.

        Args:
            session_factory: Factory para sesiones de BD (opcional)
        """
        self.session_factory = session_factory or get_db_session
        # DATABASE_PATH apunta al archivo .db dentro del directorio data
        self.cache_dir = Path(DATABASE_PATH).parent / "thai_league_cache"
        self.processed_dir = Path(DATABASE_PATH).parent / "thai_league_processed"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

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

    def _load_from_cache(self, season: str) -> Optional[str]:
        """
        Carga datos desde cache local.

        Args:
            season: Temporada a cargar

        Returns:
            Contenido del archivo o None si no existe
        """
        cache_file = self.cache_dir / f"thai_league_{season}.csv"
        try:
            if cache_file.exists():
                return cache_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Error leyendo cache para {season}: {e}")
        return None

    def _save_to_cache(self, season: str, content: str, file_hash: str) -> None:
        """
        Guarda datos en cache local.

        Args:
            season: Temporada a guardar
            content: Contenido del archivo
            file_hash: Hash del archivo para validación
        """
        cache_file = self.cache_dir / f"thai_league_{season}.csv"
        try:
            cache_file.write_text(content, encoding="utf-8")
            logger.info(f"💾 Cache actualizado para temporada {season}")
        except Exception as e:
            logger.warning(f"Error guardando cache para {season}: {e}")

    def calculate_file_hash(self, content: str) -> str:
        """
        Calcula hash SHA-256 del contenido del archivo.

        Args:
            content: Contenido del archivo

        Returns:
            Hash hexadecimal
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get_available_seasons(self) -> dict:
        """
        Obtiene las temporadas disponibles para descarga.

        Returns:
            Dict con temporadas disponibles
        """
        return self.AVAILABLE_SEASONS.copy()

    def validate_season(self, season: str) -> bool:
        """
        Valida que una temporada esté disponible.

        Args:
            season: Temporada a validar

        Returns:
            True si la temporada está disponible
        """
        return season in self.AVAILABLE_SEASONS

    def _is_current_season(self, season: str) -> bool:
        """
        Determina si es la temporada actual.
        Migrado desde ThaiLeagueController para compatibilidad con Smart Update System.

        Args:
            season: Temporada a verificar (formato "24-25")

        Returns:
            True si es la temporada actual
        """
        from datetime import datetime

        try:
            current_year = datetime.now().year
            season_years = season.split("-")
            if len(season_years) == 2:
                start_year = int(f"20{season_years[0]}")
                return start_year == current_year or start_year == current_year - 1
            return False
        except (ValueError, IndexError):
            logger.warning(f"Invalid season format: {season}")
            return False

    def get_source_url(self, season: str) -> Optional[str]:
        """
        Obtiene la URL fuente para una temporada.

        Args:
            season: Temporada solicitada

        Returns:
            URL o None si la temporada no está disponible
        """
        if not self.validate_season(season):
            return None

        filename = self.AVAILABLE_SEASONS[season]
        return (
            f"{self.GITHUB_BASE_URL}/{self.COMMIT_HASH}/Main App/"
            f"{filename.replace(' ', '%20')}"
        )

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

    def search_players_in_csv(
        self, player_name: str, threshold: int = 60
    ) -> List[Dict]:
        """
        Busca jugadores en el archivo de datos procesados y limpios.
        Optimizado para usar processed_complete.csv con datos ya normalizados.

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

            # Buscar en el archivo procesado consolidado
            processed_file = self.processed_dir / "processed_complete.csv"
            if not processed_file.exists():
                logger.warning(f"Archivo procesado no encontrado: {processed_file}")
                return []

            # Leer datos procesados (ya limpios y normalizados)
            df = pd.read_csv(processed_file)

            # Asegurar que las columnas existen y están limpias
            required_columns = [
                "Player",
                "Full name",
                "Team",
                "Team within selected timeframe",
                "Wyscout id",
                "Primary position",
                "Birthday",
                "season",
            ]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(
                    f"Columnas faltantes en archivo procesado: {missing_columns}"
                )
                return []

            # Limpiar datos nulos
            df["Player"] = df["Player"].fillna("").astype(str)
            df["Full name"] = df["Full name"].fillna("").astype(str)
            df["Team"] = df["Team"].fillna("").astype(str)
            df["Team within selected timeframe"] = (
                df["Team within selected timeframe"].fillna("").astype(str)
            )
            df["Wyscout id"] = df["Wyscout id"].fillna(0).astype(int)
            df["Primary position"] = df["Primary position"].fillna("").astype(str)
            df["Birthday"] = df["Birthday"].fillna("").astype(str)
            df["season"] = df["season"].fillna("").astype(str)

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
                        # Lógica de fallback para equipos:
                        # 1. Usar Team (equipo actual/final)
                        # 2. Si vacío, usar Team within selected timeframe (equipo inicial)
                        # 3. Si ambos vacíos, mostrar "No Team"
                        current_team = row["Team"].strip() if row["Team"] else ""
                        initial_team = (
                            row["Team within selected timeframe"].strip()
                            if row["Team within selected timeframe"]
                            else ""
                        )

                        if current_team:
                            display_team = current_team
                        elif initial_team:
                            display_team = initial_team
                        else:
                            display_team = "No Team"

                        matches.append(
                            {
                                "wyscout_id": int(row["Wyscout id"]),
                                "player_name": row["Player"],
                                "full_name": row["Full name"],
                                "team_name": display_team,
                                "position": row[
                                    "Primary position"
                                ],  # Usar posición procesada
                                "birthday": row["Birthday"],
                                "confidence": max_confidence,
                                "season": row[
                                    "season"
                                ],  # Usar temporada del archivo procesado
                            }
                        )

            # Ordenar por confidence score descendente
            matches.sort(key=lambda x: x["confidence"], reverse=True)

            # Deduplicar por WyscoutID manteniendo solo la temporada más reciente
            unique_players = {}
            for match in matches:
                wyscout_id = match["wyscout_id"]
                season = match["season"]

                # Si no existe o la temporada es más reciente, actualizar
                if (
                    wyscout_id not in unique_players
                    or season > unique_players[wyscout_id]["season"]
                ):
                    unique_players[wyscout_id] = match

            # Convertir de vuelta a lista y ordenar por confidence
            deduplicated_matches = list(unique_players.values())
            deduplicated_matches.sort(key=lambda x: x["confidence"], reverse=True)

            logger.info(
                f"Búsqueda en datos procesados para '{player_name}': {len(matches)} → {len(deduplicated_matches)} resultados (deduplicados)"
            )
            return deduplicated_matches

        except Exception as e:
            logger.error(
                f"Error buscando en datos procesados para '{player_name}': {e}"
            )
            return []

    def _normalize_name(self, name: Union[str, None]) -> Optional[str]:
        """
        Normaliza nombres para matching consistente.
        Migrado desde ThaiLeagueController para compatibilidad.

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

    def _normalize_team_for_db(
        self, team: Union[str, None], team_within_timeframe: Union[str, None]
    ) -> str:
        """
        Normaliza nombres de equipos aplicando lógica de fallback para base de datos.
        Garantiza que siempre devuelve un string válido (nunca None/nan).

        Args:
            team: Equipo actual (Team column)
            team_within_timeframe: Equipo inicial de temporada (Team within selected timeframe)

        Returns:
            str: Nombre del equipo normalizado o "No Team"
        """
        # Normalizar equipo actual
        current_team = ""
        if pd.notna(team) and str(team).strip() not in ["nan", "None", ""]:
            current_team = str(team).strip()

        # Normalizar equipo inicial
        initial_team = ""
        if pd.notna(team_within_timeframe) and str(
            team_within_timeframe
        ).strip() not in ["nan", "None", ""]:
            initial_team = str(team_within_timeframe).strip()

        # Aplicar lógica de fallback
        if current_team:
            return current_team
        elif initial_team:
            return initial_team
        else:
            return "No Team"

    def trigger_stats_import_for_player(
        self, player_id: int, wyscout_id: int
    ) -> Tuple[bool, str, Dict]:
        """
        Importa estadísticas profesionales para un jugador usando datos procesados.
        Versión optimizada que usa el CSV consolidado procesado.

        Args:
            player_id: ID del jugador en la base de datos
            wyscout_id: WyscoutID asignado al jugador

        Returns:
            Tuple[success, message, statistics]
        """
        logger.info(
            f"🎯 Importando estadísticas para player_id={player_id}, wyscout_id={wyscout_id}"
        )

        stats = {
            "seasons_processed": 0,
            "records_imported": 0,
            "records_skipped": 0,
            "errors": 0,
            "seasons_with_data": [],
            "total_records_created": 0,  # Para compatibilidad con callbacks
        }

        try:
            # Validar wyscout_id
            wyscout_id_int = int(wyscout_id) if wyscout_id else None
            if not wyscout_id_int:
                return False, f"WyscoutID inválido: {wyscout_id}", stats

            # Cargar datos del CSV procesado
            processed_file = self.processed_dir / "processed_complete.csv"
            if not processed_file.exists():
                return False, "Archivo de datos procesados no encontrado", stats

            df = pd.read_csv(processed_file)

            # Filtrar por WyscoutID
            player_records = df[df["Wyscout id"] == wyscout_id_int]
            if player_records.empty:
                return (
                    False,
                    f"Jugador con WyscoutID {wyscout_id_int} no encontrado",
                    stats,
                )

            # Procesar cada temporada del jugador
            with self.session_factory() as session:
                for _, record in player_records.iterrows():
                    season = record["season"]
                    stats["seasons_processed"] += 1

                    # Verificar si ya existe el registro
                    existing = (
                        session.query(ProfessionalStats)
                        .filter_by(player_id=player_id, season=season)
                        .first()
                    )

                    if existing:
                        logger.info(f"⏭️ Registro ya existe para temporada {season}")
                        stats["records_skipped"] += 1
                        continue

                    # Crear nuevo registro de estadísticas profesionales
                    try:
                        # Normalizar equipo aplicando lógica de fallback
                        normalized_team = self._normalize_team_for_db(
                            record["Team"], record["Team within selected timeframe"]
                        )

                        # Normalizar competición aplicando default "Thai League"
                        # Lógica: Si está en CSV Thai League → Competition = "Thai League"
                        normalized_competition = (
                            record["Competition"]
                            if pd.notna(record["Competition"])
                            and str(record["Competition"]) != "nan"
                            else "Thai League"
                        )

                        new_stats = ProfessionalStats(
                            player_id=player_id,
                            wyscout_id=wyscout_id_int,
                            season=season,
                            player_name=record["Player"],
                            full_name=record["Full name"],
                            team=normalized_team,
                            team_within_timeframe=(
                                record["Team within selected timeframe"]
                                if pd.notna(record["Team within selected timeframe"])
                                else None
                            ),
                            team_logo_url=record["Team logo"],
                            competition=normalized_competition,
                            age=int(record["Age"]) if pd.notna(record["Age"]) else None,
                            birthday=(
                                pd.to_datetime(
                                    record["Birthday"], errors="coerce"
                                ).date()
                                if pd.notna(record["Birthday"])
                                else None
                            ),
                            birth_country=record["Birth country"],
                            passport_country=record["Passport country"],
                            primary_position=record["Primary position"],
                            secondary_position=(
                                record["Secondary position"]
                                if record["Secondary position"]
                                else None
                            ),
                            third_position=(
                                record["Third position"]
                                if record["Third position"]
                                else None
                            ),
                            matches_played=(
                                int(record["Matches played"])
                                if pd.notna(record["Matches played"])
                                else None
                            ),
                            minutes_played=(
                                int(record["Minutes played"])
                                if pd.notna(record["Minutes played"])
                                else None
                            ),
                            goals=(
                                int(record["Goals"])
                                if pd.notna(record["Goals"])
                                else None
                            ),
                            assists=(
                                int(record["Assists"])
                                if pd.notna(record["Assists"])
                                else None
                            ),
                            market_value=(
                                int(record["Market value"])
                                if pd.notna(record["Market value"])
                                else None
                            ),
                            height=(
                                int(record["Height"])
                                if pd.notna(record["Height"])
                                else None
                            ),
                            weight=(
                                int(record["Weight"])
                                if pd.notna(record["Weight"])
                                else None
                            ),
                            foot=record["Foot"],
                            shots=(
                                int(record["Shots"])
                                if pd.notna(record["Shots"])
                                else None
                            ),
                            shots_per_90=(
                                float(record["Shots per 90"])
                                if pd.notna(record["Shots per 90"])
                                else None
                            ),
                            shots_on_target_pct=(
                                float(record["Shots on target, %"])
                                if pd.notna(record["Shots on target, %"])
                                else None
                            ),
                            goal_conversion_pct=(
                                float(record["Goal conversion, %"])
                                if pd.notna(record["Goal conversion, %"])
                                else None
                            ),
                            goals_per_90=(
                                float(record["Goals per 90"])
                                if pd.notna(record["Goals per 90"])
                                else None
                            ),
                            assists_per_90=(
                                float(record["Assists per 90"])
                                if pd.notna(record["Assists per 90"])
                                else None
                            ),
                            touches_in_box_per_90=(
                                float(record["Touches in box per 90"])
                                if pd.notna(record["Touches in box per 90"])
                                else None
                            ),
                            shot_assists_per_90=(
                                float(record["Shot assists per 90"])
                                if pd.notna(record["Shot assists per 90"])
                                else None
                            ),
                            defensive_actions_per_90=(
                                float(record["Successful defensive actions per 90"])
                                if pd.notna(
                                    record["Successful defensive actions per 90"]
                                )
                                else None
                            ),
                            defensive_duels_per_90=(
                                float(record["Defensive duels per 90"])
                                if pd.notna(record["Defensive duels per 90"])
                                else None
                            ),
                            defensive_duels_won_pct=(
                                float(record["Defensive duels won, %"])
                                if pd.notna(record["Defensive duels won, %"])
                                else None
                            ),
                            aerial_duels_per_90=(
                                float(record["Aerial duels per 90"])
                                if pd.notna(record["Aerial duels per 90"])
                                else None
                            ),
                            aerial_duels_won_pct=(
                                float(record["Aerial duels won, %"])
                                if pd.notna(record["Aerial duels won, %"])
                                else None
                            ),
                            sliding_tackles_per_90=(
                                float(record["Sliding tackles per 90"])
                                if pd.notna(record["Sliding tackles per 90"])
                                else None
                            ),
                            interceptions_per_90=(
                                float(record["Interceptions per 90"])
                                if pd.notna(record["Interceptions per 90"])
                                else None
                            ),
                            fouls_per_90=(
                                float(record["Fouls per 90"])
                                if pd.notna(record["Fouls per 90"])
                                else None
                            ),
                            passes_per_90=(
                                float(record["Passes per 90"])
                                if pd.notna(record["Passes per 90"])
                                else None
                            ),
                            pass_accuracy_pct=(
                                float(record["Accurate passes, %"])
                                if pd.notna(record["Accurate passes, %"])
                                else None
                            ),
                            forward_passes_per_90=(
                                float(record["Forward passes per 90"])
                                if pd.notna(record["Forward passes per 90"])
                                else None
                            ),
                            forward_passes_accuracy_pct=(
                                float(record["Accurate forward passes, %"])
                                if pd.notna(record["Accurate forward passes, %"])
                                else None
                            ),
                            back_passes_per_90=(
                                float(record["Back passes per 90"])
                                if pd.notna(record["Back passes per 90"])
                                else None
                            ),
                            back_passes_accuracy_pct=(
                                float(record["Accurate back passes, %"])
                                if pd.notna(record["Accurate back passes, %"])
                                else None
                            ),
                            long_passes_per_90=(
                                float(record["Long passes per 90"])
                                if pd.notna(record["Long passes per 90"])
                                else None
                            ),
                            long_passes_accuracy_pct=(
                                float(record["Accurate long passes, %"])
                                if pd.notna(record["Accurate long passes, %"])
                                else None
                            ),
                            progressive_passes_per_90=(
                                float(record["Progressive passes per 90"])
                                if pd.notna(record["Progressive passes per 90"])
                                else None
                            ),
                            progressive_passes_accuracy_pct=(
                                float(record["Accurate progressive passes, %"])
                                if pd.notna(record["Accurate progressive passes, %"])
                                else None
                            ),
                            key_passes_per_90=(
                                float(record["Key passes per 90"])
                                if pd.notna(record["Key passes per 90"])
                                else None
                            ),
                            duels_per_90=(
                                float(record["Duels per 90"])
                                if pd.notna(record["Duels per 90"])
                                else None
                            ),
                            duels_won_pct=(
                                float(record["Duels won, %"])
                                if pd.notna(record["Duels won, %"])
                                else None
                            ),
                            offensive_duels_per_90=(
                                float(record["Offensive duels per 90"])
                                if pd.notna(record["Offensive duels per 90"])
                                else None
                            ),
                            offensive_duels_won_pct=(
                                float(record["Offensive duels won, %"])
                                if pd.notna(record["Offensive duels won, %"])
                                else None
                            ),
                            dribbles_per_90=(
                                float(record["Dribbles per 90"])
                                if pd.notna(record["Dribbles per 90"])
                                else None
                            ),
                            dribbles_success_pct=(
                                float(record["Successful dribbles, %"])
                                if pd.notna(record["Successful dribbles, %"])
                                else None
                            ),
                            progressive_runs_per_90=(
                                float(record["Progressive runs per 90"])
                                if pd.notna(record["Progressive runs per 90"])
                                else None
                            ),
                            expected_goals=(
                                float(record["xG"]) if pd.notna(record["xG"]) else None
                            ),
                            expected_assists=(
                                float(record["xA"]) if pd.notna(record["xA"]) else None
                            ),
                            xg_per_90=(
                                float(record["xG per 90"])
                                if pd.notna(record["xG per 90"])
                                else None
                            ),
                            xa_per_90=(
                                float(record["xA per 90"])
                                if pd.notna(record["xA per 90"])
                                else None
                            ),
                            yellow_cards=(
                                int(record["Yellow cards"])
                                if pd.notna(record["Yellow cards"])
                                else None
                            ),
                            red_cards=(
                                int(record["Red cards"])
                                if pd.notna(record["Red cards"])
                                else None
                            ),
                            yellow_cards_per_90=(
                                float(record["Yellow cards per 90"])
                                if pd.notna(record["Yellow cards per 90"])
                                else None
                            ),
                            red_cards_per_90=(
                                float(record["Red cards per 90"])
                                if pd.notna(record["Red cards per 90"])
                                else None
                            ),
                            fouls_suffered_per_90=(
                                float(record["Fouls suffered per 90"])
                                if pd.notna(record["Fouls suffered per 90"])
                                else None
                            ),
                        )

                        session.add(new_stats)
                        session.commit()

                        stats["records_imported"] += 1
                        stats["seasons_with_data"].append(season)
                        logger.info(
                            f"✅ Estadísticas importadas para temporada {season}"
                        )

                    except Exception as e:
                        stats["errors"] += 1
                        logger.error(
                            f"❌ Error importando temporada {season}: {str(e)}"
                        )
                        session.rollback()

            # Establecer total_records_created para compatibilidad
            stats["total_records_created"] = stats["records_imported"]

            # Generar mensaje de resultado
            if stats["records_imported"] > 0:
                success_msg = f"Estadísticas importadas: {stats['records_imported']} registros de {len(stats['seasons_with_data'])} temporadas"
                logger.info(f"✅ {success_msg}")
                return True, success_msg, stats
            elif stats["records_skipped"] > 0:
                skip_msg = f"Estadísticas ya existían ({stats['records_skipped']} registros omitidos)"
                return True, skip_msg, stats
            else:
                return (
                    False,
                    f"No se encontraron estadísticas para WyscoutID {wyscout_id_int}",
                    stats,
                )

        except Exception as e:
            logger.error(f"❌ Error en importación de estadísticas: {str(e)}")
            return False, f"Error importando estadísticas: {str(e)}", stats

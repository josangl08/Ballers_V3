"""
Transformer Module - Limpieza, normalización y transformación de datos
"""

import logging
import re
from typing import Dict, List, Optional, Union

import pandas as pd
from unidecode import unidecode

# Lazy import to avoid circular imports
# from ml_system.data_processing.processors.cleaners import DataCleaners
from controllers.db import get_db_session
from models import Player, User, UserType

logger = logging.getLogger(__name__)


class ThaiLeagueTransformer:
    """
    Transformador para datos de la liga tailandesa.
    Maneja limpieza, normalización y preparación para matching.
    """

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
        "PAdj Sliding tackles": "padj_sliding_tackles",
        "Shots blocked per 90": "shots_blocked_per_90",
        "Interceptions per 90": "interceptions_per_90",
        "PAdj Interceptions": "padj_interceptions",
        "Fouls per 90": "fouls_per_90",
        "Yellow cards": "yellow_cards",
        "Yellow cards per 90": "yellow_cards_per_90",
        "Red cards": "red_cards",
        "Red cards per 90": "red_cards_per_90",
        # === DISTRIBUCIÓN Y PASES ===
        "Passes per 90": "passes_per_90",
        "Accurate passes per 90": "accurate_passes_per_90",
        "Passes accuracy, %": "passes_accuracy_pct",
        "Forward passes per 90": "forward_passes_per_90",
        "Accurate forward passes per 90": "accurate_forward_passes_per_90",
        "Forward passes accuracy, %": "forward_passes_accuracy_pct",
        "Back passes per 90": "back_passes_per_90",
        "Accurate back passes per 90": "accurate_back_passes_per_90",
        "Back passes accuracy, %": "back_passes_accuracy_pct",
        "Lateral passes per 90": "lateral_passes_per_90",
        "Accurate lateral passes per 90": "accurate_lateral_passes_per_90",
        "Lateral passes accuracy, %": "lateral_passes_accuracy_pct",
        "Short / medium passes per 90": "short_medium_passes_per_90",
        "Accurate short / medium passes per 90": "accurate_short_medium_passes_per_90",
        "Short / medium passes accuracy, %": "short_medium_passes_accuracy_pct",
        "Long passes per 90": "long_passes_per_90",
        "Accurate long passes per 90": "accurate_long_passes_per_90",
        "Long passes accuracy, %": "long_passes_accuracy_pct",
        "Average pass length, m": "average_pass_length_m",
        "Average long pass length, m": "average_long_pass_length_m",
        "xA per 90": "xa_per_90",
        "Key passes per 90": "key_passes_per_90",
        "Passes to final third per 90": "passes_to_final_third_per_90",
        "Accurate passes to final third per 90": "accurate_passes_to_final_third_per_90",
        "Passes to final third accuracy, %": "passes_to_final_third_accuracy_pct",
        "Passes to penalty area per 90": "passes_to_penalty_area_per_90",
        "Accurate passes to penalty area per 90": "accurate_passes_to_penalty_area_per_90",
        "Passes to penalty area accuracy, %": "passes_to_penalty_area_accuracy_pct",
        "Crosses per 90": "crosses_per_90",
        "Accurate crosses per 90": "accurate_crosses_per_90",
        "Crosses accuracy, %": "crosses_accuracy_pct",
        "Dribbles per 90": "dribbles_per_90",
        "Successful dribbles per 90": "successful_dribbles_per_90",
        "Successful dribbles, %": "successful_dribbles_pct",
        "Offensive duels per 90": "offensive_duels_per_90",
        "Offensive duels won, %": "offensive_duels_won_pct",
        "Touches per 90": "touches_per_90",
        "Touches in box per 90": "touches_in_box_per_90",
        "Received passes per 90": "received_passes_per_90",
        "Received long passes per 90": "received_long_passes_per_90",
        "Fouls suffered per 90": "fouls_suffered_per_90",
        "Offsides per 90": "offsides_per_90",
        "Lost balls per 90": "lost_balls_per_90",
        "Lost balls in own half per 90": "lost_balls_own_half_per_90",
    }

    def __init__(self, session_factory=None):
        """
        Inicializa el transformador.

        Args:
            session_factory: Factory para sesiones de BD (opcional)
        """
        self.session_factory = session_factory or get_db_session

    def clean_and_normalize_data(self, df: pd.DataFrame, season: str) -> pd.DataFrame:
        """
        Limpia y normaliza los datos del CSV aplicando las nuevas reglas de limpieza.

        Args:
            df: DataFrame con datos crudos
            season: Temporada para agregar a los datos

        Returns:
            DataFrame limpio y normalizado
        """
        logger.info(f"🧹 Iniciando limpieza de datos para temporada {season}")

        # Crear copia para no modificar el original
        clean_df = df.copy()

        # Añadir columna de temporada
        clean_df["season"] = season

        # Limpiar nombres de columnas (remover espacios extra, etc.)
        clean_df.columns = clean_df.columns.str.strip()

        # ===== LIMPIEZA ESPECÍFICA POR COLUMNAS =====

        # Lazy import to avoid circular dependency
        from ml_system.data_processing.processors.cleaners import DataCleaners

        # Limpiar nombres de jugadores
        if "Full name" in clean_df.columns:
            clean_df["Full name"] = clean_df["Full name"].apply(
                DataCleaners.clean_player_name
            )
        if "Player" in clean_df.columns:
            clean_df["Player"] = clean_df["Player"].apply(
                DataCleaners.clean_player_name
            )

        # CRÍTICO: Limpiar Team usando el limpiador específico
        # Esto resuelve el problema de David Cuerva Team="" → Team=None
        if "Team" in clean_df.columns:
            logger.info("🔧 Aplicando limpieza específica para Team (David Cuerva fix)")
            clean_df["Team"] = clean_df["Team"].apply(DataCleaners.clean_team_name)

        # Limpiar Team within selected timeframe
        if "Team within selected timeframe" in clean_df.columns:
            clean_df["Team within selected timeframe"] = clean_df[
                "Team within selected timeframe"
            ].apply(DataCleaners.clean_team_name)

        # Limpiar Wyscout ID (debe ser entero positivo)
        if "Wyscout id" in clean_df.columns:
            clean_df["Wyscout id"] = clean_df["Wyscout id"].apply(
                DataCleaners.clean_wyscout_id
            )

        # ===== CONFIGURACIÓN DE LIMPIEZA AUTOMÁTICA =====

        # Definir configuración de limpieza por columnas
        columns_config = {
            # Campos numéricos básicos
            "Age": {"type": "integer", "min_value": 16, "max_value": 50},
            "Matches played": {"type": "integer", "min_value": 0, "max_value": 100},
            "Minutes played": {"type": "integer", "min_value": 0},
            "Goals": {"type": "integer", "min_value": 0},
            "Assists": {"type": "integer", "min_value": 0},
            "Yellow cards": {"type": "integer", "min_value": 0},
            "Red cards": {"type": "integer", "min_value": 0},
            "Height": {"type": "numeric", "min_value": 1.50, "max_value": 2.20},
            "Weight": {"type": "numeric", "min_value": 50.0, "max_value": 120.0},
            # Estadísticas por 90 minutos
            "Goals per 90": {"type": "numeric", "min_value": 0.0},
            "Assists per 90": {"type": "numeric", "min_value": 0.0},
            "Shots per 90": {"type": "numeric", "min_value": 0.0},
            "Passes per 90": {"type": "numeric", "min_value": 0.0},
            "Touches per 90": {"type": "numeric", "min_value": 0.0},
            # Porcentajes
            "Shots on target, %": {
                "type": "numeric",
                "min_value": 0.0,
                "max_value": 100.0,
            },
            "Goal conversion, %": {
                "type": "numeric",
                "min_value": 0.0,
                "max_value": 100.0,
            },
            "Passes accuracy, %": {
                "type": "numeric",
                "min_value": 0.0,
                "max_value": 100.0,
            },
            "Defensive duels won, %": {
                "type": "numeric",
                "min_value": 0.0,
                "max_value": 100.0,
            },
            "Aerial duels won, %": {
                "type": "numeric",
                "min_value": 0.0,
                "max_value": 100.0,
            },
        }

        # Aplicar limpieza automática usando configuración
        clean_df = DataCleaners.clean_dataframe_nulls(clean_df, columns_config)

        # ===== CONVERSIONES DE TIPOS =====

        # Convertir fechas de nacimiento
        if "Birthday" in clean_df.columns:
            clean_df["Birthday"] = pd.to_datetime(clean_df["Birthday"], errors="coerce")

        # Limpiar valores infinitos
        clean_df = clean_df.replace([float("inf"), float("-inf")], None)

        # ===== NORMALIZACIÓN DE NOMBRES =====

        # Normalizar nombres para matching (sin modificar originales)
        if "Full name" in clean_df.columns:
            clean_df["full_name_normalized"] = clean_df["Full name"].apply(
                self._normalize_name
            )
        if "Player" in clean_df.columns:
            clean_df["player_name_normalized"] = clean_df["Player"].apply(
                self._normalize_name
            )

        # ===== ESTADÍSTICAS FINALES =====

        original_count = len(df)
        clean_count = len(clean_df)

        # Contar registros con datos críticos
        valid_players = (
            clean_df["Full name"].notna().sum()
            if "Full name" in clean_df.columns
            else 0
        )
        valid_wyscout = (
            clean_df["Wyscout id"].notna().sum()
            if "Wyscout id" in clean_df.columns
            else 0
        )

        logger.info(f"✅ Limpieza completada para {season}:")
        logger.info(f"   📥 Registros originales: {original_count}")
        logger.info(f"   📤 Registros limpios: {clean_count}")
        logger.info(f"   👤 Jugadores con nombre válido: {valid_players}")
        logger.info(f"   🆔 Jugadores con Wyscout ID: {valid_wyscout}")

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

    def prepare_for_matching(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara el DataFrame para el proceso de matching.

        Args:
            df: DataFrame limpio

        Returns:
            DataFrame preparado para matching
        """
        logger.info("🎯 Preparando datos para matching...")

        # Crear copia
        match_df = df.copy()

        # Filtrar registros válidos para matching
        # Un registro es válido si tiene al menos nombre o wyscout_id
        valid_mask = match_df["Full name"].notna() | match_df["Wyscout id"].notna()

        match_df = match_df[valid_mask].copy()

        # Agregar columnas de apoyo para matching
        if (
            "full_name_normalized" not in match_df.columns
            and "Full name" in match_df.columns
        ):
            match_df["full_name_normalized"] = match_df["Full name"].apply(
                self._normalize_name
            )

        logger.info(f"📊 Registros preparados para matching: {len(match_df)}")

        return match_df

    def get_column_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapping de columnas CSV a modelo BD.

        Returns:
            Diccionario de mapping
        """
        return self.COLUMN_MAPPING.copy()

    def validate_required_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Valida que el DataFrame tenga las columnas mínimas requeridas.

        Args:
            df: DataFrame a validar

        Returns:
            Lista de columnas faltantes (vacía si está completo)
        """
        required_columns = ["Full name", "Wyscout id", "Team", "Competition"]

        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            logger.warning(f"⚠️ Columnas faltantes: {missing_columns}")
        else:
            logger.info("✅ Todas las columnas requeridas están presentes")

        return missing_columns

    def apply_business_rules(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica reglas de negocio específicas del dominio.

        Args:
            df: DataFrame a procesar

        Returns:
            DataFrame con reglas aplicadas
        """
        logger.info("🔧 Aplicando reglas de negocio...")

        business_df = df.copy()

        # Regla 1: Si un jugador no tiene equipo, debe tener al menos estadísticas
        no_team_mask = business_df["Team"].isna()
        if no_team_mask.any():
            no_team_count = no_team_mask.sum()
            logger.info(f"👤 Jugadores sin equipo encontrados: {no_team_count}")

            # Validar que tengan al menos minutos jugados
            if "Minutes played" in business_df.columns:
                no_team_no_minutes = no_team_mask & (
                    business_df["Minutes played"].isna()
                    | (business_df["Minutes played"] == 0)
                )
                if no_team_no_minutes.any():
                    invalid_count = no_team_no_minutes.sum()
                    logger.warning(
                        f"⚠️ Jugadores sin equipo y sin minutos: {invalid_count}"
                    )

        # Regla 2: Edad debe ser consistente con fecha de nacimiento
        if "Age" in business_df.columns and "Birthday" in business_df.columns:
            # Esta validación se puede implementar posteriormente
            pass

        # Regla 3: Estadísticas por 90 deben ser proporcionales
        if "Goals" in business_df.columns and "Goals per 90" in business_df.columns:
            # Esta validación se puede implementar posteriormente
            pass

        logger.info("✅ Reglas de negocio aplicadas")

        return business_df

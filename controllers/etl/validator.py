"""
Validator Module - Validación de calidad de datos antes de inserción BD
"""

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class DataQualityValidator:
    """
    Validador de calidad de datos para asegurar integridad antes de inserción.
    Implementa validaciones críticas identificadas en el análisis.
    """

    def __init__(self):
        """Inicializa el validador."""
        pass

    def validate_dataframe(
        self, df: pd.DataFrame, season: str
    ) -> Tuple[bool, List[str], Dict[str, int]]:
        """
        Ejecuta validación completa del DataFrame.
        
        Args:
            df: DataFrame a validar
            season: Temporada siendo procesada
            
        Returns:
            Tuple[is_valid, error_list, stats_dict]
        """
        logger.info(f"🔍 Iniciando validación de calidad para {season}")
        
        errors = []
        stats = {
            "total_records": len(df),
            "valid_records": 0,
            "invalid_records": 0,
            "warnings": 0
        }
        
        # Validación 1: Estructura básica
        structure_errors = self._validate_structure(df)
        errors.extend(structure_errors)
        
        # Validación 2: Campos críticos
        critical_errors = self._validate_critical_fields(df)
        errors.extend(critical_errors)
        
        # Validación 3: Integridad de datos
        integrity_errors = self._validate_data_integrity(df)
        errors.extend(integrity_errors)
        
        # Validación 4: Consistencia empresarial
        business_errors = self._validate_business_rules(df)
        errors.extend(business_errors)
        
        # Validación 5: Duplicados
        duplicate_errors = self._validate_duplicates(df)
        errors.extend(duplicate_errors)
        
        # Calcular estadísticas finales
        stats["invalid_records"] = len([e for e in errors if "ERROR" in e])
        stats["warnings"] = len([e for e in errors if "WARNING" in e])
        stats["valid_records"] = stats["total_records"] - stats["invalid_records"]
        
        is_valid = stats["invalid_records"] == 0
        
        if is_valid:
            logger.info(f"✅ Validación exitosa para {season}")
        else:
            logger.warning(f"⚠️ Validación falló para {season}: {stats['invalid_records']} errores")
            
        logger.info(f"📊 Estadísticas de validación: {stats}")
        
        return is_valid, errors, stats

    def _validate_structure(self, df: pd.DataFrame) -> List[str]:
        """
        Valida la estructura básica del DataFrame.
        
        Args:
            df: DataFrame a validar
            
        Returns:
            Lista de errores de estructura
        """
        errors = []
        
        # Verificar que no esté vacío
        if df.empty:
            errors.append("ERROR: DataFrame está vacío")
            return errors
            
        # Verificar columnas mínimas requeridas
        required_columns = ["Full name", "Wyscout id", "Team", "Competition"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            errors.append(f"ERROR: Columnas faltantes: {missing_columns}")
            
        # Verificar que haya al menos algunos datos válidos
        if len(df.columns) < 10:
            errors.append("WARNING: Muy pocas columnas en el dataset")
            
        return errors

    def _validate_critical_fields(self, df: pd.DataFrame) -> List[str]:
        """
        Valida campos críticos para el funcionamiento.
        
        Args:
            df: DataFrame a validar
            
        Returns:
            Lista de errores de campos críticos
        """
        errors = []
        
        # Validar Full name
        if "Full name" in df.columns:
            null_names = df["Full name"].isna().sum()
            if null_names > 0:
                errors.append(f"WARNING: {null_names} jugadores sin nombre")
                
            # Verificar nombres muy cortos (posible error)
            if "Full name" in df.columns:
                short_names = df[df["Full name"].str.len() < 3]["Full name"].count()
                if short_names > 0:
                    errors.append(f"WARNING: {short_names} nombres muy cortos (< 3 caracteres)")
        
        # Validar Wyscout ID
        if "Wyscout id" in df.columns:
            null_ids = df["Wyscout id"].isna().sum()
            if null_ids > 0:
                errors.append(f"WARNING: {null_ids} jugadores sin Wyscout ID")
                
            # Verificar IDs válidos (enteros positivos)
            invalid_ids = df[
                (df["Wyscout id"].notna()) & 
                ((df["Wyscout id"] <= 0) | (df["Wyscout id"] != df["Wyscout id"].astype(int)))
            ]
            if len(invalid_ids) > 0:
                errors.append(f"ERROR: {len(invalid_ids)} Wyscout IDs inválidos")
        
        # Validar Team (aplicar fix de David Cuerva)
        if "Team" in df.columns:
            # Contar equipos vacíos DESPUÉS de limpieza
            empty_teams = df["Team"].isna().sum()
            if empty_teams > 0:
                errors.append(f"INFO: {empty_teams} jugadores sin equipo (correcto después de limpieza)")
        
        # Validar Competition
        if "Competition" in df.columns:
            null_competitions = df["Competition"].isna().sum()
            if null_competitions > 0:
                errors.append(f"WARNING: {null_competitions} registros sin competición")
        
        return errors

    def _validate_data_integrity(self, df: pd.DataFrame) -> List[str]:
        """
        Valida integridad de datos numéricos y fechas.
        
        Args:
            df: DataFrame a validar
            
        Returns:
            Lista de errores de integridad
        """
        errors = []
        
        # Validar Ages
        if "Age" in df.columns:
            invalid_ages = df[
                (df["Age"].notna()) & 
                ((df["Age"] < 16) | (df["Age"] > 50))
            ]
            if len(invalid_ages) > 0:
                errors.append(f"WARNING: {len(invalid_ages)} edades fuera de rango (16-50)")
        
        # Validar Minutes played vs Matches played
        if "Minutes played" in df.columns and "Matches played" in df.columns:
            # Un jugador no puede tener más de 90 * partidos minutos
            invalid_minutes = df[
                (df["Minutes played"].notna()) & 
                (df["Matches played"].notna()) & 
                (df["Minutes played"] > df["Matches played"] * 90)
            ]
            if len(invalid_minutes) > 0:
                errors.append(f"WARNING: {len(invalid_minutes)} jugadores con más minutos que posible")
        
        # Validar porcentajes
        percentage_columns = [col for col in df.columns if "%" in col or "accuracy" in col.lower()]
        for col in percentage_columns:
            if col in df.columns:
                invalid_pct = df[
                    (df[col].notna()) & 
                    ((df[col] < 0) | (df[col] > 100))
                ]
                if len(invalid_pct) > 0:
                    errors.append(f"WARNING: {len(invalid_pct)} valores de porcentaje inválidos en {col}")
        
        # Validar valores negativos en estadísticas que no pueden ser negativas
        non_negative_stats = ["Goals", "Assists", "Shots", "Yellow cards", "Red cards"]
        for stat in non_negative_stats:
            if stat in df.columns:
                negative_values = df[
                    (df[stat].notna()) & (df[stat] < 0)
                ]
                if len(negative_values) > 0:
                    errors.append(f"ERROR: {len(negative_values)} valores negativos en {stat}")
        
        return errors

    def _validate_business_rules(self, df: pd.DataFrame) -> List[str]:
        """
        Valida reglas de negocio específicas del dominio.
        
        Args:
            df: DataFrame a validar
            
        Returns:
            Lista de errores de reglas de negocio
        """
        errors = []
        
        # Regla 1: Jugadores sin equipo deben tener explicación
        if "Team" in df.columns and "Minutes played" in df.columns:
            no_team_no_minutes = df[
                (df["Team"].isna()) & 
                ((df["Minutes played"].isna()) | (df["Minutes played"] == 0))
            ]
            if len(no_team_no_minutes) > 0:
                errors.append(f"WARNING: {len(no_team_no_minutes)} jugadores sin equipo ni minutos")
        
        # Regla 2: Goals no puede ser mayor que Shots
        if "Goals" in df.columns and "Shots" in df.columns:
            impossible_efficiency = df[
                (df["Goals"].notna()) & 
                (df["Shots"].notna()) & 
                (df["Goals"] > df["Shots"])
            ]
            if len(impossible_efficiency) > 0:
                errors.append(f"ERROR: {len(impossible_efficiency)} jugadores con más goles que disparos")
        
        # Regla 3: Yellow + Red cards no puede exceder matches played * 2
        if all(col in df.columns for col in ["Yellow cards", "Red cards", "Matches played"]):
            excessive_cards = df[
                (df["Yellow cards"].notna()) & 
                (df["Red cards"].notna()) & 
                (df["Matches played"].notna()) & 
                ((df["Yellow cards"] + df["Red cards"]) > df["Matches played"] * 2)
            ]
            if len(excessive_cards) > 0:
                errors.append(f"WARNING: {len(excessive_cards)} jugadores con demasiadas tarjetas")
        
        return errors

    def _validate_duplicates(self, df: pd.DataFrame) -> List[str]:
        """
        Valida duplicados en campos únicos.
        
        Args:
            df: DataFrame a validar
            
        Returns:
            Lista de errores de duplicados
        """
        errors = []
        
        # Validar duplicados por Wyscout ID
        if "Wyscout id" in df.columns:
            wyscout_duplicates = df[df["Wyscout id"].notna()]["Wyscout id"].duplicated().sum()
            if wyscout_duplicates > 0:
                errors.append(f"ERROR: {wyscout_duplicates} Wyscout IDs duplicados")
        
        # Validar duplicados por nombre completo
        if "Full name" in df.columns:
            name_duplicates = df[df["Full name"].notna()]["Full name"].duplicated().sum()
            if name_duplicates > 0:
                errors.append(f"WARNING: {name_duplicates} nombres duplicados")
        
        return errors

    def validate_before_database_insert(
        self, processed_records: List[Dict], season: str
    ) -> Tuple[bool, List[str], List[Dict]]:
        """
        Validación final antes de insertar en base de datos.
        Crítico para evitar el error 'team_processed' identificado.
        
        Args:
            processed_records: Lista de registros procesados para insertar
            season: Temporada siendo procesada
            
        Returns:
            Tuple[is_valid, errors, clean_records]
        """
        logger.info(f"🔒 Validación final antes de BD para {season}")
        
        errors = []
        clean_records = []
        
        for i, record in enumerate(processed_records):
            record_errors = []
            
            # Validar campos requeridos para el modelo
            required_fields = ["full_name", "wyscout_id", "season"]
            for field in required_fields:
                if field not in record or record[field] is None:
                    record_errors.append(f"Campo requerido faltante: {field}")
            
            # Validar que no haya campos desconocidos que puedan causar 'team_processed'
            # Esto previene el error identificado en el análisis
            allowed_fields = self._get_allowed_database_fields()
            unknown_fields = [field for field in record.keys() if field not in allowed_fields]
            if unknown_fields:
                record_errors.append(f"Campos desconocidos: {unknown_fields}")
            
            # Si hay errores, registrar pero continuar con el siguiente
            if record_errors:
                errors.append(f"Registro {i+1}: {'; '.join(record_errors)}")
            else:
                clean_records.append(record)
        
        is_valid = len(clean_records) > 0
        
        logger.info(f"📊 Validación BD: {len(clean_records)}/{len(processed_records)} registros válidos")
        
        return is_valid, errors, clean_records

    def _get_allowed_database_fields(self) -> List[str]:
        """
        Obtiene lista de campos permitidos en el modelo de BD.
        Previene errores como 'team_processed' que no existe en el modelo.
        
        Returns:
            Lista de campos permitidos
        """
        # Lista basada en el modelo ProfessionalStats
        # IMPORTANTE: Mantener sincronizado con el modelo real
        return [
            # Campos básicos
            "season", "full_name", "player_name", "wyscout_id", "team",
            "team_within_timeframe", "team_logo_url", "competition",
            "age", "birthday", "birth_country", "passport_country",
            "primary_position", "secondary_position", "third_position",
            "height", "weight", "foot", "matches_played", "minutes_played", "market_value",
            
            # Estadísticas ofensivas
            "goals", "assists", "expected_goals", "expected_assists",
            "goals_per_90", "assists_per_90", "xg_per_90", "xa_per_90",
            "shots", "shots_per_90", "shots_on_target_pct", "goal_conversion_pct",
            "touches_in_box_per_90", "shot_assists_per_90",
            
            # Estadísticas defensivas
            "defensive_actions_per_90", "defensive_duels_per_90", "defensive_duels_won_pct",
            "aerial_duels_per_90", "aerial_duels_won_pct", "sliding_tackles_per_90",
            "padj_sliding_tackles", "shots_blocked_per_90", "interceptions_per_90",
            "padj_interceptions", "fouls_per_90", "yellow_cards", "yellow_cards_per_90",
            "red_cards", "red_cards_per_90",
            
            # Distribución y pases
            "passes_per_90", "accurate_passes_per_90", "passes_accuracy_pct",
            "forward_passes_per_90", "accurate_forward_passes_per_90", "forward_passes_accuracy_pct",
            "back_passes_per_90", "accurate_back_passes_per_90", "back_passes_accuracy_pct",
            "lateral_passes_per_90", "accurate_lateral_passes_per_90", "lateral_passes_accuracy_pct",
            "short_medium_passes_per_90", "accurate_short_medium_passes_per_90", "short_medium_passes_accuracy_pct",
            "long_passes_per_90", "accurate_long_passes_per_90", "long_passes_accuracy_pct",
            "average_pass_length_m", "average_long_pass_length_m", "xa_per_90",
            "key_passes_per_90", "passes_to_final_third_per_90", "accurate_passes_to_final_third_per_90",
            "passes_to_final_third_accuracy_pct", "passes_to_penalty_area_per_90",
            "accurate_passes_to_penalty_area_per_90", "passes_to_penalty_area_accuracy_pct",
            "crosses_per_90", "accurate_crosses_per_90", "crosses_accuracy_pct",
            "dribbles_per_90", "successful_dribbles_per_90", "successful_dribbles_pct",
            "offensive_duels_per_90", "offensive_duels_won_pct", "touches_per_90",
            "received_passes_per_90", "received_long_passes_per_90", "fouls_suffered_per_90",
            "offsides_per_90", "lost_balls_per_90", "lost_balls_own_half_per_90",
        ]
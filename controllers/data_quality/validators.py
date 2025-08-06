"""
Data Validators - Validadores de integridad y consistencia
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class DataValidators:
    """
    Colección de validadores para verificar integridad y consistencia de datos.
    """

    @staticmethod
    def validate_player_name(name: Any) -> Tuple[bool, Optional[str]]:
        """
        Valida que un nombre de jugador sea válido.
        
        Args:
            name: Nombre a validar
            
        Returns:
            Tuple[is_valid, error_message]
        """
        if pd.isna(name) or name is None:
            return False, "Nombre es obligatorio"
            
        if not isinstance(name, str):
            return False, "Nombre debe ser texto"
            
        if len(name.strip()) < 2:
            return False, "Nombre muy corto (mínimo 2 caracteres)"
            
        if len(name.strip()) > 100:
            return False, "Nombre muy largo (máximo 100 caracteres)"
            
        # Verificar que contenga al menos alguna letra
        if not any(c.isalpha() for c in name):
            return False, "Nombre debe contener al menos una letra"
            
        return True, None

    @staticmethod
    def validate_wyscout_id(wyscout_id: Any) -> Tuple[bool, Optional[str]]:
        """
        Valida que un Wyscout ID sea válido.
        
        Args:
            wyscout_id: ID a validar
            
        Returns:
            Tuple[is_valid, error_message]
        """
        if pd.isna(wyscout_id) or wyscout_id is None:
            return False, "Wyscout ID es obligatorio"
            
        try:
            id_value = int(wyscout_id)
            if id_value <= 0:
                return False, "Wyscout ID debe ser positivo"
            if id_value > 999999999:  # Rango razonable
                return False, "Wyscout ID fuera de rango"
            return True, None
        except (ValueError, TypeError):
            return False, "Wyscout ID debe ser numérico"

    @staticmethod
    def validate_age(age: Any) -> Tuple[bool, Optional[str]]:
        """
        Valida que una edad sea razonable para un futbolista.
        
        Args:
            age: Edad a validar
            
        Returns:
            Tuple[is_valid, error_message]
        """
        if pd.isna(age) or age is None:
            return True, None  # Edad es opcional
            
        try:
            age_value = int(age)
            if age_value < 16:
                return False, "Edad muy baja para futbolista profesional"
            if age_value > 50:
                return False, "Edad muy alta para futbolista activo"
            return True, None
        except (ValueError, TypeError):
            return False, "Edad debe ser numérica"

    @staticmethod
    def validate_matches_minutes_consistency(
        matches: Any, minutes: Any
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida consistencia entre partidos jugados y minutos.
        
        Args:
            matches: Partidos jugados
            minutes: Minutos jugados
            
        Returns:
            Tuple[is_valid, error_message]
        """
        # Si alguno es nulo, no podemos validar
        if pd.isna(matches) or pd.isna(minutes):
            return True, None
            
        try:
            matches_val = int(matches)
            minutes_val = int(minutes)
            
            # Validaciones básicas
            if matches_val < 0:
                return False, "Partidos jugados no puede ser negativo"
            if minutes_val < 0:
                return False, "Minutos jugados no puede ser negativo"
                
            # Un jugador no puede jugar más de 90 minutos por partido en promedio
            if matches_val > 0:
                avg_minutes_per_match = minutes_val / matches_val
                if avg_minutes_per_match > 95:  # Pequeño margen por tiempo añadido
                    return False, f"Promedio de {avg_minutes_per_match:.1f} min/partido es muy alto"
                    
            return True, None
        except (ValueError, TypeError):
            return False, "Partidos y minutos deben ser numéricos"

    @staticmethod
    def validate_goals_shots_consistency(
        goals: Any, shots: Any
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida que los goles no excedan los tiros.
        
        Args:
            goals: Goles anotados
            shots: Tiros realizados
            
        Returns:
            Tuple[is_valid, error_message]
        """
        # Si alguno es nulo, no podemos validar
        if pd.isna(goals) or pd.isna(shots):
            return True, None
            
        try:
            goals_val = int(goals)
            shots_val = int(shots)
            
            if goals_val < 0:
                return False, "Goles no puede ser negativo"
            if shots_val < 0:
                return False, "Tiros no puede ser negativo"
                
            if goals_val > shots_val:
                return False, f"Goles ({goals_val}) no puede exceder tiros ({shots_val})"
                
            return True, None
        except (ValueError, TypeError):
            return False, "Goles y tiros deben ser numéricos"

    @staticmethod
    def validate_percentage_range(
        value: Any, field_name: str = "campo"
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida que un porcentaje esté en rango 0-100.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo para el mensaje de error
            
        Returns:
            Tuple[is_valid, error_message]
        """
        if pd.isna(value) or value is None:
            return True, None  # Porcentajes son opcionales
            
        try:
            pct_value = float(value)
            if pct_value < 0:
                return False, f"{field_name} no puede ser negativo"
            if pct_value > 100:
                return False, f"{field_name} no puede exceder 100%"
            return True, None
        except (ValueError, TypeError):
            return False, f"{field_name} debe ser numérico"

    @staticmethod
    def validate_height_weight_consistency(
        height: Any, weight: Any
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida consistencia entre altura y peso (BMI razonable).
        
        Args:
            height: Altura en metros
            weight: Peso en kg
            
        Returns:
            Tuple[is_valid, error_message]
        """
        # Si alguno es nulo, no podemos validar
        if pd.isna(height) or pd.isna(weight):
            return True, None
            
        try:
            height_val = float(height)
            weight_val = float(weight)
            
            # Validar rangos individuales
            if height_val < 1.50 or height_val > 2.20:
                return False, f"Altura {height_val}m fuera de rango razonable"
            if weight_val < 50 or weight_val > 120:
                return False, f"Peso {weight_val}kg fuera de rango razonable"
                
            # Calcular BMI
            bmi = weight_val / (height_val ** 2)
            
            # BMI razonable para atletas: 18-35
            if bmi < 18:
                return False, f"BMI {bmi:.1f} muy bajo para atleta"
            if bmi > 35:
                return False, f"BMI {bmi:.1f} muy alto para atleta"
                
            return True, None
        except (ValueError, TypeError):
            return False, "Altura y peso deben ser numéricos"

    @staticmethod
    def validate_season_format(season: Any) -> Tuple[bool, Optional[str]]:
        """
        Valida formato de temporada (ej: "2024-25").
        
        Args:
            season: Temporada a validar
            
        Returns:
            Tuple[is_valid, error_message]
        """
        if pd.isna(season) or not isinstance(season, str):
            return False, "Temporada debe ser texto"
            
        # Formato esperado: "YYYY-YY"
        import re
        pattern = r'^\d{4}-\d{2}$'
        
        if not re.match(pattern, season):
            return False, "Formato de temporada inválido (esperado: YYYY-YY)"
            
        # Validar que los años sean consecutivos
        try:
            start_year, end_year_short = season.split('-')
            start_year = int(start_year)
            end_year = int(f"20{end_year_short}")
            
            if end_year != start_year + 1:
                return False, "Los años de la temporada deben ser consecutivos"
                
            # Validar rango razonable
            current_year = datetime.now().year
            if start_year < 2000 or start_year > current_year + 1:
                return False, f"Año de inicio {start_year} fuera de rango razonable"
                
            return True, None
        except ValueError:
            return False, "Error procesando años de la temporada"

    @staticmethod
    def validate_competition_name(competition: Any) -> Tuple[bool, Optional[str]]:
        """
        Valida nombre de competición.
        
        Args:
            competition: Competición a validar
            
        Returns:
            Tuple[is_valid, error_message]
        """
        if pd.isna(competition) or competition is None:
            return False, "Competición es obligatoria"
            
        if not isinstance(competition, str):
            return False, "Competición debe ser texto"
            
        if len(competition.strip()) < 3:
            return False, "Nombre de competición muy corto"
            
        return True, None

    @staticmethod
    def validate_record_completeness(
        record: Dict[str, Any], required_fields: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Valida que un registro tenga los campos requeridos.
        
        Args:
            record: Registro a validar
            required_fields: Lista de campos requeridos
            
        Returns:
            Tuple[is_valid, missing_fields]
        """
        missing_fields = []
        
        for field in required_fields:
            if field not in record or pd.isna(record[field]) or record[field] is None:
                missing_fields.append(field)
                
        return len(missing_fields) == 0, missing_fields

    @staticmethod
    def validate_dataframe_integrity(
        df: pd.DataFrame, validation_config: Dict[str, Any]
    ) -> Tuple[bool, List[str], Dict[str, int]]:
        """
        Ejecuta validaciones comprensivas en un DataFrame.
        
        Args:
            df: DataFrame a validar
            validation_config: Configuración de validaciones
                {
                    'required_columns': ['Full name', 'Wyscout id'],
                    'validate_consistency': True,
                    'validate_ranges': True
                }
                
        Returns:
            Tuple[is_valid, error_list, validation_stats]
        """
        logger.info("🔍 Ejecutando validación integral del DataFrame")
        
        errors = []
        stats = {
            'total_records': len(df),
            'valid_records': 0,
            'validation_errors': 0,
            'warnings': 0
        }
        
        # Validar columnas requeridas
        required_columns = validation_config.get('required_columns', [])
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            errors.append(f"Columnas faltantes: {missing_cols}")
            stats['validation_errors'] += 1
        
        # Validaciones por registro
        for idx, row in df.iterrows():
            record_errors = []
            
            # Validar nombre del jugador
            if 'Full name' in row:
                is_valid, error = DataValidators.validate_player_name(row['Full name'])
                if not is_valid:
                    record_errors.append(f"Nombre inválido: {error}")
            
            # Validar Wyscout ID
            if 'Wyscout id' in row:
                is_valid, error = DataValidators.validate_wyscout_id(row['Wyscout id'])
                if not is_valid:
                    record_errors.append(f"Wyscout ID inválido: {error}")
            
            # Validar edad
            if 'Age' in row:
                is_valid, error = DataValidators.validate_age(row['Age'])
                if not is_valid:
                    record_errors.append(f"Edad inválida: {error}")
            
            # Validaciones de consistencia si están habilitadas
            if validation_config.get('validate_consistency', False):
                
                # Consistencia partidos-minutos
                if 'Matches played' in row and 'Minutes played' in row:
                    is_valid, error = DataValidators.validate_matches_minutes_consistency(
                        row['Matches played'], row['Minutes played']
                    )
                    if not is_valid:
                        record_errors.append(f"Inconsistencia partidos-minutos: {error}")
                
                # Consistencia goles-tiros
                if 'Goals' in row and 'Shots' in row:
                    is_valid, error = DataValidators.validate_goals_shots_consistency(
                        row['Goals'], row['Shots']
                    )
                    if not is_valid:
                        record_errors.append(f"Inconsistencia goles-tiros: {error}")
                
                # Consistencia altura-peso
                if 'Height' in row and 'Weight' in row:
                    is_valid, error = DataValidators.validate_height_weight_consistency(
                        row['Height'], row['Weight']
                    )
                    if not is_valid:
                        record_errors.append(f"Inconsistencia altura-peso: {error}")
            
            # Validar rangos de porcentajes si están habilitados
            if validation_config.get('validate_ranges', False):
                percentage_columns = [col for col in df.columns if '%' in col]
                for col in percentage_columns:
                    if col in row:
                        is_valid, error = DataValidators.validate_percentage_range(
                            row[col], col
                        )
                        if not is_valid:
                            record_errors.append(f"Porcentaje inválido en {col}: {error}")
            
            # Contar errores del registro
            if record_errors:
                stats['validation_errors'] += len(record_errors)
                errors.extend([f"Fila {idx + 1}: {error}" for error in record_errors])
            else:
                stats['valid_records'] += 1
        
        is_valid = stats['validation_errors'] == 0
        
        logger.info(f"✅ Validación completada: {stats['valid_records']}/{stats['total_records']} válidos")
        
        return is_valid, errors, stats
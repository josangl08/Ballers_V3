"""
Data Cleaners - Limpiadores específicos por tipo de dato
"""

import logging
import re
from typing import Any, Optional, Union

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DataCleaners:
    """
    Colección de métodos para limpiar diferentes tipos de datos.
    Resuelve problemas específicos como inconsistencias en nulos, 
    formatos incorrectos, etc.
    """

    @staticmethod
    def clean_null_values(
        value: Any, 
        target_type: str = "string",
        empty_string_as_null: bool = True
    ) -> Any:
        """
        Limpia valores nulos de manera consistente.
        
        PROBLEMA IDENTIFICADO: fillna("") convierte nan → "", pero David Cuerva 
        tiene Team="" y debería ser None consistente.
        
        Args:
            value: Valor a limpiar
            target_type: Tipo objetivo ('string', 'numeric', 'boolean')
            empty_string_as_null: Si strings vacíos deben convertirse a None
            
        Returns:
            Valor limpio o None
        """
        # Lista de valores que consideramos "nulos"
        null_values = [
            None, np.nan, "nan", "NaN", "null", "NULL", "None", 
            "undefined", "Undefined", "UNDEFINED"
        ]
        
        # Agregar string vacío si se especifica
        if empty_string_as_null:
            null_values.extend(["", " ", "  "])
            
        # Si es string, hacer trim y verificar
        if isinstance(value, str):
            value_clean = value.strip()
            if value_clean in null_values or (empty_string_as_null and value_clean == ""):
                return None
            return value_clean
            
        # Si está en la lista de nulos, retornar None
        if value in null_values:
            return None
            
        # Para números, verificar NaN específicamente
        if target_type == "numeric":
            try:
                if pd.isna(value):
                    return None
                return float(value) if value != "" else None
            except (ValueError, TypeError):
                return None
                
        return value

    @staticmethod
    def clean_team_name(team_name: Any) -> Optional[str]:
        """
        Limpia nombres de equipos de manera consistente.
        
        CASO ESPECÍFICO: David Cuerva Team="" → debe ser None
        
        Args:
            team_name: Nombre del equipo a limpiar
            
        Returns:
            Nombre limpio o None si no hay equipo
        """
        # Usar el limpiador general con reglas específicas para equipos
        cleaned = DataCleaners.clean_null_values(
            team_name, 
            target_type="string",
            empty_string_as_null=True
        )
        
        if cleaned is None:
            return None
            
        # Verificaciones adicionales para equipos
        if isinstance(cleaned, str):
            # Remover caracteres extraños comunes en nombres de equipos
            cleaned = re.sub(r'[^\w\s\-\.&]', '', cleaned).strip()
            
            # Si después de limpiar queda vacío, retornar None
            if not cleaned:
                return None
                
            # Normalizar espacios múltiples
            cleaned = re.sub(r'\s+', ' ', cleaned)
            
        return cleaned

    @staticmethod
    def clean_player_name(player_name: Any) -> Optional[str]:
        """
        Limpia nombres de jugadores.
        
        Args:
            player_name: Nombre del jugador a limpiar
            
        Returns:
            Nombre limpio o None si inválido
        """
        cleaned = DataCleaners.clean_null_values(
            player_name,
            target_type="string", 
            empty_string_as_null=True
        )
        
        if cleaned is None:
            return None
            
        if isinstance(cleaned, str):
            # Remover caracteres especiales pero mantener acentos
            cleaned = re.sub(r'[^\w\s\-\.\']', '', cleaned).strip()
            
            # Normalizar espacios
            cleaned = re.sub(r'\s+', ' ', cleaned)
            
            # Verificar que tenga al menos 2 caracteres
            if len(cleaned) < 2:
                return None
                
        return cleaned

    @staticmethod
    def clean_numeric_value(
        value: Any, 
        allow_negative: bool = True,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> Optional[float]:
        """
        Limpia valores numéricos.
        
        Args:
            value: Valor a limpiar
            allow_negative: Si se permiten valores negativos
            min_value: Valor mínimo permitido
            max_value: Valor máximo permitido
            
        Returns:
            Valor numérico limpio o None
        """
        # Primero usar el limpiador general
        cleaned = DataCleaners.clean_null_values(value, target_type="numeric")
        
        if cleaned is None:
            return None
            
        try:
            # Convertir a float
            numeric_value = float(cleaned)
            
            # Verificar NaN
            if pd.isna(numeric_value):
                return None
                
            # Verificar valores negativos
            if not allow_negative and numeric_value < 0:
                logger.warning(f"Valor negativo no permitido: {numeric_value}")
                return None
                
            # Verificar rango
            if min_value is not None and numeric_value < min_value:
                logger.warning(f"Valor {numeric_value} menor que mínimo {min_value}")
                return None
                
            if max_value is not None and numeric_value > max_value:
                logger.warning(f"Valor {numeric_value} mayor que máximo {max_value}")
                return None
                
            return numeric_value
            
        except (ValueError, TypeError, OverflowError):
            logger.warning(f"No se pudo convertir a numérico: {value}")
            return None

    @staticmethod
    def clean_percentage_value(value: Any) -> Optional[float]:
        """
        Limpia valores de porcentaje.
        
        Args:
            value: Valor de porcentaje a limpiar
            
        Returns:
            Valor de porcentaje (0-100) o None
        """
        # Si viene como string con %, removerlo
        if isinstance(value, str) and value.endswith('%'):
            value = value[:-1].strip()
            
        return DataCleaners.clean_numeric_value(
            value,
            allow_negative=False,
            min_value=0.0,
            max_value=100.0
        )

    @staticmethod
    def clean_integer_value(
        value: Any,
        allow_negative: bool = False,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> Optional[int]:
        """
        Limpia valores enteros.
        
        Args:
            value: Valor a limpiar
            allow_negative: Si se permiten valores negativos
            min_value: Valor mínimo permitido
            max_value: Valor máximo permitido
            
        Returns:
            Valor entero limpio o None
        """
        numeric_cleaned = DataCleaners.clean_numeric_value(
            value, allow_negative, min_value, max_value
        )
        
        if numeric_cleaned is None:
            return None
            
        try:
            return int(round(numeric_cleaned))
        except (ValueError, OverflowError):
            return None

    @staticmethod
    def clean_wyscout_id(wyscout_id: Any) -> Optional[int]:
        """
        Limpia IDs de Wyscout (deben ser enteros positivos).
        
        Args:
            wyscout_id: ID a limpiar
            
        Returns:
            ID limpio o None
        """
        return DataCleaners.clean_integer_value(
            wyscout_id,
            allow_negative=False,
            min_value=1
        )

    @staticmethod
    def clean_dataframe_nulls(
        df: pd.DataFrame, 
        columns_config: Optional[dict] = None
    ) -> pd.DataFrame:
        """
        Limpia nulos en un DataFrame completo usando configuración por columna.
        
        Args:
            df: DataFrame a limpiar
            columns_config: Dict con configuración por columna
                {
                    'column_name': {
                        'type': 'string|numeric|integer',
                        'empty_as_null': True/False,
                        'min_value': float,
                        'max_value': float
                    }
                }
                
        Returns:
            DataFrame limpio
        """
        df_clean = df.copy()
        
        if columns_config is None:
            columns_config = {}
            
        for column in df_clean.columns:
            if column in columns_config:
                config = columns_config[column]
            else:
                # Configuración por defecto
                config = {'type': 'string', 'empty_as_null': True}
                
            # Aplicar limpieza según tipo
            col_type = config.get('type', 'string')
            
            if col_type == 'string':
                df_clean[column] = df_clean[column].apply(
                    lambda x: DataCleaners.clean_null_values(
                        x, 
                        target_type='string',
                        empty_string_as_null=config.get('empty_as_null', True)
                    )
                )
            elif col_type == 'numeric':
                df_clean[column] = df_clean[column].apply(
                    lambda x: DataCleaners.clean_numeric_value(
                        x,
                        min_value=config.get('min_value'),
                        max_value=config.get('max_value')
                    )
                )
            elif col_type == 'integer':
                df_clean[column] = df_clean[column].apply(
                    lambda x: DataCleaners.clean_integer_value(
                        x,
                        min_value=config.get('min_value'),
                        max_value=config.get('max_value')
                    )
                )
                
        return df_clean
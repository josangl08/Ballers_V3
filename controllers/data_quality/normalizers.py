"""
Data Normalizers - Normalizadores específicos para diferentes tipos de datos
"""

import logging
import re
from typing import Any, Optional

import pandas as pd
from unidecode import unidecode

logger = logging.getLogger(__name__)


class DataNormalizers:
    """
    Colección de normalizadores para estandarizar datos en diferentes formatos.
    """

    @staticmethod
    def normalize_player_name(name: Any) -> Optional[str]:
        """
        Normaliza nombres de jugadores para matching consistente.
        
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

    @staticmethod
    def normalize_team_name(team_name: Any) -> Optional[str]:
        """
        Normaliza nombres de equipos.
        
        Args:
            team_name: Nombre del equipo
            
        Returns:
            Nombre normalizado o None
        """
        if pd.isna(team_name) or not isinstance(team_name, str):
            return None
            
        # Limpiar espacios y caracteres especiales
        normalized = team_name.strip()
        
        # Normalizar espacios múltiples
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Capitalizar primera letra de cada palabra
        normalized = normalized.title()
        
        return normalized if normalized else None

    @staticmethod
    def normalize_position(position: Any) -> Optional[str]:
        """
        Normaliza posiciones de jugadores.
        
        Args:
            position: Posición a normalizar
            
        Returns:
            Posición normalizada o None
        """
        if pd.isna(position) or not isinstance(position, str):
            return None
            
        # Mapping de posiciones comunes
        position_mapping = {
            'gk': 'GK',
            'goalkeeper': 'GK',
            'def': 'DEF',
            'defender': 'DEF',
            'cb': 'CB',
            'lb': 'LB', 
            'rb': 'RB',
            'mid': 'MID',
            'midfielder': 'MID',
            'cm': 'CM',
            'dm': 'DM',
            'am': 'AM',
            'lm': 'LM',
            'rm': 'RM',
            'fw': 'FW',
            'forward': 'FW',
            'striker': 'ST',
            'winger': 'W'
        }
        
        # Normalizar formato
        normalized = position.upper().strip()
        
        # Aplicar mapping si existe
        return position_mapping.get(normalized.lower(), normalized)

    @staticmethod
    def normalize_country_name(country: Any) -> Optional[str]:
        """
        Normaliza nombres de países.
        
        Args:
            country: País a normalizar
            
        Returns:
            País normalizado o None
        """
        if pd.isna(country) or not isinstance(country, str):
            return None
            
        # Mapping de países comunes con variaciones
        country_mapping = {
            'thailand': 'Thailand',
            'thai': 'Thailand',
            'brasil': 'Brazil',
            'brasil': 'Brazil',
            'south korea': 'South Korea',
            'korea': 'South Korea',
            'usa': 'United States',
            'united states of america': 'United States',
            'uk': 'United Kingdom',
            'england': 'United Kingdom',
            'scotland': 'United Kingdom',
            'wales': 'United Kingdom'
        }
        
        # Normalizar formato
        normalized = country.strip().title()
        
        # Aplicar mapping si existe
        return country_mapping.get(normalized.lower(), normalized)

    @staticmethod
    def normalize_percentage(value: Any) -> Optional[float]:
        """
        Normaliza valores de porcentaje a formato 0-100.
        
        Args:
            value: Valor a normalizar
            
        Returns:
            Porcentaje normalizado (0-100) o None
        """
        if pd.isna(value):
            return None
            
        try:
            # Si es string, remover % si existe
            if isinstance(value, str):
                value = value.replace('%', '').strip()
                if not value:
                    return None
            
            # Convertir a float
            pct_value = float(value)
            
            # Si está en formato 0-1, convertir a 0-100
            if 0 <= pct_value <= 1:
                pct_value *= 100
            
            # Validar rango
            if 0 <= pct_value <= 100:
                return round(pct_value, 2)
            else:
                logger.warning(f"Porcentaje fuera de rango: {pct_value}")
                return None
                
        except (ValueError, TypeError):
            logger.warning(f"No se pudo normalizar porcentaje: {value}")
            return None

    @staticmethod
    def normalize_currency(value: Any, currency_symbol: str = "€") -> Optional[float]:
        """
        Normaliza valores monetarios.
        
        Args:
            value: Valor monetario a normalizar
            currency_symbol: Símbolo de moneda a remover
            
        Returns:
            Valor numérico o None
        """
        if pd.isna(value):
            return None
            
        try:
            if isinstance(value, str):
                # Remover símbolos de moneda y separadores
                cleaned = value.replace(currency_symbol, '').replace(',', '').replace(' ', '')
                
                # Manejar notación de millones/miles
                if 'M' in cleaned.upper():
                    cleaned = cleaned.upper().replace('M', '')
                    multiplier = 1_000_000
                elif 'K' in cleaned.upper():
                    cleaned = cleaned.upper().replace('K', '')
                    multiplier = 1_000
                else:
                    multiplier = 1
                
                if not cleaned:
                    return None
                    
                return float(cleaned) * multiplier
            else:
                return float(value)
                
        except (ValueError, TypeError):
            logger.warning(f"No se pudo normalizar valor monetario: {value}")
            return None

    @staticmethod
    def normalize_height(height: Any) -> Optional[float]:
        """
        Normaliza altura a metros.
        
        Args:
            height: Altura a normalizar (puede estar en cm o m)
            
        Returns:
            Altura en metros o None
        """
        if pd.isna(height):
            return None
            
        try:
            if isinstance(height, str):
                # Remover unidades y espacios
                cleaned = height.lower().replace('cm', '').replace('m', '').strip()
                if not cleaned:
                    return None
                height_value = float(cleaned)
            else:
                height_value = float(height)
            
            # Si está en centímetros (>3), convertir a metros
            if height_value > 3:
                height_value = height_value / 100
            
            # Validar rango razonable (1.50m - 2.20m)
            if 1.50 <= height_value <= 2.20:
                return round(height_value, 2)
            else:
                logger.warning(f"Altura fuera de rango: {height_value}")
                return None
                
        except (ValueError, TypeError):
            logger.warning(f"No se pudo normalizar altura: {height}")
            return None

    @staticmethod
    def normalize_weight(weight: Any) -> Optional[float]:
        """
        Normaliza peso a kilogramos.
        
        Args:
            weight: Peso a normalizar
            
        Returns:
            Peso en kg o None
        """
        if pd.isna(weight):
            return None
            
        try:
            if isinstance(weight, str):
                # Remover unidades
                cleaned = weight.lower().replace('kg', '').replace('lbs', '').strip()
                if not cleaned:
                    return None
                weight_value = float(cleaned)
            else:
                weight_value = float(weight)
            
            # Si podría estar en libras (>120), convertir a kg
            if weight_value > 120:
                weight_value = weight_value * 0.453592  # lbs to kg
            
            # Validar rango razonable (50-120 kg)
            if 50 <= weight_value <= 120:
                return round(weight_value, 1)
            else:
                logger.warning(f"Peso fuera de rango: {weight_value}")
                return None
                
        except (ValueError, TypeError):
            logger.warning(f"No se pudo normalizar peso: {weight}")
            return None

    @staticmethod
    def normalize_competition_name(competition: Any) -> Optional[str]:
        """
        Normaliza nombres de competiciones.
        
        Args:
            competition: Competición a normalizar
            
        Returns:
            Competición normalizada o None
        """
        if pd.isna(competition) or not isinstance(competition, str):
            return None
            
        # Mapping de competiciones comunes
        competition_mapping = {
            'thai league 1': 'Thai League 1',
            'thai premier league': 'Thai League 1',
            'tpl': 'Thai League 1',
            'premier league': 'Premier League',
            'la liga': 'La Liga',
            'serie a': 'Serie A',
            'bundesliga': 'Bundesliga',
            'ligue 1': 'Ligue 1'
        }
        
        # Normalizar formato
        normalized = competition.strip()
        
        # Aplicar mapping si existe
        return competition_mapping.get(normalized.lower(), normalized)

    @staticmethod
    def normalize_dataframe_columns(df: pd.DataFrame, column_config: dict) -> pd.DataFrame:
        """
        Aplica normalización a múltiples columnas de un DataFrame.
        
        Args:
            df: DataFrame a normalizar
            column_config: Configuración de normalización por columna
                {
                    'Player': 'player_name',
                    'Team': 'team_name', 
                    'Primary position': 'position',
                    etc.
                }
                
        Returns:
            DataFrame normalizado
        """
        df_normalized = df.copy()
        
        normalizer_mapping = {
            'player_name': DataNormalizers.normalize_player_name,
            'team_name': DataNormalizers.normalize_team_name,
            'position': DataNormalizers.normalize_position,
            'country': DataNormalizers.normalize_country_name,
            'percentage': DataNormalizers.normalize_percentage,
            'currency': DataNormalizers.normalize_currency,
            'height': DataNormalizers.normalize_height,
            'weight': DataNormalizers.normalize_weight,
            'competition': DataNormalizers.normalize_competition_name
        }
        
        for column, normalizer_type in column_config.items():
            if column in df_normalized.columns and normalizer_type in normalizer_mapping:
                normalizer_func = normalizer_mapping[normalizer_type]
                df_normalized[column] = df_normalized[column].apply(normalizer_func)
                logger.info(f"Normalizada columna {column} usando {normalizer_type}")
        
        return df_normalized
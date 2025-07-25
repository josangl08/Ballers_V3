# controllers/sheets_controller_dash.py
"""
Controlador para Google Sheets específico para Dash - SIN dependencias de Streamlit.
Versión limpia que maneja datos financieros desde Google Sheets.
"""
import time
from typing import Optional, Tuple

import pandas as pd

from common.logging_config import get_logger
from config import get_config_value

from .google_client import sheets

logger = get_logger(__name__)

# Cache simple para evitar llamadas excesivas a la API
_cache = {}
_cache_ttl = 300  # 5 minutos

# Usar la función unificada para obtener el Sheet ID
SHEET_ID = get_config_value("ACCOUNTING_SHEET_ID")


def _is_cache_valid(key: str) -> bool:
    """Verifica si el cache es válido para una clave específica."""
    if key not in _cache:
        return False

    cache_time, _ = _cache[key]
    return (time.time() - cache_time) < _cache_ttl


def _get_from_cache(key: str) -> Optional[pd.DataFrame]:
    """Obtiene datos del cache si es válido."""
    if _is_cache_valid(key):
        _, data = _cache[key]
        return data
    return None


def _set_cache(key: str, data: pd.DataFrame) -> None:
    """Almacena datos en el cache."""
    _cache[key] = (time.time(), data)


def get_accounting_df_dash() -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Obtiene datos de Google Sheets para Dash con manejo de errores mejorado.

    Returns:
        Tuple[pd.DataFrame, Optional[str]]: DataFrame con datos y
            mensaje de error si existe
    """
    cache_key = f"accounting_data_{SHEET_ID}"

    # Verificar cache primero
    cached_data = _get_from_cache(cache_key)
    if cached_data is not None:
        logger.debug("Usando datos de Google Sheets desde cache")
        return cached_data, None

    if not SHEET_ID:
        error_msg = "ACCOUNTING_SHEET_ID no está configurado"
        logger.error(error_msg)
        return _get_empty_dataframe(), error_msg

    try:
        logger.info(f"Obteniendo datos de Google Sheets: {SHEET_ID}")

        rng = "Hoja 1!A:Z"  # Ampliar rango para capturar todas las columnas
        data = (
            sheets()
            .spreadsheets()
            .values()
            .get(spreadsheetId=SHEET_ID, range=rng)
            .execute()
            .get("values", [])
        )

        if not data:
            error_msg = "No se encontraron datos en Google Sheets"
            logger.warning(error_msg)
            return _get_empty_dataframe(), error_msg

        if len(data) < 2:
            error_msg = (
                "Google Sheets no tiene suficientes datos "
                "(necesita al menos encabezados + 1 fila)"
            )
            logger.warning(error_msg)
            return _get_empty_dataframe(), error_msg

        # Crear DataFrame
        df = pd.DataFrame(data[1:], columns=data[0])

        # Limpiar columnas vacías
        df = df.dropna(axis=1, how="all")  # Eliminar columnas completamente vacías
        df = df.loc[
            :, (df != "").any(axis=0)
        ]  # Eliminar columnas con solo strings vacíos

        logger.info(
            f"DataFrame creado con {len(df)} filas y columnas: {list(df.columns)}"
        )

        # Convertir columnas numéricas - Buscar automáticamente
        # columnas que parezcan numéricas
        numeric_keywords = [
            "Ingresos",
            "Gastos",
            "Ingreso",
            "Gasto",
            "Total",
            "Cantidad",
            "Importe",
            "Precio",
            "Coste",
            "Cost",
        ]
        for col in df.columns:
            # Convertir a numérico si la columna contiene palabras clave monetarias
            if any(keyword.lower() in col.lower() for keyword in numeric_keywords):
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                logger.debug(f"Columna '{col}' convertida a numérica")

        # Asegurar que existen las columnas mínimas esperadas
        for col in ("Ingresos", "Gastos"):
            if col not in df.columns:
                logger.warning(
                    f"Columna '{col}' no encontrada en Google Sheets, "
                    f"creando con valores 0"
                )
                df[col] = 0

        # Guardar en cache
        _set_cache(cache_key, df)

        logger.info(
            f"Datos de Google Sheets obtenidos exitosamente: {len(df)} registros"
        )
        return df, None

    except Exception as e:
        error_msg = f"Error accediendo a Google Sheets: {str(e)}"
        logger.error(error_msg, exc_info=True)

        # Devolver DataFrame de ejemplo para que no se rompa la app
        return _get_example_dataframe(), error_msg


def _get_empty_dataframe() -> pd.DataFrame:
    """Retorna un DataFrame vacío con la estructura esperada."""
    return pd.DataFrame(columns=["Fecha", "Descripción", "Ingresos", "Gastos"])


def _get_example_dataframe() -> pd.DataFrame:
    """Retorna un DataFrame de ejemplo cuando hay errores de conexión."""
    return pd.DataFrame(
        {
            "Fecha": ["2024-01-01"],
            "Descripción": ["Error de conexión - datos no disponibles"],
            "Ingresos": [0],
            "Gastos": [0],
        }
    )


def check_sheets_configuration_dash() -> Tuple[bool, str]:
    """
    Función helper para verificar la configuración de Sheets para Dash.

    Returns:
        Tuple[bool, str]: (is_configured, status_message)
    """
    if not SHEET_ID:
        return False, "ACCOUNTING_SHEET_ID no está configurado"

    try:
        # Probar conexión básica
        sheets_service = sheets()

        # Intentar obtener metadatos básicos del sheet
        sheet_metadata = (
            sheets_service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        )

        sheet_title = sheet_metadata.get("properties", {}).get("title", "Unknown")
        logger.info(f"Conexión exitosa con Google Sheet: {sheet_title}")

        return True, f"Configuración correcta - Conectado a: {sheet_title}"

    except Exception as e:
        error_msg = f"Error de configuración de Google Sheets: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def clear_sheets_cache() -> None:
    """Limpia el cache de Google Sheets."""
    _cache.clear()
    logger.info("Cache de Google Sheets limpiado")

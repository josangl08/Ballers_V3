"""
Extractor Module - Maneja la descarga de datos desde fuentes externas
"""

import hashlib
import logging
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import requests

from config import DATABASE_PATH
from controllers.db import get_db_session
from models import ThaiLeagueSeason

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
        self.cache_dir = Path(DATABASE_PATH).parent / "data" / "thai_league_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

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

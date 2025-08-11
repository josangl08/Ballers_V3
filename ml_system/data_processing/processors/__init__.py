"""
Preprocessors Module - Sistema de preprocesamiento batch híbrido
Extiende la arquitectura existente para manejo inteligente de temporadas.

Componentes del sistema:
- BatchProcessor: Procesamiento batch híbrido extendiendo ETLController
- SeasonMonitor: Monitoreo inteligente reutilizando ThaiLeagueController
- LookupEngine: Motor de búsqueda O(1) con índices optimizados

El sistema proporciona arquitectura dual CSV (RAW + PROCESSED) con:
✅ Temporadas finales: Procesamiento una vez, cache permanente
✅ Temporadas activas: Monitoreo automático y updates incrementales
✅ Búsquedas instantáneas: HashMap O(1) con cache LRU
✅ Máxima reutilización: 85%+ funcionalidad existente preservada
"""

from .batch_processor import BatchProcessor, run_batch_preprocessing
from .lookup_engine import (
    LookupEngine,
    lookup_player,
    lookup_season,
    search_by_position,
)
from .season_monitor import SeasonMonitor, check_season_status, monitor_seasons

__all__ = [
    # Clases principales
    "BatchProcessor",
    "SeasonMonitor",
    "LookupEngine",
    # Funciones de conveniencia
    "run_batch_preprocessing",
    "monitor_seasons",
    "check_season_status",
    "lookup_player",
    "lookup_season",
    "search_by_position",
]

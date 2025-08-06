# controllers/ml/__init__.py

"""
Módulo de Machine Learning para el sistema Ballers.

Este módulo implementa el Player Development Index (PDI) utilizando
metodología CRISP-DM y un modelo unificado híbrido.

Componentes principales:
- MLMetricsController: Controlador principal para cálculo de métricas ML
- FeatureEngineer: Ingeniería de features por tiers (Universal/Zona/Específica)
- PositionNormalizer: Normalización posicional para comparaciones justas
- PDICalculator: Cálculo del Player Development Index
- DashboardGenerator: Generación de visualizaciones por posición

Pipeline ETL ML:
1. FeatureEngineer extrae features por tiers desde ProfessionalStats
2. PositionNormalizer normaliza métricas para fair comparison
3. MLMetricsController integra todo y calcula PDI final
4. DashboardGenerator crea visualizaciones por posición
"""


# Lazy imports para evitar circular dependencies en webhook context
def get_ml_metrics_controller():
    """Lazy loader para MLMetricsController."""
    from .ml_metrics_controller import MLMetricsController

    return MLMetricsController


def get_feature_engineer():
    """Lazy loader para FeatureEngineer."""
    from .feature_engineer import FeatureEngineer

    return FeatureEngineer


def get_position_normalizer():
    """Lazy loader para PositionNormalizer."""
    from .position_normalizer import PositionNormalizer

    return PositionNormalizer


# Backward compatibility - solo import cuando se solicita explícitamente
MLMetricsController = None
FeatureEngineer = None
PositionNormalizer = None

__all__ = [
    "get_ml_metrics_controller",
    "get_feature_engineer",
    "get_position_normalizer",
]

# ml_system/evaluation/analysis/__init__.py

"""
Análisis y Evaluación de Modelos

Herramientas para evaluación de performance y análisis de resultados ML.
"""

# Advanced features
try:
    from .advanced_features import (
        AdvancedFeatureEngineer,
        create_advanced_feature_pipeline,
    )

    _advanced_available = True
except ImportError:
    _advanced_available = False

# Evaluation pipeline
try:
    from .evaluation_pipeline import MLEvaluationPipeline

    _evaluation_available = True
except ImportError:
    _evaluation_available = False

# Build __all__ dinamically
__all__ = []
if _advanced_available:
    __all__.extend(["AdvancedFeatureEngineer", "create_advanced_feature_pipeline"])
if _evaluation_available:
    __all__.extend(["MLEvaluationPipeline"])

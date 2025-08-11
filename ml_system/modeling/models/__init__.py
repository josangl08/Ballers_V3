# ml_system/modeling/models/__init__.py

"""
Modelos de Machine Learning

Implementaciones de modelos híbridos y baseline para predicción PDI.
"""

from .hybrid_sklearn_model import (
    HybridSklearnModel,
    create_hybrid_sklearn_pipeline,
    evaluate_hybrid_model,
)

# Baseline models
try:
    from .baseline_model import BaselineEvaluator, run_comprehensive_baseline_evaluation

    __all__ = [
        "HybridSklearnModel",
        "create_hybrid_sklearn_pipeline",
        "evaluate_hybrid_model",
        "BaselineEvaluator",
        "run_comprehensive_baseline_evaluation",
    ]
except ImportError:
    __all__ = [
        "HybridSklearnModel",
        "create_hybrid_sklearn_pipeline",
        "evaluate_hybrid_model",
    ]

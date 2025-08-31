# ml_system/deployment/services/__init__.py

"""
Servicios de despliegue del sistema ML - Predicciones PDI optimizadas

Este módulo contiene los servicios para el despliegue en producción del
sistema de predicción PDI optimizado con MAE 3.692.

Componentes principales:
- model_loader: Carga automática del mejor modelo disponible
- pdi_prediction_service: Servicio principal de predicciones
"""

__all__ = [
    "ModelLoader",
    "load_production_model",
    "PdiPredictionService",
    "get_pdi_prediction_service",
]

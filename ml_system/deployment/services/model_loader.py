#!/usr/bin/env python3
"""
Model Loader - Cargador automático del mejor modelo ML disponible

Este módulo se encarga de cargar automáticamente el modelo ML optimizado más reciente
para predicciones PDI en producción.

Autor: Proyecto Fin de Máster - Python Aplicado al Deporte  
Fecha: Agosto 2025
"""

import joblib
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import sys

# Configurar path del proyecto
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

logger = logging.getLogger(__name__)


class ModelLoader:
    """Cargador inteligente de modelos ML optimizados."""
    
    def __init__(self):
        self.project_root = project_root
        self.models_dir = self.project_root / "ml_system" / "outputs" / "final_optimization"
        self.current_model = None
        self.model_metadata = {}
        
    def get_latest_model_path(self) -> Optional[Path]:
        """
        Encuentra el modelo más reciente basado en timestamp.
        
        Returns:
            Path al modelo más reciente o None si no se encuentra
        """
        try:
            model_pattern = "best_pdi_model_*.joblib"
            model_files = list(self.models_dir.glob(model_pattern))
            
            if not model_files:
                logger.warning(f"No se encontraron modelos en {self.models_dir}")
                return None
                
            # Ordenar por timestamp en nombre de archivo
            latest_model = sorted(model_files, key=lambda x: x.stem.split('_')[-2:])[-1]
            logger.info(f"Modelo más reciente identificado: {latest_model.name}")
            
            return latest_model
            
        except Exception as e:
            logger.error(f"Error buscando modelo más reciente: {e}")
            return None
    
    def load_model(self, model_path: Optional[Path] = None) -> Tuple[Optional[Any], Dict[str, Any]]:
        """
        Carga el modelo ML optimizado.
        
        Args:
            model_path: Path específico del modelo (opcional, usa el más reciente por defecto)
            
        Returns:
            Tupla (modelo_cargado, metadata)
        """
        try:
            if model_path is None:
                model_path = self.get_latest_model_path()
                
            if model_path is None or not model_path.exists():
                logger.error(f"Modelo no encontrado: {model_path}")
                return None, {}
            
            # Cargar modelo
            logger.info(f"Cargando modelo desde: {model_path}")
            model = joblib.load(model_path)
            
            # Extraer metadata del nombre del archivo
            filename_parts = model_path.stem.split('_')
            timestamp = '_'.join(filename_parts[-2:])  # fecha y hora
            
            metadata = {
                'model_path': str(model_path),
                'model_name': model_path.name,
                'timestamp': timestamp,
                'expected_mae': 3.692,  # MAE conocido del modelo optimizado
                'model_type': 'ensemble_optimized',
                'features_expected': 127,  # Número esperado de features
                'loaded_successfully': True
            }
            
            # Validaciones básicas del modelo
            if hasattr(model, 'predict'):
                metadata['has_predict_method'] = True
            else:
                logger.warning("El modelo no tiene método predict")
                metadata['has_predict_method'] = False
                
            if hasattr(model, 'feature_names_in_'):
                metadata['n_features'] = len(model.feature_names_in_)
                metadata['feature_names'] = list(model.feature_names_in_)
            else:
                logger.warning("El modelo no tiene información de features")
                
            self.current_model = model
            self.model_metadata = metadata
            
            logger.info(f"Modelo cargado exitosamente: MAE esperado {metadata['expected_mae']}")
            return model, metadata
            
        except Exception as e:
            logger.error(f"Error cargando modelo: {e}")
            return None, {'error': str(e), 'loaded_successfully': False}
    
    def validate_model(self, model: Any, metadata: Dict[str, Any]) -> bool:
        """
        Valida que el modelo cargado sea funcional.
        
        Args:
            model: Modelo cargado
            metadata: Metadata del modelo
            
        Returns:
            True si el modelo es válido, False en caso contrario
        """
        try:
            if model is None:
                logger.error("Modelo es None")
                return False
                
            if not metadata.get('has_predict_method', False):
                logger.error("Modelo no tiene método predict")
                return False
                
            # Test básico con datos dummy
            if hasattr(model, 'n_features_in_'):
                n_features = model.n_features_in_
                import numpy as np
                dummy_data = np.random.random((1, n_features))
                
                try:
                    prediction = model.predict(dummy_data)
                    if prediction is not None and len(prediction) > 0:
                        logger.info(f"Validación exitosa: predicción dummy = {prediction[0]:.2f}")
                        return True
                except Exception as pred_error:
                    logger.error(f"Error en predicción de validación: {pred_error}")
                    return False
            else:
                logger.warning("No se pudo determinar número de features, saltando validación de predicción")
                return True
                
        except Exception as e:
            logger.error(f"Error validando modelo: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Retorna información del modelo actualmente cargado.
        
        Returns:
            Diccionario con información del modelo
        """
        if self.current_model is None:
            return {'status': 'no_model_loaded'}
            
        return {
            'status': 'loaded',
            'metadata': self.model_metadata,
            'model_available': True
        }


# Instancia global para reutilizar
_global_model_loader = None

def get_model_loader() -> ModelLoader:
    """Singleton para obtener el loader de modelos."""
    global _global_model_loader
    if _global_model_loader is None:
        _global_model_loader = ModelLoader()
    return _global_model_loader


def load_production_model() -> Tuple[Optional[Any], Dict[str, Any]]:
    """
    Función conveniente para cargar el modelo de producción.
    
    Returns:
        Tupla (modelo, metadata)
    """
    loader = get_model_loader()
    model, metadata = loader.load_model()
    
    if model is not None:
        is_valid = loader.validate_model(model, metadata)
        metadata['validation_passed'] = is_valid
        
        if not is_valid:
            logger.warning("Modelo cargado pero falló validación")
            
    return model, metadata
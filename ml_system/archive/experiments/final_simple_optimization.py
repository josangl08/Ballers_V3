#!/usr/bin/env python3
"""
Optimización Final Simplificada para MAE < 3.5

Versión simplificada pero robusta del optimizador final que evita
problemas técnicos manteniendo técnicas avanzadas efectivas.

Autor: Proyecto Fin de Máster - Python Aplicado al Deporte
Fecha: Agosto 2025
"""

import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesRegressor, 
    RandomForestRegressor, 
    StackingRegressor,
)
from sklearn.linear_model import Ridge, ElasticNet
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

# Configurar path del proyecto
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Imports del sistema ML
from ml_system.modeling.train_future_pdi_model import FuturePDIPredictor
from ml_system.evaluation.analysis.advanced_features import AdvancedFeatureEngineer

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')


class SimpleFinalOptimizer:
    """Optimizador final simplificado pero efectivo."""
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.predictor = FuturePDIPredictor()
        self.feature_engineer = AdvancedFeatureEngineer()
        
    def create_optimized_ensemble(self):
        """Crea ensemble optimizado y robusto."""
        # Modelos base ultra-optimizados
        rf_model = RandomForestRegressor(
            n_estimators=500,
            max_depth=6,
            min_samples_split=8,
            min_samples_leaf=4,
            max_features=0.5,
            random_state=self.random_state,
            n_jobs=-1
        )
        
        et_model = ExtraTreesRegressor(
            n_estimators=400,
            max_depth=8,
            min_samples_split=6,
            min_samples_leaf=3,
            max_features=0.6,
            random_state=self.random_state,
            n_jobs=-1
        )
        
        # Meta-learner simple pero efectivo
        meta_learner = Ridge(alpha=2.0)
        
        # Ensemble de stacking
        stacking_model = StackingRegressor(
            estimators=[
                ('rf', rf_model),
                ('et', et_model),
                ('elastic', ElasticNet(alpha=0.1, l1_ratio=0.3, random_state=self.random_state))
            ],
            final_estimator=meta_learner,
            cv=3,
            n_jobs=-1
        )
        
        return stacking_model
    
    def temporal_validation_robust(self, model, X, y, seasons):
        """Validación temporal robusta."""
        unique_seasons = sorted(seasons.unique())
        
        if len(unique_seasons) < 3:
            return {'error': 'Insuficientes temporadas'}
            
        # Split conservador: usar últimas 2 temporadas como test
        test_seasons = unique_seasons[-2:]
        train_seasons = unique_seasons[:-2]
        
        train_mask = seasons.isin(train_seasons)
        test_mask = seasons.isin(test_seasons)
        
        X_train, X_test = X[train_mask], X[test_mask]
        y_train, y_test = y[train_mask], y[test_mask]
        
        if len(X_train) < 50 or len(X_test) < 20:
            return {'error': 'Insuficientes muestras'}
        
        # Entrenar y evaluar
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        return {
            'mae': mae,
            'r2': r2,
            'target_achieved': mae < 3.5,
            'train_seasons': train_seasons,
            'test_seasons': test_seasons,
            'train_samples': len(X_train),
            'test_samples': len(X_test)
        }
    
    def run_final_optimization(self):
        """Ejecuta optimización final completa."""
        try:
            logger.info("🎯 OPTIMIZACIÓN FINAL SIMPLIFICADA PARA MAE < 3.5")
            
            # Cargar datos
            data = self.predictor.load_historical_data()
            data_enhanced = self.feature_engineer.engineer_advanced_features(
                data, target_mode='future'
            )
            
            X, y, seasons = self.predictor.create_training_dataset(
                data_enhanced, years_ahead=1
            )
            
            logger.info(f"Dataset: {len(X)} samples, {len(X.columns)} features")
            
            # Crear modelo optimizado
            model = self.create_optimized_ensemble()
            
            # Validación temporal
            results = self.temporal_validation_robust(model, X, y, seasons)
            
            if 'error' not in results:
                logger.info(f"MAE Final: {results['mae']:.3f}")
                logger.info(f"R² Final: {results['r2']:.3f}")
                logger.info(f"Objetivo < 3.5: {'✅ CUMPLIDO' if results['target_achieved'] else '❌ PENDIENTE'}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return {'error': str(e)}


def main():
    """Función principal."""
    try:
        print("🏆 OPTIMIZACIÓN FINAL SIMPLIFICADA")
        print("=" * 50)
        
        optimizer = SimpleFinalOptimizer()
        results = optimizer.run_final_optimization()
        
        print("\n📊 RESULTADOS FINALES:")
        if 'error' in results:
            print(f"❌ Error: {results['error']}")
        else:
            mae = results['mae']
            r2 = results['r2']
            achieved = results['target_achieved']
            
            print(f"   MAE Final: {mae:.3f}")
            print(f"   R² Final: {r2:.3f}")
            print(f"   Objetivo MAE < 3.5: {'✅ CUMPLIDO' if achieved else '❌ PENDIENTE'}")
            
            if achieved:
                print(f"\n🏆 ¡OBJETIVO ALCANZADO! MAE {mae:.3f} < 3.5")
            else:
                gap = mae - 3.5
                print(f"\n🔧 Gap restante: {gap:.3f} MAE")
        
        print("\n✅ Optimización completada")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
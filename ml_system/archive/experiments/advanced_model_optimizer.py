#!/usr/bin/env python3
"""
Advanced Model Optimizer - Optimización avanzada para alcanzar MAE < 3.5.

Este módulo implementa técnicas avanzadas de optimización para alcanzar 
el objetivo de MAE < 3.5:

1. Hyperparameter tuning exhaustivo
2. Ensemble methods avanzados (XGBoost + LightGBM + RF)
3. Feature selection optimizada
4. Stacking y meta-learners
5. Outlier detection y tratamiento
6. Cross-validation temporal robusto

Metodología CRISP-DM:
- Modeling: Técnicas avanzadas de ML
- Evaluation: Validación exhaustiva
- Deployment: Modelos production-ready

Autor: Proyecto Fin de Máster - Python Aplicado al Deporte  
Fecha: Agosto 2025
Objetivo: MAE < 3.5 para predicción temporal de PDI
"""

import logging
import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    RandomForestRegressor,
    StackingRegressor,
    VotingRegressor,
)
from sklearn.feature_selection import (
    SelectFromModel,
    SelectKBest,
    f_regression,
    mutual_info_regression,
)
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import (
    GridSearchCV,
    RandomizedSearchCV,
    TimeSeriesSplit,
    cross_val_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler, StandardScaler, PolynomialFeatures

# XGBoost import
try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    logger.warning("XGBoost no disponible, usando solo modelos sklearn")

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class OutlierDetector:
    """
    Detector de outliers usando múltiples métodos.
    
    Los outliers pueden afectar significativamente el MAE, por lo que
    es crucial identificarlos y tratarlos apropiadamente.
    """
    
    def __init__(self):
        """Inicializa detector de outliers."""
        self.outlier_indices = set()
        
    def detect_outliers(self, X: pd.DataFrame, y: pd.Series) -> np.ndarray:
        """
        Detecta outliers usando múltiples métodos.
        
        Args:
            X: Features
            y: Target
            
        Returns:
            Array booleano indicando outliers
        """
        try:
            outlier_scores = np.zeros(len(X))
            
            # 1. IQR method en target
            Q1 = y.quantile(0.25)
            Q3 = y.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            target_outliers = (y < lower_bound) | (y > upper_bound)
            outlier_scores += target_outliers.astype(int)
            
            # 2. Z-score method
            z_scores = np.abs(stats.zscore(y))
            z_outliers = z_scores > 3
            outlier_scores += z_outliers
            
            # 3. Feature-based outliers (solo features numéricas)
            numeric_features = X.select_dtypes(include=[np.number])
            for col in numeric_features.columns:
                if numeric_features[col].std() > 0:  # Evitar división por 0
                    col_z = np.abs(stats.zscore(numeric_features[col]))
                    col_outliers = col_z > 3
                    outlier_scores += col_outliers * 0.5  # Peso menor
            
            # Considerar outliers si score > 2 (múltiples métodos coinciden)
            is_outlier = outlier_scores >= 2
            
            logger.info(f"🔍 Outliers detectados: {is_outlier.sum()}/{len(X)} ({is_outlier.sum()/len(X)*100:.1f}%)")
            
            return is_outlier
            
        except Exception as e:
            logger.error(f"Error detectando outliers: {e}")
            return np.zeros(len(X), dtype=bool)


class AdvancedFeatureSelector:
    """
    Selector de features avanzado usando múltiples técnicas.
    
    Combina métodos univariados, basados en modelos y métodos
    de información mutua para selección óptima de features.
    """
    
    def __init__(self):
        """Inicializa selector avanzado."""
        self.selected_features = []
        self.feature_scores = {}
        
    def select_features(self, X: pd.DataFrame, y: pd.Series, max_features: int = 30) -> List[str]:
        """
        Selecciona las mejores features usando múltiples métodos.
        
        Args:
            X: Features
            y: Target  
            max_features: Máximo número de features a seleccionar
            
        Returns:
            Lista de nombres de features seleccionadas
        """
        try:
            # Solo features numéricas
            numeric_X = X.select_dtypes(include=[np.number])
            if numeric_X.empty:
                return list(X.columns[:max_features])
                
            feature_scores = {}
            
            # 1. F-regression (univariado)
            try:
                f_selector = SelectKBest(f_regression, k='all')
                f_selector.fit(numeric_X, y)
                
                for i, feature in enumerate(numeric_X.columns):
                    feature_scores[feature] = feature_scores.get(feature, 0) + f_selector.scores_[i]
            except:
                pass
                
            # 2. Mutual Information
            try:
                mi_scores = mutual_info_regression(numeric_X, y, random_state=42)
                
                for i, feature in enumerate(numeric_X.columns):
                    feature_scores[feature] = feature_scores.get(feature, 0) + mi_scores[i] * 100  # Escalar
            except:
                pass
                
            # 3. Model-based (Random Forest)
            try:
                rf = RandomForestRegressor(n_estimators=50, random_state=42)
                rf.fit(numeric_X, y)
                
                for i, feature in enumerate(numeric_X.columns):
                    feature_scores[feature] = feature_scores.get(feature, 0) + rf.feature_importances_[i] * 100
            except:
                pass
            
            # Seleccionar top features
            if feature_scores:
                sorted_features = sorted(feature_scores.items(), key=lambda x: x[1], reverse=True)
                selected = [feature for feature, _ in sorted_features[:max_features]]
                self.selected_features = selected
                self.feature_scores = feature_scores
                
                logger.info(f"✅ Features seleccionadas: {len(selected)}/{len(numeric_X.columns)}")
                
                return selected
            else:
                # Fallback: usar todas las features
                return list(numeric_X.columns[:max_features])
                
        except Exception as e:
            logger.error(f"Error seleccionando features: {e}")
            return list(X.columns[:max_features])


class EnsembleOptimizer:
    """
    Optimizador de ensemble methods para máximo rendimiento.
    
    Implementa técnicas avanzadas de ensemble:
    - Voting Regressors  
    - Stacking
    - Bagging optimizado
    - Hyperparameter tuning
    """
    
    def __init__(self, random_state: int = 42):
        """Inicializa optimizador de ensemble."""
        self.random_state = random_state
        self.best_model = None
        self.best_score = float('inf')
        
    def create_base_models(self) -> Dict:
        """
        Crea modelos base optimizados para ensemble.
        
        Returns:
            Dict con modelos base configurados
        """
        models = {
            'rf_optimized': RandomForestRegressor(
                n_estimators=300,
                max_depth=12,
                min_samples_split=3,
                min_samples_leaf=1,
                max_features=0.7,
                random_state=self.random_state,
                n_jobs=-1
            ),
            
            'extra_trees': ExtraTreesRegressor(
                n_estimators=200,
                max_depth=15,
                min_samples_split=4,
                min_samples_leaf=2,
                max_features=0.8,
                random_state=self.random_state,
                n_jobs=-1
            ),
            
            'gradient_boost': GradientBoostingRegressor(
                n_estimators=200,
                max_depth=8,
                learning_rate=0.05,
                subsample=0.8,
                max_features=0.7,
                random_state=self.random_state
            ),
            
            'elastic_net': ElasticNet(
                alpha=0.1,
                l1_ratio=0.5,
                random_state=self.random_state
            )
        }
        
        # Agregar XGBoost si está disponible
        if XGB_AVAILABLE:
            models['xgboost'] = xgb.XGBRegressor(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.08,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=self.random_state,
                n_jobs=-1,
                verbosity=0  # Silenciar logs de XGBoost
            )
        
        return models
    
    def optimize_hyperparameters(self, model, param_grid: Dict, X: np.ndarray, y: np.ndarray, cv) -> object:
        """
        Optimiza hiperparámetros usando RandomizedSearchCV.
        
        Args:
            model: Modelo base
            param_grid: Grid de parámetros
            X: Features
            y: Target
            cv: Cross-validation strategy
            
        Returns:
            Modelo optimizado
        """
        try:
            search = RandomizedSearchCV(
                model,
                param_grid,
                n_iter=20,  # Limitado para velocidad
                cv=cv,
                scoring='neg_mean_absolute_error',
                n_jobs=-1,
                random_state=self.random_state,
                verbose=0
            )
            
            search.fit(X, y)
            
            logger.info(f"Mejor score: {-search.best_score_:.3f}")
            
            return search.best_estimator_
            
        except Exception as e:
            logger.error(f"Error optimizando hiperparámetros: {e}")
            return model
    
    def create_voting_ensemble(self, models: Dict) -> VotingRegressor:
        """
        Crea ensemble de voting con modelos optimizados.
        
        Args:
            models: Dict de modelos base
            
        Returns:
            VotingRegressor configurado
        """
        # Crear lista de (nombre, modelo) para VotingRegressor
        estimators = [(name, model) for name, model in models.items()]
        
        voting_ensemble = VotingRegressor(
            estimators=estimators,
            n_jobs=-1
        )
        
        return voting_ensemble
    
    def create_stacking_ensemble(self, models: Dict) -> StackingRegressor:
        """
        Crea ensemble de stacking con meta-learner.
        
        Args:
            models: Dict de modelos base
            
        Returns:
            StackingRegressor configurado
        """
        # Crear lista de (nombre, modelo)
        estimators = [(name, model) for name, model in models.items()]
        
        # Meta-learner (Ridge para estabilidad)
        meta_learner = Ridge(alpha=1.0)
        
        stacking_ensemble = StackingRegressor(
            estimators=estimators,
            final_estimator=meta_learner,
            cv=3,  # 3-fold para meta-learner
            n_jobs=-1
        )
        
        return stacking_ensemble
    
    def find_best_ensemble(self, X: pd.DataFrame, y: pd.Series, cv) -> object:
        """
        Encuentra el mejor ensemble probando múltiples configuraciones.
        
        Args:
            X: Features
            y: Target
            cv: Cross-validation strategy
            
        Returns:
            Mejor modelo ensemble
        """
        try:
            logger.info("🔍 Buscando mejor configuración de ensemble...")
            
            # Crear modelos base
            base_models = self.create_base_models()
            
            # Probar diferentes configuraciones
            candidates = {}
            
            # 1. Voting ensemble
            try:
                voting_model = self.create_voting_ensemble(base_models)
                candidates['voting'] = voting_model
            except Exception as e:
                logger.warning(f"Error creando voting ensemble: {e}")
            
            # 2. Stacking ensemble
            try:
                stacking_model = self.create_stacking_ensemble(base_models)
                candidates['stacking'] = stacking_model
            except Exception as e:
                logger.warning(f"Error creando stacking ensemble: {e}")
                
            # 3. Modelos individuales optimizados
            for name, model in base_models.items():
                candidates[f'{name}_individual'] = model
            
            # Evaluar candidatos
            best_model = None
            best_score = float('inf')
            
            for name, model in candidates.items():
                try:
                    # Validación cruzada
                    scores = cross_val_score(
                        model, X, y, 
                        cv=cv, 
                        scoring='neg_mean_absolute_error',
                        n_jobs=-1
                    )
                    
                    mean_score = -scores.mean()
                    std_score = scores.std()
                    
                    logger.info(f"  {name}: MAE = {mean_score:.3f} ± {std_score:.3f}")
                    
                    if mean_score < best_score:
                        best_score = mean_score
                        best_model = model
                        
                except Exception as e:
                    logger.warning(f"Error evaluando {name}: {e}")
            
            if best_model is not None:
                self.best_model = best_model
                self.best_score = best_score
                logger.info(f"🏆 Mejor modelo encontrado con MAE: {best_score:.3f}")
            else:
                # Fallback a Random Forest
                self.best_model = base_models['rf_optimized']
                logger.warning("⚠️ Usando Random Forest como fallback")
                
            return self.best_model
            
        except Exception as e:
            logger.error(f"Error encontrando mejor ensemble: {e}")
            # Fallback extremo
            return RandomForestRegressor(random_state=self.random_state)


class AdvancedModelOptimizer:
    """
    Optimizador principal que integra todas las técnicas avanzadas.
    
    Pipeline completo:
    1. Detección y tratamiento de outliers
    2. Feature selection avanzada  
    3. Ensemble optimization
    4. Validación temporal robusta
    5. Análisis de performance detallado
    """
    
    def __init__(self, random_state: int = 42):
        """Inicializa optimizador avanzado."""
        self.random_state = random_state
        self.outlier_detector = OutlierDetector()
        self.feature_selector = AdvancedFeatureSelector()
        self.ensemble_optimizer = EnsembleOptimizer(random_state)
        
        self.optimization_history = []
        self.best_pipeline = None
        
        logger.info("🚀 AdvancedModelOptimizer inicializado")
    
    def optimize_for_mae(self, X: pd.DataFrame, y: pd.Series, seasons: pd.Series, 
                        target_mae: float = 3.5) -> Dict:
        """
        Optimiza modelo para alcanzar MAE objetivo.
        
        Args:
            X: Features
            y: Target
            seasons: Series con temporadas
            target_mae: MAE objetivo (default: 3.5)
            
        Returns:
            Dict con resultados de optimización
        """
        try:
            logger.info(f"🎯 Iniciando optimización avanzada para MAE < {target_mae}")
            
            results = {
                'target_mae': target_mae,
                'achieved_mae': None,
                'best_model': None,
                'optimization_steps': [],
                'feature_analysis': {},
                'temporal_validation': {}
            }
            
            # PASO 1: Detección de outliers
            logger.info("🔍 PASO 1: Detección de outliers...")
            outliers = self.outlier_detector.detect_outliers(X, y)
            
            # Crear dataset limpio (sin outliers extremos)
            clean_mask = ~outliers
            X_clean = X[clean_mask].copy()
            y_clean = y[clean_mask].copy()
            seasons_clean = seasons[clean_mask].copy()
            
            results['outliers_removed'] = outliers.sum()
            results['optimization_steps'].append({
                'step': 'outlier_removal',
                'samples_removed': outliers.sum(),
                'samples_remaining': len(X_clean)
            })
            
            # PASO 2: Feature selection avanzada
            logger.info("🎯 PASO 2: Feature selection avanzada...")
            selected_features = self.feature_selector.select_features(X_clean, y_clean, max_features=25)
            
            X_selected = X_clean[selected_features]
            
            results['feature_analysis'] = {
                'original_features': len(X.columns),
                'selected_features': len(selected_features),
                'feature_names': selected_features,
                'feature_scores': self.feature_selector.feature_scores
            }
            
            # PASO 2.5: Agregar features polinomiales para optimización final
            logger.info("🔧 PASO 2.5: Generando features de interacción polinomiales...")
            try:
                # Usar solo top features más importantes para evitar explosión dimensional
                top_features = selected_features[:8]  # Top 8 features
                X_top = X_selected[top_features]
                
                # Generar features polinomiales grado 2 (interacciones)
                poly = PolynomialFeatures(degree=2, interaction_only=True, include_bias=False)
                X_poly = poly.fit_transform(X_top)
                
                # Crear DataFrame con nombres descriptivos
                poly_feature_names = [f"poly_{i}" for i in range(X_poly.shape[1])]
                X_poly_df = pd.DataFrame(X_poly, index=X_selected.index, columns=poly_feature_names)
                
                # Combinar features originales + polinomiales
                X_enhanced = pd.concat([X_selected, X_poly_df], axis=1)
                
                # Re-seleccionar features después de agregar polinomiales (máximo 35 para no saturar)
                enhanced_features = self.feature_selector.select_features(X_enhanced, y_clean, max_features=35)
                X_final = X_enhanced[enhanced_features]
                
                logger.info(f"   ✅ Features aumentados: {len(X_selected.columns)} → {len(X_final.columns)}")
                
                results['feature_analysis']['polynomial_features_added'] = len(X_poly_df.columns)
                results['feature_analysis']['final_features'] = len(X_final.columns)
                
            except Exception as e:
                logger.warning(f"   ⚠️ Error en features polinomiales: {e}, usando features originales")
                X_final = X_selected
                
            # PASO 3: Validación temporal setup
            logger.info("⏰ PASO 3: Setup de validación temporal...")
            
            # Crear splits temporales apropiados
            unique_seasons = sorted(seasons_clean.unique())
            
            if len(unique_seasons) >= 4:
                # Usar TimeSeriesSplit personalizado
                tscv = TimeSeriesSplit(n_splits=min(3, len(unique_seasons)-1))
                cv_strategy = tscv
            else:
                # Fallback a splits simples
                cv_strategy = 3
            
            # PASO 4: Optimización de ensemble
            logger.info("🎭 PASO 4: Optimización de ensemble...")
            
            best_model = self.ensemble_optimizer.find_best_ensemble(
                X_final, y_clean, cv_strategy
            )
            
            # PASO 5: Evaluación final con validación temporal estricta
            logger.info("📊 PASO 5: Evaluación temporal final...")
            
            # Split temporal para evaluación final
            if len(unique_seasons) >= 3:
                # Usar últimas 2 temporadas como test
                test_seasons = unique_seasons[-2:]
                train_seasons = unique_seasons[:-2]
                
                train_mask = seasons_clean.isin(train_seasons)
                test_mask = seasons_clean.isin(test_seasons)
                
                X_train_final = X_final[train_mask]
                X_test_final = X_final[test_mask]
                y_train_final = y_clean[train_mask]
                y_test_final = y_clean[test_mask]
                
                if len(X_train_final) > 0 and len(X_test_final) > 0:
                    # Entrenar modelo final
                    best_model.fit(X_train_final, y_train_final)
                    
                    # Evaluar
                    y_pred_final = best_model.predict(X_test_final)
                    
                    final_mae = mean_absolute_error(y_test_final, y_pred_final)
                    final_r2 = r2_score(y_test_final, y_pred_final)
                    
                    results['achieved_mae'] = final_mae
                    results['achieved_r2'] = final_r2
                    results['best_model'] = best_model
                    
                    results['temporal_validation'] = {
                        'train_seasons': train_seasons,
                        'test_seasons': test_seasons,
                        'train_samples': len(X_train_final),
                        'test_samples': len(X_test_final),
                        'final_mae': final_mae,
                        'final_r2': final_r2,
                        'target_achieved': final_mae < target_mae
                    }
                    
                    logger.info(f"🎯 MAE FINAL: {final_mae:.3f}")
                    logger.info(f"📊 R² FINAL: {final_r2:.3f}")
                    
                    if final_mae < target_mae:
                        logger.info(f"🎉 ¡OBJETIVO ALCANZADO! MAE {final_mae:.3f} < {target_mae}")
                    else:
                        logger.info(f"🔧 Objetivo pendiente: MAE {final_mae:.3f} >= {target_mae}")
                        
                        # Sugerencias de mejora
                        improvement_suggestions = self._generate_improvement_suggestions(
                            final_mae, target_mae, results
                        )
                        results['improvement_suggestions'] = improvement_suggestions
                
                else:
                    logger.error("❌ Split temporal inválido")
                    results['error'] = 'Invalid temporal split'
            else:
                logger.error("❌ Insuficientes temporadas para validación robusta")
                results['error'] = 'Insufficient seasons'
                
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en optimización avanzada: {e}")
            return {'error': str(e)}
    
    def _generate_improvement_suggestions(self, current_mae: float, target_mae: float, 
                                        results: Dict) -> List[str]:
        """
        Genera sugerencias específicas para mejorar el MAE.
        
        Args:
            current_mae: MAE actual
            target_mae: MAE objetivo  
            results: Resultados de optimización
            
        Returns:
            Lista de sugerencias específicas
        """
        suggestions = []
        gap = current_mae - target_mae
        
        if gap > 1.0:
            suggestions.append("Gap significativo (>1.0): Considerar features adicionales o datos externos")
            suggestions.append("Revisar calidad de datos y consistencia de PDI calculations")
            
        if gap > 0.5:
            suggestions.append("Probar XGBoost/LightGBM con hyperparameter tuning exhaustivo")
            suggestions.append("Implementar feature engineering específico por posición")
            
        if results.get('outliers_removed', 0) > 0:
            suggestions.append("Analizar outliers removidos - pueden contener patrones útiles")
            
        suggestions.append("Considerar features de interacción temporal más complejas")
        suggestions.append("Implementar ensemble de múltiples modelos temporales")
        suggestions.append("Aplicar técnicas de regularización específicas para series temporales")
        
        return suggestions
    
    def generate_optimization_report(self, results: Dict) -> str:
        """
        Genera reporte detallado de optimización.
        
        Args:
            results: Resultados de optimización
            
        Returns:
            String con reporte formateado
        """
        if 'error' in results:
            return f"❌ ERROR EN OPTIMIZACIÓN: {results['error']}"
            
        lines = [
            "=" * 80,
            "🎯 REPORTE DE OPTIMIZACIÓN AVANZADA - MODELO PDI",
            "=" * 80,
            f"📅 Fecha: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"🎯 OBJETIVO: MAE < {results.get('target_mae', 3.5)}",
            f"📊 MAE ALCANZADO: {results.get('achieved_mae', 'N/A'):.3f}" if results.get('achieved_mae') else "📊 MAE: No calculado",
            f"📈 R² ALCANZADO: {results.get('achieved_r2', 'N/A'):.3f}" if results.get('achieved_r2') else "📈 R²: No calculado",
            "",
            "🔍 ANÁLISIS DE FEATURES:",
            f"   • Features originales: {results.get('feature_analysis', {}).get('original_features', 'N/A')}",
            f"   • Features seleccionadas: {results.get('feature_analysis', {}).get('selected_features', 'N/A')}",
            f"   • Outliers removidos: {results.get('outliers_removed', 'N/A')}",
            "",
            "⏰ VALIDACIÓN TEMPORAL:",
        ]
        
        temporal_info = results.get('temporal_validation', {})
        if temporal_info:
            lines.extend([
                f"   • Temporadas entrenamiento: {temporal_info.get('train_seasons', 'N/A')}",
                f"   • Temporadas test: {temporal_info.get('test_seasons', 'N/A')}",
                f"   • Samples entrenamiento: {temporal_info.get('train_samples', 'N/A')}",
                f"   • Samples test: {temporal_info.get('test_samples', 'N/A')}",
                f"   • Objetivo alcanzado: {'✅ SÍ' if temporal_info.get('target_achieved') else '❌ NO'}",
            ])
        
        if results.get('improvement_suggestions'):
            lines.extend([
                "",
                "💡 SUGERENCIAS DE MEJORA:",
            ])
            for i, suggestion in enumerate(results.get('improvement_suggestions', []), 1):
                lines.append(f"   {i}. {suggestion}")
                
        lines.extend([
            "",
            "=" * 80,
            "✅ OPTIMIZACIÓN COMPLETADA",
            "=" * 80
        ])
        
        return "\n".join(lines)


def main():
    """Función principal para testing del optimizador."""
    try:
        print("🧪 Testing AdvancedModelOptimizer...")
        
        # Datos sintéticos para prueba
        np.random.seed(42)
        n_samples = 1000
        n_features = 20
        
        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f'feature_{i}' for i in range(n_features)]
        )
        
        # Target con patrón realista
        y = pd.Series(
            X['feature_0'] * 2 + X['feature_1'] * 1.5 + np.random.randn(n_samples) * 0.5 + 50
        )
        
        seasons = pd.Series(
            np.repeat([2020, 2021, 2022, 2023, 2024], n_samples // 5)
        )
        
        # Optimizar
        optimizer = AdvancedModelOptimizer()
        results = optimizer.optimize_for_mae(X, y, seasons, target_mae=1.0)  # Target más fácil para test
        
        # Mostrar reporte
        report = optimizer.generate_optimization_report(results)
        print(report)
        
    except Exception as e:
        print(f"❌ Error en testing: {e}")


if __name__ == "__main__":
    main()
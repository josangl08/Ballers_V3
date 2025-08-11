#!/usr/bin/env python3
"""
Hybrid Sklearn Model - Modelo Híbrido usando solo scikit-learn
Implementación simplificada del modelo híbrido con 4 posiciones principales.

Este módulo implementa la arquitectura híbrida usando solo scikit-learn:
1. Position Mapping: 27 posiciones → 4 grupos (GK, DEF, MID, FWD)
2. Shared Feature Processing: PCA y feature selection común
3. Position-Specific Models: 4 modelos especializados por grupo
4. Hybrid Ensemble: Combinación inteligente de predicciones
5. Interpretabilidad: Feature importance y análisis

Compatible con el entorno actual sin PyTorch/TensorFlow.
Simplificado para usar 4 posiciones en lugar de 27.

Autor: Proyecto Fin de Máster - Python Aplicado al Deporte
Fecha: Agosto 2025
"""

import logging

# Importar mapper de posiciones desde data_processing
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from ml_system.data_processing.processors.position_mapper import (
    map_position,
    position_mapper,
)

# Configurar logging
logger = logging.getLogger(__name__)


class HybridSklearnModel:
    """
    Modelo híbrido usando solo scikit-learn.

    Arquitectura:
    1. Shared Processing: Features universales con PCA/selection
    2. Position Models: Modelos especializados por posición
    3. Hybrid Predictions: Combinación inteligente
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializa modelo híbrido sklearn.

        Args:
            config: Configuración del modelo
        """
        self.config = config or self._get_default_config()

        # Componentes del modelo híbrido
        self.shared_scaler = StandardScaler()
        self.shared_pca = PCA(n_components=0.95)  # 95% varianza
        self.feature_selector = SelectKBest(f_regression, k=20)

        # Modelos por posición
        self.position_models = {}
        self.position_scalers = {}
        self.position_encoder = LabelEncoder()

        # Modelo de ensemble final
        self.ensemble_model = None

        # Metadatos
        self.feature_names = []
        self.position_mapping = {}
        self.is_fitted = False

        logger.info("🔧 HybridSklearnModel inicializado")

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "HybridSklearnModel":
        """
        Entrena el modelo híbrido completo.

        Args:
            X: Features de entrada
            y: Variable objetivo (PDI)

        Returns:
            Self para chaining
        """
        try:
            logger.info(
                f"🔥 Entrenando modelo híbrido: {len(X)} samples, {len(X.columns)} features"
            )

            # Validar entrada
            if "Primary position" not in X.columns:
                raise ValueError(
                    "Columna 'Primary position' requerida para modelo híbrido"
                )

            # Separar posición del resto de features
            positions_specific = X["Primary position"].copy()

            # MAPEAR posiciones específicas a grupos principales (27 → 4)
            positions_grouped = positions_specific.apply(map_position)
            logger.info(
                f"📍 Posiciones mapeadas: {positions_specific.nunique()} específicas → {positions_grouped.nunique()} grupos"
            )

            # Log de distribución
            distribution = positions_grouped.value_counts()
            for group, count in distribution.items():
                logger.info(
                    f"   • {group}: {count} jugadores ({count/len(positions_grouped)*100:.1f}%)"
                )

            X_features = X.drop(["Primary position"], axis=1, errors="ignore")

            # Asegurar que todas las features son numéricas
            numeric_cols = X_features.select_dtypes(include=[np.number]).columns
            X_features = X_features[numeric_cols].copy()

            # Guardar nombres de features
            self.feature_names = list(X_features.columns)

            # PASO 1: Procesamiento compartido (Universal + Zone features)
            logger.info("📊 Paso 1: Procesamiento compartido de features")

            # Escalar features
            X_scaled = self.shared_scaler.fit_transform(X_features)

            # Aplicar PCA para reducir dimensionalidad
            X_pca = self.shared_pca.fit_transform(X_scaled)
            logger.info(f"✅ PCA: {X_features.shape[1]} → {X_pca.shape[1]} features")

            # Seleccionar top features
            X_selected = self.feature_selector.fit_transform(X_scaled, y)
            logger.info(
                f"✅ Feature Selection: {X_scaled.shape[1]} → {X_selected.shape[1]} features"
            )

            # PASO 2: Entrenar modelos específicos por posición (4 grupos)
            logger.info("⚽ Paso 2: Entrenando modelos por grupo de posición")

            unique_positions = positions_grouped.unique()
            self.position_encoder.fit(positions_grouped)

            for position in unique_positions:
                position_mask = positions_grouped == position
                position_samples = np.sum(position_mask)

                if position_samples < 5:  # Mínimo samples para entrenar
                    logger.warning(
                        f"⚠️ {position}: Solo {position_samples} muestras, omitiendo"
                    )
                    continue

                # Datos de la posición
                X_pos = X_selected[position_mask]
                y_pos = y[position_mask]

                # Scaler específico por posición
                pos_scaler = StandardScaler()
                X_pos_scaled = pos_scaler.fit_transform(X_pos)

                # Modelo específico por posición
                pos_model = self._create_position_model(position)
                pos_model.fit(X_pos_scaled, y_pos)

                # Guardar componentes
                self.position_models[position] = pos_model
                self.position_scalers[position] = pos_scaler

                logger.info(f"✅ {position}: {position_samples} muestras entrenadas")

            # PASO 3: Modelo ensemble para combinación
            logger.info("🎯 Paso 3: Creando modelo ensemble")

            # Generar features para ensemble (predicciones de componentes)
            ensemble_features = self._create_ensemble_features(
                X_features, positions_grouped, y
            )

            # Entrenar ensemble final
            self.ensemble_model = GradientBoostingRegressor(
                n_estimators=100, max_depth=6, random_state=42
            )
            self.ensemble_model.fit(ensemble_features, y)

            # Guardar metadatos
            self.position_mapping = dict(
                zip(unique_positions, range(len(unique_positions)))
            )
            self.is_fitted = True

            logger.info("✅ Modelo híbrido entrenado exitosamente")

            return self

        except Exception as e:
            logger.error(f"Error entrenando modelo híbrido: {e}")
            raise

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Realiza predicciones con el modelo híbrido.

        Args:
            X: Features de entrada

        Returns:
            Array de predicciones
        """
        try:
            if not self.is_fitted:
                raise ValueError("Modelo no entrenado. Llama fit() primero.")

            # Separar posición y mapear a grupos
            positions_specific = X["Primary position"].copy()
            positions_grouped = positions_specific.apply(map_position)
            X_features = X.drop(["Primary position"], axis=1, errors="ignore")

            # Asegurar que todas las features son numéricas
            numeric_cols = X_features.select_dtypes(include=[np.number]).columns
            X_features = X_features[numeric_cols].copy()

            # Generar features para ensemble
            ensemble_features = self._create_ensemble_features(
                X_features, positions_grouped
            )

            # Predicción del ensemble
            predictions = self.ensemble_model.predict(ensemble_features)

            return predictions

        except Exception as e:
            logger.error(f"Error en predicción: {e}")
            raise

    def get_feature_importance(self) -> Dict[str, float]:
        """
        Obtiene importancia de features del modelo híbrido.

        Returns:
            Dict con importancia de features
        """
        try:
            if not self.is_fitted:
                return {}

            # Importancia del modelo ensemble
            ensemble_importance = dict(
                zip(
                    [f"component_{i}" for i in range(len(self.position_models) + 2)],
                    self.ensemble_model.feature_importances_,
                )
            )

            # Importancia de features seleccionadas
            selected_features = self.feature_selector.get_support(indices=True)
            feature_scores = self.feature_selector.scores_[selected_features]

            feature_importance = {}
            for i, feature_idx in enumerate(selected_features):
                if feature_idx < len(self.feature_names):
                    feature_name = self.feature_names[feature_idx]
                    feature_importance[feature_name] = float(feature_scores[i])

            # Combinar importancias
            combined_importance = {**feature_importance, **ensemble_importance}

            return combined_importance

        except Exception as e:
            logger.error(f"Error obteniendo feature importance: {e}")
            return {}

    def _get_default_config(self) -> Dict:
        """Configuración por defecto del modelo."""
        return {
            "shared_features_ratio": 0.95,  # Ratio de varianza PCA
            "selected_features_k": 20,  # Top K features
            "position_model_type": "rf",  # random_forest, gradient_boost, ridge
            "ensemble_model": "gb",  # gradient_boost, rf
            "random_state": 42,
        }

    def _create_position_model(self, position: str):
        """Crea modelo específico para una posición."""
        model_type = self.config.get("position_model_type", "rf")
        random_state = self.config.get("random_state", 42)

        if model_type == "rf":
            return RandomForestRegressor(
                n_estimators=100, max_depth=8, random_state=random_state
            )
        elif model_type == "gb":
            return GradientBoostingRegressor(
                n_estimators=100, max_depth=6, random_state=random_state
            )
        elif model_type == "ridge":
            return Ridge(alpha=1.0, random_state=random_state)
        else:
            # Default
            return RandomForestRegressor(n_estimators=50, random_state=random_state)

    def _create_ensemble_features(
        self, X_features: pd.DataFrame, positions: pd.Series, y: pd.Series = None
    ) -> np.ndarray:
        """
        Crea features para el modelo ensemble combinando predicciones.

        Args:
            X_features: Features numéricas
            positions: Posiciones de jugadores
            y: Target (solo durante entrenamiento)

        Returns:
            Array de features para ensemble
        """
        try:
            # Asegurar que X_features es numérico
            if X_features is not None:
                numeric_cols = X_features.select_dtypes(include=[np.number]).columns
                X_features = X_features[numeric_cols].copy()

            # Procesar features compartidos
            X_scaled = self.shared_scaler.transform(X_features)
            X_pca = self.shared_pca.transform(X_scaled)
            X_selected = self.feature_selector.transform(X_scaled)

            ensemble_features = []

            # Feature 1: Predicción PCA (features universales)
            if hasattr(self, "_universal_model"):
                pca_pred = self._universal_model.predict(X_pca)
            else:
                # Durante entrenamiento, crear modelo universal
                if y is not None:
                    self._universal_model = RandomForestRegressor(
                        n_estimators=50, random_state=42
                    )
                    self._universal_model.fit(X_pca, y)
                    pca_pred = self._universal_model.predict(X_pca)
                else:
                    pca_pred = np.zeros(len(X_features))

            ensemble_features.append(pca_pred)

            # Feature 2: Predicción features seleccionadas
            if hasattr(self, "_selected_model"):
                selected_pred = self._selected_model.predict(X_selected)
            else:
                if y is not None:
                    self._selected_model = RandomForestRegressor(
                        n_estimators=50, random_state=42
                    )
                    self._selected_model.fit(X_selected, y)
                    selected_pred = self._selected_model.predict(X_selected)
                else:
                    selected_pred = np.zeros(len(X_features))

            ensemble_features.append(selected_pred)

            # Features 3+: Predicciones por posición
            for position, model in self.position_models.items():
                position_pred = np.zeros(len(X_features))
                position_mask = positions == position

                if np.any(position_mask):
                    X_pos = X_selected[position_mask]
                    X_pos_scaled = self.position_scalers[position].transform(X_pos)
                    position_pred[position_mask] = model.predict(X_pos_scaled)

                ensemble_features.append(position_pred)

            # Convertir a array 2D
            return np.column_stack(ensemble_features)

        except Exception as e:
            logger.error(f"Error creando ensemble features: {e}")
            raise

    def get_model_summary(self) -> Dict[str, Any]:
        """
        Obtiene resumen del modelo entrenado.

        Returns:
            Dict con información del modelo
        """
        if not self.is_fitted:
            return {"error": "Modelo no entrenado"}

        return {
            "model_type": "HybridSklearnModel",
            "total_features": len(self.feature_names),
            "pca_components": self.shared_pca.n_components_,
            "selected_features": self.feature_selector.k,
            "position_models": len(self.position_models),
            "positions": list(self.position_models.keys()),
            "config": self.config,
            "is_fitted": self.is_fitted,
        }


def create_hybrid_sklearn_pipeline(config: Optional[Dict] = None) -> HybridSklearnModel:
    """
    Crea pipeline de modelo híbrido sklearn.

    Args:
        config: Configuración del modelo

    Returns:
        Modelo híbrido configurado
    """
    return HybridSklearnModel(config)


def evaluate_hybrid_model(
    model: HybridSklearnModel, X_test: pd.DataFrame, y_test: pd.Series
) -> Dict[str, float]:
    """
    Evalúa modelo híbrido con métricas estándar.

    Args:
        model: Modelo entrenado
        X_test: Features de test
        y_test: Target de test

    Returns:
        Dict con métricas de evaluación
    """
    try:
        # Predicciones
        y_pred = model.predict(X_test)

        # Calcular métricas
        metrics = {
            "mae": mean_absolute_error(y_test, y_pred),
            "rmse": np.sqrt(mean_squared_error(y_test, y_pred)),
            "r2": r2_score(y_test, y_pred),
            "samples": len(y_test),
        }

        # MAPE (con manejo de zeros)
        try:
            mape = np.mean(np.abs((y_test - y_pred) / np.maximum(y_test, 1e-8))) * 100
            metrics["mape"] = mape
        except:
            metrics["mape"] = 0.0

        return metrics

    except Exception as e:
        logger.error(f"Error evaluando modelo: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    # Test básico del modelo híbrido
    print("🧪 Test HybridSklearnModel...")

    # Datos sintéticos para test
    np.random.seed(42)
    n_samples = 500
    n_features = 30

    # Features aleatorias
    X_test = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f"feature_{i}" for i in range(n_features)],
    )

    # Posiciones
    positions = np.random.choice(["CB", "FB", "CMF", "AMF", "CF"], n_samples)
    X_test["Primary position"] = positions

    # Target sintético
    y_test = np.random.randn(n_samples) * 10 + 50

    # Entrenar modelo
    model = create_hybrid_sklearn_pipeline()
    model.fit(X_test, y_test)

    # Evaluar
    X_train, X_val, y_train, y_val = train_test_split(
        X_test, y_test, test_size=0.3, random_state=42
    )
    metrics = evaluate_hybrid_model(model, X_val, y_val)

    print(f"✅ Test completado:")
    print(f"   • MAE: {metrics.get('mae', 0):.3f}")
    print(f"   • R²: {metrics.get('r2', 0):.3f}")
    print(f"   • Muestras: {metrics.get('samples', 0)}")

    # Feature importance
    importance = model.get_feature_importance()
    print(f"   • Features importantes: {len(importance)}")

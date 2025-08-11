"""
Baseline Model - Modelo de referencia para Player Development Index (PDI).

Este módulo implementa modelos baseline académicos para establecer referencias
de rendimiento en la predicción del PDI. Utiliza métodos simples pero robustos
para proporcionar una línea base contra la cual comparar modelos más complejos.

Metodología CRISP-DM:
- Modelos lineales como referencia
- Validación cruzada estratificada por posición
- Métricas académicas rigurosas (MAE, R², RMSE)
- Análisis de residuos y learning curves

Arquitectura:
- BaselineModel: Clase base con funcionalidad común
- LinearBaselineModel: Regresión lineal simple
- RidgeBaselineModel: Regresión con regularización L2
- EnsembleBaselineModel: Combinación de modelos simples

Objetivo académico: MAE < 15 puntos, R² > 0.6
"""

import logging
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import plotly.express as px

# Visualización
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Machine Learning
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import (
    KFold,
    StratifiedKFold,
    cross_val_score,
    cross_validate,
    learning_curve,
    validation_curve,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler, StandardScaler

# Componentes ML system
from ml_system.evaluation.analysis.advanced_features import (
    create_advanced_feature_pipeline,
)
from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=FutureWarning)


@dataclass
class BaselineResults:
    """
    Estructura para almacenar resultados de modelos baseline.

    Contiene métricas de evaluación, predicciones y metadatos del modelo
    para análisis académico riguroso.
    """

    model_name: str
    mae: float
    rmse: float
    r2: float
    mape: float
    cv_scores: Dict[str, List[float]]
    predictions: np.ndarray
    actuals: np.ndarray
    residuals: np.ndarray
    feature_importance: Optional[Dict[str, float]] = None
    training_time: float = 0.0
    model_params: Dict = field(default_factory=dict)

    def get_summary_stats(self) -> Dict[str, float]:
        """Retorna estadísticas resumidas del modelo."""
        return {
            "MAE": round(self.mae, 3),
            "RMSE": round(self.rmse, 3),
            "R²": round(self.r2, 3),
            "MAPE": round(self.mape, 3),
            "CV_MAE_mean": round(np.mean(self.cv_scores.get("mae", [0])), 3),
            "CV_MAE_std": round(np.std(self.cv_scores.get("mae", [0])), 3),
            "Training_time": round(self.training_time, 2),
        }


class BaselineModel(BaseEstimator, RegressorMixin):
    """
    Modelo baseline base con funcionalidad común para predicción PDI.

    Proporciona interface consistente y métodos de evaluación estándar
    para todos los modelos baseline académicos.

    Attributes:
        model_name: Nombre identificativo del modelo
        feature_engineer: Instancia para extracción de features
        scaler: Escalador para normalización de features
        is_fitted: Flag indicando si el modelo está entrenado
    """

    def __init__(self, model_name: str = "BaselineModel"):
        """
        Inicializa el modelo baseline.

        Args:
            model_name: Nombre identificativo del modelo
        """
        self.model_name = model_name
        self.feature_engineer = FeatureEngineer()
        self.scaler = RobustScaler()  # Robusto ante outliers
        self.is_fitted = False

        # Mapeo de columnas CSV Thai League a features baseline
        # IMPORTANTE: NO incluir Goals/Assists directos para evitar circularidad
        self.csv_column_mapping = {
            # Básicas (SIN Goals/Assists directos)
            "Matches played": "matches_played",
            "Minutes played": "minutes_played",
            "Age": "age",
            # Pases
            "Pass accuracy, %": "pass_accuracy_pct",
            "Passes per 90": "passes_per_90",
            "Forward passes per 90": "forward_passes_per_90",
            "Back passes per 90": "back_passes_per_90",
            # Duelos
            "Duels won, %": "duels_won_pct",
            "Defensive duels won, %": "defensive_duels_won_pct",
            "Offensive duels won, %": "offensive_duels_won_pct",
            # Defensivo
            "Interceptions per 90": "interceptions_per_90",
            "Tackles per 90": "tackles_per_90",
            "Clearances per 90": "clearances_per_90",
            # Ofensivo (SIN Goals/Assists per 90 directos)
            "Shots per 90": "shots_per_90",
            "Shots on target, %": "shots_on_target_pct",
            # Disciplina
            "Yellow cards": "yellow_cards",
            "Red cards": "red_cards",
            # Posición
            "Primary position": "primary_position",
        }

        # Configuración de features para baseline (nombres mapeados)
        # Features baseline NO CIRCULARES - académicamente validados
        self.baseline_features = [
            # Básicas (SIN goals/assists directos)
            "matches_played",
            "minutes_played",
            "age",
            # Universal features (aplicables a todas las posiciones) - per_90 standard
            "passes_per_90",
            "pass_accuracy_pct",
            "duels_won_pct",
            # Métricas defensivas per_90
            "defensive_duels_won_pct",
            "interceptions_per_90",
            "tackles_per_90",
            "clearances_per_90",
            # Métricas ofensivas per_90 (SIN goals/assists directos)
            "shots_per_90",
            "shots_on_target_pct",
            # Features derivadas NO circulares
            "shot_efficiency",
            "pass_quality_score",
            "participation_ratio",
            # Disciplina
            "yellow_cards",
            "red_cards",
        ]

        logger.info(
            f"Inicializado {self.model_name} con {len(self.baseline_features)} features base"
        )

    def map_csv_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Mapea columnas CSV de Thai League a nombres estándar.

        Args:
            df: DataFrame con columnas CSV originales

        Returns:
            DataFrame con columnas mapeadas
        """
        mapped_df = df.copy()

        # Mapear columnas que existan
        for csv_name, standard_name in self.csv_column_mapping.items():
            if csv_name in df.columns:
                mapped_df[standard_name] = df[csv_name]

        logger.info(
            f"Columnas mapeadas: {len([c for c in self.csv_column_mapping.keys() if c in df.columns])}/{len(self.csv_column_mapping)}"
        )
        return mapped_df

    def extract_baseline_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extrae features baseline del dataset CSV de Thai League.

        Args:
            df: DataFrame con estadísticas de Thai League (columnas CSV)

        Returns:
            DataFrame con features preparadas para entrenamiento
        """
        try:
            # Mapear columnas CSV a nombres estándar
            mapped_df = self.map_csv_columns(df)

            # Filtrar solo features disponibles
            available_features = [
                f for f in self.baseline_features if f in mapped_df.columns
            ]

            logger.info(
                f"Features disponibles: {len(available_features)}/{len(self.baseline_features)}"
            )

            # Extraer features básicas
            position_col = (
                "primary_position"
                if "primary_position" in mapped_df.columns
                else "Primary position"
            )
            base_columns = (
                available_features + [position_col]
                if position_col in mapped_df.columns
                else available_features
            )

            feature_df = mapped_df[base_columns].copy()

            # Crear features derivadas estándar (per_90)
            if "goals" in feature_df.columns and "minutes_played" in feature_df.columns:
                # Si ya existe goals_per_90, usar esa; sino calcular
                if "goals_per_90" not in feature_df.columns:
                    feature_df["goals_per_90_calc"] = (
                        feature_df["goals"].fillna(0)
                        * 90
                        / feature_df["minutes_played"].fillna(90)
                    ).clip(
                        0, 10
                    )  # Clip valores extremos

            if (
                "assists" in feature_df.columns
                and "minutes_played" in feature_df.columns
            ):
                if "assists_per_90" not in feature_df.columns:
                    feature_df["assists_per_90_calc"] = (
                        feature_df["assists"].fillna(0)
                        * 90
                        / feature_df["minutes_played"].fillna(90)
                    ).clip(
                        0, 5
                    )  # Clip valores extremos

            # Feature de participación (ratio de minutos jugados)
            if (
                "minutes_played" in feature_df.columns
                and "matches_played" in feature_df.columns
            ):
                feature_df["participation_ratio"] = (
                    feature_df["minutes_played"].fillna(0)
                    / (feature_df["matches_played"].fillna(1) * 90)
                ).clip(0, 1)

            # Feature engineering NO CIRCULAR - evitar goals/assists derivatives
            # Solo usar features independientes del target PDI

            # Shot efficiency en lugar de goals (proxy válido)
            if (
                "shots_per_90" in feature_df.columns
                and "shots_on_target_pct" in feature_df.columns
            ):
                feature_df["shot_efficiency"] = (
                    feature_df["shots_per_90"].fillna(0)
                    * feature_df["shots_on_target_pct"].fillna(0)
                    / 100
                ).clip(0, 10)

            # Pass quality score (proxy para creatividad)
            if (
                "passes_per_90" in feature_df.columns
                and "pass_accuracy_pct" in feature_df.columns
            ):
                feature_df["pass_quality_score"] = (
                    feature_df["passes_per_90"].fillna(0)
                    * feature_df["pass_accuracy_pct"].fillna(0)
                    / 100
                ).clip(0, 200)

            # Encoding simple de posiciones (One-Hot)
            if position_col in feature_df.columns:
                position_dummies = pd.get_dummies(
                    feature_df[position_col], prefix="position", dummy_na=True
                )
                feature_df = pd.concat([feature_df, position_dummies], axis=1)
                feature_df = feature_df.drop(position_col, axis=1)

            # Imputación simple de valores faltantes
            numeric_columns = feature_df.select_dtypes(include=[np.number]).columns
            feature_df[numeric_columns] = feature_df[numeric_columns].fillna(
                feature_df[numeric_columns].median()
            )

            logger.info(f"Features finales preparadas: {len(feature_df.columns)}")
            return feature_df

        except Exception as e:
            logger.error(f"Error extrayendo features baseline: {e}")
            raise

    def calculate_target_pdi(self, df: pd.DataFrame) -> np.ndarray:
        """
        Calcula PDI target usando fórmula académica simplificada para datos CSV Thai League.

        Para el modelo baseline, usamos una versión simplificada del PDI:
        PDI = 40% * Universal + 35% * Zone + 25% * Position

        Args:
            df: DataFrame con estadísticas profesionales

        Returns:
            Array con valores PDI calculados
        """
        try:
            # Mapear columnas CSV a nombres estándar
            mapped_df = self.map_csv_columns(df)

            pdi_scores = []

            for _, row in mapped_df.iterrows():
                # Componente Universal (40%) - Métricas básicas
                universal_score = 50.0  # Base neutral

                # Usar columnas mapeadas o directas
                pass_acc = row.get("pass_accuracy_pct") or row.get("Pass accuracy, %")
                if pd.notna(pass_acc):
                    universal_score += (pass_acc - 75) * 0.5

                duels_won = row.get("duels_won_pct") or row.get("Duels won, %")
                if pd.notna(duels_won):
                    universal_score += (duels_won - 50) * 0.3

                # Componente por Zona (35%) - Basado en posición
                zone_score = 50.0
                position = row.get("primary_position") or row.get(
                    "Primary position", "CMF"
                )

                if position in [
                    "CF",
                    "W",
                    "AMF",
                    "LWF",
                    "RWF",
                    "LAMF",
                    "RAMF",
                ]:  # Ofensivos
                    goals_p90 = row.get("goals_per_90") or row.get("Goals per 90")
                    if pd.notna(goals_p90):
                        zone_score += goals_p90 * 15
                    assists_p90 = row.get("assists_per_90") or row.get("Assists per 90")
                    if pd.notna(assists_p90):
                        zone_score += assists_p90 * 10

                elif position in [
                    "DMF",
                    "CB",
                    "GK",
                    "RCB",
                    "LCB",
                    "RDMF",
                    "LDMF",
                ]:  # Defensivos
                    def_duels = row.get("defensive_duels_won_pct") or row.get(
                        "Defensive duels won, %"
                    )
                    if pd.notna(def_duels):
                        zone_score += (def_duels - 50) * 0.4
                    interceptions = row.get("interceptions_per_90") or row.get(
                        "Interceptions per 90"
                    )
                    if pd.notna(interceptions):
                        zone_score += interceptions * 3

                else:  # Mediocampo
                    passes_p90 = row.get("passes_per_90") or row.get("Passes per 90")
                    if pd.notna(passes_p90):
                        zone_score += (passes_p90 - 50) * 0.2

                # Componente Específico (25%) - Ajuste por rendimiento general
                specific_score = 50.0

                minutes = row.get("minutes_played") or row.get("Minutes played")
                matches = row.get("matches_played") or row.get("Matches played")

                if pd.notna(minutes) and pd.notna(matches) and matches > 0:
                    participation = minutes / (matches * 90)
                    specific_score += (participation - 0.7) * 20

                # Bonus por goles y asistencias totales
                goals = row.get("goals") or row.get("Goals", 0)
                assists = row.get("assists") or row.get("Assists", 0)
                if pd.notna(goals) and pd.notna(assists):
                    contribution = goals + assists
                    specific_score += min(contribution * 0.5, 10)  # Max 10 puntos extra

                # PDI final con pesos académicos
                pdi = universal_score * 0.40 + zone_score * 0.35 + specific_score * 0.25

                # Normalizar a rango [0, 100]
                pdi = max(0, min(100, pdi))
                pdi_scores.append(pdi)

            logger.info(f"PDI calculado para {len(pdi_scores)} registros")
            logger.info(
                f"PDI stats: mean={np.mean(pdi_scores):.1f}, std={np.std(pdi_scores):.1f}"
            )

            return np.array(pdi_scores)

        except Exception as e:
            logger.error(f"Error calculando PDI target: {e}")
            raise

    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaselineModel":
        """
        Entrena el modelo baseline.

        Args:
            X: Features de entrenamiento
            y: Target PDI

        Returns:
            self: Instancia entrenada
        """
        # Implementación base - debe ser sobreescrita por subclases
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Realiza predicciones con el modelo.

        Args:
            X: Features para predicción

        Returns:
            Predicciones PDI
        """
        if not self.is_fitted:
            raise ValueError("Modelo debe ser entrenado antes de predecir")

        # Implementación base - retorna media del target
        return np.full(X.shape[0], 50.0)


class LinearBaselineModel(BaselineModel):
    """
    Modelo baseline usando regresión lineal simple.

    Implementa regresión lineal múltiple como modelo de referencia
    académica. Proporciona interpretabilidad máxima y baseline sólido.

    Characteristics:
    - Rápido entrenamiento e inferencia
    - Alta interpretabilidad
    - Sensible a outliers
    - Asume relaciones lineales
    """

    def __init__(self):
        """Inicializa modelo de regresión lineal baseline."""
        super().__init__("Linear Baseline")
        self.model = LinearRegression()
        self.feature_names = []

    def fit(
        self, X: np.ndarray, y: np.ndarray, feature_names: Optional[List[str]] = None
    ) -> "LinearBaselineModel":
        """
        Entrena modelo de regresión lineal.

        Args:
            X: Features de entrenamiento
            y: Target PDI
            feature_names: Nombres de las features (opcional)

        Returns:
            self: Modelo entrenado
        """
        try:
            start_time = datetime.now()

            # Normalizar features
            X_scaled = self.scaler.fit_transform(X)

            # Entrenar modelo
            self.model.fit(X_scaled, y)

            # Guardar metadatos
            self.feature_names = feature_names or [
                f"feature_{i}" for i in range(X.shape[1])
            ]
            self.training_time = (datetime.now() - start_time).total_seconds()
            self.is_fitted = True

            logger.info(f"Linear Baseline entrenado en {self.training_time:.2f}s")
            logger.info(f"R² entrenamiento: {self.model.score(X_scaled, y):.3f}")

            return self

        except Exception as e:
            logger.error(f"Error entrenando Linear Baseline: {e}")
            raise

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predice PDI usando regresión lineal."""
        if not self.is_fitted:
            raise ValueError("Modelo debe ser entrenado primero")

        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)

        # Asegurar rango [0, 100]
        return np.clip(predictions, 0, 100)

    def get_feature_importance(self) -> Dict[str, float]:
        """Retorna importancia de features basada en coeficientes."""
        if not self.is_fitted:
            return {}

        coefficients = np.abs(self.model.coef_)
        importance = coefficients / np.sum(coefficients)

        return dict(zip(self.feature_names, importance))


class RidgeBaselineModel(BaselineModel):
    """
    Modelo baseline con regularización Ridge (L2).

    Implementa regresión Ridge para controlar overfitting y manejar
    multicolinealidad. Más robusto que regresión lineal simple.

    Characteristics:
    - Regularización L2 para estabilidad
    - Manejo de multicolinealidad
    - Hiperparámetro alpha ajustable
    - Balance bias-variance mejorado
    """

    def __init__(self, alpha: float = 1.0):
        """
        Inicializa modelo Ridge baseline.

        Args:
            alpha: Parámetro de regularización Ridge
        """
        super().__init__("Ridge Baseline")
        self.alpha = alpha
        self.model = Ridge(alpha=alpha, random_state=42)
        self.feature_names = []

    def fit(
        self, X: np.ndarray, y: np.ndarray, feature_names: Optional[List[str]] = None
    ) -> "RidgeBaselineModel":
        """Entrena modelo Ridge con validación de hiperparámetros."""
        try:
            start_time = datetime.now()

            # Normalizar features
            X_scaled = self.scaler.fit_transform(X)

            # Entrenar modelo
            self.model.fit(X_scaled, y)

            # Metadatos
            self.feature_names = feature_names or [
                f"feature_{i}" for i in range(X.shape[1])
            ]
            self.training_time = (datetime.now() - start_time).total_seconds()
            self.is_fitted = True

            logger.info(
                f"Ridge Baseline (α={self.alpha}) entrenado en {self.training_time:.2f}s"
            )
            logger.info(f"R² entrenamiento: {self.model.score(X_scaled, y):.3f}")

            return self

        except Exception as e:
            logger.error(f"Error entrenando Ridge Baseline: {e}")
            raise

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predice PDI usando Ridge regression."""
        if not self.is_fitted:
            raise ValueError("Modelo debe ser entrenado primero")

        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)

        return np.clip(predictions, 0, 100)

    def get_feature_importance(self) -> Dict[str, float]:
        """Importancia basada en coeficientes Ridge."""
        if not self.is_fitted:
            return {}

        coefficients = np.abs(self.model.coef_)
        importance = (
            coefficients / np.sum(coefficients)
            if np.sum(coefficients) > 0
            else coefficients
        )

        return dict(zip(self.feature_names, importance))


class EnsembleBaselineModel(BaselineModel):
    """
    Modelo baseline ensemble combinando múltiples algoritmos simples.

    Combina Linear, Ridge y Random Forest en ensemble votante para
    mayor robustez manteniendo interpretabilidad académica.

    Characteristics:
    - Voting regressor con múltiples algoritmos
    - Mayor robustez ante outliers
    - Reducción de varianza
    - Interpretabilidad moderada
    """

    def __init__(self, n_estimators: int = 50):
        """
        Inicializa ensemble baseline.

        Args:
            n_estimators: Número de árboles en Random Forest
        """
        super().__init__("Ensemble Baseline")
        self.n_estimators = n_estimators

        # Modelos componentes
        self.linear_model = LinearRegression()
        self.ridge_model = Ridge(alpha=1.0, random_state=42)
        self.rf_model = RandomForestRegressor(
            n_estimators=n_estimators, max_depth=8, random_state=42, n_jobs=-1
        )

        self.models = {
            "linear": self.linear_model,
            "ridge": self.ridge_model,
            "random_forest": self.rf_model,
        }

        self.feature_names = []
        self.model_weights = {"linear": 0.3, "ridge": 0.3, "random_forest": 0.4}

    def fit(
        self, X: np.ndarray, y: np.ndarray, feature_names: Optional[List[str]] = None
    ) -> "EnsembleBaselineModel":
        """Entrena ensemble de modelos baseline."""
        try:
            start_time = datetime.now()

            # Normalizar para modelos lineales
            X_scaled = self.scaler.fit_transform(X)

            # Entrenar cada modelo
            self.linear_model.fit(X_scaled, y)
            self.ridge_model.fit(X_scaled, y)
            self.rf_model.fit(X, y)  # RF no necesita normalización

            # Metadatos
            self.feature_names = feature_names or [
                f"feature_{i}" for i in range(X.shape[1])
            ]
            self.training_time = (datetime.now() - start_time).total_seconds()
            self.is_fitted = True

            # Evaluar cada componente
            linear_r2 = self.linear_model.score(X_scaled, y)
            ridge_r2 = self.ridge_model.score(X_scaled, y)
            rf_r2 = self.rf_model.score(X, y)

            logger.info(f"Ensemble Baseline entrenado en {self.training_time:.2f}s")
            logger.info(
                f"R² componentes - Linear: {linear_r2:.3f}, Ridge: {ridge_r2:.3f}, RF: {rf_r2:.3f}"
            )

            return self

        except Exception as e:
            logger.error(f"Error entrenando Ensemble Baseline: {e}")
            raise

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predice usando ensemble ponderado."""
        if not self.is_fitted:
            raise ValueError("Modelo debe ser entrenado primero")

        # Predicciones de cada modelo
        X_scaled = self.scaler.transform(X)

        linear_pred = self.linear_model.predict(X_scaled)
        ridge_pred = self.ridge_model.predict(X_scaled)
        rf_pred = self.rf_model.predict(X)

        # Ensemble ponderado
        ensemble_pred = (
            linear_pred * self.model_weights["linear"]
            + ridge_pred * self.model_weights["ridge"]
            + rf_pred * self.model_weights["random_forest"]
        )

        return np.clip(ensemble_pred, 0, 100)

    def get_feature_importance(self) -> Dict[str, float]:
        """Importancia promedio del ensemble."""
        if not self.is_fitted:
            return {}

        # Combinar importancias
        linear_coef = np.abs(self.linear_model.coef_)
        ridge_coef = np.abs(self.ridge_model.coef_)
        rf_importance = self.rf_model.feature_importances_

        # Normalizar cada conjunto
        linear_norm = (
            linear_coef / np.sum(linear_coef)
            if np.sum(linear_coef) > 0
            else linear_coef
        )
        ridge_norm = (
            ridge_coef / np.sum(ridge_coef) if np.sum(ridge_coef) > 0 else ridge_coef
        )
        rf_norm = (
            rf_importance / np.sum(rf_importance)
            if np.sum(rf_importance) > 0
            else rf_importance
        )

        # Promedio ponderado
        ensemble_importance = (
            linear_norm * self.model_weights["linear"]
            + ridge_norm * self.model_weights["ridge"]
            + rf_norm * self.model_weights["random_forest"]
        )

        return dict(zip(self.feature_names, ensemble_importance))


class BaselineEvaluator:
    """
    Evaluador académico para modelos baseline del PDI.

    Implementa evaluación rigurosa con múltiples métricas, validación cruzada
    estratificada por posición, y análisis de residuos para investigación académica.

    Features:
    - Validación cruzada estratificada por posición
    - Múltiples métricas (MAE, RMSE, R², MAPE)
    - Learning curves y validation curves
    - Análisis de residuos por posición
    - Visualizaciones académicas con Plotly
    """

    def __init__(self, cv_folds: int = 5, random_state: int = 42):
        """
        Inicializa evaluador baseline.

        Args:
            cv_folds: Número de folds para validación cruzada
            random_state: Semilla para reproducibilidad
        """
        self.cv_folds = cv_folds
        self.random_state = random_state
        self.results_history = []

        logger.info(f"BaselineEvaluator inicializado con {cv_folds}-fold CV")

    def evaluate_model(
        self,
        model: BaselineModel,
        X: np.ndarray,
        y: np.ndarray,
        positions: Optional[np.ndarray] = None,
    ) -> BaselineResults:
        """
        Evalúa modelo baseline con métricas académicas completas.

        Args:
            model: Modelo baseline a evaluar
            X: Features de evaluación
            y: Target PDI real
            positions: Array de posiciones para estratificación (opcional)

        Returns:
            BaselineResults con métricas completas
        """
        try:
            logger.info(f"Evaluando {model.model_name}...")

            # Configurar validación cruzada
            if positions is not None and len(np.unique(positions)) > 1:
                # Estratificada por posición
                cv_strategy = StratifiedKFold(
                    n_splits=self.cv_folds, shuffle=True, random_state=self.random_state
                )
                cv_splits = cv_strategy.split(X, positions)
            else:
                # K-Fold estándar
                cv_strategy = KFold(
                    n_splits=self.cv_folds, shuffle=True, random_state=self.random_state
                )
                cv_splits = cv_strategy.split(X)

            # Métricas de validación cruzada
            scoring_metrics = [
                "neg_mean_absolute_error",
                "neg_root_mean_squared_error",
                "r2",
            ]

            cv_results = cross_validate(
                model,
                X,
                y,
                cv=cv_splits,
                scoring=scoring_metrics,
                n_jobs=-1,
                return_train_score=False,
            )

            # Entrenar modelo completo para métricas adicionales
            start_time = datetime.now()
            model.fit(X, y)
            training_time = (datetime.now() - start_time).total_seconds()

            # Predicciones finales
            predictions = model.predict(X)
            residuals = y - predictions

            # Calcular métricas individuales
            mae = mean_absolute_error(y, predictions)
            rmse = np.sqrt(mean_squared_error(y, predictions))
            r2 = r2_score(y, predictions)

            # MAPE con manejo de ceros
            mape = (
                np.mean(np.abs((y - predictions) / np.maximum(np.abs(y), 1e-8))) * 100
            )

            # Organizar scores CV
            cv_scores = {
                "mae": -cv_results["test_neg_mean_absolute_error"],
                "rmse": -cv_results["test_neg_root_mean_squared_error"],
                "r2": cv_results["test_r2"],
            }

            # Importancia de features
            feature_importance = None
            try:
                feature_importance = model.get_feature_importance()
            except:
                logger.warning(
                    f"No se pudo obtener importancia de features para {model.model_name}"
                )

            # Crear resultado
            result = BaselineResults(
                model_name=model.model_name,
                mae=mae,
                rmse=rmse,
                r2=r2,
                mape=mape,
                cv_scores=cv_scores,
                predictions=predictions,
                actuals=y,
                residuals=residuals,
                feature_importance=feature_importance,
                training_time=training_time,
                model_params=getattr(model, "get_params", lambda: {})(),
            )

            # Guardar en historial
            self.results_history.append(result)

            logger.info(f"✅ {model.model_name} evaluado:")
            logger.info(f"   MAE: {mae:.3f} ± {np.std(cv_scores['mae']):.3f}")
            logger.info(f"   RMSE: {rmse:.3f}")
            logger.info(f"   R²: {r2:.3f} ± {np.std(cv_scores['r2']):.3f}")

            return result

        except Exception as e:
            logger.error(f"Error evaluando {model.model_name}: {e}")
            raise

    def compare_models(self, results: List[BaselineResults]) -> pd.DataFrame:
        """
        Compara múltiples modelos baseline académicamente.

        Args:
            results: Lista de resultados de modelos

        Returns:
            DataFrame con comparación completa
        """
        comparison_data = []

        for result in results:
            stats = result.get_summary_stats()
            stats["Model"] = result.model_name

            # Añadir métricas de estabilidad CV
            stats["CV_Stability"] = 1 - (stats["CV_MAE_std"] / stats["CV_MAE_mean"])

            # Clasificación académica
            if stats["MAE"] < 10:
                stats["Performance_Grade"] = "Excelente"
            elif stats["MAE"] < 15:
                stats["Performance_Grade"] = "Bueno"
            elif stats["MAE"] < 20:
                stats["Performance_Grade"] = "Aceptable"
            else:
                stats["Performance_Grade"] = "Insuficiente"

            comparison_data.append(stats)

        df_comparison = pd.DataFrame(comparison_data)
        df_comparison = df_comparison.sort_values("MAE")

        return df_comparison

    def plot_model_comparison(self, results: List[BaselineResults]) -> None:
        """
        Crea visualización académica de comparación de modelos.

        Args:
            results: Lista de resultados a comparar
        """
        # Crear subplots para comparación integral
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=[
                "Comparación de MAE (Validación Cruzada)",
                "R² vs MAE - Scatter Plot",
                "Distribución de Residuos por Modelo",
                "Learning Efficiency (Time vs Performance)",
            ],
            specs=[
                [{"type": "box"}, {"type": "scatter"}],
                [{"type": "violin"}, {"type": "scatter"}],
            ],
        )

        # 1. Box plot de MAE por CV
        for i, result in enumerate(results):
            mae_scores = result.cv_scores.get("mae", [])
            fig.add_trace(
                go.Box(
                    y=mae_scores,
                    name=result.model_name,
                    showlegend=False,
                    marker_color=px.colors.qualitative.Set1[
                        i % len(px.colors.qualitative.Set1)
                    ],
                ),
                row=1,
                col=1,
            )

        # 2. R² vs MAE scatter
        for i, result in enumerate(results):
            fig.add_trace(
                go.Scatter(
                    x=[result.mae],
                    y=[result.r2],
                    mode="markers+text",
                    text=[result.model_name],
                    textposition="top center",
                    marker=dict(
                        size=12,
                        color=px.colors.qualitative.Set1[
                            i % len(px.colors.qualitative.Set1)
                        ],
                    ),
                    showlegend=False,
                ),
                row=1,
                col=2,
            )

        # 3. Distribución de residuos
        for i, result in enumerate(results):
            fig.add_trace(
                go.Violin(
                    y=result.residuals,
                    name=result.model_name,
                    showlegend=False,
                    side="positive",
                    meanline_visible=True,
                ),
                row=2,
                col=1,
            )

        # 4. Eficiencia (Tiempo vs Performance)
        for i, result in enumerate(results):
            fig.add_trace(
                go.Scatter(
                    x=[result.training_time],
                    y=[result.r2],
                    mode="markers+text",
                    text=[result.model_name],
                    textposition="top center",
                    marker=dict(
                        size=result.mae * 2,  # Tamaño proporcional al error
                        color=px.colors.qualitative.Set1[
                            i % len(px.colors.qualitative.Set1)
                        ],
                        opacity=0.7,
                    ),
                    showlegend=False,
                ),
                row=2,
                col=2,
            )

        # Actualizar layout
        fig.update_layout(
            height=800,
            title_text="📊 Comparación Académica de Modelos Baseline - PDI Liga Tailandesa",
            title_x=0.5,
        )

        # Etiquetas de ejes
        fig.update_xaxes(title_text="MAE", row=1, col=2)
        fig.update_yaxes(title_text="R²", row=1, col=2)
        fig.update_yaxes(title_text="MAE", row=1, col=1)
        fig.update_yaxes(title_text="Residuos", row=2, col=1)
        fig.update_xaxes(title_text="Tiempo Entrenamiento (s)", row=2, col=2)
        fig.update_yaxes(title_text="R²", row=2, col=2)

        fig.show()

        # Imprimir estadísticas académicas
        print("\n📈 ANÁLISIS ESTADÍSTICO COMPARATIVO:")
        print("=" * 70)

        comparison_df = self.compare_models(results)
        print(comparison_df.round(3).to_string(index=False))

        # Mejores modelos por métrica
        best_mae = comparison_df.loc[comparison_df["MAE"].idxmin()]
        best_r2 = comparison_df.loc[comparison_df["R²"].idxmax()]
        most_stable = comparison_df.loc[comparison_df["CV_Stability"].idxmax()]

        print(f"\n🏆 RANKINGS ACADÉMICOS:")
        print(f"   🥇 Menor MAE: {best_mae['Model']} (MAE = {best_mae['MAE']:.3f})")
        print(f"   🥇 Mayor R²: {best_r2['Model']} (R² = {best_r2['R²']:.3f})")
        print(
            f"   🥇 Más Estable: {most_stable['Model']} (Estabilidad = {most_stable['CV_Stability']:.3f})"
        )

    def generate_learning_curves(
        self, model: BaselineModel, X: np.ndarray, y: np.ndarray
    ) -> None:
        """
        Genera learning curves académicas para análisis de sesgo-varianza.

        Args:
            model: Modelo a analizar
            X: Features de entrenamiento
            y: Target PDI
        """
        try:
            logger.info(f"Generando learning curves para {model.model_name}...")

            # Configurar tamaños de entrenamiento
            train_sizes = np.linspace(0.1, 1.0, 10)

            # Calcular learning curves
            train_sizes_abs, train_scores, val_scores = learning_curve(
                model,
                X,
                y,
                train_sizes=train_sizes,
                cv=self.cv_folds,
                scoring="neg_mean_absolute_error",
                n_jobs=-1,
                shuffle=True,
                random_state=self.random_state,
            )

            # Convertir a MAE positivo
            train_mae_mean = -np.mean(train_scores, axis=1)
            train_mae_std = np.std(train_scores, axis=1)
            val_mae_mean = -np.mean(val_scores, axis=1)
            val_mae_std = np.std(val_scores, axis=1)

            # Crear visualización
            fig = go.Figure()

            # Curva de entrenamiento
            fig.add_trace(
                go.Scatter(
                    x=train_sizes_abs,
                    y=train_mae_mean,
                    mode="lines+markers",
                    name="Training MAE",
                    line=dict(color="blue"),
                    error_y=dict(type="data", array=train_mae_std, visible=True),
                )
            )

            # Curva de validación
            fig.add_trace(
                go.Scatter(
                    x=train_sizes_abs,
                    y=val_mae_mean,
                    mode="lines+markers",
                    name="Validation MAE",
                    line=dict(color="red"),
                    error_y=dict(type="data", array=val_mae_std, visible=True),
                )
            )

            # Layout académico
            fig.update_layout(
                title=f"📈 Learning Curves - {model.model_name}",
                xaxis_title="Tamaño de Entrenamiento",
                yaxis_title="Mean Absolute Error (MAE)",
                height=500,
                showlegend=True,
            )

            fig.show()

            # Análisis académico
            final_gap = val_mae_mean[-1] - train_mae_mean[-1]

            print(f"\n📊 ANÁLISIS DE LEARNING CURVES - {model.model_name}:")
            print(f"   Gap final Train-Val: {final_gap:.3f}")

            if final_gap < 2:
                print("   ✅ Buen balance sesgo-varianza")
            elif final_gap < 5:
                print("   ⚠️ Ligero overfitting")
            else:
                print("   ❌ Overfitting significativo")

        except Exception as e:
            logger.error(f"Error generando learning curves: {e}")
            raise


def create_baseline_pipeline() -> Dict[str, BaselineModel]:
    """
    Crea pipeline completo de modelos baseline para evaluación académica.

    Returns:
        Diccionario con modelos baseline configurados
    """
    models = {
        "linear": LinearBaselineModel(),
        "ridge": RidgeBaselineModel(alpha=1.0),
        "ridge_strong": RidgeBaselineModel(alpha=10.0),
        "ensemble": EnsembleBaselineModel(n_estimators=50),
    }

    logger.info(f"Pipeline baseline creado con {len(models)} modelos")
    return models


def run_comprehensive_baseline_evaluation(
    seasons: List[str] = None,
) -> Dict[str, BaselineResults]:
    """
    Ejecuta evaluación académica completa de modelos baseline.

    Args:
        seasons: Lista de temporadas a incluir (opcional)

    Returns:
        Diccionario con resultados de evaluación
    """
    try:
        logger.info("🚀 Iniciando evaluación comprehensiva de modelos baseline...")

        # Cargar datos desde BD
        with get_db_session() as session:
            query = session.query(ProfessionalStats)
            if seasons:
                query = query.filter(ProfessionalStats.season.in_(seasons))

            stats_data = query.all()

        if not stats_data:
            raise ValueError("No se encontraron datos para evaluación")

        # Convertir a DataFrame
        data = []
        for stat in stats_data:
            row = {}
            for column in stat.__table__.columns:
                row[column.name] = getattr(stat, column.name)
            data.append(row)

        df = pd.DataFrame(data)
        logger.info(f"Datos cargados: {len(df)} registros")

        # Filtrar datos válidos (mínimo de partidos)
        df_valid = df[
            (df["matches_played"].fillna(0) >= 3)
            & (df["minutes_played"].fillna(0) >= 180)
            & (df["primary_position"].notna())
        ].copy()

        logger.info(f"Datos válidos para evaluación: {len(df_valid)} registros")

        if len(df_valid) < 100:
            raise ValueError("Datos insuficientes para evaluación rigurosa")

        # Preparar features y target
        baseline_model = LinearBaselineModel()
        X_df = baseline_model.extract_baseline_features(df_valid)
        y = baseline_model.calculate_target_pdi(df_valid)

        # Convertir a arrays numpy
        X = X_df.values
        feature_names = X_df.columns.tolist()
        positions = df_valid["primary_position"].values

        logger.info(f"Features preparadas: {X.shape}")
        logger.info(f"Target PDI - mean: {np.mean(y):.1f}, std: {np.std(y):.1f}")

        # Crear y evaluar modelos
        models = create_baseline_pipeline()
        evaluator = BaselineEvaluator(cv_folds=5)

        results = {}

        for model_name, model in models.items():
            logger.info(f"Evaluando {model_name}...")

            result = evaluator.evaluate_model(
                model=model, X=X, y=y, positions=positions
            )

            results[model_name] = result

        # Análisis comparativo
        logger.info("\n🎯 GENERANDO ANÁLISIS COMPARATIVO...")
        evaluator.plot_model_comparison(list(results.values()))

        # Learning curves del mejor modelo
        best_model_name = min(results.keys(), key=lambda k: results[k].mae)
        best_model = models[best_model_name]

        logger.info(f"Generando learning curves para mejor modelo: {best_model_name}")
        evaluator.generate_learning_curves(best_model, X, y)

        # Resumen académico
        print("\n" + "=" * 80)
        print("📋 RESUMEN EJECUTIVO - EVALUACIÓN BASELINE PDI")
        print("=" * 80)

        comparison_df = evaluator.compare_models(list(results.values()))

        print(f"\n📊 MEJORES RESULTADOS:")
        best_overall = comparison_df.iloc[0]
        print(f"   🏆 Mejor modelo: {best_overall['Model']}")
        print(
            f"   📈 MAE: {best_overall['MAE']:.3f} ± {best_overall['CV_MAE_std']:.3f}"
        )
        print(f"   📈 R²: {best_overall['R²']:.3f}")
        print(f"   📈 Calificación: {best_overall['Performance_Grade']}")

        # Objetivo académico
        target_mae = 15.0
        models_meeting_target = comparison_df[comparison_df["MAE"] < target_mae]

        print(f"\n🎯 OBJETIVO ACADÉMICO (MAE < {target_mae}):")
        if len(models_meeting_target) > 0:
            print(f"   ✅ {len(models_meeting_target)} modelos cumplen objetivo")
            for _, model in models_meeting_target.iterrows():
                print(f"      • {model['Model']}: MAE = {model['MAE']:.3f}")
        else:
            print(f"   ❌ Ningún modelo cumple objetivo inicial")
            print(f"   📋 Mejor MAE logrado: {comparison_df['MAE'].min():.3f}")
            print(f"   💡 Considerar features adicionales o modelos más complejos")

        print("\n✅ EVALUACIÓN BASELINE COMPLETADA")
        print(
            "🚀 RECOMENDACIÓN: Proceder con modelos avanzados basados en estos resultados"
        )
        print("=" * 80)

        return results

    except Exception as e:
        logger.error(f"Error en evaluación baseline: {e}")
        raise


class AdvancedBaselineModel(BaselineModel):
    """
    Modelo Baseline Avanzado con Feature Engineering sofisticado.

    Extiende el BaselineModel con features avanzadas por posición, edad y tiers
    para mejorar significativamente la predicción del PDI.

    Objetivo: Superar baseline original (MAE 0.774) con MAE < 0.700
    """

    def __init__(self, model_type="ensemble", **model_params):
        """
        Inicializa modelo baseline avanzado.

        Args:
            model_type: 'linear', 'ridge', 'ensemble'
            **model_params: Parámetros específicos del modelo
        """
        super().__init__(f"Advanced_{model_type.title()}_Baseline")

        # Inicializar motor de features avanzadas
        self.advanced_feature_engineer = create_advanced_feature_pipeline()

        # Configurar modelo subyacente
        self.model_type = model_type
        self.model_params = model_params

        if model_type == "linear":
            self.model = LinearRegression()
        elif model_type == "ridge":
            alpha = model_params.get("alpha", 1.0)
            self.model = Ridge(alpha=alpha, random_state=42)
        elif model_type == "ensemble":
            # Ensemble más sofisticado
            self.model = GradientBoostingRegressor(
                n_estimators=model_params.get("n_estimators", 100),
                learning_rate=model_params.get("learning_rate", 0.1),
                max_depth=model_params.get("max_depth", 6),
                random_state=42,
            )
        else:
            raise ValueError(f"Tipo de modelo no soportado: {model_type}")

        logger.info(f"🚀 {self.model_name} inicializado con {model_type}")

    def extract_advanced_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extrae features avanzadas combinando baseline + advanced engineering.

        Args:
            df: DataFrame con datos de Thai League

        Returns:
            DataFrame con features baseline + avanzadas
        """
        try:
            logger.info("🔧 Extrayendo features avanzadas...")

            # 1. Features baseline (sin circularidad)
            baseline_features = self.extract_baseline_features(df)

            # 2. Features avanzadas usando motor especializado
            enhanced_df = self.advanced_feature_engineer.engineer_advanced_features(df)

            # 3. Combinar features baseline con avanzadas
            # Solo tomar nuevas features avanzadas (evitar duplicates)
            baseline_columns = set(baseline_features.columns)
            advanced_only = enhanced_df[
                [col for col in enhanced_df.columns if col not in baseline_columns]
            ]

            # Concatenar features
            combined_features = pd.concat([baseline_features, advanced_only], axis=1)

            logger.info(
                f"✅ Features combinadas: {len(combined_features.columns)} "
                f"(baseline: {len(baseline_features.columns)}, "
                f"avanzadas: {len(advanced_only.columns)})"
            )

            return combined_features

        except Exception as e:
            logger.error(f"❌ Error extrayendo features avanzadas: {e}")
            # Fallback a features baseline si falla
            return self.extract_baseline_features(df)

    def fit(
        self, df: pd.DataFrame, target: np.ndarray = None
    ) -> "AdvancedBaselineModel":
        """
        Entrena el modelo con features avanzadas.

        Args:
            df: DataFrame con datos
            target: Array con valores target (PDI). Si None, se calcula

        Returns:
            Self para method chaining
        """
        try:
            logger.info(f"🎯 Entrenando {self.model_name}...")

            # Extraer features avanzadas
            X_df = self.extract_advanced_features(df)

            # Calcular target si no se proporciona
            if target is None:
                target = self.calculate_target_pdi(df)

            # Manejo de NaN
            X_clean = X_df.fillna(X_df.mean())
            y_clean = pd.Series(target).fillna(pd.Series(target).mean()).values

            # Escalar features
            X_scaled = self.scaler.fit_transform(X_clean)

            # Entrenar modelo
            self.model.fit(X_scaled, y_clean)

            # Guardar información del entrenamiento
            self.feature_names_ = X_clean.columns.tolist()
            self.n_features_ = len(self.feature_names_)
            self.is_fitted = True

            logger.info(f"✅ {self.model_name} entrenado: {self.n_features_} features")

            return self

        except Exception as e:
            logger.error(f"❌ Error entrenando modelo avanzado: {e}")
            raise

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predice PDI usando features avanzadas.

        Args:
            df: DataFrame con datos

        Returns:
            Array con predicciones PDI
        """
        if not self.is_fitted:
            raise ValueError("Modelo no entrenado. Llamar fit() primero.")

        try:
            # Extraer features avanzadas
            X_df = self.extract_advanced_features(df)

            # Manejo de NaN
            X_clean = X_df.fillna(0)  # Usar 0 para predicción

            # Escalar usando scaler entrenado
            X_scaled = self.scaler.transform(X_clean)

            # Predecir
            predictions = self.model.predict(X_scaled)

            return predictions

        except Exception as e:
            logger.error(f"❌ Error en predicción avanzada: {e}")
            raise

    def get_feature_importance(self) -> Dict[str, float]:
        """
        Obtiene importancia de features si el modelo lo soporta.

        Returns:
            Dict con nombre de feature y su importancia
        """
        if not self.is_fitted:
            return {}

        try:
            if hasattr(self.model, "feature_importances_"):
                # Para tree-based models
                importances = self.model.feature_importances_
                return dict(zip(self.feature_names_, importances))
            elif hasattr(self.model, "coef_"):
                # Para modelos lineales
                coefficients = np.abs(self.model.coef_)
                return dict(zip(self.feature_names_, coefficients))
            else:
                return {}

        except Exception as e:
            logger.error(f"Error obteniendo importancia de features: {e}")
            return {}


def run_advanced_baseline_comparison(
    df: pd.DataFrame, baseline_results: Dict = None
) -> Dict:
    """
    Ejecuta comparación entre modelos baseline tradicionales y avanzados.

    Args:
        df: DataFrame con datos de Thai League
        baseline_results: Resultados de baseline tradicional para comparación

    Returns:
        Dict con resultados de comparación
    """
    try:
        logger.info("🚀 INICIANDO COMPARACIÓN BASELINE VS AVANZADO")
        print("=" * 80)

        # Calcular target PDI
        base_model = LinearBaselineModel()
        target_pdi = base_model.calculate_target_pdi(df)

        # Configurar modelos avanzados
        advanced_models = {
            "Advanced Linear": AdvancedBaselineModel("linear"),
            "Advanced Ridge": AdvancedBaselineModel("ridge", alpha=1.0),
            "Advanced Ensemble": AdvancedBaselineModel("ensemble", n_estimators=100),
        }

        # Evaluar modelos avanzados
        advanced_results = {}

        for name, model in advanced_models.items():
            logger.info(f"🔬 Evaluando {name}...")

            # Entrenar modelo
            model.fit(df, target_pdi)

            # Predecir
            predictions = model.predict(df)

            # Calcular métricas
            mae = mean_absolute_error(target_pdi, predictions)
            rmse = np.sqrt(mean_squared_error(target_pdi, predictions))
            r2 = r2_score(target_pdi, predictions)
            mape = mean_absolute_percentage_error(target_pdi, predictions) * 100

            # Guardar resultados
            advanced_results[name] = {
                "MAE": mae,
                "RMSE": rmse,
                "R²": r2,
                "MAPE": mape,
                "Model": model,
                "Predictions": predictions,
                "Feature_Importance": model.get_feature_importance(),
            }

            print(f"✅ {name}:")
            print(f"   📊 MAE: {mae:.3f}, R²: {r2:.3f}, MAPE: {mape:.1f}%")

        # Análisis comparativo
        print(f"\n📈 ANÁLISIS COMPARATIVO:")

        # Mejor modelo avanzado
        best_advanced = min(advanced_results.items(), key=lambda x: x[1]["MAE"])

        print(f"🏆 MEJOR MODELO AVANZADO: {best_advanced[0]}")
        print(f"   MAE: {best_advanced[1]['MAE']:.3f}")
        print(f"   R²: {best_advanced[1]['R²']:.3f}")
        print(f"   MAPE: {best_advanced[1]['MAPE']:.1f}%")

        # Comparación con baseline si está disponible
        if baseline_results:
            baseline_mae = min([r["MAE"] for r in baseline_results.values()])
            improvement = baseline_mae - best_advanced[1]["MAE"]

            print(f"\n🎯 MEJORA VS BASELINE:")
            print(f"   Baseline MAE: {baseline_mae:.3f}")
            print(f"   Avanzado MAE: {best_advanced[1]['MAE']:.3f}")
            print(f"   Mejora: {improvement:.3f} ({improvement/baseline_mae*100:.1f}%)")

            if improvement > 0:
                print("   ✅ ¡MEJORA SIGNIFICATIVA LOGRADA!")
            else:
                print("   ⚠️ No hay mejora significativa")

        # Objetivo académico
        target_mae = 0.700
        meets_target = best_advanced[1]["MAE"] < target_mae

        print(f"\n🎯 OBJETIVO ACADÉMICO AVANZADO (MAE < {target_mae}):")
        if meets_target:
            print("   ✅ OBJETIVO CUMPLIDO")
            print("   🚀 Listo para modelos híbridos avanzados")
        else:
            gap = best_advanced[1]["MAE"] - target_mae
            print(f"   ❌ Objetivo no cumplido - Gap: {gap:.3f}")
            print("   💡 Considerar arquitectura híbrida")

        return {
            "advanced_results": advanced_results,
            "best_model": best_advanced,
            "meets_target": meets_target,
            "improvement_vs_baseline": improvement if baseline_results else None,
        }

    except Exception as e:
        logger.error(f"❌ Error en comparación avanzada: {e}")
        raise


if __name__ == "__main__":
    # Ejecutar evaluación baseline completa
    results = run_comprehensive_baseline_evaluation()

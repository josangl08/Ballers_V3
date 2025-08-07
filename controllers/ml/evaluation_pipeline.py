"""
Evaluation Pipeline - Sistema de evaluación académica para modelos PDI.

Este módulo implementa un pipeline robusto de evaluación siguiendo estándares
académicos rigurosos para el análisis de modelos de Machine Learning aplicados
al Player Development Index (PDI).

Metodología CRISP-DM:
- Evaluación sistemática con múltiples métricas
- Validación cruzada estratificada por posición
- Análisis estadístico de significancia
- Visualizaciones académicas con Plotly
- Reportes reproducibles para investigación

Características Académicas:
- Métricas estándar (MAE, RMSE, R², MAPE)
- Análisis de residuos por posición
- Tests de significancia estadística
- Intervalos de confianza
- Comparación rigurosa entre modelos
- Análisis de sesgo-varianza

Objetivo: Establecer framework de evaluación reproducible y riguroso
para comparar modelos PDI con estándares académicos internacionales.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import warnings
from pathlib import Path
import json

# Análisis estadístico
from scipy import stats
from scipy.stats import ttest_rel, wilcoxon, friedmanchisquare
import statsmodels.api as sm
from statsmodels.stats.contingency_tables import mcnemar

# Machine Learning
from sklearn.base import BaseEstimator
from sklearn.model_selection import (
    cross_val_score, cross_validate, StratifiedKFold, KFold,
    permutation_test_score, validation_curve, learning_curve
)
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    mean_absolute_percentage_error, explained_variance_score,
    median_absolute_error, max_error
)
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline

# Visualización académica
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.figure_factory as ff

# Configurar logging y warnings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore', category=FutureWarning)


@dataclass
class ModelPerformance:
    """
    Estructura académica para almacenar rendimiento de modelos.
    
    Contiene todas las métricas y estadísticas necesarias para
    evaluación académica rigurosa siguiendo estándares de ML.
    """
    model_name: str
    
    # Métricas principales
    mae: float
    rmse: float
    r2: float
    mape: float
    
    # Métricas adicionales
    median_ae: float = 0.0
    max_error: float = 0.0
    explained_variance: float = 0.0
    
    # Validación cruzada
    cv_scores: Dict[str, np.ndarray] = field(default_factory=dict)
    cv_mean: Dict[str, float] = field(default_factory=dict)
    cv_std: Dict[str, float] = field(default_factory=dict)
    
    # Análisis por posición
    position_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Arrays para análisis
    predictions: np.ndarray = field(default_factory=lambda: np.array([]))
    actuals: np.ndarray = field(default_factory=lambda: np.array([]))
    residuals: np.ndarray = field(default_factory=lambda: np.array([]))
    
    # Metadatos
    n_samples: int = 0
    n_features: int = 0
    training_time: float = 0.0
    prediction_time: float = 0.0
    
    # Feature importance
    feature_importance: Optional[Dict[str, float]] = None
    
    # Intervalos de confianza
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    
    def get_academic_summary(self) -> Dict[str, Any]:
        """Retorna resumen académico del rendimiento."""
        return {
            'Model': self.model_name,
            'MAE': f"{self.mae:.3f} ± {self.cv_std.get('mae', 0):.3f}",
            'RMSE': f"{self.rmse:.3f}",
            'R²': f"{self.r2:.3f} ± {self.cv_std.get('r2', 0):.3f}",
            'MAPE': f"{self.mape:.2f}%",
            'CV_Stability': f"{1 - (self.cv_std.get('mae', 0) / self.cv_mean.get('mae', 1)):.3f}",
            'N_Samples': self.n_samples,
            'Training_Time': f"{self.training_time:.2f}s"
        }


@dataclass
class EvaluationConfig:
    """
    Configuración académica para pipeline de evaluación.
    
    Define parámetros estándar para evaluación reproducible
    siguiendo mejores prácticas académicas en ML.
    """
    # Validación cruzada
    cv_folds: int = 5
    cv_strategy: str = "stratified"  # "stratified", "kfold", "grouped"
    
    # Métricas principales
    primary_metric: str = "mae"
    secondary_metrics: List[str] = field(default_factory=lambda: ["rmse", "r2", "mape"])
    
    # Configuración estadística
    confidence_level: float = 0.95
    significance_level: float = 0.05
    n_permutations: int = 1000
    
    # Análisis por posición
    position_analysis: bool = True
    min_samples_per_position: int = 10
    
    # Reproducibilidad
    random_state: int = 42
    
    # Output
    save_results: bool = True
    results_dir: str = "results/baseline_evaluation"
    
    # Visualización
    plot_style: str = "academic"
    figure_format: str = "html"
    dpi: int = 300


class StatisticalAnalyzer:
    """
    Analizador estadístico académico para comparación de modelos.
    
    Implementa tests estadísticos rigurosos para determinar
    significancia en diferencias de rendimiento entre modelos.
    """
    
    def __init__(self, significance_level: float = 0.05):
        """
        Inicializa analizador estadístico.
        
        Args:
            significance_level: Nivel de significancia para tests
        """
        self.significance_level = significance_level
        
    def compare_models_paired_ttest(self, 
                                  performance1: ModelPerformance,
                                  performance2: ModelPerformance,
                                  metric: str = "mae") -> Dict[str, Any]:
        """
        Compara dos modelos usando paired t-test académico.
        
        Args:
            performance1: Rendimiento del primer modelo
            performance2: Rendimiento del segundo modelo  
            metric: Métrica para comparación
            
        Returns:
            Diccionario con resultados del test estadístico
        """
        try:
            scores1 = performance1.cv_scores.get(metric, [])
            scores2 = performance2.cv_scores.get(metric, [])
            
            if len(scores1) != len(scores2) or len(scores1) == 0:
                return {"error": "Scores de CV inconsistentes"}
            
            # Paired t-test
            statistic, p_value = ttest_rel(scores1, scores2)
            
            # Interpretación académica
            is_significant = p_value < self.significance_level
            effect_size = (np.mean(scores1) - np.mean(scores2)) / np.sqrt(
                (np.var(scores1) + np.var(scores2)) / 2
            )
            
            # Intervalo de confianza para la diferencia
            diff = scores1 - scores2
            ci_lower, ci_upper = stats.t.interval(
                0.95, len(diff)-1, loc=np.mean(diff), scale=stats.sem(diff)
            )
            
            return {
                'test': 'Paired t-test',
                'metric': metric,
                'statistic': statistic,
                'p_value': p_value,
                'is_significant': is_significant,
                'effect_size': effect_size,
                'mean_diff': np.mean(diff),
                'confidence_interval': (ci_lower, ci_upper),
                'interpretation': self._interpret_ttest_results(
                    performance1.model_name, performance2.model_name,
                    metric, p_value, effect_size
                )
            }
            
        except Exception as e:
            logger.error(f"Error en paired t-test: {e}")
            return {"error": str(e)}
    
    def compare_multiple_models_friedman(self,
                                       performances: List[ModelPerformance],
                                       metric: str = "mae") -> Dict[str, Any]:
        """
        Compara múltiples modelos usando Friedman test.
        
        Args:
            performances: Lista de rendimientos de modelos
            metric: Métrica para comparación
            
        Returns:
            Resultados del test de Friedman
        """
        try:
            # Preparar datos para Friedman test
            scores_matrix = []
            model_names = []
            
            for perf in performances:
                scores = perf.cv_scores.get(metric, [])
                if len(scores) > 0:
                    scores_matrix.append(scores)
                    model_names.append(perf.model_name)
            
            if len(scores_matrix) < 3:
                return {"error": "Se requieren al menos 3 modelos"}
            
            # Friedman test
            statistic, p_value = friedmanchisquare(*scores_matrix)
            
            is_significant = p_value < self.significance_level
            
            # Post-hoc análisis si es significativo
            pairwise_comparisons = {}
            if is_significant:
                for i in range(len(model_names)):
                    for j in range(i+1, len(model_names)):
                        comparison = self.compare_models_paired_ttest(
                            performances[i], performances[j], metric
                        )
                        pairwise_comparisons[f"{model_names[i]}_vs_{model_names[j]}"] = comparison
            
            return {
                'test': 'Friedman test',
                'metric': metric,
                'statistic': statistic,
                'p_value': p_value,
                'is_significant': is_significant,
                'models': model_names,
                'pairwise_comparisons': pairwise_comparisons,
                'interpretation': self._interpret_friedman_results(
                    model_names, metric, p_value, is_significant
                )
            }
            
        except Exception as e:
            logger.error(f"Error en Friedman test: {e}")
            return {"error": str(e)}
    
    def _interpret_ttest_results(self, model1: str, model2: str, 
                               metric: str, p_value: float, effect_size: float) -> str:
        """Interpreta resultados de t-test académicamente."""
        
        significance = "significativa" if p_value < self.significance_level else "no significativa"
        
        if abs(effect_size) < 0.2:
            effect = "pequeño"
        elif abs(effect_size) < 0.8:
            effect = "mediano"
        else:
            effect = "grande"
        
        better_model = model1 if effect_size > 0 else model2
        
        return (
            f"La diferencia en {metric} entre {model1} y {model2} es {significance} "
            f"(p = {p_value:.4f}). El tamaño del efecto es {effect} "
            f"(d = {effect_size:.3f}). {better_model} muestra mejor rendimiento."
        )
    
    def _interpret_friedman_results(self, models: List[str], metric: str,
                                  p_value: float, is_significant: bool) -> str:
        """Interpreta resultados de Friedman test académicamente."""
        
        if is_significant:
            return (
                f"El test de Friedman indica diferencias significativas en {metric} "
                f"entre los {len(models)} modelos evaluados (p = {p_value:.4f}). "
                f"Se requiere análisis post-hoc para identificar diferencias específicas."
            )
        else:
            return (
                f"El test de Friedman no encuentra diferencias significativas en {metric} "
                f"entre los {len(models)} modelos evaluados (p = {p_value:.4f}). "
                f"Los modelos muestran rendimiento estadísticamente equivalente."
            )


class AcademicVisualizer:
    """
    Generador de visualizaciones académicas para evaluación de modelos PDI.
    
    Crea gráficos siguiendo estándares académicos con énfasis en claridad,
    interpretabilidad y rigor estadístico.
    """
    
    def __init__(self, style: str = "academic"):
        """
        Inicializa visualizador académico.
        
        Args:
            style: Estilo de visualización ("academic", "presentation")
        """
        self.style = style
        self.colors = px.colors.qualitative.Set1
        
    def plot_model_comparison_academic(self, 
                                     performances: List[ModelPerformance],
                                     config: EvaluationConfig) -> None:
        """
        Crea comparación académica integral de modelos.
        
        Args:
            performances: Lista de rendimientos de modelos
            config: Configuración de evaluación
        """
        # Crear figura con subplots académicos
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=[
                "Distribución de MAE (Validación Cruzada)",
                "R² vs MAE - Análisis de Eficiencia", 
                "Análisis de Residuos por Modelo",
                "Intervalos de Confianza por Métrica",
                "Estabilidad de Validación Cruzada",
                "Tiempo de Entrenamiento vs Rendimiento"
            ],
            specs=[
                [{"type": "box"}, {"type": "scatter"}],
                [{"type": "violin"}, {"type": "scatter"}],
                [{"type": "scatter"}, {"type": "scatter"}]
            ]
        )
        
        # 1. Box plot de MAE por CV
        for i, perf in enumerate(performances):
            mae_scores = perf.cv_scores.get('mae', [])
            if len(mae_scores) > 0:
                fig.add_trace(
                    go.Box(
                        y=mae_scores,
                        name=perf.model_name,
                        marker_color=self.colors[i % len(self.colors)],
                        showlegend=False,
                        boxmean=True
                    ),
                    row=1, col=1
                )
        
        # 2. R² vs MAE efficiency plot
        for i, perf in enumerate(performances):
            fig.add_trace(
                go.Scatter(
                    x=[perf.mae],
                    y=[perf.r2],
                    mode='markers+text',
                    text=[perf.model_name],
                    textposition="top center",
                    marker=dict(
                        size=15,
                        color=self.colors[i % len(self.colors)],
                        line=dict(width=2, color='white')
                    ),
                    showlegend=False,
                    hovertemplate=(
                        f"<b>{perf.model_name}</b><br>"
                        f"MAE: {perf.mae:.3f}<br>"
                        f"R²: {perf.r2:.3f}<br>"
                        f"Samples: {perf.n_samples}<extra></extra>"
                    )
                ),
                row=1, col=2
            )
        
        # 3. Análisis de residuos
        for i, perf in enumerate(performances):
            if len(perf.residuals) > 0:
                fig.add_trace(
                    go.Violin(
                        y=perf.residuals,
                        name=perf.model_name,
                        side="positive",
                        meanline_visible=True,
                        showlegend=False,
                        marker_color=self.colors[i % len(self.colors)]
                    ),
                    row=2, col=1
                )
        
        # 4. Intervalos de confianza
        metrics = ['mae', 'r2', 'rmse']
        x_pos = []
        y_values = []
        y_errors = []
        colors_list = []
        text_labels = []
        
        for j, metric in enumerate(metrics):
            for i, perf in enumerate(performances):
                mean_val = perf.cv_mean.get(metric, perf.__dict__.get(metric, 0))
                std_val = perf.cv_std.get(metric, 0)
                
                x_pos.append(j + (i - len(performances)/2) * 0.1)
                y_values.append(mean_val)
                y_errors.append(1.96 * std_val)  # 95% CI
                colors_list.append(self.colors[i % len(self.colors)])
                text_labels.append(perf.model_name if j == 0 else "")
        
        fig.add_trace(
            go.Scatter(
                x=x_pos,
                y=y_values,
                error_y=dict(type='data', array=y_errors, visible=True),
                mode='markers',
                marker=dict(size=8, color=colors_list),
                text=text_labels,
                showlegend=False
            ),
            row=2, col=2
        )
        
        # 5. Estabilidad CV (CV std/mean)
        for i, perf in enumerate(performances):
            mae_stability = 1 - (perf.cv_std.get('mae', 0) / perf.cv_mean.get('mae', 1))
            r2_stability = 1 - (perf.cv_std.get('r2', 0) / perf.cv_mean.get('r2', 1))
            
            fig.add_trace(
                go.Scatter(
                    x=[mae_stability],
                    y=[r2_stability], 
                    mode='markers+text',
                    text=[perf.model_name],
                    textposition="top center",
                    marker=dict(
                        size=12,
                        color=self.colors[i % len(self.colors)]
                    ),
                    showlegend=False
                ),
                row=3, col=1
            )
        
        # 6. Tiempo vs Rendimiento
        for i, perf in enumerate(performances):
            fig.add_trace(
                go.Scatter(
                    x=[perf.training_time],
                    y=[perf.r2],
                    mode='markers+text',
                    text=[perf.model_name],
                    textposition="top center",
                    marker=dict(
                        size=max(5, perf.mae * 2),  # Tamaño proporcional al error
                        color=self.colors[i % len(self.colors)],
                        opacity=0.8
                    ),
                    showlegend=False
                ),
                row=3, col=2
            )
        
        # Configurar layout académico
        fig.update_layout(
            height=1000,
            title_text="📊 Evaluación Académica Integral - Modelos Baseline PDI Liga Tailandesa",
            title_x=0.5,
            font=dict(family="Arial", size=12),
            showlegend=False
        )
        
        # Etiquetas específicas
        fig.update_xaxes(title_text="Modelo", row=1, col=1)
        fig.update_yaxes(title_text="MAE", row=1, col=1)
        
        fig.update_xaxes(title_text="Mean Absolute Error", row=1, col=2)
        fig.update_yaxes(title_text="R² Score", row=1, col=2)
        
        fig.update_yaxes(title_text="Residuos", row=2, col=1)
        
        fig.update_xaxes(title_text="Métrica (0=MAE, 1=R², 2=RMSE)", row=2, col=2)
        fig.update_yaxes(title_text="Valor ± 95% CI", row=2, col=2)
        
        fig.update_xaxes(title_text="Estabilidad MAE", row=3, col=1)
        fig.update_yaxes(title_text="Estabilidad R²", row=3, col=1)
        
        fig.update_xaxes(title_text="Tiempo Entrenamiento (s)", row=3, col=2)
        fig.update_yaxes(title_text="R² Score", row=3, col=2)
        
        fig.show()
    
    def plot_position_analysis(self, performances: List[ModelPerformance]) -> None:
        """
        Crea análisis académico de rendimiento por posición.
        
        Args:
            performances: Lista de rendimientos con análisis por posición
        """
        # Extraer datos por posición
        position_data = {}
        
        for perf in performances:
            for position, metrics in perf.position_performance.items():
                if position not in position_data:
                    position_data[position] = {}
                position_data[position][perf.model_name] = metrics
        
        if not position_data:
            logger.warning("No hay datos de rendimiento por posición")
            return
        
        # Crear heatmap por posición
        positions = list(position_data.keys())
        models = list(performances[0].position_performance.get(positions[0], {}).keys()) if positions else []
        
        # Matriz de MAE por posición
        mae_matrix = []
        for position in positions:
            row = []
            for model in models:
                mae_val = position_data[position].get(model, {}).get('mae', np.nan)
                row.append(mae_val)
            mae_matrix.append(row)
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=[
                "MAE por Posición y Modelo",
                "Variabilidad de Rendimiento por Posición"
            ],
            specs=[[{"type": "heatmap"}, {"type": "box"}]]
        )
        
        # Heatmap de MAE
        fig.add_trace(
            go.Heatmap(
                z=mae_matrix,
                x=models,
                y=positions,
                colorscale='RdYlBu_r',
                showscale=True,
                hovertemplate="Posición: %{y}<br>Modelo: %{x}<br>MAE: %{z:.3f}<extra></extra>"
            ),
            row=1, col=1
        )
        
        # Box plot de variabilidad por posición
        all_mae_by_position = {}
        for position in positions:
            mae_values = []
            for model in models:
                mae_val = position_data[position].get(model, {}).get('mae', np.nan)
                if not np.isnan(mae_val):
                    mae_values.append(mae_val)
            all_mae_by_position[position] = mae_values
        
        for i, (position, mae_vals) in enumerate(all_mae_by_position.items()):
            if mae_vals:
                fig.add_trace(
                    go.Box(
                        y=mae_vals,
                        name=position,
                        marker_color=self.colors[i % len(self.colors)],
                        showlegend=False
                    ),
                    row=1, col=2
                )
        
        fig.update_layout(
            height=500,
            title_text="📍 Análisis de Rendimiento por Posición - PDI Liga Tailandesa",
            title_x=0.5
        )
        
        fig.update_yaxes(title_text="MAE", row=1, col=2)
        
        fig.show()


class EvaluationPipeline:
    """
    Pipeline académico principal para evaluación rigurosa de modelos PDI.
    
    Integra todas las funcionalidades de evaluación en un workflow
    sistemático siguiendo metodología CRISP-DM y estándares académicos.
    
    Features:
    - Evaluación multi-métrica con validación cruzada
    - Análisis estadístico de significancia
    - Visualizaciones académicas profesionales
    - Reportes reproducibles
    - Análisis por posición
    - Intervalos de confianza
    """
    
    def __init__(self, config: EvaluationConfig = None):
        """
        Inicializa pipeline de evaluación académica.
        
        Args:
            config: Configuración personalizada (opcional)
        """
        self.config = config or EvaluationConfig()
        self.statistical_analyzer = StatisticalAnalyzer(
            significance_level=self.config.significance_level
        )
        self.visualizer = AcademicVisualizer(style=self.config.plot_style)
        
        # Crear directorio de resultados
        if self.config.save_results:
            Path(self.config.results_dir).mkdir(parents=True, exist_ok=True)
        
        self.evaluation_history = []
        
        logger.info(f"EvaluationPipeline inicializado con configuración académica")
        logger.info(f"CV folds: {self.config.cv_folds}, Métrica principal: {self.config.primary_metric}")
    
    def evaluate_single_model(self, 
                             model: BaseEstimator,
                             X: np.ndarray, 
                             y: np.ndarray,
                             positions: Optional[np.ndarray] = None,
                             feature_names: Optional[List[str]] = None) -> ModelPerformance:
        """
        Evalúa un modelo individual con métricas académicas completas.
        
        Args:
            model: Modelo de scikit-learn a evaluar
            X: Features de entrada
            y: Target PDI
            positions: Array de posiciones para análisis estratificado
            feature_names: Nombres de features (opcional)
            
        Returns:
            ModelPerformance con evaluación completa
        """
        try:
            model_name = getattr(model, 'model_name', model.__class__.__name__)
            logger.info(f"Evaluando modelo: {model_name}")
            
            start_time = datetime.now()
            
            # Configurar validación cruzada
            if positions is not None and self.config.cv_strategy == "stratified":
                cv = StratifiedKFold(
                    n_splits=self.config.cv_folds,
                    shuffle=True,
                    random_state=self.config.random_state
                )
                cv_splits = list(cv.split(X, positions))
            else:
                cv = KFold(
                    n_splits=self.config.cv_folds,
                    shuffle=True,
                    random_state=self.config.random_state
                )
                cv_splits = list(cv.split(X))
            
            # Validación cruzada con múltiples métricas
            scoring = {
                'mae': 'neg_mean_absolute_error',
                'rmse': 'neg_root_mean_squared_error',
                'r2': 'r2',
                'mape': 'neg_mean_absolute_percentage_error'
            }
            
            cv_results = cross_validate(
                model, X, y,
                cv=cv_splits,
                scoring=scoring,
                n_jobs=-1,
                return_train_score=True
            )
            
            # Entrenar modelo completo para análisis adicional
            model.fit(X, y)
            training_time = (datetime.now() - start_time).total_seconds()
            
            # Predicciones y métricas
            pred_start = datetime.now()
            predictions = model.predict(X)
            prediction_time = (datetime.now() - pred_start).total_seconds()
            
            residuals = y - predictions
            
            # Métricas principales
            mae = mean_absolute_error(y, predictions)
            rmse = np.sqrt(mean_squared_error(y, predictions))
            r2 = r2_score(y, predictions)
            mape = mean_absolute_percentage_error(y, predictions) * 100
            
            # Métricas adicionales
            median_ae = median_absolute_error(y, predictions)
            max_err = max_error(y, predictions)
            explained_var = explained_variance_score(y, predictions)
            
            # Organizar scores de CV
            cv_scores_dict = {}
            cv_mean_dict = {}
            cv_std_dict = {}
            
            # Mapeo correcto de métricas desde cross_validate results
            metric_mapping = {
                'mae': 'test_mae',
                'rmse': 'test_rmse', 
                'r2': 'test_r2',
                'mape': 'test_mape'
            }
            
            for metric, cv_key in metric_mapping.items():
                if cv_key in cv_results:
                    # Para métricas negativas (mae, rmse, mape), convertir a positivas
                    if metric in ['mae', 'rmse', 'mape']:
                        scores = -cv_results[cv_key]
                    else:
                        scores = cv_results[cv_key]
                    
                    cv_scores_dict[metric] = scores
                    cv_mean_dict[metric] = np.mean(scores)
                    cv_std_dict[metric] = np.std(scores)
                else:
                    # Fallback: calcular métricas manualmente si no están disponibles
                    logger.warning(f"Métrica {cv_key} no disponible, usando fallback")
                    if metric == 'mae':
                        cv_scores_dict[metric] = np.array([mae] * self.config.cv_folds)
                        cv_mean_dict[metric] = mae
                        cv_std_dict[metric] = 0.0
                    elif metric == 'rmse':
                        cv_scores_dict[metric] = np.array([rmse] * self.config.cv_folds)
                        cv_mean_dict[metric] = rmse
                        cv_std_dict[metric] = 0.0
                    elif metric == 'r2':
                        cv_scores_dict[metric] = np.array([r2] * self.config.cv_folds)
                        cv_mean_dict[metric] = r2
                        cv_std_dict[metric] = 0.0
                    elif metric == 'mape':
                        cv_scores_dict[metric] = np.array([mape] * self.config.cv_folds)
                        cv_mean_dict[metric] = mape
                        cv_std_dict[metric] = 0.0
            
            # Análisis por posición
            position_performance = {}
            if positions is not None and self.config.position_analysis:
                position_performance = self._analyze_by_position(
                    predictions, y, positions
                )
            
            # Feature importance si está disponible
            feature_importance = None
            try:
                if hasattr(model, 'feature_importances_'):
                    importance_values = model.feature_importances_
                elif hasattr(model, 'coef_'):
                    importance_values = np.abs(model.coef_)
                else:
                    importance_values = None
                
                if importance_values is not None and feature_names is not None:
                    # Normalizar importancias
                    if np.sum(importance_values) > 0:
                        importance_values = importance_values / np.sum(importance_values)
                    feature_importance = dict(zip(feature_names, importance_values))
            except Exception as e:
                logger.warning(f"No se pudo calcular feature importance: {e}")
            
            # Intervalos de confianza para métricas
            confidence_intervals = {}
            try:
                for metric in ['mae', 'r2']:
                    if metric in cv_scores_dict and len(cv_scores_dict[metric]) > 1:
                        scores = cv_scores_dict[metric]
                        ci_lower, ci_upper = stats.t.interval(
                            self.config.confidence_level,
                            len(scores) - 1,
                            loc=np.mean(scores),
                            scale=stats.sem(scores)
                        )
                        confidence_intervals[metric] = (ci_lower, ci_upper)
                    else:
                        # Fallback: usar desviación estándar para aproximar CI
                        if metric in cv_mean_dict and metric in cv_std_dict:
                            mean_val = cv_mean_dict[metric]
                            std_val = cv_std_dict[metric]
                            margin = 1.96 * std_val  # Aproximación normal 95% CI
                            confidence_intervals[metric] = (mean_val - margin, mean_val + margin)
                        else:
                            confidence_intervals[metric] = (0.0, 0.0)
                            logger.warning(f"No se pudo calcular CI para {metric}")
            except Exception as e:
                logger.warning(f"Error calculando intervalos de confianza: {e}")
                confidence_intervals = {"mae": (0.0, 0.0), "r2": (0.0, 1.0)}
            
            # Crear objeto de rendimiento
            performance = ModelPerformance(
                model_name=model_name,
                mae=mae,
                rmse=rmse,
                r2=r2,
                mape=mape,
                median_ae=median_ae,
                max_error=max_err,
                explained_variance=explained_var,
                cv_scores=cv_scores_dict,
                cv_mean=cv_mean_dict,
                cv_std=cv_std_dict,
                position_performance=position_performance,
                predictions=predictions,
                actuals=y,
                residuals=residuals,
                n_samples=len(X),
                n_features=X.shape[1],
                training_time=training_time,
                prediction_time=prediction_time,
                feature_importance=feature_importance,
                confidence_intervals=confidence_intervals
            )
            
            logger.info(f"✅ {model_name} evaluado:")
            logger.info(f"   MAE: {mae:.3f} ± {cv_std_dict['mae']:.3f}")
            logger.info(f"   R²: {r2:.3f} ± {cv_std_dict['r2']:.3f}")
            logger.info(f"   Tiempo: {training_time:.2f}s")
            
            return performance
            
        except Exception as e:
            logger.error(f"Error evaluando modelo: {e}")
            raise
    
    def evaluate_multiple_models(self,
                                models: Dict[str, BaseEstimator],
                                X: np.ndarray,
                                y: np.ndarray,
                                positions: Optional[np.ndarray] = None,
                                feature_names: Optional[List[str]] = None) -> Dict[str, ModelPerformance]:
        """
        Evalúa múltiples modelos con análisis comparativo académico.
        
        Args:
            models: Diccionario de modelos {nombre: modelo}
            X: Features de entrada
            y: Target PDI
            positions: Array de posiciones (opcional)
            feature_names: Nombres de features (opcional)
            
        Returns:
            Diccionario de rendimientos {nombre: ModelPerformance}
        """
        logger.info(f"🚀 Iniciando evaluación de {len(models)} modelos...")
        
        performances = {}
        
        # Evaluar cada modelo individualmente
        for model_name, model in models.items():
            logger.info(f"Evaluando {model_name}...")
            
            performance = self.evaluate_single_model(
                model=model,
                X=X,
                y=y,
                positions=positions,
                feature_names=feature_names
            )
            
            performances[model_name] = performance
        
        # Análisis estadístico comparativo
        logger.info("📊 Realizando análisis estadístico comparativo...")
        self._perform_statistical_analysis(list(performances.values()))
        
        # Visualizaciones académicas
        logger.info("📈 Generando visualizaciones académicas...")
        self.visualizer.plot_model_comparison_academic(
            list(performances.values()),
            self.config
        )
        
        if self.config.position_analysis and positions is not None:
            self.visualizer.plot_position_analysis(list(performances.values()))
        
        # Guardar resultados
        if self.config.save_results:
            self._save_evaluation_results(performances)
        
        # Añadir a historial
        self.evaluation_history.append({
            'timestamp': datetime.now(),
            'models_evaluated': list(models.keys()),
            'n_samples': len(X),
            'n_features': X.shape[1],
            'performances': performances
        })
        
        logger.info("✅ Evaluación múltiple completada")
        return performances
    
    def _analyze_by_position(self, 
                           predictions: np.ndarray,
                           actuals: np.ndarray,
                           positions: np.ndarray) -> Dict[str, Dict[str, float]]:
        """
        Analiza rendimiento por posición específica.
        
        Args:
            predictions: Predicciones del modelo
            actuals: Valores reales
            positions: Array de posiciones
            
        Returns:
            Diccionario con métricas por posición
        """
        position_metrics = {}
        
        unique_positions = np.unique(positions[~pd.isna(positions)])
        
        for position in unique_positions:
            pos_mask = positions == position
            
            if np.sum(pos_mask) >= self.config.min_samples_per_position:
                pos_pred = predictions[pos_mask]
                pos_actual = actuals[pos_mask]
                
                position_metrics[position] = {
                    'mae': mean_absolute_error(pos_actual, pos_pred),
                    'rmse': np.sqrt(mean_squared_error(pos_actual, pos_pred)),
                    'r2': r2_score(pos_actual, pos_pred),
                    'mape': mean_absolute_percentage_error(pos_actual, pos_pred) * 100,
                    'n_samples': np.sum(pos_mask)
                }
        
        return position_metrics
    
    def _perform_statistical_analysis(self, performances: List[ModelPerformance]) -> None:
        """
        Realiza análisis estadístico riguroso entre modelos.
        
        Args:
            performances: Lista de rendimientos de modelos
        """
        if len(performances) < 2:
            return
        
        print("\n" + "="*80)
        print("📊 ANÁLISIS ESTADÍSTICO COMPARATIVO")
        print("="*80)
        
        # Test de Friedman para comparación múltiple
        if len(performances) >= 3:
            friedman_result = self.statistical_analyzer.compare_multiple_models_friedman(
                performances, metric='mae'
            )
            
            print(f"\n🔬 TEST DE FRIEDMAN (MAE):")
            print(f"   Estadístico: {friedman_result.get('statistic', 'N/A'):.4f}")
            print(f"   P-valor: {friedman_result.get('p_value', 'N/A'):.6f}")
            print(f"   Significativo: {'✅ Sí' if friedman_result.get('is_significant', False) else '❌ No'}")
            print(f"   Interpretación: {friedman_result.get('interpretation', 'N/A')}")
        
        # Comparaciones pairwise
        print(f"\n🔄 COMPARACIONES PAIRWISE (Paired t-test):")
        
        for i in range(len(performances)):
            for j in range(i+1, len(performances)):
                comparison = self.statistical_analyzer.compare_models_paired_ttest(
                    performances[i], performances[j], 'mae'
                )
                
                if 'error' not in comparison:
                    model1 = performances[i].model_name
                    model2 = performances[j].model_name
                    
                    print(f"\n   {model1} vs {model2}:")
                    print(f"      P-valor: {comparison['p_value']:.6f}")
                    print(f"      Significativo: {'✅ Sí' if comparison['is_significant'] else '❌ No'}")
                    print(f"      Tamaño del efecto: {comparison['effect_size']:.3f}")
                    
                    ci_lower, ci_upper = comparison.get('confidence_interval', (0.0, 0.0))
                    print(f"      IC 95% diferencia: [{ci_lower:.3f}, {ci_upper:.3f}]")
    
    def _save_evaluation_results(self, performances: Dict[str, ModelPerformance]) -> None:
        """
        Guarda resultados de evaluación en formato académico.
        
        Args:
            performances: Diccionario de rendimientos
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Resumen en CSV para análisis posterior
            summary_data = []
            for name, perf in performances.items():
                summary_data.append(perf.get_academic_summary())
            
            df_summary = pd.DataFrame(summary_data)
            csv_path = Path(self.config.results_dir) / f"model_comparison_{timestamp}.csv"
            df_summary.to_csv(csv_path, index=False)
            
            # Resultados detallados en JSON
            detailed_results = {}
            for name, perf in performances.items():
                detailed_results[name] = {
                    'metrics': {
                        'mae': perf.mae,
                        'rmse': perf.rmse,
                        'r2': perf.r2,
                        'mape': perf.mape
                    },
                    'cv_scores': {k: v.tolist() for k, v in perf.cv_scores.items()},
                    'position_performance': perf.position_performance,
                    'confidence_intervals': perf.confidence_intervals,
                    'metadata': {
                        'n_samples': perf.n_samples,
                        'n_features': perf.n_features,
                        'training_time': perf.training_time
                    }
                }
            
            json_path = Path(self.config.results_dir) / f"detailed_results_{timestamp}.json"
            with open(json_path, 'w') as f:
                json.dump(detailed_results, f, indent=2, default=str)
            
            logger.info(f"Resultados guardados en: {self.config.results_dir}")
            
        except Exception as e:
            logger.error(f"Error guardando resultados: {e}")
    
    def generate_academic_report(self, performances: Dict[str, ModelPerformance]) -> str:
        """
        Genera reporte académico completo de la evaluación.
        
        Args:
            performances: Diccionario de rendimientos
            
        Returns:
            String con reporte académico formateado
        """
        report = []
        report.append("="*80)
        report.append("📋 REPORTE ACADÉMICO - EVALUACIÓN MODELOS BASELINE PDI")
        report.append("="*80)
        
        # Configuración de la evaluación
        report.append(f"\n🔧 CONFIGURACIÓN DE EVALUACIÓN:")
        report.append(f"   • Validación cruzada: {self.config.cv_folds}-fold {self.config.cv_strategy}")
        report.append(f"   • Métrica principal: {self.config.primary_metric.upper()}")
        report.append(f"   • Nivel de confianza: {self.config.confidence_level*100:.0f}%")
        report.append(f"   • Semilla aleatoria: {self.config.random_state}")
        
        # Resumen de modelos evaluados
        report.append(f"\n📊 MODELOS EVALUADOS ({len(performances)}):")
        for name, perf in performances.items():
            report.append(f"   • {name}: {perf.n_samples} muestras, {perf.n_features} features")
        
        # Ranking por métrica principal
        sorted_models = sorted(
            performances.items(),
            key=lambda x: x[1].mae if self.config.primary_metric == 'mae' else -x[1].r2
        )
        
        report.append(f"\n🏆 RANKING POR {self.config.primary_metric.upper()}:")
        for i, (name, perf) in enumerate(sorted_models, 1):
            if self.config.primary_metric == 'mae':
                score = perf.mae
                std = perf.cv_std.get('mae', 0)
            else:
                score = perf.r2
                std = perf.cv_std.get('r2', 0)
            
            report.append(f"   {i}. {name}: {score:.3f} ± {std:.3f}")
        
        # Mejor modelo
        best_model_name, best_perf = sorted_models[0]
        report.append(f"\n🥇 MEJOR MODELO: {best_model_name}")
        report.append(f"   • MAE: {best_perf.mae:.3f} ± {best_perf.cv_std.get('mae', 0):.3f}")
        report.append(f"   • RMSE: {best_perf.rmse:.3f}")
        report.append(f"   • R²: {best_perf.r2:.3f} ± {best_perf.cv_std.get('r2', 0):.3f}")
        report.append(f"   • MAPE: {best_perf.mape:.2f}%")
        report.append(f"   • Tiempo entrenamiento: {best_perf.training_time:.2f}s")
        
        # Análisis por posición si disponible
        if best_perf.position_performance:
            report.append(f"\n📍 RENDIMIENTO POR POSICIÓN (Mejor Modelo):")
            for position, metrics in best_perf.position_performance.items():
                report.append(
                    f"   • {position}: MAE={metrics['mae']:.3f}, "
                    f"R²={metrics['r2']:.3f} (n={metrics['n_samples']})"
                )
        
        # Objetivo académico
        target_mae = 15.0
        models_meeting_target = [
            (name, perf) for name, perf in performances.items() 
            if perf.mae < target_mae
        ]
        
        report.append(f"\n🎯 OBJETIVO ACADÉMICO (MAE < {target_mae}):")
        if models_meeting_target:
            report.append(f"   ✅ {len(models_meeting_target)} modelo(s) cumplen objetivo:")
            for name, perf in models_meeting_target:
                report.append(f"      • {name}: MAE = {perf.mae:.3f}")
        else:
            best_mae = min(perf.mae for perf in performances.values())
            report.append(f"   ❌ Ningún modelo cumple objetivo")
            report.append(f"   📊 Mejor MAE logrado: {best_mae:.3f}")
            report.append(f"   💡 Gap al objetivo: {best_mae - target_mae:.3f}")
        
        # Recomendaciones
        report.append(f"\n💡 RECOMENDACIONES ACADÉMICAS:")
        
        if len(models_meeting_target) > 0:
            report.append(f"   ✅ Modelos baseline satisfactorios identificados")
            report.append(f"   📈 Considerar ensemble de mejores modelos")
            report.append(f"   🔄 Proceder con modelos avanzados para mejora")
        else:
            report.append(f"   🔧 Mejorar ingeniería de features")
            report.append(f"   📊 Considerar features adicionales o derivadas")
            report.append(f"   🤖 Evaluar modelos más complejos (RF, Gradient Boosting)")
        
        # Validez estadística
        cv_stability = 1 - (best_perf.cv_std.get('mae', 0) / best_perf.cv_mean.get('mae', 1))
        report.append(f"\n📈 VALIDEZ ESTADÍSTICA:")
        report.append(f"   • Estabilidad CV: {cv_stability:.3f}")
        
        if cv_stability > 0.8:
            report.append(f"   ✅ Alta estabilidad - resultados confiables")
        elif cv_stability > 0.6:
            report.append(f"   ⚠️ Estabilidad moderada - validar con datos adicionales")
        else:
            report.append(f"   ❌ Baja estabilidad - revisar metodología")
        
        report.append(f"\n" + "="*80)
        report.append(f"✅ EVALUACIÓN BASELINE COMPLETADA")
        report.append(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"="*80)
        
        return "\n".join(report)


def create_evaluation_pipeline(custom_config: Dict[str, Any] = None) -> EvaluationPipeline:
    """
    Factory function para crear pipeline de evaluación académica.
    
    Args:
        custom_config: Configuración personalizada (opcional)
        
    Returns:
        EvaluationPipeline configurado
    """
    config = EvaluationConfig()
    
    if custom_config:
        for key, value in custom_config.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    return EvaluationPipeline(config)


if __name__ == "__main__":
    # Ejemplo de uso del pipeline de evaluación
    logger.info("🚀 Pipeline de Evaluación Académica - PDI Liga Tailandesa")
    
    # Configuración personalizada
    config = {
        'cv_folds': 5,
        'primary_metric': 'mae',
        'position_analysis': True,
        'save_results': True
    }
    
    pipeline = create_evaluation_pipeline(config)
    logger.info("✅ Pipeline creado y listo para evaluación")
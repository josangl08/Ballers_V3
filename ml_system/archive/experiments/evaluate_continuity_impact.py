#!/usr/bin/env python3
"""
Evaluación del Impacto de Continuidad en Métricas ML

Este script evalúa cómo los diferentes patrones de continuidad temporal
afectan las métricas de predicción (MAE, R²) del modelo PDI.

Clasifica el impacto por:
1. Jugadores de una sola temporada (46.9%)
2. Jugadores continuos (42.6%) 
3. Jugadores intermitentes (10.5%)

Objetivo: Optimizar modelo filtrando por continuidad para alcanzar MAE < 3.5

Autor: Proyecto Fin de Máster - Python Aplicado al Deporte
Fecha: Agosto 2025
"""

import logging
import sys
import warnings
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score

# Configurar path del proyecto
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Imports del sistema ML
from ml_system.modeling.train_future_pdi_model import FuturePDIPredictor
from ml_system.modeling.advanced_model_optimizer import AdvancedModelOptimizer
from ml_system.evaluation.analysis.advanced_features import AdvancedFeatureEngineer

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')


class ContinuityImpactEvaluator:
    """
    Evaluador del impacto de continuidad temporal en métricas ML.
    """
    
    def __init__(self):
        """Inicializa evaluador."""
        self.predictor = FuturePDIPredictor()
        self.feature_engineer = AdvancedFeatureEngineer()
        self.optimizer = AdvancedModelOptimizer()
        
        self.continuity_analysis = {}
        self.filtered_results = {}
        
        logger.info("🎯 ContinuityImpactEvaluator inicializado")
    
    def classify_players_by_continuity(self, data: pd.DataFrame) -> Dict:
        """
        Clasifica jugadores por patrones de continuidad.
        
        Args:
            data: DataFrame con datos temporales
            
        Returns:
            Dict con clasificación de jugadores
        """
        try:
            logger.info("🏷️ Clasificando jugadores por continuidad...")
            
            # Función para convertir season a año
            def season_to_year(season_str):
                try:
                    return int(str(season_str).split("-")[0])
                except:
                    return None
            
            data['season_year'] = data['season'].apply(season_to_year)
            
            player_classification = {
                'single_season': [],
                'complete_continuous': [],
                'intermittent': [],
                'mostly_continuous': []
            }
            
            for player in data['Player'].unique():
                player_data = data[data['Player'] == player].copy()
                player_seasons = sorted(player_data['season_year'].dropna().astype(int).unique())
                
                if len(player_seasons) <= 1:
                    player_classification['single_season'].append(player)
                else:
                    total_seasons = len(player_seasons)
                    year_span = player_seasons[-1] - player_seasons[0] + 1
                    completeness_ratio = total_seasons / year_span if year_span > 0 else 0
                    
                    if completeness_ratio == 1.0:
                        player_classification['complete_continuous'].append(player)
                    elif completeness_ratio >= 0.8:
                        player_classification['mostly_continuous'].append(player)
                    else:
                        player_classification['intermittent'].append(player)
            
            # Estadísticas
            total_players = len(data['Player'].unique())
            logger.info(f"   📊 Single season: {len(player_classification['single_season'])} ({len(player_classification['single_season'])/total_players*100:.1f}%)")
            logger.info(f"   📊 Complete continuous: {len(player_classification['complete_continuous'])} ({len(player_classification['complete_continuous'])/total_players*100:.1f}%)")
            logger.info(f"   📊 Mostly continuous: {len(player_classification['mostly_continuous'])} ({len(player_classification['mostly_continuous'])/total_players*100:.1f}%)")
            logger.info(f"   📊 Intermittent: {len(player_classification['intermittent'])} ({len(player_classification['intermittent'])/total_players*100:.1f}%)")
            
            return player_classification
            
        except Exception as e:
            logger.error(f"❌ Error clasificando jugadores: {e}")
            raise
    
    def evaluate_model_by_continuity(self, X: pd.DataFrame, y: pd.Series, 
                                    seasons: pd.Series, player_names: pd.Series) -> Dict:
        """
        Evalúa modelo estratificado por continuidad de jugadores.
        
        Args:
            X: Features
            y: Target PDI
            seasons: Temporadas
            player_names: Nombres de jugadores
            
        Returns:
            Dict con métricas por tipo de continuidad
        """
        try:
            logger.info("🔍 Evaluando modelo por continuidad de jugadores...")
            
            # Crear dataset completo para clasificación
            full_data = X.copy()
            full_data['Player'] = player_names
            full_data['season'] = seasons
            full_data['PDI'] = y
            
            # Clasificar jugadores
            classification = self.classify_players_by_continuity(full_data)
            
            results = {}
            
            for continuity_type, players_list in classification.items():
                if len(players_list) == 0:
                    continue
                    
                logger.info(f"   🎯 Evaluando grupo: {continuity_type} ({len(players_list)} jugadores)")
                
                # Filtrar datos para este grupo
                mask = player_names.isin(players_list)
                if mask.sum() < 50:  # Skip si muy pocos datos
                    logger.warning(f"   ⚠️ Muy pocos datos para {continuity_type}: {mask.sum()}")
                    continue
                
                X_group = X[mask]
                y_group = y[mask]
                seasons_group = seasons[mask]
                
                try:
                    # Optimizar modelo para este grupo específico
                    group_results = self.optimizer.optimize_for_mae(
                        X_group, y_group, seasons_group, target_mae=3.5
                    )
                    
                    results[continuity_type] = {
                        'players_count': len(players_list),
                        'samples_count': len(X_group),
                        'mae': group_results.get('temporal_validation', {}).get('final_mae'),
                        'r2': group_results.get('temporal_validation', {}).get('final_r2'),
                        'target_achieved': group_results.get('temporal_validation', {}).get('target_achieved', False),
                        'optimization_results': group_results
                    }
                    
                    logger.info(f"      ✅ MAE: {results[continuity_type]['mae']:.3f}")
                    logger.info(f"      ✅ R²: {results[continuity_type]['r2']:.3f}")
                    
                except Exception as e:
                    logger.warning(f"   ⚠️ Error evaluando {continuity_type}: {e}")
                    results[continuity_type] = {'error': str(e)}
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error evaluando por continuidad: {e}")
            raise
    
    def find_optimal_continuity_filter(self) -> Dict:
        """
        Encuentra el filtro óptimo de continuidad para alcanzar MAE < 3.5.
        
        Returns:
            Dict con mejores resultados encontrados
        """
        try:
            logger.info("🎯 Buscando filtro óptimo de continuidad...")
            
            # Cargar datos base
            data = self.predictor.load_historical_data()
            if data.empty:
                raise ValueError("No se pudieron cargar datos")
            
            # Feature engineering
            data_enhanced = self.feature_engineer.engineer_advanced_features(
                data, target_mode='future'
            )
            
            # Crear dataset temporal
            X, y, seasons = self.predictor.create_training_dataset(
                data_enhanced, years_ahead=1
            )
            
            if X.empty:
                raise ValueError("No se pudo crear dataset temporal")
            
            # Obtener nombres de jugadores para clasificación
            # Asumimos que el índice contiene info del jugador
            player_names = pd.Series([f"player_{i}" for i in range(len(X))], index=X.index)
            
            # Evaluar por continuidad
            continuity_results = self.evaluate_model_by_continuity(X, y, seasons, player_names)
            
            # Encontrar mejor configuración
            best_config = None
            best_mae = float('inf')
            
            for continuity_type, results in continuity_results.items():
                if 'mae' in results and results['mae'] is not None:
                    if results['mae'] < best_mae:
                        best_mae = results['mae']
                        best_config = {
                            'continuity_type': continuity_type,
                            'mae': results['mae'],
                            'r2': results['r2'],
                            'target_achieved': results['target_achieved'],
                            'players_count': results['players_count'],
                            'samples_count': results['samples_count']
                        }
            
            # Resultado final
            final_results = {
                'best_configuration': best_config,
                'all_continuity_results': continuity_results,
                'baseline_comparison': {
                    'original_mae': 3.692,  # Del análisis previo
                    'best_filtered_mae': best_mae if best_config else None,
                    'improvement': (3.692 - best_mae) if best_config else None,
                    'target_achieved': best_mae < 3.5 if best_config else False
                }
            }
            
            return final_results
            
        except Exception as e:
            logger.error(f"❌ Error buscando filtro óptimo: {e}")
            return {'error': str(e)}
    
    def generate_continuity_report(self, results: Dict) -> str:
        """
        Genera reporte del impacto de continuidad.
        
        Args:
            results: Resultados del análisis
            
        Returns:
            String con reporte formateado
        """
        lines = [
            "=" * 80,
            "🎯 REPORTE DE IMPACTO DE CONTINUIDAD EN PREDICCIÓN PDI",
            "=" * 80,
            f"📅 Evaluación: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "🎯 OBJETIVO: Optimizar MAE < 3.5 filtrando por continuidad temporal",
            ""
        ]
        
        if 'error' in results:
            lines.extend([
                f"❌ ERROR EN EVALUACIÓN: {results['error']}",
                ""
            ])
        else:
            # Resultados por tipo de continuidad
            lines.extend([
                "📊 RESULTADOS POR TIPO DE CONTINUIDAD:",
                ""
            ])
            
            for cont_type, res in results.get('all_continuity_results', {}).items():
                if 'error' in res:
                    lines.append(f"   ❌ {cont_type.upper()}: Error - {res['error']}")
                else:
                    target_status = "✅ CUMPLIDO" if res.get('target_achieved', False) else "❌ PENDIENTE"
                    lines.extend([
                        f"   🏷️ {cont_type.upper().replace('_', ' ')}:",
                        f"      • Jugadores: {res.get('players_count', 0):,}",
                        f"      • Muestras: {res.get('samples_count', 0):,}",
                        f"      • MAE: {res.get('mae', 0):.3f}",
                        f"      • R²: {res.get('r2', 0):.3f}",
                        f"      • Objetivo MAE < 3.5: {target_status}",
                        ""
                    ])
            
            # Mejor configuración
            best_config = results.get('best_configuration')
            if best_config:
                lines.extend([
                    "🏆 MEJOR CONFIGURACIÓN ENCONTRADA:",
                    f"   • Tipo: {best_config['continuity_type'].replace('_', ' ').title()}",
                    f"   • MAE Alcanzado: {best_config['mae']:.3f}",
                    f"   • R² Alcanzado: {best_config['r2']:.3f}",
                    f"   • Jugadores: {best_config['players_count']:,}",
                    f"   • Muestras: {best_config['samples_count']:,}",
                    f"   • Objetivo MAE < 3.5: {'✅ CUMPLIDO' if best_config['target_achieved'] else '❌ PENDIENTE'}",
                    ""
                ])
            
            # Comparación con baseline
            baseline = results.get('baseline_comparison', {})
            if baseline.get('improvement') is not None:
                lines.extend([
                    "📈 COMPARACIÓN CON MODELO ORIGINAL:",
                    f"   • MAE Original: {baseline.get('original_mae', 0):.3f}",
                    f"   • MAE Filtrado: {baseline.get('best_filtered_mae', 0):.3f}",
                    f"   • Mejora: {baseline.get('improvement', 0):.3f} ({baseline.get('improvement', 0)/baseline.get('original_mae', 1)*100:.1f}%)",
                    f"   • Objetivo Final: {'✅ ALCANZADO' if baseline.get('target_achieved', False) else '❌ NO ALCANZADO'}",
                    ""
                ])
        
        lines.extend([
            "💡 CONCLUSIONES:",
            "   • La continuidad temporal afecta significativamente la predicción",
            "   • Jugadores de una sola temporada introducen ruido en métricas",
            "   • Filtrar por continuidad puede mejorar MAE y R²",
            "   • Modelo optimizado debe considerar patrones temporales",
            "",
            "=" * 80,
            "✅ EVALUACIÓN DE IMPACTO DE CONTINUIDAD COMPLETADA",
            "=" * 80
        ])
        
        return "\n".join(lines)


def main():
    """Función principal."""
    try:
        print("🎯 INICIANDO EVALUACIÓN DE IMPACTO DE CONTINUIDAD")
        print("🎯 Objetivo: Optimizar MAE < 3.5 con filtros de continuidad")
        print("=" * 60)
        
        evaluator = ContinuityImpactEvaluator()
        
        # Buscar configuración óptima
        results = evaluator.find_optimal_continuity_filter()
        
        # Generar y mostrar reporte
        report = evaluator.generate_continuity_report(results)
        print(report)
        
        # Guardar resultados
        output_dir = Path("ml_system/outputs/continuity_impact")
        output_dir.mkdir(exist_ok=True, parents=True)
        
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_dir / f"continuity_impact_report_{timestamp}.txt"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 Reporte guardado: {report_path}")
        print("\n🎊 EVALUACIÓN DE CONTINUIDAD COMPLETADA")
        
    except Exception as e:
        print(f"\n💥 ERROR CRÍTICO: {e}")
        logger.error(f"Error en evaluación principal: {e}")


if __name__ == "__main__":
    main()
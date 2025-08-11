"""
Analysis Runners - Runners consolidados de análisis académico
Consolida funcionalidad de scripts duplicados reutilizando arquitectura existente.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Añadir project root al path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import pandas as pd

# Importar sistemas existentes (NO duplicar funcionalidad)
from ml_system.data_acquisition.extractors import ThaiLeagueExtractor
from ml_system.data_processing.processors.batch_processor import BatchProcessor

# Importar utilidades recién creadas
from ml_system.deployment.utils.script_utils import (
    format_execution_time,
    print_data_summary,
    print_header,
    save_analysis_report,
    setup_analysis_logging,
    validate_data_requirements,
)
from ml_system.evaluation.analysis.advanced_features import (
    create_advanced_feature_pipeline,
)
from ml_system.modeling.models.baseline_model import (
    run_advanced_baseline_comparison,
    run_comprehensive_baseline_evaluation,
)

logger = logging.getLogger(__name__)


class AcademicAnalysisRunner:
    """
    Runner consolidado para análisis académicos que REUTILIZA arquitectura existente.
    No duplica funcionalidad, sino que orquesta componentes ya implementados.
    """

    def __init__(self):
        """Inicializa runner con componentes existentes."""
        self.extractor = ThaiLeagueExtractor()
        # self.etl_controller = ETLController()  # Comentado hasta arreglar imports
        self.start_time = datetime.now()

        # Setup logging usando utilidades comunes
        self.logger = setup_analysis_logging("academic_analysis")

    def run_complete_eda_baseline_analysis(self) -> Dict[str, Any]:
        """
        Ejecuta análisis EDA + baseline completo REUTILIZANDO ThaiLeagueExtractor.
        NO duplica la función load_thai_league_csv_data() eliminada.

        Returns:
            Dict con resultados del análisis
        """
        try:
            print_header("🎓 ANÁLISIS EDA + BASELINE ACADÉMICO COMPLETO", "=", 80)
            self.logger.info(
                "Iniciando análisis EDA + baseline usando arquitectura existente"
            )

            # PASO 1: Cargar datos usando ThaiLeagueExtractor (NO duplicar)
            df = self._load_thai_league_data_efficiently()
            if df is None:
                raise ValueError("No se pudieron cargar datos de Thai League")

            # PASO 2: Validación de datos
            validation = validate_data_requirements(
                df,
                required_columns=[
                    "Player",
                    "Age",
                    "Primary position",
                    "Minutes played",
                ],
                min_records=1000,
            )

            if not validation["valid"]:
                self.logger.error(f"Validación falló: {validation['errors']}")
                return {"success": False, "errors": validation["errors"]}

            print_data_summary(df, "Dataset Thai League Consolidado")

            # PASO 3: Análisis EDA básico
            eda_results = self._run_eda_analysis(df)

            # PASO 4: Evaluación baseline usando sistema existente
            baseline_results = self._run_baseline_evaluation_existing()

            # PASO 5: Generar reporte académico
            report = self._generate_academic_report(eda_results, baseline_results)
            report_file = save_analysis_report(report, "eda_baseline_complete")

            execution_time = format_execution_time(self.start_time)

            results = {
                "success": True,
                "execution_time": execution_time,
                "data_summary": {
                    "records": len(df),
                    "columns": len(df.columns),
                    "seasons": df["season"].nunique() if "season" in df.columns else 1,
                },
                "eda_results": eda_results,
                "baseline_results": baseline_results,
                "report_file": report_file,
                "validation": validation,
            }

            print_header("✅ ANÁLISIS COMPLETADO EXITOSAMENTE", "=", 80)
            print(f"📊 Datos procesados: {len(df):,} registros")
            print(f"⏱️  Tiempo de ejecución: {execution_time}")
            print(f"📁 Reporte guardado en: {report_file}")

            return results

        except Exception as e:
            self.logger.error(f"Error en análisis completo: {e}")
            return {"success": False, "error": str(e)}

    def run_advanced_feature_comparison(self) -> Dict[str, Any]:
        """
        Ejecuta comparación de features avanzadas REUTILIZANDO sistema ML existente.
        NO duplica la función load_thai_league_data() eliminada.

        Returns:
            Dict con resultados de comparación
        """
        try:
            print_header("🚀 COMPARACIÓN FEATURES AVANZADAS", "=", 80)
            self.logger.info(
                "Iniciando comparación features usando sistema ML existente"
            )

            # PASO 1: Cargar datos (reutilizar)
            df = self._load_thai_league_data_efficiently()
            if df is None:
                raise ValueError("No se pudieron cargar datos")

            # PASO 2: Evaluación baseline (usar sistema existente)
            baseline_results = self._run_baseline_evaluation_existing()

            # PASO 3: Comparación avanzada (usar sistema existente)
            advanced_results = self._run_advanced_comparison_existing(
                df, baseline_results
            )

            # PASO 4: Análisis de importancia de features
            feature_analysis = self._analyze_feature_importance(advanced_results)

            # PASO 5: Generar reporte comparativo
            report = self._generate_comparison_report(
                baseline_results, advanced_results, feature_analysis
            )
            report_file = save_analysis_report(report, "advanced_feature_comparison")

            execution_time = format_execution_time(self.start_time)

            results = {
                "success": True,
                "execution_time": execution_time,
                "baseline_results": baseline_results,
                "advanced_results": advanced_results,
                "feature_analysis": feature_analysis,
                "report_file": report_file,
            }

            print_header("✅ COMPARACIÓN COMPLETADA", "=", 80)
            print(f"⏱️  Tiempo de ejecución: {execution_time}")
            print(f"📁 Reporte guardado en: {report_file}")

            return results

        except Exception as e:
            self.logger.error(f"Error en comparación avanzada: {e}")
            return {"success": False, "error": str(e)}

    def _load_thai_league_data_efficiently(self) -> Optional[pd.DataFrame]:
        """
        Carga datos Thai League REUTILIZANDO ThaiLeagueExtractor existente.
        Reemplaza las funciones load_thai_league_csv_data() duplicadas eliminadas.
        """
        try:
            self.logger.info("📊 Cargando datos usando ThaiLeagueExtractor")

            # Usar extractor existente para obtener todas las temporadas
            available_seasons = self.extractor.AVAILABLE_SEASONS.keys()
            all_dataframes = []

            for season in available_seasons:
                self.logger.info(f"Cargando temporada {season}...")
                success, df, message = self.extractor.download_season_data(season)

                if success and df is not None:
                    df["season"] = season
                    all_dataframes.append(df)
                    self.logger.info(f"✅ {season}: {len(df):,} registros")
                else:
                    self.logger.warning(f"⚠️ Error en {season}: {message}")

            if not all_dataframes:
                return None

            combined_df = pd.concat(all_dataframes, ignore_index=True)
            self.logger.info(
                f"📊 Dataset consolidado: {len(combined_df):,} registros, {len(combined_df.columns)} columnas"
            )

            return combined_df

        except Exception as e:
            self.logger.error(f"Error cargando datos: {e}")
            return None

    def _run_eda_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Ejecuta análisis EDA básico."""
        try:
            eda_results = {
                "dataset_info": {
                    "total_records": len(df),
                    "total_columns": len(df.columns),
                    "seasons": (
                        sorted(df["season"].unique()) if "season" in df.columns else []
                    ),
                    "date_range": {
                        "seasons": (
                            df["season"].nunique() if "season" in df.columns else 1
                        )
                    },
                },
                "player_analysis": {},
                "position_analysis": {},
                "quality_analysis": {},
            }

            # Análisis de jugadores únicos
            if "Player" in df.columns:
                unique_players = df["Player"].nunique()
                avg_records_per_player = len(df) / unique_players
                eda_results["player_analysis"] = {
                    "unique_players": unique_players,
                    "avg_records_per_player": round(avg_records_per_player, 2),
                }

            # Análisis de posiciones
            if "Primary position" in df.columns:
                position_counts = df["Primary position"].value_counts()
                eda_results["position_analysis"] = {
                    "unique_positions": len(position_counts),
                    "top_positions": position_counts.head().to_dict(),
                    "position_distribution": position_counts.to_dict(),
                }

            # Análisis de calidad de datos
            null_analysis = df.isnull().sum()
            eda_results["quality_analysis"] = {
                "columns_with_nulls": len(null_analysis[null_analysis > 0]),
                "total_null_values": null_analysis.sum(),
                "null_percentage": (null_analysis.sum() / (len(df) * len(df.columns)))
                * 100,
            }

            return eda_results

        except Exception as e:
            self.logger.error(f"Error en análisis EDA: {e}")
            return {"error": str(e)}

    def _run_baseline_evaluation_existing(self) -> Dict[str, Any]:
        """Ejecuta evaluación baseline usando sistema existente."""
        try:
            self.logger.info(
                "🔬 Ejecutando evaluación baseline usando sistema existente"
            )

            # Usar función existente de baseline_model.py
            baseline_results = run_comprehensive_baseline_evaluation()

            return baseline_results

        except Exception as e:
            self.logger.error(f"Error en evaluación baseline: {e}")
            return {"error": str(e), "models": {}}

    def _run_advanced_comparison_existing(
        self, df: pd.DataFrame, baseline_results: Dict
    ) -> Dict[str, Any]:
        """Ejecuta comparación avanzada usando sistema existente."""
        try:
            self.logger.info(
                "🚀 Ejecutando comparación avanzada usando sistema existente"
            )

            # Usar función existente de baseline_model.py
            advanced_results = run_advanced_baseline_comparison(df, baseline_results)

            return advanced_results

        except Exception as e:
            self.logger.error(f"Error en comparación avanzada: {e}")
            return {"error": str(e)}

    def _analyze_feature_importance(self, advanced_results: Dict) -> Dict[str, Any]:
        """Analiza importancia de features del mejor modelo."""
        try:
            if "best_model" not in advanced_results:
                return {"error": "No se encontró mejor modelo"}

            best_model_name, best_model_data = advanced_results["best_model"]
            feature_importance = best_model_data.get("Feature_Importance", {})

            if not feature_importance:
                return {"warning": "Modelo no proporciona importancia de features"}

            # Ordenar por importancia
            sorted_features = sorted(
                feature_importance.items(), key=lambda x: x[1], reverse=True
            )

            # Categorizar features
            feature_analysis = {
                "total_features": len(feature_importance),
                "top_10_features": dict(sorted_features[:10]),
                "feature_categories": {
                    "positional": len(
                        [
                            f
                            for f in feature_importance.keys()
                            if "position" in f.lower()
                        ]
                    ),
                    "age_related": len(
                        [f for f in feature_importance.keys() if "age" in f.lower()]
                    ),
                    "tier_related": len(
                        [f for f in feature_importance.keys() if "tier" in f.lower()]
                    ),
                    "interaction": len(
                        [
                            f
                            for f in feature_importance.keys()
                            if "interaction" in f.lower()
                        ]
                    ),
                },
            }

            return feature_analysis

        except Exception as e:
            self.logger.error(f"Error analizando importancia: {e}")
            return {"error": str(e)}

    def _generate_academic_report(
        self, eda_results: Dict, baseline_results: Dict
    ) -> str:
        """Genera reporte académico consolidado."""
        report_lines = [
            "=" * 80,
            "REPORTE ACADÉMICO: ANÁLISIS EDA + BASELINE",
            "=" * 80,
            f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Dataset: Liga Tailandesa",
            f"Metodología: CRISP-DM con rigor académico",
            "=" * 80,
            "",
        ]

        # Sección EDA
        if "dataset_info" in eda_results:
            info = eda_results["dataset_info"]
            report_lines.extend(
                [
                    "📊 ANÁLISIS EXPLORATORIO DE DATOS:",
                    f"   • Total registros: {info.get('total_records', 'N/A'):,}",
                    f"   • Total columnas: {info.get('total_columns', 'N/A')}",
                    f"   • Temporadas: {len(info.get('seasons', []))}",
                    "",
                ]
            )

        # Sección Baseline
        if baseline_results and "models" in baseline_results:
            report_lines.extend(
                [
                    "🔬 RESULTADOS MODELOS BASELINE:",
                    f"   • Modelos evaluados: {len(baseline_results.get('models', {}))}",
                    "",
                ]
            )

            # Mejor modelo
            models = baseline_results.get("models", {})
            if models:
                best_model = min(
                    models.items(), key=lambda x: x[1].get("MAE", float("inf"))
                )
                best_name, best_metrics = best_model

                report_lines.extend(
                    [
                        f"🏆 MEJOR MODELO: {best_name}",
                        f"   • MAE: {best_metrics.get('MAE', 'N/A'):.3f}",
                        f"   • R²: {best_metrics.get('R²', 'N/A'):.3f}",
                        f"   • RMSE: {best_metrics.get('RMSE', 'N/A'):.3f}",
                        "",
                    ]
                )

        # Conclusiones
        report_lines.extend(
            [
                "💡 CONCLUSIONES ACADÉMICAS:",
                "   • Análisis EDA completado exitosamente",
                "   • Baseline establecido para futuros modelos",
                "   • Metodología CRISP-DM aplicada correctamente",
                "",
                "🚀 PRÓXIMOS PASOS:",
                "   • Implementar modelos avanzados",
                "   • Optimización de hiperparámetros",
                "   • Validación temporal por temporadas",
                "",
                "=" * 80,
                "FIN DEL REPORTE",
                "=" * 80,
            ]
        )

        return "\n".join(report_lines)

    def _generate_comparison_report(
        self, baseline_results: Dict, advanced_results: Dict, feature_analysis: Dict
    ) -> str:
        """Genera reporte de comparación features."""
        report_lines = [
            "=" * 80,
            "REPORTE ACADÉMICO: COMPARACIÓN FEATURES AVANZADAS",
            "=" * 80,
            f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 80,
            "",
        ]

        # Resultados avanzados
        if "best_model" in advanced_results:
            best_name, best_data = advanced_results["best_model"]
            report_lines.extend(
                [
                    "🚀 RESULTADOS FEATURES AVANZADAS:",
                    f"   • Mejor modelo: {best_name}",
                    f"   • MAE: {best_data.get('MAE', 'N/A'):.3f}",
                    f"   • R²: {best_data.get('R²', 'N/A'):.3f}",
                    f"   • MAPE: {best_data.get('MAPE', 'N/A'):.1f}%",
                    "",
                ]
            )

        # Análisis de features
        if "top_10_features" in feature_analysis:
            report_lines.extend(["📊 TOP 10 FEATURES MÁS IMPORTANTES:", ""])

            for i, (feature, importance) in enumerate(
                feature_analysis["top_10_features"].items(), 1
            ):
                report_lines.append(f"   {i:2d}. {feature}: {importance:.4f}")

            report_lines.append("")

        # Categorización de features
        if "feature_categories" in feature_analysis:
            cats = feature_analysis["feature_categories"]
            report_lines.extend(
                [
                    "🔧 CATEGORÍAS DE FEATURES:",
                    f"   • Features posicionales: {cats.get('positional', 0)}",
                    f"   • Features de edad: {cats.get('age_related', 0)}",
                    f"   • Features de tier: {cats.get('tier_related', 0)}",
                    f"   • Features de interacción: {cats.get('interaction', 0)}",
                    "",
                ]
            )

        # Mejora vs baseline
        if "improvement_vs_baseline" in advanced_results:
            improvement = advanced_results.get("improvement_vs_baseline", 0)
            if improvement:
                report_lines.extend(
                    [
                        "📈 MEJORA VS BASELINE:",
                        f"   • Reducción MAE: {improvement:.3f}",
                        f"   • Estado: {'✅ Mejora significativa' if improvement > 0 else '❌ Sin mejora'}",
                        "",
                    ]
                )

        report_lines.extend(["=" * 80, "FIN DEL REPORTE", "=" * 80])

        return "\n".join(report_lines)


# Funciones de conveniencia para uso directo
def run_eda_baseline_analysis() -> Dict[str, Any]:
    """
    Función de conveniencia para ejecutar análisis EDA + baseline completo.
    Reemplaza el script run_eda_baseline_analysis.py eliminado.
    """
    runner = AcademicAnalysisRunner()
    return runner.run_complete_eda_baseline_analysis()


def run_feature_comparison() -> Dict[str, Any]:
    """
    Función de conveniencia para ejecutar comparación de features avanzadas.
    Reemplaza el script run_advanced_feature_comparison.py eliminado.
    """
    runner = AcademicAnalysisRunner()
    return runner.run_advanced_feature_comparison()


if __name__ == "__main__":
    # Permitir ejecución directa
    import argparse

    parser = argparse.ArgumentParser(description="Academic Analysis Runner")
    parser.add_argument(
        "--analysis",
        choices=["eda", "features", "both"],
        default="both",
        help="Tipo de análisis a ejecutar",
    )

    args = parser.parse_args()

    if args.analysis in ["eda", "both"]:
        print("🎓 Ejecutando análisis EDA + baseline...")
        eda_results = run_eda_baseline_analysis()
        print(f"✅ EDA completado: {eda_results.get('success', False)}")

    if args.analysis in ["features", "both"]:
        print("🚀 Ejecutando comparación features avanzadas...")
        feature_results = run_feature_comparison()
        print(f"✅ Comparación completada: {feature_results.get('success', False)}")

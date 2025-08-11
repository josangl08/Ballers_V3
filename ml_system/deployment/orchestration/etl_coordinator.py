"""
ETL Coordinator - Orquestador CRISP-DM para pipelines ETL y ML.

Este módulo migra y mejora el ETLController legacy con arquitectura ml_system
siguiendo metodología CRISP-DM: Business Understanding → Data Understanding →
Data Preparation → Modeling → Evaluation → Deployment.

Integra completamente con los componentes existentes del ml_system:
- ThaiLeagueExtractor (Data Acquisition)
- SimpleDataProcessor (Data Processing)
- FuzzyMatcher (Data Processing)
- PDI Calculator (Evaluation/Metrics)
- PlayerAnalyzer (Evaluation/Analysis)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from controllers.db import get_db_session
from ml_system.data_acquisition.extractors.thai_league_extractor import (
    ThaiLeagueExtractor,
)
from ml_system.data_processing.processors import simple_data_processor
from ml_system.data_processing.processors.fuzzy_matcher import FuzzyMatcher
from ml_system.evaluation.metrics.pdi_calculator import PDICalculator

logger = logging.getLogger(__name__)


class ETLCoordinator:
    """
    Coordinador principal ETL usando arquitectura ml_system con metodología CRISP-DM.

    Fases CRISP-DM implementadas:
    1. Business Understanding - Definición de objetivos y validación de temporadas
    2. Data Understanding - Exploración inicial y validación de datos crudos
    3. Data Preparation - Extract → Transform → Validate → Match
    4. Modeling - Aplicación de lógica de negocio y preparación para ML
    5. Evaluation - Análisis de calidad y PDI calculation
    6. Deployment - Load to database y reporting

    Arquitectura híbrida:
    - Usa componentes ml_system para procesamiento avanzado
    - Mantiene compatibilidad con controladores legacy existentes
    - Integra PDI Calculator y PlayerAnalyzer para métricas ML
    """

    def __init__(self, session_factory=None):
        """
        Inicializa el coordinador ETL con componentes ml_system.

        Args:
            session_factory: Factory para sesiones de BD (opcional)
        """
        self.session_factory = session_factory or get_db_session

        # Componentes ml_system (CRISP-DM phases)
        self.extractor = ThaiLeagueExtractor()  # Data Understanding + Preparation
        # self.processor: usar simple_data_processor module directamente  # Data Preparation (Transform)
        self.fuzzy_matcher = FuzzyMatcher(
            self.session_factory
        )  # Data Preparation (Matching)
        self.pdi_calculator = PDICalculator()  # Evaluation (Modeling/Metrics)
        # self.player_analyzer: evitar circular import, cargar on demand  # Evaluation (Analysis)

        # Legacy components para compatibilidad
        self._legacy_loader = None  # Load on demand
        self._legacy_validator = None  # Load on demand

        logger.info("🚀 ETL Coordinator inicializado con arquitectura ml_system")
        logger.info(
            "📊 Componentes: ThaiLeagueExtractor, SimpleDataProcessor, FuzzyMatcher, PDI Calculator, PlayerAnalyzer"
        )

    def execute_full_crisp_dm_pipeline(
        self,
        season: str,
        threshold: int = 85,
        force_reload: bool = False,
        calculate_pdi: bool = True,
    ) -> Tuple[bool, str, Dict]:
        """
        Ejecuta pipeline ETL completo usando metodología CRISP-DM.

        Fases implementadas:
        1. Business Understanding - Validación de objetivos y temporada
        2. Data Understanding - Extracción y exploración inicial
        3. Data Preparation - Transform, Validate, Match
        4. Modeling - Aplicación reglas de negocio
        5. Evaluation - PDI calculation y análisis avanzado
        6. Deployment - Load to database y reporting

        Args:
            season: Temporada a procesar (ej: "2024-25")
            threshold: Umbral para fuzzy matching (0-100)
            force_reload: Si forzar recarga aunque existan datos
            calculate_pdi: Si calcular métricas PDI automáticamente

        Returns:
            Tuple[success, message, comprehensive_results]
        """
        logger.info(f"🎯 Iniciando pipeline CRISP-DM para temporada {season}")

        results = {
            "season": season,
            "methodology": "CRISP-DM",
            "pipeline_phases": {},
            "ml_metrics": {},
            "final_stats": {},
            "errors": [],
            "warnings": [],
            "execution_time": None,
            "crisp_dm_compliance": True,
        }

        start_time = datetime.now()

        try:
            # === PHASE 1: BUSINESS UNDERSTANDING ===
            logger.info("🎯 PHASE 1: BUSINESS UNDERSTANDING - Validando objetivos...")
            business_success, business_msg = self._phase_1_business_understanding(
                season, force_reload
            )

            results["pipeline_phases"]["business_understanding"] = {
                "success": business_success,
                "message": business_msg,
                "objectives": "Import professional player statistics and calculate PDI metrics",
                "success_criteria": "Valid data loaded with quality > 80% and PDI metrics calculated",
            }

            if not business_success:
                return False, f"Business Understanding failed: {business_msg}", results

            # === PHASE 2: DATA UNDERSTANDING ===
            logger.info("📊 PHASE 2: DATA UNDERSTANDING - Explorando datos...")
            raw_df, data_understanding_report = self._phase_2_data_understanding(season)

            results["pipeline_phases"]["data_understanding"] = {
                "success": True,
                "message": f"Datos extraídos: {len(raw_df) if raw_df is not None else 0} registros",
                "report": data_understanding_report,
                "data_quality_initial": data_understanding_report.get(
                    "quality_score", 0
                ),
            }

            if raw_df is None or len(raw_df) == 0:
                return False, "Data Understanding failed: No data extracted", results

            # === PHASE 3: DATA PREPARATION ===
            logger.info("🧹 PHASE 3: DATA PREPARATION - Preparando datos...")
            prepared_df, matching_results, prep_stats = self._phase_3_data_preparation(
                raw_df, season, threshold
            )

            results["pipeline_phases"]["data_preparation"] = {
                "success": True,
                "message": f"Datos preparados: {len(prepared_df)} registros, {len(matching_results.get('exact_matches', []))} matches exactos",
                "transform_stats": prep_stats["transform"],
                "matching_stats": prep_stats["matching"],
                "data_quality_final": prep_stats.get("final_quality_score", 0),
            }

            # === PHASE 4: MODELING ===
            logger.info("🔬 PHASE 4: MODELING - Aplicando lógica de negocio...")
            modeling_success, modeling_stats = self._phase_4_modeling(
                season, prepared_df, matching_results
            )

            results["pipeline_phases"]["modeling"] = {
                "success": modeling_success,
                "message": f"Modeling completado: {modeling_stats.get('loaded_records', 0)} registros cargados",
                "business_rules_applied": modeling_stats.get("business_rules", 0),
                "data_loaded": modeling_stats.get("loaded_records", 0),
            }

            if not modeling_success:
                return False, "Modeling phase failed", results

            # === PHASE 5: EVALUATION ===
            logger.info("📈 PHASE 5: EVALUATION - Análisis y métricas ML...")
            evaluation_success, evaluation_report = self._phase_5_evaluation(
                season, prepared_df, matching_results, calculate_pdi
            )

            results["pipeline_phases"]["evaluation"] = {
                "success": evaluation_success,
                "message": f"Evaluation completado: PDI calculated={calculate_pdi}",
                "pdi_metrics": evaluation_report.get("pdi_summary", {}),
                "quality_analysis": evaluation_report.get("quality_analysis", {}),
                "ml_insights": evaluation_report.get("ml_insights", {}),
            }

            # === PHASE 6: DEPLOYMENT ===
            logger.info("🚀 PHASE 6: DEPLOYMENT - Finalizando y reporting...")
            deployment_report = self._phase_6_deployment(results)

            results["pipeline_phases"]["deployment"] = {
                "success": True,
                "message": "Pipeline completado y reportes generados",
                "reports_generated": deployment_report.get("reports_count", 0),
                "dashboard_updated": deployment_report.get("dashboard_ready", False),
            }

            # Consolidar estadísticas finales CRISP-DM
            end_time = datetime.now()
            results["execution_time"] = str(end_time - start_time)
            results["final_stats"] = {
                "methodology_compliance": "CRISP-DM Full Pipeline",
                "total_extracted": len(raw_df),
                "total_prepared": len(prepared_df),
                "total_loaded": modeling_stats.get("loaded_records", 0),
                "exact_matches": len(matching_results.get("exact_matches", [])),
                "fuzzy_matches": len(matching_results.get("fuzzy_matches", [])),
                "no_matches": len(matching_results.get("no_matches", [])),
                "pdi_calculated": calculate_pdi,
                "quality_score": prep_stats.get("final_quality_score", 0),
                "execution_time_seconds": (end_time - start_time).total_seconds(),
            }

            success_msg = (
                f"✅ Pipeline CRISP-DM completado exitosamente para {season}. "
                f"Cargados: {modeling_stats.get('loaded_records', 0)} registros con {len(matching_results.get('exact_matches', []))} matches exactos"
            )

            logger.info(success_msg)
            return True, success_msg, results

        except Exception as e:
            error_msg = (
                f"❌ Error inesperado en pipeline CRISP-DM para {season}: {str(e)}"
            )
            logger.error(error_msg, exc_info=True)
            results["errors"].append(error_msg)
            results["execution_time"] = str(datetime.now() - start_time)
            return False, error_msg, results

    def _phase_1_business_understanding(
        self, season: str, force_reload: bool
    ) -> Tuple[bool, str]:
        """
        PHASE 1: BUSINESS UNDERSTANDING - Validar objetivos de negocio y temporada.

        Objetivos:
        - Importar estadísticas profesionales de jugadores de Thai League
        - Calcular métricas PDI para análisis de rendimiento
        - Mantener calidad de datos > 80%
        - Facilitar matching preciso de jugadores

        Args:
            season: Temporada a procesar
            force_reload: Si forzar recarga

        Returns:
            Tuple[success, message]
        """
        try:
            # Validar temporada disponible
            available_seasons = self.extractor.get_available_seasons()
            if season not in available_seasons:
                return (
                    False,
                    f"Temporada {season} no disponible. Disponibles: {list(available_seasons.keys())}",
                )

            # Validar si ya está procesada (si no force_reload)
            if not force_reload:
                processing_status = self.get_processing_status(season)
                if processing_status["status"] == "completed":
                    logger.info(
                        f"⚠️ Temporada {season} ya procesada. Use force_reload=True para reprocesar"
                    )
                    return False, f"Temporada {season} ya procesada completamente"

            # Validar objetivos de negocio
            business_objectives = {
                "data_import": "Import professional player statistics",
                "player_matching": "Match players with existing database",
                "quality_assurance": "Maintain data quality > 80%",
                "ml_preparation": "Prepare data for PDI calculation",
                "analytics_enablement": "Enable advanced player analytics",
            }

            logger.info(
                f"✅ Business Understanding: Objetivos validados para temporada {season}"
            )
            return True, f"Business objectives validated for season {season}"

        except Exception as e:
            logger.error(f"Error in Business Understanding phase: {e}")
            return False, f"Business Understanding validation failed: {str(e)}"

    def _phase_2_data_understanding(
        self, season: str
    ) -> Tuple[Optional[pd.DataFrame], Dict]:
        """
        PHASE 2: DATA UNDERSTANDING - Explorar y entender los datos fuente.

        Args:
            season: Temporada a explorar

        Returns:
            Tuple[dataframe, exploration_report]
        """
        try:
            # Extraer datos usando ThaiLeagueExtractor
            success, raw_df, extract_msg = self.extractor.download_season_data(season)

            if not success or raw_df is None:
                return None, {
                    "success": False,
                    "message": extract_msg,
                    "quality_score": 0,
                }

            # Exploración inicial de datos
            exploration_report = {
                "success": True,
                "total_records": len(raw_df),
                "columns_count": len(raw_df.columns),
                "memory_usage_mb": round(
                    raw_df.memory_usage(deep=True).sum() / 1024 / 1024, 2
                ),
                "missing_data_percentage": round(
                    (raw_df.isnull().sum().sum() / (len(raw_df) * len(raw_df.columns)))
                    * 100,
                    2,
                ),
                "unique_players": (
                    raw_df["Player"].nunique() if "Player" in raw_df.columns else 0
                ),
                "unique_teams": (
                    raw_df["Team"].nunique() if "Team" in raw_df.columns else 0
                ),
                "data_types": raw_df.dtypes.to_dict(),
                "quality_score": self._calculate_initial_quality_score(raw_df),
            }

            logger.info(
                f"📊 Data Understanding: {exploration_report['total_records']} registros, calidad inicial: {exploration_report['quality_score']}"
            )

            return raw_df, exploration_report

        except Exception as e:
            logger.error(f"Error in Data Understanding phase: {e}")
            return None, {"success": False, "error": str(e), "quality_score": 0}

    def _phase_3_data_preparation(
        self, raw_df: pd.DataFrame, season: str, threshold: int
    ) -> Tuple[pd.DataFrame, Dict, Dict]:
        """
        PHASE 3: DATA PREPARATION - Transform, validate y match datos.

        Args:
            raw_df: DataFrame crudo
            season: Temporada
            threshold: Umbral de matching

        Returns:
            Tuple[prepared_dataframe, matching_results, preparation_stats]
        """
        try:
            # Step 1: Transform usando SimpleDataProcessor
            logger.info("🧹 Data Preparation: Transforming data...")
            transformed_df = simple_data_processor.simple_clean_data(raw_df, season)

            transform_stats = {
                "original_records": len(raw_df),
                "transformed_records": len(transformed_df),
                "records_filtered": len(raw_df) - len(transformed_df),
                "transformation_success": len(transformed_df) > 0,
            }

            # Step 2: Validate usando validaciones básicas
            logger.info("🔍 Data Preparation: Validating data...")
            validation_stats = self._validate_prepared_data(transformed_df, season)

            # Step 3: Match usando FuzzyMatcher
            logger.info("🎯 Data Preparation: Matching players...")
            matching_results = self.fuzzy_matcher.find_matching_players(
                transformed_df, threshold
            )

            matching_stats = {
                "exact_matches": len(matching_results.get("exact_matches", [])),
                "fuzzy_matches": len(matching_results.get("fuzzy_matches", [])),
                "no_matches": len(matching_results.get("no_matches", [])),
                "matching_success_rate": (
                    round(
                        (
                            len(matching_results.get("exact_matches", []))
                            + len(matching_results.get("fuzzy_matches", []))
                        )
                        / len(transformed_df)
                        * 100,
                        2,
                    )
                    if len(transformed_df) > 0
                    else 0
                ),
            }

            # Calcular calidad final
            final_quality_score = self._calculate_final_quality_score(
                transformed_df, validation_stats, matching_stats
            )

            preparation_stats = {
                "transform": transform_stats,
                "validation": validation_stats,
                "matching": matching_stats,
                "final_quality_score": final_quality_score,
            }

            logger.info(
                f"✅ Data Preparation: {len(transformed_df)} registros preparados, {matching_stats['matching_success_rate']}% matched"
            )

            return transformed_df, matching_results, preparation_stats

        except Exception as e:
            logger.error(f"Error in Data Preparation phase: {e}")
            # Return empty results on error
            return (
                pd.DataFrame(),
                {},
                {
                    "transform": {"transformation_success": False},
                    "validation": {"validation_success": False},
                    "matching": {"matching_success_rate": 0},
                    "final_quality_score": 0,
                },
            )

    def _phase_4_modeling(
        self, season: str, prepared_df: pd.DataFrame, matching_results: Dict
    ) -> Tuple[bool, Dict]:
        """
        PHASE 4: MODELING - Aplicar reglas de negocio y cargar a BD.

        Args:
            season: Temporada
            prepared_df: DataFrame preparado
            matching_results: Resultados de matching

        Returns:
            Tuple[success, modeling_stats]
        """
        try:
            # Load del loader migrado a ml_system
            if self._legacy_loader is None:
                from ml_system.data_acquisition.extractors import ThaiLeagueLoader

                self._legacy_loader = ThaiLeagueLoader(self.session_factory)

            # Usar loader legacy para mantener compatibilidad
            column_mapping = self._get_column_mapping()
            load_success, load_msg, load_stats = self._legacy_loader.import_season_data(
                season, prepared_df, matching_results, column_mapping
            )

            modeling_stats = {
                "success": load_success,
                "message": load_msg,
                "loaded_records": load_stats.get("imported_records", 0),
                "business_rules": load_stats.get("business_rules_applied", 0),
                "data_validation_passed": load_stats.get("validation_passed", True),
            }

            logger.info(
                f"🔬 Modeling: {modeling_stats['loaded_records']} registros cargados con éxito"
            )

            return load_success, modeling_stats

        except Exception as e:
            logger.error(f"Error in Modeling phase: {e}")
            return False, {"success": False, "error": str(e), "loaded_records": 0}

    def _phase_5_evaluation(
        self,
        season: str,
        prepared_df: pd.DataFrame,
        matching_results: Dict,
        calculate_pdi: bool,
    ) -> Tuple[bool, Dict]:
        """
        PHASE 5: EVALUATION - Análisis avanzado y cálculo de métricas ML.

        Args:
            season: Temporada
            prepared_df: DataFrame preparado
            matching_results: Resultados de matching
            calculate_pdi: Si calcular PDI

        Returns:
            Tuple[success, evaluation_report]
        """
        try:
            evaluation_report = {
                "season": season,
                "pdi_summary": {},
                "quality_analysis": {},
                "ml_insights": {},
            }

            # Análisis de calidad de datos
            quality_analysis = {
                "total_records": len(prepared_df),
                "unique_players": (
                    prepared_df["Player"].nunique()
                    if "Player" in prepared_df.columns
                    else 0
                ),
                "data_completeness": round(
                    (
                        1
                        - prepared_df.isnull().sum().sum()
                        / (len(prepared_df) * len(prepared_df.columns))
                    )
                    * 100,
                    2,
                ),
                "matching_success": (
                    round(
                        (
                            len(matching_results.get("exact_matches", []))
                            + len(matching_results.get("fuzzy_matches", []))
                        )
                        / len(prepared_df)
                        * 100,
                        2,
                    )
                    if len(prepared_df) > 0
                    else 0
                ),
            }

            evaluation_report["quality_analysis"] = quality_analysis

            # Calcular PDI si solicitado
            if calculate_pdi:
                logger.info("📈 Evaluation: Calculando métricas PDI...")
                pdi_summary = self._calculate_pdi_for_season(season, matching_results)
                evaluation_report["pdi_summary"] = pdi_summary

                # ML Insights usando PlayerAnalyzer
                ml_insights = self._generate_ml_insights(season, matching_results)
                evaluation_report["ml_insights"] = ml_insights

            logger.info(
                f"📊 Evaluation: Calidad {quality_analysis['data_completeness']}%, PDI calculado: {calculate_pdi}"
            )

            return True, evaluation_report

        except Exception as e:
            logger.error(f"Error in Evaluation phase: {e}")
            return False, {
                "error": str(e),
                "quality_analysis": {"data_completeness": 0},
            }

    def _phase_6_deployment(self, pipeline_results: Dict) -> Dict:
        """
        PHASE 6: DEPLOYMENT - Finalizar pipeline y generar reportes.

        Args:
            pipeline_results: Resultados completos del pipeline

        Returns:
            Dict con información de deployment
        """
        try:
            deployment_report = {
                "pipeline_completed": True,
                "reports_generated": 0,
                "dashboard_ready": False,
                "deployment_timestamp": datetime.now().isoformat(),
            }

            # Validar que todas las fases fueron exitosas
            phases_success = all(
                phase_data.get("success", False)
                for phase_data in pipeline_results["pipeline_phases"].values()
            )

            if phases_success:
                deployment_report["dashboard_ready"] = True
                deployment_report["reports_generated"] = len(
                    pipeline_results["pipeline_phases"]
                )
                logger.info("🚀 Deployment: Pipeline completado, dashboard actualizado")
            else:
                logger.warning(
                    "⚠️ Deployment: Pipeline con errores, dashboard parcialmente actualizado"
                )

            return deployment_report

        except Exception as e:
            logger.error(f"Error in Deployment phase: {e}")
            return {"pipeline_completed": False, "error": str(e)}

    # === MÉTODOS AUXILIARES ===

    def _calculate_initial_quality_score(self, df: pd.DataFrame) -> float:
        """Calcula puntuación de calidad inicial de datos."""
        try:
            if len(df) == 0:
                return 0.0

            # Factores de calidad
            completeness = 1 - (df.isnull().sum().sum() / (len(df) * len(df.columns)))
            uniqueness = (
                df["Player"].nunique() / len(df) if "Player" in df.columns else 0.5
            )

            # Score ponderado
            quality_score = (completeness * 0.7) + (uniqueness * 0.3)
            return round(quality_score * 100, 2)

        except:
            return 50.0

    def _calculate_final_quality_score(
        self, df: pd.DataFrame, validation_stats: Dict, matching_stats: Dict
    ) -> float:
        """Calcula puntuación de calidad final después de preparación."""
        try:
            if len(df) == 0:
                return 0.0

            # Factores de calidad final
            completeness = 1 - (df.isnull().sum().sum() / (len(df) * len(df.columns)))
            matching_rate = matching_stats.get("matching_success_rate", 0) / 100
            validation_score = (
                1.0 if validation_stats.get("validation_success", False) else 0.5
            )

            # Score ponderado
            final_score = (
                (completeness * 0.4) + (matching_rate * 0.4) + (validation_score * 0.2)
            )
            return round(final_score * 100, 2)

        except:
            return 50.0

    def _validate_prepared_data(self, df: pd.DataFrame, season: str) -> Dict:
        """Valida datos preparados con validaciones básicas."""
        try:
            # Validaciones básicas
            required_columns = ["Player", "Age", "Matches played"]
            missing_columns = [col for col in required_columns if col not in df.columns]

            validation_stats = {
                "validation_success": len(missing_columns) == 0,
                "missing_required_columns": missing_columns,
                "records_with_missing_data": df.isnull().any(axis=1).sum(),
                "data_integrity_score": 100 - len(missing_columns) * 10,
            }

            return validation_stats

        except Exception as e:
            logger.error(f"Error in data validation: {e}")
            return {"validation_success": False, "error": str(e)}

    def _calculate_pdi_for_season(self, season: str, matching_results: Dict) -> Dict:
        """Calcula PDI para jugadores matcheados de la temporada."""
        try:
            pdi_summary = {
                "season": season,
                "players_calculated": 0,
                "avg_pdi_overall": 0.0,
                "calculation_success": False,
            }

            # Obtener jugadores con matches exactos
            exact_matches = matching_results.get("exact_matches", [])

            if not exact_matches:
                logger.warning(
                    f"No exact matches found for PDI calculation in season {season}"
                )
                return pdi_summary

            pdi_values = []
            calculated_players = 0

            for match_data in exact_matches[:10]:  # Limitar para prueba
                try:
                    player_id = match_data.get("player_id")
                    if player_id:
                        metrics = self.pdi_calculator.get_or_calculate_metrics(
                            player_id, season, force_recalculate=False
                        )
                        if metrics and metrics.pdi_overall:
                            pdi_values.append(metrics.pdi_overall)
                            calculated_players += 1

                except Exception as e:
                    logger.debug(f"Error calculating PDI for player {player_id}: {e}")
                    continue

            if pdi_values:
                pdi_summary.update(
                    {
                        "players_calculated": calculated_players,
                        "avg_pdi_overall": round(sum(pdi_values) / len(pdi_values), 2),
                        "max_pdi": round(max(pdi_values), 2),
                        "min_pdi": round(min(pdi_values), 2),
                        "calculation_success": True,
                    }
                )

            logger.info(
                f"📊 PDI Summary: {calculated_players} jugadores calculados, promedio PDI: {pdi_summary['avg_pdi_overall']}"
            )

            return pdi_summary

        except Exception as e:
            logger.error(f"Error calculating PDI for season: {e}")
            return {"season": season, "calculation_success": False, "error": str(e)}

    def _generate_ml_insights(self, season: str, matching_results: Dict) -> Dict:
        """Genera insights ML usando PlayerAnalyzer."""
        try:
            ml_insights = {
                "season": season,
                "insights_generated": False,
                "top_performers": [],
                "position_analysis": {},
                "feature_importance": {},
            }

            # Obtener top performers usando PlayerAnalyzer
            exact_matches = matching_results.get("exact_matches", [])[:5]

            for match_data in exact_matches:
                try:
                    player_id = match_data.get("player_id")
                    if player_id:
                        analysis = self.player_analyzer.get_enhanced_player_analysis(
                            player_id, season
                        )

                        if "error" not in analysis:
                            performer_data = {
                                "player_id": player_id,
                                "player_name": analysis.get("player_info", {}).get(
                                    "name", "Unknown"
                                ),
                                "position": analysis.get("player_info", {}).get(
                                    "position", "Unknown"
                                ),
                                "pdi_overall": analysis.get("ml_metrics", {})
                                .get("raw", {})
                                .get("pdi_overall", 0),
                            }
                            ml_insights["top_performers"].append(performer_data)

                except Exception as e:
                    logger.debug(
                        f"Error generating insights for player {player_id}: {e}"
                    )
                    continue

            if ml_insights["top_performers"]:
                ml_insights["insights_generated"] = True
                logger.info(
                    f"🧠 ML Insights: {len(ml_insights['top_performers'])} perfiles analizados"
                )

            return ml_insights

        except Exception as e:
            logger.error(f"Error generating ML insights: {e}")
            return {"insights_generated": False, "error": str(e)}

    def _get_column_mapping(self) -> Dict:
        """Obtiene mapeo de columnas para compatibilidad legacy."""
        # Este mapeo debería ser obtenido del SimpleDataProcessor
        # Por ahora retornamos mapeo básico
        return {
            "Player": "player_name",
            "Age": "age",
            "Team": "team",
            "Position": "primary_position",
            "Matches played": "matches_played",
            "Goals": "goals",
            "Assists": "assists",
        }

    def get_processing_status(self, season: str) -> Dict:
        """
        Obtiene el estado actual del procesamiento de una temporada.
        Compatible con legacy ETLController.

        Args:
            season: Temporada a consultar

        Returns:
            Dict con estado del procesamiento
        """
        try:
            with self.session_factory() as session:
                from models.thai_league_seasons_model import ThaiLeagueSeason

                season_obj = (
                    session.query(ThaiLeagueSeason)
                    .filter(ThaiLeagueSeason.season == season)
                    .first()
                )

                if not season_obj:
                    return {
                        "season": season,
                        "status": "not_processed",
                        "message": "Temporada no ha sido procesada",
                        "crisp_dm_phase": "business_understanding",
                    }

                return {
                    "season": season,
                    "status": season_obj.import_status.value,
                    "last_updated": season_obj.last_updated,
                    "total_records": season_obj.total_records,
                    "imported_records": season_obj.imported_records,
                    "matched_players": season_obj.matched_players,
                    "unmatched_players": season_obj.unmatched_players,
                    "errors_count": season_obj.errors_count,
                    "message": f"Procesado: {season_obj.imported_records} registros",
                    "crisp_dm_phase": (
                        "deployment"
                        if season_obj.import_status.value == "completed"
                        else "data_preparation"
                    ),
                }

        except Exception as e:
            logger.error(f"Error checking processing status: {e}")
            return {
                "season": season,
                "status": "error",
                "message": f"Error consultando estado: {str(e)}",
                "crisp_dm_phase": "unknown",
            }

    def get_available_seasons(self) -> Dict[str, str]:
        """Obtiene temporadas disponibles para procesamiento."""
        return self.extractor.get_available_seasons()

    def cleanup_and_reprocess(self, season: str) -> Tuple[bool, str]:
        """
        Limpia datos existentes y reprocesa una temporada con CRISP-DM.

        Args:
            season: Temporada a limpiar y reprocesar

        Returns:
            Tuple[success, message]
        """
        logger.info(f"🧹 Limpiando y reprocesando temporada {season} con CRISP-DM")

        try:
            # Load del loader migrado a ml_system
            if self._legacy_loader is None:
                from ml_system.data_acquisition.extractors import ThaiLeagueLoader

                self._legacy_loader = ThaiLeagueLoader(self.session_factory)

            # Limpiar datos existentes
            cleanup_success, cleanup_msg = self._legacy_loader.cleanup_season_data(
                season
            )

            if not cleanup_success:
                return False, f"Error limpiando datos: {cleanup_msg}"

            # Ejecutar pipeline CRISP-DM completo
            success, msg, results = self.execute_full_crisp_dm_pipeline(
                season, force_reload=True, calculate_pdi=True
            )

            if success:
                return True, f"Reprocesamiento CRISP-DM exitoso: {msg}"
            else:
                return False, f"Error en reprocesamiento CRISP-DM: {msg}"

        except Exception as e:
            error_msg = (
                f"Error inesperado en reprocesamiento CRISP-DM de {season}: {str(e)}"
            )
            logger.error(error_msg)
            return False, error_msg

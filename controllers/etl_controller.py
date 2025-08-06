"""
ETL Controller - Orquestador principal del pipeline ETL modular
"""

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd

from controllers.db import get_db_session
from controllers.etl import (
    DataQualityValidator,
    StatsAnalyzer,
    ThaiLeagueExtractor,
    ThaiLeagueLoader,
    ThaiLeagueTransformer,
)

logger = logging.getLogger(__name__)


class ETLController:
    """
    Controlador principal que orquesta el pipeline ETL modular.
    Separa claramente responsabilidades: Extract -> Transform -> Load -> Validate -> Analyze
    """

    def __init__(self, session_factory=None):
        """
        Inicializa el controlador ETL.

        Args:
            session_factory: Factory para sesiones de BD (opcional)
        """
        self.session_factory = session_factory or get_db_session

        # Inicializar módulos ETL
        self.extractor = ThaiLeagueExtractor(session_factory)
        self.transformer = ThaiLeagueTransformer(session_factory)
        self.loader = ThaiLeagueLoader(session_factory)
        self.validator = DataQualityValidator()
        self.analyzer = StatsAnalyzer()

    def execute_full_pipeline(
        self, season: str, threshold: int = 85, force_reload: bool = False
    ) -> Tuple[bool, str, Dict]:
        """
        Ejecuta el pipeline ETL completo para una temporada.

        Args:
            season: Temporada a procesar (ej: "2024-25")
            threshold: Umbral para fuzzy matching
            force_reload: Si forzar recarga aunque existan datos

        Returns:
            Tuple[success, message, comprehensive_results]
        """
        logger.info(f"🚀 Iniciando pipeline ETL completo para temporada {season}")

        results = {
            "season": season,
            "pipeline_steps": {},
            "final_stats": {},
            "errors": [],
            "warnings": [],
        }

        try:
            # PASO 1: EXTRACT - Descarga de datos
            logger.info("📥 PASO 1: EXTRACT - Descargando datos...")
            success, raw_df, extract_msg = self._execute_extract(season)

            results["pipeline_steps"]["extract"] = {
                "success": success,
                "message": extract_msg,
                "records_count": len(raw_df) if raw_df is not None else 0,
            }

            if not success:
                return False, f"Error en Extract: {extract_msg}", results

            # PASO 2: TRANSFORM - Limpieza y normalización
            logger.info("🧹 PASO 2: TRANSFORM - Limpiando y normalizando...")
            clean_df, transform_stats = self._execute_transform(raw_df, season)

            results["pipeline_steps"]["transform"] = {
                "success": True,
                "message": f"Datos transformados: {len(clean_df)} registros",
                "stats": transform_stats,
            }

            # PASO 3: VALIDATE - Validación de calidad
            logger.info("🔍 PASO 3: VALIDATE - Validando calidad...")
            is_valid, validation_errors, validation_stats = self._execute_validate(
                clean_df, season
            )

            results["pipeline_steps"]["validate"] = {
                "success": is_valid,
                "message": f"Validación: {validation_stats['valid_records']}/{validation_stats['total_records']} válidos",
                "errors": validation_errors,
                "stats": validation_stats,
            }

            if not is_valid:
                logger.warning(f"⚠️ Datos no pasan validación, pero continuando...")
                results["warnings"].extend(validation_errors)

            # PASO 4: MATCHING - Encontrar jugadores coincidentes
            logger.info("🎯 PASO 4: MATCHING - Buscando coincidencias...")
            matching_results = self._execute_matching(clean_df, threshold)

            results["pipeline_steps"]["matching"] = {
                "success": True,
                "message": f"Matching completado: {len(matching_results['exact_matches'])} exactos",
                "results": matching_results,
            }

            # PASO 5: LOAD - Carga a base de datos
            logger.info("💾 PASO 5: LOAD - Cargando a base de datos...")
            load_success, load_msg, load_stats = self._execute_load(
                season, clean_df, matching_results
            )

            results["pipeline_steps"]["load"] = {
                "success": load_success,
                "message": load_msg,
                "stats": load_stats,
            }

            if not load_success:
                return False, f"Error en Load: {load_msg}", results

            # PASO 6: ANALYZE - Análisis y reportes
            logger.info("📊 PASO 6: ANALYZE - Generando análisis...")
            analysis = self._execute_analyze(clean_df, matching_results, season)

            results["pipeline_steps"]["analyze"] = {
                "success": True,
                "message": "Análisis completado",
                "analysis": analysis,
            }

            # Consolidar estadísticas finales
            results["final_stats"] = {
                "total_extracted": len(raw_df),
                "total_transformed": len(clean_df),
                "total_loaded": load_stats["imported_records"],
                "exact_matches": len(matching_results["exact_matches"]),
                "fuzzy_matches": len(matching_results["fuzzy_matches"]),
                "no_matches": len(matching_results["no_matches"]),
                "data_quality_score": analysis["summary"]["quality_assessment"][
                    "data_quality_score"
                ],
            }

            success_msg = (
                f"✅ Pipeline ETL completado exitosamente para {season}. "
                f"Cargados: {load_stats['imported_records']} registros"
            )

            logger.info(success_msg)
            return True, success_msg, results

        except Exception as e:
            error_msg = f"❌ Error inesperado en pipeline ETL para {season}: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            return False, error_msg, results

    def _execute_extract(self, season: str) -> Tuple[bool, Optional[pd.DataFrame], str]:
        """
        Ejecuta la fase de extracción.

        Args:
            season: Temporada a extraer

        Returns:
            Tuple[success, dataframe, message]
        """
        return self.extractor.download_season_data(season)

    def _execute_transform(
        self, df: pd.DataFrame, season: str
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Ejecuta la fase de transformación.

        Args:
            df: DataFrame crudo
            season: Temporada

        Returns:
            Tuple[clean_dataframe, transform_stats]
        """
        # Validar columnas requeridas
        missing_columns = self.transformer.validate_required_columns(df)

        # Limpiar y normalizar
        clean_df = self.transformer.clean_and_normalize_data(df, season)

        # Aplicar reglas de negocio
        business_df = self.transformer.apply_business_rules(clean_df)

        # Preparar para matching
        final_df = self.transformer.prepare_for_matching(business_df)

        transform_stats = {
            "original_records": len(df),
            "clean_records": len(final_df),
            "missing_columns": missing_columns,
            "data_quality_issues_resolved": len(df) - len(final_df),
        }

        return final_df, transform_stats

    def _execute_validate(
        self, df: pd.DataFrame, season: str
    ) -> Tuple[bool, List[str], Dict]:
        """
        Ejecuta la fase de validación.

        Args:
            df: DataFrame limpio
            season: Temporada

        Returns:
            Tuple[is_valid, errors, stats]
        """
        return self.validator.validate_dataframe(df, season)

    def _execute_matching(self, df: pd.DataFrame, threshold: int) -> Dict:
        """
        Ejecuta la fase de matching usando el controlador original.

        Args:
            df: DataFrame limpio
            threshold: Umbral de matching

        Returns:
            Diccionario con resultados de matching
        """
        # TEMPORAL: Usar el método del controlador original
        # En el futuro esto debería ser un módulo separado
        from controllers.thai_league_controller import ThaiLeagueController

        thai_controller = ThaiLeagueController(self.session_factory)
        return thai_controller.find_matching_players(df, threshold)

    def _execute_load(
        self, season: str, df: pd.DataFrame, matching_results: Dict
    ) -> Tuple[bool, str, Dict]:
        """
        Ejecuta la fase de carga.

        Args:
            season: Temporada
            df: DataFrame limpio
            matching_results: Resultados de matching

        Returns:
            Tuple[success, message, stats]
        """
        column_mapping = self.transformer.get_column_mapping()
        return self.loader.import_season_data(
            season, df, matching_results, column_mapping
        )

    def _execute_analyze(
        self, df: pd.DataFrame, matching_results: Dict, season: str
    ) -> Dict:
        """
        Ejecuta la fase de análisis.

        Args:
            df: DataFrame procesado
            matching_results: Resultados de matching
            season: Temporada

        Returns:
            Diccionario con análisis completo
        """
        # Análisis de datos
        data_analysis = self.analyzer.analyze_dataframe(df, season)

        # Análisis de matching
        matching_report = self.analyzer.generate_matching_report(
            matching_results, season
        )

        # Combinar análisis
        return {
            "data_analysis": data_analysis,
            "matching_report": matching_report,
            "summary": data_analysis["summary"],
        }

    def get_available_seasons(self) -> Dict[str, str]:
        """
        Obtiene temporadas disponibles para procesamiento.

        Returns:
            Dict con temporadas disponibles
        """
        return self.extractor.get_available_seasons()

    def validate_season_before_processing(self, season: str) -> Tuple[bool, str]:
        """
        Valida que una temporada pueda ser procesada.

        Args:
            season: Temporada a validar

        Returns:
            Tuple[can_process, message]
        """
        if not self.extractor.validate_season(season):
            return False, f"Temporada {season} no está disponible"

        # Aquí se podrían agregar más validaciones
        # como verificar si ya está procesada, etc.

        return True, f"Temporada {season} lista para procesamiento"

    def get_processing_status(self, season: str) -> Dict:
        """
        Obtiene el estado actual del procesamiento de una temporada.

        Args:
            season: Temporada a consultar

        Returns:
            Dict con estado del procesamiento
        """
        try:
            with self.session_factory() as session:
                from models import ThaiLeagueSeason

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
                }

        except Exception as e:
            return {
                "season": season,
                "status": "error",
                "message": f"Error consultando estado: {str(e)}",
            }

    def cleanup_and_reprocess(self, season: str) -> Tuple[bool, str]:
        """
        Limpia datos existentes y reprocesa una temporada.

        Args:
            season: Temporada a limpiar y reprocesar

        Returns:
            Tuple[success, message]
        """
        logger.info(f"🧹 Limpiando y reprocesando temporada {season}")

        try:
            # Limpiar datos existentes
            cleanup_success, cleanup_msg = self.loader.cleanup_season_data(season)

            if not cleanup_success:
                return False, f"Error limpiando datos: {cleanup_msg}"

            # Ejecutar pipeline completo
            success, msg, results = self.execute_full_pipeline(
                season, force_reload=True
            )

            if success:
                return True, f"Reprocesamiento exitoso: {msg}"
            else:
                return False, f"Error en reprocesamiento: {msg}"

        except Exception as e:
            error_msg = f"Error inesperado en reprocesamiento de {season}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

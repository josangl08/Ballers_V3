"""
Smart Update Manager - Gestor inteligente de actualizaciones estacionales.

Este módulo migra y mejora la funcionalidad de smart_weekly_update() desde
ThaiLeagueController usando la arquitectura ml_system con metodología CRISP-DM.

Funcionalidades principales:
- Detección automática de temporada activa
- Actualizaciones inteligentes basadas en período del año
- Búsqueda automática de nuevas temporadas
- Lógica estacional para determinar acciones apropiadas
- Integración completa con ETL Coordinator y Season Monitor
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from controllers.db import get_db_session
from ml_system.data_acquisition.extractors.thai_league_extractor import (
    ThaiLeagueExtractor,
)
from ml_system.data_processing.processors.season_monitor import SeasonMonitor
from ml_system.deployment.orchestration.etl_coordinator import ETLCoordinator

logger = logging.getLogger(__name__)


class SmartUpdateManager:
    """
    Gestor inteligente de actualizaciones que migra smart_weekly_update() legacy.

    Implementa lógica estacional avanzada usando metodología CRISP-DM:
    1. Business Understanding - Determinar acción apropiada según período
    2. Data Understanding - Verificar estado de temporadas disponibles
    3. Data Preparation - Preparar datos para procesamiento
    4. Modeling - Aplicar reglas de negocio estacionales
    5. Evaluation - Evaluar necesidad de actualizaciones
    6. Deployment - Ejecutar actualizaciones y reportar resultados
    """

    def __init__(self, session_factory=None):
        """
        Inicializa el Smart Update Manager con componentes ml_system.

        Args:
            session_factory: Factory para sesiones de BD (opcional)
        """
        self.session_factory = session_factory or get_db_session

        # Componentes ml_system integrados
        self.extractor = ThaiLeagueExtractor()
        self.season_monitor = SeasonMonitor()
        self.etl_coordinator = ETLCoordinator(self.session_factory)

        # Configuración de lógica estacional
        self.season_periods = {
            "pre_season": {
                "start_month": 6,
                "end_month": 8,
            },  # Jun-Ago: Búsqueda nueva temporada
            "active_season": {
                "start_month": 9,
                "end_month": 5,
            },  # Sep-May: Actualización activa
            "end_season": {
                "start_month": 6,
                "end_month": 6,
            },  # Jun: Temporada terminada
        }

        logger.info("🧠 Smart Update Manager inicializado con arquitectura ml_system")
        logger.info(
            "📊 Componentes: ThaiLeagueExtractor, SeasonMonitor, ETL Coordinator"
        )

    def execute_smart_weekly_update(self) -> Dict[str, Any]:
        """
        Función principal para actualización semanal inteligente.
        Migración completa de smart_weekly_update() con lógica CRISP-DM.

        Returns:
            Dict con resultado detallado de la operación
        """
        logger.info("=== INICIANDO SMART WEEKLY UPDATE - METODOLOGÍA CRISP-DM ===")

        try:
            start_time = datetime.now()

            # === PHASE 1: BUSINESS UNDERSTANDING ===
            logger.info(
                "🎯 PHASE 1: BUSINESS UNDERSTANDING - Determinando acción estacional..."
            )
            action = self._determine_seasonal_action()

            # === PHASE 2: DATA UNDERSTANDING ===
            logger.info(
                "📊 PHASE 2: DATA UNDERSTANDING - Evaluando estado de temporadas..."
            )
            seasonal_context = self._analyze_seasonal_context(action)

            # === PHASE 3: DATA PREPARATION ===
            logger.info(
                "🧹 PHASE 3: DATA PREPARATION - Preparando datos para acción..."
            )
            preparation_result = self._prepare_data_for_action(action, seasonal_context)

            # === PHASE 4: MODELING ===
            logger.info(
                "🔬 PHASE 4: MODELING - Aplicando lógica de negocio estacional..."
            )
            modeling_result = self._apply_seasonal_business_logic(
                action, preparation_result
            )

            # === PHASE 5: EVALUATION ===
            logger.info(
                "📈 PHASE 5: EVALUATION - Evaluando resultados y necesidades..."
            )
            evaluation_result = self._evaluate_update_needs(modeling_result)

            # === PHASE 6: DEPLOYMENT ===
            logger.info("🚀 PHASE 6: DEPLOYMENT - Ejecutando actualizaciones...")
            deployment_result = self._deploy_updates(evaluation_result)

            # Consolidar resultados CRISP-DM
            end_time = datetime.now()
            execution_time = str(end_time - start_time)

            final_result = {
                "methodology": "CRISP-DM Smart Weekly Update",
                "action": action,
                "success": deployment_result.get("success", False),
                "message": deployment_result.get("message", "Unknown result"),
                "execution_time": execution_time,
                "crisp_dm_phases": {
                    "business_understanding": {"action": action},
                    "data_understanding": seasonal_context,
                    "data_preparation": preparation_result,
                    "modeling": modeling_result,
                    "evaluation": evaluation_result,
                    "deployment": deployment_result,
                },
                "stats": deployment_result.get("stats", {}),
                "seasonal_insights": {
                    "current_period": seasonal_context.get("current_period", "unknown"),
                    "active_seasons": seasonal_context.get("active_seasons", []),
                    "final_seasons": seasonal_context.get("final_seasons", []),
                    "needs_new_season_search": seasonal_context.get(
                        "needs_new_season_search", False
                    ),
                },
            }

            # Registrar resultado final
            if final_result["success"]:
                logger.info(
                    f"✅ Smart Weekly Update completado exitosamente: {final_result['message']}"
                )
            else:
                logger.error(f"❌ Smart Weekly Update falló: {final_result['message']}")

            return final_result

        except Exception as e:
            error_msg = f"Error crítico en Smart Weekly Update: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "methodology": "CRISP-DM Smart Weekly Update",
                "action": "error",
                "success": False,
                "message": error_msg,
                "execution_time": (
                    str(datetime.now() - start_time)
                    if "start_time" in locals()
                    else "0:00:00"
                ),
                "stats": {},
            }

    def _determine_seasonal_action(self) -> str:
        """
        PHASE 1: Determina la acción apropiada según el período estacional.
        Migra determine_season_action() del legacy controller.

        Returns:
            Acción a realizar: 'update_current', 'search_new_season', 'season_ended'
        """
        try:
            current_date = datetime.now()
            current_month = current_date.month

            # Detectar período estacional
            if self._is_pre_season_period(current_month):
                logger.info("🔍 Pre-season detectada: Buscar nueva temporada")
                return "search_new_season"

            elif self._is_active_season_period(current_month):
                logger.info(
                    "🔄 Temporada activa detectada: Actualizar temporada actual"
                )
                return "update_current"

            elif self._is_end_season_period(current_month):
                logger.info("⏹️ Fin de temporada detectada: Sin actualizaciones")
                return "season_ended"

            else:
                # Fallback por defecto
                logger.warning(
                    f"Período desconocido ({current_month}), usando actualización por defecto"
                )
                return "update_current"

        except Exception as e:
            logger.error(f"Error determinando acción estacional: {e}")
            return "update_current"  # Fallback conservador

    def _analyze_seasonal_context(self, action: str) -> Dict[str, Any]:
        """
        PHASE 2: Analiza el contexto estacional para la acción determinada.

        Args:
            action: Acción estacional determinada

        Returns:
            Dict con contexto estacional detallado
        """
        try:
            # Obtener estado de temporadas usando SeasonMonitor
            monitoring_status = self.season_monitor.get_monitoring_status()

            current_date = datetime.now()

            context = {
                "action": action,
                "current_date": current_date.isoformat(),
                "current_month": current_date.month,
                "current_period": self._get_current_period_name(current_date.month),
                "active_seasons": monitoring_status.get("seasons_state", {}).get(
                    "active_seasons", []
                ),
                "final_seasons": monitoring_status.get("seasons_state", {}).get(
                    "final_seasons", []
                ),
                "total_available": monitoring_status.get("seasons_state", {}).get(
                    "total_available", 0
                ),
                "needs_monitoring_check": monitoring_status.get("monitor_info", {}).get(
                    "needs_check", True
                ),
                "last_monitor_check": monitoring_status.get("monitor_info", {}).get(
                    "last_check"
                ),
                "needs_new_season_search": action == "search_new_season",
            }

            logger.info(
                f"📊 Contexto estacional: Período {context['current_period']}, {len(context['active_seasons'])} activas, {len(context['final_seasons'])} finales"
            )

            return context

        except Exception as e:
            logger.error(f"Error analizando contexto estacional: {e}")
            return {
                "action": action,
                "error": str(e),
                "active_seasons": [],
                "final_seasons": [],
            }

    def _prepare_data_for_action(
        self, action: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        PHASE 3: Prepara datos necesarios para ejecutar la acción estacional.

        Args:
            action: Acción a realizar
            context: Contexto estacional

        Returns:
            Dict con datos preparados
        """
        try:
            preparation_result = {
                "action": action,
                "data_ready": False,
                "current_season": None,
                "target_seasons": [],
                "registered_players": [],
                "preparation_details": {},
            }

            if action == "update_current":
                # Preparar para actualización de temporada actual
                current_season = self._identify_current_season()
                if current_season:
                    preparation_result.update(
                        {
                            "data_ready": True,
                            "current_season": current_season,
                            "target_seasons": [current_season],
                            "preparation_details": {
                                "update_type": "incremental",
                                "target_season": current_season,
                            },
                        }
                    )
                    logger.info(
                        f"🔄 Datos preparados para actualizar temporada actual: {current_season}"
                    )
                else:
                    logger.warning(
                        "⚠️ No se pudo identificar temporada actual para actualización"
                    )

            elif action == "search_new_season":
                # Preparar para búsqueda de nueva temporada
                registered_players = self._get_registered_professional_players()
                preparation_result.update(
                    {
                        "data_ready": True,
                        "registered_players": registered_players,
                        "preparation_details": {
                            "search_type": "new_season_detection",
                            "registered_players_count": len(registered_players),
                        },
                    }
                )
                logger.info(
                    f"🔍 Datos preparados para búsqueda nueva temporada: {len(registered_players)} jugadores profesionales"
                )

            elif action == "season_ended":
                # Sin preparación necesaria
                preparation_result.update(
                    {
                        "data_ready": True,
                        "preparation_details": {
                            "action_type": "no_action_needed",
                            "reason": "season_ended",
                        },
                    }
                )
                logger.info("⏹️ Sin preparación necesaria - temporada terminada")

            return preparation_result

        except Exception as e:
            logger.error(f"Error preparando datos para acción {action}: {e}")
            return {"action": action, "data_ready": False, "error": str(e)}

    def _apply_seasonal_business_logic(
        self, action: str, preparation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        PHASE 4: Aplica reglas de negocio específicas según la lógica estacional.

        Args:
            action: Acción estacional
            preparation: Datos preparados

        Returns:
            Dict con resultado de aplicación de lógica de negocio
        """
        try:
            modeling_result = {
                "action": action,
                "business_rules_applied": True,
                "modeling_success": False,
                "recommendations": [],
                "processing_plan": {},
            }

            if not preparation.get("data_ready", False):
                modeling_result.update(
                    {
                        "business_rules_applied": False,
                        "modeling_success": False,
                        "error": "Data preparation failed",
                    }
                )
                return modeling_result

            if action == "update_current":
                # Aplicar lógica para actualización incremental
                current_season = preparation.get("current_season")
                if current_season:
                    modeling_result.update(
                        {
                            "modeling_success": True,
                            "recommendations": [
                                "incremental_update",
                                "verify_data_quality",
                            ],
                            "processing_plan": {
                                "type": "incremental_update",
                                "target_season": current_season,
                                "force_reload": False,
                                "calculate_pdi": True,
                                "threshold": 85,
                            },
                        }
                    )
                    logger.info(
                        f"🔬 Lógica aplicada para actualización incremental: {current_season}"
                    )

            elif action == "search_new_season":
                # Aplicar lógica para búsqueda de nueva temporada
                registered_count = len(preparation.get("registered_players", []))
                modeling_result.update(
                    {
                        "modeling_success": True,
                        "recommendations": ["detect_new_season", "process_if_found"],
                        "processing_plan": {
                            "type": "new_season_search",
                            "registered_players_count": registered_count,
                            "auto_process_new_season": registered_count > 0,
                            "threshold": 85,
                        },
                    }
                )
                logger.info(
                    f"🔬 Lógica aplicada para búsqueda nueva temporada: {registered_count} jugadores profesionales"
                )

            elif action == "season_ended":
                # Sin lógica de negocio activa
                modeling_result.update(
                    {
                        "modeling_success": True,
                        "recommendations": ["no_action"],
                        "processing_plan": {
                            "type": "no_action",
                            "reason": "season_ended_period",
                        },
                    }
                )
                logger.info("🔬 Lógica aplicada: Sin acciones - temporada terminada")

            return modeling_result

        except Exception as e:
            logger.error(f"Error aplicando lógica de negocio para {action}: {e}")
            return {
                "action": action,
                "business_rules_applied": False,
                "modeling_success": False,
                "error": str(e),
            }

    def _evaluate_update_needs(self, modeling: Dict[str, Any]) -> Dict[str, Any]:
        """
        PHASE 5: Evalúa si son necesarias las actualizaciones basándose en el modelado.

        Args:
            modeling: Resultado del modelado estacional

        Returns:
            Dict con evaluación de necesidades
        """
        try:
            evaluation = {
                "action": modeling.get("action"),
                "updates_needed": False,
                "evaluation_success": False,
                "update_recommendations": [],
                "execution_plan": {},
            }

            if not modeling.get("modeling_success", False):
                evaluation.update(
                    {"evaluation_success": False, "error": "Modeling phase failed"}
                )
                return evaluation

            processing_plan = modeling.get("processing_plan", {})
            action = modeling.get("action")

            if action == "update_current":
                # Evaluar necesidad de actualización incremental
                current_season = processing_plan.get("target_season")
                if current_season:
                    # Verificar si hay actualizaciones disponibles
                    has_updates = self.extractor.check_for_updates(current_season)
                    evaluation.update(
                        {
                            "updates_needed": has_updates,
                            "evaluation_success": True,
                            "update_recommendations": (
                                ["execute_incremental_update"]
                                if has_updates
                                else ["no_update_needed"]
                            ),
                            "execution_plan": {
                                "type": "etl_pipeline",
                                "season": current_season,
                                "threshold": processing_plan.get("threshold", 85),
                                "calculate_pdi": processing_plan.get(
                                    "calculate_pdi", True
                                ),
                                "force_reload": has_updates,
                            },
                        }
                    )
                    logger.info(
                        f"📈 Evaluación temporada actual {current_season}: Updates needed = {has_updates}"
                    )

            elif action == "search_new_season":
                # Evaluar necesidad de búsqueda
                evaluation.update(
                    {
                        "updates_needed": True,  # Siempre buscar en período pre-season
                        "evaluation_success": True,
                        "update_recommendations": [
                            "search_new_season",
                            "process_if_found",
                        ],
                        "execution_plan": {
                            "type": "new_season_search",
                            "auto_process": processing_plan.get(
                                "auto_process_new_season", False
                            ),
                            "threshold": processing_plan.get("threshold", 85),
                        },
                    }
                )
                logger.info(
                    "📈 Evaluación búsqueda nueva temporada: Proceder con búsqueda"
                )

            elif action == "season_ended":
                # Sin actualizaciones necesarias
                evaluation.update(
                    {
                        "updates_needed": False,
                        "evaluation_success": True,
                        "update_recommendations": ["no_action"],
                        "execution_plan": {
                            "type": "no_action",
                            "reason": "season_ended",
                        },
                    }
                )
                logger.info(
                    "📈 Evaluación temporada terminada: Sin actualizaciones necesarias"
                )

            return evaluation

        except Exception as e:
            logger.error(f"Error evaluando necesidades de actualización: {e}")
            return {
                "action": modeling.get("action", "unknown"),
                "updates_needed": False,
                "evaluation_success": False,
                "error": str(e),
            }

    def _deploy_updates(self, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """
        PHASE 6: Ejecuta las actualizaciones basándose en la evaluación.

        Args:
            evaluation: Evaluación de necesidades

        Returns:
            Dict con resultado del deployment
        """
        try:
            deployment = {
                "action": evaluation.get("action"),
                "success": False,
                "message": "No deployment executed",
                "stats": {},
                "deployment_details": {},
            }

            if not evaluation.get("evaluation_success", False):
                deployment.update(
                    {
                        "success": False,
                        "message": "Evaluation phase failed",
                        "error": evaluation.get("error", "Unknown evaluation error"),
                    }
                )
                return deployment

            if not evaluation.get("updates_needed", False):
                deployment.update(
                    {
                        "success": True,
                        "message": "No updates needed - system up to date",
                        "stats": {"action": "no_action_needed"},
                    }
                )
                return deployment

            execution_plan = evaluation.get("execution_plan", {})
            plan_type = execution_plan.get("type")

            if plan_type == "etl_pipeline":
                # Ejecutar ETL pipeline para actualización incremental
                season = execution_plan.get("season")
                threshold = execution_plan.get("threshold", 85)
                calculate_pdi = execution_plan.get("calculate_pdi", True)
                force_reload = execution_plan.get("force_reload", False)

                logger.info(f"🚀 Ejecutando ETL pipeline para {season}")
                success, message, results = (
                    self.etl_coordinator.execute_full_crisp_dm_pipeline(
                        season=season,
                        threshold=threshold,
                        force_reload=force_reload,
                        calculate_pdi=calculate_pdi,
                    )
                )

                deployment.update(
                    {
                        "success": success,
                        "message": message,
                        "stats": results.get("final_stats", {}),
                        "deployment_details": {
                            "type": "etl_pipeline",
                            "season": season,
                            "pipeline_results": results,
                        },
                    }
                )

            elif plan_type == "new_season_search":
                # Ejecutar búsqueda de nueva temporada
                logger.info("🚀 Ejecutando búsqueda de nueva temporada")
                search_result = self._execute_new_season_search(execution_plan)

                deployment.update(
                    {
                        "success": search_result.get("success", False),
                        "message": search_result.get(
                            "message", "New season search completed"
                        ),
                        "stats": search_result.get("stats", {}),
                        "deployment_details": {
                            "type": "new_season_search",
                            "search_results": search_result,
                        },
                    }
                )

            elif plan_type == "no_action":
                # Sin acción requerida
                deployment.update(
                    {
                        "success": True,
                        "message": f"No action required - {execution_plan.get('reason', 'unknown reason')}",
                        "stats": {"action": "no_action"},
                        "deployment_details": {
                            "type": "no_action",
                            "reason": execution_plan.get("reason"),
                        },
                    }
                )

            else:
                deployment.update(
                    {
                        "success": False,
                        "message": f"Unknown execution plan type: {plan_type}",
                        "error": f"Unsupported plan type: {plan_type}",
                    }
                )

            return deployment

        except Exception as e:
            logger.error(f"Error ejecutando deployment: {e}")
            return {
                "action": evaluation.get("action", "unknown"),
                "success": False,
                "message": f"Deployment failed: {str(e)}",
                "error": str(e),
                "stats": {},
            }

    def _execute_new_season_search(
        self, execution_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ejecuta búsqueda de nueva temporada e importación automática si corresponde.

        Args:
            execution_plan: Plan de ejecución para búsqueda

        Returns:
            Dict con resultado de la búsqueda
        """
        try:
            # Buscar nueva temporada usando extractor
            new_seasons = self._search_for_new_seasons()

            if not new_seasons:
                return {
                    "success": True,
                    "message": "No new seasons found",
                    "stats": {"new_seasons_found": 0},
                    "new_seasons": [],
                }

            # Procesar nueva temporada si se encuentra
            new_season = new_seasons[0]  # Tomar la primera nueva temporada
            registered_players = self._get_registered_professional_players()

            if not registered_players:
                return {
                    "success": True,
                    "message": f"New season {new_season} found but no professional players registered",
                    "stats": {"new_seasons_found": 1, "processed": 0},
                    "new_season": new_season,
                }

            # Ejecutar ETL pipeline para nueva temporada
            logger.info(
                f"🚀 Procesando nueva temporada {new_season} para {len(registered_players)} jugadores"
            )
            success, message, results = (
                self.etl_coordinator.execute_full_crisp_dm_pipeline(
                    season=new_season,
                    threshold=execution_plan.get("threshold", 85),
                    force_reload=True,  # Nueva temporada requiere carga completa
                    calculate_pdi=True,
                )
            )

            return {
                "success": success,
                "message": f"New season {new_season}: {message}",
                "stats": results.get("final_stats", {}),
                "new_season": new_season,
                "pipeline_results": results,
            }

        except Exception as e:
            logger.error(f"Error executing new season search: {e}")
            return {
                "success": False,
                "message": f"New season search failed: {str(e)}",
                "error": str(e),
                "stats": {},
            }

    # === MÉTODOS AUXILIARES ===

    def _is_pre_season_period(self, month: int) -> bool:
        """Verifica si estamos en período pre-temporada (Jun-Ago)."""
        return (
            self.season_periods["pre_season"]["start_month"]
            <= month
            <= self.season_periods["pre_season"]["end_month"]
        )

    def _is_active_season_period(self, month: int) -> bool:
        """Verifica si estamos en período de temporada activa (Sep-May)."""
        start = self.season_periods["active_season"]["start_month"]
        end = self.season_periods["active_season"]["end_month"]
        return month >= start or month <= end

    def _is_end_season_period(self, month: int) -> bool:
        """Verifica si estamos en período de fin de temporada."""
        return month == self.season_periods["end_season"]["start_month"]

    def _get_current_period_name(self, month: int) -> str:
        """Obtiene el nombre del período actual."""
        if self._is_pre_season_period(month):
            return "pre_season"
        elif self._is_active_season_period(month):
            return "active_season"
        elif self._is_end_season_period(month):
            return "end_season"
        else:
            return "unknown"

    def _identify_current_season(self) -> Optional[str]:
        """Identifica la temporada actual usando lógica migrada."""
        try:
            current_year = datetime.now().year
            for season in self.extractor.AVAILABLE_SEASONS.keys():
                season_years = season.split("-")
                if len(season_years) == 2:
                    start_year = int(f"20{season_years[0]}")
                    if start_year == current_year or start_year == current_year - 1:
                        logger.info(f"🎯 Temporada actual identificada: {season}")
                        return season

            logger.warning("⚠️ No se pudo identificar temporada actual")
            return None

        except Exception as e:
            logger.error(f"Error identificando temporada actual: {e}")
            return None

    def _get_registered_professional_players(self) -> List[int]:
        """Obtiene lista de jugadores profesionales registrados."""
        try:
            with self.session_factory() as session:
                from models.player_model import Player

                professional_players = (
                    session.query(Player.player_id)
                    .filter(Player.is_professional == True)
                    .filter(Player.wyscout_id.isnot(None))
                    .all()
                )

                player_ids = [player.player_id for player in professional_players]
                logger.info(
                    f"👥 {len(player_ids)} jugadores profesionales registrados encontrados"
                )
                return player_ids

        except Exception as e:
            logger.error(f"Error obteniendo jugadores profesionales: {e}")
            return []

    def _search_for_new_seasons(self) -> List[str]:
        """Busca nuevas temporadas disponibles."""
        try:
            # Obtener temporadas disponibles vs importadas
            available_seasons = set(self.extractor.AVAILABLE_SEASONS.keys())

            with self.session_factory() as session:
                from models.thai_league_seasons_model import ThaiLeagueSeason

                imported_seasons = set(
                    season.season
                    for season in session.query(ThaiLeagueSeason.season).all()
                )

            new_seasons = list(available_seasons - imported_seasons)

            if new_seasons:
                logger.info(
                    f"🆕 {len(new_seasons)} nuevas temporadas encontradas: {new_seasons}"
                )
            else:
                logger.info("ℹ️ No se encontraron nuevas temporadas")

            return sorted(new_seasons)

        except Exception as e:
            logger.error(f"Error buscando nuevas temporadas: {e}")
            return []

    def get_smart_update_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del sistema de Smart Updates.

        Returns:
            Dict con estado completo del sistema
        """
        try:
            current_date = datetime.now()
            current_month = current_date.month

            status = {
                "system_info": {
                    "current_date": current_date.isoformat(),
                    "current_month": current_month,
                    "current_period": self._get_current_period_name(current_month),
                    "suggested_action": self._determine_seasonal_action(),
                },
                "seasonal_periods": self.season_periods,
                "components_status": {
                    "extractor_available": bool(self.extractor),
                    "season_monitor_available": bool(self.season_monitor),
                    "etl_coordinator_available": bool(self.etl_coordinator),
                },
                "season_analysis": {},
                "registered_players": {
                    "count": len(self._get_registered_professional_players()),
                    "professional_players": True,
                },
            }

            # Añadir análisis de temporadas
            try:
                monitoring_status = self.season_monitor.get_monitoring_status()
                status["season_analysis"] = monitoring_status.get("seasons_state", {})
            except Exception as e:
                logger.warning(f"Error obteniendo análisis de temporadas: {e}")
                status["season_analysis"] = {"error": str(e)}

            return status

        except Exception as e:
            logger.error(f"Error obteniendo estado Smart Update: {e}")
            return {"error": str(e), "system_available": False}


# Funciones de conveniencia para compatibilidad con sync_coordinator
def execute_smart_weekly_update() -> Dict[str, Any]:
    """
    Función de conveniencia para ejecutar Smart Weekly Update.
    Permite compatibilidad directa con sync_coordinator.

    Returns:
        Dict con resultado de la actualización semanal
    """
    manager = SmartUpdateManager()
    return manager.execute_smart_weekly_update()


def get_smart_update_system_status() -> Dict[str, Any]:
    """
    Función de conveniencia para obtener estado del sistema.

    Returns:
        Dict con estado completo del sistema Smart Update
    """
    manager = SmartUpdateManager()
    return manager.get_smart_update_status()

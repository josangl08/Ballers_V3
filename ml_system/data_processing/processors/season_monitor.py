#!/usr/bin/env python3
"""
SeasonMonitor - Monitor inteligente de temporadas que REUTILIZA ThaiLeagueExtractor
Sistema de monitoreo automático que detecta cambios en temporadas activas sin duplicar funcionalidad.

Este módulo REUTILIZA completamente ThaiLeagueExtractor existente:
1. _is_current_season() - Detección de temporada activa
2. auto_update_current_season() - Monitor automático de updates
3. check_for_updates() - Verificación de cambios
4. Arquitectura webhook existente para triggers

NO duplica funcionalidad, sino que la ORQUESTA de manera inteligente.

Autor: Proyecto Fin de Máster - Python Aplicado al Deporte
Fecha: Agosto 2025
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Configurar path del proyecto
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

import pandas as pd

from controllers.webhook_controller import WebhookController

# Importar arquitectura existente (NO duplicar)
from ml_system.data_acquisition.extractors import ThaiLeagueExtractor

# Importar utilidades consolidadas
from ml_system.deployment.utils.script_utils import (
    format_execution_time,
    print_header,
    setup_analysis_logging,
)

# Importar preprocessor para updates
from .batch_processor import BatchProcessor

logger = logging.getLogger(__name__)


class SeasonMonitor:
    """
    Monitor inteligente que REUTILIZA ThaiLeagueExtractor existente.

    No duplica funcionalidad, sino que aprovecha:
    - _is_current_season() para detectar temporada activa
    - auto_update_current_season() para monitoreo automático
    - Sistema webhook existente para triggers en tiempo real
    """

    def __init__(self, check_interval_hours: int = 24):
        """
        Inicializa SeasonMonitor reutilizando controladores existentes.

        Args:
            check_interval_hours: Intervalo entre verificaciones automáticas
        """
        # REUTILIZAR controladores existentes (NO crear nuevos)
        self.thai_controller = ThaiLeagueExtractor()
        self.batch_processor = BatchProcessor()

        # Configurar parámetros de monitoreo
        self.check_interval_hours = check_interval_hours
        self.project_root = project_root
        self.processed_dir = self.project_root / "data" / "thai_league_processed"

        # Cache de estado de monitoreo
        self.monitoring_cache = {
            "last_check": None,
            "active_seasons": set(),
            "final_seasons": set(),
            "last_updates": {},
        }

        # Configurar logging
        self.logger = setup_analysis_logging("season_monitor")

        logger.info("🔍 SeasonMonitor inicializado reutilizando ThaiLeagueExtractor")

        # Inicializar estado de temporadas
        self._initialize_season_states()

    def monitor_all_seasons(self, force_check: bool = False) -> Dict[str, Any]:
        """
        Monitorea TODAS las temporadas de manera inteligente.

        Temporadas finales: No monitoreo (cache permanente)
        Temporadas activas: Monitoreo automático con ThaiLeagueExtractor

        Args:
            force_check: Si forzar verificación incluso si no toca

        Returns:
            Dict con resultado del monitoreo
        """
        try:
            start_time = datetime.now()
            print_header("🔍 MONITOREO INTELIGENTE DE TEMPORADAS", "=", 70)

            self.logger.info("Iniciando monitoreo usando ThaiLeagueExtractor existente")

            # Verificar si necesita chequeo
            if not force_check and not self._needs_monitoring_check():
                self.logger.info("⚡ Monitoreo reciente, omitiendo verificación")
                return {
                    "success": True,
                    "message": "Monitoreo reciente, no necesario",
                    "last_check": self.monitoring_cache.get("last_check"),
                    "skipped": True,
                }

            # Actualizar estado de temporadas
            self._refresh_season_states()

            results = {
                "start_time": start_time,
                "seasons_monitored": {},
                "updates_needed": {},
                "updates_completed": {},
                "summary": {},
            }

            # Monitorear temporadas activas usando ThaiLeagueExtractor
            active_seasons = self.monitoring_cache["active_seasons"]

            if active_seasons:
                self.logger.info(
                    f"🔍 Monitoreando temporadas activas: {active_seasons}"
                )

                for season in active_seasons:
                    season_result = self._monitor_season_with_thai_controller(season)
                    results["seasons_monitored"][season] = season_result

                    if season_result.get("needs_update", False):
                        results["updates_needed"][season] = season_result

                        # Ejecutar actualización automática
                        if season_result.get("auto_update", True):
                            update_result = self._execute_season_update(season)
                            results["updates_completed"][season] = update_result
            else:
                self.logger.info("ℹ️ No hay temporadas activas que monitorear")

            # Actualizar timestamp de último chequeo
            self.monitoring_cache["last_check"] = datetime.now()

            # Generar resumen
            execution_time = format_execution_time(start_time)
            results["summary"] = {
                "execution_time": execution_time,
                "active_seasons": len(active_seasons),
                "final_seasons": len(self.monitoring_cache["final_seasons"]),
                "updates_needed": len(results["updates_needed"]),
                "updates_completed": len(results["updates_completed"]),
            }

            # Mostrar resumen
            print_header("✅ MONITOREO COMPLETADO", "=", 70)
            print(f"⏱️  Tiempo: {execution_time}")
            print(f"🔍 Temporadas activas monitoreadas: {len(active_seasons)}")
            print(f"📊 Updates necesarios: {len(results['updates_needed'])}")
            print(f"✅ Updates completados: {len(results['updates_completed'])}")

            return results

        except Exception as e:
            self.logger.error(f"Error en monitoreo: {e}")
            raise

    def check_season_updates(self, season: str) -> Dict[str, Any]:
        """
        Verifica si una temporada específica necesita actualización.
        REUTILIZA ThaiLeagueExtractor.check_for_updates() existente.

        Args:
            season: Temporada a verificar

        Returns:
            Dict con resultado de la verificación
        """
        try:
            self.logger.info(f"🔍 Verificando updates para {season}")

            # REUTILIZAR método existente de ThaiLeagueExtractor
            has_updates = self.thai_controller.check_for_updates(season)

            # Información adicional sobre estado de archivos
            raw_file = (
                self.project_root
                / "data"
                / "thai_league_cache"
                / f"thai_league_{season}.csv"
            )
            processed_file = self.processed_dir / f"processed_{season}.csv"

            file_info = {
                "raw_exists": raw_file.exists(),
                "processed_exists": processed_file.exists(),
                "raw_modified": None,
                "processed_modified": None,
                "needs_processing": False,
            }

            if raw_file.exists():
                file_info["raw_modified"] = datetime.fromtimestamp(
                    raw_file.stat().st_mtime
                )

            if processed_file.exists():
                file_info["processed_modified"] = datetime.fromtimestamp(
                    processed_file.stat().st_mtime
                )

                # Verificar si raw es más nuevo que processed
                if file_info["raw_modified"] and file_info["processed_modified"]:
                    file_info["needs_processing"] = (
                        file_info["raw_modified"] > file_info["processed_modified"]
                    )
            else:
                file_info["needs_processing"] = file_info["raw_exists"]

            result = {
                "season": season,
                "has_remote_updates": has_updates,
                "needs_processing": file_info["needs_processing"],
                "file_info": file_info,
                "is_active_season": self._is_active_season_cached(season),
                "recommendation": self._get_update_recommendation(
                    has_updates, file_info, season
                ),
            }

            self.logger.info(
                f"📊 {season}: Remote={has_updates}, Processing={file_info['needs_processing']}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Error verificando {season}: {e}")
            return {
                "season": season,
                "error": str(e),
                "has_remote_updates": False,
                "needs_processing": False,
            }

    def _initialize_season_states(self):
        """
        Inicializa el estado de temporadas usando ThaiLeagueExtractor._is_current_season().
        """
        try:
            self.logger.info("🔄 Inicializando estado de temporadas")

            available_seasons = list(self.thai_controller.AVAILABLE_SEASONS.keys())
            active_seasons = set()
            final_seasons = set()

            for season in available_seasons:
                # REUTILIZAR método existente de ThaiLeagueExtractor
                if self.thai_controller._is_current_season(season):
                    active_seasons.add(season)
                    self.logger.info(f"🔄 Temporada activa detectada: {season}")
                else:
                    final_seasons.add(season)
                    self.logger.info(f"✅ Temporada final: {season}")

            # Actualizar cache
            self.monitoring_cache["active_seasons"] = active_seasons
            self.monitoring_cache["final_seasons"] = final_seasons

            self.logger.info(
                f"📊 Estado inicializado: {len(active_seasons)} activas, {len(final_seasons)} finales"
            )

        except Exception as e:
            self.logger.error(f"Error inicializando estados: {e}")
            # Fallback conservador
            self.monitoring_cache["active_seasons"] = set()
            self.monitoring_cache["final_seasons"] = set(
                self.thai_controller.AVAILABLE_SEASONS.keys()
            )

    def _refresh_season_states(self):
        """Refresca el estado de temporadas periódicamente."""
        try:
            # Re-detectar temporadas activas
            current_active = set()

            for season in self.thai_controller.AVAILABLE_SEASONS.keys():
                if self.thai_controller._is_current_season(season):
                    current_active.add(season)

            # Detectar cambios en estado
            previous_active = self.monitoring_cache["active_seasons"]

            newly_active = current_active - previous_active
            newly_final = previous_active - current_active

            if newly_active:
                self.logger.info(f"🆕 Nuevas temporadas activas: {newly_active}")

            if newly_final:
                self.logger.info(f"✅ Temporadas ahora finales: {newly_final}")
                # Mover de activas a finales
                self.monitoring_cache["final_seasons"].update(newly_final)

            # Actualizar estado
            self.monitoring_cache["active_seasons"] = current_active

        except Exception as e:
            self.logger.warning(f"Error refrescando estados: {e}")

    def _monitor_season_with_thai_controller(self, season: str) -> Dict[str, Any]:
        """
        Monitorea una temporada específica usando ThaiLeagueExtractor.
        REUTILIZA auto_update_current_season() existente.
        """
        try:
            self.logger.info(f"🔍 Monitoreando {season} con ThaiLeagueExtractor")

            # REUTILIZAR método existente de auto-update
            update_success, update_message, update_data = (
                self.thai_controller.auto_update_current_season()
            )

            # Verificar estado de archivos procesados
            processed_file = self.processed_dir / f"processed_{season}.csv"
            needs_reprocessing = self._needs_reprocessing(season)

            result = {
                "season": season,
                "remote_check_success": update_success,
                "remote_message": update_message,
                "remote_data": update_data,
                "needs_update": needs_reprocessing,
                "processed_file_exists": processed_file.exists(),
                "auto_update": True,  # Por defecto, auto-actualizar
                "last_checked": datetime.now().isoformat(),
            }

            # Actualizar cache de último update
            self.monitoring_cache["last_updates"][season] = result

            return result

        except Exception as e:
            self.logger.error(f"Error monitoreando {season}: {e}")
            return {
                "season": season,
                "error": str(e),
                "needs_update": False,
                "auto_update": False,
            }

    def _execute_season_update(self, season: str) -> Dict[str, Any]:
        """
        Ejecuta actualización automática de una temporada usando BatchProcessor.
        """
        try:
            self.logger.info(f"🔄 Ejecutando actualización automática para {season}")

            # Usar BatchProcessor para procesar la temporada actualizada
            update_result = self.batch_processor.preprocess_season_with_ml(
                season, force_reprocess=True  # Forzar porque sabemos que hay cambios
            )

            if update_result.get("success", False):
                self.logger.info(f"✅ {season} actualizada exitosamente")

                # Regenerar cache completo si es necesario
                if not update_result.get("skipped", False):
                    cache_result = self.batch_processor._generate_complete_cache()
                    update_result["cache_regenerated"] = cache_result.get(
                        "success", False
                    )

            return update_result

        except Exception as e:
            self.logger.error(f"Error ejecutando update para {season}: {e}")
            return {"success": False, "season": season, "error": str(e)}

    def _needs_monitoring_check(self) -> bool:
        """Verifica si necesita hacer chequeo de monitoreo basado en intervalo."""
        last_check = self.monitoring_cache.get("last_check")

        if not last_check:
            return True

        time_since_check = datetime.now() - last_check
        return time_since_check > timedelta(hours=self.check_interval_hours)

    def _is_active_season_cached(self, season: str) -> bool:
        """Verifica si es temporada activa usando cache."""
        return season in self.monitoring_cache["active_seasons"]

    def _needs_reprocessing(self, season: str) -> bool:
        """
        Determina si una temporada necesita reprocesamiento.
        Combina verificación remota + estado de archivos locales.
        """
        try:
            processed_file = self.processed_dir / f"processed_{season}.csv"

            # Si no existe archivo procesado, definitivamente necesita procesamiento
            if not processed_file.exists():
                return True

            # Para temporadas activas, verificar antigüedad
            if self._is_active_season_cached(season):
                processed_time = datetime.fromtimestamp(processed_file.stat().st_mtime)
                age_hours = (datetime.now() - processed_time).total_seconds() / 3600

                # Si tiene más de 24 horas, reprocesar
                return age_hours > 24

            # Temporadas finales normalmente no necesitan reprocesamiento
            return False

        except Exception as e:
            self.logger.warning(f"Error verificando reprocesamiento {season}: {e}")
            return True  # En caso de duda, procesar

    def _get_update_recommendation(
        self, has_remote_updates: bool, file_info: Dict, season: str
    ) -> str:
        """Genera recomendación de acción basada en estado."""
        if has_remote_updates and file_info["needs_processing"]:
            return "update_and_reprocess"
        elif has_remote_updates:
            return "download_update"
        elif file_info["needs_processing"]:
            return "reprocess_only"
        elif self._is_active_season_cached(season):
            return "monitor_continue"
        else:
            return "no_action_needed"

    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Obtiene estado actual completo del sistema de monitoreo.
        """
        try:
            status = {
                "monitor_info": {
                    "check_interval_hours": self.check_interval_hours,
                    "last_check": self.monitoring_cache.get("last_check"),
                    "needs_check": self._needs_monitoring_check(),
                },
                "seasons_state": {
                    "active_seasons": list(self.monitoring_cache["active_seasons"]),
                    "final_seasons": list(self.monitoring_cache["final_seasons"]),
                    "total_available": len(self.thai_controller.AVAILABLE_SEASONS),
                },
                "recent_updates": dict(
                    list(self.monitoring_cache["last_updates"].items())[-5:]
                ),
                "system_health": {
                    "thai_controller_available": bool(self.thai_controller),
                    "batch_processor_available": bool(self.batch_processor),
                    "processed_dir_exists": self.processed_dir.exists(),
                },
            }

            return status

        except Exception as e:
            self.logger.error(f"Error obteniendo estado: {e}")
            return {"error": str(e)}


# Funciones de conveniencia para uso directo
def monitor_seasons(force_check: bool = False) -> Dict[str, Any]:
    """
    Función de conveniencia para ejecutar monitoreo completo.

    Args:
        force_check: Si forzar verificación inmediata

    Returns:
        Dict con resultados del monitoreo
    """
    monitor = SeasonMonitor()
    return monitor.monitor_all_seasons(force_check=force_check)


def check_season_status(season: str) -> Dict[str, Any]:
    """
    Función de conveniencia para verificar una temporada específica.

    Args:
        season: Temporada a verificar

    Returns:
        Dict con estado de la temporada
    """
    monitor = SeasonMonitor()
    return monitor.check_season_updates(season)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="SeasonMonitor - Monitoreo inteligente de temporadas"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Ejecutar verificación de todas las temporadas",
    )
    parser.add_argument("--season", type=str, help="Verificar temporada específica")
    parser.add_argument(
        "--status", action="store_true", help="Mostrar estado del sistema de monitoreo"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forzar verificación incluso si es reciente",
    )

    args = parser.parse_args()

    monitor = SeasonMonitor()

    if args.status:
        print("📊 Estado del sistema de monitoreo:")
        status = monitor.get_monitoring_status()
        print(
            f"   • Temporadas activas: {len(status['seasons_state']['active_seasons'])}"
        )
        print(
            f"   • Temporadas finales: {len(status['seasons_state']['final_seasons'])}"
        )
        print(f"   • Último chequeo: {status['monitor_info']['last_check']}")

    elif args.season:
        print(f"🔍 Verificando temporada: {args.season}")
        result = check_season_status(args.season)
        print(f"   • Updates remotos: {result.get('has_remote_updates', False)}")
        print(f"   • Necesita procesamiento: {result.get('needs_processing', False)}")
        print(f"   • Recomendación: {result.get('recommendation', 'N/A')}")

    elif args.check:
        print("🔍 Ejecutando monitoreo completo...")
        results = monitor_seasons(args.force)
        summary = results.get("summary", {})
        print(f"✅ Monitoreo completado:")
        print(f"   • Temporadas activas: {summary.get('active_seasons', 0)}")
        print(f"   • Updates necesarios: {summary.get('updates_needed', 0)}")
        print(f"   • Updates completados: {summary.get('updates_completed', 0)}")

    else:
        print("🔍 SeasonMonitor - Sistema de monitoreo inteligente")
        print("Uso: --check, --season TEMPORADA, --status, --force")
        print("Ejemplo: python season_monitor.py --check --force")

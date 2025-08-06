"""
Loader Module - Carga de datos a la base de datos
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from controllers.db import get_db_session
from models import ImportStatus, ProfessionalStats, ThaiLeagueSeason

logger = logging.getLogger(__name__)


class ThaiLeagueLoader:
    """
    Cargador para datos de la liga tailandesa hacia la base de datos.
    Maneja inserción, actualización y manejo de errores de BD.
    """

    def __init__(self, session_factory=None):
        """
        Inicializa el loader.

        Args:
            session_factory: Factory para sesiones de BD (opcional)
        """
        self.session_factory = session_factory or get_db_session

    def import_season_data(
        self,
        season: str,
        df: pd.DataFrame,
        matching_results: Dict,
        column_mapping: Dict,
    ) -> Tuple[bool, str, Dict]:
        """
        Importa datos de una temporada a la base de datos.

        Args:
            season: Temporada en formato "2024-25"
            df: DataFrame con datos limpios
            matching_results: Resultados del matching de jugadores
            column_mapping: Mapping de columnas CSV a BD

        Returns:
            Tuple[success, message, statistics]
        """
        logger.info(f"📥 Iniciando importación de datos para temporada {season}")

        stats = {
            "total_records": len(df),
            "imported_records": 0,
            "matched_players": 0,
            "unmatched_players": 0,
            "errors": 0,
            "error_details": [],
        }

        try:
            with self.session_factory() as session:
                # Marcar temporada como en progreso
                season_obj = self._create_or_update_season(
                    session,
                    season,
                    import_status=ImportStatus.in_progress,
                    last_import_attempt=datetime.now(timezone.utc),
                )
                session.commit()

                # Procesar matches exactos y fuzzy
                all_matches = matching_results.get(
                    "exact_matches", []
                ) + matching_results.get("fuzzy_matches", [])

                logger.info(f"🎯 Procesando {len(all_matches)} matches encontrados")

                for i, match in enumerate(all_matches):
                    try:
                        # Buscar datos del jugador en el CSV
                        player_rows = df[df["Full name"] == match["csv_player"]]
                        if player_rows.empty:
                            stats["error_details"].append(
                                f"Jugador no encontrado en CSV: {match['csv_player']}"
                            )
                            stats["errors"] += 1
                            continue

                        player_data = player_rows.iloc[0]

                        # Crear registro de estadísticas usando el mapping
                        prof_stats = self._create_professional_stats_record(
                            player_data,
                            season,
                            match["matched_player"]["player_id"],
                            column_mapping,
                        )

                        # Verificar si ya existe registro para esta temporada
                        existing = (
                            session.query(ProfessionalStats)
                            .filter(
                                ProfessionalStats.player_id
                                == match["matched_player"]["player_id"],
                                ProfessionalStats.season == season,
                            )
                            .first()
                        )

                        if existing:
                            # Actualizar registro existente
                            for key, value in prof_stats.items():
                                if hasattr(existing, key):
                                    setattr(existing, key, value)
                            logger.debug(
                                f"Actualizado registro existente para {match['csv_player']}"
                            )
                        else:
                            # Crear nuevo registro
                            new_stats = ProfessionalStats(**prof_stats)
                            session.add(new_stats)
                            logger.debug(
                                f"Creado nuevo registro para {match['csv_player']}"
                            )

                        stats["imported_records"] += 1
                        stats["matched_players"] += 1

                        # Commit cada 50 registros para evitar transacciones muy grandes
                        if (i + 1) % 50 == 0:
                            session.commit()
                            logger.info(f"💾 Guardados {i + 1} registros...")

                    except Exception as e:
                        stats["errors"] += 1
                        error_msg = f"Error procesando {match['csv_player']}: {str(e)}"
                        stats["error_details"].append(error_msg)
                        logger.error(error_msg)
                        # Continuar con el siguiente registro

                # Procesar jugadores sin match
                unmatched_count = len(matching_results.get("no_matches", []))
                stats["unmatched_players"] = unmatched_count

                # Commit final
                session.commit()

                # Marcar temporada como completada
                season_obj.import_status = ImportStatus.completed
                season_obj.last_updated = datetime.now(timezone.utc)
                season_obj.update_import_stats(
                    total=stats["total_records"],
                    imported=stats["imported_records"],
                    matched=stats["matched_players"],
                    unmatched=stats["unmatched_players"],
                    errors=stats["errors"],
                )
                session.commit()

                success_msg = (
                    f"✅ Importación exitosa para {season}: "
                    f"{stats['imported_records']}/{stats['total_records']} registros importados"
                )
                logger.info(success_msg)

                return True, success_msg, stats

        except SQLAlchemyError as e:
            error_msg = f"❌ Error de base de datos al importar {season}: {str(e)}"
            logger.error(error_msg)

            # Marcar temporada como fallida
            try:
                with self.session_factory() as session:
                    season_obj = self._get_season(session, season)
                    if season_obj:
                        season_obj.mark_failed(error_msg)
                        session.commit()
            except Exception as inner_e:
                logger.error(
                    f"Error adicional marcando temporada como fallida: {inner_e}"
                )

            return False, error_msg, stats

        except Exception as e:
            error_msg = f"❌ Error inesperado al importar {season}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, stats

    def _create_professional_stats_record(
        self, player_data: pd.Series, season: str, player_id: int, column_mapping: Dict
    ) -> Dict:
        """
        Crea un diccionario con datos para ProfessionalStats usando el mapping de columnas.

        CRÍTICO: Previene error 'team_processed' usando solo campos válidos del modelo.

        Args:
            player_data: Serie con datos del jugador del CSV
            season: Temporada
            player_id: ID del jugador en BD
            column_mapping: Mapping de columnas CSV a BD

        Returns:
            Diccionario con datos para crear ProfessionalStats
        """
        # Base del registro
        prof_stats = {
            "player_id": player_id,
            "season": season,
        }

        # Mapear campos usando el mapping proporcionado
        for csv_column, db_field in column_mapping.items():
            if csv_column in player_data.index:
                value = player_data[csv_column]

                # Limpiar valor (convertir nan a None)
                if pd.isna(value):
                    value = None
                elif isinstance(value, str) and value.strip() == "":
                    value = None

                # Asignar al diccionario
                prof_stats[db_field] = value

        # LOG: Verificar si hay campos problemáticos
        problematic_fields = [
            field for field in prof_stats.keys() if field.endswith("_processed")
        ]
        if problematic_fields:
            logger.warning(f"⚠️ Campos problemáticos detectados: {problematic_fields}")

        return prof_stats

    def _create_or_update_season(
        self, session, season: str, **kwargs
    ) -> ThaiLeagueSeason:
        """
        Crea o actualiza registro de temporada.

        Args:
            session: Sesión de BD
            season: Temporada
            **kwargs: Campos a actualizar

        Returns:
            Objeto ThaiLeagueSeason
        """
        season_obj = self._get_season(session, season)

        if not season_obj:
            season_obj = ThaiLeagueSeason(season=season)
            session.add(season_obj)
            logger.info(f"📝 Creada nueva temporada: {season}")

        # Actualizar campos proporcionados
        for key, value in kwargs.items():
            if hasattr(season_obj, key):
                setattr(season_obj, key, value)

        return season_obj

    def _get_season(self, session, season: str) -> Optional[ThaiLeagueSeason]:
        """
        Obtiene registro de temporada existente.

        Args:
            session: Sesión de BD
            season: Temporada a buscar

        Returns:
            Objeto ThaiLeagueSeason o None
        """
        return (
            session.query(ThaiLeagueSeason)
            .filter(ThaiLeagueSeason.season == season)
            .first()
        )

    def bulk_insert_records(
        self, records: List[Dict], session, batch_size: int = 100
    ) -> Tuple[int, int, List[str]]:
        """
        Inserta múltiples registros en lotes para mejor rendimiento.

        Args:
            records: Lista de diccionarios con datos para ProfessionalStats
            session: Sesión de BD
            batch_size: Tamaño del lote

        Returns:
            Tuple[inserted_count, error_count, error_details]
        """
        logger.info(f"📦 Insertando {len(records)} registros en lotes de {batch_size}")

        inserted_count = 0
        error_count = 0
        error_details = []

        # Procesar en lotes
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]

            try:
                # Crear objetos ProfessionalStats
                stats_objects = []
                for record in batch:
                    stats_obj = ProfessionalStats(**record)
                    stats_objects.append(stats_obj)

                # Insertar lote
                session.add_all(stats_objects)
                session.commit()

                inserted_count += len(batch)
                logger.info(
                    f"✅ Lote {i//batch_size + 1} insertado: {len(batch)} registros"
                )

            except SQLAlchemyError as e:
                session.rollback()
                error_count += len(batch)
                error_msg = f"Error en lote {i//batch_size + 1}: {str(e)}"
                error_details.append(error_msg)
                logger.error(error_msg)

                # Intentar insertar uno por uno para identificar el problemático
                for j, record in enumerate(batch):
                    try:
                        stats_obj = ProfessionalStats(**record)
                        session.add(stats_obj)
                        session.commit()
                        inserted_count += 1
                        error_count -= 1  # Corregir el conteo
                    except SQLAlchemyError as individual_e:
                        session.rollback()
                        individual_error = (
                            f"Error en registro individual {i + j}: {str(individual_e)}"
                        )
                        error_details.append(individual_error)
                        logger.error(individual_error)

        logger.info(
            f"📊 Inserción completa: {inserted_count} exitosos, {error_count} errores"
        )

        return inserted_count, error_count, error_details

    def update_season_metadata(
        self, season: str, file_hash: str, file_size: float, source_url: str
    ) -> bool:
        """
        Actualiza metadatos de la temporada.

        Args:
            season: Temporada
            file_hash: Hash del archivo fuente
            file_size: Tamaño del archivo en MB
            source_url: URL fuente

        Returns:
            True si se actualizó exitosamente
        """
        try:
            with self.session_factory() as session:
                season_obj = self._get_season(session, season)

                if season_obj:
                    season_obj.file_hash = file_hash
                    season_obj.file_size = file_size
                    season_obj.source_url = source_url
                    season_obj.last_updated = datetime.now(timezone.utc)

                    session.commit()
                    logger.info(f"📝 Metadatos actualizados para {season}")
                    return True
                else:
                    logger.warning(
                        f"⚠️ Temporada {season} no encontrada para actualizar metadatos"
                    )
                    return False

        except SQLAlchemyError as e:
            logger.error(f"❌ Error actualizando metadatos para {season}: {e}")
            return False

    def cleanup_season_data(self, season: str) -> Tuple[bool, str]:
        """
        Limpia datos existentes de una temporada antes de reimportación.

        Args:
            season: Temporada a limpiar

        Returns:
            Tuple[success, message]
        """
        try:
            with self.session_factory() as session:
                # Contar registros existentes
                existing_count = (
                    session.query(ProfessionalStats)
                    .filter(ProfessionalStats.season == season)
                    .count()
                )

                if existing_count > 0:
                    # Eliminar registros existentes
                    session.query(ProfessionalStats).filter(
                        ProfessionalStats.season == season
                    ).delete()

                    session.commit()

                    message = f"🧹 Limpiados {existing_count} registros existentes de {season}"
                    logger.info(message)
                    return True, message
                else:
                    message = f"ℹ️ No hay registros existentes para {season}"
                    logger.info(message)
                    return True, message

        except SQLAlchemyError as e:
            error_msg = f"❌ Error limpiando datos de {season}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

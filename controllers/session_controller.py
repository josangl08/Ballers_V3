# controllers/session_controller.py
"""
Controlador para CRUD de sesiones.
Usa ValidationController para validaciones de existencia
"""
import datetime as dt
import logging
import os
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session as SQLSession
from sqlalchemy.orm import joinedload

from config import CALENDAR_COLORS
from controllers.db import get_db_session
from controllers.google_client import calendar
from controllers.validation_controller import ValidationController
from models import Coach, Player, Session, SessionStatus, User

from .calendar_utils import (
    build_calendar_event_body,
    session_needs_update,
    update_session_tracking,
)

logger = logging.getLogger(__name__)
CAL_ID = os.getenv("CALENDAR_ID")


# Funciones simples para reemplazar cloud_utils removido
def is_streamlit_cloud():
    return False


def safe_database_operation(operation, *args, **kwargs):
    try:
        return operation(*args, **kwargs)
    except Exception as e:
        logging.error(f"Database operation failed: {e}")
        return None


class SessionController:
    """
    Controlador para operaciones CRUD con sesiones.
    Usa ValidationController para validaciones de existencia.
    """

    def __init__(self):
        self.db = None

    def __enter__(self):
        """Context manager para manejo automático de BD"""
        self.db = get_db_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra la sesión de BD automáticamente"""
        if self.db:
            self.db.close()

    # Consultas y filtros

    def get_sessions(
        self,
        start: dt.datetime,
        end: dt.datetime,
        coach_id: Optional[int] = None,
        player_id: Optional[int] = None,
        statuses: Optional[List[SessionStatus]] = None,
    ) -> List[Session]:
        """
        Obtiene sesiones filtradas y ordenadas por fecha de inicio.

        Args:
            start: Fecha inicio del rango
            end: Fecha fin del rango
            coach_id: ID del coach (opcional)
            player_id: ID del player (opcional)
            statuses: Lista de estados a filtrar (opcional)

        Returns:
            Lista de sesiones que cumplen los filtros
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        query = (
            self.db.query(Session)
            .options(
                joinedload(Session.coach).joinedload(Coach.user),
                joinedload(Session.player).joinedload(Player.user),
            )
            .filter(Session.start_time >= start, Session.start_time <= end)
        )

        if coach_id:
            query = query.filter(Session.coach_id == coach_id)
        if player_id:
            query = query.filter(Session.player_id == player_id)
        if statuses:
            query = query.filter(Session.status.in_(statuses))

        return query.order_by(Session.start_time.asc()).all()

    def get_session_by_id(self, session_id: int) -> Optional[Session]:
        """Obtiene una sesión por su ID."""
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        return (
            self.db.query(Session)
            .options(
                joinedload(Session.coach).joinedload(Coach.user),
                joinedload(Session.player).joinedload(Player.user),
            )
            .filter_by(id=session_id)
            .first()
        )

    # Operaciones CRUD

    def create_session(
        self,
        coach_id: int,
        player_id: int,
        start_time: dt.datetime,
        end_time: dt.datetime,
        notes: Optional[str] = None,
        status: SessionStatus = SessionStatus.SCHEDULED,
        sync_to_calendar: bool = True,
    ) -> tuple[bool, str, Optional[Session]]:
        """Crear sesión - verificar si es Cloud"""
        if is_streamlit_cloud():
            # En Cloud: simular éxito sin escribir
            return True, "Session created successfully (demo mode)", None
        """
        Crea una nueva sesión.
        Usa ValidationController para validar coach/player existence

        Args:
            coach_id: ID del coach
            player_id: ID del player
            start_time: Hora de inicio
            end_time: Hora de fin
            notes: Notas opcionales
            status: Estado inicial
            sync_to_calendar: Si sincronizar con Google Calendar

        Returns:
            Tuple (success, message, session_object)
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        try:
            # Usar ValidationController para coach/player existence
            coach = self.db.query(Coach).options(joinedload(Coach.user)).filter_by(coach_id=coach_id).first()
            coach_valid, coach_error = ValidationController.validate_coach_exists(coach)
            if not coach_valid:
                return False, coach_error, None

            player = self.db.query(Player).options(joinedload(Player.user)).filter_by(player_id=player_id).first()
            player_valid, player_error = ValidationController.validate_player_exists(
                player
            )
            if not player_valid:
                return False, player_error, None

            # Obtener nombres para snapshots
            coach_name_snapshot = coach.user.name if coach and coach.user else f"Coach {coach_id}"
            player_name_snapshot = player.user.name if player and player.user else f"Player {player_id}"

            # Crear sesión con snapshots de nombres
            new_session = Session(
                coach_id=coach_id,
                player_id=player_id,
                start_time=start_time,
                end_time=end_time,
                status=status,
                notes=notes,
                coach_name_snapshot=coach_name_snapshot,
                player_name_snapshot=player_name_snapshot,
                source="app",
                version=1,
            )

            self.db.add(new_session)
            self.db.flush()  # Para obtener el ID

            # Sincronizar con Calendar si se solicita
            if sync_to_calendar:
                success = self._push_session_to_calendar(new_session)
                if not success:
                    self.db.rollback()
                    return False, "Error creating session in Google Calendar", None

            # Tracking ya actualizado en _push_session_to_calendar (optimización)

            self.db.commit()
            self.db.refresh(new_session)

            return True, "Session created successfully", new_session

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating session: {e}")
            return False, f"Error creating session: {str(e)}", None

    def update_session(self, session_id: int, **kwargs) -> tuple[bool, str]:
        """Actualizar sesión - verificar si es Cloud"""
        if is_streamlit_cloud():
            # En Cloud: simular éxito
            return True, "Session updated successfully (demo mode)"
        """
        Actualiza una sesión existente.
        Usa ValidationController para validar session existence

        Args:
            session_id: ID de la sesión
            **kwargs: Campos a actualizar

        Returns:
            Tuple (success, message)
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        # Usar ValidationController para session existence
        session = self.get_session_by_id(session_id)
        session_valid, session_error = ValidationController.validate_session_exists(
            session
        )
        if not session_valid:
            return False, session_error

        # Type hint para Pylance - después de validación, session no puede ser None
        assert session is not None, "Session validated but is None"

        try:
            # Actualizar campos
            coach_changed = False
            player_changed = False
            
            for field, value in kwargs.items():
                if hasattr(session, field):
                    setattr(session, field, value)
                    # Detectar cambios en coach/player para actualizar snapshots
                    if field == 'coach_id':
                        coach_changed = True
                    elif field == 'player_id':
                        player_changed = True

            # Actualizar snapshots si coach o player cambiaron
            if coach_changed or player_changed:
                # Obtener nombres actualizados para snapshots
                if coach_changed and hasattr(session, 'coach_id'):
                    coach = self.db.query(Coach).options(joinedload(Coach.user)).filter_by(coach_id=session.coach_id).first()
                    session.coach_name_snapshot = coach.user.name if coach and coach.user else f"Coach {session.coach_id}"
                
                if player_changed and hasattr(session, 'player_id'):
                    player = self.db.query(Player).options(joinedload(Player.user)).filter_by(player_id=session.player_id).first()
                    session.player_name_snapshot = player.user.name if player and player.user else f"Player {session.player_id}"

            # Marcar como dirty para sincronización
            session.is_dirty = True

            # Verificar cambios y actualizar tracking en una sola operación (optimización)
            from controllers.calendar_utils import calculate_session_hash

            # Calcular hash una sola vez para evitar duplicación
            current_hash = calculate_session_hash(session)
            has_real_changes = session.sync_hash != current_hash

            if has_real_changes:
                success = self._update_session_in_calendar(
                    session, cached_hash=current_hash
                )
                if not success:
                    self.db.rollback()
                    return False, "Error updating session in Google Calendar"
            else:
                # Si no hay cambios, solo actualizar tracking con hash cacheado
                from controllers.calendar_utils import update_session_tracking_with_hash

                update_session_tracking_with_hash(session, current_hash)

            self.db.commit()
            return True, "Session updated successfully"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating session {session_id}: {e}")
            return False, f"Error updating session: {str(e)}"

    def delete_session(self, session_id: int) -> tuple[bool, str]:
        """Eliminar sesión - verificar si es Cloud"""
        if is_streamlit_cloud():
            # En Cloud: simular éxito
            return True, "Session deleted successfully (demo mode)"
        """
        Elimina una sesión.
        Usa ValidationController para validar session existence

        Args:
            session_id: ID de la sesión a eliminar

        Returns:
            Tuple (success, message)
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        # Usar ValidationController para session existence
        session = self.get_session_by_id(session_id)
        session_valid, session_error = ValidationController.validate_session_exists(
            session
        )
        if not session_valid:
            return False, session_error

        # Type hint para Pylance - después de validación, session no puede ser None
        assert session is not None, "Session validated but is None"

        try:
            # Eliminar de Calendar si existe
            if session.calendar_event_id:
                self._delete_session_from_calendar(session)

            # Eliminar de BD
            self.db.delete(session)
            self.db.commit()

            return True, "Session deleted successfully"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting session {session_id}: {e}")
            return False, f"Error deleting session: {str(e)}"

    def update_past_sessions(self) -> int:
        """
        Marca sesiones pasadas como completadas.

        Returns:
            Número de sesiones actualizadas
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        try:

            madrid_tz = ZoneInfo("Europe/Madrid")
            now = dt.datetime.now(madrid_tz)
            sessions_to_update = (
                self.db.query(Session)
                .filter(
                    Session.status == SessionStatus.SCHEDULED, Session.end_time <= now
                )
                .all()
            )

            count = 0
            for session in sessions_to_update:
                session.status = SessionStatus.COMPLETED
                # Actualizar color en Calendar
                if session.calendar_event_id:
                    self._patch_session_color(session)
                count += 1

            if count > 0:
                self.db.commit()
                logger.info(f"📅 {count} sesiones marcadas como completadas")

            return count

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating past sessions: {e}")
            return 0

    # Metodos privados para Google Calendar

    def _push_session_to_calendar(self, session: Session) -> bool:
        """
        Crea evento en Google Calendar.
        🔧 CORREGIDO: Actualiza correctamente los campos de tracking después de creación exitosa.
        """
        try:

            body = build_calendar_event_body(session)
            event = calendar().events().insert(calendarId=CAL_ID, body=body).execute()

            # Actualizar calendar_event_id
            session.calendar_event_id = event["id"]

            # Actualizar campos de tracking después de creación exitosa
            update_session_tracking(session)

            # Commitear los cambios en BD
            self.db.add(session)
            self.db.commit()

            logger.info(
                f"📤 Sesión #{session.id} creada en Calendar (evento {event['id'][:8]}...)"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Error creando evento en Calendar: {e}")
            return False

    def _update_session_in_calendar(
        self, session: Session, cached_hash: str = None
    ) -> bool:
        """
        Actualiza evento existente en Google Calendar.
        Optimizado: Acepta hash cacheado para evitar recálculos.
        """
        if not session.calendar_event_id:
            # Si no tiene event_id, crear nuevo
            return self._push_session_to_calendar(session)

        try:

            body = build_calendar_event_body(session)
            calendar().events().patch(
                calendarId=CAL_ID, eventId=session.calendar_event_id, body=body
            ).execute()

            # Actualizar tracking con hash cacheado (optimización)
            if cached_hash:
                from controllers.calendar_utils import update_session_tracking_with_hash

                update_session_tracking_with_hash(session, cached_hash)
            else:
                # Fallback para compatibilidad
                update_session_tracking(session)

            # Commitear los cambios en BD
            self.db.add(session)
            self.db.commit()

            logger.info(f"📤 Sesión #{session.id} actualizada en Calendar exitosamente")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(
                    f"⚠️ Evento {session.calendar_event_id[:8]}... no existe - recreando"
                )
                session.calendar_event_id = None
                return self._push_session_to_calendar(session)
            else:
                logger.error(f"❌ Error actualizando evento: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Error actualizando evento: {e}")
            return False

    def _delete_session_from_calendar(self, session: Session) -> bool:
        """Elimina evento de Google Calendar."""
        if not session.calendar_event_id:
            return True

        try:
            calendar().events().delete(
                calendarId=CAL_ID, eventId=session.calendar_event_id
            ).execute()

            logger.info(
                f"🗑️ Evento {session.calendar_event_id[:8]}... eliminado de Calendar"
            )
            return True

        except HttpError as e:
            if e.resp.status == 404:
                # Ya no existe, no es error
                return True
            else:
                logger.error(f"❌ Error eliminando evento: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Error eliminando evento: {e}")
            return False

    def _patch_session_color(self, session: Session):
        """Actualiza solo el color del evento en Calendar."""
        if not session.calendar_event_id:
            return

        try:
            COLOR = {k: v["google"] for k, v in CALENDAR_COLORS.items()}

            calendar().events().patch(
                calendarId=CAL_ID,
                eventId=session.calendar_event_id,
                body={"colorId": COLOR[session.status.value]},
            ).execute()

        except Exception as e:
            logger.error(f"❌ Error actualizando color: {e}")

    def get_coach_stats(self, coach_id: int) -> dict:
        """Obtiene estadísticas de un coach específico."""
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        comp = (
            self.db.query(Session)
            .filter(
                Session.coach_id == coach_id, Session.status == SessionStatus.COMPLETED
            )
            .count()
        )

        prog = (
            self.db.query(Session)
            .filter(
                Session.coach_id == coach_id, Session.status == SessionStatus.SCHEDULED
            )
            .count()
        )

        canc = (
            self.db.query(Session)
            .filter(
                Session.coach_id == coach_id, Session.status == SessionStatus.CANCELED
            )
            .count()
        )

        return {"completed": comp, "scheduled": prog, "canceled": canc}

    def get_sessions_for_display(
        self,
        start_date: dt.date,
        end_date: dt.date,
        coach_id: Optional[int] = None,
        player_id: Optional[int] = None,
        status_filter: Optional[List[str]] = None,
    ) -> List[Session]:
        """Obtiene sesiones para mostrar con filtros de UI."""
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        start_datetime = dt.datetime.combine(start_date, dt.time.min)
        end_datetime = dt.datetime.combine(end_date, dt.time.max)

        # Convertir status strings a enums si se proporcionan
        status_enums = None
        if status_filter:
            status_enums = [SessionStatus(s) for s in status_filter]

        return self.get_sessions(
            start=start_datetime,
            end=end_datetime,
            coach_id=coach_id,
            player_id=player_id,
            statuses=status_enums,
        )

    def format_sessions_for_table(self, sessions: List[Session]) -> List[dict]:
        """Formatea sesiones para mostrar en tabla de UI."""
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        sessions_data = []
        for session in sessions:
            # Obtener nombres de coach y player (manejar snapshots)
            if session.coach_id:
                coach = (
                    self.db.query(Coach)
                    .join(User)
                    .filter(Coach.coach_id == session.coach_id)
                    .first()
                )
                coach_name = (
                    coach.user.name if coach and coach.user else "Coach not found"
                )
            else:
                # Usar snapshot si coach fue eliminado
                coach_name = session.coach_name_snapshot or "Coach deleted"

            if session.player_id:
                player = (
                    self.db.query(Player)
                    .join(User)
                    .filter(Player.player_id == session.player_id)
                    .first()
                )
                player_name = (
                    player.user.name if player and player.user else "Player not found"
                )
            else:
                # Usar snapshot si player fue eliminado
                player_name = session.player_name_snapshot or "Player deleted"

            sessions_data.append(
                {
                    "ID": session.id,
                    "Coach": coach_name,
                    "Player": player_name,
                    "Date": session.start_time.strftime("%d/%m/%Y"),
                    "Start Time": session.start_time.strftime("%H:%M"),
                    "End Time": (
                        session.end_time.strftime("%H:%M")
                        if session.end_time
                        else "Not established"
                    ),
                    "Status": session.status.value,
                }
            )

        return sessions_data

    def get_available_coaches(self) -> List[tuple]:
        """Obtiene lista de coaches disponibles para formularios."""
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        coaches = self.db.query(Coach).join(User).filter(User.is_active.is_(True)).all()
        return [(c.coach_id, c.user.name) for c in coaches]

    def get_available_players(self) -> List[tuple]:
        """Obtiene lista de players disponibles para formularios."""
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        players = (
            self.db.query(Player).join(User).filter(User.is_active.is_(True)).all()
        )
        return [(p.player_id, p.user.name) for p in players]

    def get_sessions_for_editing(
        self,
        coach_id: Optional[int] = None,
        date_filter: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> Dict[int, str]:
        """
        Obtiene sesiones para editar como diccionario con filtros avanzados.

        Args:
            coach_id: ID del coach para filtrar (opcional)
            date_filter: Filtro temporal ('today', 'tomorrow', 'this_week', etc.)
            search_query: Texto de búsqueda (nombre coach/player, ID, fecha)
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        query = (
            self.db.query(Session)
            .options(
                joinedload(Session.coach).joinedload(Coach.user),
                joinedload(Session.player).joinedload(Player.user),
            )
            .order_by(Session.start_time.asc())
        )

        # Filtro por coach
        if coach_id:
            query = query.filter(Session.coach_id == coach_id)

        # Aplicar filtro de fecha si se proporciona
        if date_filter:
            start_date, end_date = self._get_date_range_for_filter(date_filter)
            if start_date and end_date:
                query = query.filter(
                    Session.start_time >= dt.datetime.combine(start_date, dt.time.min),
                    Session.start_time <= dt.datetime.combine(end_date, dt.time.max),
                )

        sessions = query.all()

        # Aplicar búsqueda por texto si se proporciona
        if search_query and search_query.strip():
            sessions = self._filter_sessions_by_search(sessions, search_query.strip())

        # Crear diccionario con descripciones mejoradas
        return self._create_session_descriptions(sessions)

    def _get_date_range_for_filter(
        self, date_filter: str
    ) -> tuple[Optional[dt.date], Optional[dt.date]]:
        """Convierte filtro de fecha a rango de fechas."""
        today = dt.date.today()

        if date_filter == "today":
            return today, today
        elif date_filter == "tomorrow":
            tomorrow = today + dt.timedelta(days=1)
            return tomorrow, tomorrow
        elif date_filter == "yesterday":
            yesterday = today - dt.timedelta(days=1)
            return yesterday, yesterday
        elif date_filter == "this_week":
            start_week = today - dt.timedelta(days=today.weekday())
            end_week = start_week + dt.timedelta(days=6)
            return start_week, end_week
        elif date_filter == "last_week":
            start_last_week = today - dt.timedelta(days=today.weekday() + 7)
            end_last_week = start_last_week + dt.timedelta(days=6)
            return start_last_week, end_last_week
        elif date_filter == "this_month":
            start_month = today.replace(day=1)
            if today.month == 12:
                end_month = today.replace(
                    year=today.year + 1, month=1, day=1
                ) - dt.timedelta(days=1)
            else:
                end_month = today.replace(month=today.month + 1, day=1) - dt.timedelta(
                    days=1
                )
            return start_month, end_month
        elif date_filter == "last_month":
            if today.month == 1:
                start_last_month = today.replace(year=today.year - 1, month=12, day=1)
                end_last_month = today.replace(day=1) - dt.timedelta(days=1)
            else:
                start_last_month = today.replace(month=today.month - 1, day=1)
                end_last_month = today.replace(day=1) - dt.timedelta(days=1)
            return start_last_month, end_last_month
        else:
            return None, None

    def _filter_sessions_by_search(
        self, sessions: List[Session], search_query: str
    ) -> List[Session]:
        """Filtra sesiones por consulta de búsqueda."""
        search_lower = search_query.lower()
        filtered_sessions = []

        for session in sessions:
            # Buscar en nombres de coach y player (manejar snapshots)
            if session.coach:
                coach_name = session.coach.user.name.lower()
            else:
                # Usar snapshot si coach fue eliminado
                coach_name = (session.coach_name_snapshot or "").lower()

            if session.player:
                player_name = session.player.user.name.lower()
            else:
                # Usar snapshot si player fue eliminado
                player_name = (session.player_name_snapshot or "").lower()

            # Buscar en ID de sesión
            session_id_str = str(session.id)

            # Buscar en fecha formateada
            date_str = session.start_time.strftime("%d/%m/%Y").lower()
            date_str_alt = session.start_time.strftime("%d/%m").lower()

            # Buscar palabras clave temporales
            session_date = session.start_time.date()
            today = dt.date.today()
            temporal_keywords = []

            if session_date == today:
                temporal_keywords.extend(["today", "hoy"])
            elif session_date == today + dt.timedelta(days=1):
                temporal_keywords.extend(["tomorrow", "mañana"])
            elif session_date == today - dt.timedelta(days=1):
                temporal_keywords.extend(["yesterday", "ayer"])

            # Verificar si la búsqueda coincide con algún campo
            if (
                search_lower in coach_name
                or search_lower in player_name
                or search_lower in session_id_str
                or search_lower in date_str
                or search_lower in date_str_alt
                or any(
                    keyword.startswith(search_lower) for keyword in temporal_keywords
                )
            ):
                filtered_sessions.append(session)

        return filtered_sessions

    def _create_session_descriptions(self, sessions: List[Session]) -> Dict[int, str]:
        """Crea descripciones mejoradas para las sesiones."""
        today = dt.date.today()
        tomorrow = today + dt.timedelta(days=1)
        yesterday = today - dt.timedelta(days=1)

        descriptions = {}
        for s in sessions:
            session_date = s.start_time.date()

            # Prefijo temporal con emoji
            if session_date == yesterday:
                prefix = "🔘 Yesterday – "
            elif session_date == today:
                prefix = "🟢 Today – "
            elif session_date == tomorrow:
                prefix = "🟡 Tomorrow – "
            elif session_date < today:
                prefix = "🔘 Past – "
            elif session_date <= today + dt.timedelta(days=7):
                prefix = "📅 This week – "
            else:
                prefix = "📆 "

            # Obtener nombres (manejar snapshots)
            if s.coach_id and s.coach:
                coach_name = s.coach.user.name
            else:
                coach_name = s.coach_name_snapshot or "Coach deleted"

            if s.player_id and s.player:
                player_name = s.player.user.name
            else:
                player_name = s.player_name_snapshot or "Player deleted"

            # Descripción completa
            descriptions[s.id] = (
                f"{prefix}{coach_name} with {player_name} "
                f"({s.start_time:%d/%m %H:%M}) [{s.status.value}]"
            )

        return descriptions

    def _session_needs_update(self, session: Session) -> bool:
        """Método que faltaba - movido desde calendar_utils."""
        # Importar la función desde calendar_utils
        return session_needs_update(session)


def get_sessions(
    start: dt.datetime,
    end: dt.datetime,
    coach_id: Optional[int] = None,
    player_id: Optional[int] = None,
    statuses: Optional[List[SessionStatus]] = None,
) -> List[Session]:
    """Función de conveniencia para mantener compatibilidad."""
    with SessionController() as controller:
        return controller.get_sessions(start, end, coach_id, player_id, statuses)


def push_session(session: Session, db: Optional[SQLSession] = None):
    """Función de conveniencia para mantener compatibilidad."""
    # Si ya tiene una sesión BD, usarla
    if db:
        # Crear controller que use esa sesión
        controller = SessionController()
        controller.db = db
        return controller._push_session_to_calendar(session)
    else:
        # Usar context manager
        with SessionController() as controller:
            return controller._push_session_to_calendar(session)


def update_session(session: Session):
    """Función de conveniencia para mantener compatibilidad."""
    with SessionController() as controller:
        # Obtener la sesión desde BD para actualizarla
        db_session = controller.get_session_by_id(session.id)
        if db_session:
            return controller._update_session_in_calendar(db_session)
        return False


def delete_session(session: Session):
    """Función de conveniencia para mantener compatibilidad."""
    with SessionController() as controller:
        return controller._delete_session_from_calendar(session)


def update_past_sessions() -> int:
    """Función de conveniencia para mantener compatibilidad."""
    with SessionController() as controller:
        return controller.update_past_sessions()


# Decorador removido para simplificación
def create_session_with_calendar(
    coach_id: int,
    player_id: int,
    session_date: dt.date,
    start_time: dt.time,
    end_time: dt.time,
    notes: Optional[str] = None,
    status: SessionStatus = SessionStatus.SCHEDULED,
) -> tuple[bool, str, Optional[Session]]:
    """Función de conveniencia para crear sesión con sincronización."""

    # Combinar date + time para crear datetimes
    start_datetime = dt.datetime.combine(session_date, start_time)
    end_datetime = dt.datetime.combine(session_date, end_time)

    with SessionController() as controller:
        return controller.create_session(
            coach_id=coach_id,
            player_id=player_id,
            start_time=start_datetime,
            end_time=end_datetime,
            notes=notes,
            status=status,
            sync_to_calendar=True,
        )


# Decorador removido para simplificación
def update_session_with_calendar(session_id: int, **kwargs) -> tuple[bool, str]:
    """Función de conveniencia para actualizar sesión con sincronización - CORREGIDA."""

    # Convertir date + time a datetime antes de enviar al controller
    if "session_date" in kwargs and ("start_time" in kwargs or "end_time" in kwargs):
        session_date = kwargs.pop("session_date")  # Remover del kwargs

        if "start_time" in kwargs:
            start_time = kwargs.pop("start_time")
            kwargs["start_time"] = dt.datetime.combine(session_date, start_time)

        if "end_time" in kwargs:
            end_time = kwargs.pop("end_time")
            kwargs["end_time"] = dt.datetime.combine(session_date, end_time)

    # 🔧 FIX: Convertir status string a enum si necesario
    if "status" in kwargs and isinstance(kwargs["status"], str):
        kwargs["status"] = SessionStatus(kwargs["status"])

    with SessionController() as controller:
        return controller.update_session(session_id, **kwargs)


# Decorador removido para simplificación
def delete_session_with_calendar(session_id: int) -> tuple[bool, str]:
    """Función de conveniencia para eliminar sesión con sincronización."""
    with SessionController() as controller:
        return controller.delete_session(session_id)


def get_coach_stats(coach_id: int) -> dict:
    """Función de conveniencia para obtener stats de coach."""
    with SessionController() as controller:
        return controller.get_coach_stats(coach_id)


def get_sessions_for_display(
    start_date: dt.date,
    end_date: dt.date,
    coach_id: Optional[int] = None,
    player_id: Optional[int] = None,
    status_filter: Optional[List[str]] = None,
) -> List[Session]:
    """Función de conveniencia para obtener sesiones para UI."""
    with SessionController() as controller:
        return controller.get_sessions_for_display(
            start_date, end_date, coach_id, player_id, status_filter
        )


def format_sessions_for_table(sessions: List[Session]) -> List[dict]:
    """Función de conveniencia para formatear sesiones."""
    with SessionController() as controller:
        return controller.format_sessions_for_table(sessions)


def get_available_coaches() -> List[tuple]:
    """Función de conveniencia para obtener coaches."""
    with SessionController() as controller:
        return controller.get_available_coaches()


def get_available_players() -> List[tuple]:
    """Función de conveniencia para obtener players."""
    with SessionController() as controller:
        return controller.get_available_players()


def get_sessions_for_editing(
    coach_id: Optional[int] = None,
    date_filter: Optional[str] = None,
    search_query: Optional[str] = None,
) -> Dict[int, str]:
    """Función de conveniencia para obtener sesiones para editar."""
    with SessionController() as controller:
        return controller.get_sessions_for_editing(coach_id, date_filter, search_query)


def get_coach_by_user_id(user_id: int):
    """Obtiene un coach por su user_id."""
    from controllers.db import get_db_session
    from models import Coach

    with get_db_session() as db:
        coach = db.query(Coach).filter(Coach.user_id == user_id).first()
        return coach
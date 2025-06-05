# controllers/session_controller.py
"""
Controlador para manejo de sesiones.
Separa la lógica de negocio de las páginas de UI.
IMPORTANTE: Este controller es independiente de Streamlit para facilitar testing.
"""
import datetime as dt
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session as SQLSession
from sqlalchemy import asc

from models import Session, SessionStatus, Coach, Player, User
from controllers.db import get_db_session


class SessionController:
    """
    Controlador para operaciones con sesiones.
    Principio: Separar lógica de negocio de la presentación.
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
    
    # ========================================================================
    # CONSULTAS Y FILTRADO
    # ========================================================================
    
    def get_sessions_for_display(
        self, 
        start_date: dt.date, 
        end_date: dt.date,
        coach_id: Optional[int] = None,
        player_id: Optional[int] = None,
        status_filter: Optional[List[str]] = None
    ) -> List[Session]:
        """
        Obtiene sesiones filtradas para mostrar.
        
        Args:
            start_date: Fecha inicio
            end_date: Fecha fin  
            coach_id: ID del coach (opcional)
            player_id: ID del player (opcional)
            status_filter: Lista de estados (opcional)
            
        Returns:
            Lista de sesiones ordenadas por fecha
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        # Convertir fechas a datetime
        start_datetime = dt.datetime.combine(start_date, dt.time.min)
        end_datetime = dt.datetime.combine(end_date, dt.time.max)
        
        # Construir consulta base
        query = self.db.query(Session).filter(
            Session.start_time >= start_datetime,
            Session.start_time <= end_datetime
        )
        
        # Aplicar filtros opcionales
        if coach_id:
            query = query.filter(Session.coach_id == coach_id)
        
        if player_id:
            query = query.filter(Session.player_id == player_id)
        
        if status_filter:
            status_enums = [SessionStatus(s) for s in status_filter]
            query = query.filter(Session.status.in_(status_enums))
        
        return query.order_by(Session.start_time).all()
    
    def format_sessions_for_table(self, sessions: List[Session]) -> List[Dict[str, Any]]:
        """
        Formatea sesiones para mostrar en tabla.
        Elimina duplicación entre coach/admin views.
        
        Args:
            sessions: Lista de objetos Session
            
        Returns:
            Lista de diccionarios con datos formateados
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        formatted_sessions = []
        
        for session in sessions:
            # Obtener nombres de coach y player (con protección contra errores)
            coach = self.db.query(Coach).filter(Coach.coach_id == session.coach_id).first()
            player = self.db.query(Player).filter(Player.player_id == session.player_id).first()
            
            coach_name = coach.user.name if coach and coach.user else "Coach not found"
            player_name = player.user.name if player and player.user else "Player not found"
            
            formatted_sessions.append({
                "ID": session.id,
                "Coach": coach_name,
                "Player": player_name,
                "Date": session.start_time.strftime("%d/%m/%Y"),
                "Start Time": session.start_time.strftime("%H:%M"),
                "End Time": session.end_time.strftime("%H:%M") if session.end_time else "Not established",
                "Status": session.status.value,
            })
        
        return formatted_sessions
    
    def get_coach_stats(self, coach_id: int) -> Dict[str, int]:
        """
        Obtiene estadísticas de un coach.
        
        Args:
            coach_id: ID del coach
            
        Returns:
            Diccionario con estadísticas
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        coach = self.db.query(Coach).filter(Coach.coach_id == coach_id).first()
        if not coach:
            return {"scheduled": 0, "completed": 0, "canceled": 0}
        
        return {
            "scheduled": sum(s.status == SessionStatus.SCHEDULED for s in coach.sessions),
            "completed": sum(s.status == SessionStatus.COMPLETED for s in coach.sessions),
            "canceled": sum(s.status == SessionStatus.CANCELED for s in coach.sessions),
        }
    
    # ========================================================================
    # OPERACIONES CRUD
    # ========================================================================
    
    def _validate_session_time(self, session_date: dt.date, start_time: dt.time, end_time: dt.time) -> Tuple[bool, str]:
        """
        Validación básica de horarios (independiente de Streamlit).
        Para validación completa, usar common.validation en la capa de UI.
        """
        # 1. Verificar que end_time > start_time
        if end_time <= start_time:
            return False, "La hora de fin debe ser posterior a la hora de inicio."
        
        # 2. Verificar horario de trabajo básico
        if start_time < dt.time(8, 0) or start_time >= dt.time(19, 0):
            return False, "La hora de inicio debe estar entre 08:00 y 19:00."
        
        if end_time <= dt.time(8, 0) or end_time > dt.time(19, 0):
            return False, "La hora de fin debe estar entre 08:00 y 19:00."
        
        # 3. Verificar duración
        start_dt = dt.datetime.combine(session_date, start_time)
        end_dt = dt.datetime.combine(session_date, end_time)
        duration = (end_dt - start_dt).total_seconds() / 60  # minutos
        
        if duration < 15:
            return False, "La sesión debe durar al menos 15 minutos."
        
        if duration > 240:  # 4 horas
            return False, "La sesión no puede durar más de 4 horas."
        
        return True, ""

    def create_session(
        self,
        coach_id: int,
        player_id: int,
        session_date: dt.date,
        start_time: dt.time,
        end_time: dt.time,
        notes: Optional[str] = None,
        sync_calendar: bool = False
    ) -> Tuple[bool, str, Optional[Session]]:
        """
        Crea una nueva sesión con validación.
        
        Args:
            coach_id: ID del coach
            player_id: ID del player
            session_date: Fecha de la sesión
            start_time: Hora de inicio
            end_time: Hora de fin
            notes: Notas opcionales
            sync_calendar: Si True, sincroniza con Google Calendar (requiere UI)
            
        Returns:
            Tuple (success, message, session_object)
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        # Validar tiempos con validación básica
        is_valid, error_msg = self._validate_session_time(session_date, start_time, end_time)
        if not is_valid:
            return False, error_msg, None
        
        try:
            # Crear objeto sesión
            start_dt = dt.datetime.combine(session_date, start_time)
            end_dt = dt.datetime.combine(session_date, end_time)
            
            new_session = Session(
                coach_id=coach_id,
                player_id=player_id,
                start_time=start_dt,
                end_time=end_dt,
                status=SessionStatus.SCHEDULED,
                notes=notes
            )
            
            # Guardar en BD
            self.db.add(new_session)
            self.db.flush()  # Obtener ID sin hacer commit
            
            # Sincronizar con Calendar solo si se especifica (desde UI)
            if sync_calendar:
                try:
                    from controllers.calendar_controller import push_session
                    push_session(new_session)
                except ImportError:
                    # Calendar controller no disponible (ej: en tests)
                    pass
            
            self.db.commit()
            self.db.refresh(new_session)
            
            return True, "Session created successfully", new_session
            
        except Exception as e:
            self.db.rollback()
            return False, f"Error creating session: {str(e)}", None
    
    def update_session(
        self,
        session_id: int,
        coach_id: Optional[int] = None,
        player_id: Optional[int] = None,
        session_date: Optional[dt.date] = None,
        start_time: Optional[dt.time] = None,
        end_time: Optional[dt.time] = None,
        status: Optional[str] = None,
        notes: Optional[str] = None,
        sync_calendar: bool = False
    ) -> Tuple[bool, str]:
        """
        Actualiza una sesión existente.
        
        Args:
            session_id: ID de la sesión a actualizar
            Los demás parámetros son opcionales y solo se actualizan si se proporcionan
            sync_calendar: Si True, sincroniza con Google Calendar (requiere UI)
            
        Returns:
            Tuple (success, message)
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        session = self.db.get(Session, session_id)
        if not session:
            return False, "Session not found"
        
        try:
            # Validar tiempos si se proporcionan
            if session_date and start_time and end_time:
                is_valid, error_msg = self._validate_session_time(session_date, start_time, end_time)
                if not is_valid:
                    return False, error_msg
            
            # Actualizar campos proporcionados
            if coach_id is not None:
                session.coach_id = coach_id
            
            if player_id is not None:
                session.player_id = player_id
            
            if session_date and start_time:
                session.start_time = dt.datetime.combine(session_date, start_time)
            
            if session_date and end_time:
                session.end_time = dt.datetime.combine(session_date, end_time)
            
            if status is not None:
                session.status = SessionStatus(status)
            
            if notes is not None:
                session.notes = notes
            
            # Guardar cambios
            self.db.commit()
            
            # Sincronizar con Calendar solo si se especifica
            if sync_calendar:
                try:
                    from controllers.calendar_controller import update_session as calendar_update
                    calendar_update(session)
                except ImportError:
                    # Calendar controller no disponible (ej: en tests)
                    pass
            
            return True, f"Session #{session_id} updated successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Error updating session: {str(e)}"
    
    def delete_session(self, session_id: int, sync_calendar: bool = False) -> Tuple[bool, str]:
        """
        Elimina una sesión.
        
        Args:
            session_id: ID de la sesión a eliminar
            sync_calendar: Si True, sincroniza con Google Calendar (requiere UI)
            
        Returns:
            Tuple (success, message)
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        session = self.db.get(Session, session_id)
        if not session:
            return False, "Session not found"
        
        try:
            # Eliminar de Google Calendar si existe y se especifica
            if sync_calendar and session.calendar_event_id:
                try:
                    from controllers.calendar_controller import delete_session as calendar_delete
                    calendar_delete(session)
                except ImportError:
                    # Calendar controller no disponible (ej: en tests)
                    pass
            
            # Eliminar de BD
            self.db.delete(session)
            self.db.commit()
            
            return True, "Session deleted successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Error deleting session: {str(e)}"
    
    # ========================================================================
    # HELPERS PARA UI
    # ========================================================================
    
    def get_available_coaches(self) -> List[Tuple[int, str]]:
        """Obtiene lista de coaches activos para selectores"""
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        coaches = self.db.query(Coach).join(User).filter(User.is_active == True).all()
        return [(c.coach_id, c.user.name) for c in coaches]
    
    def get_available_players(self) -> List[Tuple[int, str]]:
        """Obtiene lista de players activos para selectores"""
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        players = self.db.query(Player).join(User).filter(User.is_active == True).all()
        return [(p.player_id, p.user.name) for p in players]
    
    def get_sessions_for_editing(self, coach_id: Optional[int] = None) -> Dict[int, str]:
        """
        Obtiene sesiones con formato para selector de edición.
        
        Args:
            coach_id: Si se proporciona, filtra solo sesiones de ese coach
            
        Returns:
            Diccionario {session_id: description}
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        query = self.db.query(Session).order_by(asc(Session.start_time))
        
        if coach_id:
            query = query.filter(Session.coach_id == coach_id)
        
        sessions = query.all()
        
        # Crear descripciones dinámicas
        today = dt.date.today()
        tomorrow = today + dt.timedelta(days=1)
        
        descriptions = {}
        for s in sessions:
            session_date = s.start_time.date()
            
            if session_date < today:
                prefix = "🔘 Past – "
            elif session_date == today:
                prefix = "🟢 Today – "
            elif session_date == tomorrow:
                prefix = "🟡 Tomorrow – "
            else:
                prefix = ""
            
            descriptions[s.id] = (
                f"{prefix}#{s.id} – {s.coach.user.name} with {s.player.user.name} "
                f"({s.start_time:%d/%m %H:%M})"
            )
        
        return descriptions


# ========================================================================
# FUNCIONES DE CONVENIENCIA (compatibilidad con código existente)
# ========================================================================

def get_sessions_formatted(
    start_date: dt.date,
    end_date: dt.date,
    coach_id: Optional[int] = None,
    status_filter: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Función de conveniencia para obtener sesiones formateadas.
    Mantiene compatibilidad con código existente.
    """
    with SessionController() as controller:
        sessions = controller.get_sessions_for_display(
            start_date, end_date, coach_id=coach_id, status_filter=status_filter
        )
        return controller.format_sessions_for_table(sessions)


def create_session_simple(
    coach_id: int,
    player_id: int,
    session_date: dt.date,
    start_time: dt.time,
    end_time: dt.time,
    notes: Optional[str] = None,
    sync_calendar: bool = True
) -> Tuple[bool, str]:
    """
    Función de conveniencia para crear sesión.
    Mantiene compatibilidad con código existente.
    
    Args:
        sync_calendar: Si True (default), sincroniza con Google Calendar
    """
    with SessionController() as controller:
        success, message, _ = controller.create_session(
            coach_id, player_id, session_date, start_time, end_time, notes, sync_calendar
        )
        return success, message


# ========================================================================
# FUNCIONES WRAPPER PARA COMPATIBILIDAD CON UI
# ========================================================================

def create_session_with_calendar(
    coach_id: int,
    player_id: int,
    session_date: dt.date,
    start_time: dt.time,
    end_time: dt.time,
    notes: Optional[str] = None
) -> Tuple[bool, str, Optional[Session]]:
    """
    Función específica para UI que incluye validación completa y sync con Calendar.
    Usa validación completa de common.validation cuando está disponible.
    """
    # Intentar usar validación completa desde UI
    try:
        from common.validation import validate_session_time
        is_valid, error_msg = validate_session_time(session_date, start_time, end_time)
        if not is_valid:
            return False, error_msg, None
    except ImportError:
        # Fallback a validación básica si no está disponible
        pass
    
    with SessionController() as controller:
        return controller.create_session(
            coach_id, player_id, session_date, start_time, end_time, notes, sync_calendar=True
        )


def update_session_with_calendar(
    session_id: int,
    **kwargs
) -> Tuple[bool, str]:
    """
    Función específica para UI que incluye sync con Calendar.
    """
    with SessionController() as controller:
        return controller.update_session(session_id, sync_calendar=True, **kwargs)


def delete_session_with_calendar(session_id: int) -> Tuple[bool, str]:
    """
    Función específica para UI que incluye sync con Calendar.
    """
    with SessionController() as controller:
        return controller.delete_session(session_id, sync_calendar=True)
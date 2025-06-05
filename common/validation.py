# controllers/validation.py
"""
Módulo de validaciones para la aplicación Ballers.
Contiene todas las reglas de negocio y validaciones de datos.
"""
import datetime as dt
from typing import Tuple, Optional, List, Dict, Any
from config import WORK_HOURS_FLEXIBLE, WORK_HOURS_STRICT, SESSION_DURATION


class SessionValidationError(Exception):
    """Excepción personalizada para errores de validación de sesiones."""
    pass


def validate_session_time(session_date: dt.date, start_time: dt.time, end_time: dt.time) -> Tuple[bool, str]:
    """
    Valida que la sesión cumpla las reglas de negocio.
    
    Args:
        session_date: Fecha de la sesión
        start_time: Hora de inicio
        end_time: Hora de fin
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    # 1. Verificar que end_time > start_time
    if end_time <= start_time:
        return False, "La hora de fin debe ser posterior a la hora de inicio."
    
    # 2. Verificar horario de trabajo (8:00 - 18:00)
    WORK_START = dt.time(8, 0)
    WORK_END = dt.time(19, 0)
    
    if start_time < WORK_START or start_time >= WORK_END:
        return False, f"The start time must be between {WORK_START.strftime('%H:%M')} and {WORK_END.strftime('%H:%M')}."
    
    if end_time <= WORK_START or end_time > WORK_END:
        return False, f"The end time must be between {WORK_START.strftime('%H:%M')} and {WORK_END.strftime('%H:%M')}."
    
    # 3. Verificar que la sesión no exceda el mismo día
    start_dt = dt.datetime.combine(session_date, start_time)
    end_dt = dt.datetime.combine(session_date, end_time)
    
    if end_dt.date() != start_dt.date():
        return False, "The session cannot be extended to another day."
    
    # 4. Verificar duración mínima (60 min) y máxima (2 horas)
    duration = (end_dt - start_dt).total_seconds() / 60  # minutos
    
    if duration < 15:
        return False, "The session should last at least 15 minutes."
    
    if duration > 120:  # 2 horas
        return False, "The session cannot last more than 4 hours."
    
    return True, ""


def validate_session_datetime(start_dt: dt.datetime, end_dt: dt.datetime) -> Tuple[bool, str]:
    """
    Valida datetime objects directamente.
    
    Args:
        start_dt: Datetime de inicio
        end_dt: Datetime de fin
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    return validate_session_time(
        session_date=start_dt.date(),
        start_time=start_dt.time(),
        end_time=end_dt.time()
    )


def validate_user_data(name: str, username: str, email: str, password: Optional[str] = None) -> Tuple[bool, str]:
    """
    Valida datos básicos de usuario.
    
    Args:
        name: Nombre completo
        username: Nombre de usuario
        email: Email
        password: Contraseña (opcional para edición)
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    # Validar campos obligatorios
    if not name or not name.strip():
        return False, "The name is required."
    
    if not username or not username.strip():
        return False, "The username is required."
    
    if not email or not email.strip():
        return False, "The email is required."
    
    # Validar formato de email básico
    if "@" not in email or "." not in email.split("@")[-1]:
        return False, "The email format is invalid."
    
    # Validar username (solo alfanumérico y guiones bajos)
    if not username.replace("_", "").replace("-", "").isalnum():
        return False, "The username can only contain letters, numbers, hyphens and underscores."
    
    # Validar longitud de username
    if len(username) < 3 or len(username) > 20:
        return False, "The username must be between 3 and 20 characters long."
    
    # Validar contraseña si se proporciona
    if password is not None:
        if len(password) < 6:
            return False, "The password must be at least 6 characters long."
    
    return True, ""

def validate_session_for_import(start_dt: dt.datetime, end_dt: dt.datetime) -> Tuple[bool, str, List[str]]:
    """
    Validación FLEXIBLE para eventos importados de Google Calendar.
    
    Esta función distingue entre:
    - ERRORES CRÍTICOS: Rechazan el evento (no se importa)
    - WARNINGS: Permiten importar pero alertan al usuario
    
    Args:
        start_dt: Datetime de inicio
        end_dt: Datetime de fin
        
    Returns:
        Tuple[bool, str, List[str]]: (is_valid, error_message, warnings_list)
    """
    warnings = []
    
    # ❌ CRÍTICO 1: end_time > start_time (RECHAZAR si falla)
    if end_dt <= start_dt:
        return False, "End time must be later than start time", warnings
    
    # ❌ CRÍTICO 2: Mismo día (RECHAZAR si falla) 
    if end_dt.date() != start_dt.date():
        return False, "The session cannot be spread over multiple days", warnings
    
    # ❌ CRÍTICO 3: Duración excesiva claramente errónea (RECHAZAR)
    duration_minutes = (end_dt - start_dt).total_seconds() / 60
    
    if duration_minutes > 180:  # 3 horas - claramente un error
        return False, f"Excessive duration: {duration_minutes/60:.1f} hours (reasonable maximum: 2h)", warnings
    
    if duration_minutes < 1:  # Menos de 1 minuto - error obvio
        return False, f"Duration too short: {int(duration_minutes)} min (minimum: 60 min)", warnings
    
    # ⚠️ WARNING 1: Horario recomendado (MÁS FLEXIBLE para imports)
    RECOMMENDED_START = dt.time(8, 0)   # 8:00 AM - más temprano que formularios
    RECOMMENDED_END = dt.time(18, 0)    # 6:00 PM - más tarde que formularios

    # Horario extendido permitido pero con warning
    EXTENDED_START = dt.time(6, 0)      # 6:00 AM límite absoluto
    EXTENDED_END = dt.time(20, 0)       # 8:00 PM límite absoluto
    
    if start_dt.time() < RECOMMENDED_START:
        if start_dt.time() >= EXTENDED_START:
            warnings.append(f"Early start: {start_dt.time().strftime('%H:%M')} (recommended: 8:00-18:00)")
        else:
            warnings.append(f"Very early start: {start_dt.time().strftime('%H:%M')} (limit: 6:00)")
    
    if start_dt.time() >= RECOMMENDED_END:
        if start_dt.time() <= EXTENDED_END:
            warnings.append(f"Late Start: {start_dt.time().strftime('%H:%M')} (recommended: 8:00-18:00)")
        else:
            warnings.append(f"Very late start: {start_dt.time().strftime('%H:%M')} (limit: 20:00)")
    
    if end_dt.time() <= RECOMMENDED_START:
        warnings.append(f"End very early: {end_dt.time().strftime('%H:%M')} (recommended: after 8:00)")
    
    if end_dt.time() > RECOMMENDED_END:
        if end_dt.time() <= EXTENDED_END:
            warnings.append(f"End late: {end_dt.time().strftime('%H:%M')} (recommended: 8:00-18:00)")
        else:
            warnings.append(f"End very late: {end_dt.time().strftime('%H:%M')} (limit: 20:00)")
    
    # ⚠️ WARNING 2: Duración (FLEXIBLE - permitir pero avisar)
    if duration_minutes < 60:
        warnings.append(f"Duration short: {int(duration_minutes)} min (recommended: 60 min)")
    
    if duration_minutes > 180:  # 3 horas
        warnings.append(f"Duración long: {duration_minutes/60:.1f}h (recommended: less than 2h)")
    
    # ⚠️ WARNING 3: Horarios poco comunes (fines de semana, etc.)
    weekday = start_dt.weekday()  # 0=Monday, 6=Sunday
    
    if weekday >= 5:  # Sábado (5) o Domingo (6)
        warnings.append(f"Weekend session: {['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'][weekday]}")
    
    # ✅ SIEMPRE VÁLIDO si no hay errores críticos (aunque tenga warnings)
    return True, "", warnings


def validate_session_for_import_simple(session_date: dt.date, start_time: dt.time, end_time: dt.time) -> Tuple[bool, str, List[str]]:
    """
    Versión simplificada que acepta date y time por separado.
    
    Args:
        session_date: Fecha de la sesión
        start_time: Hora de inicio
        end_time: Hora de fin
        
    Returns:
        Tuple[bool, str, List[str]]: (is_valid, error_message, warnings_list)
    """
    start_dt = dt.datetime.combine(session_date, start_time)
    end_dt = dt.datetime.combine(session_date, end_time)
    
    return validate_session_for_import(start_dt, end_dt)


def check_existing_sessions_problems(db_session) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Verifica problemas en todas las sesiones existentes en la BD.
    
    Args:
        db_session: Sesión de base de datos SQLAlchemy
        
    Returns:
        Tuple[List[Dict], List[Dict]]: (invalid_sessions, warning_sessions)
    """
    try:
        from models import Session, SessionStatus
    except ImportError:
        return [], []  # Si no puede importar modelos, devolver listas vacías
    
    invalid_sessions = []
    warning_sessions = []
    
    try:
        # Obtener sesiones activas (no canceladas)
        sessions = db_session.query(Session).filter(
            Session.status.in_([SessionStatus.SCHEDULED, SessionStatus.COMPLETED])
        ).all()
        
        for session in sessions:
            try:
                # Validar usando la función flexible
                is_valid, error_msg, warnings = validate_session_for_import(
                    session.start_time, session.end_time
                )
                
                if not is_valid:
                    invalid_sessions.append({
                        "id": session.id,
                        "title": f"{session.coach.user.name} × {session.player.user.name}",
                        "date": session.start_time.strftime("%d/%m/%Y"),
                        "time": f"{session.start_time.strftime('%H:%M')}-{session.end_time.strftime('%H:%M')}",
                        "reason": error_msg,
                        "session": session
                    })
                
                elif warnings:
                    warning_sessions.append({
                        "id": session.id,
                        "title": f"{session.coach.user.name} × {session.player.user.name}",
                        "date": session.start_time.strftime("%d/%m/%Y"),
                        "time": f"{session.start_time.strftime('%H:%M')}-{session.end_time.strftime('%H:%M')}",
                        "warnings": warnings,
                        "session": session
                    })
                    
            except Exception as e:
                # Si hay error verificando la sesión, añadir como inválida
                invalid_sessions.append({
                    "id": session.id,
                    "title": f"Sesión #{session.id}",
                    "date": "Error",
                    "time": "Error",
                    "reason": f"Error verificando sesión: {str(e)}",
                    "session": session
                })
        
    except Exception as e:
        # Error general accediendo a la BD
        invalid_sessions.append({
            "id": 0,
            "title": "Error del sistema",
            "date": "N/A",
            "time": "N/A",
            "reason": f"Error verificando sesiones: {str(e)}",
            "session": None
        })
    
    return invalid_sessions, warning_sessions


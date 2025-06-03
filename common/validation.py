# controllers/validation.py
"""
Módulo de validaciones para la aplicación Ballers.
Contiene todas las reglas de negocio y validaciones de datos.
"""
import datetime as dt
from typing import Tuple, Optional
from config import WORK_HOURS, SESSION_DURATION


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
    WORK_END = dt.time(18, 0)
    
    if start_time < WORK_START or start_time >= WORK_END:
        return False, f"La hora de inicio debe estar entre {WORK_START.strftime('%H:%M')} y {WORK_END.strftime('%H:%M')}."
    
    if end_time <= WORK_START or end_time > WORK_END:
        return False, f"La hora de fin debe estar entre {WORK_START.strftime('%H:%M')} y {WORK_END.strftime('%H:%M')}."
    
    # 3. Verificar que la sesión no exceda el mismo día
    start_dt = dt.datetime.combine(session_date, start_time)
    end_dt = dt.datetime.combine(session_date, end_time)
    
    if end_dt.date() != start_dt.date():
        return False, "La sesión no puede extenderse a otro día."
    
    # 4. Verificar duración mínima (15 min) y máxima (4 horas)
    duration = (end_dt - start_dt).total_seconds() / 60  # minutos
    
    if duration < 15:
        return False, "La sesión debe durar al menos 15 minutos."
    
    if duration > 240:  # 4 horas
        return False, "La sesión no puede durar más de 4 horas."
    
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
        return False, "El nombre es obligatorio."
    
    if not username or not username.strip():
        return False, "El username es obligatorio."
    
    if not email or not email.strip():
        return False, "El email es obligatorio."
    
    # Validar formato de email básico
    if "@" not in email or "." not in email.split("@")[-1]:
        return False, "El formato del email no es válido."
    
    # Validar username (solo alfanumérico y guiones bajos)
    if not username.replace("_", "").replace("-", "").isalnum():
        return False, "El username solo puede contener letras, números, guiones y guiones bajos."
    
    # Validar longitud de username
    if len(username) < 3 or len(username) > 20:
        return False, "El username debe tener entre 3 y 20 caracteres."
    
    # Validar contraseña si se proporciona
    if password is not None:
        if len(password) < 6:
            return False, "La contraseña debe tener al menos 6 caracteres."
    
    return True, ""

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
        return False, "Hora de fin debe ser posterior a hora de inicio", warnings
    
    # ❌ CRÍTICO 2: Mismo día (RECHAZAR si falla) 
    if end_dt.date() != start_dt.date():
        return False, "La sesión no puede extenderse a múltiples días", warnings
    
    # ❌ CRÍTICO 3: Duración excesiva claramente errónea (RECHAZAR)
    duration_minutes = (end_dt - start_dt).total_seconds() / 60
    
    if duration_minutes > 180:  # 3 horas - claramente un error
        return False, f"Duración excesiva: {duration_minutes/60:.1f} horas (máximo razonable: 3h)", warnings
    
    if duration_minutes < 1:  # Menos de 1 minuto - error obvio
        return False, f"Duración demasiado corta: {int(duration_minutes)} min (mínimo: 1 min)", warnings
    
    # ⚠️ WARNING 1: Horario recomendado (MÁS FLEXIBLE para imports)
    RECOMMENDED_START = dt.time(8, 0)   # 8:00 AM - más temprano que formularios
    RECOMMENDED_END = dt.time(18, 0)    # 6:00 PM - más tarde que formularios

    # Horario extendido permitido pero con warning
    EXTENDED_START = dt.time(6, 0)      # 6:00 AM límite absoluto
    EXTENDED_END = dt.time(20, 0)       # 8:00 PM límite absoluto
    
    if start_dt.time() < RECOMMENDED_START:
        if start_dt.time() >= EXTENDED_START:
            warnings.append(f"Inicio temprano: {start_dt.time().strftime('%H:%M')} (recomendado: 8:00-18:00)")
        else:
            warnings.append(f"Inicio muy temprano: {start_dt.time().strftime('%H:%M')} (límite: 6:00)")
    
    if start_dt.time() >= RECOMMENDED_END:
        if start_dt.time() <= EXTENDED_END:
            warnings.append(f"Inicio tardío: {start_dt.time().strftime('%H:%M')} (recomendado: 8:00-18:00)")
        else:
            warnings.append(f"Inicio muy tardío: {start_dt.time().strftime('%H:%M')} (límite: 20:00)")
    
    if end_dt.time() <= RECOMMENDED_START:
        warnings.append(f"Fin muy temprano: {end_dt.time().strftime('%H:%M')} (recomendado: después de 8:00)")
    
    if end_dt.time() > RECOMMENDED_END:
        if end_dt.time() <= EXTENDED_END:
            warnings.append(f"Fin tardío: {end_dt.time().strftime('%H:%M')} (recomendado: 8:00-18:00)")
        else:
            warnings.append(f"Fin muy tardío: {end_dt.time().strftime('%H:%M')} (límite: 20:00)")
    
    # ⚠️ WARNING 2: Duración (FLEXIBLE - permitir pero avisar)
    if duration_minutes < 60:
        warnings.append(f"Duración muy corta: {int(duration_minutes)} min (recomendado: 60+ min)")
    
    if duration_minutes > 180:  # 3 horas
        warnings.append(f"Duración larga: {duration_minutes/60:.1f}h (recomendado: menos de 3h)")
    
    # ⚠️ WARNING 3: Horarios poco comunes (fines de semana, etc.)
    weekday = start_dt.weekday()  # 0=Monday, 6=Sunday
    
    if weekday >= 5:  # Sábado (5) o Domingo (6)
        warnings.append(f"Sesión en fin de semana: {['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'][weekday]}")
    
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


def auto_correct_session_time(session_date: dt.date, start_time: dt.time, end_time: dt.time) -> Tuple[dt.time, dt.time, List[str]]:
    """
    Auto-corrige horarios problemáticos de forma conservadora.
    (Función opcional para implementar más adelante si es necesario)
    
    Args:
        session_date: Fecha de la sesión
        start_time: Hora de inicio problemática
        end_time: Hora de fin problemática
        
    Returns:
        Tuple[dt.time, dt.time, List[str]]: (corrected_start, corrected_end, corrections_made)
    """
    corrections = []
    corrected_start = start_time
    corrected_end = end_time
    
    # 1. Si está fuera del horario laboral, mover al horario válido más cercano
    WORK_START = dt.time(8, 0)
    WORK_END = dt.time(18, 0)
    
    if start_time < WORK_START:
        corrected_start = WORK_START
        corrections.append(f"Inicio movido de {start_time} a {WORK_START}")
    elif start_time >= WORK_END:
        corrected_start = dt.time(17, 0)  # Una hora antes del cierre
        corrections.append(f"Inicio movido de {start_time} a 17:00")
    
    if end_time > WORK_END:
        corrected_end = WORK_END
        corrections.append(f"Fin movido de {end_time} a {WORK_END}")
    elif end_time <= WORK_START:
        corrected_end = dt.time(9, 0)  # Una hora después de apertura
        corrections.append(f"Fin movido de {end_time} a 09:00")
    
    # 2. Verificar que sigue siendo válido después de corrección
    if corrected_end <= corrected_start:
        # Si la corrección causó conflicto, hacer sesión de 1 hora
        corrected_end = dt.time(corrected_start.hour + 1, corrected_start.minute)
        if corrected_end > WORK_END:
            corrected_start = dt.time(17, 0)
            corrected_end = WORK_END
        corrections.append("Duración ajustada a 1 hora por conflicto")
    
    # 3. Verificar duración máxima
    start_dt = dt.datetime.combine(session_date, corrected_start)
    end_dt = dt.datetime.combine(session_date, corrected_end)
    duration = (end_dt - start_dt).total_seconds() / 60
    
    if duration > 240:  # Más de 4 horas
        corrected_end = dt.time(corrected_start.hour + 4, corrected_start.minute)
        if corrected_end > WORK_END:
            corrected_end = WORK_END
        corrections.append("Duración limitada a 4 horas máximo")
    
    return corrected_start, corrected_end, corrections

validate_session_time_strict = validate_session_time  # La función original es la estricta
validate_session_time_flexible = validate_session_for_import_simple  # La nueva función flexible
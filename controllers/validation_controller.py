# controllers/validation_controller.py
"""
Controlador central de validaciones para la aplicación Ballers.
Centraliza TODAS las validaciones eliminando duplicaciones masivas.
"""
import datetime as dt
import os
import re
from typing import Tuple, Optional, List, Dict, Any, Union
from config import WORK_HOURS_FLEXIBLE, WORK_HOURS_STRICT, SESSION_DURATION


class ValidationController:
    """
    Controlador central para TODAS las validaciones de la aplicación.
    Elimina duplicaciones y centraliza lógica de validación.
    """
    
    # ========================================================================
    # VALIDACIONES DE USUARIO (consolidadas desde user_controller.py y settings.py)
    # ========================================================================
    
    @staticmethod
    def validate_user_fields(
        name: str, 
        username: str, 
        email: str, 
        password: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validación UNIFICADA de campos básicos de usuario.
        Reemplaza: user_controller._validate_user_data() y validation.validate_user_data()
        
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
        
        # Validar formato de email
        if not ValidationController.validate_email_format(email):
            return False, "The email format is invalid."
        
        # Validar username formato
        valid_username, username_error = ValidationController.validate_username_format(username)
        if not valid_username:
            return False, username_error
        
        # Validar contraseña si se proporciona
        if password is not None:
            valid_password, password_error = ValidationController.validate_password_strength(password)
            if not valid_password:
                return False, password_error
        
        return True, ""
    
    @staticmethod
    def validate_email_format(email: str) -> bool:
        """
        Validación unificada de formato de email.
        Reemplaza validaciones dispersas en settings.py, user_controller.py, validation.py
        """
        if not email:
            return False
        
        # Validación básica mejorada
        if "@" not in email or "." not in email.split("@")[-1]:
            return False
        
        # Validación con regex más robusta
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))
    
    @staticmethod
    def validate_username_format(username: str) -> Tuple[bool, str]:
        """
        Validación unificada de formato de username.
        Reemplaza validaciones en user_controller.py y validation.py
        """
        if not username:
            return False, "The username is required."
        
        # Validar caracteres permitidos
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "The username can only contain letters, numbers, hyphens and underscores."
        
        # Validar longitud
        if len(username) < 3 or len(username) > 20:
            return False, "The username must be between 3 and 20 characters long."
        
        return True, ""
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """
        Validación unificada de fortaleza de contraseña.
        Centraliza validaciones dispersas.
        """
        if not password:
            return False, "The password is required."
        
        if len(password) < 6:
            return False, "The password must be at least 6 characters long."
        
        # Opcional: validaciones más estrictas
        if len(password) < 8:
            return True, ""  # Advertencia suave, pero válido
        
        return True, ""
    
    @staticmethod
    def validate_password_match(password: str, confirm_password: str) -> Tuple[bool, str]:
        """
        Validación unificada de confirmación de contraseña.
        Reemplaza duplicaciones en settings.py (líneas ~180 y ~280)
        """
        if password != confirm_password:
            return False, "The passwords do not match."
        return True, ""
    
    # ========================================================================
    # VALIDACIONES DE SESIONES (consolidadas desde validation.py y administration.py)
    # ========================================================================
    
    @staticmethod
    def validate_session_time_strict(
        session_date: dt.date, 
        start_time: dt.time, 
        end_time: dt.time
    ) -> Tuple[bool, str]:
        """
        Validación ESTRICTA de horarios para CREAR sesiones nuevas.
        Reemplaza: validation.validate_session_time() con horarios estrictos
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        # 1. Verificar que end_time > start_time
        if end_time <= start_time:
            return False, "The end time must be later than the start time."
        
        # 2. Verificar horario de trabajo ESTRICTO (8:00 - 18:00)
        WORK_START = dt.time(8, 0)
        WORK_END = dt.time(18, 0)
        
        if start_time < WORK_START or start_time >= WORK_END:
            return False, f"The start time must be between {WORK_START.strftime('%H:%M')} and {WORK_END.strftime('%H:%M')}."
        
        if end_time <= WORK_START or end_time > dt.time(19, 0):  # Fin hasta 19:00
            return False, f"The end time must be between {WORK_START.strftime('%H:%M')} and 19:00."
        
        # 3. Verificar duración
        valid_duration, duration_error = ValidationController.validate_session_duration(
            session_date, start_time, end_time, strict=True
        )
        if not valid_duration:
            return False, duration_error
        
        return True, ""
    
    @staticmethod
    def validate_session_time_flexible(
        start_dt: dt.datetime, 
        end_dt: dt.datetime
    ) -> Tuple[bool, str, List[str]]:
        """
        Validación FLEXIBLE de horarios para IMPORTS de Google Calendar.
        Reemplaza: validation.validate_session_for_import()
        
        Returns:
            Tuple[bool, str, List[str]]: (is_valid, error_message, warnings_list)
        """
        warnings = []
        
        # ❌ CRÍTICOS (rechazan)
        if end_dt <= start_dt:
            return False, "End time must be later than start time", warnings
        
        if end_dt.date() != start_dt.date():
            return False, "The session cannot be spread over multiple days", warnings
        
        # Duración excesiva
        duration_minutes = (end_dt - start_dt).total_seconds() / 60
        if duration_minutes > 180:  # 3 horas
            return False, f"Excessive duration: {duration_minutes/60:.1f} hours (maximum: 3h)", warnings
        
        if duration_minutes < 1:
            return False, f"Duration too short: {int(duration_minutes)} min (minimum: 1 min)", warnings
        
        # ⚠️ WARNINGS (permiten pero alertan)
        warnings.extend(ValidationController._check_time_warnings(start_dt, end_dt))
        warnings.extend(ValidationController._check_duration_warnings(duration_minutes))
        warnings.extend(ValidationController._check_weekend_warnings(start_dt))
        
        return True, "", warnings
    
    @staticmethod
    def validate_session_duration(
        session_date: dt.date, 
        start_time: dt.time, 
        end_time: dt.time, 
        strict: bool = True
    ) -> Tuple[bool, str]:
        """
        Validación unificada de duración de sesión.
        """
        start_dt = dt.datetime.combine(session_date, start_time)
        end_dt = dt.datetime.combine(session_date, end_time)
        duration_minutes = (end_dt - start_dt).total_seconds() / 60
        
        if strict:
            # Modo estricto para formularios
            if duration_minutes < 60:
                return False, "The session should last at least 60 minutes."
            if duration_minutes > 120:
                return False, "The session cannot last more than 2 hours."
        else:
            # Modo flexible para imports
            if duration_minutes < 15:
                return False, "The session should last at least 15 minutes."
            if duration_minutes > 180:
                return False, "The session cannot last more than 3 hours."
        
        return True, ""
    
    # ========================================================================
    # VALIDACIONES DE FECHAS (consolidadas desde ballers.py y administration.py)
    # ========================================================================
    
    @staticmethod
    def validate_date_range(start_date: dt.date, end_date: dt.date) -> Tuple[bool, str]:
        """
        Validación unificada de rangos de fecha.
        Reemplaza duplicaciones en ballers.py y administration.py
        """
        if end_date < start_date:
            return False, "The 'To' date must be on or after the 'From' date."
        return True, ""
    
    @staticmethod
    def validate_future_date(date: dt.date, allow_today: bool = True) -> Tuple[bool, str]:
        """
        Validación de fechas futuras para sesiones.
        """
        today = dt.date.today()
        
        if allow_today:
            if date < today:
                return False, "The date cannot be in the past."
        else:
            if date <= today:
                return False, "The date must be in the future."
        
        return True, ""
    
    # ========================================================================
    # VALIDACIONES DE AUTENTICACIÓN (consolidadas desde auth_controller.py)
    # ========================================================================
    
    @staticmethod
    def validate_login_fields(username: str, password: str) -> Tuple[bool, str]:
        """
        Validación unificada de campos de login.
        Reemplaza validaciones en auth_controller.py
        """
        if not username or not password:
            return False, "Please enter username and password"
        
        if not username.strip() or not password.strip():
            return False, "Username and password cannot be empty"
        
        return True, ""
    
    # ========================================================================
    # VALIDACIONES DE ARCHIVOS (consolidadas desde settings.py y user_controller.py)
    # ========================================================================
    
    @staticmethod
    def validate_profile_photo(uploaded_file) -> Tuple[bool, str]:
        """
        Validación unificada de fotos de perfil.
        Centraliza validaciones de archivos.
        """
        if not uploaded_file:
            return True, ""  # Opcional
        
        # Validar extensión
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            return False, f"File type not allowed. Use: {', '.join(allowed_extensions)}"
        
        # Validar tamaño (2MB máximo)
        max_size_mb = 2
        if hasattr(uploaded_file, 'size'):
            if uploaded_file.size > max_size_mb * 1024 * 1024:
                return False, f"File too large. Maximum size: {max_size_mb}MB"
        
        return True, ""
    
    # ========================================================================
    # VALIDACIONES DE EXISTENCIA EN BD (consolidadas desde session_controller.py)
    # ========================================================================
    
    @staticmethod
    def validate_user_exists_and_active(user, user_type: str = "user") -> Tuple[bool, str]:
        """
        Validación unificada de existencia y estado activo de usuarios.
        """
        if not user:
            return False, f"{user_type.capitalize()} not found"
        
        if hasattr(user, 'is_active') and not user.is_active:
            return False, f"{user_type.capitalize()} is deactivated"
        
        return True, ""
    
    @staticmethod
    def validate_coach_exists(coach) -> Tuple[bool, str]:
        """Validación específica de coach."""
        return ValidationController.validate_user_exists_and_active(coach, "coach")
    
    @staticmethod
    def validate_player_exists(player) -> Tuple[bool, str]:
        """Validación específica de player."""
        return ValidationController.validate_user_exists_and_active(player, "player")
    
    @staticmethod
    def validate_session_exists(session) -> Tuple[bool, str]:
        """Validación de existencia de sesión."""
        if not session:
            return False, "Session not found"
        return True, ""
    
    # ========================================================================
    # VALIDACIONES DE CONFIRMACIÓN (consolidadas desde settings.py)
    # ========================================================================
    
    @staticmethod
    def validate_deletion_confirmation(confirm_text: str, expected: str = "DELETE") -> Tuple[bool, str]:
        """
        Validación unificada de confirmación de eliminación.
        Reemplaza validaciones en settings.py
        """
        if confirm_text != expected:
            return False, f"Please type '{expected}' to confirm."
        return True, ""
    
    # ========================================================================
    # MÉTODOS PRIVADOS DE APOYO
    # ========================================================================
    
    @staticmethod
    def _check_time_warnings(start_dt: dt.datetime, end_dt: dt.datetime) -> List[str]:
        """Verifica warnings de horarios para imports flexibles."""
        warnings = []
        
        RECOMMENDED_START = dt.time(8, 0)
        RECOMMENDED_END = dt.time(18, 0)
        EXTENDED_START = dt.time(6, 0)
        EXTENDED_END = dt.time(20, 0)
        
        # Warnings para horarios tempranos/tardíos
        if start_dt.time() < RECOMMENDED_START:
            if start_dt.time() >= EXTENDED_START:
                warnings.append(f"Early start: {start_dt.time().strftime('%H:%M')} (recommended: 8:00-18:00)")
            else:
                warnings.append(f"Very early start: {start_dt.time().strftime('%H:%M')} (limit: 6:00)")
        
        if start_dt.time() > RECOMMENDED_END:
            if start_dt.time() <= EXTENDED_END:
                warnings.append(f"Late start: {start_dt.time().strftime('%H:%M')} (recommended: 8:00-18:00)")
            else:
                warnings.append(f"Very late start: {start_dt.time().strftime('%H:%M')} (limit: 20:00)")
        
        return warnings
    
    @staticmethod
    def _check_duration_warnings(duration_minutes: float) -> List[str]:
        """Verifica warnings de duración."""
        warnings = []
        
        if duration_minutes < 60:
            warnings.append(f"Duration short: {int(duration_minutes)} min (recommended: 60 min)")
        
        if duration_minutes > 120:
            warnings.append(f"Duration long: {duration_minutes/60:.1f}h (recommended: less than 2h)")
        
        return warnings
    
    @staticmethod
    def _check_weekend_warnings(start_dt: dt.datetime) -> List[str]:
        """Verifica warnings de fines de semana."""
        warnings = []
        
        weekday = start_dt.weekday()  # 0=Monday, 6=Sunday
        if weekday >= 5:  # Sábado (5) o Domingo (6)
            day_names = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
            warnings.append(f"Weekend session: {day_names[weekday]}")
        
        return warnings


# ========================================================================
# FUNCIONES DE CONVENIENCIA (compatibilidad con código existente)
# ========================================================================

def validate_user_data(name: str, username: str, email: str, password: Optional[str] = None) -> Tuple[bool, str]:
    """Función de conveniencia - mantiene compatibilidad con validation.py"""
    return ValidationController.validate_user_fields(name, username, email, password)

def validate_session_time(session_date: dt.date, start_time: dt.time, end_time: dt.time) -> Tuple[bool, str]:
    """Función de conveniencia - mantiene compatibilidad con validation.py"""
    return ValidationController.validate_session_time_strict(session_date, start_time, end_time)

def validate_session_for_import(start_dt: dt.datetime, end_dt: dt.datetime) -> Tuple[bool, str, List[str]]:
    """Función de conveniencia - mantiene compatibilidad con validation.py"""
    return ValidationController.validate_session_time_flexible(start_dt, end_dt)

def validate_session_datetime(start_dt: dt.datetime, end_dt: dt.datetime) -> Tuple[bool, str]:
    """Función de conveniencia - mantiene compatibilidad con validation.py"""
    is_valid, error, _ = ValidationController.validate_session_time_flexible(start_dt, end_dt)
    return is_valid, error
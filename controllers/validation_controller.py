# controllers/validation_controller.py
"""
Controlador central de validaciones para la aplicación Ballers.
Centraliza TODAS las validaciones eliminando duplicaciones masivas.
"""
import datetime as dt
import re
from typing import Tuple, Optional, List, Union, Any

# CONFIGURACIÓN DE HORARIOS CENTRALIZADOS (movido desde administration.py)

class ScheduleConfig:
    """Configuración centralizada de horarios para formularios."""
    
    # Horarios ESTRICTOS para CREAR sesiones
    CREATE_START_HOUR_MIN = 8   # 8:00
    CREATE_START_HOUR_MAX = 18  # último inicio: 18:00
    CREATE_END_HOUR_MIN = 9     # 9:00  
    CREATE_END_HOUR_MAX = 19    # último fin: 19:00
    
    # Horarios BASE para EDITAR (recomendados)
    EDIT_BASE_START_MIN = 8     # 8:00
    EDIT_BASE_START_MAX = 18    # 18:00
    EDIT_BASE_END_MIN = 9       # 9:00
    EDIT_BASE_END_MAX = 19      # 19:00
    
    # Horarios EXTENDIDOS para EDITAR (permitidos con advertencia)
    EDIT_EXTENDED_START_MIN = 6   # 6:00
    EDIT_EXTENDED_START_MAX = 22  # 22:00  
    EDIT_EXTENDED_END_MIN = 7     # 7:00
    EDIT_EXTENDED_END_MAX = 23    # 23:00
    
    # Horarios RECOMENDADOS (para advertencias)
    RECOMMENDED_START = dt.time(8, 0)
    RECOMMENDED_END = dt.time(19, 0)  # 🔧 FIX: 19:00 es válido
    
class ValidationController:
    """
    Controlador central para TODAS las validaciones de la aplicación.
    Elimina duplicaciones y centraliza lógica de validación.
    """
    
    # Validaciones de usuario
    
    @staticmethod
    def validate_user_fields(
        name: str, 
        username: str, 
        email: str, 
        password: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validación unificada de campos básicos de usuario.
        
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
    
    # Validaciones de sesiones
    
    @staticmethod
    def validate_session_time_strict(
        session_date: dt.date, 
        start_time: dt.time, 
        end_time: dt.time
    ) -> Tuple[bool, str]:
        """
        Validación estricta de horarios para Crear sesiones nuevas.
        
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
        
        if duration_minutes < 45:
            return False, f"Duration too short: {int(duration_minutes)} min (minimum: 45 min)", warnings
        
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
            if duration_minutes < 45:
                return False, "The session should last at least 15 minutes."
            if duration_minutes > 180:
                return False, "The session cannot last more than 3 hours."
        
        return True, ""
    

    # Validaciones de fechas

    
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
 
    # Validaciones de autentificacion
    
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
    
    # Validaciones de archivos
    
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
    
    # Validaciones de existencia en BD

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
    
    # Validaciones de confirmacion
    
    @staticmethod
    def validate_deletion_confirmation(confirm_text: str, expected: str = "DELETE") -> Tuple[bool, str]:
        """
        Validación unificada de confirmación de eliminación.
        Reemplaza validaciones en settings.py
        """
        if confirm_text != expected:
            return False, f"Please type '{expected}' to confirm."
        return True, ""
    

    # Métodos privados de apoyo
    
    @staticmethod
    def _check_time_warnings(start_dt: dt.datetime, end_dt: dt.datetime) -> List[str]:
        """Verifica warnings de horarios para imports flexibles."""
        warnings = []
        
        RECOMMENDED_START = dt.time(8, 0)
        RECOMMENDED_END = dt.time(19, 0)
        EXTENDED_START = dt.time(6, 0)
        EXTENDED_END = dt.time(21, 0)
        
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

        if end_dt.time() < RECOMMENDED_START:
            if end_dt.time() >= EXTENDED_START:
                warnings.append(f"Early end: {start_dt.time().strftime('%H:%M')} (recommended: 9:00-19:00)")
            else:
                warnings.append(f"Very early end: {start_dt.time().strftime('%H:%M')} (limit: 7:00)")
        if end_dt.time() > RECOMMENDED_END:
            if end_dt.time() <= EXTENDED_END:
                warnings.append(f"Late end: {start_dt.time().strftime('%H:%M')} (recommended: 9:00-19:00)")
            else:
                warnings.append(f"Very late end: {start_dt.time().strftime('%H:%M')} (limit: 21:00)")
        
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
    @staticmethod
    def validate_coach_selection(coach_id: Optional[int]) -> Tuple[bool, str]:
        """
        Validación de selección de coach en formularios.
        Reemplaza validación manual en administration.py
        """
        if coach_id is None:
            return False, "Please select a coach"
        return True, ""

    @staticmethod  
    def validate_player_selection(player_id: Optional[int]) -> Tuple[bool, str]:
        """
        Validación de selección de player en formularios.
        """
        if player_id is None:
            return False, "Please select a player"
        return True, ""

    @staticmethod
    def validate_date_within_allowed_range(
        date: dt.date, 
        min_date: Optional[dt.date] = None, 
        max_date: Optional[dt.date] = None
    ) -> Tuple[bool, str, dt.date]:
        """
        Validación de fecha dentro de rango permitido.
        Reemplaza validación manual en administration.py
        
        Args:
            date: Fecha a validar
            min_date: Fecha mínima permitida (por defecto: hoy)
            max_date: Fecha máxima permitida (por defecto: hoy + 90 días)
            
        Returns:
            Tuple[bool, str, dt.date]: (is_valid, error_message, corrected_date)
        """
        if min_date is None:
            min_date = dt.date.today()
        if max_date is None:
            max_date = dt.date.today() + dt.timedelta(days=90)
        
        if date < min_date:
            return False, f"Date cannot be before {min_date.strftime('%d/%m/%Y')}", min_date
        elif date > max_date:
            return False, f"Date cannot be after {max_date.strftime('%d/%m/%Y')}", max_date
        
        return True, "", date

    @staticmethod
    def validate_time_index_in_list(
        time_value: dt.time, 
        available_times: List[dt.time],
        field_name: str = "time"
    ) -> Tuple[bool, str, int]:
        """
        Validación de tiempo en lista de horarios disponibles.
        Reemplaza validación manual try/except en administration.py
        
        Args:
            time_value: Tiempo a buscar
            available_times: Lista de tiempos disponibles
            field_name: Nombre del campo para el mensaje de error
            
        Returns:
            Tuple[bool, str, int]: (is_valid, error_message, safe_index)
        """
        try:
            index = available_times.index(time_value)
            return True, "", index
        except ValueError:
            # Buscar el tiempo más cercano como fallback
            closest_index = 0
            if available_times:
                closest_time = min(available_times, key=lambda t: abs(
                    (dt.datetime.combine(dt.date.today(), t) - 
                    dt.datetime.combine(dt.date.today(), time_value)).total_seconds()
                ))
                closest_index = available_times.index(closest_time)
            
            error_msg = (f"{field_name.capitalize()} {time_value.strftime('%H:%M')} not available. "
                        f"Using closest available: {available_times[closest_index].strftime('%H:%M')}")
            
            return False, error_msg, closest_index

    @staticmethod
    def validate_session_form_data(
        coach_id: Optional[int],
        player_id: Optional[int], 
        session_date: dt.date,
        start_time: dt.time,
        end_time: dt.time
    ) -> Tuple[bool, str]:
        """
        Validación completa de formulario de sesión.
        Combina múltiples validaciones en una sola función.
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        # Validar selecciones
        coach_valid, coach_error = ValidationController.validate_coach_selection(coach_id)
        if not coach_valid:
            return False, coach_error
        
        player_valid, player_error = ValidationController.validate_player_selection(player_id)
        if not player_valid:
            return False, player_error
        
        # Validar fecha
        date_valid, date_error, _ = ValidationController.validate_date_within_allowed_range(session_date)
        if not date_valid:
            return False, date_error
        
        # Validar horarios
        time_valid, time_error = ValidationController.validate_session_time_strict(
            session_date, start_time, end_time
        )
        if not time_valid:
            return False, time_error
        
        return True, ""
    
    # Generación de horarios para sesiones
    
    @staticmethod
    def get_create_session_hours() -> Tuple[List[dt.time], List[dt.time]]:
        """
        Obtiene horarios ESTRICTOS para crear sesiones nuevas.
        Reemplaza la lógica duplicada en administration.py
        
        Returns:
            Tuple[List[dt.time], List[dt.time]]: (start_hours, end_hours)
        """
        start_hours = [dt.time(h, 0) for h in range(
            ScheduleConfig.CREATE_START_HOUR_MIN, 
            ScheduleConfig.CREATE_START_HOUR_MAX + 1
        )]
        
        end_hours = [dt.time(h, 0) for h in range(
            ScheduleConfig.CREATE_END_HOUR_MIN, 
            ScheduleConfig.CREATE_END_HOUR_MAX + 1
        )]
        
        return start_hours, end_hours

    @staticmethod  
    def get_edit_session_hours(
        existing_start: Optional[dt.time] = None,
        existing_end: Optional[dt.time] = None
    ) -> Tuple[List[dt.time], List[dt.time]]:
        """
        Obtiene horarios FLEXIBLES para editar sesiones existentes.
        Incluye horarios extendidos si la sesión actual los necesita.
        Reemplaza get_flexible_hours() de administration.py
        
        Args:
            existing_start: Hora actual de inicio (opcional)
            existing_end: Hora actual de fin (opcional)
            
        Returns:
            Tuple[List[dt.time], List[dt.time]]: (start_hours, end_hours)
        """
        # Horarios base recomendados
        base_start = [dt.time(h, 0) for h in range(
            ScheduleConfig.EDIT_BASE_START_MIN,
            ScheduleConfig.EDIT_BASE_START_MAX + 1
        )]
        
        base_end = [dt.time(h, 0) for h in range(
            ScheduleConfig.EDIT_BASE_END_MIN,
            ScheduleConfig.EDIT_BASE_END_MAX + 1
        )]
        
        # Si no hay horarios existentes, usar base
        if not existing_start and not existing_end:
            return base_start, base_end
        
        # Función helper para extender horarios si es necesario
        def extend_hours_if_needed(current_time: Optional[dt.time], base_hours: List[dt.time], is_start: bool) -> List[dt.time]:
            if not current_time or current_time in base_hours:
                return base_hours
            
            # Generar horarios extendidos
            if is_start:
                extended = [dt.time(h, 0) for h in range(
                    ScheduleConfig.EDIT_EXTENDED_START_MIN,
                    ScheduleConfig.EDIT_EXTENDED_START_MAX + 1
                )]
            else:
                extended = [dt.time(h, 0) for h in range(
                    ScheduleConfig.EDIT_EXTENDED_END_MIN,
                    ScheduleConfig.EDIT_EXTENDED_END_MAX + 1
                )]
            
            # Si está en extendidos, usar extendidos
            if current_time in extended:
                return extended
            
            # Si está completamente fuera, agregarlo manualmente
            combined = base_hours + [current_time]
            return sorted(combined)
        
        # Extender horarios si es necesario
        final_start = extend_hours_if_needed(existing_start, base_start, True)
        final_end = extend_hours_if_needed(existing_end, base_end, False)
        
        return final_start, final_end

    @staticmethod
    def check_session_time_recommendation(start_time: dt.time, end_time: dt.time) -> Tuple[bool, str]:
        """
        Verifica si los horarios están dentro del rango recomendado.
        Reemplaza la validación manual en administration.py
        
        Args:
            start_time: Hora de inicio
            end_time: Hora de fin
            
        Returns:
            Tuple[bool, str]: (is_recommended, warning_message)
        """
        issues = []
        
        if start_time < ScheduleConfig.RECOMMENDED_START:
            issues.append(f"start time {start_time.strftime('%H:%M')} is early")
        
        if start_time >= dt.time(18, 0):  # 18:00 o después para inicio es tarde
            issues.append(f"start time {start_time.strftime('%H:%M')} is late")
        
        if end_time <= dt.time(9, 0):  # 9:00 o antes para fin es muy temprano
            issues.append(f"end time {end_time.strftime('%H:%M')} is very early")
        
        if end_time > ScheduleConfig.RECOMMENDED_END:
            issues.append(f"end time {end_time.strftime('%H:%M')} is late")
        
        if issues:
            warning = (f"⚠️ **Note**: This session has {', '.join(issues)} "
                    f"(recommended: {ScheduleConfig.RECOMMENDED_START.strftime('%H:%M')}-"
                    f"{ScheduleConfig.RECOMMENDED_END.strftime('%H:%M')}). "
                    "Consider rescheduling to a standard time slot.")
            return False, warning
        
        return True, ""

    @staticmethod
    def validate_coach_selection_safe(coach_id: Union[int, None, Any]) -> Tuple[bool, str, Optional[int]]:
        """
        Validación SEGURA de coach que maneja tipos Unknown/Any de Pylance.
        🔧 FIX: Arreglado problema de tipos con len()
        
        Args:
            coach_id: ID del coach (puede ser None, int, o Unknown)
            
        Returns:
            Tuple[bool, str, Optional[int]]: (is_valid, error_message, safe_coach_id)
        """
        # Verificar None o valores vacíos
        if coach_id is None:
            return False, "Please select a coach", None
        
        # Verificar strings vacíos (solo si es string)
        if isinstance(coach_id, str):
            if coach_id.strip() == "":
                return False, "Please select a coach", None
            # Intentar convertir string a int
            try:
                coach_id = int(coach_id)
            except (ValueError, TypeError):
                return False, "Invalid coach selection format", None
        
        # Verificar listas vacías (solo si tiene __len__ y no es int)
        if hasattr(coach_id, '__len__') and not isinstance(coach_id, (int, str)):
            try:
                if len(coach_id) == 0:  # type: ignore
                    return False, "Please select a coach", None
            except TypeError:
                pass  # Si falla len(), continuar con la validación normal
        
        # Intentar convertir a int si no es int ya
        try:
            if not isinstance(coach_id, int):
                coach_id = int(coach_id)
            
            if coach_id <= 0:
                return False, "Invalid coach selection", None
                
            return True, "", coach_id
            
        except (ValueError, TypeError):
            return False, "Invalid coach selection format", None

    @staticmethod
    def validate_player_selection_safe(player_id: Union[int, None, Any]) -> Tuple[bool, str, Optional[int]]:
        """
        Validación SEGURA de player que maneja tipos Unknown/Any de Pylance.
        🔧 FIX: Arreglado problema de tipos con len()
        """
        # Verificar None o valores vacíos
        if player_id is None:
            return False, "Please select a player", None
        
        # Verificar strings vacíos (solo si es string)
        if isinstance(player_id, str):
            if player_id.strip() == "":
                return False, "Please select a player", None
            # Intentar convertir string a int
            try:
                player_id = int(player_id)
            except (ValueError, TypeError):
                return False, "Invalid player selection format", None
        
        # Verificar listas vacías (solo si tiene __len__ y no es int)
        if hasattr(player_id, '__len__') and not isinstance(player_id, (int, str)):
            try:
                if len(player_id) == 0:  # type: ignore
                    return False, "Please select a player", None
            except TypeError:
                pass  # Si falla len(), continuar con la validación normal
        
        # Intentar convertir a int si no es int ya
        try:
            if not isinstance(player_id, int):
                player_id = int(player_id)
            
            if player_id <= 0:
                return False, "Invalid player selection", None
                
            return True, "", player_id
            
        except (ValueError, TypeError):
            return False, "Invalid player selection format", None
    


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
def validate_coach_selection(coach_id: Optional[int]) -> Tuple[bool, str]:
    """Función de conveniencia para validación de coach."""
    return ValidationController.validate_coach_selection(coach_id)

def validate_player_selection(player_id: Optional[int]) -> Tuple[bool, str]:
    """Función de conveniencia para validación de player.""" 
    return ValidationController.validate_player_selection(player_id)

def validate_session_form_data(
    coach_id: Optional[int],
    player_id: Optional[int], 
    session_date: dt.date,
    start_time: dt.time,
    end_time: dt.time
) -> Tuple[bool, str]:
    """Función de conveniencia para validación completa de formulario."""
    return ValidationController.validate_session_form_data(
        coach_id, player_id, session_date, start_time, end_time
    )
def get_create_session_hours() -> Tuple[List[dt.time], List[dt.time]]:
    """Función de conveniencia para horarios de crear sesión."""
    return ValidationController.get_create_session_hours()

def get_edit_session_hours(
    existing_start: Optional[dt.time] = None,
    existing_end: Optional[dt.time] = None
) -> Tuple[List[dt.time], List[dt.time]]:
    """Función de conveniencia para horarios de editar sesión."""
    return ValidationController.get_edit_session_hours(existing_start, existing_end)

def check_session_time_recommendation(start_time: dt.time, end_time: dt.time) -> Tuple[bool, str]:
    """Función de conveniencia para verificar horarios recomendados."""
    return ValidationController.check_session_time_recommendation(start_time, end_time)

def validate_coach_selection_safe(coach_id: Union[int, None, Any]) -> Tuple[bool, str, Optional[int]]:
    """Función de conveniencia para validación segura de coach."""
    return ValidationController.validate_coach_selection_safe(coach_id)

def validate_player_selection_safe(player_id: Union[int, None, Any]) -> Tuple[bool, str, Optional[int]]:
    """Función de conveniencia para validación segura de player."""
    return ValidationController.validate_player_selection_safe(player_id)
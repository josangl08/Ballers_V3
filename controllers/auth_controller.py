# controllers/auth_controller.py
"""
Controlador para manejo de autenticación y sesiones.
Version migrada a Dash - SIN dependencias de Streamlit.
Usa ValidationController para validación de login fields
"""
from typing import Any, Dict, Optional, Tuple

from common.logging_config import LoggerMixin, log_user_action
from common.utils import hash_password
from controllers.db import get_db_session
from controllers.validation_controller import ValidationController
from models import User


class AuthController(LoggerMixin):
    """
    Controlador para operaciones de autenticación.
    Usa ValidationController para validaciones de login.
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

    # Autenticación básica

    def authenticate_user(
        self, username: str, password: str
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Autentica un usuario con username y password.
        Usa ValidationController para validación de login fields

        Args:
            username: Nombre de usuario
            password: Contraseña en texto plano

        Returns:
            Tuple (success, message, user_object)
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        # Log del intento de autenticación
        self.log_info("authentication_attempt", username=username)

        # Usar ValidationController para validar login fields
        login_valid, login_error = ValidationController.validate_login_fields(
            username, password
        )
        if not login_valid:
            self.log_warning(
                "authentication_validation_failed",
                username=username,
                reason=login_error,
            )
            return False, login_error, None

        try:
            # Buscar usuario por username
            hashed_password = hash_password(password)
            user = (
                self.db.query(User)
                .filter_by(username=username, password_hash=hashed_password)
                .first()
            )

            if not user:
                self.log_warning(
                    "authentication_failed",
                    username=username,
                    reason="invalid_credentials",
                )
                return False, "Incorrect username or password", None

            # Verificar si está activo
            if hasattr(user, "is_active") and not user.is_active:
                self.log_warning(
                    "authentication_failed",
                    username=username,
                    user_id=user.user_id,
                    reason="user_deactivated",
                )
                return (
                    False,
                    "This user is deactivated. Contact an administrator.",
                    None,
                )

            # Login exitoso
            self.log_info(
                "authentication_success",
                username=username,
                user_id=user.user_id,
                user_type=user.user_type.name,
            )

            # Log de acción de usuario usando función de conveniencia
            log_user_action(
                user_id=user.user_id,
                action="login",
                user_type=user.user_type.name,
                username=username,
            )

            return True, f"Welcome, {user.name}!", user

        except Exception as e:
            self.log_error(
                "authentication_exception",
                username=username,
                error=str(e),
                exc_info=True,
            )
            return False, f"Authentication error: {str(e)}", None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Obtiene un usuario por ID para restauración de sesión.

        Args:
            user_id: ID del usuario

        Returns:
            Objeto User o None si no existe/activo
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        try:
            user = self.db.query(User).filter_by(user_id=user_id).first()

            # Verificar que existe y está activo
            if user and getattr(user, "is_active", True):
                return user

        except Exception as e:
            print(f"Error getting user by ID: {e}")

        return None

    # Gestión de sesiones

    def create_session(self, user: User, remember_me: bool = False) -> Dict[str, Any]:
        """
        Crea datos de sesión para un usuario (agnóstico del sistema de almacenamiento).

        Args:
            user: Objeto User autenticado
            remember_me: Si mantener sesión (para futura implementación)

        Returns:
            Diccionario con datos de sesión
        """
        # Datos básicos de sesión
        session_data = {
            "user_id": user.user_id,
            "username": user.username,
            "name": user.name,
            "user_type": user.user_type.name,
            "permit_level": getattr(user, "permit_level", 1),
            "remember_me": remember_me,
        }

        # Log de la creación de sesión
        self.log_info(
            "session_created",
            user_id=user.user_id,
            username=user.username,
            user_type=user.user_type.name,
            remember_me=remember_me,
        )

        return session_data

    def restore_session_from_url(self) -> Tuple[bool, str]:
        """
        TEMPORAL: Método stub para compatibilidad.
        TODO: Implementar con Dash URL routing y storage.
        """
        return False, "No session to restore"

    def clear_session(self, show_message: bool = True) -> None:
        """
        TEMPORAL: Método stub para compatibilidad.
        TODO: Implementar con Dash storage clearing.
        """
        # Log del logout
        self.log_info("session_logout", message="User logged out")
        pass

    # Validaciones y permisos

    def is_logged_in(self, session_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Verifica si hay una sesión activa.
        TEMPORAL: Acepta session_data como parámetro para compatibilidad con Dash.
        """
        if session_data is None:
            # Fallback temporal - no hay sesión
            return False
        return session_data.get("user_id") is not None

    def get_current_user_data(
        self, session_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos del usuario actual desde session_data.
        TEMPORAL: Acepta session_data como parámetro para compatibilidad con Dash.

        Returns:
            Diccionario con datos de usuario o None
        """
        if not self.is_logged_in(session_data):
            return None

        return {
            "user_id": session_data.get("user_id"),
            "username": session_data.get("username"),
            "name": session_data.get("name"),
            "user_type": session_data.get("user_type"),
            "permit_level": session_data.get("permit_level", 1),
        }

    def check_user_type(
        self, required_types: list, session_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Verifica si el usuario actual tiene uno de los tipos requeridos.
        TEMPORAL: Acepta session_data como parámetro para compatibilidad con Dash.

        Args:
            required_types: Lista de tipos permitidos (ej: ["admin", "coach"])
            session_data: Datos de sesión (opcional, para compatibilidad con Dash)

        Returns:
            True si el usuario tiene el tipo requerido
        """
        if not self.is_logged_in(session_data):
            return False

        current_type = session_data.get("user_type") if session_data else None
        return current_type in required_types

    def check_permission_level(
        self, required_level: int, session_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Verifica si el usuario actual tiene el nivel de permiso requerido.
        TEMPORAL: Acepta session_data como parámetro para compatibilidad con Dash.

        Args:
            required_level: Nivel mínimo requerido
            session_data: Datos de sesión (opcional, para compatibilidad con Dash)

        Returns:
            True si el usuario tiene suficiente nivel
        """
        if not self.is_logged_in(session_data):
            return False

        current_level = session_data.get("permit_level", 1) if session_data else 1
        return current_level >= required_level

    def require_login(self, session_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Requiere que el usuario esté logueado.
        TEMPORAL: Acepta session_data como parámetro para compatibilidad con Dash.

        Returns:
            True si está logueado, False si no
        """
        return self.is_logged_in(session_data)

    def require_user_type(
        self, required_types: list, session_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Requiere que el usuario tenga uno de los tipos especificados.
        TEMPORAL: Acepta session_data como parámetro para compatibilidad con Dash.

        Args:
            required_types: Lista de tipos permitidos
            session_data: Datos de sesión (opcional, para compatibilidad con Dash)

        Returns:
            True si tiene permiso, False si no
        """
        if not self.require_login(session_data):
            return False

        return self.check_user_type(required_types, session_data)


def authenticate_user(username: str, password: str) -> Tuple[bool, str, Optional[User]]:
    """Función de conveniencia para mantener compatibilidad."""
    with AuthController() as controller:
        return controller.authenticate_user(username, password)


def create_user_session(user: User, remember_me: bool = False) -> Dict[str, Any]:
    """Función de conveniencia para crear sesión."""
    with AuthController() as controller:
        return controller.create_session(user, remember_me)


def restore_session_from_url() -> Tuple[bool, str]:
    """Función de conveniencia para restaurar sesión."""
    with AuthController() as controller:
        return controller.restore_session_from_url()


def clear_user_session(show_message: bool = True) -> None:
    """Función de conveniencia para logout."""
    with AuthController() as controller:
        return controller.clear_session(show_message)


def is_user_logged_in() -> bool:
    """Función de conveniencia para verificar login."""
    with AuthController() as controller:
        return controller.is_logged_in()


def get_current_user() -> Optional[Dict[str, Any]]:
    """Función de conveniencia para obtener usuario actual."""
    with AuthController() as controller:
        return controller.get_current_user_data()


def require_auth(user_types: Optional[list] = None) -> bool:
    """
    Función de conveniencia para requerir autenticación.

    Args:
        user_types: Lista opcional de tipos de usuario permitidos

    Returns:
        True si tiene permiso
    """
    with AuthController() as controller:
        if user_types:
            return controller.require_user_type(user_types)
        else:
            return controller.require_login()

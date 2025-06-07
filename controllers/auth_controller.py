# controllers/auth_controller.py
"""
Controlador para manejo de autenticación y sesiones.
🔄 REFACTORIZADO: Usa ValidationController para validación de login fields
"""
import streamlit as st
import datetime as dt
import hashlib
from typing import Optional, Tuple, Dict, Any

from models import User, UserType
from controllers.db import get_db_session
from common.utils import hash_password
# 🆕 NUEVO: Import para eliminar duplicación de login validation
from controllers.validation_controller import ValidationController


class AuthController:
    """
    Controlador para operaciones de autenticación.
    🔄 REFACTORIZADO: Usa ValidationController para validaciones de login.
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

    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """
        Autentica un usuario con username y password.
        🔄 REFACTORIZADO: Usa ValidationController para validación de login fields
        
        Args:
            username: Nombre de usuario
            password: Contraseña en texto plano
            
        Returns:
            Tuple (success, message, user_object)
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        # 🔄 REFACTORIZADO: Usar ValidationController para validar login fields
        login_valid, login_error = ValidationController.validate_login_fields(username, password)
        if not login_valid:
            return False, login_error, None
        
        try:
            # Buscar usuario por username
            hashed_password = hash_password(password)
            user = self.db.query(User).filter_by(
                username=username, 
                password_hash=hashed_password
            ).first()
            
            if not user:
                return False, "Incorrect username or password", None
            
            # Verificar si está activo
            # 📝 NOTA: Mantenemos validación original por especificidad del mensaje
            if hasattr(user, 'is_active') and not user.is_active:
                return False, "This user is deactivated. Contact an administrator.", None
            
            return True, f"Welcome, {user.name}!", user
            
        except Exception as e:
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
            if user and getattr(user, 'is_active', True):
                return user
            
        except Exception as e:
            print(f"Error getting user by ID: {e}")
        
        return None


    # Gestión de sesiones

    
    def create_session(self, user: User, remember_me: bool = False) -> Dict[str, Any]:
        """
        Crea una sesión completa para un usuario.
        
        Args:
            user: Objeto User autenticado
            remember_me: Si mantener sesión en URL
            
        Returns:
            Diccionario con datos de sesión
        """
        # Datos básicos de sesión
        session_data = {
            "user_id": user.user_id,
            "username": user.username,
            "name": user.name,
            "user_type": user.user_type.name,
            "permit_level": getattr(user, 'permit_level', 1)
        }
        
        # Guardar en Streamlit session_state
        for key, value in session_data.items():
            st.session_state[key] = value
        
        # Si "recordarme", agregar a URL
        if remember_me:
            st.query_params.update({
                "auto_login": "true",
                "uid": str(user.user_id)
            })
        
        return session_data
    
    def restore_session_from_url(self) -> Tuple[bool, str]:
        """
        Restaura sesión desde parámetros de URL.
        
        Returns:
            Tuple (success, message)
        """
        try:
            # Verificar flag de logout reciente
            if st.session_state.get("just_logged_out", False):
                st.session_state.pop("just_logged_out", None)
                st.query_params.clear()
                return False, "Logout completed"
            
            # Verificar parámetros de URL
            if "auto_login" in st.query_params and "uid" in st.query_params:
                user_id = int(st.query_params["uid"])
                
                # Obtener usuario
                user = self.get_user_by_id(user_id)
                if user:
                    # Crear sesión sin remember_me (ya está en URL)
                    self.create_session(user, remember_me=False)
                    return True, f"Session restored for {user.name}"
                else:
                    # Usuario no válido, limpiar URL
                    st.query_params.clear()
                    return False, "Invalid session data"
            
        except Exception as e:
            print(f"Error restoring session: {e}")
            st.query_params.clear()
        
        return False, "No session to restore"
    
    def clear_session(self, show_message: bool = True) -> None:
        """
        Limpia completamente la sesión (logout).
        
        Args:
            show_message: Si mostrar mensaje de logout
        """
        # Marcar logout para evitar auto-restore
        st.session_state["just_logged_out"] = True
        
        # Limpiar URL
        st.query_params.clear()
        
        # Limpiar sync data específica (para compatibilidad)
        sync_keys = ['last_sync_result', 'show_sync_details', 'show_details_sidebar', 'sync_problems']
        for key in sync_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        # Limpiar session_state general (excepto flag de logout)
        keys_to_delete = [key for key in st.session_state.keys() if key != "just_logged_out"]
        for key in keys_to_delete:
            del st.session_state[key]
        
        if show_message:
            st.success("Has cerrado sesión correctamente")


    # Validaciones y permisos

    
    def is_logged_in(self) -> bool:
        """Verifica si hay una sesión activa."""
        return "user_id" in st.session_state and st.session_state["user_id"]
    
    def get_current_user_data(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos del usuario actual desde session_state.
        
        Returns:
            Diccionario con datos de usuario o None
        """
        if not self.is_logged_in():
            return None
        
        return {
            "user_id": st.session_state.get("user_id"),
            "username": st.session_state.get("username"),
            "name": st.session_state.get("name"),
            "user_type": st.session_state.get("user_type"),
            "permit_level": st.session_state.get("permit_level", 1)
        }
    
    def check_user_type(self, required_types: list) -> bool:
        """
        Verifica si el usuario actual tiene uno de los tipos requeridos.
        
        Args:
            required_types: Lista de tipos permitidos (ej: ["admin", "coach"])
            
        Returns:
            True si el usuario tiene el tipo requerido
        """
        if not self.is_logged_in():
            return False
        
        current_type = st.session_state.get("user_type")
        return current_type in required_types
    
    def check_permission_level(self, required_level: int) -> bool:
        """
        Verifica si el usuario actual tiene el nivel de permiso requerido.
        
        Args:
            required_level: Nivel mínimo requerido
            
        Returns:
            True si el usuario tiene suficiente nivel
        """
        if not self.is_logged_in():
            return False
        
        current_level = st.session_state.get("permit_level", 1)
        return current_level >= required_level
    
    def require_login(self) -> bool:
        """
        Requiere que el usuario esté logueado. Si no, redirige al login.
        
        Returns:
            True si está logueado, False si redirige
        """
        if not self.is_logged_in():
            st.error("You must be logged in to access this page.")
            st.stop()
        return True
    
    def require_user_type(self, required_types: list) -> bool:
        """
        Requiere que el usuario tenga uno de los tipos especificados.
        
        Args:
            required_types: Lista de tipos permitidos
            
        Returns:
            True si tiene permiso, False si no (y muestra error)
        """
        self.require_login()
        
        if not self.check_user_type(required_types):
            current_type = st.session_state.get("user_type", "unknown")
            st.error(f"Access denied. Required: {', '.join(required_types)}. Current: {current_type}")
            st.stop()
        
        return True


# ========================================================================
# FUNCIONES DE CONVENIENCIA (compatibilidad con código existente)
# ========================================================================

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
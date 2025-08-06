# common/notification_system.py
"""
Sistema centralizado de notificaciones para toda la aplicación.
Proporciona una interfaz unificada para manejar toasts, alertas y notificaciones
de manera consistente y reutilizable.
"""

import time
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class NotificationType(Enum):
    """Tipos de notificaciones disponibles."""

    SUCCESS = "success"
    ERROR = "danger"
    WARNING = "warning"
    INFO = "info"


class NotificationDuration(Enum):
    """Duraciones predefinidas para notificaciones."""

    SHORT = 3000  # 3 segundos
    MEDIUM = 5000  # 5 segundos (por defecto)
    LONG = 8000  # 8 segundos
    PERMANENT = 0  # No se oculta automáticamente


class NotificationManager:
    """
    Gestor centralizado de notificaciones.
    Maneja la creación, configuración y estado de notificaciones
    de manera consistente en toda la aplicación.
    """

    # Configuración por defecto
    DEFAULT_DURATION = NotificationDuration.MEDIUM.value
    DEFAULT_DISMISSABLE = True

    # Iconos Bootstrap por tipo de notificación
    ICONS = {
        NotificationType.SUCCESS: "bi-check-circle-fill",
        NotificationType.ERROR: "bi-x-circle-fill",
        NotificationType.WARNING: "bi-exclamation-triangle-fill",
        NotificationType.INFO: "bi-info-circle-fill",
    }

    @classmethod
    def create_notification(
        cls,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        duration: int = None,
        dismissable: bool = None,
        include_icon: bool = True,
    ) -> Dict[str, Any]:
        """
        Crea una notificación con la configuración especificada.

        Args:
            message: Mensaje a mostrar
            notification_type: Tipo de notificación (success, error, warning, info)
            duration: Duración en ms (None usa el default)
            dismissable: Si se puede cerrar manualmente
            include_icon: Si incluir icono al inicio del mensaje

        Returns:
            Dict con datos de la notificación listos para el store
        """
        if duration is None:
            duration = cls.DEFAULT_DURATION
        if dismissable is None:
            dismissable = cls.DEFAULT_DISMISSABLE

        # Agregar icono si está habilitado
        final_message = message
        if include_icon and notification_type in cls.ICONS:
            final_message = f"{cls.ICONS[notification_type]} {message}"

        return {
            "message": final_message,
            "type": notification_type.value,
            "duration": duration,
            "dismissable": dismissable,
            "timestamp": time.time(),  # Para debugging y tracking
            "show": True,
        }

    @classmethod
    def success(cls, message: str, duration: int = None) -> Dict[str, Any]:
        """Crea notificación de éxito."""
        return cls.create_notification(message, NotificationType.SUCCESS, duration)

    @classmethod
    def error(cls, message: str, duration: int = None) -> Dict[str, Any]:
        """Crea notificación de error."""
        return cls.create_notification(
            message,
            NotificationType.ERROR,
            duration or NotificationDuration.LONG.value,  # Errores duran más
        )

    @classmethod
    def warning(cls, message: str, duration: int = None) -> Dict[str, Any]:
        """Crea notificación de advertencia."""
        return cls.create_notification(message, NotificationType.WARNING, duration)

    @classmethod
    def info(cls, message: str, duration: int = None) -> Dict[str, Any]:
        """Crea notificación informativa."""
        return cls.create_notification(message, NotificationType.INFO, duration)

    @classmethod
    def hide_notification(cls) -> Dict[str, Any]:
        """
        Crea datos para ocultar notificación.

        Returns:
            Dict que indica que la notificación debe ocultarse
        """
        return {
            "show": False,
            "message": "",
            "type": "info",
            "duration": 0,
            "dismissable": True,
            "timestamp": time.time(),
        }


class NotificationHelper:
    """
    Helper con métodos de conveniencia para crear notificaciones
    específicas del contexto de la aplicación.
    """

    @staticmethod
    def user_created(username: str) -> Dict[str, Any]:
        """Notificación para usuario creado exitosamente."""
        return NotificationManager.success(f"Usuario '{username}' creado exitosamente")

    @staticmethod
    def user_updated(username: str) -> Dict[str, Any]:
        """Notificación para usuario actualizado exitosamente."""
        return NotificationManager.success(
            f"Usuario '{username}' actualizado exitosamente"
        )

    @staticmethod
    def user_deleted(username: str) -> Dict[str, Any]:
        """Notificación para usuario eliminado exitosamente."""
        return NotificationManager.success(
            f"Usuario '{username}' eliminado exitosamente"
        )

    @staticmethod
    def user_status_changed(username: str, new_status: str) -> Dict[str, Any]:
        """Notificación para cambio de estado de usuario."""
        return NotificationManager.success(f"Usuario '{username}' {new_status.lower()}")

    @staticmethod
    def session_created(coach: str, player: str) -> Dict[str, Any]:
        """Notificación para sesión creada exitosamente."""
        return NotificationManager.success(f"Sesión creada: {coach} × {player}")

    @staticmethod
    def session_updated(session_id: str) -> Dict[str, Any]:
        """Notificación para sesión actualizada exitosamente."""
        return NotificationManager.success(
            f"Sesión #{session_id} actualizada exitosamente"
        )

    @staticmethod
    def session_deleted(session_id: str) -> Dict[str, Any]:
        """Notificación para sesión eliminada exitosamente."""
        return NotificationManager.success(
            f"Sesión #{session_id} eliminada exitosamente"
        )

    @staticmethod
    def operation_error(operation: str, error_msg: str = None) -> Dict[str, Any]:
        """Notificación genérica de error en operación."""
        message = f"Error en {operation}"
        if error_msg:
            message += f": {error_msg}"
        return NotificationManager.error(message)

    @staticmethod
    def validation_error(field: str, error_msg: str) -> Dict[str, Any]:
        """Notificación de error de validación."""
        return NotificationManager.error(f"Error en {field}: {error_msg}")

    @staticmethod
    def export_success(filename: str) -> Dict[str, Any]:
        """Notificación para exportación exitosa."""
        return NotificationManager.success(
            f"Archivo '{filename}' exportado exitosamente"
        )

    @staticmethod
    def sync_completed(items_count: int) -> Dict[str, Any]:
        """Notificación para sincronización completada."""
        return NotificationManager.success(
            f"Sincronización completada: {items_count} elementos procesados"
        )

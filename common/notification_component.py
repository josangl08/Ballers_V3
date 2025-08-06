# common/notification_component.py
"""
Componentes Dash reutilizables para el sistema de notificaciones.
Proporciona componentes pre-configurados que pueden usarse en cualquier página.
"""

from dash import dcc, html
import dash_bootstrap_components as dbc
from typing import Dict, Any, List


class NotificationComponent:
    """
    Componente reutilizable para sistema de notificaciones.
    Genera todos los elementos necesarios para una página específica.
    """
    
    @staticmethod
    def create_notification_system(page_id: str) -> List[Any]:
        """
        Crea el sistema completo de notificaciones para una página.
        
        Args:
            page_id: Identificador único de la página (ej: "settings", "admin", "ballers")
            
        Returns:
            Lista de componentes Dash listos para agregar a la página
        """
        store_id = f"{page_id}-notification-store"
        alert_id = f"{page_id}-alert"
        timer_id = f"{page_id}-alert-timer"
        
        return [
            # Store para manejar estado de notificaciones
            dcc.Store(
                id=store_id,
                data=None,
                storage_type="memory"  # Solo en memoria, no persistir
            ),
            
            # Alert component para mostrar notificaciones
            dbc.Alert(
                id=alert_id,
                is_open=False,
                dismissable=True,
                className="notification-alert",  # Las clases de animación se manejan dinámicamente
                style={
                    "position": "fixed",
                    "top": "20px",
                    "right": "20px",
                    "z-index": "9999",
                    "min-width": "300px",
                    "max-width": "500px",
                    "display": "none"  # Inicialmente oculto
                }
            ),
            
            # Timer para auto-hide
            dcc.Interval(
                id=timer_id,
                interval=100,  # Check cada 100ms para responsividad
                n_intervals=0,
                disabled=True,  # Disabled por defecto
                max_intervals=50  # 100ms x 50 = 5000ms = 5 segundos
            )
        ]
    
    @staticmethod
    def get_component_ids(page_id: str) -> Dict[str, str]:
        """
        Obtiene los IDs de los componentes para una página.
        Útil para callbacks que necesitan referenciar los componentes.
        
        Args:
            page_id: Identificador de la página
            
        Returns:
            Dict con los IDs de store, alert y timer
        """
        return {
            "store": f"{page_id}-notification-store",
            "alert": f"{page_id}-alert", 
            "timer": f"{page_id}-alert-timer"
        }
    
    @staticmethod
    def create_toast_notification(page_id: str) -> List[Any]:
        """
        Crea un sistema de notificaciones estilo toast (más moderno).
        Alternativa al alert tradicional.
        
        Args:
            page_id: Identificador único de la página
            
        Returns:
            Lista de componentes para sistema toast
        """
        store_id = f"{page_id}-notification-store"
        toast_id = f"{page_id}-toast"
        timer_id = f"{page_id}-toast-timer"
        
        return [
            # Store para estado
            dcc.Store(
                id=store_id,
                data=None,
                storage_type="memory"
            ),
            
            # Toast container
            html.Div(
                id=f"{page_id}-toast-container",
                children=[
                    dbc.Toast(
                        id=toast_id,
                        header="Notificación",
                        is_open=False,
                        dismissable=True,
                        duration=5000,  # Auto-hide después de 5s
                        style={
                            "position": "fixed",
                            "top": "20px",
                            "right": "20px",
                            "z-index": "9999",
                            "min-width": "350px"
                        }
                    )
                ]
            ),
            
            # Timer para control adicional si se necesita
            dcc.Interval(
                id=timer_id,
                interval=100,
                n_intervals=0,
                disabled=True,
                max_intervals=50  # 100ms x 50 = 5000ms = 5 segundos
            )
        ]


class NotificationStyles:
    """
    Estilos CSS y configuraciones de estilo para notificaciones.
    Centraliza todos los estilos relacionados con notificaciones.
    """
    
    # Estilos base para alerts
    ALERT_BASE_STYLE = {
        "position": "fixed",
        "top": "20px", 
        "right": "20px",
        "z-index": "9999",
        "min-width": "300px",
        "max-width": "500px",
        "border-radius": "8px",
        "box-shadow": "0 4px 12px rgba(0,0,0,0.15)",
        "animation": "slideInRight 0.3s ease-out"
    }
    
    # Estilos por tipo de notificación
    TYPE_STYLES = {
        "success": {
            **ALERT_BASE_STYLE,
            "border-left": "4px solid #28a745",
            "background-color": "rgba(40, 167, 69, 0.1)"
        },
        "danger": {
            **ALERT_BASE_STYLE,
            "border-left": "4px solid #dc3545", 
            "background-color": "rgba(220, 53, 69, 0.1)"
        },
        "warning": {
            **ALERT_BASE_STYLE,
            "border-left": "4px solid #ffc107",
            "background-color": "rgba(255, 193, 7, 0.1)"
        },
        "info": {
            **ALERT_BASE_STYLE,
            "border-left": "4px solid #17a2b8",
            "background-color": "rgba(23, 162, 184, 0.1)"
        }
    }
    
    # CSS para animaciones (para agregar al archivo style.css si se necesita)
    ANIMATION_CSS = """
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .notification-alert {
        animation: slideInRight 0.3s ease-out;
    }
    
    .notification-alert.hiding {
        animation: slideOutRight 0.3s ease-in;
    }
    """
    
    @classmethod
    def get_style_for_type(cls, notification_type: str) -> Dict[str, Any]:
        """
        Obtiene el estilo CSS para un tipo específico de notificación.
        
        Args:
            notification_type: success, danger, warning, info
            
        Returns:
            Dict con estilos CSS aplicables
        """
        return cls.TYPE_STYLES.get(notification_type, cls.TYPE_STYLES["info"])


class NotificationConfig:
    """
    Configuración global del sistema de notificaciones.
    Permite personalizar comportamientos por página o globalmente.
    """
    
    # Configuración por defecto
    DEFAULT_CONFIG = {
        "position": "top-right",
        "auto_hide": True,
        "default_duration": 5000,
        "max_notifications": 3,  # Máximo de notificaciones simultáneas
        "show_icons": True,
        "dismissable": True,
        "animation": True
    }
    
    # Configuraciones específicas por página (si se necesita)
    PAGE_CONFIGS = {
        "settings": {
            **DEFAULT_CONFIG,
            "default_duration": 5000  # Settings usa 5 segundos
        },
        "admin": {
            **DEFAULT_CONFIG, 
            "default_duration": 4000  # Admin puede usar 4 segundos
        },
        "ballers": {
            **DEFAULT_CONFIG,
            "default_duration": 3000  # Ballers más rápido
        }
    }
    
    @classmethod
    def get_config(cls, page_id: str = None) -> Dict[str, Any]:
        """
        Obtiene la configuración para una página específica.
        
        Args:
            page_id: ID de la página (opcional)
            
        Returns:
            Dict con configuración aplicable
        """
        if page_id and page_id in cls.PAGE_CONFIGS:
            return cls.PAGE_CONFIGS[page_id]
        return cls.DEFAULT_CONFIG
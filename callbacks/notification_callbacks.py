# callbacks/notification_callbacks.py
"""
Callbacks universales para el sistema de notificaciones.
Proporciona callbacks reutilizables que pueden registrarse en cualquier página.
"""

import time
from typing import Any, Dict, Optional

from dash import Input, Output, no_update

from common.notification_component import NotificationComponent, NotificationStyles
from common.notification_system import NotificationManager


class NotificationCallbacks:
    """
    Clase para registrar callbacks universales de notificaciones.
    Maneja toda la lógica de mostrar/ocultar notificaciones de manera centralizada.
    """

    @staticmethod
    def register_notification_callbacks(app, page_id: str):
        """
        Registra todos los callbacks necesarios para notificaciones en una página.

        Args:
            app: Instancia de la aplicación Dash
            page_id: Identificador único de la página
        """
        component_ids = NotificationComponent.get_component_ids(page_id)

        # Callback principal para mostrar notificaciones
        NotificationCallbacks._register_main_callback(app, component_ids)

        # Callback para auto-hide con timer
        NotificationCallbacks._register_timer_callback(app, component_ids)

    @staticmethod
    def _register_main_callback(app, component_ids: Dict[str, str]):
        """
        Registra el callback principal que maneja mostrar/ocultar notificaciones.

        Args:
            app: Aplicación Dash
            component_ids: Dict con IDs de componentes
        """

        @app.callback(
            [
                Output(component_ids["alert"], "children"),
                Output(component_ids["alert"], "is_open"),
                Output(component_ids["alert"], "color"),
                Output(component_ids["alert"], "style"),
                Output(component_ids["timer"], "disabled"),
                Output(component_ids["timer"], "n_intervals"),
            ],
            [Input(component_ids["store"], "data")],
            prevent_initial_call=True,
        )
        def handle_notification(notification_data):
            """
            Maneja la visualización de notificaciones basado en datos del store.

            Args:
                notification_data: Datos de notificación del store

            Returns:
                Tuple con valores para actualizar componentes de notificación
            """
            # DEBUG: Logging temporal para verificar funcionamiento
            print(f"🔔 NOTIFICATION DEBUG: Received data: {notification_data}")
            if not notification_data:
                # No hay notificación, ocultar todo
                print("🔔 NOTIFICATION DEBUG: No data, hiding notification")
                return (
                    "",  # children
                    False,  # is_open
                    "info",  # color
                    {"display": "none"},  # style
                    True,  # timer disabled
                    0,  # reset timer
                )

            if not notification_data.get("show", False):
                # Notificación marcada para ocultar
                return ("", False, "info", {"display": "none"}, True, 0)

            # Mostrar notificación
            message = notification_data.get("message", "")
            notification_type = notification_data.get("type", "info")
            duration = notification_data.get("duration", 5000)
            # dismissable = notification_data.get("dismissable", True)  # Not used

            print(
                f"🔔 NOTIFICATION DEBUG: Showing notification - "
                f"Type: {notification_type}, Message: {message}"
            )

            # Crear contenido HTML estructurado con iconos Bootstrap
            from dash import html

            # Mapear tipos a colores temáticos (texto del mismo color que iconos)
            type_configs = {
                "success": {
                    "icon_color": "#28a745",
                    "text_color": "#28a745",  # Verde como el icono
                    "icon_class": "bi-check-circle-fill",
                },
                "danger": {
                    "icon_color": "#dc3545",
                    "text_color": "#dc3545",  # Rojo como el icono
                    "icon_class": "bi-x-circle-fill",
                },
                "warning": {
                    "icon_color": "#ffc107",
                    "text_color": "#ffc107",  # Amarillo como el icono
                    "icon_class": "bi-exclamation-triangle-fill",
                },
                "info": {
                    "icon_color": "#17a2b8",
                    "text_color": "#17a2b8",  # Azul como el icono
                    "icon_class": "bi-info-circle-fill",
                },
            }

            config = type_configs.get(notification_type, type_configs["info"])

            # Limpiar mensaje de iconos anteriores si los tiene
            clean_message = message
            emoji_patterns = ["✅", "❌", "⚠️", "ℹ️"]
            for emoji in emoji_patterns:
                clean_message = clean_message.replace(emoji, "").strip()

            # Crear HTML estructurado con espacio para botón cerrar
            notification_content = html.Div(
                [
                    # Icono de tipo
                    html.I(
                        className=f"bi {config['icon_class']}",
                        style={
                            "color": config["icon_color"],
                            "font-size": "1.2rem",
                            "margin-right": "12px",
                            "flex-shrink": "0",
                        },
                    ),
                    # Mensaje
                    html.Span(
                        clean_message,
                        style={
                            "flex": "1",
                            "color": config["text_color"],
                            "font-weight": "500",
                            "line-height": "1.4",
                            "padding-right": "8px",  # Espacio para botón cerrar
                        },
                    ),
                    # Espacio para botón cerrar (Bootstrap lo maneja automáticamente)
                    html.Div(style={"width": "20px", "flex-shrink": "0"}),
                ],
                style={
                    "display": "flex",
                    "align-items": "center",
                    "width": "100%",
                    "justify-content": "space-between",
                },
            )

            # Obtener estilo apropiado para el tipo
            style = NotificationStyles.get_style_for_type(notification_type)
            style["display"] = "block"  # Asegurar que se muestre
            style["background-color"] = "rgba(33,33,33,0.98)"  # Más opaco y más oscuro

            # Configurar timer si hay duración
            timer_disabled = duration <= 0  # Timer disabled si es permanente

            return (
                notification_content,  # children (HTML estructurado)
                True,  # is_open
                notification_type,  # color
                style,  # style
                timer_disabled,  # timer disabled
                0,  # reset timer intervals
            )

    @staticmethod
    def _register_timer_callback(app, component_ids: Dict[str, str]):
        """
        Registra el callback del timer para auto-hide.

        Args:
            app: Aplicación Dash
            component_ids: Dict con IDs de componentes
        """

        @app.callback(
            [
                Output(component_ids["store"], "data", allow_duplicate=True),
            ],
            [
                Input(component_ids["timer"], "n_intervals"),
                Input(component_ids["alert"], "is_open"),
            ],
            prevent_initial_call=True,
        )
        def auto_hide_notification(n_intervals, is_open):
            """
            Oculta automáticamente la notificación después del tiempo especificado.

            Args:
                n_intervals: Número de intervalos del timer
                is_open: Si la alerta está abierta

            Returns:
                Datos para ocultar la notificación
            """
            if n_intervals >= 50 and is_open:
                # Timer completó 50 intervalos (5000ms), ocultar notificación
                return [NotificationManager.hide_notification()]

            return [no_update]


class NotificationHelperCallbacks:
    """
    Helpers adicionales para callbacks específicos de notificaciones.
    Proporcionan funciones utilitarias para casos de uso comunes.
    """

    @staticmethod
    def create_notification_trigger(
        app, trigger_id: str, store_id: str, notification_func: callable
    ):
        """
        Crea un callback que dispara una notificación específica.
        Útil para acciones simples que siempre muestran la misma notificación.

        Args:
            app: Aplicación Dash
            trigger_id: ID del componente que dispara la notificación
            store_id: ID del store de notificaciones
            notification_func: Función que retorna datos de notificación
        """

        @app.callback(
            Output(store_id, "data", allow_duplicate=True),
            Input(trigger_id, "n_clicks"),
            prevent_initial_call=True,
        )
        def trigger_notification(n_clicks):
            if n_clicks and n_clicks > 0:
                return notification_func()
            return no_update

    @staticmethod
    def create_success_callback(app, trigger_id: str, store_id: str, message: str):
        """
        Callback pre-configurado para mostrar mensaje de éxito.

        Args:
            app: Aplicación Dash
            trigger_id: ID del trigger
            store_id: ID del store
            message: Mensaje de éxito a mostrar
        """
        NotificationHelperCallbacks.create_notification_trigger(
            app, trigger_id, store_id, lambda: NotificationManager.success(message)
        )

    @staticmethod
    def create_error_callback(app, trigger_id: str, store_id: str, message: str):
        """
        Callback pre-configurado para mostrar mensaje de error.

        Args:
            app: Aplicación Dash
            trigger_id: ID del trigger
            store_id: ID del store
            message: Mensaje de error a mostrar
        """
        NotificationHelperCallbacks.create_notification_trigger(
            app, trigger_id, store_id, lambda: NotificationManager.error(message)
        )


class NotificationValidator:
    """
    Validador para datos de notificaciones.
    Asegura que los datos estén en el formato correcto.
    """

    @staticmethod
    def validate_notification_data(data: Any) -> bool:
        """
        Valida que los datos de notificación estén en formato correcto.

        Args:
            data: Datos a validar

        Returns:
            True si los datos son válidos
        """
        if not isinstance(data, dict):
            return False

        required_fields = ["message", "type", "show"]
        return all(field in data for field in required_fields)

    @staticmethod
    def sanitize_notification_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitiza y normaliza datos de notificación.

        Args:
            data: Datos de notificación

        Returns:
            Datos sanitizados
        """
        if not NotificationValidator.validate_notification_data(data):
            return NotificationManager.hide_notification()

        # Asegurar valores por defecto
        sanitized = {
            "message": str(data.get("message", "")),
            "type": data.get("type", "info"),
            "duration": int(data.get("duration", 5000)),
            "dismissable": bool(data.get("dismissable", True)),
            "show": bool(data.get("show", False)),
            "timestamp": data.get("timestamp", time.time()),
        }

        # Validar tipo de notificación
        valid_types = ["success", "danger", "warning", "info"]
        if sanitized["type"] not in valid_types:
            sanitized["type"] = "info"

        # Validar duración
        if sanitized["duration"] < 0:
            sanitized["duration"] = 5000

        return sanitized


class NotificationQueue:
    """
    Sistema de cola para múltiples notificaciones (funcionalidad avanzada).
    Permite encolar notificaciones y mostrarlas secuencialmente.
    """

    _queues = {}  # Dict para mantener colas por página

    @classmethod
    def add_to_queue(cls, page_id: str, notification_data: Dict[str, Any]):
        """
        Agrega una notificación a la cola de una página.

        Args:
            page_id: ID de la página
            notification_data: Datos de la notificación
        """
        if page_id not in cls._queues:
            cls._queues[page_id] = []

        validated_data = NotificationValidator.sanitize_notification_data(
            notification_data
        )
        cls._queues[page_id].append(validated_data)

    @classmethod
    def get_next_notification(cls, page_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene la siguiente notificación en cola para una página.

        Args:
            page_id: ID de la página

        Returns:
            Datos de la siguiente notificación o None si no hay
        """
        if page_id not in cls._queues or not cls._queues[page_id]:
            return None

        return cls._queues[page_id].pop(0)

    @classmethod
    def clear_queue(cls, page_id: str):
        """
        Limpia la cola de notificaciones de una página.

        Args:
            page_id: ID de la página
        """
        if page_id in cls._queues:
            cls._queues[page_id] = []

    @classmethod
    def queue_size(cls, page_id: str) -> int:
        """
        Obtiene el tamaño de la cola para una página.

        Args:
            page_id: ID de la página

        Returns:
            Número de notificaciones en cola
        """
        if page_id not in cls._queues:
            return 0
        return len(cls._queues[page_id])

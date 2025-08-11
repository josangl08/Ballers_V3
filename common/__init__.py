"""
Common Module - Utilidades compartidas para toda la aplicación Ballers.

Este módulo contiene componentes reutilizables organizados por categoría:
- UI Components: Componentes de interfaz de usuario
- System Utils: Utilidades de sistema y formateo

Para evitar imports circulares, este módulo no importa automáticamente.
Usar imports específicos según necesidad:

    from common.utils import format_currency
    from common.format_utils import format_date
"""

# NO imports automáticos para evitar circularidad
# Los imports se deben hacer explícitamente donde se necesiten

__all__ = [
    # Módulos disponibles para import explícito
    "login_dash",
    "menu_dash",
    "notification_component",
    "upload_component",
    "utils",
    "format_utils",
    "datepicker_utils",
    "logging_config",
    "notification_system",
]

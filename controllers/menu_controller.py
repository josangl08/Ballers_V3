# controllers/menu_controller.py
"""
Controlador para manejo del menú lateral y navegación.
Separa la lógica del menú de la presentación UI.
"""
from typing import Dict, List, Optional

from .sync_coordinator import get_sync_stats_unified, is_auto_sync_running

# Eliminado import de streamlit - completamente migrado a Dash


class MenuController:
    """
    Controlador para el menú lateral - maneja configuración, estado y navegación.
    """

    # Configuración estática de menús por tipo de usuario
    MENU_CONFIG = {
        "player": {"options": ["Ballers"], "icons": ["person-badge"]},
        "coach": {
            "options": ["Ballers", "Administration"],
            "icons": ["people-fill", "calendar-week"],
        },
        "admin": {
            "options": ["Ballers", "Administration", "Settings"],
            "icons": ["people-fill", "calendar-week", "gear"],
        },
    }

    # Mapeo de rutas de contenido
    CONTENT_ROUTES = {
        "Ballers": "pages.ballers",
        "Administration": "pages.administration",
        "Settings": "pages.settings",
    }

    def __init__(self, session_data: Optional[Dict] = None):
        """
        Inicializa el controller con datos de sesión.
        TEMPORAL: Acepta session_data como parámetro para compatibilidad con Dash.
        """
        if session_data:
            self.user_id = session_data.get("user_id")
            self.user_type = session_data.get("user_type", "player")
            self.user_name = session_data.get("name", "")
        else:
            # Fallback temporal para admin si no hay session_data
            self.user_id = 1
            self.user_type = "admin"
            self.user_name = "Admin User"

    # Configuración del menú

    def is_user_logged_in(self) -> bool:
        """Verifica si hay un usuario logueado."""
        return bool(self.user_id)

    def get_menu_config(self) -> Dict[str, List[str]]:
        """
        Obtiene configuración de menú para el tipo de usuario actual.

        Returns:
            Dict con 'options' e 'icons' para el menú
        """
        return self.MENU_CONFIG.get(self.user_type, self.MENU_CONFIG["player"])

    def get_menu_title(self) -> str:
        """Genera título del menú con nombre y tipo de usuario."""
        return f" {self.user_name}    |    🔑 {self.user_type.capitalize()}"

    def get_content_route(self, section: str) -> Optional[str]:
        """
        Obtiene la ruta del módulo para una sección del menú.

        Args:
            section: Sección seleccionada (ej: "Ballers", "Settings")

        Returns:
            Ruta del módulo o None si no existe
        """
        return self.CONTENT_ROUTES.get(section)

    # Estado de sincronización

    def should_show_sync_area(self) -> bool:
        """Determina si mostrar el área de auto-sync según el tipo de usuario."""
        return self.user_type in ["admin", "coach"]

    def get_sync_display_data(self) -> Optional[Dict]:
        """
        Obtiene datos de sincronización para mostrar en UI.

        Returns:
            Dict con stats de sync o None si no hay datos
        """
        if not self.should_show_sync_area():
            return None

        # Pasar session_data que tiene el MenuController
        session_data = {
            "user_id": self.user_id,
            "user_type": self.user_type,
            "name": self.user_name,
        }
        return get_sync_stats_unified(session_data)

    def get_auto_sync_status_display(self) -> Dict[str, str]:
        """
        Obtiene estado del auto-sync para mostrar en UI.

        Returns:
            Dict con 'status' y 'icon' para mostrar
        """
        if is_auto_sync_running():
            return {"status": "🔄 Auto-Sync: ✅", "type": "success"}
        else:
            return {"status": "🔄 Auto-Sync: ⏸️", "type": "info"}

    # Navegación y redirecciones

    def handle_forced_navigation(
        self, session_data: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Maneja navegación forzada desde otros componentes - MIGRADO A DASH.

        Args:
            session_data: Datos de sesión de Dash para verificar navegación forzada

        Returns:
            Sección forzada o None si no hay redirección
        """
        # En Dash, la navegación forzada se maneja vía callbacks y no session state
        # Esta funcionalidad se implementa directamente en los callbacks de navegación
        return None

    def create_sync_details_redirect(self, target_section: str) -> Dict[str, str]:
        """
        Crea datos para redirección a detalles de sync - MIGRADO A DASH.

        Args:
            target_section: Sección destino ("Settings" o "Administration")

        Returns:
            Dict con datos de redirección para usar en callbacks de Dash
        """
        return {
            "show_sync_details": True,
            "target_section": target_section,
            "redirect_reason": "sync_details_requested",
        }

    # Limpieza y logout

    def prepare_logout_cleanup(self) -> None:
        """
        Prepara limpieza de datos antes del logout.
        Limpia datos temporales (auto-sync stats removed with webhook migration).
        """
        try:
            # Auto-sync stats cleanup removed - migrated to webhook-based sync
            print("🔄 Logout cleanup completed (auto-sync stats deprecated)")
        except Exception as e:
            print(f"Warning: Could not complete logout cleanup: {e}")

    # Validaciones y permisos

    def can_access_section(self, section: str) -> bool:
        """
        Verifica si el usuario actual puede acceder a una sección.

        Args:
            section: Sección a verificar

        Returns:
            True si puede acceder
        """
        menu_config = self.get_menu_config()
        return section in menu_config["options"]

    def get_accessible_sections(self) -> List[str]:
        """Obtiene lista de secciones accesibles para el usuario actual."""
        menu_config = self.get_menu_config()
        return menu_config["options"]


def get_menu_controller(session_data: Optional[Dict] = None) -> MenuController:
    """
    Factory function para obtener instancia del MenuController.
    Útil para mantener compatibilidad con código existente - MIGRADO A DASH.

    Args:
        session_data: Datos de sesión de Dash
    """
    return MenuController(session_data)


def get_user_menu_config(session_data: Optional[Dict] = None) -> Dict[str, List[str]]:
    """Función de conveniencia para obtener configuración de menú - MIGRADO A DASH."""
    controller = get_menu_controller(session_data)
    return controller.get_menu_config()


def can_user_access_section(section: str, session_data: Optional[Dict] = None) -> bool:
    """Función de conveniencia para verificar acceso a sección - MIGRADO A DASH."""
    controller = get_menu_controller(session_data)
    return controller.can_access_section(section)


def get_content_path(
    section: str, session_data: Optional[Dict] = None
) -> Optional[str]:
    """
    Función de conveniencia para obtener ruta de contenido - MIGRADO A DASH.
    Mantiene compatibilidad con main.py existente.
    """
    controller = get_menu_controller(session_data)
    return controller.get_content_route(section)


def should_show_sync_area(session_data: Optional[Dict] = None) -> bool:
    """Función de conveniencia para verificar si mostrar área de sync - DASH."""
    controller = get_menu_controller(session_data)
    return controller.should_show_sync_area()


# Utilidades para sync status


def get_sync_status_for_ui(session_data: Optional[Dict] = None) -> Optional[Dict]:
    """
    Obtiene estado de sincronización formateado para UI - MIGRADO A DASH.
    Combina datos de sync stats y auto-sync status.
    """
    controller = get_menu_controller(session_data)

    if not controller.should_show_sync_area():
        return None

    # Obtener datos de sync stats
    sync_stats = controller.get_sync_display_data()
    auto_sync_status = controller.get_auto_sync_status_display()

    return {
        "sync_stats": sync_stats,
        "auto_sync_status": auto_sync_status,
        "show_sync_area": True,
    }


def handle_sync_details_redirect(session_data: Optional[Dict] = None) -> Optional[Dict]:
    """
    Maneja redirección a detalles de sync según tipo de usuario - MIGRADO A DASH.
    Centraliza la lógica de redirección.

    Args:
        session_data: Datos de sesión de Dash

    Returns:
        Dict con datos de redirección o None si no aplica
    """
    controller = MenuController(session_data)

    if controller.user_type == "admin":
        return controller.create_sync_details_redirect("Settings")
    elif controller.user_type == "coach":
        return controller.create_sync_details_redirect("Administration")

    return None

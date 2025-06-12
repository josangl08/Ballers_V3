# controllers/menu_controller.py
"""
Controlador para manejo del menú lateral y navegación.
Separa la lógica del menú de la presentación UI.
"""
import streamlit as st
from typing import Dict, List, Optional
from .sync_coordinator import get_sync_stats_unified, is_auto_sync_running, _auto_sync

class MenuController:
    """
    Controlador para el menú lateral - maneja configuración, estado y navegación.
    """
    
    # Configuración estática de menús por tipo de usuario
    MENU_CONFIG = {
        "player": {
            "options": ["Ballers"],
            "icons": ["person-badge"]
        },
        "coach": {
            "options": ["Ballers", "Administration"],
            "icons": ["people-fill", "calendar-week"]
        },
        "admin": {
            "options": ["Ballers", "Administration", "Settings"],
            "icons": ["people-fill", "calendar-week", "gear"]
        }
    }
    
    # Mapeo de rutas de contenido
    CONTENT_ROUTES = {
        "Ballers": "pages.ballers",
        "Administration": "pages.administration",
        "Settings": "pages.settings"
    }

    def __init__(self):
        """Inicializa el controller con datos de sesión actual."""
        self.user_id = st.session_state.get("user_id")
        self.user_type = st.session_state.get("user_type", "player")
        self.user_name = st.session_state.get("name", "")
    
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
        
        return get_sync_stats_unified()
    
    def get_auto_sync_status_display(self) -> Dict[str, str]:
        """
        Obtiene estado del auto-sync para mostrar en UI.
        
        Returns:
            Dict con 'status' y 'icon' para mostrar
        """
        if is_auto_sync_running():
            return {
                "status": "🔄 Auto-Sync: ✅",
                "type": "success"
            }
        else:
            return {
                "status": "🔄 Auto-Sync: ⏸️", 
                "type": "info"
            }
    
    # Navegación y redirecciones
    
    def handle_forced_navigation(self) -> Optional[str]:
        """
        Maneja navegación forzada desde otros componentes.
        
        Returns:
            Sección forzada o None si no hay redirección
        """
        if "force_section" in st.session_state:
            forced_section = st.session_state["force_section"]
            del st.session_state["force_section"]  # Limpiar inmediatamente
            return forced_section
        return None
    
    def create_sync_details_redirect(self, target_section: str) -> None:
        """
        Crea redirección para ver detalles de sync.
        
        Args:
            target_section: Sección destino ("Settings" o "Administration")
        """
        st.session_state["show_sync_details"] = True
        st.session_state["force_section"] = target_section
    
    # Limpieza y logout
    
    def prepare_logout_cleanup(self) -> None:
        """
        Prepara limpieza de datos antes del logout.
        Limpia estadísticas de auto-sync y otros datos temporales.
        """
        try:
            # Limpiar estadísticas del auto-sync
            
            _auto_sync.stats.last_sync_time = None
            _auto_sync.stats.last_sync_duration = 0
            _auto_sync.stats.last_changes = None
            _auto_sync.stats.last_changes_time = None
            _auto_sync.stats.changes_notified = True
            
            print("🔄 Auto-sync stats cleared on logout")
        except Exception as e:
            print(f"Warning: Could not clear auto-sync stats: {e}")
    
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


def get_menu_controller() -> MenuController:
    """
    Factory function para obtener instancia del MenuController.
    Útil para mantener compatibilidad con código existente.
    """
    return MenuController()


def get_user_menu_config() -> Dict[str, List[str]]:
    """Función de conveniencia para obtener configuración de menú."""
    controller = get_menu_controller()
    return controller.get_menu_config()


def can_user_access_section(section: str) -> bool:
    """Función de conveniencia para verificar acceso a sección."""
    controller = get_menu_controller()
    return controller.can_access_section(section)


def get_content_path(section: str) -> Optional[str]:
    """
    Función de conveniencia para obtener ruta de contenido.
    Mantiene compatibilidad con main.py existente.
    """
    controller = get_menu_controller()
    return controller.get_content_route(section)


def should_show_sync_area() -> bool:
    """Función de conveniencia para verificar si mostrar área de sync."""
    controller = get_menu_controller()
    return controller.should_show_sync_area()

# Utilidades para sync status

def get_sync_status_for_ui() -> Optional[Dict]:
    """
    Obtiene estado de sincronización formateado para UI.
    Combina datos de sync stats y auto-sync status.
    """
    controller = get_menu_controller()
    
    if not controller.should_show_sync_area():
        return None
    
    # Obtener datos de sync stats
    sync_stats = controller.get_sync_display_data()
    auto_sync_status = controller.get_auto_sync_status_display()
    
    return {
        "sync_stats": sync_stats,
        "auto_sync_status": auto_sync_status,
        "show_sync_area": True
    }


def handle_sync_details_redirect() -> None:
    """
    Maneja redirección a detalles de sync según tipo de usuario.
    Centraliza la lógica de redirección.
    """
    controller = get_menu_controller()
    
    if controller.user_type == "admin":
        controller.create_sync_details_redirect("Settings")
    elif controller.user_type == "coach":
        controller.create_sync_details_redirect("Administration")
    
    st.rerun()  # Forzar refresh inmediato
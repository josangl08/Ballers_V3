# common/menu.py
import streamlit as st
import datetime as dt
from streamlit_option_menu import option_menu
from typing import Optional

# 🆕 IMPORTAR el nuevo MenuController
from controllers.menu_controller import (
    MenuController,
    get_sync_status_for_ui,
    handle_sync_details_redirect
)
from controllers.sync_coordinator import force_manual_sync
from controllers.auth_controller import clear_user_session


def show_sync_status_message(stats: dict) -> None:
    """
    🎨 UI PURA - Muestra mensaje de sync con color apropiado.
    Versión simplificada que solo maneja presentación.
    """
    # Construir texto de estadísticas
    changes = []
    if stats['imported'] > 0:
        changes.append(f"{stats['imported']} 📥")
    if stats['updated'] > 0:
        changes.append(f"{stats['updated']} 🔄")
    if stats['deleted'] > 0:
        changes.append(f"{stats['deleted']} 🗑️")

    problems = []
    if stats['rejected'] > 0:
        problems.append(f"{stats['rejected']} 🚫")
    if stats['warnings'] > 0:
        problems.append(f"{stats['warnings']} ⚠️")

    # Construir mensaje completo
    message_parts = [f"Sync: ⏱ {stats['sync_time']:.1f}s"]

    if changes or problems:
        message_parts.append(" ● ")
        message_parts.extend(changes + problems)
    else:
        message_parts.append("● No Changes")
    
    message = " ".join(message_parts)

    # 🎨 Mostrar con color apropiado
    has_rejected = stats['rejected'] > 0
    has_warnings = stats['warnings'] > 0
    has_changes = stats['imported'] + stats['updated'] + stats['deleted'] > 0

    if has_rejected:
        st.error(message)
    elif has_warnings:
        st.warning(message)
    elif has_changes:
        st.success(message)
    else:
        st.info(message)
    
    # Botón para ver detalles si hay problemas
    if has_rejected or has_warnings:
        if st.button("🔍 See details", key="view_sync_details", use_container_width=True):
            handle_sync_details_redirect()


def show_auto_sync_area() -> None:
    """
    🎨 UI PURA - Área unificada de auto-sync usando MenuController.
    """
    # 🆕 Usar MenuController para obtener datos
    sync_data = get_sync_status_for_ui()
    
    if not sync_data or not sync_data["show_sync_area"]:
        return
    
    # Mostrar estadísticas si hay datos
    if sync_data["sync_stats"]:
        st.divider()
        show_sync_status_message(sync_data["sync_stats"])
        st.divider()
    
    # Mostrar estado de auto-sync
    auto_status = sync_data["auto_sync_status"]
    if auto_status["type"] == "success":
        st.success(auto_status["status"])
    else:
        st.info(auto_status["status"])
    
    # Quick sync button
    if st.button("⚡ Quick Sync", type="primary", use_container_width=True):
        with st.spinner("Ejecutando sync manual..."):
            result = force_manual_sync()
            
            if result['success']:
                # Guardar resultado con timestamp
                result['timestamp'] = dt.datetime.now().isoformat()
                st.session_state['last_sync_result'] = result
                st.rerun()
            else:
                st.error(f"❌ Error: {result['error']}")


def create_sidebar_menu() -> str:
    """
    🎨 UI PURA - Crea menú lateral usando MenuController para toda la lógica.
    
    Returns:
        str: La sección seleccionada del menú.
    """
    # 🆕 Crear instancia del controller
    controller = MenuController()
    
    # Verificar si hay usuario logueado
    if not controller.is_user_logged_in():
        return ""
    
    # Manejar navegación forzada
    forced_section = controller.handle_forced_navigation()
    
    # Obtener configuración del menú
    menu_config = controller.get_menu_config()
    menu_title = controller.get_menu_title()
    
    # Crear menú
    with st.sidebar:
        # Logo
        try:
            st.image("assets/ballers/isotipo_white.png", width=200)
        except:
            st.write("Logo no encontrado")
        
        # Menú principal usando configuración del controller
        selected = option_menu(
            menu_title, 
            menu_config["options"],
            icons=menu_config["icons"],
            menu_icon="person-circle",
            default_index=0,
            styles={
                "container": {"padding": "1!important","margin-top": "2!important", "background-color": "#1D1B1A"},
                "icon": {"color": "#1DDD6E", "font-size": "18px"},
                "nav": {
                    "font-size": "16px",
                    "text-align": "left",
                    "margin": "0px",
                    "transition": "all 0.3s ease",
                    "--hover-color": "#333333",
                },
                "nav-link-selected": {
                    "background-color": "#333333",
                }, 
                "menu-title": {
                    "font-size": "14px",
                    "font-weight": "bold",
                    "margin-bottom": "10px",
                    "color": "#FFFFFF",
                    "text-align": "center"
                }
            }
        )
        
        # Área de auto-sync (si corresponde)
        show_auto_sync_area()
        
        # Botón de logout
        if st.button("📤 Log Out", key="logout_button", 
            type="primary", use_container_width=True):
            
            # Preparar limpieza usando controller
            controller.prepare_logout_cleanup()
            
            # Usar controller de auth para logout limpio
            clear_user_session(show_message=True)
            st.rerun()

    # Devolver sección forzada o seleccionada
    return forced_section or selected


def get_content_path(section: str) -> Optional[str]:
    """
    🗺️ ROUTING - Función de compatibilidad que usa MenuController.
    Mantiene compatibilidad con main.py existente.
    
    Args:
        section: Sección seleccionada en el menú
        
    Returns:
        str: Ruta al módulo de contenido
    """
    controller = MenuController()
    return controller.get_content_route(section)


if __name__ == "__main__":
    # Mostrar mensaje de cierre de sesión si es necesario
    if st.session_state.get("show_logout_message"):
        st.success("You have successfully logged out")
        del st.session_state["show_logout_message"]
    
    selected = create_sidebar_menu()
    st.title(f"Sección: {selected}")
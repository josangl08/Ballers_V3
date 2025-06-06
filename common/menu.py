
import streamlit as st
import datetime as dt
from streamlit_option_menu import option_menu
from common.login import logout
from controllers.sync_coordinator import is_auto_sync_running, get_auto_sync_status, force_manual_sync, has_pending_notifications
from common.notifications import get_sync_problems

def get_last_sync_stats():
    """Lee estadísticas con manejo robusto de errores"""
    
    # 🔧 FIX: Agregar flag para evitar bucles infinitos
    if hasattr(st.session_state, '_reading_stats') and st.session_state._reading_stats:
        return None  # Evitar bucle infinito
    
    st.session_state._reading_stats = True
    
    try:
        manual_stats = None
        auto_stats = None
        
        # Fuente 1: Manual sync (session_state) - mas reciente
        if 'last_sync_result' in st.session_state:
            result = st.session_state['last_sync_result']
            timestamp = result.get('timestamp')
            
            if timestamp:
                try:
                    sync_time = dt.datetime.fromisoformat(timestamp)
                    seconds_ago = (dt.datetime.now() - sync_time).total_seconds()
                    
                    if seconds_ago < 90:  # 90 segundos
                        manual_stats = build_stats_from_manual_sync(result)

                    else:
                        # Auto-limpiar datos expirados
                        del st.session_state['last_sync_result']
                except Exception:
                    # Si hay error, limpiar
                    if 'last_sync_result' in st.session_state:
                        del st.session_state['last_sync_result']
        
        # Fuente 2: Auto-sync - con validacion
        try:
            auto_status = get_auto_sync_status()
            last_sync_time = auto_status.get('last_sync_time')
            
            # Verificar que auto-sync tenga datos válidos
            if last_sync_time and auto_status.get('last_sync_duration', 0) > 0:
                last_sync = dt.datetime.fromisoformat(last_sync_time)
                time_since_sync = (dt.datetime.now() - last_sync).total_seconds()
                
                if time_since_sync < 300:  # 5 minutos
                    auto_stats = build_stats_from_auto_sync(auto_status)
                    
                    # Validar que auto_stats tenga datos útiles
                    if auto_stats:
                        total_data = (auto_stats['imported'] + auto_stats['updated'] + 
                                    auto_stats['deleted'] + auto_stats['rejected'] + 
                                    auto_stats['warnings'])
                        
                        # Si auto-sync solo tiene duración pero no datos, ignorar
                        if total_data == 0 and not manual_stats:
                            auto_stats = None
                            
                            
        except Exception as e:
            auto_stats = None
        
        # Decidir cuál usar 
        if manual_stats and auto_stats:
            manual_total = sum([manual_stats['imported'], manual_stats['updated'], 
                manual_stats['deleted'], manual_stats['rejected'], 
                manual_stats['warnings']])
            auto_total = sum([auto_stats['imported'], auto_stats['updated'], 
                auto_stats['deleted'], auto_stats['rejected'], 
                auto_stats['warnings']])
            
            selected = manual_stats if manual_total >= auto_total else auto_stats
            return selected
        
        final_stats = manual_stats or auto_stats
        return final_stats
    
    finally:
        # flag siempre
        if '_reading_stats' in st.session_state:
            del st.session_state._reading_stats

def show_sync_status_message(stats):
    """Muestra mensaje de sync con color apropiado"""
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

    
    # Determinar color y mensaje
    has_changes = stats['imported'] + stats['updated'] + stats['deleted'] > 0
    has_warnings = stats['warnings'] > 0
    has_rejected = stats['rejected'] > 0

     # Construir mensaje completo
    message_parts = []
    message_parts.append(f"Sync: ⏱ {stats['sync_time']:.1f}s")

    if changes or problems:
        message_parts.append(" ● ")
        
        # Agregar cambios exitosos
        if changes:
            message_parts.extend(changes)
        
        # Agregar problemas al mensaje
        if problems:
            message_parts.extend(problems)
    else:
        message_parts.append("● No Changes")
    
    message = " ".join(message_parts)
    

    if has_rejected:
        # 🔴 ROJO - Prioridad máxima: hay eventos rechazados
        st.error(message)
        
    elif has_warnings:
        # 🟡 AMARILLO - Hay warnings pero no rechazados
        st.warning(message)
        
    elif has_changes:
        # 🟢 VERDE - Hay cambios exitosos sin problemas
        st.success(message)
        
    else:
        # 🔵 AZUL - Sin cambios ni problemas
        st.info(message)
    
    # Mostrar enlace a detalles solo si hay problemas
    if has_rejected or has_warnings:
        user_type = st.session_state.get("user_type")
        
        if user_type == "admin":
            if st.button("🔍 See details in Settings", key="view_sync_details", use_container_width=True):
                # Marcar que queremos ver detalles Y forzar redirección
                st.session_state["show_sync_details"] = True
                st.session_state["force_section"] = "Settings"
                st.rerun()  # Forzar refresh inmediato
                
        elif user_type == "coach":
            if st.button("🔍 See full details", key="view_sync_details", use_container_width=True):
                # Para coach: forzar ir a Administration Y mostrar detalles
                st.session_state["show_sync_details"] = True
                st.session_state["force_section"] = "Administration"
                st.rerun()  # Forzar refresh inmediato


def show_auto_sync_area():
    """Área unificada de auto-sync - elimina duplicación"""
    user_type = st.session_state.get("user_type")
    
    if user_type not in ["admin", "coach"]:
        return
    
    # Mostrar estadisticas del ultimo sync (solo si hay datos recientes)
    stats = get_last_sync_stats()
    if stats:
        st.divider()
        show_sync_status_message(stats)
        st.divider()
    
    # Auto-Sync status
    if is_auto_sync_running():
        st.success("🔄 Auto-Sync: ✅")
    else:
        st.info("🔄 Auto-Sync: ⏸️")
    
    # Quick sync
    if st.button("⚡ Quick Sync", type="primary", use_container_width=True):
        with st.spinner("Ejecutando sync manual..."):
            result = force_manual_sync()
            
            if result['success']:
                # Guardar resultado con timestamp para que dure 1 minuto
                result['timestamp'] = dt.datetime.now().isoformat()
                st.session_state['last_sync_result'] = result
                st.rerun()  # Refrescar para mostrar el mensaje
            else:
                st.error(f"❌ Error: {result['error']}")
            
def create_sidebar_menu():
    """
    Crea un menú lateral personalizado según el tipo de usuario.
    Returns:
        str: La sección seleccionada del menú.
    """
    # Verificar si hay usuario en sesión
    if "user_id" not in st.session_state:
        return None
    
    # Obtener el tipo de usuario de la sesión
    user_type: str = st.session_state.get("user_type", "player")
    user_name = st.session_state.get("name", "")
    
    # Definir opciones de menú según el tipo de usuario
    menu_options = {
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
    
    # Obtener configuración de menú para el tipo de usuario actual
    current_menu = menu_options.get(user_type) or menu_options["player"]
    
    # Crear menú
    with st.sidebar:
        try:
            st.image("assets/ballers/isotipo_white.png", width=200)
        except:
            st.write("Logo no encontrado")
        
        # Crear string personalizado para el título del menú con iconos
        menu_title = f" {user_name}    |    🔑 {user_type.capitalize()}"
        
        # Menú de opciones con título personalizado
        selected = option_menu(
            menu_title, 
            current_menu["options"],
            icons=current_menu["icons"],
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
        
        # Auto-Sync
        show_auto_sync_area()
        
        # Botón de cerrar sesión
        if st.button("📤 Log Out", key="logout_button", 
                type="primary", use_container_width=True):
            
            # 🎯 RESET AUTO-SYNC stats antes de logout
            try:
                from controllers.sync import _auto_sync  # Instancia global
                
                # Limpiar estadísticas del auto-sync
                _auto_sync.stats.last_sync_time = None
                _auto_sync.stats.last_sync_duration = 0
                _auto_sync.stats.last_changes = None
                _auto_sync.stats.last_changes_time = None
                _auto_sync.stats.changes_notified = True
                
                print("🔄 Auto-sync stats cleared on logout")
            except Exception as e:
                print(f"Warning: Could not clear auto-sync stats: {e}")
            
            # Limpiar session_state sync data
            sync_keys = ['last_sync_result', 'show_sync_details', 'show_details_sidebar', 'sync_problems']
            for key in sync_keys:
                if key in st.session_state:
                    del st.session_state[key]
            
            # Logout general (código existente)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            st.session_state["show_logout_message"] = True
            st.rerun()

    return selected

def get_coach_id_if_needed():
    """Obtiene coach_id si el usuario actual es coach, None en caso contrario"""
    user_type = st.session_state.get("user_type")
    if user_type != "coach":
        return None
        
    try:
        from controllers.db import get_db_session
        from models import Coach, User
        
        user_id = st.session_state.get("user_id")
        db = get_db_session()
        coach = db.query(Coach).join(User).filter(User.user_id == user_id).first()
        db.close()
        
        return coach.coach_id if coach else None
    except Exception:
        return None
    
def build_stats_from_manual_sync(result):
    """Construye stats desde manual sync con filtrado por coach"""
    # Aplicar filtrado por coach si es necesario
    coach_id = get_coach_id_if_needed()
    if coach_id:
        result = filter_sync_results_by_coach(result, coach_id)
    
    return {
        "imported": result.get('imported', 0),
        "updated": result.get('updated', 0),
        "deleted": result.get('deleted', 0),
        "rejected": len(result.get('rejected_events', [])),
        "warnings": len(result.get('warning_events', [])),
        "sync_time": result.get('duration', 0)
    }

def build_stats_from_auto_sync(auto_status):
    """Construye stats desde auto-sync"""
    
    # Stats de cambios
    last_changes = auto_status.get('last_changes') or {}
 
    problems = get_sync_problems()

    rejected_count = 0
    warnings_count = 0
  
    
    if problems:
        # 🔧 VERIFICAR que los datos sean recientes (últimos 2 minutos)
        timestamp_str = problems.get('timestamp', '')
        if timestamp_str:
            try:
                import datetime as dt
                problem_time = dt.datetime.strptime(timestamp_str, "%d/%m/%Y %H:%M:%S")
                current_time = dt.datetime.now()
                age_minutes = (current_time - problem_time).total_seconds() / 60
                
                # Solo usar datos si son recientes (< 2 min)
                if age_minutes < 2:
                    rejected = problems.get('rejected', [])
                    warnings = problems.get('warnings', [])
                else:
                    # Datos antiguos, usar listas vacías
                    rejected = []
                    warnings = []
            except:
                # Error parseando timestamp, usar datos como están
                rejected = problems.get('rejected', [])
                warnings = problems.get('warnings', [])
        else:
            rejected = problems.get('rejected', [])
            warnings = problems.get('warnings', [])

        # Filtrar por coach si es necesario
        coach_id = get_coach_id_if_needed()
        if coach_id:
            temp_result = {
                'rejected_events': rejected,
                'warning_events': warnings
            }
            filtered_result = filter_sync_results_by_coach(temp_result, coach_id)
            
            rejected_count = len(filtered_result.get('rejected_events', []))
            warnings_count = len(filtered_result.get('warning_events', []))
        else:
            rejected_count = len(rejected)
            warnings_count = len(warnings)
    
    result = {
        "imported": last_changes.get('imported', 0),
        "updated": last_changes.get('updated', 0), 
        "deleted": last_changes.get('deleted', 0),
        "rejected": rejected_count,
        "warnings": warnings_count,
        "sync_time": auto_status.get('last_sync_duration', 0)
    }
    
    return result

def filter_sync_results_by_coach(result, coach_id):
    """Filtra resultados de sync para mostrar solo eventos del coach específico"""
    if not result or not coach_id:
        return result
    
    # Burscar con mayúscula y minúscula
    coach_patterns = [
        f"#C{coach_id}",  # Mayúscula: #C1
        f"#c{coach_id}",  # Minúscula: #c1
        f"coach {coach_id}",  # Texto: coach 1
        f"Coach {coach_id}"   # Texto: Coach 1
    ]
    
    def is_coach_event(title):
        """Verifica si un título pertenece al coach"""
        if not title:
            return False
        title_lower = title.lower()
        for pattern in coach_patterns:
            if pattern.lower() in title_lower:
                return True
        return False
    
    coach_rejected = []
    coach_warnings = []

    # Filtrar eventos rechazados
    for event in result.get('rejected_events', []):
        if is_coach_event(event.get('title', '')):
            coach_rejected.append(event)
    
    # Filtrar warnings
    for event in result.get('warning_events', []):
        if is_coach_event(event.get('title', '')):
            coach_warnings.append(event)
    
    # Devolver resultado filtrado
    filtered_result = result.copy()
    filtered_result['rejected_events'] = coach_rejected
    filtered_result['warning_events'] = coach_warnings
    
    return filtered_result

def get_content_path(section):
    """
    Devuelve la ruta al módulo de contenido según la sección seleccionada.
    
    Args:
        section (str): Sección seleccionada en el menú
        
    Returns:
        str: Ruta al módulo de contenido
    """
    content_map = {
        "Ballers": "pages.ballers",
        "Administration": "pages.administration",
        "Settings": "pages.settings"
    }
    
    return content_map.get(section)

if __name__ == "__main__":
    # Mostrar mensaje de cierre de sesión si es necesario
    if st.session_state.get("show_logout_message"):
        st.success("You have successfully logged out")
        del st.session_state["show_logout_message"]
    
    selected = create_sidebar_menu()
    st.title(f"Sección: {selected}")
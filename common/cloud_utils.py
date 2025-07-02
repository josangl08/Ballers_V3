# common/cloud_utils.py - NUEVO ARCHIVO

import os

import streamlit as st


def is_streamlit_cloud():
    """
    Detecta si la aplicación está ejecutándose en Streamlit Cloud.

    Returns:
        bool: True si está en Streamlit Cloud
    """
    # Múltiples formas de detectar Streamlit Cloud
    cloud_indicators = [
        # Variable de entorno específica
        os.getenv("STREAMLIT_CLOUD") == "true",
        # Hostname contiene streamlit.io
        "streamlit.io" in os.getenv("HOSTNAME", ""),
        # No hay permisos de escritura en directorio actual
        not os.access(".", os.W_OK),
        # Variable de entorno del servidor
        os.getenv("STREAMLIT_SERVER_PORT") is not None,
        # Directorio de trabajo específico de Cloud
        "/app" in os.getcwd() and not os.access("/app", os.W_OK),
    ]

    is_cloud = any(cloud_indicators)

    # Debug info (solo mostrar una vez)
    if not hasattr(st.session_state, "_cloud_detection_logged"):
        environment = "🌐 Streamlit Cloud" if is_cloud else "💻 Local"
        print(f"{environment} detectado")
        st.session_state._cloud_detection_logged = True

    return is_cloud


def safe_database_operation(operation_name="Database operation"):
    """
    Decorator que protege operaciones de escritura en Streamlit Cloud.

    Args:
        operation_name: Nombre descriptivo de la operación

    Returns:
        Decorator function
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            if is_streamlit_cloud():
                # En Cloud: retornar éxito simulado pero sin ejecutar
                success_message = f"✅ {operation_name} completed (demo mode)"
                print(f"🌐 Cloud: {operation_name} skipped (read-only mode)")

                # Retornar formato típico de success
                if func.__name__.startswith(("create_", "update_", "delete_")):
                    return True, success_message
                else:
                    return True
            else:
                # En local: ejecutar normalmente
                return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


def show_cloud_mode_info():
    """
    Muestra información sobre el modo Cloud de forma no invasiva.
    Llamar al inicio de páginas que permiten edición.
    """
    if is_streamlit_cloud():
        st.info(
            "📖 **Demo Mode**: You're viewing the live demo. "
            "Data changes are simulated but not saved permanently. "
            "For full functionality, run the app locally."
        )


def show_cloud_feature_limitation(feature_name="This feature"):
    """
    Muestra limitación específica de una característica en Cloud.

    Args:
        feature_name: Nombre de la característica limitada
    """
    if is_streamlit_cloud():
        st.warning(
            f"🌐 {feature_name} is view-only in the demo. Run locally for full functionality."
        )


def get_environment_info():
    """
    Obtiene información del entorno para debugging.

    Returns:
        dict: Información del entorno
    """
    return {
        "is_cloud": is_streamlit_cloud(),
        "hostname": os.getenv("HOSTNAME", "unknown"),
        "cwd": os.getcwd(),
        "write_access": os.access(".", os.W_OK),
        "streamlit_server_port": os.getenv("STREAMLIT_SERVER_PORT"),
        "environment_type": "cloud" if is_streamlit_cloud() else "local",
    }

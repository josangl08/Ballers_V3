# main_dash.py - Aplicación principal migrada de Streamlit a Dash
import atexit
import logging
import os

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from callbacks.administration_callbacks import register_administration_callbacks
from callbacks.ballers_callbacks import register_ballers_callbacks

# Importar callbacks organizados
from callbacks.navigation_callbacks import register_navigation_callbacks
from callbacks.player_callbacks import register_player_callbacks
from callbacks.settings_callbacks import register_settings_callbacks
from callbacks.sidebar_callbacks import register_sidebar_callbacks
from common.datepicker_utils import (
    create_datepicker_dummy_divs,
    register_datepicker_callbacks,
)
from common.login_dash import register_login_callbacks
from common.menu_dash import register_menu_callbacks

# Importar configuración
from config import APP_ICON, APP_NAME  # noqa: F401
from controllers.db import initialize_database  # noqa: F401

# Importar integración completa de webhooks
from controllers.webhook_integration import (
    initialize_webhook_integration, 
    shutdown_webhook_integration,
    is_webhook_integration_healthy
)

# Configuración de la aplicación Dash
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css",
    ],
    suppress_callback_exceptions=True,
    assets_folder="assets",
)
app.title = APP_NAME
server = app.server


def get_app_layout():
    """Retorna el layout principal de la aplicación Dash."""
    return dbc.Container(
        [
            dcc.Location(id="url", refresh=False),
            dcc.Store(id="session-store", storage_type="session"),
            # Layout principal
            html.Div(id="main-content"),
            # Divs dummy para callbacks de datepicker
            *create_datepicker_dummy_divs(),
        ],
        fluid=True,
    )


# Layout principal de la aplicación
app.layout = get_app_layout()


# Registrar todos los callbacks organizados
def register_all_callbacks():
    """Registra todos los callbacks de la aplicación."""
    # register_auth_callbacks(app)  # Deshabilitado - usando login_dash.py callbacks
    register_login_callbacks(app)  # Callbacks de login con pausa
    register_menu_callbacks(app)  # Callbacks del menú y logout
    register_navigation_callbacks(app)
    register_player_callbacks(app)
    register_administration_callbacks(app)
    register_settings_callbacks(app)
    register_sidebar_callbacks(app)

    # Registrar callbacks específicos de páginas
    register_ballers_callbacks(app)

    # Registrar callbacks comunes para datepickers
    register_datepicker_callbacks(app)


def initialize_dash_app():
    """Inicializa la aplicación Dash."""
    # Configurar nivel de logging basado en variable de entorno
    DEBUG_MODE = os.getenv("DEBUG", "False") == "True"

    if DEBUG_MODE:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        print("🔧 DEBUG MODE ENABLED - Verbose logging active")
    else:
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )

    # Registrar callbacks
    register_all_callbacks()

    # Inicializar integración completa de webhooks para sync en tiempo real
    _initialize_webhook_integration()

    return app


def _initialize_webhook_integration():
    """Inicializa la integración completa de webhooks (servidor + Google Calendar)."""
    # Evitar doble inicialización en modo debug (Flask reloader)
    if os.getenv('WERKZEUG_RUN_MAIN') == 'true':
        return  # Skip initialization in reloader process
        
    try:
        print("🚀 Initializing complete webhook integration for real-time sync...")
        success = initialize_webhook_integration()
        
        if success:
            print("✅ Webhook integration initialized successfully")
            print("📡 Real-time sync with Google Calendar fully enabled")
            print("🔄 Auto-renewal system active for webhook channels")
            
            # Registrar cleanup al cerrar la aplicación
            atexit.register(_cleanup_webhook_integration)
        else:
            print("⚠️ Failed to initialize webhook integration - using manual sync only")
            print("📝 Real-time sync disabled, manual sync remains available")
            
    except Exception as e:
        print(f"❌ Error initializing webhook integration: {e}")
        print("📝 Fallback: Manual sync remains available")


def _cleanup_webhook_integration():
    """Limpia la integración completa de webhooks al cerrar la aplicación."""
    try:
        print("🧹 Cleaning up webhook integration...")
        shutdown_webhook_integration()
        print("✅ Webhook integration shut down successfully")
    except Exception as e:
        print(f"⚠️ Error shutting down webhook integration: {e}")


if __name__ == "__main__":
    app = initialize_dash_app()

    print("🚀 Starting Ballers Dash Application...")
    print("📊 Main app: http://127.0.0.1:8050")
    print("📡 Webhook integration: http://127.0.0.1:8001/webhook/calendar")
    
    # Verificar estado de integración después de inicialización
    if is_webhook_integration_healthy():
        print("💚 Real-time sync: ACTIVE")
    else:
        print("🟡 Real-time sync: INACTIVE (manual sync available)")

    app.run(debug=True, host="127.0.0.1", port=8050)

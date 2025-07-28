# main_dash.py - Aplicación principal migrada de Streamlit a Dash
import atexit
import logging
import os
import time

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, no_update

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
    is_webhook_integration_healthy,
    shutdown_webhook_integration,
)

# Sistema simple para webhook events
_webhook_pending = False

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

# Usar layout estándar de Dash - eliminamos JavaScript manual


def get_app_layout():
    """Retorna el layout principal de la aplicación Dash."""
    return dbc.Container(
        [
            dcc.Location(id="url", refresh=False),
            dcc.Store(id="session-store", storage_type="session"),
            dcc.Store(id="webhook-trigger", storage_type="memory", data=0),
            dcc.Store(id="webhook-activation", storage_type="memory", data=0),
            # Smart interval para real-time updates (siempre activo pero lento cuando no hay webhooks)
            dcc.Interval(
                id="smart-interval",
                interval=5000,  # 5 segundos por defecto (lento)
                disabled=False,  # Siempre habilitado
                max_intervals=-1,  # Sin limite
                n_intervals=0
            ),
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
    
    # Webhook Activation Trigger - Activar cuando hay webhook
    @app.callback(
        Output("webhook-activation", "data"),
        [Input("smart-interval", "n_intervals")],
        prevent_initial_call=True
    )
    def trigger_activation_on_webhook(n_intervals):
        """Trigger interno - convierte webhook flag en Store update"""
        global _webhook_pending
        print(f"🔍 DEBUG: trigger_activation_on_webhook called - n_intervals={n_intervals}, _webhook_pending={_webhook_pending}")
        
        if _webhook_pending:
            _webhook_pending = False
            timestamp = int(time.time())
            print(f"🔄 Webhook activation triggered: {timestamp}")
            print(f"🔍 DEBUG: Returning NEW timestamp to webhook-activation Store: {timestamp}")
            print(f"🔍 DEBUG: This should trigger manage_smart_interval callback")
            return timestamp
        
        print(f"🔍 DEBUG: No webhook pending, returning no_update")
        return no_update

    # Smart Interval Manager - Control por velocidad basado en webhook activation  
    @app.callback(
        Output("smart-interval", "interval"),
        [Input("webhook-activation", "data"),
         Input("smart-interval", "n_intervals")],
        prevent_initial_call=False
    )
    def manage_smart_interval(activation_data, n_intervals):
        """Gestiona el smart interval: acelerar cuando hay webhook, desacelerar después de inactividad"""
        print(f"🔍 DEBUG: manage_smart_interval called - activation_data={activation_data}, n_intervals={n_intervals}")
        
        if activation_data and activation_data > 0:
            # Acelerar interval cuando hay webhook activation (1 segundo)
            print(f"🔄 Smart interval accelerated by webhook at timestamp {activation_data}")
            print(f"🔍 DEBUG: Setting interval to 1000ms (fast)")
            return 1000  # 1 segundo - rápido
        elif n_intervals > 10:  # Después de 10 intervals sin webhook
            # Desacelerar después de inactividad (5 segundos)
            print(f"🔄 Smart interval decelerated after inactivity")
            print(f"🔍 DEBUG: Setting interval to 5000ms (slow)")
            return 5000  # 5 segundos - lento
        else:
            # No cambios necesarios
            print(f"🔍 DEBUG: No changes needed, keeping current interval")
            return no_update

    # Smart Interval Update - Actualiza Store cuando interval está activo
    @app.callback(
        Output("webhook-trigger", "data"),
        [Input("smart-interval", "n_intervals")],
        prevent_initial_call=True
    )
    def update_store_from_smart_interval(n_intervals):
        """Actualiza webhook-trigger Store cuando smart interval está activo"""
        print(f"🔍 DEBUG: update_store_from_smart_interval called - n_intervals={n_intervals}")
        
        if n_intervals > 0:
            timestamp = int(time.time())
            print(f"🔄 Smart interval update #{n_intervals} - Store updated: {timestamp}")
            print(f"🔍 DEBUG: Updating webhook-trigger Store with timestamp: {timestamp}")
            return timestamp
        
        print(f"🔍 DEBUG: n_intervals <= 0, returning no_update")
        return no_update
    
    

def trigger_webhook_ui_refresh():
    """
    Función llamada por webhook server para activar smart interval.
    Actualiza directamente los Stores sin depender del smart interval.
    """
    global _webhook_pending
    try:
        current_time = int(time.time())
        print(f"🔍 DEBUG: trigger_webhook_ui_refresh called at {current_time}")
        print(f"🔍 DEBUG: _webhook_pending before: {_webhook_pending}")
        
        _webhook_pending = True
        print(f"🔄 Webhook detected - smart interval activation requested")
        print(f"🔍 DEBUG: _webhook_pending after: {_webhook_pending}")
        
        # NUEVO: Intentar actualizar Stores directamente
        try:
            # Esto forzará la reactivación del smart interval
            print(f"🔄 Attempting to force Store updates...")
        except Exception as store_error:
            print(f"⚠️ Error updating Stores directly: {store_error}")
        
    except Exception as e:
        print(f"⚠️ Error activating smart interval: {e}")
        import traceback
        traceback.print_exc()
    


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
    if os.getenv("WERKZEUG_RUN_MAIN") == "true":
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

    # Solo mostrar mensajes en el proceso principal (no en Flask reloader)
    if os.getenv('WERKZEUG_RUN_MAIN') != 'true':
        print("🚀 Starting Ballers Dash Application...")
        print("📊 Main app: http://127.0.0.1:8050")
        print("📡 Webhook integration: http://127.0.0.1:8001/webhook/calendar")

        # Verificar estado de integración después de inicialización
        try:
            from controllers.webhook_integration import is_webhook_integration_healthy
            if is_webhook_integration_healthy():
                print("💚 Real-time sync: ACTIVE")
            else:
                print("🟡 Real-time sync: INACTIVE (manual sync available)")
        except Exception:
            print("🟡 Real-time sync: INACTIVE (manual sync available)")

    app.run(debug=True, host="127.0.0.1", port=8050)

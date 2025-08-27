# main_dash.py - Aplicación principal migrada de Streamlit a Dash
import atexit
import datetime as dt
import json
import logging
import os
import queue
import threading
import time

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html, no_update
from flask import Response, jsonify, request

from callbacks.administration_callbacks import register_administration_callbacks
from callbacks.ballers_callbacks import register_ballers_callbacks

# Importar callbacks organizados
from callbacks.navigation_callbacks import register_navigation_callbacks
from callbacks.player_callbacks import register_player_callbacks
from callbacks.professional_tabs_callbacks import register_professional_tabs_callbacks
from callbacks.settings_callbacks import register_settings_callbacks
from callbacks.sidebar_callbacks import register_sidebar_callbacks
from callbacks.webhook_callbacks import register_webhook_callbacks
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

# Importar componentes webhook para integración
from controllers.calendar_sync_core import (
    sync_calendar_to_db_with_feedback,
    sync_db_to_calendar,
)
from controllers.notification_controller import save_sync_problems
from controllers.session_controller import update_past_sessions

# Sistema de webhook events movido a callbacks/webhook_callbacks.py

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

# Variables globales para webhook integrado
_webhook_stats = {
    "webhooks_received": 0,
    "webhooks_processed": 0,
    "last_webhook_time": None,
    "server_started_at": None,
    "sync_errors": 0,
}
_sse_event_queue = queue.Queue(maxsize=100)

# Usar layout estándar de Dash - eliminamos JavaScript manual


def get_app_layout():
    """Retorna el layout principal de la aplicación Dash."""
    return dbc.Container(
        [
            dcc.Location(id="url", refresh=False),
            # SISTEMA HÍBRIDO DE SESIONES:
            # Store principal (expira al cerrar navegador si no hay "Remember Me")
            dcc.Store(id="session-store", storage_type="session"),
            # Store persistente para "Remember Me" (localStorage, 30 días)
            dcc.Store(id="persistent-session-store", storage_type="local"),
            # Store para gestión de timeout e inactividad
            dcc.Store(
                id="session-activity",
                storage_type="memory",
                data={"last_activity": None, "remember_me": False},
            ),
            # 🛡️ FALLBACK STORE: Para modo degradado sin SSE
            dcc.Store(id="fallback-trigger", storage_type="memory", data=0),
            dcc.Store(
                id="sse-status",
                storage_type="memory",
                data={"connected": False, "last_heartbeat": 0},
            ),
            # 🛡️ FALLBACK INTELIGENTE: Interval de seguridad si SSE falla (deshabilitado por defecto)
            dcc.Interval(
                id="fallback-interval",
                interval=30000,  # 30 segundos - muy conservador
                disabled=True,  # INACTIVO por defecto - solo se activa si SSE falla
                max_intervals=-1,
                n_intervals=0,
            ),
            # SSE connector para real-time updates (SOLUCIÓN: Zero-polling)
            html.Div(id="sse-connector", style={"display": "none"}),
            # Layout principal
            html.Div(id="main-content"),
            # Divs dummy para callbacks de datepicker
            *create_datepicker_dummy_divs(),
        ],
        fluid=True,
    )


# Layout principal de la aplicación
app.layout = get_app_layout()


# =============================================================================
# WEBHOOK ENDPOINTS INTEGRADOS PARA PRODUCCIÓN
# =============================================================================

# Solo en producción: agregar endpoints webhook al servidor Dash
from config import ENVIRONMENT

if ENVIRONMENT == "production":
    import logging
    
    @server.route("/webhook/calendar", methods=["POST"])
    def handle_calendar_webhook():
        """Endpoint principal para webhooks de Google Calendar (integrado en Dash)"""
        try:
            # Validar headers básicos de Google
            required_headers = ["X-Goog-Channel-ID", "X-Goog-Resource-ID", "X-Goog-Resource-State"]
            for header in required_headers:
                if header not in request.headers:
                    logging.warning(f"Missing required header: {header}")
                    return jsonify({"error": "Invalid webhook"}), 401

            # Extraer información del webhook
            channel_id = request.headers.get("X-Goog-Channel-ID")
            resource_state = request.headers.get("X-Goog-Resource-State")
            
            logging.info(f"📡 Webhook received (integrated): channel={channel_id}, state={resource_state}")

            # Procesar webhook si es necesario
            if resource_state in ["exists", "updated"]:
                # Importar y ejecutar sync en background
                def process_webhook():
                    try:
                        from controllers.calendar_sync_core import sync_calendar_to_db_with_feedback
                        from controllers.session_controller import update_past_sessions
                        from controllers.notification_controller import save_sync_problems
                        
                        # Ejecutar sincronización
                        imported, updated, deleted, rejected_events, warning_events = sync_calendar_to_db_with_feedback()
                        
                        # Actualizar sesiones pasadas si es necesario
                        n_past = update_past_sessions()
                        
                        total_changes = imported + updated + deleted
                        logging.info(f"✅ Integrated webhook sync completed: {imported}+{updated}+{deleted} changes")
                        
                        # Guardar problemas
                        save_sync_problems(rejected_events, warning_events)
                        
                    except Exception as e:
                        logging.error(f"❌ Integrated webhook sync error: {e}")
                
                # Ejecutar en thread separado para no bloquear response
                import threading
                threading.Thread(target=process_webhook, daemon=True).start()
                
            elif resource_state == "sync":
                logging.info("📞 Webhook sync message received (integrated endpoint)")
            
            return jsonify({"status": "received", "server": "dash_integrated"}), 200

        except Exception as e:
            logging.error(f"❌ Integrated webhook processing error: {e}")
            return jsonify({"error": "Webhook processing failed"}), 500

    @server.route("/webhook/status", methods=["GET"])
    def webhook_status():
        """Endpoint para verificar estado del servidor webhook (integrado en Dash)"""
        return jsonify({
            "status": "active",
            "server_type": "dash_integrated",
            "environment": "production",
            "integration": "enabled"
        }), 200

    @server.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint (integrado en Dash)"""
        return jsonify({
            "status": "healthy", 
            "server_type": "dash_integrated",
            "environment": "production"
        }), 200


# Registrar todos los callbacks organizados
def register_all_callbacks():
    """Registra todos los callbacks de la aplicación."""
    # register_auth_callbacks(app)  # DESHABILITADO: duplica callbacks con login_dash.py
    register_login_callbacks(app)  # Callbacks de login con pausa
    register_menu_callbacks(app)  # Callbacks del menú (logout movido a login_dash.py)
    register_navigation_callbacks(app)
    register_player_callbacks(app)
    register_administration_callbacks(app)
    register_settings_callbacks(app)
    register_sidebar_callbacks(app)

    # Registrar callbacks específicos de páginas
    register_ballers_callbacks(app)
    register_professional_tabs_callbacks(app)

    # Registrar callbacks comunes para datepickers
    register_datepicker_callbacks(app)

    # 🛡️ Registrar callbacks legacy (ahora vacíos) y fallback
    register_webhook_callbacks(app)

    # SSE Client Callback para real-time updates (SOLUCIÓN: Zero-polling)
    app.clientside_callback(
        """
        function(pathname) {
            // Establecer conexión SSE una sola vez
            if (!window.webhookSSE) {
                console.log('🌐 Establishing SSE connection for real-time updates...');

                // Crear conexión SSE al webhook server
                window.webhookSSE = new EventSource('http://localhost:8001/webhook/events');

                // Handler para eventos SSE - Updates directos a UI
                window.webhookSSE.onmessage = function(event) {
                    try {
                        const eventData = JSON.parse(event.data);
                        console.log('📡 SSE event received:', eventData);

                        if (eventData.type === 'calendar_change') {
                            // 🎯 UPDATE GRANULAR: Actualizar stores sin recargar página
                            console.log('🔄 Calendar changed - triggering granular UI refresh');
                            console.log(`📊 Changes detected: ${eventData.changes_count}`);

                            // Update granular via Dash stores - mantiene contexto de navegación
                            if (!document.activeElement || document.activeElement.tagName === 'BODY') {
                                // Update inmediato: Actualizar fallback-trigger store
                                const timestamp = Date.now();
                                console.log('🎯 Triggering store-based refresh - no page reload');

                                // Trigger update del store fallback-trigger
                                if (window.dash_clientside && window.dash_clientside.set_props) {
                                    window.dash_clientside.set_props('fallback-trigger', {'data': timestamp});
                                } else {
                                    // Fallback: Dispatch custom event para callback listener
                                    window.dispatchEvent(new CustomEvent('calendar-change', {
                                        detail: {
                                            timestamp: timestamp,
                                            changes_count: eventData.changes_count,
                                            type: 'calendar_change'
                                        }
                                    }));
                                }
                            } else {
                                // Usuario escribiendo - diferir update
                                console.log('⚠️ User is typing - deferring store update');
                                window.pendingSSEUpdate = {
                                    timestamp: Date.now(),
                                    changes_count: eventData.changes_count
                                };

                                // Auto-update cuando usuario termine de escribir
                                setTimeout(() => {
                                    if (window.pendingSSEUpdate && (!document.activeElement || document.activeElement.tagName === 'BODY')) {
                                        console.log('🎯 Executing deferred store update');
                                        const data = window.pendingSSEUpdate;

                                        if (window.dash_clientside && window.dash_clientside.set_props) {
                                            window.dash_clientside.set_props('fallback-trigger', {'data': data.timestamp});
                                        } else {
                                            window.dispatchEvent(new CustomEvent('calendar-change', {
                                                detail: data
                                            }));
                                        }

                                        window.pendingSSEUpdate = null;
                                    }
                                }, 3000);
                            }
                        } else if (eventData.type === 'heartbeat') {
                            // Heartbeat - actualizar estado de conexión
                            window.lastSSEHeartbeat = Date.now();
                            window.sseConnected = true;
                            console.debug('💓 SSE heartbeat - connection healthy');
                        }
                    } catch (error) {
                        console.error('❌ Error processing SSE event:', error);
                    }
                };

                window.webhookSSE.onopen = function() {
                    console.log('✅ SSE connection established');

                    // Actualizar estado SSE - desactivar fallback
                    window.sseConnected = true;
                    window.lastSSEHeartbeat = Date.now();

                    // Trigger update del store de estado SSE
                    if (window.dash_clientside) {
                        window.dispatchEvent(new CustomEvent('sse-status-update', {
                            detail: { connected: true, last_heartbeat: Date.now() }
                        }));
                    }
                };

                window.webhookSSE.onerror = function(error) {
                    console.warn('⚠️ SSE connection error, browser will auto-reconnect:', error);

                    // Marcar SSE como desconectado - activará fallback
                    window.sseConnected = false;
                    window.dispatchEvent(new CustomEvent('sse-status-update', {
                        detail: { connected: false, last_heartbeat: window.lastSSEHeartbeat || 0 }
                    }));
                };

                // Handler para cuando usuario deja de escribir - ejecutar update pendiente
                document.addEventListener('focusout', function() {
                    setTimeout(() => {
                        if (window.pendingSSEUpdate && (!document.activeElement || document.activeElement.tagName === 'BODY')) {
                            console.log('🎯 Executing deferred store update on focus out');
                            const data = window.pendingSSEUpdate;

                            if (window.dash_clientside && window.dash_clientside.set_props) {
                                window.dash_clientside.set_props('fallback-trigger', {'data': data.timestamp});
                            } else {
                                window.dispatchEvent(new CustomEvent('calendar-change', {
                                    detail: data
                                }));
                            }

                            window.pendingSSEUpdate = null;
                        }
                    }, 1000);
                });
            }

            return window.dash_clientside.no_update;
        }
        """,
        Output("sse-connector", "children"),
        Input("url", "pathname"),
        prevent_initial_call=False,
    )

    # 🛡️ FALLBACK CALLBACK: Monitor de estado SSE y activación de fallback
    app.clientside_callback(
        """
        function(n_intervals) {
            // Verificar estado de conexión SSE
            const now = Date.now();
            const lastHeartbeat = window.lastSSEHeartbeat || 0;
            const timeSinceHeartbeat = now - lastHeartbeat;
            const sseConnected = window.sseConnected || false;

            // Si no hay heartbeat en > 60 segundos, considerar SSE desconectado
            if (timeSinceHeartbeat > 60000 && lastHeartbeat > 0) {
                console.warn('⚠️ SSE connection timeout - no heartbeat for 60s');
                return { connected: false, last_heartbeat: lastHeartbeat };
            }

            // Retornar estado actual
            return {
                connected: sseConnected,
                last_heartbeat: lastHeartbeat,
                check_time: now
            };
        }
        """,
        Output("sse-status", "data"),
        Input("fallback-interval", "n_intervals"),
        prevent_initial_call=True,
    )

    # 🛡️ FALLBACK ACTIVATION: Activar interval de seguridad si SSE falla
    app.clientside_callback(
        """
        function(sse_status) {
            if (!sse_status) return window.dash_clientside.no_update;

            const connected = sse_status.connected;
            const timeSinceHeartbeat = Date.now() - (sse_status.last_heartbeat || 0);

            // Activar fallback si:
            // 1. SSE no está conectado Y
            // 2. Ha pasado más de 60s sin heartbeat Y
            // 3. Hubo al menos un heartbeat previo (SSE intentó conectar)
            const shouldActivateFallback = (
                !connected &&
                timeSinceHeartbeat > 60000 &&
                sse_status.last_heartbeat > 0
            );

            if (shouldActivateFallback) {
                console.warn('🛡️ Activating fallback polling - SSE connection lost');
                return false; // disabled = false (activar interval)
            }

            // Mantener fallback desactivado si SSE funciona
            return true; // disabled = true (mantener desactivado)
        }
        """,
        Output("fallback-interval", "disabled"),
        Input("sse-status", "data"),
        prevent_initial_call=True,
    )


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
            print(
                "⚠️ Failed to initialize webhook integration - using manual sync only"
            )  # noqa: E501
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
    if os.getenv("WERKZEUG_RUN_MAIN") != "true":
        # Configuración adaptativa según entorno
        from config import ENVIRONMENT, WEBHOOK_BASE_URL
        
        print("🚀 Starting Ballers Dash Application...")
        
        if ENVIRONMENT == "production":
            print("🌍 Modo producción (Render)")
            print(f"📊 Main app: https://ballers-v3.onrender.com")
            print(f"📡 Webhook endpoint: {WEBHOOK_BASE_URL}/webhook/calendar")
        else:
            print("🔧 Modo desarrollo")
            print("📊 Main app: http://127.0.0.1:8050")
            print("📡 Webhook integration: http://127.0.0.1:8001/webhook/calendar")

        # Verificar estado de integración después de inicialización
        try:
            if is_webhook_integration_healthy():
                print("💚 Real-time sync: ACTIVE")
            else:
                print("🟡 Real-time sync: INACTIVE (manual sync available)")
        except Exception:
            print("🟡 Real-time sync: INACTIVE (manual sync available)")

    # Configuración puerto y host para Render
    # Render usa PORT env var dinámicamente
    port = int(os.getenv("PORT", "8050"))
    
    # Host binding: 0.0.0.0 para producción, 127.0.0.1 para desarrollo
    if os.getenv("ENVIRONMENT") == "production":
        host = "0.0.0.0"
        debug = False
    else:
        host = "127.0.0.1"
        debug = True
    
    print(f"🎯 Starting server on {host}:{port} (debug={debug})")
    app.run(debug=debug, host=host, port=port)

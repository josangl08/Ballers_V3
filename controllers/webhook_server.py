# controllers/webhook_server.py
"""
Webhook server for Google Calendar push notifications.
Runs as separate Flask server to receive real-time calendar events.
"""
import datetime as dt
import logging
import threading
import time
from typing import Any, Dict

import json
import queue

from flask import Flask, Response, jsonify, request
from werkzeug.serving import make_server

from config import WEBHOOK_PORT, WEBHOOK_SECRET_TOKEN
from controllers.calendar_sync_core import (
    sync_calendar_to_db_with_feedback,
    sync_db_to_calendar,
)
from controllers.notification_controller import save_sync_problems
from controllers.session_controller import update_past_sessions

logger = logging.getLogger(__name__)


class WebhookServer:
    """
    Flask server para recibir webhooks de Google Calendar.
    Ejecuta en un thread separado para no bloquear la aplicación principal.
    """

    def __init__(
        self, port: int = WEBHOOK_PORT, secret_token: str = WEBHOOK_SECRET_TOKEN
    ):
        self.port = port
        self.secret_token = secret_token
        self.app = Flask(__name__)
        self.server = None
        self.thread = None
        self._setup_routes()

        # Statistics
        self.stats = {
            "webhooks_received": 0,
            "webhooks_processed": 0,
            "last_webhook_time": None,
            "server_started_at": None,
            "sync_errors": 0,
        }
        
        # SSE Event queue for real-time updates (SOLUCIÓN: Zero-polling)
        self.sse_event_queue = queue.Queue(maxsize=100)
        self.sse_clients = set()  # Track connected SSE clients

    def _setup_routes(self):
        """Configura las rutas del servidor Flask"""

        @self.app.route("/webhook/calendar", methods=["POST"])
        def handle_calendar_webhook():
            """Endpoint principal para webhooks de Google Calendar"""
            try:
                self.stats["webhooks_received"] += 1
                self.stats["last_webhook_time"] = dt.datetime.now().isoformat()

                # Validar headers de Google
                if not self._validate_google_webhook(request):
                    logger.warning("🚨 Webhook validation failed")
                    return jsonify({"error": "Invalid webhook"}), 401

                # Extraer información del webhook
                headers = dict(request.headers)
                channel_id = headers.get("X-Goog-Channel-ID")
                resource_id = headers.get("X-Goog-Resource-ID")
                resource_state = headers.get("X-Goog-Resource-State")

                logger.info(
                    f"📡 Webhook received: channel={channel_id}, state={resource_state}"
                )

                # Procesar webhook en background
                if resource_state in ["exists", "updated"]:
                    self._process_webhook_async(channel_id, resource_id, resource_state)
                elif resource_state == "sync":
                    logger.info(
                        "📞 Webhook sync message received (channel established)"
                    )
                else:
                    logger.warning(f"🤔 Unknown webhook state: {resource_state}")

                return jsonify({"status": "received"}), 200

            except Exception as e:
                logger.error(f"❌ Webhook processing error: {e}")
                return jsonify({"error": "Webhook processing failed"}), 500

        @self.app.route("/webhook/status", methods=["GET"])
        def webhook_status():
            """Endpoint para verificar estado del servidor webhook"""
            return (
                jsonify(
                    {
                        "status": "active",
                        "stats": self.stats,
                        "uptime_seconds": (
                            (
                                time.time()
                                - self.stats.get("server_started_at", time.time())
                            )
                            if self.stats.get("server_started_at")
                            else 0
                        ),
                    }
                ),
                200,
            )

        @self.app.route("/health", methods=["GET"])
        def health_check():
            """Health check endpoint"""
            return jsonify({"status": "healthy"}), 200

        @self.app.route("/webhook/events", methods=["GET"])
        def sse_event_stream():
            """
            Server-Sent Events endpoint para updates en tiempo real.
            SOLUCIÓN: Zero-polling, updates instantáneos a la UI.
            """
            def generate_sse_events():
                """Generador de eventos SSE para el cliente"""
                try:
                    logger.info("🌐 New SSE client connected")
                    
                    while True:
                        try:
                            # Esperar evento de webhook (con timeout para heartbeat)
                            event_data = self.sse_event_queue.get(timeout=30)
                            
                            # Enviar evento al cliente
                            sse_message = f"data: {json.dumps(event_data)}\n\n"
                            logger.debug(f"📤 Sending SSE event: {event_data}")
                            yield sse_message
                            
                        except queue.Empty:
                            # Heartbeat para mantener conexión viva
                            heartbeat = f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
                            yield heartbeat
                            
                except GeneratorExit:
                    logger.info("🔌 SSE client disconnected")
                except Exception as e:
                    logger.error(f"❌ SSE stream error: {e}")
            
            # Retornar stream SSE con headers correctos
            return Response(
                generate_sse_events(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                }
            )

    def _validate_google_webhook(self, request) -> bool:
        """
        Valida que el webhook provenga realmente de Google Calendar.
        Verifica headers requeridos y token de seguridad.
        """
        try:
            # Verificar headers requeridos de Google
            required_headers = [
                "X-Goog-Channel-ID",
                "X-Goog-Resource-ID",
                "X-Goog-Resource-State",
            ]

            for header in required_headers:
                if header not in request.headers:
                    logger.warning(f"Missing required header: {header}")
                    return False

            # Verificar token si está configurado
            if self.secret_token and self.secret_token != "default-secret-token":
                webhook_token = request.headers.get("X-Goog-Channel-Token")
                if webhook_token != self.secret_token:
                    logger.warning("Invalid webhook token")
                    return False

            return True

        except Exception as e:
            logger.error(f"Webhook validation error: {e}")
            return False

    def _process_webhook_async(
        self, channel_id: str, resource_id: str, resource_state: str
    ):
        """
        Procesa el webhook de forma asíncrona para no bloquear la respuesta HTTP.
        Ejecuta sincronización targeted usando el core sync existente.
        """

        def process():
            try:
                logger.info(
                    f"🔄 Processing webhook: {resource_state} for resource {resource_id}"
                )
                start_time = time.time()

                # Ejecutar sincronización usando la función existente
                imported, updated, deleted, rejected_events, warning_events = (
                    sync_calendar_to_db_with_feedback()
                )

                # Actualizar sesiones pasadas si es necesario
                n_past = update_past_sessions()
                if n_past > 0:
                    sync_db_to_calendar()

                duration = time.time() - start_time

                # Guardar problemas usando NotificationController existente
                save_sync_problems(rejected_events, warning_events)

                # Calcular totales para logging y notificaciones
                total_changes = imported + updated + deleted
                total_problems = len(rejected_events) + len(warning_events)

                # Actualizar estadísticas
                self.stats["webhooks_processed"] += 1

                # Notificar cambios a la UI para auto-refresh
                self._notify_ui_changes(total_changes, {
                    'imported': imported,
                    'updated': updated, 
                    'deleted': deleted,
                    'problems': total_problems
                })

                if total_problems > 0:
                    logger.warning(
                        f"🔧 Webhook sync completed with issues in {duration:.1f}s: "
                        f"{imported}+{updated}+{deleted} changes, "
                        f"{len(rejected_events)} rejected, {len(warning_events)} warnings"
                    )
                else:
                    logger.info(
                        f"✅ Webhook sync completed successfully in {duration:.1f}s: "
                        f"{imported}+{updated}+{deleted} changes"
                    )

                # Real-time UI updates handled via notification system

            except Exception as e:
                self.stats["sync_errors"] += 1
                logger.error(f"❌ Webhook sync processing error: {e}")
                # Limpiar problemas en caso de error
                save_sync_problems([], [])

        # Ejecutar en thread separado
        thread = threading.Thread(target=process, daemon=True)
        thread.start()

    def start(self) -> bool:
        """Inicia el servidor webhook en un thread separado"""
        try:
            if self.thread and self.thread.is_alive():
                logger.warning("Webhook server already running")
                return False

            # Crear servidor
            self.server = make_server("localhost", self.port, self.app, threaded=True)
            self.stats["server_started_at"] = time.time()

            # Iniciar en thread separado
            self.thread = threading.Thread(
                target=self.server.serve_forever, daemon=True
            )
            self.thread.start()

            logger.info(f"🚀 Webhook server started on http://localhost:{self.port}")
            logger.info(
                f"📡 Calendar webhook endpoint: http://localhost:{self.port}/webhook/calendar"
            )

            return True

        except Exception as e:
            logger.error(f"❌ Failed to start webhook server: {e}")
            return False

    def stop(self) -> bool:
        """Detiene el servidor webhook"""
        try:
            if self.server:
                self.server.shutdown()
                logger.info("🛑 Webhook server stopped")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Error stopping webhook server: {e}")
            return False

    def is_running(self) -> bool:
        """Verifica si el servidor está ejecutándose"""
        return self.thread and self.thread.is_alive()

    def get_status(self) -> Dict[str, Any]:
        """Obtiene estado detallado del servidor"""
        return {
            "running": self.is_running(),
            "port": self.port,
            "webhook_url": f"http://localhost:{self.port}/webhook/calendar",
            "stats": self.stats.copy(),
        }

    def _notify_ui_changes(self, changes_count: int, details: Dict = None):
        """
        Notifica cambios a la UI via Server-Sent Events.
        NUEVA IMPLEMENTACIÓN: Push directo via cola SSE, sin polling.
        """
        if changes_count > 0:
            try:
                # Crear evento SSE con información detallada del cambio
                sse_event = {
                    'type': 'calendar_change',
                    'changes_count': changes_count,
                    'timestamp': time.time(),
                    'message': f'Calendar updated: {changes_count} changes detected'
                }
                
                # Agregar detalles específicos si están disponibles
                if details:
                    sse_event.update({
                        'details': details,
                        'imported': details.get('imported', 0),
                        'updated': details.get('updated', 0),
                        'deleted': details.get('deleted', 0),
                        'problems': details.get('problems', 0)
                    })
                    
                    # Mensaje más descriptivo
                    parts = []
                    if details.get('imported', 0) > 0:
                        parts.append(f"{details['imported']} imported")
                    if details.get('updated', 0) > 0:
                        parts.append(f"{details['updated']} updated")
                    if details.get('deleted', 0) > 0:
                        parts.append(f"{details['deleted']} deleted")
                    
                    if parts:
                        sse_event['message'] = f'Calendar sync: {", ".join(parts)}'
                
                # Push evento a la cola SSE (sin blocking)
                try:
                    self.sse_event_queue.put_nowait(sse_event)
                    logger.info(f"📤 SSE event pushed: {changes_count} changes")
                except queue.Full:
                    logger.warning("⚠️ SSE event queue full, skipping event")

            except Exception as e:
                logger.error(f"❌ Failed to push SSE event: {e}")


# Instancia global del servidor webhook
_webhook_server = WebhookServer()


# Funciones públicas para integración con la aplicación principal
def start_webhook_server() -> bool:
    """Inicia el servidor webhook"""
    return _webhook_server.start()


def stop_webhook_server() -> bool:
    """Detiene el servidor webhook"""
    return _webhook_server.stop()


def is_webhook_server_running() -> bool:
    """Verifica si el servidor webhook está ejecutándose"""
    return _webhook_server.is_running()


def get_webhook_server_status() -> Dict[str, Any]:
    """Obtiene estado del servidor webhook"""
    return _webhook_server.get_status()


def get_webhook_endpoint_url() -> str:
    """Obtiene la URL del endpoint webhook para registro con Google Calendar"""
    from config import WEBHOOK_BASE_URL

    return f"{WEBHOOK_BASE_URL}/webhook/calendar"

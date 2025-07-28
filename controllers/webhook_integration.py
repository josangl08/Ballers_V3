# controllers/webhook_integration.py
"""
Integración completa del sistema de webhooks para Google Calendar.
Combina webhook server + Google Calendar push notifications para sync en tiempo real.
"""
import logging
import threading
import time
from typing import Any, Dict

from controllers.webhook_controller import (
    auto_renew_webhook_if_needed,
    get_webhook_channel_status,
    register_calendar_webhook,
    stop_calendar_webhook,
)
from controllers.webhook_server import (
    get_webhook_endpoint_url,
    is_webhook_server_running,
    start_webhook_server,
    stop_webhook_server,
)

logger = logging.getLogger(__name__)


class WebhookIntegration:
    """
    Controlador principal para integración completa de webhooks.
    Gestiona servidor webhook + Google Calendar push notifications.
    """

    def __init__(self):
        self.webhook_channel = None
        self.auto_renewal_thread = None
        self._stop_renewal = False

    def initialize(self) -> bool:
        """
        Inicializa la integración completa de webhooks.

        Returns:
            True si se inicializó correctamente, False si hay errores
        """
        try:
            logger.info("🚀 Initializing complete webhook integration...")

            # Paso 1: Iniciar servidor webhook
            if not self._initialize_webhook_server():
                return False

            # Paso 2: Registrar channel con Google Calendar
            if not self._register_google_calendar_channel():
                return False

            # Paso 3: Iniciar auto-renewal en background
            self._start_auto_renewal_thread()

            logger.info("✅ Webhook integration initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Error initializing webhook integration: {e}")
            return False

    def _initialize_webhook_server(self) -> bool:
        """Inicializa el servidor webhook Flask."""
        try:
            if is_webhook_server_running():
                logger.info("📡 Webhook server already running")
                return True

            success = start_webhook_server()
            if success:
                logger.info("✅ Webhook server started successfully")
                return True
            else:
                logger.error("❌ Failed to start webhook server")
                return False

        except Exception as e:
            logger.error(f"❌ Error starting webhook server: {e}")
            return False

    def _register_google_calendar_channel(self) -> bool:
        """Registra webhook channel con Google Calendar API con detección automática de entorno."""
        try:
            webhook_url = get_webhook_endpoint_url()
            is_local_dev = "localhost" in webhook_url or "127.0.0.1" in webhook_url

            if is_local_dev:
                logger.info(f"🔧 Development environment detected: {webhook_url}")
                logger.info("📡 Attempting to register webhook with Google Calendar...")
                logger.info(
                    "💡 For full webhook testing, consider using ngrok for HTTPS"
                )
            else:
                logger.info(f"🌍 Production environment detected: {webhook_url}")
                logger.info("📡 Registering webhook channel with Google Calendar...")

            # Intentar registrar channel real con Google Calendar API
            self.webhook_channel = register_calendar_webhook(webhook_url)

            if self.webhook_channel:
                if is_local_dev:
                    logger.info("🎉 ¡Webhook registration successful in development!")
                    logger.info(
                        "✅ Google Calendar will send real-time notifications to localhost"
                    )
                else:
                    logger.info(
                        "✅ Production webhook channel registered successfully!"
                    )

                logger.info(
                    f"📋 Channel Details:\n"
                    f"   Channel ID: {self.webhook_channel.get('id')}\n"
                    f"   Resource ID: {self.webhook_channel.get('resource_id')}\n"
                    f"   Expires: {self.webhook_channel.get('expires_at')}\n"
                    f"   Webhook URL: {webhook_url}"
                )
                return True
            else:
                if is_local_dev:
                    logger.warning(
                        "⚠️ Could not register webhook in development environment"
                    )
                    logger.info("🔄 Webhook server running for manual testing")
                    logger.info("🛠️ You can test webhook endpoint manually:")
                    logger.info(
                        f"   curl -X POST {webhook_url} -H 'Content-Type: application/json'"
                    )

                    # Continuar con servidor webhook activo para testing manual
                    self.webhook_channel = {
                        "id": "dev-server-only",
                        "resource_id": "dev-server-only",
                        "webhook_url": webhook_url,
                        "expires_at": "N/A (development)",
                        "development_mode": True,
                    }
                    return True  # Permitir continuar en modo desarrollo
                else:
                    logger.error("❌ Failed to register webhook channel in production")
                    return False

        except Exception as e:
            webhook_url = get_webhook_endpoint_url()
            is_local_dev = "localhost" in webhook_url or "127.0.0.1" in webhook_url

            if is_local_dev:
                logger.warning(f"⚠️ Webhook registration failed in development: {e}")
                logger.info("🔄 Continuing with webhook server for manual testing")
                logger.info("💡 This is normal for localhost development")

                # Continuar en modo desarrollo
                self.webhook_channel = {
                    "id": "dev-server-only",
                    "resource_id": "dev-server-only",
                    "webhook_url": webhook_url,
                    "expires_at": "N/A (development)",
                    "development_mode": True,
                    "error": str(e),
                }
                return True
            else:
                logger.error(
                    f"❌ Critical error registering webhook in production: {e}"
                )
                return False

    def _start_auto_renewal_thread(self):
        """Inicia thread para auto-renovación de channels (solo en producción)."""
        try:
            # Skip auto-renewal en desarrollo
            if self.webhook_channel and self.webhook_channel.get("development_mode"):
                logger.info("🔧 Development mode: skipping auto-renewal thread")
                return

            if self.auto_renewal_thread and self.auto_renewal_thread.is_alive():
                logger.info("🔄 Auto-renewal thread already running")
                return

            self._stop_renewal = False
            self.auto_renewal_thread = threading.Thread(
                target=self._auto_renewal_loop, daemon=True
            )
            self.auto_renewal_thread.start()

            logger.info("🔄 Auto-renewal thread started for production webhook")

        except Exception as e:
            logger.error(f"❌ Error starting auto-renewal thread: {e}")

    def _auto_renewal_loop(self):
        """Loop para verificar y renovar channels automáticamente."""
        try:
            while not self._stop_renewal:
                try:
                    # Verificar cada 6 horas si necesita renovación
                    time.sleep(6 * 3600)  # 6 horas

                    if self._stop_renewal:
                        break

                    logger.info("🔄 Checking if webhook channel needs renewal...")
                    success = auto_renew_webhook_if_needed()

                    if not success:
                        logger.warning("⚠️ Failed to auto-renew webhook channel")

                except Exception as e:
                    logger.error(f"❌ Error in auto-renewal loop: {e}")
                    time.sleep(3600)  # Esperar 1 hora antes de reintentar

        except Exception as e:
            logger.error(f"❌ Critical error in auto-renewal loop: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        Obtiene estado completo de la integración de webhooks.

        Returns:
            Dict con estado del servidor webhook y channel de Google Calendar
        """
        try:
            # Estado del servidor webhook
            server_running = is_webhook_server_running()
            endpoint_url = get_webhook_endpoint_url() if server_running else None

            # Detectar modo de desarrollo
            is_development = endpoint_url and (
                "localhost" in endpoint_url or "127.0.0.1" in endpoint_url
            )

            # Estado del channel de Google Calendar
            channel_status = get_webhook_channel_status()
            has_real_channel = self.webhook_channel and not self.webhook_channel.get(
                "development_mode", False
            )

            # Estado del thread de auto-renewal
            auto_renewal_active = (
                self.auto_renewal_thread
                and self.auto_renewal_thread.is_alive()
                and not self._stop_renewal
            )

            # Determinar health según el modo
            if is_development:
                # En desarrollo, healthy = servidor webhook running
                integration_healthy = server_running
                capabilities = ["manual_testing", "webhook_endpoint"]
                if has_real_channel:
                    capabilities.append("google_calendar_notifications")
            else:
                # En producción, healthy = todo funcionando
                integration_healthy = (
                    server_running
                    and channel_status.get("active", False)
                    and auto_renewal_active
                )
                capabilities = [
                    "real_time_sync",
                    "google_calendar_notifications",
                    "auto_renewal",
                ]

            return {
                "mode": "development" if is_development else "production",
                "webhook_server": {
                    "running": server_running,
                    "endpoint_url": endpoint_url,
                },
                "google_calendar_channel": {
                    **channel_status,
                    "real_channel": has_real_channel,
                    "development_mode": (
                        self.webhook_channel.get("development_mode", False)
                        if self.webhook_channel
                        else False
                    ),
                },
                "auto_renewal": {
                    "active": auto_renewal_active,
                    "enabled": not is_development,
                    "thread_alive": (
                        self.auto_renewal_thread.is_alive()
                        if self.auto_renewal_thread
                        else False
                    ),
                },
                "integration_healthy": integration_healthy,
                "capabilities": capabilities,
            }

        except Exception as e:
            logger.error(f"❌ Error getting webhook integration status: {e}")
            return {
                "mode": "unknown",
                "webhook_server": {"running": False},
                "google_calendar_channel": {"active": False, "real_channel": False},
                "auto_renewal": {"active": False, "enabled": False},
                "integration_healthy": False,
                "capabilities": [],
                "error": str(e),
            }

    def shutdown(self):
        """Cierra la integración completa de webhooks."""
        try:
            logger.info("🧹 Shutting down webhook integration...")

            # Detener auto-renewal
            self._stop_renewal = True
            if self.auto_renewal_thread:
                logger.info("🔄 Stopping auto-renewal thread...")

            # Detener Google Calendar channel
            if self.webhook_channel:
                logger.info("📡 Stopping Google Calendar webhook channel...")
                stop_calendar_webhook()

            # Detener servidor webhook
            logger.info("🛑 Stopping webhook server...")
            stop_webhook_server()

            logger.info("✅ Webhook integration shut down successfully")

        except Exception as e:
            logger.error(f"❌ Error shutting down webhook integration: {e}")


# Instancia global para integración
_webhook_integration = WebhookIntegration()


# Funciones públicas para integrar con main_dash.py
def initialize_webhook_integration() -> bool:
    """Inicializa la integración completa de webhooks."""
    return _webhook_integration.initialize()


def get_webhook_integration_status() -> Dict[str, Any]:
    """Obtiene estado de la integración de webhooks."""
    return _webhook_integration.get_status()


def shutdown_webhook_integration():
    """Cierra la integración de webhooks."""
    _webhook_integration.shutdown()


def is_webhook_integration_healthy() -> bool:
    """Verifica si la integración está funcionando correctamente."""
    status = get_webhook_integration_status()
    return status.get("integration_healthy", False)

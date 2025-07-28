# controllers/webhook_controller.py
"""
Controlador para manejo de Google Calendar webhook channels.
Gestiona el ciclo de vida de channels: creación, renovación, eliminación.
"""
import datetime as dt
import logging
import uuid
from typing import Dict, Any, Optional

from googleapiclient.errors import HttpError

from config import CALENDAR_ID, WEBHOOK_BASE_URL, WEBHOOK_SECRET_TOKEN
from controllers.google_client import calendar

logger = logging.getLogger(__name__)


class WebhookController:
    """
    Controlador para gestionar channels de webhooks de Google Calendar.
    Maneja registro, renovación y eliminación de channels.
    """
    
    def __init__(self):
        self.calendar_service = None
        self.current_channel = None
        
    def _get_calendar_service(self):
        """Obtiene instancia del servicio de Google Calendar"""
        if not self.calendar_service:
            self.calendar_service = calendar()
        return self.calendar_service
    
    def register_webhook_channel(self, webhook_url: str = None, 
                                 expiration_hours: int = 168) -> Optional[Dict[str, Any]]:
        """
        Registra un nuevo channel de webhook con Google Calendar.
        
        Args:
            webhook_url: URL donde Google enviará los webhooks
            expiration_hours: Horas hasta que expire el channel (default: 7 días)
            
        Returns:
            Channel info si se registra exitosamente, None si falla
        """
        try:
            service = self._get_calendar_service()
            
            # URL base del webhook
            if not webhook_url:
                if WEBHOOK_BASE_URL.startswith('https://localhost'):
                    logger.warning("⚠️ Using localhost webhook URL - only for development!")
                webhook_url = f"{WEBHOOK_BASE_URL}/webhook/calendar"
            
            # Generar ID único para el channel
            channel_id = str(uuid.uuid4())
            
            # Calcular tiempo de expiración
            expiration_time = dt.datetime.now() + dt.timedelta(hours=expiration_hours)
            expiration_ms = int(expiration_time.timestamp() * 1000)
            
            # Configurar channel
            channel_body = {
                "id": channel_id,
                "type": "web_hook", 
                "address": webhook_url,
                "expiration": expiration_ms
            }
            
            # Añadir token de validación si está configurado
            if WEBHOOK_SECRET_TOKEN and WEBHOOK_SECRET_TOKEN != "default-secret-token":
                channel_body["token"] = WEBHOOK_SECRET_TOKEN
            
            logger.info(f"📡 Registering webhook channel: {webhook_url}")
            
            # Registrar channel con Google Calendar
            channel = service.events().watch(
                calendarId=CALENDAR_ID,
                body=channel_body
            ).execute()
            
            # Guardar información del channel
            self.current_channel = {
                "id": channel.get("id"),
                "resource_id": channel.get("resourceId"),
                "expiration": channel.get("expiration"),
                "webhook_url": webhook_url,
                "created_at": dt.datetime.now().isoformat(),
                "expires_at": expiration_time.isoformat()
            }
            
            logger.info(
                f"✅ Webhook channel registered successfully!\n"
                f"   Channel ID: {channel.get('id')}\n"
                f"   Resource ID: {channel.get('resourceId')}\n"
                f"   Expires: {expiration_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"   Webhook URL: {webhook_url}"
            )
            
            return self.current_channel
            
        except HttpError as e:
            logger.error(f"❌ Google Calendar API error registering webhook: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error registering webhook channel: {e}")
            return None
    
    def stop_webhook_channel(self, channel_id: str = None, 
                           resource_id: str = None) -> bool:
        """
        Detiene un channel de webhook activo.
        
        Args:
            channel_id: ID del channel a detener
            resource_id: Resource ID del channel
            
        Returns:
            True si se detiene exitosamente, False si falla
        """
        try:
            service = self._get_calendar_service()
            
            # Usar channel actual si no se especifican parámetros
            if not channel_id and self.current_channel:
                channel_id = self.current_channel.get("id")
                resource_id = self.current_channel.get("resource_id")
            
            if not channel_id or not resource_id:
                logger.warning("No channel ID or resource ID provided for stopping")
                return False
            
            # Detener channel
            service.channels().stop(body={
                "id": channel_id,
                "resourceId": resource_id
            }).execute()
            
            logger.info(f"✅ Webhook channel stopped: {channel_id}")
            
            # Limpiar channel actual si coincide
            if self.current_channel and self.current_channel.get("id") == channel_id:
                self.current_channel = None
            
            return True
            
        except HttpError as e:
            logger.error(f"❌ Google Calendar API error stopping webhook: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error stopping webhook channel: {e}")
            return False
    
    def renew_webhook_channel(self, expiration_hours: int = 168) -> Optional[Dict[str, Any]]:
        """
        Renueva el channel actual creando uno nuevo y eliminando el anterior.
        
        Args:
            expiration_hours: Horas hasta que expire el nuevo channel
            
        Returns:
            Nuevo channel info si se renueva exitosamente, None si falla
        """
        try:
            if not self.current_channel:
                logger.warning("No current channel to renew")
                return None
            
            old_webhook_url = self.current_channel.get("webhook_url")
            old_channel_id = self.current_channel.get("id")
            old_resource_id = self.current_channel.get("resource_id")
            
            # Crear nuevo channel
            new_channel = self.register_webhook_channel(
                webhook_url=old_webhook_url,
                expiration_hours=expiration_hours
            )
            
            if new_channel:
                # Detener channel anterior
                if old_channel_id and old_resource_id:
                    self.stop_webhook_channel(old_channel_id, old_resource_id)
                
                logger.info(f"✅ Webhook channel renewed successfully")
                return new_channel
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error renewing webhook channel: {e}")
            return None
    
    def get_channel_status(self) -> Dict[str, Any]:
        """
        Obtiene estado actual del channel de webhook.
        
        Returns:
            Dict con información del channel
        """
        if not self.current_channel:
            return {
                "active": False,
                "message": "No webhook channel registered"
            }
        
        try:
            # Verificar si el channel ha expirado
            expires_at = dt.datetime.fromisoformat(self.current_channel["expires_at"])
            now = dt.datetime.now()
            
            is_expired = now >= expires_at
            time_until_expiry = expires_at - now
            
            return {
                "active": not is_expired,
                "channel_id": self.current_channel.get("id"),
                "resource_id": self.current_channel.get("resource_id"),
                "webhook_url": self.current_channel.get("webhook_url"),
                "created_at": self.current_channel.get("created_at"),
                "expires_at": self.current_channel.get("expires_at"),
                "expired": is_expired,
                "time_until_expiry_hours": time_until_expiry.total_seconds() / 3600 if not is_expired else 0,
                "needs_renewal": time_until_expiry.total_seconds() < (24 * 3600)  # Menos de 24 horas
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting channel status: {e}")
            return {
                "active": False,
                "error": str(e)
            }
    
    def auto_renew_if_needed(self) -> bool:
        """
        Renueva automáticamente el channel si está próximo a expirar.
        
        Returns:
            True si se renovó o no era necesario, False si falló la renovación
        """
        try:
            status = self.get_channel_status()
            
            if not status.get("active"):
                logger.info("No active channel to renew")
                return True
            
            if status.get("needs_renewal"):
                logger.info("🔄 Channel needs renewal, renewing automatically...")
                result = self.renew_webhook_channel()
                return result is not None
            
            logger.info("✅ Channel does not need renewal yet")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in auto-renewal: {e}")
            return False


# Instancia global del controlador
_webhook_controller = WebhookController()


# Funciones públicas para integración
def register_calendar_webhook(webhook_url: str = None) -> Optional[Dict[str, Any]]:
    """Registra webhook channel con Google Calendar"""
    return _webhook_controller.register_webhook_channel(webhook_url)


def stop_calendar_webhook() -> bool:
    """Detiene el webhook channel activo"""
    return _webhook_controller.stop_webhook_channel()


def get_webhook_channel_status() -> Dict[str, Any]:
    """Obtiene estado del webhook channel"""
    return _webhook_controller.get_channel_status()


def renew_webhook_channel() -> Optional[Dict[str, Any]]:
    """Renueva el webhook channel"""
    return _webhook_controller.renew_webhook_channel()


def auto_renew_webhook_if_needed() -> bool:
    """Auto-renueva el webhook si es necesario"""
    return _webhook_controller.auto_renew_if_needed()
# 📡 Webhook Setup Guide - Real-time Google Calendar Sync

Esta guía explica cómo configurar webhooks para sincronización en tiempo real con Google Calendar en diferentes entornos.

## 🔧 Desarrollo Local

### Estado Actual ✅
- **Webhook server**: Funcionando en `http://localhost:8001`
- **Endpoint**: `/webhook/calendar`
- **Testing manual**: Disponible con `test_webhook.py`

### Limitaciones en Desarrollo
- Google Calendar requiere **HTTPS** para webhooks reales
- Localhost HTTP no puede recibir webhooks de Google
- **Solución**: Testing manual + configuración para producción

### Testing Manual
```bash
# Iniciar aplicación
python main_dash.py

# En otra terminal, probar webhook
python test_webhook.py
```

## 🌍 Transición a Producción

### Opción 1: ngrok (Desarrollo/Testing Rápido)
```bash
# Instalar ngrok
brew install ngrok  # macOS
# o descargar desde https://ngrok.com

# Iniciar túnel HTTPS
ngrok http 8001

# Usar URL HTTPS generada
export WEBHOOK_BASE_URL="https://abc123.ngrok.io"
python main_dash.py
```

### Opción 2: Servidor con SSL (Producción Real)
```bash
# Configurar variables de entorno
export WEBHOOK_BASE_URL="https://tu-dominio.com"
export WEBHOOK_PORT="8001"
export WEBHOOK_SECRET_TOKEN="tu-token-seguro"

# Asegurar certificados SSL configurados
# Nginx/Apache configurado para proxy_pass a :8001
```

### Opción 3: Cloud Deployment (Recomendado)
```bash
# Heroku, Railway, Fly.io, etc.
export WEBHOOK_BASE_URL="${APP_URL}"
export WEBHOOK_PORT="${PORT}"
export WEBHOOK_SECRET_TOKEN="${SECRET_TOKEN}"
```

## 🔄 Configuración por Entorno

### config.py - Variables Automáticas
```python
# Desarrollo - Detectado automáticamente
WEBHOOK_BASE_URL = "http://localhost:8001"

# Producción - Variables de entorno
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://tu-app.com")
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", "token-seguro")
```

### Detección Automática de Entorno
- **Desarrollo**: URL contiene `localhost` o `127.0.0.1`
- **Producción**: URL HTTPS externa

## 📊 Monitoreo y Estado

### Verificar Estado
```python
from controllers.webhook_integration import get_webhook_integration_status
import json

status = get_webhook_integration_status()
print(json.dumps(status, indent=2))
```

### Estados Posibles
```json
{
  "mode": "development|production",
  "webhook_server": {"running": true},
  "google_calendar_channel": {"active": true, "real_channel": true},
  "auto_renewal": {"active": true, "enabled": true},
  "integration_healthy": true,
  "capabilities": ["real_time_sync", "google_calendar_notifications"]
}
```

## 🚀 Flujo de Trabajo Completo

### 1. Desarrollo Local
```bash
git clone proyecto
pip install -r requirements.txt
python main_dash.py  # Webhook server en modo desarrollo
python test_webhook.py  # Probar endpoint manualmente
```

### 2. Testing con ngrok
```bash
ngrok http 8001
export WEBHOOK_BASE_URL="https://abc123.ngrok.io"
python main_dash.py  # Webhook real con Google Calendar
```

### 3. Producción
```bash
# Configurar variables de entorno
# Desplegar aplicación
# Webhook automático en tiempo real
```

## 🔧 Troubleshooting

### Problema: "WebHook callback must be HTTPS"
- **Causa**: localhost HTTP en desarrollo
- **Solución**: Normal en desarrollo, usar ngrok para testing real

### Problema: "Failed to register webhook channel"
- **Verificar**: Credenciales Google Calendar
- **Verificar**: CALENDAR_ID en config
- **Verificar**: Permisos de Service Account

### Problema: "Webhook server failed to start"
- **Verificar**: Puerto 8001 disponible (`lsof -i :8001`)
- **Verificar**: Flask instalado (`pip install flask`)

## 💡 Best Practices

### Seguridad
- Usar `WEBHOOK_SECRET_TOKEN` en producción
- Validar headers de Google Calendar
- HTTPS obligatorio en producción

### Performance
- Webhook processing asíncrono (implementado)
- Auto-renewal de channels (implementado)
- Logging detallado para debugging

### Monitoring
- Health check endpoint: `/health`
- Status endpoint: `/webhook/status`
- Integration status en aplicación

## 📈 Próximos Pasos

1. **✅ STAGE 1-3 COMPLETADOS**: Webhook server + Google Calendar integration
2. **🎯 STAGE 4**: Real-time UI updates vía Server-Sent Events
3. **🎯 STAGE 5**: Enhanced notification system
4. **🎯 STAGE 6**: UI simplification con webhook status
5. **🎯 STAGE 7**: Testing completo + deployment guide

## 📞 Testing en Vivo

### Con tu Google Calendar Conectado:
1. Usar ngrok para obtener HTTPS URL
2. Configurar `WEBHOOK_BASE_URL` con URL de ngrok
3. Reiniciar aplicación
4. Crear/modificar evento en Google Calendar
5. Ver sync en tiempo real en aplicación

¡El sistema está listo para sync en tiempo real! 🚀

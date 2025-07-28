# config.py
import datetime as dt
import json
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Cargar variables de entorno si existe el archivo .env
load_dotenv()

# Configurar logging temprano
from common.logging_config import get_logger, setup_logging

logger = setup_logging()


def get_config_value(key, default=None):
    """
    Obtiene valor de configuración desde múltiples fuentes con debug mejorado.
    """
    # Debug: mostrar qué se está buscando
    debug_logger = get_logger("config.debug")
    if os.getenv("DEBUG") == "True":
        debug_logger.debug("config_lookup", extra={"extra_data": {"key": key}})

    # 1. Intentar obtener desde Streamlit secrets (despliegue)
    try:
        if hasattr(st, "secrets"):
            # Verificar si la key existe directamente en secrets
            if key in st.secrets:
                value = st.secrets[key]
                if os.getenv("DEBUG") == "True":
                    debug_logger.debug(
                        "config_found_in_secrets",
                        extra={
                            "extra_data": {"key": key, "value_preview": str(value)[:50]}
                        },
                    )
                return value

            # Para debug: mostrar todas las keys disponibles
            if os.getenv("DEBUG") == "True":
                try:
                    available_keys = (
                        list(st.secrets.keys()) if hasattr(st.secrets, "keys") else []
                    )
                    print(f"📋 Keys disponibles en secrets: {available_keys}")
                except:
                    print("⚠️ No se pudieron listar las keys de secrets")

    except Exception as e:
        if os.getenv("DEBUG") == "True":
            print(f"⚠️ Error accediendo a st.secrets para {key}: {e}")

    # 2. Intentar obtener desde variables de entorno (local)
    env_value = os.getenv(key, default)
    if env_value != default:
        if os.getenv("DEBUG") == "True":
            print(f"✅ Encontrado en env: {key} = {str(env_value)[:50]}...")
        return env_value

    # 3. Usar valor por defecto
    if os.getenv("DEBUG") == "True":
        print(f"❌ No encontrado {key}, usando default: {default}")

    return default


# Directorios base del proyecto
BASE_DIR = Path(__file__).parent
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
STYLES_DIR = os.path.join(BASE_DIR, "styles")
PROFILE_PHOTOS_DIR = os.path.join(ASSETS_DIR, "profile_photos")

# Crear directorios si no existen
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STYLES_DIR, exist_ok=True)
os.makedirs(PROFILE_PHOTOS_DIR, exist_ok=True)

# Rutas de archivos importantes
DATABASE_PATH = get_config_value(
    "DATABASE_PATH", os.path.join(DATA_DIR, "ballers_app.db")
)
DEFAULT_PROFILE_PHOTO = os.path.join(ASSETS_DIR, "default_profile.png")
CSS_FILE = os.path.join(STYLES_DIR, "style.css")

# Configuración de la aplicación Streamlit
APP_NAME = "Ballers App"
APP_ICON = "assets/ballers/favicon.ico"


# Configuración de Google Services
def get_google_service_account_info():
    """Obtiene información de la cuenta de servicio de Google con debug."""
    try:
        # Para despliegue en Streamlit Cloud
        if hasattr(st, "secrets") and "google" in st.secrets:
            if os.getenv("DEBUG") == "True":
                print("✅ Credenciales Google encontradas en st.secrets")
            return dict(st.secrets["google"])
    except Exception as e:
        if os.getenv("DEBUG") == "True":
            print(f"⚠️ Error obteniendo credenciales Google de secrets: {e}")

    # Para desarrollo local - usar archivo JSON
    google_sa_path = get_config_value("GOOGLE_SA_PATH")
    if google_sa_path and os.path.exists(google_sa_path):
        with open(google_sa_path, "r") as f:
            if os.getenv("DEBUG") == "True":
                print(
                    f"✅ Credenciales Google cargadas desde archivo: {google_sa_path}"
                )
            return json.load(f)

    if os.getenv("DEBUG") == "True":
        print("❌ No se pudieron cargar credenciales de Google")
    return None


# IDs de Google Services con debug
CALENDAR_ID = get_config_value("CALENDAR_ID", "")
ACCOUNTING_SHEET_ID = get_config_value("ACCOUNTING_SHEET_ID", "")

# Debug: verificar IDs críticos
if os.getenv("DEBUG") == "True":
    print(f"📅 CALENDAR_ID configurado: {'✅' if CALENDAR_ID else '❌'}")
    print(
        f"📊 ACCOUNTING_SHEET_ID configurado: {'✅' if ACCOUNTING_SHEET_ID else '❌'}"
    )

# Configuración de la aplicación
DEBUG = get_config_value("DEBUG", "False") == "True"
LOG_LEVEL = get_config_value("LOG_LEVEL", "INFO")
ENVIRONMENT = get_config_value("ENVIRONMENT", "development")

# Lista de tipos de archivos permitidos para fotos de perfil
ALLOWED_PHOTO_EXTENSIONS = ["jpg", "jpeg", "png"]
MAX_PHOTO_SIZE_MB = 2

# Constantes de la aplicación
SESSION_DURATION_DEFAULT = 60  # minutos

# Clave secreta para sesiones
SESSION_SECRET = get_config_value("SESSION_SECRET", "your-default-secret-key")

# Configuración de calendario
CALENDAR_ENABLED = get_config_value("CALENDAR_ENABLED", "True") == "True"

# Configuración de webhook-based sync (future implementation)
WEBHOOK_PORT = int(str(get_config_value("WEBHOOK_PORT", "8001")))
WEBHOOK_SECRET_TOKEN = get_config_value("WEBHOOK_SECRET_TOKEN", "default-secret-token")
WEBHOOK_BASE_URL = get_config_value("WEBHOOK_BASE_URL", "http://localhost:8001")

# Colores para las sesiones (código Google Calendar + color HEX para la UI)
CALENDAR_COLORS = {
    "scheduled": {"google": "9", "hex": "#1E88E5"},  # azul
    "completed": {"google": "2", "hex": "#4CAF50"},  # verde
    "canceled": {"google": "11", "hex": "#F44336"},  # rojo
}

# Horarios para formularios de la app (estrictos)
WORK_HOURS_STRICT = {"start": dt.time(8, 0), "end": dt.time(18, 0)}

# Horarios para imports de Calendar (flexibles)
WORK_HOURS_FLEXIBLE = {"start": dt.time(6, 0), "end": dt.time(22, 0)}

SESSION_DURATION = {
    "min_minutes": 60,
    "max_minutes": 120,  # 2 horas para formularios
    "max_minutes_import": 180,  # 3 horas para imports (antes de rechazar)
}

# Información para logging
if DEBUG:
    print(f"🔧 Configuración cargada:")
    print(f"   - Entorno: {ENVIRONMENT}")
    print(f"   - Base de datos: {DATABASE_PATH}")
    print(
        f"   - Calendar ID: {CALENDAR_ID[:20]}..."
        if CALENDAR_ID
        else "   - Calendar ID: ❌ No configurado"
    )
    print(
        f"   - Sheets ID: {ACCOUNTING_SHEET_ID[:20]}..."
        if ACCOUNTING_SHEET_ID
        else "   - Sheets ID: ❌ No configurado"
    )

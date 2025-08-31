# config.py
import datetime as dt
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from common.logging_config import get_logger, setup_logging

# Cargar variables de entorno si existe el archivo .env
load_dotenv()

logger = setup_logging()


def get_config_value(key, default=None):
    """
    Obtiene valor de configuración desde variables de entorno con debug mejorado.

    Orden de prioridad:
    1. Variables de entorno del sistema
    2. Archivo .env (cargado por dotenv)
    3. Valor por defecto
    """
    # Debug: mostrar qué se está buscando
    debug_logger = get_logger("config.debug")
    if os.getenv("DEBUG") == "True":
        debug_logger.debug("config_lookup", extra={"extra_data": {"key": key}})

    # Obtener desde variables de entorno
    env_value = os.getenv(key, default)
    if env_value != default:
        if os.getenv("DEBUG") == "True":
            debug_logger.debug(
                "config_found_in_env",
                extra={
                    "extra_data": {"key": key, "value_preview": str(env_value)[:50]}
                },
            )
        return env_value

    # Usar valor por defecto
    if os.getenv("DEBUG") == "True":
        debug_logger.debug(
            "config_using_default",
            extra={"extra_data": {"key": key, "default": default}},
        )

    return default


# Directorios base del proyecto
BASE_DIR = Path(__file__).parent
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
PROFILE_PHOTOS_DIR = os.path.join(ASSETS_DIR, "profile_photos")

# Crear directorios si no existen
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PROFILE_PHOTOS_DIR, exist_ok=True)

# Configuración de base de datos dual (SQLite local / PostgreSQL producción)
DATABASE_PATH = get_config_value(
    "DATABASE_PATH", os.path.join(DATA_DIR, "ballers_app.db")
)

# Configuración Supabase para producción
SUPABASE_URL = get_config_value("SUPABASE_URL", "")
SUPABASE_ANON_KEY = get_config_value("SUPABASE_ANON_KEY", "")
SUPABASE_DATABASE_URL = get_config_value("SUPABASE_DATABASE_URL", "")

# Configuración de la aplicación (definir antes de usar en funciones)
DEBUG = get_config_value("DEBUG", "False") == "True"
LOG_LEVEL = get_config_value("LOG_LEVEL", "INFO")
ENVIRONMENT = get_config_value("ENVIRONMENT", "development")
DEFAULT_PROFILE_PHOTO = os.path.join(ASSETS_DIR, "default_profile.png")
CSS_FILE = os.path.join(ASSETS_DIR, "style.css")

# Configuración de la aplicación (Dash)
APP_NAME = "Ballers App"
APP_ICON = "assets/ballers/favicon.ico"


# Configuración de Google Services
def get_google_service_account_from_env_vars():
    """
    Obtiene credenciales de Google Service Account desde variables de entorno individuales.

    Variables requeridas:
    - GOOGLE_PROJECT_ID
    - GOOGLE_PRIVATE_KEY_ID
    - GOOGLE_PRIVATE_KEY
    - GOOGLE_CLIENT_EMAIL
    - GOOGLE_CLIENT_ID
    """
    try:
        project_id = get_config_value("GOOGLE_PROJECT_ID")
        private_key_id = get_config_value("GOOGLE_PRIVATE_KEY_ID")
        private_key = get_config_value("GOOGLE_PRIVATE_KEY")
        client_email = get_config_value("GOOGLE_CLIENT_EMAIL")
        client_id = get_config_value("GOOGLE_CLIENT_ID")

        if all([project_id, private_key_id, private_key, client_email, client_id]):
            # Construir el diccionario de credenciales
            credentials = {
                "type": "service_account",
                "project_id": project_id,
                "private_key_id": private_key_id,
                "private_key": private_key,
                "client_email": client_email,
                "client_id": client_id,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email.replace('@', '%40')}",
                "universe_domain": "googleapis.com",
            }

            if DEBUG:
                logger.info(
                    "✅ Credenciales Google cargadas desde variables de entorno individuales"
                )
            return credentials

    except Exception as e:
        if DEBUG:
            logger.warning(
                f"⚠️ Error obteniendo credenciales desde variables individuales: {e}"
            )

    return None


def get_google_service_account_info():
    """
    Obtiene información de la cuenta de servicio de Google con debug.

    Orden de prioridad:
    1. Variables de entorno individuales (GOOGLE_PROJECT_ID, GOOGLE_PRIVATE_KEY, etc.)
    2. Variables de entorno como JSON string (GOOGLE_SERVICE_ACCOUNT_JSON)
    3. Archivo JSON especificado en GOOGLE_SA_PATH
    4. Archivo por defecto en data/google_service_account.json
    """
    try:
        # 1. Intentar desde variables de entorno individuales (más fácil para producción)
        env_vars_credentials = get_google_service_account_from_env_vars()
        if env_vars_credentials:
            return env_vars_credentials

        # 2. Intentar desde variable de entorno como JSON string
        google_json_str = get_config_value("GOOGLE_SERVICE_ACCOUNT_JSON")
        if google_json_str:
            try:
                credentials = json.loads(google_json_str)
                if DEBUG:
                    logger.info(
                        "✅ Credenciales Google cargadas desde variable de entorno JSON"
                    )
                return credentials
            except json.JSONDecodeError as e:
                if DEBUG:
                    logger.warning(
                        f"⚠️ Error parseando JSON de GOOGLE_SERVICE_ACCOUNT_JSON: {e}"
                    )

        # 3. Intentar desde archivo especificado en GOOGLE_SA_PATH
        google_sa_path = get_config_value("GOOGLE_SA_PATH")
        if google_sa_path and os.path.exists(google_sa_path):
            with open(google_sa_path, "r") as f:
                if DEBUG:
                    logger.info(
                        f"✅ Credenciales Google cargadas desde archivo: {google_sa_path}"
                    )
                return json.load(f)

        # 4. Intentar archivo por defecto
        default_path = os.path.join(DATA_DIR, "google_service_account.json")
        if os.path.exists(default_path):
            with open(default_path, "r") as f:
                if DEBUG:
                    logger.info(
                        f"✅ Credenciales Google cargadas desde archivo por defecto: {default_path}"
                    )
                return json.load(f)

    except Exception as e:
        if DEBUG:
            logger.error(f"⚠️ Error obteniendo credenciales Google: {e}")

    if DEBUG:
        logger.error("❌ No se pudieron cargar credenciales de Google")
    return None


# IDs de Google Services con debug
CALENDAR_ID = get_config_value("CALENDAR_ID", "")
ACCOUNTING_SHEET_ID = get_config_value("ACCOUNTING_SHEET_ID", "")

# Debug: verificar IDs críticos
if DEBUG:
    logger.debug(f"📅 CALENDAR_ID configurado: {'✅' if CALENDAR_ID else '❌'}")
    logger.debug(
        f"📊 ACCOUNTING_SHEET_ID configurado: {'✅' if ACCOUNTING_SHEET_ID else '❌'}"
    )


# Lista de tipos de archivos permitidos para fotos de perfil
ALLOWED_PHOTO_EXTENSIONS = ["jpg", "jpeg", "png"]

# Clave secreta para sesiones
SESSION_SECRET = get_config_value("SESSION_SECRET", "your-default-secret-key")

# Configuración de calendario
CALENDAR_ENABLED = get_config_value("CALENDAR_ENABLED", "True") == "True"


# Configuración webhook para producción Render
def get_webhook_config():
    """
    Configuración webhook adaptativa para desarrollo y producción.

    Desarrollo: localhost con puerto fijo
    Producción: Render con puerto dinámico y HTTPS
    """
    # Puerto dinámico para Render (usa PORT env var)
    port = int(str(get_config_value("PORT", get_config_value("WEBHOOK_PORT", "8001"))))

    # Base URL adaptativa según entorno
    base_url = get_config_value("WEBHOOK_BASE_URL")
    if not base_url:
        if ENVIRONMENT == "production":
            # URL Render desde variable de entorno (más flexible)
            base_url = get_config_value(
                "RENDER_APP_URL", "https://ballers-v3.onrender.com"
            )
        else:
            # Desarrollo local
            base_url = f"http://localhost:{port}"

    return {
        "port": port,
        "base_url": base_url,
        "secret_token": get_config_value(
            "WEBHOOK_SECRET_TOKEN", "default-secret-token"
        ),
    }


# Configuración webhook
_webhook_config = get_webhook_config()
WEBHOOK_PORT = _webhook_config["port"]
WEBHOOK_BASE_URL = _webhook_config["base_url"]
WEBHOOK_SECRET_TOKEN = _webhook_config["secret_token"]

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
    logger.info("🔧 Configuración cargada:")
    logger.info(f"   - Entorno: {ENVIRONMENT}")
    logger.info(f"   - Base de datos: {SUPABASE_DATABASE_URL}")
    if ENVIRONMENT == "production":
        logger.info(
            f"   - Supabase URL: {'✅ Configurado' if SUPABASE_URL else '❌ No configurado'}"
        )
        logger.info(
            f"   - Supabase Key: {'✅ Configurado' if SUPABASE_ANON_KEY else '❌ No configurado'}"
        )
    calendar_status = f"{CALENDAR_ID[:20]}..." if CALENDAR_ID else "❌ No configurado"
    logger.info(f"   - Calendar ID: {calendar_status}")
    sheets_status = (
        f"{ACCOUNTING_SHEET_ID[:20]}..." if ACCOUNTING_SHEET_ID else "❌ No configurado"
    )
    logger.info(f"   - Sheets ID: {sheets_status}")

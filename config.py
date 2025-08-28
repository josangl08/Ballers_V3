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
STYLES_DIR = os.path.join(BASE_DIR, "styles")
PROFILE_PHOTOS_DIR = os.path.join(ASSETS_DIR, "profile_photos")

# Crear directorios si no existen
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STYLES_DIR, exist_ok=True)
os.makedirs(PROFILE_PHOTOS_DIR, exist_ok=True)

# Rutas de archivos importantes
db_path = get_config_value("DATABASE_PATH", os.path.join(DATA_DIR, "ballers_app.db"))
if not os.path.isabs(db_path):
    db_path = os.path.join(BASE_DIR, db_path)
DATABASE_PATH = db_path
DEFAULT_PROFILE_PHOTO = os.path.join(ASSETS_DIR, "default_profile.png")
CSS_FILE = os.path.join(STYLES_DIR, "style.css")

# Configuración de la aplicación (Dash)
APP_NAME = "Ballers App"
APP_ICON = "assets/ballers/favicon.ico"


# Configuración de Google Services
def get_google_service_account_info():
    """
    Obtiene información de la cuenta de servicio de Google con debug.

    Orden de prioridad:
    1. Variables de entorno como JSON string (GOOGLE_SERVICE_ACCOUNT_JSON)
    2. Archivo JSON especificado en GOOGLE_SA_PATH
    3. Archivo por defecto en data/google_service_account.json
    """
    try:
        # 1. Intentar desde variable de entorno como JSON string
        google_json_str = get_config_value("GOOGLE_SERVICE_ACCOUNT_JSON")
        if google_json_str:
            try:
                credentials = json.loads(google_json_str)
                if os.getenv("DEBUG") == "True":
                    print(
                        "✅ Credenciales Google cargadas desde "
                        "variable de entorno JSON"
                    )
                return credentials
            except json.JSONDecodeError as e:
                if os.getenv("DEBUG") == "True":
                    print(
                        f"⚠️ Error parseando JSON de "
                        f"GOOGLE_SERVICE_ACCOUNT_JSON: {e}"
                    )

        # 2. Intentar desde archivo especificado en GOOGLE_SA_PATH
        google_sa_path = get_config_value("GOOGLE_SA_PATH")
        if google_sa_path and os.path.exists(google_sa_path):
            with open(google_sa_path, "r") as f:
                if os.getenv("DEBUG") == "True":
                    print(
                        f"✅ Credenciales Google cargadas desde "
                        f"archivo: {google_sa_path}"
                    )
                return json.load(f)

        # 3. Intentar archivo por defecto
        default_path = os.path.join(DATA_DIR, "google_service_account.json")
        if os.path.exists(default_path):
            with open(default_path, "r") as f:
                if os.getenv("DEBUG") == "True":
                    print(
                        f"✅ Credenciales Google cargadas desde "
                        f"archivo por defecto: {default_path}"
                    )
                return json.load(f)

    except Exception as e:
        if os.getenv("DEBUG") == "True":
            print(f"⚠️ Error obteniendo credenciales Google: {e}")

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
    print("🔧 Configuración cargada:")
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

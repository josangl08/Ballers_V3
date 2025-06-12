# config.py
import os
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
import datetime as dt

# Cargar variables de entorno si existe el archivo .env
load_dotenv()

def get_config_value(key, default=None):
    """
    Obtiene valor de configuración desde múltiples fuentes:
    1. Streamlit secrets (para despliegue)
    2. Variables de entorno (para local)
    3. Valor por defecto
    """
    # Intentar obtener desde Streamlit secrets (despliegue)
    try:
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except:
        pass
    
    # Intentar obtener desde variables de entorno (local)
    return os.getenv(key, default)

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
DATABASE_PATH = get_config_value("DATABASE_PATH", os.path.join(DATA_DIR, "ballers_app.db"))
DEFAULT_PROFILE_PHOTO = os.path.join(ASSETS_DIR, "default_profile.png")
CSS_FILE = os.path.join(STYLES_DIR, "style.css")

# Configuración de la aplicación Streamlit
APP_NAME = "Ballers App"
APP_ICON = "assets/ballers/favicon.ico"

# Configuración de Google Services
def get_google_service_account_info():
    """Obtiene información de la cuenta de servicio de Google."""
    try:
        # Para despliegue en Streamlit Cloud
        if hasattr(st, 'secrets') and 'google' in st.secrets:
            return dict(st.secrets['google'])
    except:
        pass
    
    # Para desarrollo local - usar archivo JSON
    google_sa_path = get_config_value("GOOGLE_SA_PATH")
    if google_sa_path and os.path.exists(google_sa_path):
        import json
        with open(google_sa_path, 'r') as f:
            return json.load(f)
    
    return None

# IDs de Google Services
CALENDAR_ID = get_config_value("CALENDAR_ID", "")
ACCOUNTING_SHEET_ID = get_config_value("ACCOUNTING_SHEET_ID", "")

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

# Configuración de auto-sync
AUTO_SYNC_DEFAULT_INTERVAL = int(str(get_config_value("AUTO_SYNC_DEFAULT_INTERVAL", "10")))
AUTO_SYNC_AUTO_START = get_config_value("AUTO_SYNC_AUTO_START", "False") == "True"

# Colores para las sesiones (código Google Calendar + color HEX para la UI)
CALENDAR_COLORS = {
    "scheduled": {"google": "9",  "hex": "#1E88E5"},  # azul
    "completed": {"google": "2",  "hex": "#4CAF50"},  # verde
    "canceled":  {"google": "11", "hex": "#F44336"},  # rojo
}

# Horarios para formularios de la app (estrictos)
WORK_HOURS_STRICT = {
    "start": dt.time(8, 0),
    "end": dt.time(18, 0)
}

# Horarios para imports de Calendar (flexibles)
WORK_HOURS_FLEXIBLE = {
    "start": dt.time(6, 0),
    "end": dt.time(22, 0)
}

SESSION_DURATION = {
    "min_minutes": 60,
    "max_minutes": 120,  # 2 horas para formularios
    "max_minutes_import": 180  # 3 horas para imports (antes de rechazar)
}

# Información para logging
if DEBUG:
    print(f"🔧 Configuración cargada:")
    print(f"   - Entorno: {ENVIRONMENT}")
    print(f"   - Base de datos: {DATABASE_PATH}")
    print(f"   - Calendar ID: {CALENDAR_ID[:20]}..." if CALENDAR_ID else "   - Calendar ID: No configurado")
    print(f"   - Sheets ID: {ACCOUNTING_SHEET_ID[:20]}..." if ACCOUNTING_SHEET_ID else "   - Sheets ID: No configurado")
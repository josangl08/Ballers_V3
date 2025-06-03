# config.py
import os
from dotenv import load_dotenv
from pathlib import Path
import datetime as dt

# Cargar variables de entorno si existe el archivo .env
load_dotenv()

# Directorios base del proyecto
BASE_DIR = Path(__file__).parent
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
STYLES_DIR = os.path.join(BASE_DIR, "styles")  # Cambio: styles en la raíz
PROFILE_PHOTOS_DIR = os.path.join(ASSETS_DIR, "profile_photos")

# Crear directorios si no existen
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STYLES_DIR, exist_ok=True)
os.makedirs(PROFILE_PHOTOS_DIR, exist_ok=True)

# Rutas de archivos importantes
DATABASE_PATH = os.path.join(DATA_DIR, "ballers_app.db")
DEFAULT_PROFILE_PHOTO = os.path.join(ASSETS_DIR, "default_profile.png")
CSS_FILE = os.path.join(STYLES_DIR, "style.css")  # Añadido: ruta completa al CSS

# Configuración de la aplicación Streamlit
APP_NAME = "Ballers App"
APP_ICON = "assets/ballers/isotipo_white.png"  # Cambiado a ruta relativa

# API Keys y configuraciones externas (desde variables de entorno)
CALENDAR_API_KEY = os.getenv("CALENDAR_API_KEY", "")
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY", "")

# Configuración de la aplicación
DEBUG = os.getenv("DEBUG", "False") == "True"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Lista de tipos de archivos permitidos para fotos de perfil
ALLOWED_PHOTO_EXTENSIONS = ["jpg", "jpeg", "png"]
MAX_PHOTO_SIZE_MB = 2

# Contantes de la aplicación
SESSION_DURATION_DEFAULT = 60  # minutos

# Clave secreta para sesiones
SESSION_SECRET = os.getenv("SESSION_SECRET", "your-default-secret-key")

# Colores para las sesiones (código Google Calendar + color HEX para la UI)
CALENDAR_COLORS = {
    "scheduled": {"google": "9",  "hex": "#1E88E5"},  # azul
    "completed": {"google": "2",  "hex": "#4CAF50"},  # verde
    "canceled":  {"google": "11", "hex": "#F44336"},  # rojo
}
# Configuración de horarios 
WORK_HOURS = {
    "start": dt.time(8, 0),
    "end": dt.time(18, 0)
}

SESSION_DURATION = {
    "min_minutes": 60,
    "max_minutes": 120  # 4 horas
}
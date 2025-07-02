# controllers/google_client.py
import os

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from config import get_google_service_account_info

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


def _creds():
    """Obtiene credenciales de Google Service Account desde múltiples fuentes."""
    # Opción 1: Información desde secrets/config (para despliegue)
    service_account_info = get_google_service_account_info()
    if service_account_info:
        return Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )

    # Opción 2: Archivo JSON (para desarrollo local)
    google_sa_path = os.getenv("GOOGLE_SA_PATH")
    if google_sa_path and os.path.exists(google_sa_path):
        return Credentials.from_service_account_file(google_sa_path, scopes=SCOPES)

    # Si no hay credenciales disponibles
    raise ValueError(
        "No se pudieron cargar las credenciales de Google Service Account. "
        "Verifica que GOOGLE_SA_PATH esté configurado o que los secrets de Streamlit estén disponibles."
    )


def calendar():
    """Crea cliente de Google Calendar."""
    try:
        return build("calendar", "v3", credentials=_creds(), cache_discovery=False)
    except Exception as e:
        print(f"⚠️ Error creando cliente de Google Calendar: {e}")
        raise


def sheets():
    """Crea cliente de Google Sheets."""
    try:
        return build("sheets", "v4", credentials=_creds(), cache_discovery=False)
    except Exception as e:
        print(f"⚠️ Error creando cliente de Google Sheets: {e}")
        raise

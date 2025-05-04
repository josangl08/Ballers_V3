from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import os

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

def _creds():
    return Credentials.from_service_account_file(
        os.getenv("GOOGLE_SA_PATH"), scopes=SCOPES
    )

def calendar():
    return build("calendar", "v3", credentials=_creds(), cache_discovery=False)

def sheets():
    return build("sheets", "v4", credentials=_creds(), cache_discovery=False)

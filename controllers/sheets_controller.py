import os
import pandas as pd
import streamlit as st
from .google_client import sheets

SHEET_ID = os.getenv("ACCOUNTING_SHEET_ID")

@st.cache_data(ttl=300)                      # se actualiza cada 5 min
def get_accounting_df():
    rng = "Hoja 1!A:G"                # cambia si tu pestaña se llama distinto
    data = sheets().spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=rng
    ).execute().get("values", [])
    df = pd.DataFrame(data[1:], columns=data[0])
    for col in ("Ingresos", "Gastos"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

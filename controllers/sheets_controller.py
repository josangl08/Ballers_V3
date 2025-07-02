import os

import pandas as pd
import streamlit as st

from config import get_config_value

from .google_client import sheets

# Usar la función unificada para obtener el Sheet ID
SHEET_ID = get_config_value("ACCOUNTING_SHEET_ID")


@st.cache_data(ttl=300)  # se actualiza cada 5 min
def get_accounting_df():
    """
    Obtiene datos de Google Sheets con manejo de errores mejorado.
    """
    if not SHEET_ID:
        st.error("❌ ACCOUNTING_SHEET_ID no está configurado")
        st.info("💡 Verifica que esté configurado en .streamlit/secrets.toml")
        return pd.DataFrame()  # Devolver DataFrame vacío

    try:
        rng = "Hoja 1!A:G"  # cambia si tu pestaña se llama distinto
        data = (
            sheets()
            .spreadsheets()
            .values()
            .get(spreadsheetId=SHEET_ID, range=rng)
            .execute()
            .get("values", [])
        )

        if not data:
            st.warning("⚠️ No se encontraron datos en Google Sheets")
            return pd.DataFrame()

        if len(data) < 2:
            st.warning(
                "⚠️ Google Sheets no tiene suficientes datos (necesita al menos encabezados + 1 fila)"
            )
            return pd.DataFrame()

        # Crear DataFrame
        df = pd.DataFrame(data[1:], columns=data[0])

        # Convertir columnas numéricas
        for col in ("Ingresos", "Gastos"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            else:
                st.warning(f"⚠️ Columna '{col}' no encontrada en Google Sheets")
                df[col] = 0  # Crear columna con valores 0

        return df

    except Exception as e:
        st.error(f"❌ Error accediendo a Google Sheets: {str(e)}")
        st.info("💡 Posibles soluciones:")
        st.info("1. Verificar que ACCOUNTING_SHEET_ID esté configurado correctamente")
        st.info(
            "2. Verificar que la cuenta de servicio tenga permisos de lectura en el Sheet"
        )
        st.info("3. Verificar que Google Sheets API esté habilitada")

        # Devolver DataFrame de ejemplo para que no se rompa la app
        return pd.DataFrame(
            {
                "Fecha": ["2024-01-01"],
                "Descripción": ["Error de conexión"],
                "Ingresos": [0],
                "Gastos": [0],
            }
        )


def check_sheets_configuration():
    """
    Función helper para verificar la configuración de Sheets.
    Útil para debugging.
    """
    config_info = {
        "SHEET_ID": SHEET_ID,
        "SHEET_ID_Length": len(SHEET_ID) if SHEET_ID else 0,
        "Has_Google_Credentials": bool(get_config_value("client_email")),
    }

    return config_info

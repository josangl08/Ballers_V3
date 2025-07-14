# main_dash.py - Aplicación principal migrada de Streamlit a Dash
import logging
import os

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from callbacks.administration_callbacks import register_administration_callbacks

# Importar callbacks organizados
from callbacks.navigation_callbacks import register_navigation_callbacks
from callbacks.player_callbacks import register_player_callbacks
from callbacks.settings_callbacks import register_settings_callbacks
from callbacks.sidebar_callbacks import register_sidebar_callbacks
from common.login_dash import register_login_callbacks
from common.menu_dash import register_menu_callbacks

# Importar configuración
from config import APP_NAME, APP_ICON
from controllers.db import initialize_database

# Configuración de la aplicación Dash
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css",
    ],
    suppress_callback_exceptions=True,
    assets_folder="assets",
)
app.title = APP_NAME
server = app.server


def get_app_layout():
    """Retorna el layout principal de la aplicación Dash."""
    return dbc.Container(
        [
            dcc.Location(id="url", refresh=False),
            dcc.Store(id="session-store", storage_type="session"),
            # Layout principal
            html.Div(id="main-content"),
        ],
        fluid=True,
    )


# Layout principal de la aplicación
app.layout = get_app_layout()


# Registrar todos los callbacks organizados
def register_all_callbacks():
    """Registra todos los callbacks de la aplicación."""
    # register_auth_callbacks(app)  # Deshabilitado - usando login_dash.py callbacks
    register_login_callbacks(app)  # Callbacks de login con pausa
    register_menu_callbacks(app)  # Callbacks del menú y logout
    register_navigation_callbacks(app)
    register_player_callbacks(app)
    register_administration_callbacks(app)
    register_settings_callbacks(app)
    register_sidebar_callbacks(app)
    
    # Registrar callbacks específicos de páginas
    from pages.ballers_dash import register_ballers_callbacks
    register_ballers_callbacks(app)


def initialize_dash_app():
    """Inicializa la aplicación Dash."""
    # Configurar nivel de logging basado en variable de entorno
    DEBUG_MODE = os.getenv("DEBUG", "False") == "True"

    if DEBUG_MODE:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        print("🔧 DEBUG MODE ENABLED - Verbose logging active")
    else:
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )

    # Registrar callbacks
    register_all_callbacks()

    return app


if __name__ == "__main__":
    app = initialize_dash_app()

    print("🚀 Starting Ballers Dash Application...")
    print("📊 Visit: http://127.0.0.1:8050")

    app.run(debug=True, host="127.0.0.1", port=8050)

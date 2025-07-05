# main_dash.py - Aplicación principal migrada de Streamlit a Dash
import logging
import os

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc

# Importar configuración
from config import APP_ICON, APP_NAME
from controllers.db import initialize_database

# Importar callbacks organizados
from callbacks.auth_callbacks import register_auth_callbacks
from callbacks.navigation_callbacks import register_navigation_callbacks
from callbacks.player_callbacks import register_player_callbacks

# Configuración de la aplicación Dash
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP, 
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css"
    ],
    suppress_callback_exceptions=True,
    assets_folder="assets"
)
app.title = APP_NAME
server = app.server


def get_app_layout():
    """Retorna el layout principal de la aplicación Dash."""
    return dbc.Container([
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="session-store", storage_type="session"),
        
        # Layout principal
        html.Div(id="main-content")
    ], fluid=True)


# Layout principal de la aplicación
app.layout = get_app_layout()


# Registrar todos los callbacks organizados
def register_all_callbacks():
    """Registra todos los callbacks de la aplicación."""
    register_auth_callbacks(app)
    register_navigation_callbacks(app)
    register_player_callbacks(app)


# Función de inicialización
@app.callback(
    Output("main-content", "children"),
    [Input("url", "pathname")],
    [State("session-store", "data")]
)
def display_page(pathname, session_data):
    """Maneja la navegación y muestra el contenido apropiado."""
    
    # Configurar logging
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
    
    # Inicializar base de datos
    try:
        if not initialize_database():
            return dbc.Alert([
                "❌ Critical error: Failed to initialise database",
                html.Br(),
                "💡 Suggested solutions:",
                html.Br(),
                "1. Run `python data/check_database.py` to diagnose",
                html.Br(),
                "2. Verify write permissions on the `data/` folder",
                html.Br(),
                "3. Run `python data/seed_database.py` to recreate the database"
            ], color="danger")
    except Exception as e:
        return dbc.Alert(f"❌ Error initializing application: {str(e)}", color="danger")

    # Verificar sesión activa
    with AuthController() as auth:
        # Intentar restaurar sesión desde URL si no hay sesión activa
        if not auth.is_logged_in():
            success, message = auth.restore_session_from_url()
            if success:
                print(f"Auto-login: {message}")

        has_session = auth.is_logged_in()

    # Si no hay sesión, mostrar página de login
    if not has_session:
        return login_page_dash()
    
    # Si hay sesión, mostrar layout con sidebar y contenido (migrado de Streamlit)
    return html.Div([
        dbc.Row([
            # Sidebar
            dbc.Col([
                create_sidebar_menu_dash()
            ], width=3, className="p-0"),
            
            # Contenido principal
            dbc.Col([
                dbc.Container([
                    # Logo centrado (migrado de main.py Streamlit)
                    dbc.Row([
                        dbc.Col([
                            html.Img(
                                src="/assets/ballers/logo_white.png",
                                style={
                                    "width": "400px", 
                                    "display": "block", 
                                    "margin": "0 auto 20px auto",
                                    "pointer-events": "none"
                                }
                            )
                        ], width=12, className="text-center")
                    ]),
                    
                    # Contenido dinámico (con contenido por defecto)
                    html.Div(id="dynamic-content", children=[
                        html.H3("🏀 Welcome to Ballers", 
                               style={"color": "rgba(36, 222, 132, 1)", "text-align": "center"}),
                        html.P("Select a section from the menu to get started.", 
                              className="text-center text-muted")
                    ])
                ], fluid=True)
            ], width=9)
        ], className="g-0")
    ], style={"background-color": "rgba(0, 0, 0, 0.2)", "min-height": "100vh"})


# Callback para cargar contenido dinámico según la navegación
@app.callback(
    Output("dynamic-content", "children"),
    [Input("selected-menu-item", "data")],
    prevent_initial_call=False
)
def load_dynamic_content(selected_section):
    """Carga contenido dinámico según la sección seleccionada del menú."""
    if not selected_section:
        selected_section = "Ballers"  # Sección por defecto
    
    print(f"DEBUG: Loading content for section: {selected_section}")
    
    try:
        # Obtener la ruta del módulo para la sección seleccionada
        content_module_path = get_content_path_dash(selected_section)
        
        if content_module_path:
            # Importar dinámicamente el módulo de contenido
            try:
                if content_module_path == "pages.ballers":
                    from pages.ballers_dash import show_ballers_content_dash
                    return show_ballers_content_dash()
                elif content_module_path == "pages.administration":
                    from pages.administration_dash import show_administration_content_dash
                    return show_administration_content_dash()
                elif content_module_path == "pages.settings":
                    from pages.settings_dash import show_settings_content_dash
                    return show_settings_content_dash()
                else:
                    return html.Div([
                        html.H3(f"📄 {selected_section}", style={"color": "rgba(36, 222, 132, 1)"}),
                        html.P("Esta sección está en desarrollo."),
                        dbc.Alert("Contenido disponible próximamente.", color="info")
                    ])
            except ImportError as e:
                return html.Div([
                    html.H3("❌ Import Error", style={"color": "rgba(36, 222, 132, 1)"}),
                    dbc.Alert(f"Error importing module {content_module_path}: {str(e)}", color="danger")
                ])
        else:
            return html.Div([
                html.H3("⚠️ Sección no encontrada", style={"color": "rgba(36, 222, 132, 1)"}),
                dbc.Alert("La sección seleccionada no está disponible.", color="warning")
            ])
            
    except Exception as e:
        return html.Div([
            html.H3("❌ Error", style={"color": "rgba(36, 222, 132, 1)"}),
            dbc.Alert(f"Error al cargar el contenido: {str(e)}", color="danger")
        ])


# Callbacks centralizados para evitar problemas de registro
@app.callback(
    [Output("login-alert", "children"),
     Output("login-alert", "color"),
     Output("login-alert", "is_open"),
     Output("username-input", "value"),
     Output("password-input", "value"),
     Output("url", "pathname")],
    [Input("login-button", "n_clicks")],
    [State("username-input", "value"),
     State("password-input", "value"),
     State("remember-me", "value")],
    prevent_initial_call=True
)
def handle_login_callback(n_clicks, username, password, remember_me):
    """Callback de login centralizado."""
    from dash import no_update
    from controllers.auth_controller import authenticate_user, create_user_session
    
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update, no_update
    
    if not username or not password:
        return "Please enter both username and password.", "danger", True, no_update, no_update, no_update
    
    success, message, user = authenticate_user(username, password)
    
    if success and user is not None:
        remember = "remember" in (remember_me or [])
        create_user_session(user, remember)
        return message, "success", True, "", "", "/"
    else:
        return message, "danger", True, no_update, no_update, no_update


@app.callback(
    Output("recovery-panel", "is_open"),
    [Input("forgot-password-button", "n_clicks"),
     Input("cancel-recovery-button", "n_clicks")],
    [State("recovery-panel", "is_open")],
    prevent_initial_call=True
)
def toggle_recovery_panel_callback(forgot_clicks, cancel_clicks, is_open):
    """Callback para panel de recuperación."""
    if forgot_clicks or cancel_clicks:
        return not is_open
    return is_open


@app.callback(
    Output("selected-menu-item", "data"),
    [Input("menu-ballers", "n_clicks"),
     Input("menu-administration", "n_clicks"),
     Input("menu-settings", "n_clicks")],
    prevent_initial_call=True
)
def update_selected_menu_item_callback(ballers_clicks, admin_clicks, settings_clicks):
    """Callback para navegación del menú con IDs simples."""
    from dash import callback_context, no_update
    
    if not callback_context.triggered:
        return no_update
    
    # Obtener el ID del elemento que fue clickeado
    trigger_id = callback_context.triggered[0]['prop_id'].split('.')[0]
    
    # Mapear IDs a nombres de sección
    if trigger_id == "menu-ballers":
        print("DEBUG: Menu clicked: Ballers")
        return "Ballers"
    elif trigger_id == "menu-administration":
        print("DEBUG: Menu clicked: Administration")
        return "Administration"
    elif trigger_id == "menu-settings":
        print("DEBUG: Menu clicked: Settings")
        return "Settings"
    
    return no_update


@app.callback(
    Output("url", "pathname", allow_duplicate=True),
    [Input("logout-button", "n_clicks")],
    prevent_initial_call=True
)
def handle_logout_callback(n_clicks):
    """Callback para logout."""
    if n_clicks:
        from controllers.auth_controller import clear_user_session
        clear_user_session(show_message=False)  # No usar streamlit message en Dash
        return "/"  # Redirigir para recargar la página
    return "/"


@app.callback(
    Output("selected-player-id", "data"),
    [Input("back-to-list-btn", "n_clicks")],
    [State("selected-player-id", "data")],
    prevent_initial_call=True
)
def handle_back_to_list_callback(back_clicks, current_selection):
    """Callback para el botón de vuelta a la lista."""
    from dash import no_update
    
    if back_clicks:
        print("DEBUG: Back to list clicked")
        return None
    
    return no_update


# Callback universal para capturar todos los botones View Profile
@app.callback(
    Output("selected-player-id", "data", allow_duplicate=True),
    [Input({'type': 'view-profile-button', 'index': ALL}, 'n_clicks')],
    [State("selected-player-id", "data")],
    prevent_initial_call=True
)
def handle_view_profile_universal_callback(n_clicks_list, current_selection):
    """Callback universal para manejar todos los botones View Profile."""
    from dash import callback_context, no_update
    
    if not callback_context.triggered:
        return no_update
    
    # Verificar si algún botón fue presionado
    if not any(n_clicks_list or []):
        return no_update
    
    trigger_id = callback_context.triggered[0]['prop_id']
    print(f"DEBUG: Universal view profile trigger: {trigger_id}")
    
    # Parsear el trigger para obtener el player_id
    try:
        if 'view-profile-button' in trigger_id:
            # Patrón complejo: {"index":"player_id","type":"view-profile-button"}
            import json
            trigger_data = json.loads(trigger_id.split('.')[0])
            player_id = trigger_data['index']
            print(f"DEBUG: Navigating to player (complex): {player_id}")
            return player_id
        elif 'view-profile-' in trigger_id:
            # Patrón simple: view-profile-{player_id}
            player_id = trigger_id.split('view-profile-')[1].split('.')[0]
            print(f"DEBUG: Navigating to player (simple): {player_id}")
            return player_id
    except Exception as e:
        print(f"DEBUG: Error parsing view profile trigger: {e}")
    
    return no_update


@app.callback(
    Output("user-type-store", "data"),
    [Input("url", "pathname")],
    prevent_initial_call=False
)
def get_user_type_callback(pathname):
    """Obtiene el tipo de usuario de la sesión."""
    from controllers.auth_controller import AuthController
    
    try:
        with AuthController() as auth:
            if auth.is_logged_in():
                user_data = auth.get_current_user_data()
                return user_data.get("user_type", "player") if user_data else "player"
    except:
        pass
    return "player"


@app.callback(
    Output("ballers-user-content", "children"),
    [Input("user-type-store", "data"),
     Input("selected-player-id", "data")]
)
def update_ballers_content_callback(user_type, selected_player_id):
    """Actualiza contenido de Ballers según tipo de usuario y selección."""
    from pages.ballers_dash import create_player_profile_dash, create_players_list_dash
    from dash import no_update
    
    # Si es un jugador, mostrar su propio perfil
    if user_type == "player":
        return create_player_profile_dash()
    
    # Si es coach o admin
    elif user_type in ["coach", "admin"]:
        if selected_player_id:
            # Mostrar perfil del jugador seleccionado con botón de vuelta
            return html.Div([
                dbc.Button(
                    "← Back to list",
                    id="back-to-list-btn",
                    color="secondary",
                    className="mb-3"
                ),
                create_player_profile_dash(selected_player_id)
            ])
        else:
            # Mostrar lista de jugadores
            return create_players_list_dash()
    else:
        return dbc.Alert("No tienes permisos para acceder a esta sección.", color="danger")


# Callbacks adicionales para las páginas
@app.callback(
    Output("admin-user-content", "children"),
    [Input("admin-user-type-store", "data")],
    prevent_initial_call=False
)
def update_admin_content(user_type):
    """Actualiza contenido de Administration según el tipo de usuario."""
    from pages.administration_dash import create_administration_dashboard_dash
    return create_administration_dashboard_dash()


@app.callback(
    Output("settings-main-content", "children"),
    [Input("settings-main-tabs", "active_tab")],
    prevent_initial_call=False
)
def update_settings_main_content(active_tab):
    """Actualiza contenido principal de Settings según la pestaña activa."""
    from pages.settings_dash import create_sync_settings_dash
    
    if active_tab == "system-tab":
        return create_sync_settings_dash()
    elif active_tab == "users-tab":
        # Users tab con 4 subtabs exactamente como en el original
        return html.Div([
            dbc.Tabs([
                dbc.Tab(
                    label="➕ Create User",
                    tab_id="create-user",
                    active_label_style={"color": "rgba(36, 222, 132, 1)"}
                ),
                dbc.Tab(
                    label="✏️ Edit User",
                    tab_id="edit-user",
                    active_label_style={"color": "rgba(36, 222, 132, 1)"}
                ),
                dbc.Tab(
                    label="🗑️ Delete User",
                    tab_id="delete-user",
                    active_label_style={"color": "rgba(36, 222, 132, 1)"}
                ),
                dbc.Tab(
                    label="📊 User Status",
                    tab_id="user-status",
                    active_label_style={"color": "rgba(36, 222, 132, 1)"}
                )
            ], id="users-subtabs", active_tab="create-user"),
            
            # Contenido de las subtabs
            html.Div(id="users-subtab-content", className="mt-4")
        ])
    else:
        return html.Div("Select a tab to view content")


@app.callback(
    Output("users-subtab-content", "children"),
    [Input("users-subtabs", "active_tab")],
    prevent_initial_call=False
)
def update_users_subtab_content(active_subtab):
    """Actualiza contenido de las subtabs de Users."""
    from pages.settings_dash import create_user_form_dash, create_users_list_dash
    
    if active_subtab == "create-user":
        return create_user_form_dash()
    elif active_subtab == "edit-user":
        return html.Div([
            html.H4("✏️ Edit User", style={"color": "rgba(36, 222, 132, 1)"}),
            create_users_list_dash()
        ])
    elif active_subtab == "delete-user":
        return html.Div([
            html.H4("🗑️ Delete User", style={"color": "rgba(36, 222, 132, 1)"}),
            dbc.Alert("Select users from the list to delete", color="warning"),
            create_users_list_dash()
        ])
    elif active_subtab == "user-status":
        return html.Div([
            html.H4("📊 User Status", style={"color": "rgba(36, 222, 132, 1)"}),
            dbc.Alert("User activity and status overview", color="info"),
            create_users_list_dash()
        ])
    else:
        return html.Div("Select a subtab to view content")


# Callbacks para Administration
@app.callback(
    [Output("admin-calendar-view", "children"),
     Output("admin-sessions-table", "children")],
    [Input("admin-apply-filters-btn", "n_clicks")],
    [State("admin-filter-date-start", "value"),
     State("admin-filter-date-end", "value"),
     State("admin-filter-status", "value"),
     State("admin-filter-coach", "value")],
    prevent_initial_call=False
)
def update_admin_sessions_content(n_clicks, start_date, end_date, status, coach):
    """Actualiza el contenido de sesiones en Administration."""
    # Calendario placeholder
    calendar_content = dbc.Alert("📅 Integrated calendar view - To be implemented with real session data", color="info")
    
    # Tabla de sesiones placeholder
    sessions_table = dbc.Alert("📋 Sessions table with filtering - To be implemented with SessionController", color="info")
    
    return calendar_content, sessions_table


# Callback para cargar opciones dinámicas de coaches y players
@app.callback(
    [Output("new-session-coach", "options"),
     Output("new-session-players", "options"),
     Output("admin-filter-coach", "options")],
    [Input("url", "pathname")],
    prevent_initial_call=False
)
def load_session_form_options(pathname):
    """Carga opciones dinámicas para formularios de sesiones."""
    # Placeholder options - deberían venir de controllers
    coach_options = [
        {"label": "Coach 1", "value": "coach1"},
        {"label": "Coach 2", "value": "coach2"}
    ]
    
    player_options = [
        {"label": "Player 1", "value": "player1"},
        {"label": "Player 2", "value": "player2"}
    ]
    
    filter_coach_options = [{"label": "All Coaches", "value": "all"}] + coach_options
    
    return coach_options, player_options, filter_coach_options


# Función simplificada para registro
def register_callbacks():
    """Los callbacks ya están definidos arriba."""
    pass


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
    
    return app


if __name__ == "__main__":
    app = initialize_dash_app()
    
    # Registrar todos los callbacks manteniendo separación de responsabilidades
    register_callbacks()
    
    app.run(debug=True, host="127.0.0.1", port=8050)

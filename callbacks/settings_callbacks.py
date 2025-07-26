# callbacks/settings_callbacks.py
"""
Callbacks relacionados con la página de Settings.
"""
import datetime as dt
import base64
import os
from typing import Dict, List, Optional

import dash_bootstrap_components as dbc
import pandas as pd
import dash
from dash import Input, Output, State, callback_context, html, no_update

from controllers.user_controller import (
    UserController,
    create_user_simple,
    delete_user_simple,
    get_user_with_profile,
    get_users_for_management,
    update_user_simple,
)
from controllers.validation_controller import ValidationController


def process_dash_upload(contents: str, filename: str = None) -> object:
    """
    Procesa un archivo subido desde Dash y lo convierte al formato que espera UserController.
    
    Args:
        contents: String base64 con formato "data:image/png;base64,<contenido>"
        filename: Nombre del archivo (opcional)
    
    Returns:
        Objeto que simula el uploaded_file de Streamlit
    """
    if not contents:
        return None
        
    # Extraer el contenido base64
    content_type, content_string = contents.split(',')
    
    # Decodificar base64
    decoded = base64.b64decode(content_string)
    
    # Determinar extensión desde content_type o usar por defecto
    if 'image/jpeg' in content_type:
        ext = '.jpg'
    elif 'image/png' in content_type:
        ext = '.png'
    elif 'image/gif' in content_type:
        ext = '.gif'
    else:
        ext = '.jpg'  # Por defecto
    
    # Crear objeto que simula uploaded_file de Streamlit
    class DashUploadedFile:
        def __init__(self, content, filename):
            self._content = content
            self.name = filename or f"profile{ext}"
            
        def getbuffer(self):
            return self._content
    
    return DashUploadedFile(decoded, filename or f"profile{ext}")


def save_profile_photo_dash(contents: str, username: str, filename: str = None) -> str:
    """
    Guarda una foto de perfil desde Dash upload.
    
    Args:
        contents: String base64 con formato "data:image/png;base64,<contenido>"
        username: Nombre de usuario para generar nombre único
        filename: Nombre del archivo original (opcional)
    
    Returns:
        Ruta del archivo guardado
    """
    if not contents:
        return "assets/profile_photos/default_profile.png"
    
    # Crear directorio si no existe
    photo_dir = "assets/profile_photos"
    if not os.path.exists(photo_dir):
        os.makedirs(photo_dir)
    
    # Extraer el contenido base64
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    # Determinar extensión
    if 'image/jpeg' in content_type:
        ext = '.jpg'
    elif 'image/png' in content_type:
        ext = '.png'
    elif 'image/gif' in content_type:
        ext = '.gif'
    else:
        ext = '.jpg'  # Por defecto
    
    # Generar nombre de archivo único
    timestamp = dt.datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"{username}_{timestamp}{ext}"
    file_path = os.path.join(photo_dir, filename)
    
    # Guardar archivo
    with open(file_path, "wb") as f:
        f.write(decoded)
    
    return file_path
from models import UserType


def register_settings_callbacks(app):
    """Registra callbacks de Settings en la aplicación Dash."""

    @app.callback(
        Output("settings-main-content", "children"),
        [Input("settings-main-tabs", "active_tab")],
        prevent_initial_call=False,
    )
    def update_settings_main_content(active_tab):
        """Actualiza contenido principal de Settings según la pestaña activa."""
        from pages.settings_dash import create_sync_settings_dash

        if active_tab == "system-tab":
            return create_sync_settings_dash()
        elif active_tab == "users-tab":
            # Users tab con 4 subtabs exactamente como en el original
            return html.Div(
                [
                    dbc.Tabs(
                        [
                            dbc.Tab(
                                label="➕ Create User",
                                tab_id="create-user",
                                active_label_style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Tab(
                                label="✏️ Edit User",
                                tab_id="edit-user",
                                active_label_style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Tab(
                                label="🗑️ Delete User",
                                tab_id="delete-user",
                                active_label_style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Tab(
                                label="📊 User Status",
                                tab_id="user-status",
                                active_label_style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                        ],
                        id="users-subtabs",
                        active_tab="create-user",
                    ),
                    # Contenido de las subtabs
                    html.Div(id="users-subtab-content", className="mt-4"),
                ]
            )
        else:
            return html.Div("Select a tab to view content")

    @app.callback(
        Output("users-subtab-content", "children"),
        [Input("users-subtabs", "active_tab")],
        prevent_initial_call=False,
    )
    def update_users_subtab_content(active_subtab):
        """Actualiza contenido de las subtabs de Users."""
        from pages.settings_dash import create_user_form_dash, create_users_list_dash

        if active_subtab == "create-user":
            return create_user_form_dash()
        elif active_subtab == "edit-user":
            return html.Div(
                [
                    html.H4("✏️ Edit User", style={"color": "rgba(36, 222, 132, 1)"}),
                    create_users_list_dash(),
                ]
            )
        elif active_subtab == "delete-user":
            return html.Div(
                [
                    html.H4("🗑️ Delete User", style={"color": "rgba(36, 222, 132, 1)"}),
                    dbc.Alert("Select users from the list to delete", color="warning"),
                    create_users_list_dash(),
                ]
            )
        elif active_subtab == "user-status":
            return html.Div(
                [
                    html.H4("📊 User Status", style={"color": "rgba(36, 222, 132, 1)"}),
                    dbc.Alert("User activity and status overview", color="info"),
                    create_users_list_dash(),
                ]
            )
        else:
            return html.Div("Select a subtab to view content")

    @app.callback(
        [
            Output("player-fields", "style"),
            Output("coach-fields", "style"),
            Output("admin-fields", "style"),
        ],
        [Input("user-type-selector", "value")],
    )
    def toggle_user_type_fields(user_type):
        """Muestra/oculta campos según el tipo de usuario - migrado de Streamlit"""
        player_style = (
            {"display": "block"} if user_type == "player" else {"display": "none"}
        )
        coach_style = (
            {"display": "block"} if user_type == "coach" else {"display": "none"}
        )
        admin_style = (
            {"display": "block"} if user_type == "admin" else {"display": "none"}
        )

        return player_style, coach_style, admin_style

    @app.callback(
        Output("settings-tab-content", "children"),
        [Input("settings-tabs", "active_tab")],
        prevent_initial_call=False,
    )
    def update_settings_tab_content(active_tab):
        """Actualiza el contenido según la pestaña activa."""
        from pages.settings_dash import (
            create_sync_settings_dash,
            create_system_settings_dash,
            create_user_form_dash,
            create_users_list_dash,
        )

        if active_tab == "users":
            return dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col([create_user_form_dash()], width=12, lg=6),
                            dbc.Col([create_users_list_dash()], width=12, lg=6),
                        ]
                    )
                ]
            )
        elif active_tab == "sync":
            return create_sync_settings_dash()
        elif active_tab == "system":
            return create_system_settings_dash()
        elif active_tab == "reports":
            return html.Div("📊 System reports - To be implemented")
        else:
            return html.Div("Select a tab to view content")

    # ========================================================================
    # CALLBACKS FUNCIONALES PARA CRUD DE USUARIOS
    # ========================================================================

    @app.callback(
        [
            Output("settings-alert", "children"),
            Output("settings-alert", "is_open"),
            Output("settings-alert", "color"),
            # Limpiar formulario tras éxito
            Output("new-fullname", "value"),
            Output("new-username", "value"),
            Output("new-email", "value"),
            Output("new-password", "value"),
            Output("new-confirm-password", "value"),
            Output("new-phone", "value"),
            Output("new-line-id", "value"),
            Output({'type': 'auto-hide-date', 'index': 'new-birth-date'}, "value"),
            Output("new-license-name", "value"),
            Output("new-service-types", "value"),
            Output("new-enrolled-sessions", "value"),
            Output("new-player-notes", "value"),
            Output("new-internal-role", "value"),
            Output("new-permit-level", "value"),
        ],
        [Input("create-user-btn", "n_clicks")],
        [
            State("user-type-selector", "value"),
            State("new-fullname", "value"),
            State("new-username", "value"),
            State("new-email", "value"),
            State("new-password", "value"),
            State("new-confirm-password", "value"),
            State("new-phone", "value"),
            State("new-line-id", "value"),
            State({'type': 'auto-hide-date', 'index': 'new-birth-date'}, "value"),
            State("new-profile-picture", "contents"),
            State("new-license-name", "value"),
            State("new-service-types", "value"),
            State("new-enrolled-sessions", "value"),
            State("new-player-notes", "value"),
            State("new-internal-role", "value"),
            State("new-permit-level", "value"),
        ],
        prevent_initial_call=True,
    )
    def create_new_user(
        n_clicks,
        user_type,
        name,
        username,
        email,
        password,
        confirm_password,
        phone,
        line_id,
        birth_date,
        profile_picture,
        license_name,
        service_types,
        enrolled_sessions,
        player_notes,
        internal_role,
        permit_level,
    ):
        """Crea un nuevo usuario usando el controlador existente."""
        if not n_clicks:
            return "", False, "info", *([no_update] * 14)

        # Validar campos requeridos
        if not all([name, username, email, password, confirm_password]):
            return (
                "Please fill in all required fields (*)",
                True,
                "danger",
                *([no_update] * 14),
            )

        # Validar coincidencia de contraseñas usando controlador existente
        is_valid, error = ValidationController.validate_password_match(
            password, confirm_password
        )
        if not is_valid:
            return error, True, "danger", *([no_update] * 14)

        # Preparar datos específicos del tipo de usuario
        profile_data = {}
        if user_type == "coach":
            profile_data["license"] = license_name or ""
        elif user_type == "player":
            profile_data.update(
                {
                    "services": service_types or [],
                    "enrolment": enrolled_sessions or 0,
                    "notes": player_notes or "",
                }
            )
        elif user_type == "admin":
            profile_data.update(
                {"role": internal_role or "", "permit_level": permit_level or 1}
            )

        # Procesar foto de perfil si se subió
        profile_photo_file = None
        if profile_picture:
            try:
                profile_photo_file = process_dash_upload(profile_picture)
            except Exception as e:
                return (
                    f"Error processing profile picture: {str(e)}",
                    True,
                    "danger",
                    *([no_update] * 14),
                )

        # Preparar datos de usuario
        user_data = {
            "name": name,
            "username": username,
            "email": email,
            "password": password,
            "user_type": user_type,
            "phone": phone,
            "line": line_id,
            "date_of_birth": (
                dt.datetime.fromisoformat(birth_date).date() if birth_date else None
            ),
            "profile_photo_file": profile_photo_file,
            **profile_data,
        }

        # Crear usuario usando controlador existente
        success, message = create_user_simple(user_data)

        if success:
            # Limpiar formulario tras éxito
            return (
                f"✅ {message}",
                True,
                "success",
                "",  # name
                "",  # username
                "",  # email
                "",  # password
                "",  # confirm_password
                "",  # phone
                "",  # line_id
                "",  # birth_date
                "",  # license_name
                [],  # service_types
                0,  # enrolled_sessions
                "",  # player_notes
                "",  # internal_role
                1,  # permit_level
            )
        else:
            return f"❌ {message}", True, "danger", *([no_update] * 14)

    @app.callback(
        Output("users-management-table", "children"),
        [
            Input("users-filter-type", "value"),
            Input("users-search", "value"),
            Input("settings-alert", "is_open"),  # Refrescar tras crear usuario
        ],
        prevent_initial_call=False,
    )
    def update_users_table(filter_type, search_term, alert_state):
        """Actualiza la tabla de usuarios con filtros."""
        try:
            # Obtener usuarios usando controlador existente
            users_data = get_users_for_management()

            if not users_data:
                return dbc.Alert("No users found in the database.", color="info")

            # Filtrar por tipo
            if filter_type and filter_type != "all":
                users_data = [
                    u for u in users_data if u["User Type"].lower() == filter_type
                ]

            # Filtrar por búsqueda
            if search_term:
                search_lower = search_term.lower()
                users_data = [
                    u
                    for u in users_data
                    if search_lower in u["Name"].lower()
                    or search_lower in u["Username"].lower()
                    or search_lower in u["Email"].lower()
                ]

            if not users_data:
                return dbc.Alert(
                    "No users match the selected filters.", color="warning"
                )

            # Crear tabla con estilo del proyecto
            table_rows = []
            for user in users_data:
                # Iconos para estado y tipo
                status_icon = "🟢" if user["Active_Bool"] else "🔴"
                type_icons = {"admin": "🔑", "coach": "📢", "player": "⚽"}
                type_icon = type_icons.get(user["User Type"].lower(), "👤")

                # Color de fila según tipo de usuario
                row_style = {"background-color": "#1D1B1A", "color": "#FFFFFF"}
                user_type_lower = user["User Type"].lower()
                if user_type_lower == "admin":
                    row_style["border-left"] = "4px solid #dc3545"
                elif user_type_lower == "coach":
                    row_style["border-left"] = "4px solid #ffc107"
                elif user_type_lower == "player":
                    row_style["border-left"] = "4px solid rgba(36, 222, 132, 1)"

                table_rows.append(
                    html.Tr(
                        [
                            html.Td(
                                f"{type_icon} {user['User Type']}",
                                style={"padding": "8px", "text-align": "center"},
                            ),
                            html.Td(
                                user["Name"], 
                                style={"padding": "8px", "font-weight": "500"}
                            ),
                            html.Td(user["Username"], style={"padding": "8px"}),
                            html.Td(user["Email"], style={"padding": "8px"}),
                            html.Td(
                                f"{status_icon} {'Active' if user['Active_Bool'] else 'Inactive'}",
                                style={"padding": "8px", "text-align": "center"},
                            ),
                            html.Td(
                                [
                                    dbc.ButtonGroup(
                                        [
                                            dbc.Button(
                                                "🔄 Toggle",
                                                id={
                                                    "type": "toggle-user-btn", 
                                                    "index": user["ID"]
                                                },
                                                size="sm",
                                                color="info",
                                                style={
                                                    "font-size": "0.75rem",
                                                    "border-radius": "15px",
                                                },
                                            ),
                                        ],
                                        size="sm",
                                    )
                                ],
                                style={"padding": "8px", "text-align": "center"},
                            ),
                        ],
                        style=row_style,
                    )
                )

            # Tabla con headers estilizados
            table_header = html.Thead(
                [
                    html.Tr(
                        [
                            html.Th(
                                "Type",
                                style={
                                    "background-color": "transparent",
                                    "color": "rgba(36, 222, 132, 1)",
                                    "border": "1px solid rgba(36, 222, 132, 0.5)",
                                    "padding": "12px 8px",
                                    "text-align": "center",
                                    "font-weight": "600",
                                    "font-size": "0.85rem",
                                },
                            ),
                            html.Th(
                                "Name",
                                style={
                                    "background-color": "transparent",
                                    "color": "rgba(36, 222, 132, 1)",
                                    "border": "1px solid rgba(36, 222, 132, 0.5)",
                                    "padding": "12px 8px",
                                    "font-weight": "600",
                                    "font-size": "0.85rem",
                                },
                            ),
                            html.Th(
                                "Username",
                                style={
                                    "background-color": "transparent",
                                    "color": "rgba(36, 222, 132, 1)",
                                    "border": "1px solid rgba(36, 222, 132, 0.5)",
                                    "padding": "12px 8px",
                                    "font-weight": "600",
                                    "font-size": "0.85rem",
                                },
                            ),
                            html.Th(
                                "Email",
                                style={
                                    "background-color": "transparent",
                                    "color": "rgba(36, 222, 132, 1)",
                                    "border": "1px solid rgba(36, 222, 132, 0.5)",
                                    "padding": "12px 8px",
                                    "font-weight": "600",
                                    "font-size": "0.85rem",
                                },
                            ),
                            html.Th(
                                "Status",
                                style={
                                    "background-color": "transparent",
                                    "color": "rgba(36, 222, 132, 1)",
                                    "border": "1px solid rgba(36, 222, 132, 0.5)",
                                    "padding": "12px 8px",
                                    "text-align": "center",
                                    "font-weight": "600",
                                    "font-size": "0.85rem",
                                },
                            ),
                            html.Th(
                                "Actions",
                                style={
                                    "background-color": "transparent",
                                    "color": "rgba(36, 222, 132, 1)",
                                    "border": "1px solid rgba(36, 222, 132, 0.5)",
                                    "padding": "12px 8px",
                                    "text-align": "center",
                                    "font-weight": "600",
                                    "font-size": "0.85rem",
                                },
                            ),
                        ]
                    )
                ]
            )

            return html.Div(
                [
                    dbc.Table(
                        [table_header, html.Tbody(table_rows)],
                        striped=False,
                        bordered=True,
                        hover=False,
                        responsive=True,
                        size="sm",
                        style={
                            "background-color": "#1D1B1A",
                            "border": "1px solid rgba(36, 222, 132, 0.4)",
                            "border-radius": "6px",
                            "margin": "0",
                        },
                    )
                ],
                style={
                    "max-height": "500px",
                    "overflow": "auto",
                    "background-color": "#1D1B1A",
                    "border-radius": "6px",
                    "padding": "0",
                },
            )

        except Exception as e:
            return dbc.Alert(f"Error loading users: {str(e)}", color="danger")

    @app.callback(
        [
            Output("settings-alert", "children", allow_duplicate=True),
            Output("settings-alert", "is_open", allow_duplicate=True),
            Output("settings-alert", "color", allow_duplicate=True),
        ],
        [
            Input({"type": "toggle-user-btn", "index": dash.dependencies.ALL}, "n_clicks")
        ],
        prevent_initial_call=True,
    )
    def toggle_user_status(n_clicks_list):
        """Activa/desactiva usuarios usando el controlador existente."""
        if not any(n_clicks_list):
            return no_update, no_update, no_update

        # Identificar qué botón fue clickeado
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        user_id = eval(button_id)["index"]

        try:
            # Usar controlador existente
            with UserController() as controller:
                success, message = controller.toggle_user_status(user_id)

            if success:
                return f"✅ {message}", True, "success"
            else:
                return f"❌ {message}", True, "danger"

        except Exception as e:
            return f"❌ Error: {str(e)}", True, "danger"

# callbacks/settings_callbacks.py
"""
Callbacks relacionados con la página de Settings.
"""
import ast
import base64
import datetime as dt
import os

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback_context, html, no_update
from dash.exceptions import PreventUpdate

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
    Procesa un archivo subido desde Dash y lo convierte al formato
    que espera UserController.

    Args:
        contents: String base64 con formato
        "data:image/png;base64,<contenido>"
        filename: Nombre del archivo (opcional)

    Returns:
        Objeto que simula el uploaded_file de Streamlit
    """
    if not contents:
        return None

    # Extraer el contenido base64
    content_type, content_string = contents.split(",")

    # Decodificar base64
    decoded = base64.b64decode(content_string)

    # Determinar extensión desde content_type o usar por defecto
    if "image/jpeg" in content_type:
        ext = ".jpg"
    elif "image/png" in content_type:
        ext = ".png"
    elif "image/gif" in content_type:
        ext = ".gif"
    else:
        ext = ".jpg"  # Por defecto

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
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)

    # Determinar extensión
    if "image/jpeg" in content_type:
        ext = ".jpg"
    elif "image/png" in content_type:
        ext = ".png"
    elif "image/gif" in content_type:
        ext = ".gif"
    else:
        ext = ".jpg"  # Por defecto

    # Generar nombre de archivo único
    timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{username}_{timestamp}{ext}"
    file_path = os.path.join(photo_dir, filename)

    # Guardar archivo
    with open(file_path, "wb") as f:
        f.write(decoded)

    return file_path


def register_settings_callbacks(app):
    """Registra callbacks de Settings en la aplicación Dash."""

    @app.callback(
        Output("settings-main-content", "children"),
        [Input("settings-main-tabs", "active_tab")],
        prevent_initial_call=False,
    )
    def update_settings_main_content(active_tab):
        """Actualiza contenido principal de Settings según pestaña activa."""
        from pages.settings_dash import create_system_settings_dash

        if active_tab == "system-tab":
            return create_system_settings_dash()
        elif active_tab == "users-tab":
            # Users tab con 3 subtabs (Delete User integrado en Edit User)
            return html.Div(
                [
                    dbc.Tabs(
                        [
                            dbc.Tab(
                                label="Create User",
                                tab_id="create-user",
                                active_label_style={"color": "var(--color-primary)"},
                            ),
                            dbc.Tab(
                                label="Edit User",
                                tab_id="edit-user",
                                active_label_style={"color": "var(--color-primary)"},
                            ),
                            dbc.Tab(
                                label="User Status",
                                tab_id="user-status",
                                active_label_style={"color": "var(--color-primary)"},
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
        from pages.settings_dash import create_user_form_dash

        if active_subtab == "create-user":
            return create_user_form_dash()
        elif active_subtab == "edit-user":
            from pages.settings_dash import create_edit_user_form_dash

            return create_edit_user_form_dash()
        elif active_subtab == "user-status":
            from pages.settings_dash import create_user_status_dash

            return create_user_status_dash()
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
            Output({"type": "auto-hide-date", "index": "new-birth-date"}, "value"),
            Output("new-license-name", "value"),
            Output("new-service-types", "value"),
            Output("new-enrolled-sessions", "value"),
            Output("new-player-notes", "value"),
            Output("new-internal-role", "value"),
            Output("new-permit-level", "value"),
            Output("new-is-professional", "value"),
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
            State({"type": "auto-hide-date", "index": "new-birth-date"}, "value"),
            State("new-profile-picture", "contents"),
            State("new-license-name", "value"),
            State("new-service-types", "value"),
            State("new-enrolled-sessions", "value"),
            State("new-player-notes", "value"),
            State("new-internal-role", "value"),
            State("new-permit-level", "value"),
            State("new-is-professional", "value"),
            State("new-wyscout-id", "value"),
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
        is_professional_value,
        wyscout_id,
    ):
        """Crea un nuevo usuario usando el controlador existente."""
        if not n_clicks:
            return "", False, "info", *([no_update] * 15)

        # Validar campos requeridos
        if not all([name, username, email, password, confirm_password]):
            return (
                "Please fill in all required fields (*)",
                True,
                "danger",
                *([no_update] * 15),
            )

        # Validar coincidencia de contraseñas usando controlador existente
        is_valid, error = ValidationController.validate_password_match(
            password, confirm_password
        )
        if not is_valid:
            return error, True, "danger", *([no_update] * 15)

        # Preparar datos específicos del tipo de usuario
        profile_data = {}
        if user_type == "coach":
            profile_data["license"] = license_name or ""
        elif user_type == "player":
            # Procesar estado profesional - Corregir conversión de lista a boolean
            is_professional = bool(
                is_professional_value and "professional" in is_professional_value
            )

            profile_data.update(
                {
                    "services": service_types or [],
                    "enrolment": enrolled_sessions or 0,
                    "notes": player_notes or "",
                    "is_professional": is_professional,
                    "wyscout_id": wyscout_id.strip() if wyscout_id else None,
                }
            )
        elif user_type == "admin":
            profile_data.update(
                {
                    "role": internal_role or "",
                    "permit_level": permit_level or 1,
                }
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
                    *([no_update] * 15),
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
            success_message = f"✅ {message}"

            # Limpiar formulario tras éxito
            return (
                success_message,
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
                [],  # is_professional (empty list to uncheck)
                "",  # wyscout_id
            )
        else:
            return f"❌ {message}", True, "danger", *([no_update] * 15)

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
        print(
            f"🔍 DEBUG USERS LIST: filter_type={filter_type}, search_term={search_term}"
        )
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
                # Iconos Bootstrap para estado y tipo
                status_icon = (
                    html.I(
                        className="bi bi-check-circle-fill me-1",
                        style={"color": "#28a745"},
                    )
                    if user["Active_Bool"]
                    else html.I(
                        className="bi bi-x-circle-fill me-1",
                        style={"color": "#dc3545"},
                    )
                )

                # Iconos Bootstrap para tipos de usuario
                user_type_lower = user["User Type"].lower()
                if user_type_lower == "admin":
                    type_icon = html.I(
                        className="bi bi-shield-lock-fill me-1",
                        style={"color": "#dc3545"},
                    )
                elif user_type_lower == "coach":
                    type_icon = html.I(
                        className="bi bi-megaphone-fill me-1",
                        style={"color": "#ffc107"},
                    )
                elif user_type_lower == "player":
                    type_icon = html.I(
                        className="bi bi-person-fill me-1 text-primary",
                    )
                else:
                    type_icon = html.I(
                        className="bi bi-person me-1",
                        style={"color": "#6c757d"},
                    )

                # Color de fila según tipo de usuario
                row_style = {"background-color": "#1D1B1A", "color": "#FFFFFF"}
                user_type_lower = user["User Type"].lower()
                if user_type_lower == "admin":
                    row_style["border-left"] = "4px solid #dc3545"
                elif user_type_lower == "coach":
                    row_style["border-left"] = "4px solid #ffc107"
                elif user_type_lower == "player":
                    row_style["border-left"] = "4px solid var(--color-primary)"

                table_rows.append(
                    html.Tr(
                        [
                            html.Td(
                                [type_icon, user["User Type"]],
                                style={
                                    "padding": "8px",
                                    "text-align": "center",
                                    "color": "#FFFFFF",
                                },
                            ),
                            html.Td(
                                user["Name"],
                                style={
                                    "padding": "8px",
                                    "font-weight": "500",
                                    "color": "#FFFFFF",
                                },
                            ),
                            html.Td(
                                user["Username"],
                                style={"padding": "8px", "color": "#FFFFFF"},
                            ),
                            html.Td(
                                user["Email"],
                                style={"padding": "8px", "color": "#FFFFFF"},
                            ),
                            html.Td(
                                [
                                    status_icon,
                                    ("Active" if user["Active_Bool"] else "Inactive"),
                                ],
                                style={
                                    "padding": "8px",
                                    "text-align": "center",
                                    "color": "#FFFFFF",
                                },
                            ),
                            html.Td(
                                [
                                    dbc.ButtonGroup(
                                        [
                                            dbc.Button(
                                                "🔄 Toggle",
                                                id={
                                                    "type": "toggle-user-btn",
                                                    "index": user["ID"],
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
                                style={
                                    "padding": "8px",
                                    "text-align": "center",
                                },
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
                                    "color": "var(--color-primary)",
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
                                    "color": "var(--color-primary)",
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
                                    "color": "var(--color-primary)",
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
                                    "color": "var(--color-primary)",
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
                                    "color": "var(--color-primary)",
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
                                    "color": "var(--color-primary)",
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
            Input(
                {"type": "toggle-user-btn", "index": dash.dependencies.ALL},
                "n_clicks",
            )
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
        user_id = ast.literal_eval(button_id)["index"]

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

    # Callback para toggle de User Status tab - con actualización dinámica de tabla
    @app.callback(
        [
            Output("settings-alert", "children", allow_duplicate=True),
            Output("settings-alert", "is_open", allow_duplicate=True),
            Output("settings-alert", "color", allow_duplicate=True),
            Output("user-status-table-container", "children", allow_duplicate=True),
        ],
        [
            Input(
                {"type": "toggle-user-status-btn", "index": dash.dependencies.ALL},
                "n_clicks",
            )
        ],
        [
            State("user-status-type-filter", "value"),
            State("user-status-status-filter", "value"),
        ],
        prevent_initial_call=True,
    )
    def toggle_user_status_from_status_tab(n_clicks_list, type_filter, status_filter):
        """Activa/desactiva usuarios desde User Status tab y actualiza tabla."""
        if not any(n_clicks_list):
            return no_update, no_update, no_update, no_update

        # Identificar qué botón fue clickeado
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        user_id = ast.literal_eval(button_id)["index"]

        try:
            # Usar controlador existente
            with UserController() as controller:
                success, message = controller.toggle_user_status(user_id)

            if success:
                # Actualizar tabla dinámicamente
                updated_table = update_user_status_table(type_filter, status_filter)
                return f"✅ {message}", True, "success", updated_table
            else:
                return f"❌ {message}", True, "danger", no_update

        except Exception as e:
            return f"❌ Error: {str(e)}", True, "danger", no_update

    # ========================================================================
    # CALLBACKS PARA EDIT USER
    # ========================================================================

    @app.callback(
        Output("edit-user-selector", "options"),
        [Input("users-subtabs", "active_tab")],
        prevent_initial_call=False,
    )
    def populate_edit_user_selector(active_tab):
        """Puebla el selector de usuarios para editar."""
        if active_tab != "edit-user":
            return []

        try:
            users_data = get_users_for_management()
            if not users_data:
                return []

            options = []
            for user in users_data:
                # Texto descriptivo para tipo de usuario y estado
                user_type_lower = user["User Type"].lower()
                if user_type_lower == "admin":
                    type_text = "Admin"
                elif user_type_lower == "coach":
                    type_text = "Coach"
                elif user_type_lower == "player":
                    type_text = "Player"
                else:
                    type_text = "User"

                status_text = "Active" if user["Active_Bool"] else "Inactive"

                label = (
                    f"{type_text} - {user['Name']} ({user['Username']}) - {status_text}"
                )
                options.append({"label": label, "value": user["ID"]})

            return options

        except Exception as e:
            return [{"label": f"Error loading users: {str(e)}", "value": ""}]

    @app.callback(
        [
            Output("edit-user-info-display", "style"),
            Output("edit-user-form-container", "style"),
            Output("edit-user-profile-image", "src"),
            Output("edit-user-info-text", "children"),
            Output("edit-user-professional-badge", "children"),
            Output("edit-user-professional-badge", "style"),
            # Form fields
            Output("edit-fullname", "value"),
            Output("edit-username", "value"),
            Output("edit-email", "value"),
            Output("edit-phone", "value"),
            Output("edit-line-id", "value"),
            Output("edit-user-status-text", "children"),
            Output("edit-user-current-status", "data"),
            Output("edit-user-status-toggle-btn", "children"),
            Output("edit-user-type-selector", "value"),
            Output({"type": "auto-hide-date", "index": "edit-birth-date"}, "value"),
            Output("edit-license-name", "value"),
            Output("edit-service-types", "value"),
            Output("edit-enrolled-sessions", "value"),
            Output("edit-player-notes", "value"),
            Output("edit-internal-role", "value"),
            Output("edit-permit-level", "value"),
            Output("edit-is-professional", "value"),
            Output("edit-wyscout-id", "value", allow_duplicate=True),
            Output("edit-wyscout-search-btn", "disabled"),
            Output("edit-wyscout-help", "style"),
        ],
        [Input("edit-user-selector", "value")],
        prevent_initial_call=True,
    )
    def load_user_data_for_editing(selected_user_id):
        """Carga los datos del usuario seleccionado para edición."""
        if not selected_user_id:
            # Hide sections when no user selected
            return (
                {"display": "none"},  # info display
                {"display": "none"},  # form container
                "",  # profile image
                "",  # info text
                "",  # professional badge children
                {"display": "none"},  # professional badge style
                "",  # fullname
                "",  # username
                "",  # email
                "",  # phone
                "",  # line_id
                "",  # user_status_text
                False,  # current_status
                "Activate",  # toggle_btn_text
                "",  # user_type
                "",  # birth_date
                "",  # license_name
                [],  # service_types
                0,  # enrolled_sessions
                "",  # player_notes
                "",  # internal_role
                1,  # permit_level
                [],  # is_professional (empty)
                "",  # wyscout_id (empty)
                True,  # wyscout search button disabled
                {"display": "none"},  # help text hidden
            )

        try:
            user_data = get_user_with_profile(selected_user_id)
            if not user_data:
                return (
                    {"display": "none"},
                    {"display": "none"},
                    "",
                    "Error loading user data",
                    "",
                    {"display": "none"},
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    False,
                    "Activate",
                    "",
                    "",
                    "",
                    [],
                    0,
                    "",
                    "",
                    1,
                    [],  # is_professional (empty)
                )

            # Prepare user info display with Bootstrap icons
            status_icon = (
                html.I(
                    className="bi bi-check-circle-fill me-1",
                    style={"color": "#28a745"},
                )
                if user_data["is_active"]
                else html.I(
                    className="bi bi-x-circle-fill me-1",
                    style={"color": "#dc3545"},
                )
            )

            # Professional player fields - definir ANTES de usar en user_info
            is_professional = user_data.get("is_professional", False) or False

            user_info = [
                html.P(
                    [
                        html.I(
                            className="bi bi-person me-1 text-primary",
                        ),
                        f"Name: {user_data['name']}",
                    ],
                    style={"font-weight": "500", "color": "#FFFFFF"},
                ),
                html.P(
                    [
                        html.I(
                            className="bi bi-shield-lock me-1 text-primary",
                        ),
                        f"User Type: {user_data['user_type']}",
                    ],
                    style={"font-weight": "500", "color": "#FFFFFF"},
                ),
                html.P(
                    [
                        html.I(
                            className="bi bi-envelope me-1 text-primary",
                        ),
                        f"Email: {user_data['email']}",
                    ],
                    style={"font-weight": "500", "color": "#FFFFFF"},
                ),
                # Professional/Amateur info - solo para jugadores
                (
                    html.P(
                        [
                            html.I(
                                className="bi bi-speedometer2 me-1",
                                style={"color": "#24DE84"},
                            ),
                            (
                                "Baller Level: "
                                + (
                                    "Professional"
                                    if (
                                        user_data["user_type"] == "player"
                                        and is_professional
                                    )
                                    else (
                                        "Amateur"
                                        if (user_data["user_type"] == "player")
                                        else "N/A"
                                    )
                                )
                            ),
                        ],
                        style={"font-weight": "500", "color": "#FFFFFF"},
                    )
                    if user_data["user_type"] == "player"
                    else html.P("", style={"display": "none"})
                ),
                html.P(
                    [
                        status_icon,
                        f"Status: {'Active' if user_data['is_active'] else 'Inactive'}",
                    ],
                    style={"font-weight": "500", "color": "#FFFFFF"},
                ),
            ]

            # Process user type specific data - extraer fecha de timestamp BD
            birth_date = user_data.get("date_of_birth", "")
            if birth_date:
                try:
                    # Formato BD: "2010-04-09 00:00:00.000000" → Extraer: "2010-04-09"
                    birth_date = str(birth_date)[:10] if birth_date else ""
                    # Validar que el formato sea YYYY-MM-DD
                    if (
                        len(birth_date) == 10
                        and birth_date[4] == "-"
                        and birth_date[7] == "-"
                    ):
                        pass  # Formato correcto
                    else:
                        birth_date = ""  # Formato incorrecto, dejar vacío
                except Exception:
                    birth_date = ""
            else:
                birth_date = ""

            # User type specific fields
            license_name = user_data.get("coach_license", "") or ""

            # Player services - handle different formats
            service_current = user_data.get("player_service", "") or ""
            if isinstance(service_current, str) and service_current:
                current_services = [
                    s.strip() for s in service_current.split(",") if s.strip()
                ]
            elif isinstance(service_current, list):
                current_services = service_current
            else:
                current_services = []

            enrolled_sessions = user_data.get("player_enrolment", 0) or 0
            player_notes = user_data.get("player_notes", "") or ""
            internal_role = user_data.get("admin_role", "") or ""
            permit_level = user_data.get("permit_level", 1) or 1

            # Professional player fields - ya definido arriba
            professional_value = ["professional"] if is_professional else []
            _wyscout_id = user_data.get("wyscout_id", "") or ""  # Para Wyscout API

            # Status display with icon
            status_icon = (
                html.I(
                    className="bi bi-check-circle-fill me-1",
                    style={"color": "#28a745"},
                )
                if user_data["is_active"]
                else html.I(
                    className="bi bi-x-circle-fill me-1",
                    style={"color": "#dc3545"},
                )
            )
            status_text = [
                status_icon,
                "Active" if user_data["is_active"] else "Inactive",
            ]

            # Button text shows opposite action
            toggle_btn_text = "Deactivate" if user_data["is_active"] else "Activate"

            # Professional badge - eliminado, no mostrar debajo de la foto
            professional_badge_children = ""
            professional_badge_style = {"display": "none"}

            return (
                {"display": "block"},  # show info display
                {"display": "block"},  # show form container
                user_data.get("profile_photo", ""),  # profile image
                user_info,  # info text
                professional_badge_children,  # professional badge children
                professional_badge_style,  # professional badge style
                user_data["name"],  # fullname
                user_data["username"],  # username
                user_data["email"],  # email
                user_data.get("phone", "") or "",  # phone
                user_data.get("line", "") or "",  # line_id
                status_text,  # user_status_text
                user_data["is_active"],  # current_status
                toggle_btn_text,  # toggle_btn_text
                user_data["user_type"],  # user_type
                birth_date,  # birth_date
                license_name,  # license_name
                current_services,  # service_types
                enrolled_sessions,  # enrolled_sessions
                player_notes,  # player_notes
                internal_role,  # internal_role
                permit_level,  # permit_level
                professional_value,  # is_professional
                user_data.get("wyscout_id", "") or "",  # wyscout_id
                False,  # wyscout search button enabled when user selected
                {"display": "block"},  # help text visible
            )

        except Exception as e:
            return (
                {"display": "block"},
                {"display": "none"},
                "",
                f"Error loading user: {str(e)}",
                "",
                {"display": "none"},
                "",
                "",
                "",
                "",
                "",
                "Error",
                False,
                "Activate",
                "",
                "",
                "",
                [],
                0,
                "",
                "",
                1,
                [],  # is_professional (empty)
                "",  # wyscout_id (empty)
                True,  # wyscout search button disabled
                {"display": "none"},  # help text hidden
            )

    @app.callback(
        [
            Output("edit-player-fields", "style"),
            Output("edit-coach-fields", "style"),
            Output("edit-admin-fields", "style"),
        ],
        [Input("edit-user-type-selector", "value")],
    )
    def toggle_edit_user_type_fields(user_type):
        """Muestra/oculta campos según el tipo de usuario en modo edición."""
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
        [
            Output("edit-user-status-text", "children", allow_duplicate=True),
            Output("edit-user-current-status", "data", allow_duplicate=True),
            Output("edit-user-status-toggle-btn", "children", allow_duplicate=True),
            Output("edit-user-info-text", "children", allow_duplicate=True),
        ],
        [Input("edit-user-status-toggle-btn", "n_clicks")],
        [
            State("edit-user-current-status", "data"),
            State("edit-user-selector", "value"),
        ],
        prevent_initial_call=True,
    )
    def toggle_edit_user_status(n_clicks, current_status, selected_user_id):
        """Toggle user status in edit form."""
        if not n_clicks or not selected_user_id:
            return no_update, no_update, no_update, no_update

        # Toggle status
        new_status = not current_status

        # Create status display with icon
        status_icon = (
            html.I(
                className="bi bi-check-circle-fill me-1",
                style={"color": "#28a745"},
            )
            if new_status
            else html.I(
                className="bi bi-x-circle-fill me-1",
                style={"color": "#dc3545"},
            )
        )

        status_text = [status_icon, "Active" if new_status else "Inactive"]

        # Button text shows opposite action
        toggle_btn_text = "Deactivate" if new_status else "Activate"

        # Update only the status line in user info display
        try:
            user_data = get_user_with_profile(selected_user_id)
            if user_data:
                # Rebuild only the updated status line, keep other info unchanged
                updated_status_icon = (
                    html.I(
                        className="bi bi-check-circle-fill me-1",
                        style={"color": "#28a745"},
                    )
                    if new_status
                    else html.I(
                        className="bi bi-x-circle-fill me-1",
                        style={"color": "#dc3545"},
                    )
                )

                # Keep existing user info but update only the status line
                updated_user_info = [
                    html.P(
                        [
                            html.I(
                                className="bi bi-person me-1 text-primary",
                            ),
                            f"Username: {user_data['username']}",
                        ],
                        style={"font-weight": "500", "color": "#FFFFFF"},
                    ),
                    html.P(
                        [
                            html.I(
                                className="bi bi-shield-lock me-1 text-primary",
                            ),
                            f"User Type: {user_data['user_type']}",
                        ],
                        style={"font-weight": "500", "color": "#FFFFFF"},
                    ),
                    html.P(
                        [
                            html.I(
                                className="bi bi-envelope me-1 text-primary",
                            ),
                            f"Email: {user_data['email']}",
                        ],
                        style={"font-weight": "500", "color": "#FFFFFF"},
                    ),
                    html.P(
                        [
                            updated_status_icon,
                            f"Status: {'Active' if new_status else 'Inactive'}",
                        ],
                        style={"font-weight": "500", "color": "#FFFFFF"},
                    ),
                ]

                return (
                    status_text,
                    new_status,
                    toggle_btn_text,
                    updated_user_info,
                )
            else:
                return status_text, new_status, toggle_btn_text, no_update
        except Exception:
            return status_text, new_status, toggle_btn_text, no_update

    @app.callback(
        Output("edit-profile-picture-preview", "children"),
        Output("edit-profile-picture-preview", "style"),
        [Input("edit-profile-picture", "contents")],
        [State("edit-profile-picture", "filename")],
        prevent_initial_call=True,
    )
    def show_profile_picture_preview(contents, filename):
        """Show preview of uploaded profile picture."""
        if contents is None:
            return "", {"display": "none"}

        try:
            # Create preview with delete button
            preview = html.Div(
                [
                    html.Div(
                        [
                            html.P(
                                f"Selected: {filename}",
                                style={
                                    "color": "var(--color-primary)",
                                    "font-weight": "500",
                                    "margin-bottom": "10px",
                                    "font-size": "0.9rem",
                                    "display": "inline-block",
                                },
                            ),
                            dbc.Button(
                                html.I(className="bi bi-x-circle"),
                                id="clear-profile-picture-btn",
                                size="sm",
                                color="link",
                                style={
                                    "color": "#dc3545",
                                    "margin-left": "10px",
                                    "padding": "0",
                                    "border": "none",
                                    "background": "none",
                                },
                                title="Remove image",
                            ),
                        ],
                        style={
                            "display": "flex",
                            "align-items": "center",
                            "justify-content": "center",
                        },
                    ),
                    html.Img(
                        src=contents,
                        style={
                            "max-width": "150px",
                            "max-height": "150px",
                            "border-radius": "10px",
                            "border": "2px solid rgba(36, 222, 132, 0.5)",
                            "object-fit": "cover",
                        },
                    ),
                ]
            )

            return preview, {
                "margin-top": "10px",
                "text-align": "center",
                "display": "block",
            }

        except Exception as e:
            error_msg = html.P(
                f"Error loading image: {str(e)[:50]}...",
                style={"color": "#dc3545", "font-size": "0.8rem"},
            )
            return error_msg, {
                "margin-top": "10px",
                "text-align": "center",
                "display": "block",
            }

    @app.callback(
        [
            Output("edit-profile-picture", "contents"),
            Output("edit-profile-picture", "filename"),
        ],
        [Input("clear-profile-picture-btn", "n_clicks")],
        prevent_initial_call=True,
    )
    def clear_profile_picture(n_clicks):
        """Clear the uploaded profile picture."""
        if n_clicks:
            return None, None
        return no_update, no_update

    # Create User Profile Picture Preview
    @app.callback(
        Output("new-profile-picture-preview", "children"),
        Output("new-profile-picture-preview", "style"),
        [Input("new-profile-picture", "contents")],
        [State("new-profile-picture", "filename")],
        prevent_initial_call=True,
    )
    def show_new_profile_picture_preview(contents, filename):
        """Show preview of uploaded profile picture for new user."""
        from common.upload_component import create_upload_preview_callback_function

        return create_upload_preview_callback_function(
            contents, filename, "new-profile-picture-clear-btn"
        )

    @app.callback(
        [
            Output("new-profile-picture", "contents"),
            Output("new-profile-picture", "filename"),
        ],
        [Input("new-profile-picture-clear-btn", "n_clicks")],
        prevent_initial_call=True,
    )
    def clear_new_profile_picture(n_clicks):
        """Clear the uploaded profile picture for new user."""
        if n_clicks:
            return None, None
        return no_update, no_update

    @app.callback(
        [
            Output("settings-alert", "children", allow_duplicate=True),
            Output("settings-alert", "is_open", allow_duplicate=True),
            Output("settings-alert", "color", allow_duplicate=True),
            Output("edit-user-selector", "value", allow_duplicate=True),
            Output("settings-alert-timer", "disabled", allow_duplicate=True),
        ],
        [Input("save-user-changes-btn", "n_clicks")],
        [
            State("edit-user-selector", "value"),
            State("edit-fullname", "value"),
            State("edit-username", "value"),
            State("edit-email", "value"),
            State("edit-phone", "value"),
            State("edit-line-id", "value"),
            State("edit-user-current-status", "data"),
            State("edit-user-type-selector", "value"),
            State({"type": "auto-hide-date", "index": "edit-birth-date"}, "value"),
            State("edit-new-password", "value"),
            State("edit-confirm-password", "value"),
            State("edit-profile-picture", "contents"),
            State("edit-license-name", "value"),
            State("edit-service-types", "value"),
            State("edit-enrolled-sessions", "value"),
            State("edit-player-notes", "value"),
            State("edit-internal-role", "value"),
            State("edit-permit-level", "value"),
            State("edit-is-professional", "value"),
            State("edit-wyscout-id", "value"),
        ],
        prevent_initial_call=True,
    )
    def save_user_changes(
        n_clicks,
        selected_user_id,
        name,
        username,
        email,
        phone,
        line_id,
        user_current_status,
        user_type,
        birth_date,
        new_password,
        confirm_password,
        profile_picture,
        license_name,
        service_types,
        enrolled_sessions,
        player_notes,
        internal_role,
        permit_level,
        is_professional_value,
        wyscout_id,
    ):
        """Guarda los cambios del usuario editado."""
        if not n_clicks or not selected_user_id:
            return "", False, "info", no_update, True

        # Validar campos requeridos
        if not all([name, username, email]):
            return (
                "Please fill in all required fields (*)",
                True,
                "danger",
                no_update,
                False,  # Activar timer para auto-hide
            )

        # Validar coincidencia de contraseñas si se proporcionan
        if new_password or confirm_password:
            is_valid, error = ValidationController.validate_password_match(
                new_password, confirm_password
            )
            if not is_valid:
                return error, True, "danger", no_update, False

        # Preparar datos específicos del tipo de usuario
        profile_data = {}
        if user_type == "coach":
            profile_data["license"] = license_name or ""
        elif user_type == "player":
            # Procesar estado profesional - Corregir conversión de lista a boolean
            is_professional = bool(
                is_professional_value and "professional" in is_professional_value
            )

            profile_data.update(
                {
                    "services": service_types or [],
                    "enrolment": enrolled_sessions or 0,
                    "notes": player_notes or "",
                    "is_professional": is_professional,
                    "wyscout_id": wyscout_id.strip() if wyscout_id else None,
                }
            )
        elif user_type == "admin":
            profile_data.update(
                {
                    "role": internal_role or "",
                    "permit_level": permit_level or 1,
                }
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
                    no_update,
                )

        # Obtener datos originales para comparar el tipo de usuario
        try:
            original_user_data = get_user_with_profile(selected_user_id)
            original_user_type = original_user_data.get("user_type")
        except Exception:
            original_user_type = None

        # Preparar datos para actualización
        update_data = {
            "name": name,
            "username": username,
            "email": email,
            "phone": phone if phone else None,
            "line": line_id if line_id else None,
            "is_active": bool(user_current_status),
            "new_password": new_password if new_password else None,
            "new_user_type": (user_type if user_type != original_user_type else None),
            "profile_photo_file": profile_photo_file,
            **profile_data,
        }

        # Actualizar usuario usando controlador existente
        success, message = update_user_simple(selected_user_id, **update_data)

        if success:
            success_message = f"✅ {message}"

            return (
                success_message,
                True,
                "success",
                None,
                False,  # Activar timer para auto-hide
            )  # Clear selection to refresh
        else:
            return f"❌ {message}", True, "danger", no_update, False

    @app.callback(
        [
            Output("settings-alert", "is_open", allow_duplicate=True),
            Output("settings-alert-timer", "disabled", allow_duplicate=True),
        ],
        [Input("settings-alert-timer", "n_intervals")],
        prevent_initial_call=True,
    )
    def auto_hide_alert(n_intervals):
        """Auto-hide alert después de 5 segundos."""
        if n_intervals > 0:
            return False, True  # Ocultar alert y deshabilitar timer
        return no_update, no_update

    # ========================================================================
    # CALLBACKS PARA DELETE USER (INTEGRADO EN EDIT USER)
    # ========================================================================

    @app.callback(
        [
            Output("delete-confirmation-modal", "is_open"),
            Output("delete-user-info-display", "children"),
        ],
        [
            Input("show-delete-confirmation-btn", "n_clicks"),
            Input("cancel-delete-btn", "n_clicks"),
        ],
        [State("edit-user-selector", "value")],
        prevent_initial_call=True,
    )
    def show_hide_delete_modal(show_clicks, cancel_clicks, selected_user_id):
        """Muestra/oculta el modal de confirmación de eliminación."""
        ctx = callback_context
        if not ctx.triggered:
            return False, ""

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if (
            trigger_id == "show-delete-confirmation-btn"
            and show_clicks
            and selected_user_id
        ):
            try:
                # Obtener datos del usuario para mostrar en el modal
                user_data = get_user_with_profile(selected_user_id)
                if user_data:
                    user_info = [
                        html.P(
                            [
                                html.I(
                                    className="bi bi-person me-1 text-primary",
                                ),
                                f"Name: {user_data['name']}",
                            ],
                            style={"font-weight": "500", "color": "#FFFFFF"},
                        ),
                        html.P(
                            [
                                html.I(
                                    className="bi bi-person-badge me-1 text-primary",
                                ),
                                f"Username: {user_data['username']}",
                            ],
                            style={"font-weight": "500", "color": "#FFFFFF"},
                        ),
                        html.P(
                            [
                                html.I(
                                    className="bi bi-shield-lock me-1 text-primary",
                                ),
                                f"User Type: {user_data['user_type']}",
                            ],
                            style={"font-weight": "500", "color": "#FFFFFF"},
                        ),
                        html.P(
                            [
                                html.I(
                                    className="bi bi-envelope me-1 text-primary",
                                ),
                                f"Email: {user_data['email']}",
                            ],
                            style={"font-weight": "500", "color": "#FFFFFF"},
                        ),
                    ]
                    return True, user_info
                else:
                    return False, "Error loading user data"
            except Exception as e:
                return False, f"Error: {str(e)}"

        elif trigger_id == "cancel-delete-btn":
            return False, ""

        return False, ""

    @app.callback(
        Output("confirm-delete-btn", "disabled"),
        [Input("delete-confirmation-input", "value")],
    )
    def enable_delete_button(confirmation_text):
        """Habilita el botón de eliminación cuando se escribe 'DELETE'."""
        return confirmation_text != "DELETE"

    @app.callback(
        [
            Output("settings-alert", "children", allow_duplicate=True),
            Output("settings-alert", "is_open", allow_duplicate=True),
            Output("settings-alert", "color", allow_duplicate=True),
            Output("delete-confirmation-modal", "is_open", allow_duplicate=True),
            Output("delete-confirmation-input", "value"),
            Output("edit-user-selector", "value", allow_duplicate=True),
        ],
        [Input("confirm-delete-btn", "n_clicks")],
        [
            State("edit-user-selector", "value"),
            State("delete-confirmation-input", "value"),
        ],
        prevent_initial_call=True,
    )
    def confirm_delete_user(n_clicks, selected_user_id, confirmation_text):
        """Confirma y ejecuta la eliminación del usuario."""
        if not n_clicks or not selected_user_id:
            return "", False, "info", no_update, no_update, no_update

        # Validar confirmación
        is_valid, error = ValidationController.validate_deletion_confirmation(
            confirmation_text, "DELETE"
        )
        if not is_valid:
            return error, True, "danger", no_update, no_update, no_update

        try:
            # Obtener datos del usuario antes de eliminar
            user_data = get_user_with_profile(selected_user_id)
            if not user_data:
                return (
                    "Error: Could not load user data",
                    True,
                    "danger",
                    False,
                    "",
                    no_update,
                )

            # Eliminar usuario usando controlador existente
            success, message = delete_user_simple(user_data["user_id"])

            if success:
                return (
                    f"✅ {message}",
                    True,
                    "success",
                    False,  # Close modal
                    "",  # Clear confirmation input
                    None,  # Clear user selection
                )
            else:
                return (
                    f"❌ {message}",
                    True,
                    "danger",
                    False,  # Close modal
                    "",  # Clear confirmation input
                    no_update,
                )

        except Exception as e:
            return (
                f"❌ Error: {str(e)}",
                True,
                "danger",
                False,  # Close modal
                "",  # Clear confirmation input
                no_update,
            )

    # ========================================================================
    # CALLBACKS PARA USER STATUS TAB
    # ========================================================================

    @app.callback(
        Output("user-status-table-container", "children"),
        [
            Input("user-status-type-filter", "value"),
            Input("user-status-status-filter", "value"),
        ],
        prevent_initial_call=False,
    )
    def update_user_status_table(type_filter, status_filter):
        """Actualiza la tabla de usuarios en User Status con filtros."""
        try:
            # Obtener usuarios usando controlador existente
            users_data = get_users_for_management()

            if not users_data:
                return dbc.Alert("No users found in the database.", color="info")

            # Filtrar por tipo
            if type_filter and type_filter != "all":
                users_data = [
                    u for u in users_data if u["User Type"].lower() == type_filter
                ]

            # Filtrar por estado
            if status_filter == "active":
                users_data = [u for u in users_data if u["Active_Bool"]]
            elif status_filter == "inactive":
                users_data = [u for u in users_data if not u["Active_Bool"]]

            if not users_data:
                return dbc.Alert("No users match the selected filters.", color="info")

            # Crear headers como en create_sessions_table_dash
            headers = [
                html.Th("Type"),
                html.Th("Name"),
                html.Th("Username"),
                html.Th("Email"),
                html.Th("Status"),
                html.Th("Actions"),
            ]

            # Crear filas usando el mismo patrón que create_sessions_table_dash
            rows = []
            for user in users_data:
                # Status con estilo de badge como en sessions
                status_text = "Active" if user["Active_Bool"] else "Inactive"
                status_class = (
                    "status-completed" if user["Active_Bool"] else "status-canceled"
                )

                # Toggle button - texto muestra acción contraria al estado actual
                toggle_text = "Deactivate" if user["Active_Bool"] else "Activate"
                toggle_button = html.Button(
                    toggle_text,
                    id={
                        "type": "toggle-user-status-btn",
                        "index": user["ID"],
                    },
                    style={
                        "background-color": "#17a2b8",
                        "color": "white",
                        "border": "none",
                        "border-radius": "15px",
                        "padding": "4px 8px",
                        "font-size": "0.75rem",
                        "cursor": "pointer",
                    },
                )

                # Iconos Bootstrap según tipo de usuario
                user_type_lower = user["User Type"].lower()
                if user_type_lower == "admin":
                    type_icon = html.I(
                        className="bi bi-shield-lock-fill me-1",
                        style={"color": "#dc3545"},
                    )
                    type_text = "Admin"
                elif user_type_lower == "coach":
                    type_icon = html.I(
                        className="bi bi-megaphone-fill me-1",
                        style={"color": "#ffc107"},
                    )
                    type_text = "Coach"
                elif user_type_lower == "player":
                    type_icon = html.I(
                        className="bi bi-person-fill me-1 text-primary",
                    )
                    type_text = "Player"
                else:
                    type_icon = html.I(
                        className="bi bi-person me-1", style={"color": "#6c757d"}
                    )
                    type_text = "User"

                # Usar exactamente el mismo patrón que create_sessions_table_dash
                row = html.Tr(
                    [
                        html.Td([type_icon, type_text]),
                        html.Td(user["Name"]),
                        html.Td(user["Username"]),
                        html.Td(user["Email"]),
                        html.Td(
                            [
                                html.Span(
                                    status_text,
                                    className=status_class,
                                )
                            ]
                        ),
                        html.Td(toggle_button),
                    ],
                    className="table-row-hover",  # Clase CSS existente
                )
                rows.append(row)

            # Crear tabla usando el mismo patrón que create_sessions_table_dash
            table = dbc.Table(
                [html.Thead(html.Tr(headers)), html.Tbody(rows)],
                striped=True,
                bordered=True,
                hover=True,
                responsive=True,
                className="table-dark",  # Usar clase CSS como en sessions que funciona
            )

            # Envolver con contenedor de scroll simple y limpio
            return html.Div(
                [table],
                className="hide-scrollbar",
                style={
                    "max-height": "400px",
                    "overflow-y": "auto",
                    "overflow-x": "hidden",
                },
            )

        except Exception as e:
            return dbc.Alert(f"Error loading users: {str(e)}", color="danger")

    @app.callback(
        Output("user-status-selector", "options"),
        [
            Input("user-status-type-filter", "value"),
            Input("user-status-status-filter", "value"),
        ],
        prevent_initial_call=False,
    )
    def update_user_status_selector_options(type_filter, status_filter):
        """Actualiza las opciones del selector de usuarios para User Status."""
        try:
            users_data = get_users_for_management()

            if not users_data:
                return []

            # Aplicar filtros
            if type_filter and type_filter != "all":
                users_data = [
                    u for u in users_data if u["User Type"].lower() == type_filter
                ]

            if status_filter == "active":
                users_data = [u for u in users_data if u["Active_Bool"]]
            elif status_filter == "inactive":
                users_data = [u for u in users_data if not u["Active_Bool"]]

            # Crear opciones con iconos usando Bootstrap icons
            options = []
            for user in users_data:
                user_type_lower = user["User Type"].lower()
                if user_type_lower == "admin":
                    type_text = "🔑 Admin"
                elif user_type_lower == "coach":
                    type_text = "📢 Coach"
                elif user_type_lower == "player":
                    type_text = "⚽ Player"
                else:
                    type_text = "👤 User"

                status_icon = "✅" if user["Active_Bool"] else "❌"

                label = (
                    f"{type_text} - {user['Name']} ({user['Username']}) {status_icon}"
                )
                options.append({"label": label, "value": user["ID"]})

            return options

        except Exception as e:
            return [{"label": f"Error loading users: {str(e)}", "value": ""}]

    @app.callback(
        [
            Output("user-status-action-button-container", "children"),
            Output("user-status-current-info", "children"),
        ],
        [Input("user-status-selector", "value")],
        prevent_initial_call=True,
    )
    def update_user_status_action_section(selected_user_id):
        """Actualiza la sección de acción y información del usuario seleccionado."""
        if not selected_user_id:
            return "", ""

        try:
            # Obtener información del usuario seleccionado
            users_data = get_users_for_management()
            selected_user = next(
                (u for u in users_data if u["ID"] == selected_user_id), None
            )

            if not selected_user:
                return "", dbc.Alert("User not found.", color="danger")

            current_status = "Active" if selected_user["Active_Bool"] else "Inactive"
            action = "Deactivate" if selected_user["Active_Bool"] else "Activate"
            button_color = "danger" if selected_user["Active_Bool"] else "success"

            # Botón de acción
            action_button = dbc.Button(
                [
                    html.I(
                        className=(
                            "bi bi-toggle2-off me-2"
                            if selected_user["Active_Bool"]
                            else "bi bi-toggle2-on me-2"
                        )
                    ),
                    f"{action} User",
                ],
                id={"type": "user-status-action-btn", "index": selected_user_id},
                color=button_color,
                size="sm",
                className="w-100",
                style={"margin-top": "1.9rem"},
            )

            # Información actual del usuario
            user_info = dbc.Alert(
                [
                    html.Strong(f"{selected_user['Name']}"),
                    html.Br(),
                    f"Current status: {current_status}",
                ],
                color="info",
                style={"margin-bottom": "0"},
            )

            return action_button, user_info

        except Exception as e:
            return "", dbc.Alert(f"Error: {str(e)}", color="danger")

    @app.callback(
        [
            Output("settings-alert", "children", allow_duplicate=True),
            Output("settings-alert", "is_open", allow_duplicate=True),
            Output("settings-alert", "color", allow_duplicate=True),
        ],
        [
            Input(
                {"type": "user-status-action-btn", "index": dash.dependencies.ALL},
                "n_clicks",
            )
        ],
        prevent_initial_call=True,
    )
    def handle_user_status_action(n_clicks_list):
        """Maneja la acción de cambio de estado de usuario desde User Status."""
        if not any(n_clicks_list):
            return no_update, no_update, no_update

        # Identificar qué botón fue clickeado
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        user_id = ast.literal_eval(button_id)["index"]

        try:
            # Usar controlador existente para cambiar estado
            with UserController() as controller:
                success, message = controller.toggle_user_status(user_id)

            if success:
                return f"✅ {message}", True, "success"
            else:
                return f"❌ {message}", True, "danger"

        except Exception as e:
            return f"❌ Error: {str(e)}", True, "danger"

    # ========================================================================
    # CALLBACKS PARA SYSTEM SETTINGS TAB
    # ========================================================================

    # Auto-sync status callback removed - replaced with webhook-based real-time sync

    @app.callback(
        [
            Output("system-settings-alert", "children"),
            Output("system-settings-alert", "is_open"),
            Output("system-settings-alert", "color"),
        ],
        [
            Input("backup-db-btn", "n_clicks"),
            Input("refresh-sheets-btn", "n_clicks"),
            Input("sync-to-calendar-btn", "n_clicks"),
            Input("sync-from-calendar-btn", "n_clicks"),
            Input("manual-sync-btn", "n_clicks"),
            Input("clear-sync-results-btn", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def handle_system_settings_actions(
        backup_clicks,
        refresh_clicks,
        sync_to_clicks,
        sync_from_clicks,
        manual_sync_clicks,
        clear_results_clicks,
    ):
        """Maneja todas las acciones de System Settings."""
        ctx = callback_context
        if not ctx.triggered:
            return "", False, "info"

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        try:
            if trigger_id == "backup-db-btn" and backup_clicks:
                import datetime as dt
                import os
                import shutil

                backup_dir = "backups"
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir)

                timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"{backup_dir}/ballers_app_{timestamp}.db"

                try:
                    shutil.copy2("data/ballers_app.db", backup_file)
                    return (
                        f"✅ Backup created successfully: {backup_file}",
                        True,
                        "success",
                    )
                except Exception as e:
                    return f"❌ Error creating backup: {str(e)}", True, "danger"

            elif trigger_id == "refresh-sheets-btn" and refresh_clicks:
                from controllers.sheets_controller_dash import get_accounting_df

                try:
                    get_accounting_df.clear()
                    _df = get_accounting_df()  # Para análisis estadísticas
                    return "✅ Google Sheets updated successfully", True, "success"
                except Exception as e:
                    return f"❌ Error updating Google Sheets: {e}", True, "danger"

            elif trigger_id == "sync-to-calendar-btn" and sync_to_clicks:
                from controllers.calendar_sync_core import sync_db_to_calendar

                try:
                    pushed, updated = sync_db_to_calendar()
                    sessions_msg = f"✅ {pushed} new sessions sent"
                    updates_msg = f"{updated} sessions updated in Google Calendar"
                    return (
                        f"{sessions_msg}, {updates_msg}",
                        True,
                        "success",
                    )
                except Exception as e:
                    return f"❌ Error syncing to calendar: {e}", True, "danger"

            elif trigger_id == "sync-from-calendar-btn" and sync_from_clicks:
                from controllers.sync_coordinator import force_manual_sync

                try:
                    result = force_manual_sync()

                    if result["success"]:
                        duration = result["duration"]
                        imported = result.get("imported", 0)
                        updated = result.get("updated", 0)
                        deleted = result.get("deleted", 0)
                        rejected_events = result.get("rejected_events", [])
                        warning_events = result.get("warning_events", [])

                        changes = []
                        if imported > 0:
                            changes.append(f"{imported} imported")
                        if updated > 0:
                            changes.append(f"{updated} updated")
                        if deleted > 0:
                            changes.append(f"{deleted} deleted")

                        changes_text = ", ".join(changes) if changes else "no changes"

                        if len(rejected_events) > 0:
                            rejected_msg = f"⚠️ Sync completed with {len(rejected_events)} rejected events"
                            time_msg = f"({duration:.1f}s) | {changes_text}"
                            return (
                                f"{rejected_msg} {time_msg}",
                                True,
                                "warning",
                            )
                        elif len(warning_events) > 0:
                            warning_msg = (
                                f"⚠️ Sync completed with {len(warning_events)} warnings"
                            )
                            time_msg = f"({duration:.1f}s) | {changes_text}"
                            return (
                                f"{warning_msg} {time_msg}",
                                True,
                                "warning",
                            )
                        elif imported + updated + deleted > 0:
                            success_msg = f"✅ Sync completed successfully"
                            time_msg = f"({duration:.1f}s) | {changes_text}"
                            return (
                                f"{success_msg} {time_msg}",
                                True,
                                "success",
                            )
                        else:
                            return (
                                f"ℹ️ Sync completed - no changes ({duration:.1f}s)",
                                True,
                                "info",
                            )
                    else:
                        return f"❌ Sync failed: {result['error']}", True, "danger"
                except Exception as e:
                    return f"❌ Error during manual sync: {e}", True, "danger"

            elif trigger_id == "manual-sync-btn" and manual_sync_clicks:
                from controllers.sync_coordinator import force_manual_sync

                try:
                    result = force_manual_sync()
                    if result["success"]:
                        total_changes = (
                            result.get("imported", 0)
                            + result.get("updated", 0)
                            + result.get("deleted", 0)
                        )
                        if total_changes > 0:
                            return (
                                f"✅ Manual sync completed: {total_changes} changes",
                                True,
                                "success",
                            )
                        else:
                            return (
                                "✅ Manual sync completed: No changes",
                                True,
                                "success",
                            )
                    else:
                        return (
                            f"❌ Manual sync failed: {result['error']}",
                            True,
                            "danger",
                        )
                except Exception as e:
                    return f"❌ Error during manual sync: {e}", True, "danger"

            elif trigger_id == "clear-sync-results-btn" and clear_results_clicks:
                from controllers.notification_controller import clear_sync_problems

                try:
                    clear_sync_problems()
                    return "✅ Sync results cleared successfully", True, "success"
                except Exception as e:
                    return f"❌ Error clearing sync results: {e}", True, "danger"

            return "", False, "info"

        except Exception as e:
            return f"❌ Unexpected error: {str(e)}", True, "danger"

    @app.callback(
        Output("sync-results-content", "children"),
        [
            Input("settings-main-tabs", "active_tab"),
            Input("clear-sync-results-btn", "n_clicks"),
        ],
        prevent_initial_call=False,
    )
    def update_sync_results_display(active_tab, clear_clicks):
        """Actualiza la visualización de resultados de sync."""
        if active_tab != "system-tab":
            return ""

        try:
            from controllers.notification_controller import get_sync_problems

            problems = get_sync_problems()
            if not problems:
                return dbc.Alert(
                    "ℹ️ No recent sync data available",
                    color="info",
                    style={"font-size": "0.9rem"},
                )

            # Mostrar estadísticas si están disponibles
            if "stats" in problems:
                stats = problems["stats"]
                imported = stats.get("imported", 0)
                updated = stats.get("updated", 0)
                deleted = stats.get("deleted", 0)
                duration = stats.get("duration", 0)

                metrics = dbc.Row(
                    [
                        dbc.Col(
                            dbc.Alert(
                                f"📥 {imported}",
                                color="primary",
                                style={"text-align": "center", "font-size": "0.8rem"},
                            ),
                            width=2,
                        ),
                        dbc.Col(
                            dbc.Alert(
                                f"🔄 {updated}",
                                color="info",
                                style={"text-align": "center", "font-size": "0.8rem"},
                            ),
                            width=2,
                        ),
                        dbc.Col(
                            dbc.Alert(
                                f"🗑️ {deleted}",
                                color="secondary",
                                style={"text-align": "center", "font-size": "0.8rem"},
                            ),
                            width=2,
                        ),
                        dbc.Col(
                            dbc.Alert(
                                f"🚫 {len(problems.get('rejected', []))}",
                                color="danger",
                                style={"text-align": "center", "font-size": "0.8rem"},
                            ),
                            width=2,
                        ),
                        dbc.Col(
                            dbc.Alert(
                                f"⚠️ {len(problems.get('warnings', []))}",
                                color="warning",
                                style={"text-align": "center", "font-size": "0.8rem"},
                            ),
                            width=2,
                        ),
                        dbc.Col(
                            dbc.Alert(
                                f"⏱️ {duration:.1f}s",
                                color="light",
                                style={
                                    "text-align": "center",
                                    "font-size": "0.8rem",
                                    "color": "#000000",
                                },
                            ),
                            width=2,
                        ),
                    ],
                    className="mb-3",
                )

                return html.Div([metrics])
            else:
                return dbc.Alert(
                    f"📊 Sync problems detected: {len(problems.get('rejected', []))} rejected, {len(problems.get('warnings', []))} warnings",
                    color="warning",
                    style={"font-size": "0.9rem"},
                )

        except Exception as e:
            return dbc.Alert(
                f"❌ Error loading sync results: {str(e)}",
                color="danger",
                style={"font-size": "0.9rem"},
            )

    @app.callback(
        Output("edit-user-info-text", "children", allow_duplicate=True),
        [Input("edit-is-professional", "value")],
        [
            State("edit-user-selector", "value"),
            State("edit-fullname", "value"),
        ],
        prevent_initial_call=True,
    )
    def update_baller_level_dynamically(
        is_professional_value, selected_user_id, player_name
    ):
        """Actualiza dinámicamente el Baller Level cuando se cambia el checkbox professional."""
        if not selected_user_id:
            return no_update

        try:
            # Obtener datos del usuario
            user_data = get_user_with_profile(selected_user_id)
            if not user_data or user_data["user_type"] != "player":
                return no_update

            # Determinar si es profesional
            is_professional = bool(
                is_professional_value and "professional" in is_professional_value
            )

            # Recrear la información del usuario con el Baller Level actualizado
            status_icon = (
                html.I(
                    className="bi bi-check-circle-fill me-1",
                    style={"color": "#28a745"},
                )
                if user_data["is_active"]
                else html.I(
                    className="bi bi-x-circle-fill me-1",
                    style={"color": "#dc3545"},
                )
            )

            user_info = [
                html.P(
                    [
                        html.I(
                            className="bi bi-person me-1 text-primary",
                        ),
                        f"Name: {user_data['name']}",
                    ],
                    style={"font-weight": "500", "color": "#FFFFFF"},
                ),
                html.P(
                    [
                        html.I(
                            className="bi bi-shield-lock me-1 text-primary",
                        ),
                        f"User Type: {user_data['user_type']}",
                    ],
                    style={"font-weight": "500", "color": "#FFFFFF"},
                ),
                html.P(
                    [
                        html.I(
                            className="bi bi-envelope me-1 text-primary",
                        ),
                        f"Email: {user_data['email']}",
                    ],
                    style={"font-weight": "500", "color": "#FFFFFF"},
                ),
                # Baller Level actualizado dinámicamente
                html.P(
                    [
                        html.I(
                            className="bi bi-speedometer2 me-1",
                            style={"color": "#24DE84"},
                        ),
                        f"Baller Level: {'Professional' if is_professional else 'Amateur'}",
                    ],
                    style={"font-weight": "500", "color": "#FFFFFF"},
                ),
                html.P(
                    [
                        status_icon,
                        f"Status: {'Active' if user_data['is_active'] else 'Inactive'}",
                    ],
                    style={"font-weight": "500", "color": "#FFFFFF"},
                ),
            ]

            return user_info

        except Exception:
            return no_update


# ================================
# Professional Player Callbacks
# ================================


@dash.callback(
    [
        Output("new-wyscout-section", "style"),
        Output("new-wyscout-help", "style"),
        Output("new-wyscout-id", "disabled"),
        Output("new-thai-search-btn", "disabled"),
        Output("thai-league-matching-modal", "is_open"),
        Output("matching-search-input", "value"),
        Output("settings-alert", "children", allow_duplicate=True),
        Output("settings-alert", "is_open", allow_duplicate=True),
        Output("settings-alert", "color", allow_duplicate=True),
    ],
    [
        Input("new-is-professional", "value"),
        Input("matching-cancel-btn", "n_clicks"),
    ],
    [State("new-fullname", "value")],
    prevent_initial_call=True,
)
def toggle_new_wyscout_section_and_modal(
    is_professional_value, cancel_clicks, player_name
):
    """Toggle WyscoutID section and open matching modal when professional is checked."""
    ctx = dash.callback_context

    if not ctx.triggered:
        return (
            {"display": "none"},
            {"display": "none"},
            True,
            True,
            False,
            "",
            "",
            False,
            "info",
        )

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "new-is-professional":
        if is_professional_value and "professional" in is_professional_value:
            # Check if player name exists
            if player_name and player_name.strip():
                # Show WyscoutID section and help, enable field and button, open modal, clear any alert
                return (
                    {"display": "block"},
                    {"display": "block"},
                    False,
                    False,
                    True,
                    player_name.strip(),
                    "",
                    False,
                    "info",
                )
            else:
                # Show warning message, keep section hidden
                warning_msg = "⚠️ Please enter the player's name first to enable professional player matching."
                return (
                    {"display": "none"},
                    {"display": "none"},
                    True,
                    True,
                    False,
                    "",
                    warning_msg,
                    True,
                    "warning",
                )
        else:
            # Hide WyscoutID section and help, disable field and button, close modal, clear alert
            return (
                {"display": "none"},
                {"display": "none"},
                True,
                True,
                False,
                "",
                "",
                False,
                "info",
            )

    elif trigger_id == "matching-cancel-btn":
        # Close modal, keep WyscoutID section and help visible, keep button enabled, clear alert
        return (
            {"display": "block"},
            {"display": "block"},
            False,
            False,
            False,
            "",
            "",
            False,
            "info",
        )

    return (
        {"display": "none"},
        {"display": "none"},
        True,
        True,
        False,
        "",
        "",
        False,
        "info",
    )


@dash.callback(
    [
        Output("edit-wyscout-section", "style"),
        Output("edit-wyscout-id", "disabled"),
        Output("edit-wyscout-search-btn", "disabled", allow_duplicate=True),
        Output("edit-thai-league-matching-modal", "is_open"),
        Output("edit-matching-search-input", "value"),
        Output("edit-wyscout-help", "style", allow_duplicate=True),
    ],
    [
        Input("edit-is-professional", "value"),
        Input("edit-matching-cancel-btn", "n_clicks"),
    ],
    [
        State("edit-fullname", "value"),
        State("edit-wyscout-id", "value"),
    ],
    prevent_initial_call=True,
)
def toggle_edit_wyscout_section_and_modal(
    is_professional_value, cancel_clicks, player_name, current_wyscout_id
):
    """Toggle WyscoutID section and open matching modal when professional is checked in edit form."""
    ctx = dash.callback_context

    if not ctx.triggered:
        return {"display": "none"}, True, True, False, "", {"display": "none"}

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "edit-is-professional":
        if is_professional_value and "professional" in is_professional_value:
            # Show WyscoutID section, enable field and search button, show help text
            # NEVER auto-open modal - only manual opening via Search button
            return {"display": "block"}, False, False, False, "", {"display": "block"}
        else:
            # Hide WyscoutID section, disable field and search button, close modal, hide help text
            return {"display": "none"}, True, True, False, "", {"display": "none"}

    elif trigger_id == "edit-matching-cancel-btn":
        # Close modal, keep WyscoutID section visible with enabled buttons and help text
        return {"display": "block"}, False, False, False, "", {"display": "block"}

    return {"display": "none"}, True, True, False, "", {"display": "none"}


@dash.callback(
    [
        Output("matching-results-container", "children"),
        Output("matching-search-alert", "children"),
        Output("matching-search-alert", "is_open"),
        Output("matching-search-alert", "color"),
        Output("thai-league-matching-modal", "is_open", allow_duplicate=True),
    ],
    [
        Input("new-is-professional", "value"),
        Input("matching-search-btn", "n_clicks"),
    ],
    [
        State("new-fullname", "value"),
        State("matching-search-input", "value"),
    ],
    prevent_initial_call=True,
)
def auto_search_thai_league_new(
    is_professional_value, search_btn_clicks, player_name, search_term
):
    """Búsqueda automática y manual en Thai League para formulario de creación."""
    ctx = dash.callback_context

    # Determinar qué triggered el callback
    if not ctx.triggered:
        return [], "", False, "info", False

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # Búsqueda manual desde el modal
    if trigger_id == "matching-search-btn":
        if not search_btn_clicks or not search_term or not search_term.strip():
            return [], "Enter a player name to search", True, "info", True

        search_name = search_term.strip()
        # Retornar valores vacíos para alerts del formulario principal
        _main_alert = ("", False, "info")  # Para notificaciones futuras

    # Búsqueda automática al marcar checkbox
    elif trigger_id == "new-is-professional":
        if not is_professional_value or "professional" not in is_professional_value:
            return [], "", False, "info", False

        if not player_name or not player_name.strip():
            return (
                [],
                "Enter player name first to search Thai League data",
                True,
                "warning",
                False,
            )

        search_name = player_name.strip()
        # Retornar valores vacíos para contenedores del modal
        _modal_results = ([], "", False, "info")  # Para resultados modales

    else:
        return [], "", False, "info", False

    try:
        from controllers.thai_league_controller import ThaiLeagueController

        controller = ThaiLeagueController()
        matches = controller.search_players_in_csv(search_name)

        if matches:
            # Búsqueda automática - mantener modal abierto para permitir selección manual
            if trigger_id == "new-is-professional":
                return [], "", False, "info", True

            # Búsqueda manual - mostrar resultados en modal
            elif trigger_id == "matching-search-btn":
                results = []
                for idx, match in enumerate(matches[:10]):  # Máximo 10 resultados
                    confidence = match.get("confidence", 0)
                    player_name_result = match.get("player_name", "N/A")
                    full_name = match.get("full_name", player_name_result)
                    team_name = match.get("team_name", "N/A")
                    wyscout_id = match.get("wyscout_id", "N/A")
                    birthday = match.get("birthday", "N/A")

                    # Crear card para cada resultado
                    card = dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6(
                                        f"{full_name} ({confidence}%)",
                                        className="card-title mb-1",
                                        style={"color": "#FFFFFF"},
                                    ),
                                    html.P(
                                        [
                                            html.Small(
                                                f"Team: {team_name}",
                                                style={"color": "#CCCCCC"},
                                            ),
                                            html.Br(),
                                            html.Small(
                                                f"Wyscout ID: {wyscout_id} | Birthday: {birthday}",
                                                style={"color": "#CCCCCC"},
                                            ),
                                        ],
                                        className="mb-2",
                                    ),
                                    dbc.Button(
                                        "Select This Player",
                                        id={
                                            "type": "select-player",
                                            "index": idx,
                                            "wyscout_id": wyscout_id,
                                        },
                                        className="btn-modal-cancel btn-sm w-100",
                                    ),
                                ],
                                style={"padding": "1rem"},
                            ),
                        ],
                        className="mb-2",
                        style={
                            "background-color": "rgba(51,51,51,1)",
                            "border": "1px solid #555",
                            "border-radius": "8px",
                            "margin-right": "10px",
                        },
                    )
                    results.append(card)

                return results, f"Found {len(matches)} matches", True, "success", True
        else:
            # Sin resultados
            if trigger_id == "new-is-professional":
                return (
                    [],
                    f"❌ No matches found for '{search_name}' in Thai League database",
                    True,
                    "warning",
                    True,
                )
            elif trigger_id == "matching-search-btn":
                return (
                    [],
                    f"No matches found for '{search_name}'",
                    True,
                    "warning",
                    True,
                )

    except Exception as e:
        _error_msg = f"⚠️ Error searching Thai League: {str(e)}"  # Futuro
        if trigger_id == "new-is-professional":
            return [], f"⚠️ Error searching Thai League: {str(e)}", True, "danger", True
        elif trigger_id == "matching-search-btn":
            return [], f"Error searching: {str(e)}", True, "danger", True


@dash.callback(
    [
        Output("settings-alert", "children", allow_duplicate=True),
        Output("settings-alert", "is_open", allow_duplicate=True),
        Output("settings-alert", "color", allow_duplicate=True),
        Output("edit-matching-results-container", "children"),
        Output("edit-matching-search-alert", "children"),
        Output("edit-matching-search-alert", "is_open"),
        Output("edit-matching-search-alert", "color"),
        Output("edit-thai-league-matching-modal", "is_open", allow_duplicate=True),
        Output("edit-matching-search-input", "value", allow_duplicate=True),
    ],
    [
        Input("edit-is-professional", "value"),
        Input("edit-matching-search-btn", "n_clicks"),
        Input("edit-wyscout-search-btn", "n_clicks"),
    ],
    [
        State("edit-fullname", "value"),
        State("edit-wyscout-id", "value"),
        State("edit-matching-search-input", "value"),
    ],
    prevent_initial_call=True,
)
def auto_search_thai_league_edit(
    is_professional_value,
    search_btn_clicks,
    wyscout_search_clicks,
    player_name,
    current_wyscout_id,
    search_term,
):
    """Búsqueda automática y manual en Thai League para formulario de edición."""
    ctx = dash.callback_context

    # Determinar qué triggered el callback
    if not ctx.triggered:
        return "", False, "info", [], "", False, "info", False, ""

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # Búsqueda manual desde el modal
    if trigger_id == "edit-matching-search-btn":
        if not search_btn_clicks or not search_term or not search_term.strip():
            return (
                "",
                False,
                "info",
                [],
                "Enter a player name to search",
                True,
                "info",
                True,
                "",
            )

        search_name = search_term.strip()

    # Búsqueda manual desde botón Search junto al WyscoutID (Edit User)
    elif trigger_id == "edit-wyscout-search-btn":
        if not wyscout_search_clicks or not player_name or not player_name.strip():
            return (
                "",
                False,
                "info",
                [],
                "Player name is required to search",
                True,
                "warning",
                False,
                "",
            )

        # Abrir modal con nombre del jugador pre-rellenado para búsqueda manual
        return "", False, "info", [], "", False, "info", True, player_name.strip()

        search_name = player_name.strip()

    # Búsqueda automática SELECTIVA: solo para amateur → professional sin WyscoutID
    elif trigger_id == "edit-is-professional":
        if not is_professional_value or "professional" not in is_professional_value:
            return "", False, "info", [], "", False, "info", False, ""

        # Si ya tiene WyscoutID, NO hacer búsqueda automática (ya es profesional)
        if current_wyscout_id and current_wyscout_id.strip():
            return "", False, "info", [], "", False, "info", False, ""

        # Si no tiene nombre del jugador, no hacer búsqueda
        if not player_name or not player_name.strip():
            return "", False, "info", [], "", False, "info", False, ""

        # Amateur → Professional: hacer búsqueda automática con modal
        search_name = player_name.strip()

    else:
        return "", False, "info", [], "", False, "info", False, ""

    try:
        from controllers.thai_league_controller import ThaiLeagueController

        controller = ThaiLeagueController()
        matches = controller.search_players_in_csv(search_name)

        if matches:
            # Búsqueda automática y manual - mostrar resultados en modal
            if (
                trigger_id == "edit-is-professional"
                or trigger_id == "edit-matching-search-btn"
                or trigger_id == "edit-wyscout-search-btn"
            ):
                results = []
                for idx, match in enumerate(matches[:10]):  # Máximo 10 resultados
                    confidence = match.get("confidence", 0)
                    player_name_result = match.get("player_name", "N/A")
                    full_name = match.get("full_name", player_name_result)
                    team_name = match.get("team_name", "N/A")
                    wyscout_id = match.get("wyscout_id", "N/A")
                    birthday = match.get("birthday", "N/A")

                    # Crear card para cada resultado
                    card = dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6(
                                        f"{full_name} ({confidence}%)",
                                        className="card-title mb-1",
                                        style={"color": "#FFFFFF"},
                                    ),
                                    html.P(
                                        [
                                            html.Small(
                                                f"Team: {team_name}",
                                                style={"color": "#CCCCCC"},
                                            ),
                                            html.Br(),
                                            html.Small(
                                                f"Wyscout ID: {wyscout_id} | Birthday: {birthday}",
                                                style={"color": "#CCCCCC"},
                                            ),
                                        ],
                                        className="mb-2",
                                    ),
                                    dbc.Button(
                                        "Select This Player",
                                        id={
                                            "type": "edit-select-player",
                                            "index": idx,
                                            "wyscout_id": wyscout_id,
                                        },
                                        className="btn-modal-cancel btn-sm w-100",
                                    ),
                                ]
                            ),
                        ],
                        className="mb-2",
                        style={
                            "background-color": "rgba(51,51,51,1)",
                            "border": "1px solid #555",
                            "border-radius": "8px",
                            "margin-right": "10px",
                        },
                    )
                    results.append(card)

                # Para búsqueda automática de amateur → professional, pre-rellenar input y abrir modal
                if trigger_id == "edit-is-professional":
                    return (
                        "",
                        False,
                        "info",
                        results,
                        f"Found {len(matches)} matches",
                        True,
                        "success",
                        True,
                        search_name,
                    )
                else:
                    return (
                        "",
                        False,
                        "info",
                        results,
                        f"Found {len(matches)} matches",
                        True,
                        "success",
                        True,
                        "",
                    )
        else:
            # Sin resultados
            if trigger_id == "edit-is-professional":
                message = (
                    f"❌ No matches found for '{search_name}' in Thai League database"
                )
                return (
                    message,
                    True,
                    "warning",
                    [],
                    "",
                    False,
                    "info",
                    True,
                    search_name,
                )
            elif (
                trigger_id == "edit-matching-search-btn"
                or trigger_id == "edit-wyscout-search-btn"
            ):
                return (
                    "",
                    False,
                    "info",
                    [],
                    f"No matches found for '{search_name}'",
                    True,
                    "warning",
                    True,
                    "",
                )

    except Exception as e:
        error_msg = f"⚠️ Error searching Thai League: {str(e)}"
        if trigger_id == "edit-is-professional":
            return error_msg, True, "danger", [], "", False, "info", True, search_name
        elif (
            trigger_id == "edit-matching-search-btn"
            or trigger_id == "edit-wyscout-search-btn"
        ):
            return (
                "",
                False,
                "info",
                [],
                f"Error searching: {str(e)}",
                True,
                "danger",
                True,
                "",
            )


@dash.callback(
    [
        Output("thai-league-matching-modal", "is_open", allow_duplicate=True),
        Output("matching-search-input", "value", allow_duplicate=True),
    ],
    [
        Input("new-thai-search-btn", "n_clicks"),
    ],
    [
        State("new-fullname", "value"),
    ],
    prevent_initial_call=True,
)
def handle_new_thai_search_btn(search_clicks, player_name):
    """Manejar click del botón Search en Create User - abrir modal con nombre pre-rellenado."""
    if not search_clicks or not player_name or not player_name.strip():
        return False, ""

    # Abrir modal con nombre del jugador pre-rellenado para búsqueda manual
    return True, player_name.strip()


# ===== CALLBACKS PARA ASIGNACIÓN DE WYSCOUT_ID =====


@dash.callback(
    [
        Output("new-wyscout-id", "value"),
        Output("thai-league-matching-modal", "is_open", allow_duplicate=True),
        Output("matching-search-alert", "children", allow_duplicate=True),
        Output("matching-search-alert", "is_open", allow_duplicate=True),
        Output("matching-search-alert", "color", allow_duplicate=True),
    ],
    [Input({"type": "select-player", "index": ALL, "wyscout_id": ALL}, "n_clicks")],
    [State({"type": "select-player", "index": ALL, "wyscout_id": ALL}, "id")],
    prevent_initial_call=True,
)
def assign_wyscout_id_create(n_clicks_list, button_ids):
    """Asignar wyscout_id cuando se selecciona un jugador en formulario de creación."""
    ctx = dash.callback_context

    if not ctx.triggered or not any(n_clicks_list):
        raise PreventUpdate

    # Encontrar cuál botón fue presionado
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    button_data = ast.literal_eval(triggered_id)  # Convertir string a dict

    wyscout_id = button_data.get("wyscout_id", "")

    if wyscout_id and wyscout_id != "N/A":
        return (
            wyscout_id,
            False,
            f"✅ WyscoutID {wyscout_id} assigned successfully!",
            True,
            "success",
        )
    else:
        return "", True, "❌ Error: Invalid WyscoutID", True, "danger"


@dash.callback(
    [
        Output("edit-wyscout-id", "value"),
        Output("edit-thai-league-matching-modal", "is_open", allow_duplicate=True),
        Output("edit-matching-search-alert", "children", allow_duplicate=True),
        Output("edit-matching-search-alert", "is_open", allow_duplicate=True),
        Output("edit-matching-search-alert", "color", allow_duplicate=True),
    ],
    [
        Input(
            {"type": "edit-select-player", "index": ALL, "wyscout_id": ALL}, "n_clicks"
        )
    ],
    [State({"type": "edit-select-player", "index": ALL, "wyscout_id": ALL}, "id")],
    prevent_initial_call=True,
)
def assign_wyscout_id_edit(n_clicks_list, button_ids):
    """Asignar wyscout_id cuando se selecciona un jugador en formulario de edición."""
    ctx = dash.callback_context

    if not ctx.triggered or not any(n_clicks_list):
        raise PreventUpdate

    # Encontrar cuál botón fue presionado
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    button_data = ast.literal_eval(triggered_id)  # Convertir string a dict

    wyscout_id = button_data.get("wyscout_id", "")

    if wyscout_id and wyscout_id != "N/A":
        return (
            wyscout_id,
            False,
            f"✅ WyscoutID {wyscout_id} assigned successfully!",
            True,
            "success",
        )
    else:
        return "", True, "❌ Error: Invalid WyscoutID", True, "danger"

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
                                label="Create User",
                                tab_id="create-user",
                                active_label_style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Tab(
                                label="Edit User",
                                tab_id="edit-user",
                                active_label_style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Tab(
                                label="Delete User",
                                tab_id="delete-user",
                                active_label_style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Tab(
                                label="User Status",
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
            from pages.settings_dash import create_edit_user_form_dash

            return create_edit_user_form_dash()
        elif active_subtab == "delete-user":
            return html.Div(
                [
                    html.H4("Delete User", style={"color": "rgba(36, 222, 132, 1)"}),
                    dbc.Alert("Select users from the list to delete", color="warning"),
                    create_users_list_dash(),
                ]
            )
        elif active_subtab == "user-status":
            return html.Div(
                [
                    html.H4("User Status", style={"color": "rgba(36, 222, 132, 1)"}),
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
            Output({"type": "auto-hide-date", "index": "new-birth-date"}, "value"),
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
            State({"type": "auto-hide-date", "index": "new-birth-date"}, "value"),
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
                        className="bi bi-person-fill me-1",
                        style={"color": "rgba(36, 222, 132, 1)"},
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
                    row_style["border-left"] = "4px solid rgba(36, 222, 132, 1)"

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

            user_info = [
                html.P(
                    [
                        html.I(
                            className="bi bi-person me-1",
                            style={"color": "rgba(36, 222, 132, 1)"},
                        ),
                        f"Username: {user_data['username']}",
                    ],
                    style={"font-weight": "500", "color": "#FFFFFF"},
                ),
                html.P(
                    [
                        html.I(
                            className="bi bi-shield-lock me-1",
                            style={"color": "rgba(36, 222, 132, 1)"},
                        ),
                        f"User Type: {user_data['user_type']}",
                    ],
                    style={"font-weight": "500", "color": "#FFFFFF"},
                ),
                html.P(
                    [
                        html.I(
                            className="bi bi-envelope me-1",
                            style={"color": "rgba(36, 222, 132, 1)"},
                        ),
                        f"Email: {user_data['email']}",
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

            # Process user type specific data
            birth_date = user_data.get("date_of_birth", "")
            if birth_date and hasattr(birth_date, "isoformat"):
                birth_date = birth_date.isoformat()
            elif birth_date:
                birth_date = str(birth_date)
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

            return (
                {"display": "block"},  # show info display
                {"display": "block"},  # show form container
                user_data.get("profile_photo", ""),  # profile image
                user_info,  # info text
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
            )

        except Exception as e:
            return (
                {"display": "block"},
                {"display": "none"},
                "",
                f"Error loading user: {str(e)}",
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
                                className="bi bi-person me-1",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            f"Username: {user_data['username']}",
                        ],
                        style={"font-weight": "500", "color": "#FFFFFF"},
                    ),
                    html.P(
                        [
                            html.I(
                                className="bi bi-shield-lock me-1",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            f"User Type: {user_data['user_type']}",
                        ],
                        style={"font-weight": "500", "color": "#FFFFFF"},
                    ),
                    html.P(
                        [
                            html.I(
                                className="bi bi-envelope me-1",
                                style={"color": "rgba(36, 222, 132, 1)"},
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
                                    "color": "rgba(36, 222, 132, 1)",
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
    ):
        """Guarda los cambios del usuario editado."""
        if not n_clicks or not selected_user_id:
            return "", False, "info", no_update

        # Validar campos requeridos
        if not all([name, username, email]):
            return (
                "Please fill in all required fields (*)",
                True,
                "danger",
                no_update,
            )

        # Validar coincidencia de contraseñas si se proporcionan
        if new_password or confirm_password:
            is_valid, error = ValidationController.validate_password_match(
                new_password, confirm_password
            )
            if not is_valid:
                return error, True, "danger", no_update

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
            return (
                f"✅ {message}",
                True,
                "success",
                None,
            )  # Clear selection to refresh
        else:
            return f"❌ {message}", True, "danger", no_update

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
                                    className="bi bi-person me-1",
                                    style={"color": "rgba(36, 222, 132, 1)"},
                                ),
                                f"Name: {user_data['name']}",
                            ],
                            style={"font-weight": "500", "color": "#FFFFFF"},
                        ),
                        html.P(
                            [
                                html.I(
                                    className="bi bi-person-badge me-1",
                                    style={"color": "rgba(36, 222, 132, 1)"},
                                ),
                                f"Username: {user_data['username']}",
                            ],
                            style={"font-weight": "500", "color": "#FFFFFF"},
                        ),
                        html.P(
                            [
                                html.I(
                                    className="bi bi-shield-lock me-1",
                                    style={"color": "rgba(36, 222, 132, 1)"},
                                ),
                                f"User Type: {user_data['user_type']}",
                            ],
                            style={"font-weight": "500", "color": "#FFFFFF"},
                        ),
                        html.P(
                            [
                                html.I(
                                    className="bi bi-envelope me-1",
                                    style={"color": "rgba(36, 222, 132, 1)"},
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

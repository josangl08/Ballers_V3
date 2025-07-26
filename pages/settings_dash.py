# pages/settings_dash.py - Migración visual de settings.py a Dash
import dash_bootstrap_components as dbc
from dash import dcc, html


# Funciones simples para reemplazar cloud_utils removido
def is_streamlit_cloud():
    return False


def show_cloud_feature_limitation(feature_name):
    return f"Feature {feature_name} not available in local mode"


def show_cloud_mode_info():
    return "Running in local mode"


def create_user_form_dash():
    """Crea el formulario de usuario para Dash - migrado exactamente de Streamlit (lines 949-1120)"""

    return dbc.Container(
        [
            # Formulario completo con selector y campos dinámicos
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            # User Type Selector al principio
                            html.H5(
                                "User Information",
                                className="card-title",
                                style={
                                    "color": "rgba(36, 222, 132, 1)",
                                    "font-size": "1.1rem",
                                },
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "User Type *", className="filter-label"
                                            ),
                                            dcc.Dropdown(
                                                id="user-type-selector",
                                                options=[
                                                    {
                                                        "label": "Admin",
                                                        "value": "admin",
                                                    },
                                                    {
                                                        "label": "Coach",
                                                        "value": "coach",
                                                    },
                                                    {
                                                        "label": "Player",
                                                        "value": "player",
                                                    },
                                                ],
                                                value="player",
                                                className="standard-dropdown",
                                                placeholder="Select user type to see specific fields below",
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-4",
                            ),
                            html.H6(
                                "Basic Information",
                                style={
                                    "color": "rgba(36, 222, 132, 1)",
                                    "font-size": "1rem",
                                },
                                className="mb-3",
                            ),
                            # Basic Information (left and right columns como original)
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "Full Name *", className="filter-label"
                                            ),
                                            dbc.Input(
                                                id="new-fullname",
                                                placeholder="Enter full name",
                                                type="text",
                                                className="dash-input",
                                            ),
                                            dbc.Label(
                                                "Username *",
                                                className="mt-2 filter-label",
                                            ),
                                            dbc.Input(
                                                id="new-username",
                                                placeholder="Enter username",
                                                type="text",
                                                className="dash-input",
                                            ),
                                            dbc.Label(
                                                "Email *", className="mt-2 filter-label"
                                            ),
                                            dbc.Input(
                                                id="new-email",
                                                placeholder="Enter email address",
                                                type="email",
                                                className="dash-input",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "Password *", className="filter-label"
                                            ),
                                            dbc.Input(
                                                id="new-password",
                                                placeholder="Enter password",
                                                type="password",
                                                className="dash-input",
                                            ),
                                            dbc.Label(
                                                "Confirm Password *",
                                                className="mt-2 filter-label",
                                            ),
                                            dbc.Input(
                                                id="new-confirm-password",
                                                placeholder="Confirm password",
                                                type="password",
                                                className="dash-input",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Additional Information
                            html.H6(
                                "Additional Information",
                                style={
                                    "color": "rgba(36, 222, 132, 1)",
                                    "font-size": "1rem",
                                },
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "Phone", className="filter-label"
                                            ),
                                            dbc.Input(
                                                id="new-phone",
                                                placeholder="Enter phone number",
                                                type="tel",
                                                className="dash-input",
                                            ),
                                            dbc.Label(
                                                "LINE ID", className="mt-2 filter-label"
                                            ),
                                            dbc.Input(
                                                id="new-line-id",
                                                placeholder="Enter LINE ID",
                                                type="text",
                                                className="dash-input",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "Date of Birth",
                                                className="filter-label",
                                            ),
                                            dbc.Input(
                                                id={
                                                    "type": "auto-hide-date",
                                                    "index": "new-birth-date",
                                                },
                                                type="date",
                                                className="date-filter-input",
                                            ),
                                            # Div de output para auto-hide callback
                                            html.Div(
                                                id={
                                                    "type": "datepicker-output",
                                                    "index": "new-birth-date",
                                                },
                                                style={"display": "none"},
                                            ),
                                            dbc.Label(
                                                "Profile Picture",
                                                className="mt-2 filter-label",
                                            ),
                                            dcc.Upload(
                                                id="new-profile-picture",
                                                children=html.Div(
                                                    [
                                                        "Drag and Drop or ",
                                                        html.A("Select Files"),
                                                    ]
                                                ),
                                                className="upload-area",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Dynamic Type-Specific Fields
                            # Coach Fields
                            html.Div(
                                [
                                    html.H6(
                                        "Coach Information",
                                        style={
                                            "color": "rgba(36, 222, 132, 1)",
                                            "font-size": "1rem",
                                        },
                                    ),
                                    dbc.Label("License Name", className="filter-label"),
                                    dbc.Input(
                                        id="new-license-name",
                                        placeholder="Enter coaching license",
                                        type="text",
                                        className="dash-input",
                                    ),
                                ],
                                id="coach-fields",
                                style={"display": "none"},
                                className="mb-3",
                            ),
                            # Player Fields
                            html.Div(
                                [
                                    html.H6(
                                        "Player Information",
                                        style={
                                            "color": "rgba(36, 222, 132, 1)",
                                            "font-size": "1rem",
                                        },
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "Service Types",
                                                        className="filter-label",
                                                    ),
                                                    dcc.Dropdown(
                                                        id="new-service-types",
                                                        options=[
                                                            {
                                                                "label": "Basic",
                                                                "value": "Basic",
                                                            },
                                                            {
                                                                "label": "Premium",
                                                                "value": "Premium",
                                                            },
                                                            {
                                                                "label": "Elite",
                                                                "value": "Elite",
                                                            },
                                                            {
                                                                "label": "Performance",
                                                                "value": "Performance",
                                                            },
                                                            {
                                                                "label": "Recovery",
                                                                "value": "Recovery",
                                                            },
                                                        ],
                                                        multi=True,
                                                        value=[
                                                            "Basic"
                                                        ],  # Default value como en Streamlit
                                                        placeholder="Select service types...",
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "Number of Enrolled Sessions",
                                                        className="filter-label",
                                                    ),
                                                    dbc.Input(
                                                        id="new-enrolled-sessions",
                                                        type="number",
                                                        min=0,
                                                        value=0,
                                                        className="dash-input",
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    dbc.Label(
                                        "Additional Notes", className="filter-label"
                                    ),
                                    dbc.Textarea(
                                        id="new-player-notes",
                                        placeholder="Add notes about the player...",
                                        rows=4,
                                        className="form-textarea",
                                        style={
                                            "background-color": "#3b3b3a",
                                            "border": "1px solid #555",
                                            "border-radius": "10px",
                                            "color": "#FFFFFF",
                                            "resize": "vertical",
                                            "transition": "all 0.3s ease",
                                            "font-size": "0.9rem",
                                        },
                                    ),
                                ],
                                id="player-fields",
                                style={"display": "block"},
                                className="mb-3",
                            ),
                            # Admin Fields
                            html.Div(
                                [
                                    html.H6(
                                        "Admin Information",
                                        style={
                                            "color": "rgba(36, 222, 132, 1)",
                                            "font-size": "1rem",
                                        },
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "Internal Role",
                                                        className="filter-label",
                                                    ),
                                                    dbc.Input(
                                                        id="new-internal-role",
                                                        placeholder="Enter internal role",
                                                        type="text",
                                                        className="dash-input",
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "Permit Level (1-10)",
                                                        className="filter-label",
                                                    ),
                                                    dbc.Input(
                                                        id="new-permit-level",
                                                        type="number",
                                                        min=1,
                                                        max=10,
                                                        value=5,
                                                        className="dash-input",
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                        ]
                                    ),
                                ],
                                id="admin-fields",
                                style={"display": "none"},
                                className="mb-3",
                            ),
                            # Submit Button con estilo consistente
                            dbc.Button(
                                "Create User",
                                id="create-user-btn",
                                className="btn-admin-style",
                            ),
                        ]
                    )
                ],
                style={
                    "background-color": "rgba(51,51,51,0.6)",
                    "padding": "20px",
                    "border-radius": "10px",
                    "margin-bottom": "20px",
                },
            ),
        ],
        fluid=True,
        style={
            "padding": "20px",
            "min-height": "80vh",
        },
    )


def create_sync_settings_dash():
    """Crea la configuración de sync para Dash - migrado de Streamlit"""

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H5(
                        "Sync Settings",
                        className="card-title",
                        style={"color": "rgba(36, 222, 132, 1)", "font-size": "1.1rem"},
                    ),
                    # Estado actual del sync
                    dbc.Alert(id="sync-status-alert", className="mb-3"),
                    # Configuración de auto-sync
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Auto-sync Interval (minutes)",
                                        className="filter-label",
                                    ),
                                    dbc.Input(
                                        id="sync-interval",
                                        type="number",
                                        min=1,
                                        max=60,
                                        value=5,
                                        style={
                                            "border-radius": "5px",
                                            "border": "1px solid #e0e0e0",
                                        },
                                    ),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Auto-start on Login", className="filter-label"
                                    ),
                                    dbc.Checklist(
                                        id="auto-start-sync",
                                        options=[
                                            {
                                                "label": "Enable auto-start",
                                                "value": "enable",
                                            }
                                        ],
                                        value=[],
                                        className="mt-2",
                                    ),
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-3",
                    ),
                    # Botones de control
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "Start Auto-sync",
                                        id="start-sync-btn",
                                        color="success",
                                        className="w-100",
                                        style={"border-radius": "20px"},
                                    )
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "Stop Auto-sync",
                                        id="stop-sync-btn",
                                        color="danger",
                                        className="w-100",
                                        style={"border-radius": "20px"},
                                    )
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-3",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "🔄 Manual Sync",
                                        id="manual-sync-settings-btn",
                                        color="primary",
                                        className="w-100",
                                        style={
                                            "border-radius": "20px",
                                            "background-color": "#333333",
                                            "color": "rgba(36, 222, 132, 1)",
                                            "border": "none",
                                        },
                                    )
                                ],
                                width=12,
                            )
                        ]
                    ),
                ]
            )
        ],
        style={
            "background-color": "#333333",
            "border-radius": "10px",
            "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
        },
    )


def create_system_settings_dash():
    """Crea la configuración del sistema para Dash - migrado exactamente de Streamlit"""

    return dbc.Container(
        [
            # Sync Results & Monitoring (migrado de lines 936-1000 en settings.py)
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H5(
                                "Sync Results & Monitoring",
                                className="card-title",
                                style={
                                    "color": "rgba(36, 222, 132, 1)",
                                    "font-size": "1.1rem",
                                },
                            ),
                            html.Div(id="sync-results-content"),
                            dbc.Button(
                                "Clear Sync Results",
                                id="clear-sync-results-btn",
                                color="warning",
                                className="w-100 mt-2",
                                style={"border-radius": "20px"},
                            ),
                        ]
                    )
                ],
                className="mb-4",
                style={
                    "background-color": "#333333",
                    "border-radius": "10px",
                    "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
                },
            ),
            # Database/Google Sheets Management (migrado de lines 1002-1020)
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H5(
                                "Database/Google Sheets Management",
                                className="card-title",
                                style={
                                    "color": "rgba(36, 222, 132, 1)",
                                    "font-size": "1.1rem",
                                },
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "Create a backup copy of the database",
                                                id="backup-db-btn",
                                                color="primary",
                                                className="w-100",
                                                style={
                                                    "border-radius": "20px",
                                                    "background-color": "#333333",
                                                    "color": "rgba(36, 222, 132, 1)",
                                                    "border": "none",
                                                },
                                            )
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "Refresh Google Sheets",
                                                id="refresh-sheets-btn",
                                                color="secondary",
                                                className="w-100",
                                                style={
                                                    "border-radius": "20px",
                                                    "background-color": "#333333",
                                                    "color": "rgba(36, 222, 132, 1)",
                                                    "border": "none",
                                                },
                                            )
                                        ],
                                        width=6,
                                    ),
                                ]
                            ),
                        ]
                    )
                ],
                className="mb-4",
                style={
                    "background-color": "#333333",
                    "border-radius": "10px",
                    "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
                },
            ),
            # Manual Synchronization (migrado de lines 1022-1040)
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H5(
                                "Manual Synchronization",
                                className="card-title",
                                style={
                                    "color": "rgba(36, 222, 132, 1)",
                                    "font-size": "1.1rem",
                                },
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "Push local sessions → Google Calendar",
                                                id="sync-to-calendar-btn",
                                                color="success",
                                                className="w-100",
                                                style={"border-radius": "20px"},
                                            )
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "Bring events ← Google Calendar",
                                                id="sync-from-calendar-btn",
                                                color="info",
                                                className="w-100",
                                                style={"border-radius": "20px"},
                                            )
                                        ],
                                        width=6,
                                    ),
                                ]
                            ),
                        ]
                    )
                ],
                className="mb-4",
                style={
                    "background-color": "#333333",
                    "border-radius": "10px",
                    "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
                },
            ),
            # Auto-Sync Management (migrado de lines 1042-1080)
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H5(
                                "Auto-Sync Management",
                                className="card-title",
                                style={
                                    "color": "rgba(36, 222, 132, 1)",
                                    "font-size": "1.1rem",
                                },
                            ),
                            # Estado del auto-sync
                            dbc.Alert(id="auto-sync-status-alert", className="mb-3"),
                            # Configuración de auto-sync
                            html.Div(
                                id="auto-sync-config",
                                children=[
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "Sync Interval (minutes)",
                                                        className="filter-label",
                                                    ),
                                                    dcc.Slider(
                                                        id="sync-interval-slider",
                                                        min=2,
                                                        max=60,
                                                        value=5,
                                                        marks={
                                                            i: str(i)
                                                            for i in [
                                                                2,
                                                                5,
                                                                10,
                                                                15,
                                                                30,
                                                                60,
                                                            ]
                                                        },
                                                        step=1,
                                                        tooltip={
                                                            "placement": "bottom",
                                                            "always_visible": True,
                                                        },
                                                    ),
                                                ],
                                                width=8,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "Auto-start on Login",
                                                        className="filter-label",
                                                    ),
                                                    dbc.Checklist(
                                                        id="auto-start-checkbox",
                                                        options=[
                                                            {
                                                                "label": "Enable auto-start",
                                                                "value": "enable",
                                                            }
                                                        ],
                                                        value=[],
                                                        className="mt-2",
                                                    ),
                                                ],
                                                width=4,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    # Botones de control
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Button(
                                                        "Start Auto-Sync",
                                                        id="start-auto-sync-btn",
                                                        color="success",
                                                        className="w-100",
                                                        style={"border-radius": "20px"},
                                                    )
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Button(
                                                        "Stop Auto-Sync",
                                                        id="stop-auto-sync-btn",
                                                        color="danger",
                                                        className="w-100",
                                                        style={"border-radius": "20px"},
                                                    )
                                                ],
                                                width=6,
                                            ),
                                        ]
                                    ),
                                ],
                            ),
                        ]
                    )
                ],
                style={
                    "background-color": "#333333",
                    "border-radius": "10px",
                    "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
                },
            ),
            # Alert para mensajes
            dbc.Alert(
                id="system-settings-alert",
                is_open=False,
                dismissable=True,
                className="mt-3",
            ),
        ]
    )


def create_settings_dashboard_dash():
    """Crea el dashboard de configuración para Dash - migrado de Streamlit"""

    return dbc.Container(
        [
            # Cabecera principal
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H1(
                                "⚙️ Settings",
                                style={
                                    "color": "rgba(36, 222, 132, 1)",
                                    "text-align": "center",
                                },
                            ),
                            html.P(
                                "Manage users, sync, and system configuration",
                                className="text-center text-muted",
                            ),
                        ],
                        width=12,
                    )
                ],
                className="mb-4",
            ),
            # Navegación por pestañas (migrado de Streamlit)
            dbc.Tabs(
                [
                    dbc.Tab(
                        label="Users",
                        tab_id="users",
                        active_label_style={"color": "rgba(36, 222, 132, 1)"},
                    ),
                    dbc.Tab(
                        label="Sync",
                        tab_id="sync",
                        active_label_style={"color": "rgba(36, 222, 132, 1)"},
                    ),
                    dbc.Tab(
                        label="System",
                        tab_id="system",
                        active_label_style={"color": "rgba(36, 222, 132, 1)"},
                    ),
                    dbc.Tab(
                        label="Reports",
                        tab_id="reports",
                        active_label_style={"color": "rgba(36, 222, 132, 1)"},
                    ),
                ],
                id="settings-tabs",
                active_tab="users",
            ),
            # Contenido de las pestañas
            html.Div(id="settings-tab-content", className="mt-4"),
            # Alerta para mensajes
            dbc.Alert(
                id="settings-alert", is_open=False, dismissable=True, className="mt-3"
            ),
        ]
    )


def create_users_list_dash():
    """Crea la lista de usuarios para Dash - migrado de Streamlit"""

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H5(
                        "Users Management",
                        className="card-title",
                        style={"color": "rgba(36, 222, 132, 1)", "font-size": "1.1rem"},
                    ),
                    # Filtros
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dcc.Dropdown(
                                        id="users-filter-type",
                                        options=[
                                            {"label": "All Users", "value": "all"},
                                            {"label": "Players", "value": "player"},
                                            {"label": "Coaches", "value": "coach"},
                                            {
                                                "label": "Administrators",
                                                "value": "admin",
                                            },
                                        ],
                                        value="all",
                                        style={"border-radius": "5px"},
                                    )
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Input(
                                        id="users-search",
                                        placeholder="Search users...",
                                        type="text",
                                        style={
                                            "border-radius": "5px",
                                            "border": "1px solid #e0e0e0",
                                        },
                                    )
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-3",
                    ),
                    # Tabla de usuarios
                    html.Div(id="users-management-table"),
                ]
            )
        ],
        style={
            "background-color": "#333333",
            "border-radius": "10px",
            "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
        },
    )


# Función principal para mostrar contenido (migrada exactamente de settings.py)
def show_settings_content_dash():
    """Función principal para mostrar el contenido de la sección Settings - MIGRADA DE STREAMLIT."""

    return dbc.Container(
        [
            # Título principal con estilo consistente
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H1(
                                [
                                    html.I(className="bi bi-gear me-3"),
                                    "Settings",
                                ],
                                style={
                                    "color": "rgba(36, 222, 132, 1)",
                                    "margin-bottom": "30px",
                                    "font-size": "2.5rem",
                                },
                            ),
                        ],
                        width=12,
                    ),
                ]
            ),
            # Main tabs (System/Users) con estilo consistente
            dbc.Tabs(
                [
                    dbc.Tab(
                        label="System",
                        tab_id="system-tab",
                        active_label_style={
                            "color": "rgba(36, 222, 132, 1)",
                            "font-weight": "bold",
                        },
                        label_style={"color": "#CCCCCC"},
                    ),
                    dbc.Tab(
                        label="Users",
                        tab_id="users-tab",
                        active_label_style={
                            "color": "rgba(36, 222, 132, 1)",
                            "font-weight": "bold",
                        },
                        label_style={"color": "#CCCCCC"},
                    ),
                ],
                id="settings-main-tabs",
                active_tab="users-tab",  # Cambiar a users como default
                style={
                    "margin-bottom": "30px",
                },
            ),
            # Contenido de las pestañas
            html.Div(id="settings-main-content", className="mt-4"),
            # Alert global para mensajes
            dbc.Alert(
                id="settings-alert",
                is_open=False,
                dismissable=True,
                className="mt-3",
                style={
                    "position": "fixed",
                    "top": "20px",
                    "right": "20px",
                    "z-index": "1060",
                    "min-width": "350px",
                    "max-width": "500px",
                    "box-shadow": "0 8px 16px rgba(0, 0, 0, 0.15)",
                    "border-radius": "8px",
                },
            ),
        ]
    )


# Callback movido a callbacks/settings_callbacks.py


if __name__ == "__main__":
    # Para testing
    pass

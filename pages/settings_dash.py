# pages/settings_dash.py - Migración visual de settings.py a Dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from common.datepicker_utils import create_auto_hide_datepicker
from common.notification_component import NotificationComponent
from common.upload_component import create_upload_component


# Funciones simples para reemplazar cloud_utils removido
def is_streamlit_cloud():
    return False


def show_cloud_feature_limitation(feature_name):
    return f"Feature {feature_name} not available in local mode"


def show_cloud_mode_info():
    return "Running in local mode"


def create_user_form_dash():
    """Crea el formulario de usuario para Dash - migrado exactamente de Streamlit"""

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
                                    "color": "var(--color-primary)",
                                    "font-size": "1.1rem",
                                },
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "User Type *",
                                                className="filter-label",
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
                                                placeholder=(
                                                    "Select user type to see specific "
                                                    "fields below"
                                                ),
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
                                    "color": "var(--color-primary)",
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
                                                "Full Name *",
                                                className="filter-label",
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
                                                "Email *",
                                                className="mt-2 filter-label",
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
                                                "Password *",
                                                className="filter-label",
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
                                            dbc.Label(
                                                "Date of Birth",
                                                className="mt-2 filter-label",
                                            ),
                                            *create_auto_hide_datepicker(
                                                "new-birth-date",
                                                placeholder="Select birth date",
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
                                    "color": "var(--color-primary)",
                                    "font-size": "1rem",
                                },
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "Phone",
                                                className="filter-label",
                                            ),
                                            dbc.Input(
                                                id="new-phone",
                                                placeholder="Enter phone number",
                                                type="tel",
                                                className="dash-input",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "LINE ID",
                                                className="filter-label",
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
                                ],
                                className="mb-3",
                            ),
                            # Profile Picture Row
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "Profile Picture",
                                                className="filter-label",
                                            ),
                                            # Usar componente reutilizable
                                            create_upload_component(
                                                upload_id="new-profile-picture",
                                                preview_id=(
                                                    "new-profile-picture-preview"
                                                ),
                                                clear_btn_id=(
                                                    "new-profile-picture-clear-btn"
                                                ),
                                                title="Profile Picture",
                                            ),
                                        ],
                                        width=12,
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
                                            "color": "var(--color-primary)",
                                            "font-size": "1rem",
                                        },
                                    ),
                                    dbc.Label(
                                        "License Name",
                                        className="filter-label",
                                    ),
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
                                            "color": "var(--color-primary)",
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
                                                        ],  # Default value
                                                        placeholder=(
                                                            "Select service types..."
                                                        ),
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
                                        "Additional Notes",
                                        className="filter-label",
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
                                    # Professional Player Fields
                                    html.Hr(
                                        style={
                                            "border-color": "#555",
                                            "margin": "1.5rem 0",
                                        }
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Checklist(
                                                        options=[
                                                            {
                                                                "label": "Professional Player",
                                                                "value": "professional",
                                                            }
                                                        ],
                                                        value=[],
                                                        id="new-is-professional",
                                                        inline=True,
                                                        style={
                                                            "color": "#FFFFFF",
                                                            "font-weight": "bold",
                                                        },
                                                    ),
                                                    html.Small(
                                                        "Mark this player as professional to enable statistics tracking from Thai League",
                                                        style={
                                                            "color": "#888",
                                                            "font-style": "italic",
                                                        },
                                                    ),
                                                ],
                                                width=12,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "WyscoutID (Optional)",
                                                        className="filter-label",
                                                    ),
                                                    dbc.Input(
                                                        id="new-wyscout-id",
                                                        type="text",
                                                        placeholder="Enter WyscoutID for manual matching...",
                                                        className="dash-input",
                                                        disabled=True,  # Enabled when professional is checked
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        " ",  # Espaciador para alineación
                                                        className="filter-label",
                                                    ),
                                                    dbc.Button(
                                                        [
                                                            html.I(
                                                                className="bi bi-search me-2"
                                                            ),
                                                            "Search",
                                                        ],
                                                        id="new-thai-search-btn",
                                                        className="btn-modal-cancel w-100",
                                                        disabled=True,  # Enabled when professional is checked
                                                    ),
                                                ],
                                                width=3,
                                            ),
                                        ],
                                        className="mb-2",
                                        id="new-wyscout-section",
                                        style={"display": "none"},  # Hidden initially
                                    ),
                                    html.Div(
                                        [
                                            html.Small(
                                                "WyscoutID is used for precise matching with Thai League statistics. Leave empty for automatic matching by name.",
                                                style={
                                                    "color": "#888",
                                                    "font-style": "italic",
                                                },
                                            ),
                                        ],
                                        className="mb-3",
                                        id="new-wyscout-help",
                                        style={"display": "none"},  # Hidden initially
                                    ),
                                    # Modal de matching manual
                                    dbc.Modal(
                                        [
                                            dbc.ModalHeader(
                                                dbc.ModalTitle(
                                                    [
                                                        html.I(
                                                            className="bi bi-search me-2",
                                                            style={
                                                                "color": "#24DE84",
                                                                "font-size": "1.0rem",
                                                            },
                                                        ),
                                                        "Search Thai League Player",
                                                    ],
                                                    style={
                                                        "color": "#FFFFFF",
                                                        "font-weight": "600",
                                                        "font-size": "1.0rem",
                                                    },
                                                ),
                                                close_button=True,
                                                style={
                                                    "background-color": "rgba(51,51,51,1)",
                                                    "border-bottom": "2px solid #24DE84",
                                                    "padding": "1rem 1.5rem",
                                                },
                                            ),
                                            dbc.ModalBody(
                                                [
                                                    dbc.Alert(
                                                        id="matching-search-alert",
                                                        is_open=False,
                                                    ),
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                [
                                                                    dbc.Label(
                                                                        "Player Name:",
                                                                        className="form-label",
                                                                        style={
                                                                            "color": "#FFFFFF"
                                                                        },
                                                                    ),
                                                                    dbc.Input(
                                                                        id="matching-search-input",
                                                                        type="text",
                                                                        placeholder="Enter player name to search...",
                                                                        className="dash-input",
                                                                    ),
                                                                ],
                                                                width=12,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Contenedor de resultados
                                                    html.Div(
                                                        id="matching-results-container",
                                                        style={
                                                            "max-height": "400px",
                                                            "overflow-y": "auto",
                                                        },
                                                    ),
                                                ],
                                                className="modal-body-standard",
                                            ),
                                            dbc.ModalFooter(
                                                [
                                                    dbc.Button(
                                                        [
                                                            html.I(
                                                                className="bi bi-search me-2"
                                                            ),
                                                            "Search",
                                                        ],
                                                        id="matching-search-btn",
                                                        className="btn-modal-cancel me-2",
                                                    ),
                                                    dbc.Button(
                                                        "Cancel",
                                                        id="matching-cancel-btn",
                                                        className="btn-modal-cancel",
                                                    ),
                                                ],
                                                className="modal-footer-standard",
                                            ),
                                        ],
                                        id="thai-league-matching-modal",
                                        size="md",
                                        is_open=False,
                                        style={"z-index": "1060"},
                                        backdrop="static",
                                        fade=True,
                                        centered=True,
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
                                            "color": "var(--color-primary)",
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
                                                        placeholder=(
                                                            "Enter internal role"
                                                        ),
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
    """Crea la configuración de sync para Dash - adaptado para Dash"""

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H5(
                        "Sync Settings",
                        className="card-title",
                        style={
                            "color": "var(--color-primary)",
                            "font-size": "1.1rem",
                        },
                    ),
                    # Estado actual del sync
                    dbc.Alert("", id="sync-status-alert", className="mb-3"),
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
                                        "Auto-start on Login",
                                        className="filter-label",
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
                                        className="btn-admin-style w-100",
                                    )
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "Stop Auto-sync",
                                        id="stop-sync-btn",
                                        className="btn-admin-style w-100",
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
                                        className="btn-admin-style w-100",
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
                                    "color": "var(--color-primary)",
                                    "font-size": "1.1rem",
                                },
                            ),
                            html.Div(id="sync-results-content"),
                            dbc.Button(
                                "Clear Sync Results",
                                id="clear-sync-results-btn",
                                className="btn-admin-style w-100 mt-2",
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
                                    "color": "var(--color-primary)",
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
                                                className="btn-admin-style w-100",
                                            )
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "Refresh Google Sheets",
                                                id="refresh-sheets-btn",
                                                className="btn-admin-style w-100",
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
            # Manual Synchronization (limpiado: solo Manual Sync y Pull from Google)
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H5(
                                "Manual Synchronization",
                                className="card-title",
                                style={
                                    "color": "var(--color-primary)",
                                    "font-size": "1.1rem",
                                },
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "Manual Sync Now (2-way)",
                                                id="manual-sync-btn",
                                                className="btn-admin-style w-100",
                                            )
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "Pull from Google Calendar",
                                                id="sync-from-calendar-btn",
                                                className="btn-admin-style w-100",
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
            # Intervalo de refresco de resultados de sync (también se actualiza en clicks)
            dcc.Interval(
                id="sync-results-refresh-interval",
                interval=10_000,  # 10 segundos
                n_intervals=0,
            ),
            # Alert para mensajes (oculto, solo para propagar eventos/mensajes a Monitoring)
            dbc.Alert(
                "",
                id="system-settings-alert",
                is_open=False,
                dismissable=False,
                className="mt-3",
                style={"display": "none"},
            ),
            # Real-time Sync Management (Webhook-based)
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H5(
                                "Real-time Sync Management",
                                className="card-title",
                                style={
                                    "color": "var(--color-primary)",
                                    "font-size": "1.1rem",
                                },
                            ),
                            # Webhook status display (placeholder)
                            dbc.Alert(
                                "🚀 Webhook-based real-time sync (implementation in progress)",
                                color="info",
                                className="mb-3",
                            ),
                            # Manual sync as fallback
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "Manual Sync Now",
                                                id="manual-sync-btn",
                                                className="btn-admin-style w-100",
                                            )
                                        ],
                                        width=12,
                                    ),
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
            ),
            # Alert para mensajes
            dbc.Alert(
                "",
                id="system-settings-alert",
                is_open=False,
                dismissable=True,
                className="mt-3",
            ),
        ]
    )


def create_settings_dashboard_dash():
    """Crea el dashboard de configuración para Dash - adaptado para Dash"""

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
                                    "color": "var(--color-primary)",
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
            # Navegación por pestañas (adaptado para Dash)
            dbc.Tabs(
                [
                    dbc.Tab(
                        label="Users",
                        tab_id="users",
                        active_label_style={"color": "var(--color-primary)"},
                    ),
                    dbc.Tab(
                        label="Sync",
                        tab_id="sync",
                        active_label_style={"color": "var(--color-primary)"},
                    ),
                    dbc.Tab(
                        label="System",
                        tab_id="system",
                        active_label_style={"color": "var(--color-primary)"},
                    ),
                    dbc.Tab(
                        label="Reports",
                        tab_id="reports",
                        active_label_style={"color": "var(--color-primary)"},
                    ),
                ],
                id="settings-tabs",
                active_tab="users",
            ),
            # Contenido de las pestañas
            html.Div(id="settings-tab-content", className="mt-4"),
            # Alerta para mensajes
            dbc.Alert(
                "",
                id="settings-alert",
                is_open=False,
                dismissable=True,
                className="mt-3",
            ),
        ]
    )


def create_edit_user_form_dash():
    """Crea el formulario de edición de usuario para Dash."""

    return dbc.Container(
        [
            # User Selection Section
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H5(
                                "Select User to Edit",
                                className="card-title",
                                style={
                                    "color": "var(--color-primary)",
                                    "font-size": "1.1rem",
                                },
                            ),
                            dcc.Dropdown(
                                id="edit-user-selector",
                                placeholder="Select a user to edit...",
                                className="standard-dropdown",
                                style={"margin-bottom": "20px"},
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
            # User Info Display Section (hidden until user selected)
            html.Div(
                id="edit-user-info-display",
                style={"display": "none"},
                children=[
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H5(
                                        "Current User Information",
                                        style={
                                            "color": "var(--color-primary)",
                                            "font-size": "1.1rem",
                                            "margin-bottom": "20px",
                                        },
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.Img(
                                                        id="edit-user-profile-image",
                                                        src="",
                                                        style={
                                                            "width": "150px",
                                                            "height": "150px",
                                                            "border-radius": "50%",
                                                            "object-fit": "cover",
                                                        },
                                                    ),
                                                    # Badge Professional/Amateur
                                                    html.Div(
                                                        id="edit-user-professional-badge",
                                                        style={
                                                            "text-align": "center",
                                                            "margin-top": "10px",
                                                            "display": "none",
                                                        },
                                                    ),
                                                ],
                                                width=4,
                                            ),
                                            dbc.Col(
                                                [html.Div(id="edit-user-info-text")],
                                                width=8,
                                            ),
                                        ]
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
                    )
                ],
            ),
            # Edit Form Section (hidden until user selected)
            html.Div(
                id="edit-user-form-container",
                style={"display": "none"},
                children=[
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H5(
                                        "Edit User Information",
                                        className="card-title",
                                        style={
                                            "color": "var(--color-primary)",
                                            "font-size": "1.1rem",
                                        },
                                    ),
                                    # Basic Information
                                    html.H6(
                                        "Basic Information",
                                        style={
                                            "color": "var(--color-primary)",
                                            "font-size": "1rem",
                                        },
                                        className="mb-3 mt-4",
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "Full Name *",
                                                        className="filter-label",
                                                    ),
                                                    dbc.Input(
                                                        id="edit-fullname",
                                                        placeholder="Enter full name",
                                                        type="text",
                                                        className="dash-input",
                                                    ),
                                                    dbc.Label(
                                                        "Username *",
                                                        className="mt-2 filter-label",
                                                    ),
                                                    dbc.Input(
                                                        id="edit-username",
                                                        placeholder="Enter username",
                                                        type="text",
                                                        className="dash-input",
                                                    ),
                                                    dbc.Label(
                                                        "Email *",
                                                        className="mt-2 filter-label",
                                                    ),
                                                    dbc.Input(
                                                        id="edit-email",
                                                        placeholder=(
                                                            "Enter email address"
                                                        ),
                                                        type="email",
                                                        className="dash-input",
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "Phone",
                                                        className="filter-label",
                                                    ),
                                                    dbc.Input(
                                                        id="edit-phone",
                                                        placeholder=(
                                                            "Enter phone number"
                                                        ),
                                                        type="tel",
                                                        className="dash-input",
                                                    ),
                                                    dbc.Label(
                                                        "LINE ID",
                                                        className="mt-2 filter-label",
                                                    ),
                                                    dbc.Input(
                                                        id="edit-line-id",
                                                        placeholder="Enter LINE ID",
                                                        type="text",
                                                        className="dash-input",
                                                    ),
                                                    dbc.Label(
                                                        "Date of Birth",
                                                        className="mt-2 filter-label",
                                                    ),
                                                    *create_auto_hide_datepicker(
                                                        "edit-birth-date",
                                                        placeholder="Select birth date",
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    # User Type and Status in same row
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "User Type *",
                                                        className="filter-label",
                                                    ),
                                                    dcc.Dropdown(
                                                        id="edit-user-type-selector",
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
                                                        className=("standard-dropdown"),
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "User Status",
                                                        className="filter-label",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Span(
                                                                id=(
                                                                    "edit-user-status-text"
                                                                ),
                                                                style={
                                                                    "color": "#FFFFFF",
                                                                    "font-weight": "500",
                                                                    "margin-right": (
                                                                        "10px"
                                                                    ),
                                                                    "display": (
                                                                        "inline-block"
                                                                    ),
                                                                },
                                                            ),
                                                            dbc.Button(
                                                                id="edit-user-status-toggle-btn",
                                                                size="sm",
                                                                className="btn-admin-style",
                                                                style={
                                                                    "font-size": "0.8rem",
                                                                    "padding": "0.2rem 0.8rem",
                                                                },
                                                            ),
                                                        ],
                                                        className="mt-2",
                                                        style={
                                                            "display": ("flex"),
                                                            "align-items": ("center"),
                                                        },
                                                    ),
                                                    # Hidden field to store current status
                                                    dcc.Store(
                                                        id="edit-user-current-status"
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                        ],
                                        className="mb-4",
                                    ),
                                    # Dynamic Type-Specific Fields
                                    # Coach Fields
                                    html.Div(
                                        [
                                            html.H6(
                                                "Coach Information",
                                                style={
                                                    "color": "var(--color-primary)",
                                                    "font-size": "1rem",
                                                },
                                            ),
                                            dbc.Label(
                                                "License Name",
                                                className="filter-label",
                                            ),
                                            dbc.Input(
                                                id="edit-license-name",
                                                placeholder="Enter coaching license",
                                                type="text",
                                                className="dash-input",
                                            ),
                                        ],
                                        id="edit-coach-fields",
                                        style={"display": "none"},
                                        className="mb-3",
                                    ),
                                    # Player Fields
                                    html.Div(
                                        [
                                            html.H6(
                                                "Player Information",
                                                style={
                                                    "color": "var(--color-primary)",
                                                    "font-size": "1rem",
                                                },
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Label(
                                                                "Service Types",
                                                                className=(
                                                                    "filter-label"
                                                                ),
                                                            ),
                                                            dcc.Dropdown(
                                                                id="edit-service-types",
                                                                options=[
                                                                    {
                                                                        "label": (
                                                                            "Basic"
                                                                        ),
                                                                        "value": (
                                                                            "Basic"
                                                                        ),
                                                                    },
                                                                    {
                                                                        "label": (
                                                                            "Premium"
                                                                        ),
                                                                        "value": (
                                                                            "Premium"
                                                                        ),
                                                                    },
                                                                    {
                                                                        "label": (
                                                                            "Elite"
                                                                        ),
                                                                        "value": (
                                                                            "Elite"
                                                                        ),
                                                                    },
                                                                    {
                                                                        "label": (
                                                                            "Performance"
                                                                        ),
                                                                        "value": (
                                                                            "Performance"
                                                                        ),
                                                                    },
                                                                    {
                                                                        "label": (
                                                                            "Recovery"
                                                                        ),
                                                                        "value": (
                                                                            "Recovery"
                                                                        ),
                                                                    },
                                                                ],
                                                                multi=True,
                                                                placeholder=(
                                                                    "Select service types..."
                                                                ),
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label(
                                                                "Number of Enrolled Sessions",
                                                                className=(
                                                                    "filter-label"
                                                                ),
                                                            ),
                                                            dbc.Input(
                                                                id="edit-enrolled-sessions",
                                                                type="number",
                                                                min=0,
                                                                className="dash-input",
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            dbc.Label(
                                                "Additional Notes",
                                                className="filter-label",
                                            ),
                                            dbc.Textarea(
                                                id="edit-player-notes",
                                                placeholder=(
                                                    "Add notes about the player..."
                                                ),
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
                                            # Professional Player Fields
                                            html.Hr(
                                                style={
                                                    "border-color": "#555",
                                                    "margin": "1.5rem 0",
                                                }
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Checklist(
                                                                options=[
                                                                    {
                                                                        "label": "Professional Player",
                                                                        "value": "professional",
                                                                    }
                                                                ],
                                                                value=[],
                                                                id="edit-is-professional",
                                                                inline=True,
                                                                style={
                                                                    "color": "#FFFFFF",
                                                                    "font-weight": "bold",
                                                                },
                                                            ),
                                                            html.Small(
                                                                "Mark this player as professional to enable statistics tracking from Thai League",
                                                                style={
                                                                    "color": "#888",
                                                                    "font-style": "italic",
                                                                },
                                                            ),
                                                        ],
                                                        width=12,
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Label(
                                                                "WyscoutID (Optional)",
                                                                className="filter-label",
                                                            ),
                                                            dbc.Input(
                                                                id="edit-wyscout-id",
                                                                type="text",
                                                                placeholder="Enter WyscoutID for manual matching...",
                                                                className="dash-input",
                                                                disabled=True,  # Enabled when professional is checked
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label(
                                                                " ",  # Espaciador para alineación
                                                                className="filter-label",
                                                            ),
                                                            dbc.Button(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-search me-2"
                                                                    ),
                                                                    "Search",
                                                                ],
                                                                id="edit-wyscout-search-btn",
                                                                className="btn-modal-cancel w-100",
                                                                disabled=True,  # Enabled when user is selected
                                                            ),
                                                        ],
                                                        width=3,
                                                    ),
                                                ],
                                                className="mb-2",
                                                id="edit-wyscout-section",
                                                style={
                                                    "display": "none"
                                                },  # Hidden initially
                                            ),
                                            html.Div(
                                                [
                                                    html.Small(
                                                        "Click 'Search Player' to find and match players from Thai League database. WyscoutID is used for precise statistical matching.",
                                                        style={
                                                            "color": "#888",
                                                            "font-style": "italic",
                                                        },
                                                    ),
                                                ],
                                                id="edit-wyscout-help",
                                                className="mb-3",
                                                style={
                                                    "display": "none"
                                                },  # Hidden initially
                                            ),
                                            # Modal de matching manual para edición
                                            dbc.Modal(
                                                [
                                                    dbc.ModalHeader(
                                                        dbc.ModalTitle(
                                                            [
                                                                html.I(
                                                                    className="bi bi-search me-2",
                                                                    style={
                                                                        "color": "#24DE84",
                                                                        "font-size": "1.0rem",
                                                                    },
                                                                ),
                                                                "Search Thai League Player",
                                                            ],
                                                            style={
                                                                "color": "#FFFFFF",
                                                                "font-weight": "600",
                                                                "font-size": "1.0rem",
                                                            },
                                                        ),
                                                        close_button=True,
                                                        style={
                                                            "background-color": "rgba(51,51,51,1)",
                                                            "border-bottom": "2px solid #24DE84",
                                                            "padding": "1rem 1.5rem",
                                                        },
                                                    ),
                                                    dbc.ModalBody(
                                                        [
                                                            dbc.Alert(
                                                                id="edit-matching-search-alert",
                                                                is_open=False,
                                                            ),
                                                            dbc.Row(
                                                                [
                                                                    dbc.Col(
                                                                        [
                                                                            dbc.Label(
                                                                                "Player Name:",
                                                                                className="form-label",
                                                                                style={
                                                                                    "color": "#FFFFFF"
                                                                                },
                                                                            ),
                                                                            dbc.Input(
                                                                                id="edit-matching-search-input",
                                                                                type="text",
                                                                                placeholder="Enter player name to search...",
                                                                                className="dash-input",
                                                                            ),
                                                                        ],
                                                                        width=12,
                                                                    ),
                                                                ],
                                                                className="mb-3",
                                                            ),
                                                            # Contenedor de resultados
                                                            html.Div(
                                                                id="edit-matching-results-container",
                                                                style={
                                                                    "max-height": "400px",
                                                                    "overflow-y": "auto",
                                                                },
                                                            ),
                                                        ],
                                                        className="modal-body-standard",
                                                    ),
                                                    dbc.ModalFooter(
                                                        [
                                                            dbc.Button(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-search me-2"
                                                                    ),
                                                                    "Search",
                                                                ],
                                                                id="edit-matching-search-btn",
                                                                className="btn-modal-cancel me-2",
                                                            ),
                                                            dbc.Button(
                                                                "Cancel",
                                                                id="edit-matching-cancel-btn",
                                                                className="btn-modal-cancel",
                                                            ),
                                                        ],
                                                        className="modal-footer-standard",
                                                    ),
                                                ],
                                                id="edit-thai-league-matching-modal",
                                                size="md",
                                                is_open=False,
                                                style={"z-index": "1060"},
                                                backdrop="static",
                                                fade=True,
                                                centered=True,
                                            ),
                                        ],
                                        id="edit-player-fields",
                                        style={"display": "none"},
                                        className="mb-3",
                                    ),
                                    # Admin Fields
                                    html.Div(
                                        [
                                            html.H6(
                                                "Admin Information",
                                                style={
                                                    "color": "var(--color-primary)",
                                                    "font-size": "1rem",
                                                },
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Label(
                                                                "Internal Role",
                                                                className=(
                                                                    "filter-label"
                                                                ),
                                                            ),
                                                            dbc.Input(
                                                                id="edit-internal-role",
                                                                placeholder=(
                                                                    "Enter internal role"
                                                                ),
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
                                                                className=(
                                                                    "filter-label"
                                                                ),
                                                            ),
                                                            dbc.Input(
                                                                id="edit-permit-level",
                                                                type="number",
                                                                min=1,
                                                                max=10,
                                                                className="dash-input",
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                ]
                                            ),
                                        ],
                                        id="edit-admin-fields",
                                        style={"display": "none"},
                                        className="mb-3",
                                    ),
                                    # Password Change Section
                                    html.Hr(),
                                    html.H6(
                                        "Change Password (Optional)",
                                        style={
                                            "color": "var(--color-primary)",
                                            "font-size": "1rem",
                                        },
                                        className="mb-3",
                                    ),
                                    dbc.Alert(
                                        "As an administrator, you can change the password "
                                        "without knowing the previous password.",
                                        color="info",
                                        className="mb-3",
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "New Password",
                                                        className="filter-label",
                                                    ),
                                                    dbc.Input(
                                                        id="edit-new-password",
                                                        placeholder=(
                                                            "Enter new password"
                                                        ),
                                                        type="password",
                                                        className="dash-input",
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "Confirm New Password",
                                                        className="filter-label",
                                                    ),
                                                    dbc.Input(
                                                        id="edit-confirm-password",
                                                        placeholder=(
                                                            "Confirm new password"
                                                        ),
                                                        type="password",
                                                        className="dash-input",
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    # Profile Picture Change Section
                                    html.Hr(),
                                    html.H6(
                                        "Change Profile Picture (Optional)",
                                        style={
                                            "color": "var(--color-primary)",
                                            "font-size": "1rem",
                                        },
                                        className="mb-3",
                                    ),
                                    # Usar componente reutilizable
                                    create_upload_component(
                                        upload_id="edit-profile-picture",
                                        preview_id="edit-profile-picture-preview",
                                        clear_btn_id="clear-profile-picture-btn",
                                        title="New Profile Picture",
                                    ),
                                    # Action Buttons
                                    html.Hr(),
                                    html.Div(
                                        [
                                            dbc.Button(
                                                "Save Changes",
                                                id="save-user-changes-btn",
                                                className="btn-admin-style",
                                                style={
                                                    "margin-right": "15px",
                                                },
                                            ),
                                            dbc.Button(
                                                [
                                                    html.I(
                                                        className="bi bi-trash me-2"
                                                    ),
                                                    "Delete User",
                                                ],
                                                id="show-delete-confirmation-btn",
                                                className="btn-delete",
                                                style={
                                                    "color": "#dc3545",
                                                },
                                            ),
                                        ],
                                        style={
                                            "text-align": "left",
                                            "margin-top": "10px",
                                        },
                                        className="mb-3",
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
                    )
                ],
            ),
            # Delete Confirmation Modal (styled like administration)
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle(
                            [
                                html.I(
                                    className="bi bi-exclamation-triangle me-2",
                                    style={
                                        "color": "#24DE84",
                                        "font-size": "1.0rem",
                                    },
                                ),
                                "Confirm Delete",
                            ],
                            style={
                                "color": "#FFFFFF",
                                "font-weight": "600",
                                "font-size": "1.0rem",
                            },
                        ),
                        style={
                            "background-color": "rgba(51,51,51,1)",
                            "border-bottom": "2px solid #24DE84",
                            "padding": "1rem 1.5rem",
                        },
                    ),
                    dbc.ModalBody(
                        [
                            html.P(
                                "Do you really want to delete this user? "
                                "This action cannot be undone.",
                                style={
                                    "color": "#FFFFFF",
                                    "font-size": "0.9rem",
                                    "margin-bottom": "1rem",
                                    "text-align": "center",
                                    "line-height": "1.5",
                                },
                            ),
                            html.Div(
                                id="delete-user-info-display",
                                style={"margin-bottom": "1rem"},
                            ),
                            html.Hr(
                                style={
                                    "border-color": "#24DE84",
                                    "margin": "1rem 0",
                                }
                            ),
                            dbc.Label(
                                "Type 'DELETE' to confirm:",
                                style={
                                    "color": "#FFFFFF",
                                    "font-weight": "500",
                                },
                            ),
                            dbc.Input(
                                id="delete-confirmation-input",
                                placeholder="Type DELETE to confirm",
                                type="text",
                                className="dash-input",
                                style={
                                    "margin-top": "0.5rem",
                                },
                            ),
                        ],
                        className="modal-body-standard",
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id="cancel-delete-btn",
                                className="btn-modal-cancel",
                                style={
                                    "margin-right": "15px",
                                },
                            ),
                            dbc.Button(
                                [
                                    html.I(className="bi bi-trash me-2"),
                                    "Delete",
                                ],
                                id="confirm-delete-btn",
                                className="btn-delete",
                                disabled=True,
                            ),
                        ],
                        className="modal-footer-standard",
                    ),
                ],
                id="delete-confirmation-modal",
                is_open=False,
                style={"z-index": "1060"},
                backdrop="static",
                fade=True,
                size="md",
                centered=True,
            ),
        ],
        fluid=True,
        style={
            "padding": "20px",
            "min-height": "80vh",
        },
    )


def create_users_list_dash():
    """Crea la lista de usuarios para Dash - adaptado para Dash"""

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H5(
                        "Users Management",
                        className="card-title",
                        style={
                            "color": "var(--color-primary)",
                            "font-size": "1.1rem",
                        },
                    ),
                    # Filtros
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dcc.Dropdown(
                                        id="users-filter-type",
                                        options=[
                                            {
                                                "label": "All Users",
                                                "value": "all",
                                            },
                                            {
                                                "label": "Players",
                                                "value": "player",
                                            },
                                            {
                                                "label": "Coaches",
                                                "value": "coach",
                                            },
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
def show_settings_content_dash(session_data=None):
    """Función principal para mostrar el contenido de la sección Settings."""

    return dbc.Container(
        [
            # Global user type store - needed for navigation callbacks
            dcc.Store(
                id="user-type-store",
                data=session_data.get("user_type") if session_data else None,
            ),
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
                                    "color": "var(--color-primary)",
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
                            "color": "var(--color-primary)",
                            "font-weight": "bold",
                        },
                        label_style={"color": "#CCCCCC"},
                    ),
                    dbc.Tab(
                        label="Users",
                        tab_id="users-tab",
                        active_label_style={
                            "color": "var(--color-primary)",
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
            # Sistema de notificaciones centralizado
            *NotificationComponent.create_notification_system("settings"),
        ]
    )


def create_user_status_dash():
    """Crea el tab de User Status para Dash - reutilizando estructura existente"""

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H5(
                        "User Status Management",
                        className="card-title",
                        style={
                            "color": "var(--color-primary)",
                            "font-size": "1.1rem",
                        },
                    ),
                    # Filtros - usando clases estándar del proyecto
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Filter by User Type:",
                                        className="filter-label",
                                    ),
                                    dcc.Dropdown(
                                        id="user-status-type-filter",
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
                                        className="standard-dropdown",
                                    ),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Filter by Status:",
                                        className="filter-label",
                                    ),
                                    dcc.Dropdown(
                                        id="user-status-status-filter",
                                        options=[
                                            {"label": "All Status", "value": "all"},
                                            {"label": "Active", "value": "active"},
                                            {"label": "Inactive", "value": "inactive"},
                                        ],
                                        value="all",
                                        className="standard-dropdown",
                                    ),
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-3",
                    ),
                    # Tabla de usuarios - reutilizamos el contenedor existente
                    html.Div(id="user-status-table-container", children=[]),
                ]
            )
        ],
        style={
            "background-color": "#333333",
            "border-radius": "10px",
            "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
        },
    )


# Callback movido a callbacks/settings_callbacks.py


if __name__ == "__main__":
    # Para testing
    pass

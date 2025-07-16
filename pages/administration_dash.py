# pages/administration_dash.py - Migración exacta copiando estructura de ballers_dash.py
import datetime

import dash_bootstrap_components as dbc
from dash import dcc, html


def show_administration_content_dash():
    """Función principal para mostrar el contenido de Administration"""

    return dbc.Container(
        [
            # Título principal
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H1(
                                [
                                    html.I(className="bi bi-shield-lock me-3"),
                                    "Administration",
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
            # Main tabs (Sessions/Financials)
            dbc.Tabs(
                [
                    dbc.Tab(
                        label="Sessions",
                        tab_id="sessions-tab",
                        active_label_style={"color": "rgba(36, 222, 132, 1)"},
                        label_style={"color": "#FFFFFF"},
                    ),
                    dbc.Tab(
                        label="Financials",
                        tab_id="financials-tab",
                        active_label_style={"color": "rgba(36, 222, 132, 1)"},
                        label_style={"color": "#FFFFFF"},
                    ),
                ],
                id="admin-main-tabs",
                active_tab="sessions-tab",
                style={"margin-bottom": "40px"},
            ),
            # Tab content
            html.Div(id="admin-main-content"),
            # Store for user type
            dcc.Store(id="admin-user-type-store", data="admin"),
            # Store for status filters
            dcc.Store(
                id="admin-status-filters", data=["scheduled", "completed", "canceled"]
            ),
        ]
    )


def create_sessions_content():
    """Crea el contenido de sessions copiando exactamente la estructura de ballers"""

    return html.Div(
        [
            # COPIANDO EXACTAMENTE LA ESTRUCTURA DE BALLERS_DASH PROFILES
            html.Div(
                [
                    html.H5(
                        [
                            html.I(className="bi bi-calendar-week me-2"),
                            "Sessions Calendar",
                        ],
                        style={
                            "color": "rgba(36, 222, 132, 1)",
                            "margin-bottom": "20px",
                            "font-size": "1.1rem",
                        },
                    ),
                    dbc.Row(
                        [
                            # Filtros de fecha combinados en una sola columna
                            dbc.Col(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "From",
                                                        style={
                                                            "color": "#FFFFFF",
                                                            "font-weight": "500",
                                                            "font-size": "0.9rem",
                                                        },
                                                    ),
                                                    dbc.Input(
                                                        id="filter-from-date",
                                                        type="date",
                                                        className="custom-date-input",
                                                        value=(
                                                            datetime.date.today()
                                                            - datetime.timedelta(days=7)
                                                        ).isoformat(),
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "To",
                                                        style={
                                                            "color": "#FFFFFF",
                                                            "font-weight": "500",
                                                            "font-size": "0.9rem",
                                                        },
                                                    ),
                                                    dbc.Input(
                                                        id="filter-to-date",
                                                        type="date",
                                                        className="custom-date-input",
                                                        value=(
                                                            datetime.date.today()
                                                            + datetime.timedelta(
                                                                days=21
                                                            )
                                                        ).isoformat(),
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                        ]
                                    )
                                ],
                                width=4,
                                lg=4,
                                md=6,
                                sm=12,
                            ),
                            # Status badges centrados
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            dbc.Label(
                                                "Status",
                                                style={
                                                    "color": "#FFFFFF",
                                                    "font-weight": "500",
                                                    "margin-bottom": "8px",
                                                    "font-size": "0.9rem",
                                                },
                                            ),
                                            html.Div(
                                                [
                                                    html.Span(
                                                        "Scheduled",
                                                        id="admin-status-scheduled",
                                                        className="status-scheduled",
                                                        style={
                                                            "cursor": "pointer",
                                                            "margin-right": "10px",
                                                        },
                                                    ),
                                                    html.Span(
                                                        "Completed",
                                                        id="admin-status-completed",
                                                        className="status-completed",
                                                        style={
                                                            "cursor": "pointer",
                                                            "margin-right": "10px",
                                                        },
                                                    ),
                                                    html.Span(
                                                        "Canceled",
                                                        id="admin-status-canceled",
                                                        className="status-canceled",
                                                        style={
                                                            "cursor": "pointer",
                                                        },
                                                    ),
                                                ],
                                                style={"text-align": "center"},
                                            ),
                                        ],
                                        style={"text-align": "center"},
                                    )
                                ],
                                width=4,
                                lg=4,
                                md=6,
                                sm=12,
                            ),
                            # Coach filter
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Coach",
                                        style={
                                            "color": "#FFFFFF",
                                            "font-weight": "500",
                                            "font-size": "0.9rem",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="admin-filter-coach",
                                        placeholder="All Coaches",
                                        className="custom-dropdown",
                                        style={"color": "#000"},
                                    ),
                                ],
                                width=4,
                                lg=4,
                                md=12,
                                sm=12,
                            ),
                        ],
                        className="mb-4",
                    ),
                    # Calendario - directo sobre fondo
                    html.Div(
                        [html.Div(id="admin-calendar")],
                        style={"margin-bottom": "30px", "margin-top": "20px"},
                    ),
                    # Lista de sesiones - directo sobre fondo
                    html.Div(
                        [
                            html.H6(
                                [
                                    html.I(className="bi bi-list-ul me-2"),
                                    "Sessions List",
                                ],
                                style={
                                    "color": "rgba(36, 222, 132, 1)",
                                    "margin-bottom": "15px",
                                    "font-size": "1rem",
                                },
                            ),
                            html.Div(id="admin-sessions-table"),
                        ],
                        style={"margin-bottom": "30px"},
                    ),
                ],
                style={"margin-bottom": "30px"},
            ),
            # Sessions Management section
            html.Hr(style={"border-color": "#555555", "margin": "40px 0"}),
            html.H5(
                [
                    html.I(className="bi bi-gear me-2"),
                    "Sessions Management",
                ],
                style={
                    "color": "rgba(36, 222, 132, 1)",
                    "margin-bottom": "20px",
                    "font-size": "1.1rem",
                },
            ),
            # Tabs para Create/Edit copiando estilo de ballers
            dbc.Tabs(
                [
                    dbc.Tab(
                        label="Create Session",
                        tab_id="create-session",
                        active_label_style={
                            "color": "rgba(36, 222, 132, 1)",
                            "font-size": "0.9rem",
                        },
                        label_style={"font-size": "0.9rem"},
                    ),
                    dbc.Tab(
                        label="Edit Session",
                        tab_id="edit-session",
                        active_label_style={
                            "color": "rgba(36, 222, 132, 1)",
                            "font-size": "0.9rem",
                        },
                        label_style={"font-size": "0.9rem"},
                    ),
                ],
                id="admin-session-tabs",
                active_tab="create-session",
                style={"margin-bottom": "20px"},
            ),
            # Contenido de las tabs
            html.Div(id="admin-session-tab-content", style={"margin-top": "20px"}),
            # Alert para mensajes
            dbc.Alert(
                id="admin-alert", is_open=False, dismissable=True, className="mb-3"
            ),
        ]
    )


def create_session_form():
    """Crea el formulario para crear sesiones copiando estructura de ballers"""

    return dbc.Container(
        [
            html.H5(
                [
                    html.I(className="bi bi-plus-circle me-2"),
                    "New Session",
                ],
                style={
                    "color": "rgba(36, 222, 132, 1)",
                    "margin-bottom": "20px",
                    "font-size": "1.1rem",
                },
            ),
            # Form usando el mismo estilo que ballers
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label(
                                "Coach",
                                style={"color": "#FFFFFF", "margin-bottom": "8px"},
                            ),
                            dcc.Dropdown(
                                id="admin-new-session-coach",
                                placeholder="Select coach...",
                                className="custom-dropdown",
                                style={"color": "#000"},
                            ),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Label(
                                "Player",
                                style={"color": "#FFFFFF", "margin-bottom": "8px"},
                            ),
                            dcc.Dropdown(
                                id="admin-new-session-player",
                                placeholder="Select player...",
                                className="custom-dropdown",
                                style={"color": "#000"},
                            ),
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
                            dbc.Label(
                                "Date",
                                style={"color": "#FFFFFF", "margin-bottom": "8px"},
                            ),
                            dbc.Input(
                                id="admin-new-session-date",
                                type="date",
                                className="custom-date-input",
                                value=datetime.date.today().isoformat(),
                            ),
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Label(
                                "Start hour",
                                style={"color": "#FFFFFF", "margin-bottom": "8px"},
                            ),
                            dcc.Dropdown(
                                id="admin-new-session-start-time",
                                placeholder="Select start time...",
                                className="custom-dropdown",
                                style={"color": "#000"},
                            ),
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Label(
                                "End hour",
                                style={"color": "#FFFFFF", "margin-bottom": "8px"},
                            ),
                            dcc.Dropdown(
                                id="admin-new-session-end-time",
                                placeholder="Select end time...",
                                className="custom-dropdown",
                                style={"color": "#000"},
                            ),
                        ],
                        width=4,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label(
                                "Notes",
                                style={"color": "#FFFFFF", "margin-bottom": "8px"},
                            ),
                            dbc.Textarea(
                                id="admin-new-session-notes",
                                placeholder="Add notes...",
                                rows=4,
                                style={
                                    "background-color": "#333333",
                                    "border": "1px solid #555555",
                                    "border-radius": "10px",
                                    "color": "#FFFFFF",
                                    "resize": "vertical",
                                },
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
            # Save button usando estilo verde
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                "Save Session",
                                id="admin-save-session-btn",
                                style={
                                    "background-color": "rgba(36, 222, 132, 1)",
                                    "border": "none",
                                    "border-radius": "10px",
                                    "color": "#FFFFFF",
                                    "padding": "10px 30px",
                                    "font-weight": "500",
                                },
                            ),
                        ],
                        width=12,
                    ),
                ]
            ),
        ]
    )


def create_edit_session_form():
    """Crea el formulario para editar sesiones"""

    return dbc.Container(
        [
            html.H5(
                [
                    html.I(className="bi bi-pencil-square me-2"),
                    "Edit / Delete Session",
                ],
                style={
                    "color": "rgba(36, 222, 132, 1)",
                    "margin-bottom": "20px",
                    "font-size": "1.1rem",
                },
            ),
            # Session selector
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label(
                                "Select session",
                                style={"color": "#FFFFFF", "margin-bottom": "8px"},
                            ),
                            dcc.Dropdown(
                                id="admin-edit-session-selector",
                                placeholder="Select session to edit...",
                                className="custom-dropdown",
                                style={"color": "#000"},
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
            # Container for edit form (will be populated dynamically)
            html.Div(id="admin-edit-session-form-container"),
        ]
    )


def create_financials_content():
    """Crea el contenido de financials"""

    return html.Div(
        [
            html.H5(
                [
                    html.I(className="bi bi-calculator me-2"),
                    "Financial Management",
                ],
                style={
                    "color": "rgba(36, 222, 132, 1)",
                    "margin-bottom": "20px",
                    "font-size": "1.1rem",
                },
            ),
            # Export buttons
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.ButtonGroup(
                                [
                                    dbc.Button(
                                        [
                                            html.I(
                                                className="bi bi-file-earmark-pdf me-2"
                                            ),
                                            "Export PDF",
                                        ],
                                        id="admin-financials-export-btn",
                                        style={
                                            "background-color": "rgba(36, 222, 132, 1)",
                                            "border": "none",
                                            "border-radius": "10px",
                                        },
                                    ),
                                    dbc.Button(
                                        [
                                            html.I(className="bi bi-printer me-2"),
                                            "Print",
                                        ],
                                        id="admin-financials-print-btn",
                                        style={
                                            "background-color": "#666666",
                                            "border": "none",
                                            "border-radius": "10px",
                                        },
                                    ),
                                ]
                            ),
                        ],
                        width=12,
                        className="text-end mb-4",
                    ),
                ]
            ),
            # Financial content
            html.Div(id="admin-financials-content"),
            html.Div(id="admin-financials-metrics", className="mb-4"),
            html.Div(id="admin-financials-chart"),
        ]
    )


if __name__ == "__main__":
    # Para testing
    pass

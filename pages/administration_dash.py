# pages/administration_dash.py - Migración exacta copiando estructura de ballers_dash.py
import datetime

import dash_bootstrap_components as dbc
from dash import dcc, html


def create_fixed_calendar_component():
    """Crea el componente del calendario fijo usando el controller."""
    try:
        from controllers.internal_calendar import create_fixed_calendar_dash

        return create_fixed_calendar_dash(key="admin-cal", height=650)
    except Exception as e:
        return html.Div(
            f"Error loading calendar: {str(e)}",
            style={"color": "red", "text-align": "center", "padding": "20px"},
        )


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
            # Store for active filter in edit session
            dcc.Store(id="admin-active-filter", data=None),
            # Input invisible para search (usado en callbacks)
            dbc.Input(id="admin-session-search", style={"display": "none"}),
            # Toast alert (invisible inicialmente, se posiciona con callback)
            dbc.Alert(
                id="admin-alert",
                is_open=False,
                dismissable=True,
                style={"display": "none"},  # Inicialmente oculto
            ),
            # Stores básicos para funcionalidad
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
                                                    html.Div(
                                                        [
                                                            dbc.Label(
                                                                "From",
                                                                className=(
                                                                    "filter-label"
                                                                ),
                                                            ),
                                                            dbc.Input(
                                                                id="filter-from-date",
                                                                type="date",  # noqa: E501
                                                                className="date-filter-input",  # noqa: E501
                                                                value=(
                                                                    datetime.date.today()  # noqa: E501
                                                                    - datetime.timedelta(  # noqa: E501
                                                                        days=7
                                                                    )
                                                                ).isoformat(),  # noqa: E501
                                                            ),
                                                        ],
                                                        className=(
                                                            "date-filter-container"
                                                        ),
                                                    )
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    html.Div(
                                                        [
                                                            dbc.Label(
                                                                "To",
                                                                className=(
                                                                    "filter-label"
                                                                ),
                                                            ),
                                                            dbc.Input(
                                                                id="filter-to-date",
                                                                type="date",  # noqa: E501
                                                                className="date-filter-input",  # noqa: E501
                                                                value=(
                                                                    datetime.date.today()  # noqa: E501
                                                                    + datetime.timedelta(  # noqa: E501
                                                                        days=21
                                                                    )
                                                                ).isoformat(),  # noqa: E501
                                                            ),
                                                        ],
                                                        className=(
                                                            "date-filter-container"
                                                        ),
                                                    )
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
                                                className="filter-label",
                                            ),
                                            html.Div(
                                                [
                                                    html.Span(
                                                        "Scheduled",
                                                        id=("admin-status-scheduled"),
                                                        className=(
                                                            "status-scheduled "
                                                            "status-badge"
                                                        ),
                                                    ),
                                                    html.Span(
                                                        "Completed",
                                                        id=("admin-status-completed"),
                                                        className=(
                                                            "status-completed "
                                                            "status-badge"
                                                        ),
                                                    ),
                                                    html.Span(
                                                        "Canceled",
                                                        id=("admin-status-canceled"),
                                                        className=(
                                                            "status-canceled "
                                                            "status-badge"
                                                        ),
                                                    ),
                                                ],
                                                className="status-badges-container",
                                            ),
                                        ],
                                        className="status-filter-container",
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
                                    html.Div(
                                        [
                                            dbc.Label(
                                                "Coach",
                                                className="filter-label",
                                            ),
                                            dcc.Dropdown(
                                                id="admin-filter-coach",
                                                placeholder="All Coaches",
                                                className="standard-dropdown",
                                            ),
                                        ],
                                        className="coach-filter-container",
                                    )
                                ],
                                width=4,
                                lg=4,
                                md=12,
                                sm=12,
                            ),
                        ],
                        className="mb-4",
                    ),
                    # Calendario - Pre-cargado para carga instantánea
                    html.Div(
                        [
                            html.Div(
                                create_fixed_calendar_component(), id="admin-calendar"
                            )
                        ],
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
                            html.Div(
                                [html.Div(id="admin-sessions-table")],
                                style={
                                    "max-height": "400px",
                                    "overflow-y": "auto",
                                    "overflow-x": "hidden",
                                },
                            ),
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
            # Script para forzar cierre del minicalendario y auto-resize del calendario
            html.Script(
                """
            document.addEventListener('DOMContentLoaded', function() {
                // Agregar evento a los inputs de fecha para forzar cierre
                const dateInputs = document.querySelectorAll('input[type="date"]');
                dateInputs.forEach(input => {
                    input.addEventListener('change', function() {
                        this.blur(); // Quitar foco del input para cerrar el calendario
                    });
                });
            });
            """
            ),
        ]
    )


def create_session_form():
    """Formulario simplificado para crear sesiones"""

    return html.Div(
        [
            html.Div(
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
                    # Primera fila: Coach y Player
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label(
                                        "Coach",
                                        style={
                                            "color": "#FFFFFF",
                                            "margin-bottom": "8px",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="admin-new-session-coach",
                                        placeholder="Select coach...",
                                        className="standard-dropdown",
                                    ),
                                ],
                                style={"width": "48%", "display": "inline-block"},
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Player",
                                        style={
                                            "color": "#FFFFFF",
                                            "margin-bottom": "8px",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="admin-new-session-player",
                                        placeholder="Select player...",
                                        className="standard-dropdown",
                                    ),
                                ],
                                style={
                                    "width": "48%",
                                    "display": "inline-block",
                                    "margin-left": "4%",
                                },
                            ),
                        ],
                        style={"margin-bottom": "20px"},
                    ),
                    # Segunda fila: Date, Start time, End time
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label(
                                        "Date",
                                        style={
                                            "color": "#FFFFFF",
                                            "margin-bottom": "8px",
                                        },
                                    ),
                                    dbc.Input(
                                        id="admin-new-session-date",
                                        type="date",
                                        className="date-filter-input",
                                        value=datetime.date.today().isoformat(),
                                    ),
                                ],
                                style={"width": "30%", "display": "inline-block"},
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Start hour",
                                        style={
                                            "color": "#FFFFFF",
                                            "margin-bottom": "8px",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="admin-new-session-start-time",
                                        placeholder="Select start time...",
                                        className="standard-dropdown",
                                    ),
                                ],
                                style={
                                    "width": "30%",
                                    "display": "inline-block",
                                    "margin-left": "5%",
                                },
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "End hour",
                                        style={
                                            "color": "#FFFFFF",
                                            "margin-bottom": "8px",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="admin-new-session-end-time",
                                        placeholder="Select end time...",
                                        className="standard-dropdown",
                                    ),
                                ],
                                style={
                                    "width": "30%",
                                    "display": "inline-block",
                                    "margin-left": "5%",
                                },
                            ),
                        ],
                        style={"margin-bottom": "20px"},
                    ),
                    # Tercera fila: Notes
                    html.Div(
                        [
                            html.Label(
                                "Notes",
                                style={"color": "#FFFFFF", "margin-bottom": "8px"},
                            ),
                            dbc.Textarea(
                                id="admin-new-session-notes",
                                placeholder="Add notes...",
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
                        style={"margin-bottom": "20px"},
                    ),
                    # Botón de guardar
                    html.Div(
                        [
                            dbc.Button(
                                "Save Session",
                                id="admin-save-session-btn",
                                style={
                                    "background-color": "#1D1B1A",
                                    "color": "#FFFFFF",
                                    "border": "2px solid #1D1B1A",
                                    "border-radius": "20px",
                                    "font-weight": "500",
                                    "padding": "0.4rem 1.2rem",
                                    "transition": "all 0.3s ease",
                                    "cursor": "pointer",
                                    "display": "inline-block",
                                    "width": "auto",
                                    "font-size": "0.9rem",
                                },
                            ),
                        ],
                        style={"text-align": "left", "margin-top": "10px"},
                    ),
                ],
                style={
                    "background-color": "rgba(51,51,51,0.6)",
                    "padding": "20px",
                    "border-radius": "10px",
                    "margin-bottom": "20px",
                },
            )
        ]
    )


def create_edit_session_form():
    """Formulario completo para editar sesiones - migrado desde Streamlit"""

    return html.Div(
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
            # Formulario completo de edición con selector incluido
            html.Div(
                [
                    # Primera fila: Filtros rápidos temporales
                    html.Div(
                        [
                            html.Label(
                                "Quick filters",
                                style={"color": "#FFFFFF", "margin-bottom": "8px"},
                            ),
                            html.Div(
                                [
                                    # Grupo de filtros principales
                                    html.Div(
                                        [
                                            html.Button(
                                                "Last Month",
                                                id="filter-last-month",
                                                className="btn-filter-quick",
                                                style={
                                                    "background-color": "#3b3b3a",
                                                    "border": "1px solid #555",
                                                    "color": "#FFFFFF",
                                                    "border-radius": "15px",
                                                    "padding": "6px 12px",
                                                    "margin-right": "12px",
                                                    "margin-bottom": "6px",
                                                    "font-size": "0.8rem",
                                                    "cursor": "pointer",
                                                    "transition": "all 0.3s ease",
                                                },
                                            ),
                                            html.Button(
                                                "Last Week",
                                                id="filter-last-week",
                                                className="btn-filter-quick",
                                                style={
                                                    "background-color": "#3b3b3a",
                                                    "border": "1px solid #555",
                                                    "color": "#FFFFFF",
                                                    "border-radius": "15px",
                                                    "padding": "6px 12px",
                                                    "margin-right": "12px",
                                                    "margin-bottom": "6px",
                                                    "font-size": "0.8rem",
                                                    "cursor": "pointer",
                                                    "transition": "all 0.3s ease",
                                                },
                                            ),
                                            html.Button(
                                                "Yesterday",
                                                id="filter-yesterday",
                                                className="btn-filter-quick",
                                                style={
                                                    "background-color": "#3b3b3a",
                                                    "border": "1px solid #555",
                                                    "color": "#FFFFFF",
                                                    "border-radius": "15px",
                                                    "padding": "6px 12px",
                                                    "margin-right": "12px",
                                                    "margin-bottom": "6px",
                                                    "font-size": "0.8rem",
                                                    "cursor": "pointer",
                                                    "transition": "all 0.3s ease",
                                                },
                                            ),
                                            html.Button(
                                                "Today",
                                                id="filter-today",
                                                className="btn-filter-quick",
                                                style={
                                                    "background-color": "#3b3b3a",
                                                    "border": "1px solid #555",
                                                    "color": "#FFFFFF",
                                                    "border-radius": "15px",
                                                    "padding": "6px 12px",
                                                    "margin-right": "12px",
                                                    "margin-bottom": "6px",
                                                    "font-size": "0.8rem",
                                                    "cursor": "pointer",
                                                    "transition": "all 0.3s ease",
                                                },
                                            ),
                                            html.Button(
                                                "Tomorrow",
                                                id="filter-tomorrow",
                                                className="btn-filter-quick",
                                                style={
                                                    "background-color": "#3b3b3a",
                                                    "border": "1px solid #555",
                                                    "color": "#FFFFFF",
                                                    "border-radius": "15px",
                                                    "padding": "6px 12px",
                                                    "margin-right": "12px",
                                                    "margin-bottom": "6px",
                                                    "font-size": "0.8rem",
                                                    "cursor": "pointer",
                                                    "transition": "all 0.3s ease",
                                                },
                                            ),
                                            html.Button(
                                                "This Week",
                                                id="filter-this-week",
                                                className="btn-filter-quick",
                                                style={
                                                    "background-color": "#3b3b3a",
                                                    "border": "1px solid #555",
                                                    "color": "#FFFFFF",
                                                    "border-radius": "15px",
                                                    "padding": "6px 12px",
                                                    "margin-right": "12px",
                                                    "margin-bottom": "6px",
                                                    "font-size": "0.8rem",
                                                    "cursor": "pointer",
                                                    "transition": "all 0.3s ease",
                                                },
                                            ),
                                            html.Button(
                                                "This Month",
                                                id="filter-this-month",
                                                className="btn-filter-quick",
                                                style={
                                                    "background-color": "#3b3b3a",
                                                    "border": "1px solid #555",
                                                    "color": "#FFFFFF",
                                                    "border-radius": "15px",
                                                    "padding": "6px 12px",
                                                    "margin-right": "12px",
                                                    "margin-bottom": "6px",
                                                    "font-size": "0.8rem",
                                                    "cursor": "pointer",
                                                    "transition": "all 0.3s ease",
                                                },
                                            ),
                                        ],
                                        style={
                                            "display": "flex",
                                            "flex-wrap": "wrap",
                                            "align-items": "center",
                                        },
                                    ),
                                    # Botón Clear separado a la derecha
                                    html.Button(
                                        "Clear",
                                        id="filter-clear",
                                        className="btn-filter-clear",
                                        style={
                                            "background-color": "#dc3545",
                                            "border": "1px solid #dc3545",
                                            "color": "#FFFFFF",
                                            "border-radius": "15px",
                                            "padding": "6px 12px",
                                            "margin-bottom": "6px",
                                            "font-size": "0.8rem",
                                            "cursor": "pointer",
                                            "transition": "all 0.3s ease",
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "flex-wrap": "wrap",
                                    "align-items": "center",
                                    "justify-content": "space-between",
                                },
                            ),
                        ],
                        style={"margin-bottom": "20px"},
                    ),
                    # Segunda fila: Buscador y Selector de sesiones
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label(
                                        "Search sessions",
                                        style={
                                            "color": "#FFFFFF",
                                            "margin-bottom": "8px",
                                        },
                                    ),
                                    dbc.Input(
                                        id="admin-session-search-visible",
                                        type="text",
                                        placeholder="Search by coach, player, ID...",
                                        className="custom-date-input",
                                        style={
                                            "background-color": "#3b3b3a",
                                            "border": "1px solid #555",
                                            "color": "#FFFFFF",
                                            "height": "38px",
                                        },
                                    ),
                                ],
                                style={"width": "30%", "display": "inline-block"},
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Select session",
                                        style={
                                            "color": "#FFFFFF",
                                            "margin-bottom": "8px",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="admin-edit-session-selector",
                                        placeholder="Select session to edit...",
                                        className="standard-dropdown",
                                        style={"height": "38px"},
                                    ),
                                ],
                                style={
                                    "width": "70%",
                                    "display": "inline-block",
                                    "margin-left": "0%",
                                },
                            ),
                        ],
                        style={
                            "margin-bottom": "25px",
                            "display": "flex",
                            "align-items": "flex-end",
                            "gap": "10px",
                        },
                    ),
                    # Advertencia si la sesión está fuera de horarios recomendados
                    html.Div(
                        id="admin-edit-session-warning", style={"margin-bottom": "15px"}
                    ),
                    # Primera fila: Coach y Player
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label(
                                        "Coach",
                                        style={
                                            "color": "#FFFFFF",
                                            "margin-bottom": "8px",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="admin-edit-session-coach",
                                        placeholder="Select coach...",
                                        className="standard-dropdown",
                                    ),
                                ],
                                style={"width": "48%", "display": "inline-block"},
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Player",
                                        style={
                                            "color": "#FFFFFF",
                                            "margin-bottom": "8px",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="admin-edit-session-player",
                                        placeholder="Select player...",
                                        className="standard-dropdown",
                                    ),
                                ],
                                style={
                                    "width": "48%",
                                    "display": "inline-block",
                                    "margin-left": "4%",
                                },
                            ),
                        ],
                        style={"margin-bottom": "20px"},
                    ),
                    # Segunda fila: Status, Date, Start time, End time
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label(
                                        "Status",
                                        style={
                                            "color": "#FFFFFF",
                                            "margin-bottom": "8px",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="admin-edit-session-status",
                                        placeholder="Select status...",
                                        className="standard-dropdown",
                                        options=[
                                            {
                                                "label": "Scheduled",
                                                "value": "scheduled",
                                            },
                                            {
                                                "label": "Completed",
                                                "value": "completed",
                                            },
                                            {"label": "Canceled", "value": "canceled"},
                                        ],
                                    ),
                                ],
                                style={"width": "22%", "display": "inline-block"},
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Date",
                                        style={
                                            "color": "#FFFFFF",
                                            "margin-bottom": "8px",
                                        },
                                    ),
                                    dbc.Input(
                                        id="admin-edit-session-date",
                                        type="date",
                                        className="date-filter-input",
                                    ),
                                ],
                                style={
                                    "width": "22%",
                                    "display": "inline-block",
                                    "margin-left": "4%",
                                },
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Start hour",
                                        style={
                                            "color": "#FFFFFF",
                                            "margin-bottom": "8px",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="admin-edit-session-start-time",
                                        placeholder="Select start time...",
                                        className="standard-dropdown",
                                    ),
                                ],
                                style={
                                    "width": "22%",
                                    "display": "inline-block",
                                    "margin-left": "4%",
                                },
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "End hour",
                                        style={
                                            "color": "#FFFFFF",
                                            "margin-bottom": "8px",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="admin-edit-session-end-time",
                                        placeholder="Select end time...",
                                        className="standard-dropdown",
                                    ),
                                ],
                                style={
                                    "width": "22%",
                                    "display": "inline-block",
                                    "margin-left": "4%",
                                },
                            ),
                        ],
                        style={"margin-bottom": "20px"},
                    ),
                    # Tercera fila: Notes
                    html.Div(
                        [
                            html.Label(
                                "Notes",
                                style={"color": "#FFFFFF", "margin-bottom": "8px"},
                            ),
                            dbc.Textarea(
                                id="admin-edit-session-notes",
                                placeholder="Add notes...",
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
                        style={"margin-bottom": "20px"},
                    ),
                    # Botones Save y Delete
                    html.Div(
                        [
                            dbc.Button(
                                "Save Changes",
                                id="admin-update-session-btn",
                                style={
                                    "background-color": "#1D1B1A",
                                    "color": "#FFFFFF",
                                    "border": "2px solid #1D1B1A",
                                    "border-radius": "20px",
                                    "font-weight": "500",
                                    "padding": "0.4rem 1.2rem",
                                    "transition": "all 0.3s ease",
                                    "cursor": "pointer",
                                    "display": "inline-block",
                                    "width": "auto",
                                    "margin-right": "15px",
                                    "font-size": "0.9rem",
                                },
                            ),
                            dbc.Button(
                                [
                                    html.I(className="bi bi-trash me-2"),
                                    "Delete Session",
                                ],
                                id="admin-delete-session-btn",
                                className="btn-delete",
                                style={
                                    "background-color": "#1D1B1A",
                                    "color": "#dc3545",
                                    "border": "2px solid #1D1B1A",
                                    "border-radius": "20px",
                                    "font-weight": "500",
                                    "padding": "0.4rem 1.2rem",
                                    "transition": "all 0.3s ease",
                                    "cursor": "pointer",
                                    "display": "inline-block",
                                    "width": "auto",
                                    "font-size": "0.9rem",
                                },
                            ),
                        ],
                        style={"text-align": "left", "margin-top": "10px"},
                    ),
                ],
                style={
                    "background-color": "rgba(51,51,51,0.6)",
                    "padding": "20px",
                    "border-radius": "10px",
                    "margin-bottom": "20px",
                },
            ),
            # Modal de confirmación para Delete
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle(
                            [
                                html.I(
                                    className="bi bi-exclamation-triangle me-2",
                                    style={"color": "#24DE84", "font-size": "1.0rem"},
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
                                id="admin-delete-confirmation-text",
                                children="Do you really want to delete this "
                                "session? This action cannot be undone.",
                                style={
                                    "color": "#FFFFFF",
                                    "font-size": "0.9rem",
                                    "margin-bottom": "0",
                                    "text-align": "center",
                                    "line-height": "1.5",
                                },
                            )
                        ],
                        style={
                            "background-color": "rgba(51,51,51,1)",
                            "padding": "2rem 1.5rem",
                            "border": "none",
                        },
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id="admin-delete-cancel-btn",
                                style={
                                    "background-color": "#1D1B1A",
                                    "color": "#FFFFFF",
                                    "border": "2px solid #1D1B1A",
                                    "border-radius": "20px",
                                    "font-weight": "500",
                                    "padding": "0.4rem 1.2rem",
                                    "transition": "all 0.3s ease",
                                    "cursor": "pointer",
                                    "display": "inline-block",
                                    "width": "auto",
                                    "margin-right": "15px",
                                    "font-size": "0.9rem",
                                },
                            ),
                            dbc.Button(
                                [html.I(className="bi bi-trash me-2"), "Delete"],
                                id="admin-delete-confirm-btn",
                                className="btn-delete",
                                style={
                                    "background-color": "#1D1B1A",
                                    "color": "#dc3545",
                                    "border": "2px solid #1D1B1A",
                                    "border-radius": "20px",
                                    "font-weight": "500",
                                    "padding": "0.4rem 1.2rem",
                                    "transition": "all 0.3s ease",
                                    "cursor": "pointer",
                                    "display": "inline-block",
                                    "width": "auto",
                                    "font-size": "0.9rem",
                                },
                            ),
                        ],
                        style={
                            "background-color": "rgba(51,51,51,1)",
                            "border-top": "2px solid #24DE84",
                            "padding": "1rem 1.5rem",
                            "justify-content": "flex-start",
                            "display": "flex",
                        },
                    ),
                ],
                id="admin-delete-confirmation-modal",
                is_open=False,
                style={"z-index": "1060"},
                backdrop="static",  # No cerrar al hacer click fuera
                fade=True,
                size="md",
                centered=True,
            ),
            # Store para datos de la sesión seleccionada
            dcc.Store(id="admin-selected-session-data"),
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
            # Export button - mismo estilo que Export Profile PDF
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                [
                                    html.I(className="bi bi-file-earmark-pdf me-2"),
                                    "Export Financial PDF",
                                ],
                                id="admin-financials-export-btn",
                                className="custom-button",
                                style={
                                    "border-radius": "20px",
                                    "background-color": "#333333",
                                    "color": "#24DE84",
                                    "border": "none",
                                    "padding": "0.5rem 1rem",
                                    "font-weight": "500",
                                    "transition": "all 0.3s ease",
                                },
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

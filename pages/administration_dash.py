# pages/administration_dash.py - Migración visual de administration.py a Dash
import datetime as dt
import os
import sys
from typing import Optional

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, callback, dcc, html, no_update

from common.cloud_utils import (
    is_streamlit_cloud,
    show_cloud_feature_limitation,
    show_cloud_mode_info,
)
from common.export import (
    create_download_link,
    show_export_error_message,
    show_export_success_message,
    trigger_browser_print,
)
from controllers.export_controller import generate_financials_pdf, generate_sessions_pdf
from controllers.internal_calendar import show_calendar
from controllers.notification_controller import get_sync_problems
from controllers.session_controller import (
    SessionController,
    create_session_with_calendar,
    delete_session_with_calendar,
    update_session_with_calendar,
)
from controllers.sheets_controller import get_accounting_df
from controllers.sync_coordinator import (
    filter_sync_results_by_coach,
    get_coach_id_if_needed,
)
from controllers.validation_controller import (
    ValidationController,
    check_session_time_recommendation,
    get_create_session_hours,
    get_edit_session_hours,
    validate_coach_selection_safe,
    validate_player_selection_safe,
    validate_session_form_data,
)
from models import Coach, Session, SessionStatus, User


def create_session_form_dash():
    """Crea el formulario de sesión para Dash - migrado exactamente de Streamlit"""

    return dbc.Container(
        [
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H5(
                                "📅 Create New Session",
                                className="card-title",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            # Información básica de la sesión
                            html.H6(
                                "📋 Basic Information",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Session Date *"),
                                            dbc.Input(
                                                id="new-session-date",
                                                type="date",
                                                style={
                                                    "border-radius": "5px",
                                                    "border": "1px solid #e0e0e0",
                                                },
                                            ),
                                        ],
                                        width=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Start Time *"),
                                            dbc.Input(
                                                id="new-session-time",
                                                type="time",
                                                style={
                                                    "border-radius": "5px",
                                                    "border": "1px solid #e0e0e0",
                                                },
                                            ),
                                        ],
                                        width=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Duration (minutes) *"),
                                            dbc.Input(
                                                id="new-session-duration",
                                                type="number",
                                                min=15,
                                                max=240,
                                                value=60,
                                                style={
                                                    "border-radius": "5px",
                                                    "border": "1px solid #e0e0e0",
                                                },
                                            ),
                                        ],
                                        width=4,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Asignación de personal y jugadores
                            html.H6(
                                "👥 Assignment",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Coach *"),
                                            dcc.Dropdown(
                                                id="new-session-coach",
                                                placeholder="Select a coach...",
                                                style={"border-radius": "5px"},
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Session Type *"),
                                            dcc.Dropdown(
                                                id="new-session-type",
                                                options=[
                                                    {
                                                        "label": "🏃‍♀️ Training",
                                                        "value": "training",
                                                    },
                                                    {
                                                        "label": "⚽ Match",
                                                        "value": "match",
                                                    },
                                                    {
                                                        "label": "📊 Evaluation",
                                                        "value": "evaluation",
                                                    },
                                                    {
                                                        "label": "🎯 Personal Training",
                                                        "value": "personal",
                                                    },
                                                ],
                                                value="training",
                                                style={"border-radius": "5px"},
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
                                            dbc.Label("Players"),
                                            dcc.Dropdown(
                                                id="new-session-players",
                                                placeholder="Select players (optional for open sessions)...",
                                                multi=True,
                                                style={"border-radius": "5px"},
                                            ),
                                        ],
                                        width=12,
                                    )
                                ],
                                className="mb-3",
                            ),
                            # Información financiera y adicional
                            html.H6(
                                "💰 Financial & Additional",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Price per Player (€)"),
                                            dbc.Input(
                                                id="new-session-price",
                                                type="number",
                                                min=0,
                                                step=0.01,
                                                value=20.00,
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
                                            dbc.Label("Maximum Participants"),
                                            dbc.Input(
                                                id="new-session-max-participants",
                                                type="number",
                                                min=1,
                                                max=20,
                                                value=10,
                                                style={
                                                    "border-radius": "5px",
                                                    "border": "1px solid #e0e0e0",
                                                },
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
                                            dbc.Label("Session Notes"),
                                            dbc.Textarea(
                                                id="new-session-notes",
                                                placeholder="Add any additional notes or instructions for this session...",
                                                style={
                                                    "border-radius": "5px",
                                                    "border": "1px solid #e0e0e0",
                                                },
                                                rows=3,
                                            ),
                                        ],
                                        width=12,
                                    )
                                ],
                                className="mb-3",
                            ),
                            # Configuración de sincronización
                            html.H6(
                                "🔄 Sync Settings",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Checklist(
                                                id="session-sync-options",
                                                options=[
                                                    {
                                                        "label": "🗓️ Sync to Google Calendar",
                                                        "value": "calendar",
                                                    },
                                                    {
                                                        "label": "📧 Send email notifications",
                                                        "value": "email",
                                                    },
                                                    {
                                                        "label": "📱 Send SMS reminders",
                                                        "value": "sms",
                                                    },
                                                ],
                                                value=["calendar"],
                                                className="mb-3",
                                            )
                                        ],
                                        width=12,
                                    )
                                ],
                                className="mb-3",
                            ),
                            # Botones de acción
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "📅 Create Session",
                                                id="create-session-submit-btn",
                                                color="success",
                                                size="lg",
                                                className="w-100",
                                                style={"border-radius": "20px"},
                                            )
                                        ],
                                        width=8,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "🔍 Check Time Conflicts",
                                                id="check-conflicts-btn",
                                                color="warning",
                                                size="lg",
                                                className="w-100",
                                                style={"border-radius": "20px"},
                                            )
                                        ],
                                        width=4,
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
                id="session-form-alert",
                is_open=False,
                dismissable=True,
                className="mt-3",
            ),
        ]
    )


def create_sessions_list_dash():
    """Crea la lista de sesiones para Dash - migrado exactamente de Streamlit"""

    return dbc.Container(
        [
            # Filtros mejorados (migrado del original)
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H5(
                                "🔍 Session Filters",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("From Date"),
                                            dbc.Input(
                                                id="admin-filter-date-start",
                                                type="date",
                                                style={"border-radius": "5px"},
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("To Date"),
                                            dbc.Input(
                                                id="admin-filter-date-end",
                                                type="date",
                                                style={"border-radius": "5px"},
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Status"),
                                            dcc.Dropdown(
                                                id="admin-filter-status",
                                                options=[
                                                    {"label": "All", "value": "all"},
                                                    {
                                                        "label": "✅ Completed",
                                                        "value": "completed",
                                                    },
                                                    {
                                                        "label": "📅 Scheduled",
                                                        "value": "scheduled",
                                                    },
                                                    {
                                                        "label": "❌ Canceled",
                                                        "value": "canceled",
                                                    },
                                                ],
                                                value="all",
                                                style={"border-radius": "5px"},
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Coach"),
                                            dcc.Dropdown(
                                                id="admin-filter-coach",
                                                options=[],  # Se llenará dinámicamente
                                                placeholder="All coaches",
                                                style={"border-radius": "5px"},
                                            ),
                                        ],
                                        width=3,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Button(
                                "🔍 Apply Filters",
                                id="admin-apply-filters-btn",
                                color="primary",
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
            # Sessions Management (migrado del original)
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H5(
                                "📋 Sessions Management",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            # Calendario integrado
                            html.Div(id="admin-calendar-view", className="mb-4"),
                            # Lista de sesiones
                            html.Div(id="admin-sessions-table"),
                            # Botones de export y acciones
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "📊 Export Sessions PDF",
                                                id="export-sessions-pdf-btn",
                                                color="primary",
                                                className="me-2",
                                                style={
                                                    "border-radius": "20px",
                                                    "background-color": "#333333",
                                                    "color": "rgba(36, 222, 132, 1)",
                                                    "border": "none",
                                                },
                                            ),
                                            dbc.Button(
                                                "🖨️ Print Sessions",
                                                id="print-sessions-btn",
                                                color="secondary",
                                                className="me-2",
                                                style={
                                                    "border-radius": "20px",
                                                    "background-color": "#666666",
                                                    "color": "white",
                                                    "border": "none",
                                                },
                                            ),
                                            dbc.Button(
                                                "🔄 Sync with Calendar",
                                                id="sync-calendar-btn",
                                                color="info",
                                                style={"border-radius": "20px"},
                                            ),
                                        ],
                                        width=12,
                                        className="text-center",
                                    )
                                ],
                                className="mt-3",
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
        ]
    )


def create_sync_alerts_dash():
    """Crea las alertas de sync para Dash - migrado de Streamlit"""

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H5(
                        "🔄 Sync Status",
                        className="card-title",
                        style={"color": "rgba(36, 222, 132, 1)"},
                    ),
                    html.Div(id="sync-alerts-content"),
                    dbc.Button(
                        "🔄 Manual Sync",
                        id="manual-sync-btn",
                        color="info",
                        className="w-100 mt-3",
                        style={"border-radius": "20px"},
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


def create_administration_dashboard_dash():
    """Crea el dashboard de administración para Dash - migrado de Streamlit"""

    return dbc.Container(
        [
            # Cabecera principal
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H1(
                                "⚙️ Administration",
                                style={
                                    "color": "rgba(36, 222, 132, 1)",
                                    "text-align": "center",
                                },
                            ),
                            html.P(
                                "Manage sessions, users, and system settings",
                                className="text-center text-muted",
                            ),
                        ],
                        width=12,
                    )
                ],
                className="mb-4",
            ),
            # Navegación por pestañas (migrado exactamente de Streamlit)
            dbc.Tabs(
                [
                    dbc.Tab(
                        label="📅 Sessions",
                        tab_id="sessions",
                        active_label_style={"color": "rgba(36, 222, 132, 1)"},
                    ),
                    dbc.Tab(
                        label="💰 Financials",
                        tab_id="financials",
                        active_label_style={"color": "rgba(36, 222, 132, 1)"},
                    ),
                ],
                id="admin-tabs",
                active_tab="sessions",
            ),
            # Contenido de las pestañas
            html.Div(id="admin-tab-content", className="mt-4"),
            # Alerta para mensajes
            dbc.Alert(
                id="admin-alert", is_open=False, dismissable=True, className="mt-3"
            ),
        ]
    )


def create_users_management_dash():
    """Crea la gestión de usuarios para Dash - migrado de Streamlit"""

    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H4(
                                "👥 Users Management",
                                style={"color": "rgba(36, 222, 132, 1)"},
                            ),
                            html.P(
                                "Manage players, coaches, and administrators",
                                className="text-muted",
                            ),
                        ],
                        width=8,
                    ),
                    dbc.Col(
                        [
                            dbc.Button(
                                "➕ Add User",
                                id="add-user-btn",
                                color="success",
                                className="float-end",
                                style={"border-radius": "20px"},
                            )
                        ],
                        width=4,
                    ),
                ],
                className="mb-4",
            ),
            # Filtros de usuarios
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dcc.Dropdown(
                                id="user-type-filter",
                                options=[
                                    {"label": "All Users", "value": "all"},
                                    {"label": "Players", "value": "player"},
                                    {"label": "Coaches", "value": "coach"},
                                    {"label": "Administrators", "value": "admin"},
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
                                id="user-search",
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
                className="mb-4",
            ),
            # Tabla de usuarios
            html.Div(id="users-table-container"),
        ]
    )


# Función principal para mostrar contenido (migrada exactamente de administration.py)
def show_administration_content_dash():
    """Función principal para mostrar el contenido de la sección Administration - MIGRADA DE STREAMLIT."""

    return html.Div(
        [
            # Título de la sección (migrado de Streamlit)
            html.H3(
                "Administration",
                style={"color": "rgba(36, 222, 132, 1)", "text-align": "center"},
                className="section-title mb-4",
            ),
            # Contenido según el tipo de usuario (migrada la lógica de Streamlit)
            html.Div(id="admin-user-content"),
            # Store para manejar estados
            dcc.Store(
                id="admin-user-type-store", data="player"
            ),  # Se actualizará dinámicamente
        ]
    )


# Callback movido a callbacks/administration_callbacks.py


if __name__ == "__main__":
    # Para testing
    pass

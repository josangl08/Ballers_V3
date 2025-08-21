"""
Componentes de alertas y mensajes reutilizables.

Contiene funciones para crear alertas, mensajes de error, y notificaciones.
"""

import dash_bootstrap_components as dbc
from dash import html


def create_error_alert(message: str, title: str = "Error", dismissable: bool = True):
    """
    Crea una alerta de error estándar.

    Args:
        message: Mensaje de error
        title: Título del error
        dismissable: Si la alerta puede cerrarse

    Returns:
        dbc.Alert: Alerta de error
    """
    return dbc.Alert(
        [
            html.H6(
                [
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    title,
                ],
                className="mb-2",
            ),
            html.P(message, className="mb-0"),
        ],
        color="danger",
        dismissable=dismissable,
    )


def create_warning_alert(
    message: str, title: str = "Atención", dismissable: bool = True
):
    """
    Crea una alerta de advertencia estándar.

    Args:
        message: Mensaje de advertencia
        title: Título de la advertencia
        dismissable: Si la alerta puede cerrarse

    Returns:
        dbc.Alert: Alerta de advertencia
    """
    return dbc.Alert(
        [
            html.H6(
                [
                    html.I(className="bi bi-exclamation-circle me-2"),
                    title,
                ],
                className="mb-2",
            ),
            html.P(message, className="mb-0"),
        ],
        color="warning",
        dismissable=dismissable,
    )


def create_success_alert(message: str, title: str = "Éxito", dismissable: bool = True):
    """
    Crea una alerta de éxito estándar.

    Args:
        message: Mensaje de éxito
        title: Título del éxito
        dismissable: Si la alerta puede cerrarse

    Returns:
        dbc.Alert: Alerta de éxito
    """
    return dbc.Alert(
        [
            html.H6(
                [
                    html.I(className="bi bi-check-circle me-2"),
                    title,
                ],
                className="mb-2",
            ),
            html.P(message, className="mb-0"),
        ],
        color="success",
        dismissable=dismissable,
    )


def create_info_alert(
    message: str, title: str = "Información", dismissable: bool = True
):
    """
    Crea una alerta informativa estándar.

    Args:
        message: Mensaje informativo
        title: Título de la información
        dismissable: Si la alerta puede cerrarse

    Returns:
        dbc.Alert: Alerta informativa
    """
    return dbc.Alert(
        [
            html.H6(
                [
                    html.I(className="bi bi-info-circle me-2"),
                    title,
                ],
                className="mb-2",
            ),
            html.P(message, className="mb-0"),
        ],
        color="info",
        dismissable=dismissable,
    )


def create_no_data_alert(entity: str = "datos", suggestion: str = None):
    """
    Crea una alerta estándar para casos de "no hay datos".

    Args:
        entity: Entidad de la que no hay datos (ej: "estadísticas", "jugadores")
        suggestion: Sugerencia opcional para el usuario

    Returns:
        dbc.Alert: Alerta de no datos
    """
    message_parts = [f"No hay {entity} disponibles"]
    if suggestion:
        message_parts.append(f" {suggestion}")

    message = "".join(message_parts) + "."

    return dbc.Alert(
        [
            html.I(className="bi bi-database-x me-2"),
            message,
        ],
        color="warning",
    )


def create_loading_alert(message: str = "Cargando datos..."):
    """
    Crea una alerta de carga.

    Args:
        message: Mensaje de carga

    Returns:
        dbc.Alert: Alerta de carga
    """
    return dbc.Alert(
        [
            dbc.Spinner(size="sm", color="primary", spinnerClassName="me-2"),
            message,
        ],
        color="info",
    )


def create_feature_coming_soon_alert(feature_name: str = "Esta funcionalidad"):
    """
    Crea una alerta para funcionalidades que estarán disponibles próximamente.

    Args:
        feature_name: Nombre de la funcionalidad

    Returns:
        dbc.Alert: Alerta de "coming soon"
    """
    return dbc.Alert(
        [
            html.I(className="bi bi-clock me-2"),
            f"{feature_name} estará disponible próximamente.",
        ],
        color="secondary",
    )

"""
Componentes de cards reutilizables.

Contiene funciones para crear cards genéricas que pueden ser utilizadas
en cualquier parte de la aplicación.
"""

import dash_bootstrap_components as dbc
from dash import html


def create_metric_card(
    title: str, value, icon: str, color: str = "primary", subtitle: str = None
):
    """
    Crea una card genérica para mostrar métricas.

    Args:
        title: Título de la métrica
        value: Valor a mostrar (puede ser string, número, o componente HTML)
        icon: Clase del icono Bootstrap (ej: "bi bi-trophy")
        color: Color del tema (primary, success, warning, etc.)
        subtitle: Subtítulo opcional

    Returns:
        dbc.Card: Card con la métrica formateada
    """
    # Determinar colores según el tipo
    color_map = {
        "primary": "#24DE84",
        "success": "#28a745",
        "warning": "#FFA726",
        "danger": "#FF6B6B",
        "info": "#42A5F5",
        "secondary": "#6c757d",
    }

    main_color = color_map.get(color, color_map["primary"])

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.I(
                                className=f"{icon} me-2",
                                style={"color": main_color, "font-size": "1.5rem"},
                            ),
                            html.H6(
                                title,
                                className="mb-2",
                                style={"color": "#FFFFFF", "font-weight": "600"},
                            ),
                        ],
                        className="d-flex align-items-center mb-2",
                    ),
                    html.Div(
                        (
                            value
                            if isinstance(value, (list, html.Div, html.Span))
                            else str(value)
                        ),
                        style={
                            "color": "#FFFFFF",
                            "font-size": "1.8rem",
                            "font-weight": "bold",
                            "text-align": "center",
                        },
                    ),
                    (
                        html.P(
                            subtitle,
                            className="mb-0 mt-2",
                            style={
                                "color": "var(--color-white-faded)",
                                "font-size": "0.85rem",
                                "text-align": "center",
                            },
                        )
                        if subtitle
                        else None
                    ),
                ],
                className="text-center p-3",
            )
        ],
        style={
            "background-color": "#2B2B2B",
            "border": f"2px solid {main_color}80",  # 2px más visible, 80 = 50% opacity en hex
            "border-radius": "8px",
            "height": "100%",
        },
        className="h-100",
    )


def create_info_card(
    title: str, content, icon: str = "bi bi-info-circle", color: str = "primary"
):
    """
    Crea una card informativa genérica.

    Args:
        title: Título de la card
        content: Contenido de la card (puede ser string, lista, o componente HTML)
        icon: Icono para el header
        color: Color del tema

    Returns:
        dbc.Card: Card informativa
    """
    color_map = {
        "primary": "#24DE84",
        "success": "#28a745",
        "warning": "#FFA726",
        "danger": "#FF6B6B",
        "info": "#42A5F5",
    }

    main_color = color_map.get(color, color_map["primary"])

    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H6(
                        [
                            html.I(className=f"{icon} me-2"),
                            title,
                        ],
                        className="text-primary mb-0",
                        style={"color": main_color},
                    )
                ],
                style={
                    "background-color": "#2B2B2B",
                    "border-bottom": "1px solid rgba(255,255,255,0.2)",
                },
            ),
            dbc.CardBody(
                (
                    content
                    if isinstance(content, (list, html.Div, html.P))
                    else html.P(content)
                ),
                style={"color": "#FFFFFF"},
            ),
        ],
        style={
            "background-color": "#2B2B2B",
            "border": f"2px solid {main_color}80",
            "border-radius": "8px",
        },
    )


def create_stats_card(
    stats_dict: dict, title: str = "Statistics", icon: str = "bi bi-bar-chart"
):
    """
    Crea una card con múltiples estadísticas.

    Args:
        stats_dict: Diccionario con las estadísticas {label: value}
        title: Título de la card
        icon: Icono del header

    Returns:
        dbc.Card: Card con estadísticas
    """
    stats_items = []

    for label, value in stats_dict.items():
        stats_items.append(
            html.Div(
                [
                    html.Span(
                        label,
                        style={
                            "color": "var(--color-white-faded)",
                            "font-size": "0.9rem",
                        },
                    ),
                    html.Span(
                        str(value),
                        style={
                            "color": "#FFFFFF",
                            "font-weight": "bold",
                            "font-size": "1.1rem",
                            "float": "right",
                        },
                    ),
                ],
                className="d-flex justify-content-between mb-2",
                style={
                    "border-bottom": "1px solid rgba(255,255,255,0.1)",
                    "padding-bottom": "8px",
                },
            )
        )

    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H6(
                        [
                            html.I(className=f"{icon} me-2"),
                            title,
                        ],
                        className="text-primary mb-0",
                    )
                ]
            ),
            dbc.CardBody(stats_items),
        ],
        style={
            "background-color": "#2B2B2B",
            "border-color": "rgba(36, 222, 132, 0.3)",
        },
    )


def create_comparison_card(
    item1_label: str,
    item1_value,
    item2_label: str,
    item2_value,
    title: str = "Comparison",
    icon: str = "bi bi-arrow-left-right",
):
    """
    Crea una card para comparar dos valores.

    Args:
        item1_label: Etiqueta del primer item
        item1_value: Valor del primer item
        item2_label: Etiqueta del segundo item
        item2_value: Valor del segundo item
        title: Título de la card
        icon: Icono del header

    Returns:
        dbc.Card: Card comparativa
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H6(
                        [
                            html.I(className=f"{icon} me-2"),
                            title,
                        ],
                        className="text-primary mb-0",
                    )
                ]
            ),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H4(
                                        str(item1_value),
                                        className="text-center",
                                        style={
                                            "color": "#24DE84",
                                            "font-weight": "bold",
                                        },
                                    ),
                                    html.P(
                                        item1_label,
                                        className="text-center mb-0",
                                        style={
                                            "color": "var(--color-white-faded)",
                                            "font-size": "0.9rem",
                                        },
                                    ),
                                ],
                                width=5,
                            ),
                            dbc.Col(
                                [
                                    html.Div(
                                        "VS",
                                        className="text-center",
                                        style={
                                            "color": "#FFA726",
                                            "font-weight": "bold",
                                            "font-size": "1.2rem",
                                            "padding-top": "0.5rem",
                                        },
                                    )
                                ],
                                width=2,
                            ),
                            dbc.Col(
                                [
                                    html.H4(
                                        str(item2_value),
                                        className="text-center",
                                        style={
                                            "color": "#42A5F5",
                                            "font-weight": "bold",
                                        },
                                    ),
                                    html.P(
                                        item2_label,
                                        className="text-center mb-0",
                                        style={
                                            "color": "var(--color-white-faded)",
                                            "font-size": "0.9rem",
                                        },
                                    ),
                                ],
                                width=5,
                            ),
                        ]
                    )
                ]
            ),
        ],
        style={
            "background-color": "#2B2B2B",
            "border-color": "rgba(36, 222, 132, 0.3)",
        },
    )

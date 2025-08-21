"""
Componentes de tablas reutilizables.

Contiene funciones para crear tablas de estadísticas y otros componentes tabulares.
"""

import logging

import dash_bootstrap_components as dbc
from dash import html

logger = logging.getLogger(__name__)


def create_statistics_summary(player_stats):
    """
    Crea tabla resumida de estadísticas clave con comparación temporal.
    MOVIDO desde pages/ballers_dash.py

    Args:
        player_stats: Lista de diccionarios con estadísticas por temporada

    Returns:
        Componente dbc.Table con estadísticas resumidas
    """
    if not player_stats:
        return dbc.Alert("No statistical data available", color="warning")

    # Usar la temporada más reciente y anterior para comparación
    current_stats = player_stats[-1] if player_stats else {}
    previous_stats = player_stats[-2] if len(player_stats) > 1 else {}

    current_season = current_stats.get("season", "N/A")
    previous_season = previous_stats.get("season", "N/A") if previous_stats else None

    def get_trend_indicator(current_val, previous_val, metric_format="number"):
        """Genera indicador de tendencia visual con variación porcentual para no-porcentajes."""
        if not previous_val or previous_val == 0:
            return html.Span("—", style={"color": "var(--color-white-faded)"})

        # Calcular diferencia absoluta y porcentual
        diff_absolute = current_val - previous_val
        diff_percentage = ((current_val - previous_val) / previous_val) * 100

        # Para métricas que no son porcentajes, mostrar variación porcentual entre paréntesis
        if metric_format != "percentage":
            if current_val > previous_val:
                return html.Span(
                    [
                        html.I(className="bi bi-trend-up me-1"),
                        f"+{diff_absolute:.1f} ({diff_percentage:+.1f}%)",
                    ],
                    style={"color": "var(--color-primary)", "font-weight": "bold"},
                )
            elif current_val < previous_val:
                return html.Span(
                    [
                        html.I(className="bi bi-trend-down me-1"),
                        f"{diff_absolute:.1f} ({diff_percentage:.1f}%)",
                    ],
                    style={"color": "#FF6B6B", "font-weight": "bold"},
                )
            else:
                return html.Span(
                    [html.I(className="bi bi-dash me-1"), "0.0 (0.0%)"],
                    style={"color": "var(--color-white-faded)"},
                )
        else:
            # Para porcentajes, mantener el formato original (solo diferencia absoluta)
            if current_val > previous_val:
                return html.Span(
                    [html.I(className="bi bi-trend-up me-1"), f"+{diff_absolute:.1f}"],
                    style={"color": "var(--color-primary)", "font-weight": "bold"},
                )
            elif current_val < previous_val:
                return html.Span(
                    [html.I(className="bi bi-trend-down me-1"), f"{diff_absolute:.1f}"],
                    style={"color": "#FF6B6B", "font-weight": "bold"},
                )
            else:
                return html.Span(
                    [html.I(className="bi bi-dash me-1"), "0.0"],
                    style={"color": "var(--color-white-faded)"},
                )

    def format_percentage(value):
        """Formatea porcentajes con color según rango."""
        if not value:
            return html.Span("—", style={"color": "var(--color-white-faded)"})

        color = (
            "var(--color-primary)"
            if value >= 70
            else "#FFA726" if value >= 50 else "#FF6B6B"
        )
        return html.Span(f"{value:.1f}%", style={"color": color, "font-weight": "bold"})

    # Métricas clave optimizadas para primera impresión del jugador
    key_metrics = [
        # === RENDIMIENTO OFENSIVO ===
        {
            "icon": "bi bi-trophy",
            "metric": "Goals per 90",
            "current": current_stats.get("goals_per_90", 0.0) or 0.0,
            "previous": (
                previous_stats.get("goals_per_90", 0.0) or 0.0
                if previous_stats
                else 0.0
            ),
            "format": "decimal",
            "category": "offensive",
        },
        {
            "icon": "bi bi-hand-thumbs-up",
            "metric": "Assists per 90",
            "current": current_stats.get("assists_per_90", 0.0) or 0.0,
            "previous": (
                previous_stats.get("assists_per_90", 0.0) or 0.0
                if previous_stats
                else 0.0
            ),
            "format": "decimal",
            "category": "offensive",
        },
        {
            "icon": "bi bi-bullseye",
            "metric": "Shots on Target %",
            "current": current_stats.get("shots_on_target_pct", 0.0) or 0.0,
            "previous": (
                previous_stats.get("shots_on_target_pct", 0.0) or 0.0
                if previous_stats
                else 0.0
            ),
            "format": "percentage",
            "category": "offensive",
        },
        # === TÉCNICA Y DISTRIBUCIÓN ===
        {
            "icon": "bi bi-check-circle",
            "metric": "Pass Accuracy %",
            "current": current_stats.get("pass_accuracy_pct", 0.0) or 0.0,
            "previous": (
                previous_stats.get("pass_accuracy_pct", 0.0) or 0.0
                if previous_stats
                else 0.0
            ),
            "format": "percentage",
            "category": "technical",
        },
        {
            "icon": "bi bi-lightning",
            "metric": "xG + xA per 90",
            "current": (current_stats.get("xg_per_90", 0.0) or 0.0)
            + (current_stats.get("xa_per_90", 0.0) or 0.0),
            "previous": (
                (
                    (previous_stats.get("xg_per_90", 0.0) or 0.0)
                    + (previous_stats.get("xa_per_90", 0.0) or 0.0)
                )
                if previous_stats
                else 0.0
            ),
            "format": "decimal",
            "category": "technical",
        },
        # === RENDIMIENTO DEFENSIVO ===
        {
            "icon": "bi bi-shield",
            "metric": "Defensive Actions per 90",
            "current": current_stats.get("defensive_actions_per_90", 0.0) or 0.0,
            "previous": (
                previous_stats.get("defensive_actions_per_90", 0.0) or 0.0
                if previous_stats
                else 0.0
            ),
            "format": "decimal",
            "category": "defensive",
        },
        {
            "icon": "bi bi-arrow-up-circle",
            "metric": "Duels Won %",
            "current": current_stats.get("duels_won_pct", 0.0) or 0.0,
            "previous": (
                previous_stats.get("duels_won_pct", 0.0) or 0.0
                if previous_stats
                else 0.0
            ),
            "format": "percentage",
            "category": "defensive",
        },
        # === DISPONIBILIDAD Y EFICIENCIA ===
        {
            "icon": "bi bi-calendar-check",
            "metric": "Matches Played",
            "current": current_stats.get("matches_played", 0) or 0,
            "previous": (
                previous_stats.get("matches_played", 0) or 0 if previous_stats else 0
            ),
            "format": "number",
            "category": "availability",
        },
        {
            "icon": "bi bi-clock",
            "metric": "Minutes per Match",
            "current": (current_stats.get("minutes_played", 0) or 0)
            / max(1, current_stats.get("matches_played", 1) or 1),
            "previous": (
                (previous_stats.get("minutes_played", 0) or 0)
                / max(1, previous_stats.get("matches_played", 1) or 1)
                if previous_stats
                else 0
            ),
            "format": "decimal",
            "category": "availability",
        },
    ]

    # Crear filas de la tabla con agrupación por categorías
    table_rows = []
    current_category = None

    for metric in key_metrics:
        # Añadir separador de categoría si es necesario
        if metric["category"] != current_category:
            current_category = metric["category"]

            # Añadir header de categoría más visible
            category_names = {
                "offensive": "OFFENSIVE",
                "technical": "TECHNICAL",
                "defensive": "DEFENSIVE",
                "availability": "AVAILABILITY",
            }
            category_colors = {
                "offensive": "#FF6B6B",
                "technical": "#24DE84",
                "defensive": "#4DABF7",
                "availability": "#FFA726",
            }
            category_icons = {
                "offensive": "bi-crosshair",
                "technical": "bi-gear",
                "defensive": "bi-shield",
                "availability": "bi-calendar-week",
            }

            table_rows.append(
                html.Tr(
                    [
                        html.Td(
                            [
                                html.Div(
                                    [
                                        html.I(
                                            className=f"{category_icons.get(metric['category'], 'bi-circle')} me-2",
                                            style={
                                                "color": category_colors.get(
                                                    metric["category"],
                                                    "var(--color-white-faded)",
                                                )
                                            },
                                        ),
                                        html.Span(
                                            category_names.get(
                                                metric["category"],
                                                metric["category"].upper(),
                                            ),
                                            style={
                                                "color": category_colors.get(
                                                    metric["category"],
                                                    "var(--color-white-faded)",
                                                ),
                                                "font-weight": "700",
                                                "font-size": "0.75rem",
                                                "letter-spacing": "1px",
                                                "text-transform": "uppercase",
                                            },
                                        ),
                                    ],
                                    style={
                                        "padding": "4px 8px",
                                        "background-color": "rgba(255,255,255,0.05)",
                                        "border-radius": "4px",
                                        "border-left": f"3px solid {category_colors.get(metric['category'], '#FFFFFF')}",
                                        "display": "flex",
                                        "align-items": "center",
                                    },
                                )
                            ],
                            colSpan=3,
                            style={"padding": "0.5rem 1rem", "border": "none"},
                        )
                    ]
                )
            )

        # Formatear valor actual según tipo
        if metric["format"] == "percentage":
            current_display = format_percentage(metric["current"])
        elif metric["format"] == "decimal":
            current_display = html.Span(
                f"{metric['current']:.2f}",
                style={"color": "var(--color-white-faded)", "font-weight": "bold"},
            )
        else:  # number
            current_display = html.Span(
                str(int(metric["current"])),
                style={"color": "var(--color-white-faded)", "font-weight": "bold"},
            )

        # Generar indicador de tendencia
        trend = (
            get_trend_indicator(metric["current"], metric["previous"], metric["format"])
            if previous_stats
            else html.Span("—", style={"color": "var(--color-white-faded)"})
        )

        table_rows.append(
            html.Tr(
                [
                    html.Td(
                        [
                            html.I(
                                className=f"{metric['icon']} me-2",
                                style={"color": "var(--color-primary)"},
                            ),
                            metric["metric"],
                        ],
                        style={"color": "var(--color-white-faded)"},
                    ),
                    html.Td(current_display, className="text-center"),
                    html.Td(trend, className="text-center"),
                ]
            )
        )

    # Crear tabla con headers
    table_header = html.Thead(
        [
            html.Tr(
                [
                    html.Th(
                        "Metric",
                        style={
                            "color": "var(--color-primary)",
                            "border-bottom": "2px solid var(--color-primary)",
                        },
                    ),
                    html.Th(
                        current_season,
                        className="text-center",
                        style={
                            "color": "var(--color-primary)",
                            "border-bottom": "2px solid var(--color-primary)",
                        },
                    ),
                    html.Th(
                        (
                            f"vs {previous_season}"
                            if previous_season and previous_season != "N/A"
                            else "Trend"
                        ),
                        className="text-center",
                        style={
                            "color": "var(--color-primary)",
                            "border-bottom": "2px solid var(--color-primary)",
                        },
                    ),
                ]
            )
        ]
    )

    table = dbc.Table(
        [table_header, html.Tbody(table_rows)],
        bordered=False,
        hover=True,
        responsive=True,
        style={
            "background-color": "transparent",
            "color": "var(--color-white-faded)",
            "margin-bottom": "0",
        },
        className="stats-summary-table",
    )

    return html.Div([table])

#!/usr/bin/env python3
"""
ETL Tester Dashboard - Interfaz de testeo para ETL Coordinator CRISP-DM

Este dashboard permite probar y monitorear el ETL Coordinator implementado
en ml_system con metodología CRISP-DM completa.

Funcionalidades:
- Ejecutar pipeline ETL CRISP-DM completo
- Monitorear estado de procesamiento por temporada
- Limpiar y reprocesar temporadas
- Visualizar resultados y métricas
"""

import logging

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar app Dash
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css",
    ],
)

app.title = "ETL Coordinator Tester - CRISP-DM Pipeline"

# Estilos personalizados
CUSTOM_STYLE = {
    "backgroundColor": "#1A1A1A",
    "color": "#FFFFFF",
    "fontFamily": "Arial, sans-serif",
}

CARD_STYLE = {
    "background-color": "#2B2B2B",
    "border-color": "rgba(36, 222, 132, 0.3)",
    "color": "#FFFFFF",
}

PRIMARY_COLOR = "#24DE84"


def create_etl_dashboard_layout():
    """Crea el layout principal del dashboard ETL."""
    try:
        # Importar PlayerAnalyzer para obtener temporadas
        from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer

        player_analyzer = PlayerAnalyzer()
        available_seasons = player_analyzer.get_available_seasons_for_etl()

        # Crear opciones de dropdown
        season_options = [
            {"label": f"{season} - {desc}", "value": season}
            for season, desc in available_seasons.items()
        ]

        if not season_options:
            season_options = [{"label": "No seasons available", "value": ""}]

    except Exception as e:
        logger.error(f"Error loading seasons: {e}")
        season_options = [{"label": "Error loading seasons", "value": ""}]

    layout = dbc.Container(
        [
            # Header
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H1(
                                [
                                    html.I(
                                        className="bi bi-gear-fill me-3",
                                        style={"color": PRIMARY_COLOR},
                                    ),
                                    "ETL Coordinator Tester",
                                ],
                                className="text-center mb-1",
                                style={"color": PRIMARY_COLOR},
                            ),
                            html.P(
                                "CRISP-DM Pipeline Testing Interface",
                                className="text-center text-muted mb-4",
                            ),
                        ]
                    )
                ]
            ),
            # Control Panel
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H5(
                                                [
                                                    html.I(
                                                        className="bi bi-sliders me-2"
                                                    ),
                                                    "Pipeline Controls",
                                                ],
                                                className="mb-0",
                                                style={"color": PRIMARY_COLOR},
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            # Season Selection
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            html.Label(
                                                                "Season:",
                                                                className="form-label",
                                                                style={
                                                                    "color": PRIMARY_COLOR
                                                                },
                                                            ),
                                                            dcc.Dropdown(
                                                                id="season-dropdown",
                                                                options=season_options,
                                                                value=(
                                                                    season_options[0][
                                                                        "value"
                                                                    ]
                                                                    if season_options
                                                                    and season_options[
                                                                        0
                                                                    ]["value"]
                                                                    else None
                                                                ),
                                                                style={
                                                                    "color": "#000000"
                                                                },
                                                                placeholder="Select season to process",
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            html.Label(
                                                                "Matching Threshold:",
                                                                className="form-label",
                                                                style={
                                                                    "color": PRIMARY_COLOR
                                                                },
                                                            ),
                                                            dbc.Input(
                                                                id="threshold-input",
                                                                type="number",
                                                                value=85,
                                                                min=70,
                                                                max=100,
                                                                step=5,
                                                                style={
                                                                    "background-color": "#2B2B2B",
                                                                    "border-color": PRIMARY_COLOR,
                                                                    "color": "#FFFFFF",
                                                                },
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            # Options
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Checklist(
                                                                options=[
                                                                    {
                                                                        "label": " Calculate PDI Metrics",
                                                                        "value": "pdi",
                                                                    },
                                                                    {
                                                                        "label": " Force Reload Data",
                                                                        "value": "force",
                                                                    },
                                                                ],
                                                                value=["pdi"],
                                                                id="options-checklist",
                                                                inline=True,
                                                                style={
                                                                    "color": "#FFFFFF"
                                                                },
                                                            )
                                                        ],
                                                        width=12,
                                                    )
                                                ],
                                                className="mb-3",
                                            ),
                                            # Buttons
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Button(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-play-fill me-2"
                                                                    ),
                                                                    "Execute CRISP-DM Pipeline",
                                                                ],
                                                                id="execute-btn",
                                                                color="success",
                                                                size="lg",
                                                                className="me-2 mb-2",
                                                            ),
                                                            dbc.Button(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-arrow-clockwise me-2"
                                                                    ),
                                                                    "Check Status",
                                                                ],
                                                                id="status-btn",
                                                                color="info",
                                                                size="lg",
                                                                className="me-2 mb-2",
                                                            ),
                                                            dbc.Button(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-trash me-2"
                                                                    ),
                                                                    "Cleanup & Reprocess",
                                                                ],
                                                                id="cleanup-btn",
                                                                color="warning",
                                                                size="lg",
                                                                className="me-2 mb-2",
                                                            ),
                                                            dbc.Button(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-lightning-charge me-2"
                                                                    ),
                                                                    "Smart Weekly Update",
                                                                ],
                                                                id="smart-update-btn",
                                                                color="primary",
                                                                size="lg",
                                                                className="mb-2",
                                                            ),
                                                        ],
                                                        width=12,
                                                    )
                                                ]
                                            ),
                                        ]
                                    ),
                                ],
                                style=CARD_STYLE,
                            )
                        ],
                        width=12,
                    )
                ],
                className="mb-4",
            ),
            # Results Area
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div(
                                id="results-area",
                                children=[
                                    dbc.Alert(
                                        [
                                            html.I(className="bi bi-info-circle me-2"),
                                            "Welcome to ETL Coordinator Tester! Select a season and execute the CRISP-DM pipeline to begin.",
                                        ],
                                        color="info",
                                        className="mb-0",
                                    )
                                ],
                            )
                        ],
                        width=12,
                    )
                ],
                className="mb-4",
            ),
            # Status Monitoring
            dbc.Row(
                [dbc.Col([html.Div(id="status-monitoring")], width=12)],
                className="mb-4",
            ),
            # Footer
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Hr(),
                            html.P(
                                [
                                    "🚀 ETL Coordinator with CRISP-DM Methodology | ",
                                    "📊 Integrated with ml_system Architecture",
                                ],
                                className="text-center text-muted",
                            ),
                        ]
                    )
                ]
            ),
        ],
        fluid=True,
        style=CUSTOM_STYLE,
    )

    return layout


# Layout de la app
app.layout = create_etl_dashboard_layout()

# Callbacks para interactividad


@app.callback(
    Output("results-area", "children"),
    [Input("execute-btn", "n_clicks")],
    [
        State("season-dropdown", "value"),
        State("threshold-input", "value"),
        State("options-checklist", "value"),
    ],
)
def execute_etl_pipeline(n_clicks, season, threshold, options):
    """Ejecuta el pipeline ETL CRISP-DM."""
    if not n_clicks or not season:
        return dbc.Alert(
            [
                html.I(className="bi bi-info-circle me-2"),
                "Please select a season and click 'Execute CRISP-DM Pipeline'.",
            ],
            color="info",
        )

    try:
        # Importar PlayerAnalyzer
        from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer

        player_analyzer = PlayerAnalyzer()

        # Configurar opciones
        calculate_pdi = "pdi" in (options or [])
        force_reload = "force" in (options or [])
        threshold = threshold or 85

        # Ejecutar pipeline
        success, message, results = player_analyzer.execute_season_etl_pipeline(
            season=season, threshold=threshold, calculate_pdi=calculate_pdi
        )

        if success:
            # Mostrar resultados exitosos
            final_stats = results.get("final_stats", {})

            success_card = dbc.Card(
                [
                    dbc.CardHeader(
                        [
                            html.H6(
                                [
                                    html.I(
                                        className="bi bi-check-circle-fill me-2",
                                        style={"color": "#28A745"},
                                    ),
                                    "Pipeline Executed Successfully",
                                ],
                                className="mb-0",
                                style={"color": "#28A745"},
                            )
                        ]
                    ),
                    dbc.CardBody(
                        [
                            dbc.Alert(message, color="success", className="mb-3"),
                            # Estadísticas
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.H6(
                                                "Execution Statistics",
                                                className="text-primary mb-2",
                                            ),
                                            html.P(
                                                f"Season: {season}", className="mb-1"
                                            ),
                                            html.P(
                                                f"Total Extracted: {final_stats.get('total_extracted', 0)}",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"Total Loaded: {final_stats.get('total_loaded', 0)}",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"Exact Matches: {final_stats.get('exact_matches', 0)}",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"Quality Score: {final_stats.get('quality_score', 0)}%",
                                                className="mb-1",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            html.H6(
                                                "CRISP-DM Phases",
                                                className="text-primary mb-2",
                                            ),
                                            *[
                                                html.P(
                                                    [
                                                        html.I(
                                                            className="bi bi-check me-2",
                                                            style={"color": "#28A745"},
                                                        ),
                                                        phase_name.replace(
                                                            "_", " "
                                                        ).title(),
                                                    ],
                                                    className="mb-1",
                                                )
                                                for phase_name in results.get(
                                                    "pipeline_phases", {}
                                                ).keys()
                                            ],
                                        ],
                                        width=6,
                                    ),
                                ]
                            ),
                        ]
                    ),
                ],
                style=CARD_STYLE,
            )

            return success_card

        else:
            # Mostrar errores
            error_card = dbc.Card(
                [
                    dbc.CardHeader(
                        [
                            html.H6(
                                [
                                    html.I(
                                        className="bi bi-exclamation-triangle-fill me-2",
                                        style={"color": "#DC3545"},
                                    ),
                                    "Pipeline Failed",
                                ],
                                className="mb-0",
                                style={"color": "#DC3545"},
                            )
                        ]
                    ),
                    dbc.CardBody(
                        [
                            dbc.Alert(message, color="danger", className="mb-2"),
                            html.P(
                                "Check the logs for detailed error information.",
                                className="text-muted",
                            ),
                        ]
                    ),
                ],
                style=CARD_STYLE,
            )

            return error_card

    except Exception as e:
        logger.error(f"Error in ETL execution: {e}")
        return dbc.Alert(
            [
                html.I(className="bi bi-exclamation-triangle me-2"),
                f"Unexpected error: {str(e)}",
            ],
            color="danger",
        )


@app.callback(
    Output("status-monitoring", "children"),
    [Input("status-btn", "n_clicks")],
    [State("season-dropdown", "value")],
)
def check_etl_status(n_clicks, season):
    """Verifica el estado ETL de una temporada."""
    if not n_clicks or not season:
        return html.Div()

    try:
        from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer

        player_analyzer = PlayerAnalyzer()

        # Obtener estado ETL
        etl_status = player_analyzer.get_etl_processing_status(season)

        # Obtener resumen de análisis
        season_summary = player_analyzer.get_season_analysis_summary(season)

        status = etl_status.get("status", "unknown")

        # Color según estado
        status_colors = {
            "completed": "success",
            "processing": "info",
            "error": "danger",
            "not_processed": "secondary",
        }
        color = status_colors.get(status, "secondary")

        # Crear display de estado
        status_card = dbc.Card(
            [
                dbc.CardHeader(
                    [
                        html.H6(
                            [
                                html.I(className="bi bi-clipboard-data me-2"),
                                f"Status Report: {season}",
                            ],
                            className="mb-0",
                            style={"color": PRIMARY_COLOR},
                        )
                    ]
                ),
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Badge(
                                            status.replace("_", " ").title(),
                                            color=color,
                                            className="mb-2",
                                        ),
                                        html.P(
                                            etl_status.get("message", "No message"),
                                            className="mb-3",
                                        ),
                                        # Estadísticas detalladas
                                        html.H6(
                                            "Processing Statistics",
                                            className="text-primary mb-2",
                                        ),
                                        html.P(
                                            f"Total Records: {etl_status.get('total_records', 0)}",
                                            className="mb-1",
                                        ),
                                        html.P(
                                            f"Imported: {etl_status.get('imported_records', 0)}",
                                            className="mb-1",
                                        ),
                                        html.P(
                                            f"Matched Players: {etl_status.get('matched_players', 0)}",
                                            className="mb-1",
                                        ),
                                        html.P(
                                            f"Errors: {etl_status.get('errors_count', 0)}",
                                            className="mb-1",
                                        ),
                                    ],
                                    width=6,
                                ),
                                dbc.Col(
                                    [
                                        html.H6(
                                            "Analysis Summary",
                                            className="text-primary mb-2",
                                        ),
                                        html.P(
                                            f"Players Available: {season_summary.get('player_statistics', {}).get('total_players', 0)}",
                                            className="mb-1",
                                        ),
                                        html.P(
                                            f"With PDI: {season_summary.get('player_statistics', {}).get('players_with_pdi', 0)}",
                                            className="mb-1",
                                        ),
                                        html.P(
                                            f"Avg PDI: {season_summary.get('player_statistics', {}).get('avg_pdi_overall', 0):.2f}",
                                            className="mb-1",
                                        ),
                                        html.P(
                                            f"Analysis Ready: {'Yes' if season_summary.get('analysis_ready') else 'No'}",
                                            className="mb-1",
                                        ),
                                    ],
                                    width=6,
                                ),
                            ]
                        ),
                        html.Hr(),
                        html.Small(
                            [
                                f"Last Updated: {etl_status.get('last_updated', 'Never')} | ",
                                f"CRISP-DM Phase: {etl_status.get('crisp_dm_phase', 'Unknown')}",
                            ],
                            className="text-muted",
                        ),
                    ]
                ),
            ],
            style=CARD_STYLE,
        )

        return status_card

    except Exception as e:
        logger.error(f"Error checking status: {e}")
        return dbc.Alert(
            [
                html.I(className="bi bi-exclamation-triangle me-2"),
                f"Error checking status: {str(e)}",
            ],
            color="danger",
        )


@app.callback(
    Output("results-area", "children", allow_duplicate=True),
    [Input("smart-update-btn", "n_clicks")],
    prevent_initial_call=True,
)
def execute_smart_weekly_update(n_clicks):
    """Ejecuta Smart Weekly Update con lógica estacional."""
    if not n_clicks:
        return dbc.Alert("Click Smart Weekly Update button to execute.", color="info")

    try:
        from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer

        player_analyzer = PlayerAnalyzer()

        # Ejecutar Smart Weekly Update
        result = player_analyzer.execute_smart_weekly_update()

        if result.get("success", False):
            # Mostrar resultados exitosos con detalle CRISP-DM
            crisp_dm_phases = result.get("crisp_dm_phases", {})
            seasonal_insights = result.get("seasonal_insights", {})

            success_card = dbc.Card(
                [
                    dbc.CardHeader(
                        [
                            html.H6(
                                [
                                    html.I(
                                        className="bi bi-lightning-charge-fill me-2",
                                        style={"color": "#28A745"},
                                    ),
                                    "Smart Weekly Update Executed Successfully",
                                ],
                                className="mb-0",
                                style={"color": "#28A745"},
                            )
                        ]
                    ),
                    dbc.CardBody(
                        [
                            dbc.Alert(
                                result.get("message", "Update completed"),
                                color="success",
                                className="mb-3",
                            ),
                            # Información estacional
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.H6(
                                                "Seasonal Analysis",
                                                className="text-primary mb-2",
                                            ),
                                            html.P(
                                                f"Action: {result.get('action', 'unknown')}",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"Period: {seasonal_insights.get('current_period', 'unknown')}",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"Active Seasons: {len(seasonal_insights.get('active_seasons', []))}",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"Execution Time: {result.get('execution_time', 'N/A')}",
                                                className="mb-1",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            html.H6(
                                                "CRISP-DM Methodology",
                                                className="text-primary mb-2",
                                            ),
                                            *[
                                                html.P(
                                                    [
                                                        html.I(
                                                            className="bi bi-check me-2",
                                                            style={"color": "#28A745"},
                                                        ),
                                                        phase_name.replace(
                                                            "_", " "
                                                        ).title(),
                                                    ],
                                                    className="mb-1",
                                                )
                                                for phase_name in crisp_dm_phases.keys()
                                            ],
                                        ],
                                        width=6,
                                    ),
                                ]
                            ),
                            # Estadísticas
                            html.Hr(),
                            html.H6(
                                "Execution Statistics", className="text-primary mb-2"
                            ),
                            *[
                                html.P(f"{key}: {value}", className="mb-1")
                                for key, value in result.get("stats", {}).items()
                            ],
                        ]
                    ),
                ],
                style=CARD_STYLE,
            )

            return success_card

        else:
            # Mostrar errores
            error_card = dbc.Card(
                [
                    dbc.CardHeader(
                        [
                            html.H6(
                                [
                                    html.I(
                                        className="bi bi-exclamation-triangle-fill me-2",
                                        style={"color": "#DC3545"},
                                    ),
                                    "Smart Weekly Update Failed",
                                ],
                                className="mb-0",
                                style={"color": "#DC3545"},
                            )
                        ]
                    ),
                    dbc.CardBody(
                        [
                            dbc.Alert(
                                result.get("message", "Unknown error"),
                                color="danger",
                                className="mb-2",
                            ),
                            html.P(
                                f"Action attempted: {result.get('action', 'unknown')}",
                                className="text-muted mb-1",
                            ),
                            html.P(
                                "Check the logs for detailed error information.",
                                className="text-muted",
                            ),
                        ]
                    ),
                ],
                style=CARD_STYLE,
            )

            return error_card

    except Exception as e:
        logger.error(f"Error in Smart Weekly Update execution: {e}")
        return dbc.Alert(
            [
                html.I(className="bi bi-exclamation-triangle me-2"),
                f"Unexpected error in Smart Weekly Update: {str(e)}",
            ],
            color="danger",
        )


@app.callback(
    Output("results-area", "children", allow_duplicate=True),
    [Input("cleanup-btn", "n_clicks")],
    [State("season-dropdown", "value")],
    prevent_initial_call=True,
)
def cleanup_and_reprocess(n_clicks, season):
    """Limpia y reprocesa una temporada."""
    if not n_clicks or not season:
        return dbc.Alert("Please select a season first.", color="warning")

    try:
        from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer

        player_analyzer = PlayerAnalyzer()

        # Ejecutar limpieza y reprocesamiento
        success, message = player_analyzer.cleanup_and_reprocess_season(season)

        if success:
            return dbc.Alert(
                [
                    html.I(className="bi bi-check-circle me-2"),
                    f"Season {season} cleaned and reprocessed successfully: {message}",
                ],
                color="success",
            )
        else:
            return dbc.Alert(
                [
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    f"Error in cleanup/reprocess: {message}",
                ],
                color="danger",
            )

    except Exception as e:
        logger.error(f"Error in cleanup: {e}")
        return dbc.Alert(
            [
                html.I(className="bi bi-exclamation-triangle me-2"),
                f"Unexpected error: {str(e)}",
            ],
            color="danger",
        )


if __name__ == "__main__":
    print("🚀 Starting ETL Coordinator Tester Dashboard...")
    print("📊 Access at: http://localhost:8050")
    print("🎯 Features: CRISP-DM Pipeline, Status Monitoring, Season Management")

    app.run_server(debug=True, port=8050, host="0.0.0.0")

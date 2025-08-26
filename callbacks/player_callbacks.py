# callbacks/player_callbacks.py
"""
Callbacks relacionados con jugadores y perfiles.
"""
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, html, no_update


def register_player_callbacks(app):
    """Registra callbacks de jugadores en la aplicación Dash."""

    @app.callback(
        Output("selected-player-id", "data"),
        [Input("back-to-list-btn", "n_clicks")],
        [State("selected-player-id", "data")],
        prevent_initial_call=True,
    )
    def handle_back_to_list_callback(back_clicks, current_selection):
        """Callback para el botón de vuelta a la lista."""
        if back_clicks:
            print("DEBUG: Back to list clicked")
            return None
        return no_update

    @app.callback(
        Output("selected-player-id", "data", allow_duplicate=True),
        [Input({"type": "view-profile-button", "index": ALL}, "n_clicks")],
        [State("selected-player-id", "data")],
        prevent_initial_call=True,
    )
    def handle_view_profile_universal_callback(n_clicks_list, current_selection):
        """Callback universal para manejar todos los botones View Profile."""
        from dash import callback_context

        if not callback_context.triggered:
            return no_update

        if not any(n_clicks_list or []):
            return no_update

        trigger_id = callback_context.triggered[0]["prop_id"]
        print(f"DEBUG: Universal view profile trigger: {trigger_id}")

        try:
            if "view-profile-button" in trigger_id:
                import json

                trigger_data = json.loads(trigger_id.split(".")[0])
                player_id = trigger_data["index"]
                print(f"DEBUG: Navigating to player (complex): {player_id}")
                return player_id
            elif "view-profile-" in trigger_id:
                player_id = trigger_id.split("view-profile-")[1].split(".")[0]
                print(f"DEBUG: Navigating to player (simple): {player_id}")
                return player_id
        except Exception as e:
            print(f"DEBUG: Error parsing view profile trigger: {e}")

        return no_update

    @app.callback(
        Output("user-type-store", "data"),
        [Input("session-store", "data")],
        prevent_initial_call=False,
    )
    def get_user_type_callback(session_data):
        """Obtiene el tipo de usuario de la sesión."""
        try:
            if session_data and session_data.get("user_type"):
                return session_data.get("user_type", "player")
        except Exception as e:
            print(f"DEBUG: Error getting user type from session: {e}")

        # Fallback to admin for testing
        return "admin"

    @app.callback(
        [
            Output("ballers-user-content", "children"),
            Output("selected-player-id", "data", allow_duplicate=True),
        ],
        [
            Input("user-type-store", "data"),
            Input("selected-player-id", "data"),
            Input("session-store", "data"),
        ],
        prevent_initial_call="initial_duplicate",
    )
    def update_ballers_content_callback(user_type, selected_player_id, session_data):
        """Actualiza contenido de Ballers según tipo de usuario y selección."""
        from dash import no_update

        from pages.ballers_dash import (
            create_player_profile_dash,
            create_players_list_dash,
        )

        if user_type == "player":
            # Para players, obtener su player_id desde user_id y establecerlo en el store
            user_id = session_data.get("user_id") if session_data else None
            if user_id:
                from controllers.player_controller import PlayerController

                try:
                    with PlayerController() as controller:
                        player = controller.get_player_by_user_id(user_id)
                        if player:
                            player_id = player.player_id
                            print(
                                f"🎯 PLAYER MODE: user_id={user_id} -> player_id={player_id}"
                            )
                            return (
                                create_player_profile_dash(
                                    player_id=player_id, user_id=user_id
                                ),
                                player_id,
                            )
                        else:
                            print(f"❌ No player found for user_id={user_id}")
                except Exception as e:
                    print(f"❌ Error getting player_id for user_id={user_id}: {e}")

            # Fallback sin player_id
            return (
                create_player_profile_dash(player_id=None, user_id=user_id),
                no_update,
            )
        elif user_type in ["coach", "admin"]:
            if selected_player_id:
                return (
                    html.Div(
                        [
                            # Fila con botones de navegación y acción
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                [
                                                    html.I(
                                                        className="bi bi-arrow-left me-2"
                                                    ),
                                                    "Back to list",
                                                ],
                                                id="back-to-list-btn",
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
                                            )
                                        ],
                                        width="auto",
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                [
                                                    html.I(
                                                        className=(
                                                            "bi bi-file-earmark-pdf me-2"
                                                        )
                                                    ),
                                                    "Export Profile PDF",
                                                ],
                                                id="export-profile-btn",
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
                                            )
                                        ],
                                        width="auto",
                                        className="ms-auto",  # Empujar hacia la derecha
                                    ),
                                ],
                                className="mb-3 align-items-center",
                            ),
                            create_player_profile_dash(selected_player_id),
                        ]
                    ),
                    selected_player_id,  # Asegurar que el store se actualice para activar tabs profesionales
                )
            else:
                return create_players_list_dash(), no_update
        else:
            return (
                dbc.Alert(
                    "No tienes permisos para acceder a esta sección.", color="danger"
                ),
                no_update,
            )

    @app.callback(
        Output("profile-tab-content", "children"),
        [Input("profile-tabs", "active_tab")],
        prevent_initial_call=False,
    )
    def update_profile_tab_content(active_tab):
        """Actualiza contenido de las tabs del perfil - adaptado para Dash"""
        from pages.ballers_dash import (
            create_notes_content_dash,
            create_test_results_content_dash,
        )

        if active_tab == "test-results":
            return create_test_results_content_dash()
        elif active_tab == "notes":
            return create_notes_content_dash()
        else:
            return html.Div("Select a tab to view content")

    @app.callback(
        Output("calendar-display", "children"),
        [
            Input(
                {"type": "auto-hide-date", "index": "ballers-filter-from-date"}, "value"
            ),
            Input(
                {"type": "auto-hide-date", "index": "ballers-filter-to-date"}, "value"
            ),
            Input("status-filters", "data"),
            Input(
                "selected-player-id", "data"
            ),  # Mover de State a Input para manejar cambios
            Input("fallback-trigger", "data"),  # Fallback trigger para auto-refresh
        ],
        prevent_initial_call=False,  # Permitir inicialización
    )
    def update_sessions_calendar_content(
        from_date, to_date, status_filter, player_id, webhook_trigger
    ):
        """
        Actualiza el contenido del calendario de sesiones de forma reactiva.
        Se actualiza automáticamente cuando cambian los filtros.
        """
        from pages.ballers_dash import create_sessions_calendar_dash

        # Usar filtros del store, por defecto todos están activos
        if not status_filter:
            status_filter = ["scheduled", "completed", "canceled"]

        result = create_sessions_calendar_dash(
            from_date=from_date,
            to_date=to_date,
            status_filter=status_filter,
            player_id=player_id,
        )

        return result

    @app.callback(
        Output("performance-evolution-chart", "figure"),
        [Input("metrics-selector", "value")],
        [State("selected-player-id", "data")],
        prevent_initial_call=False,
    )
    def update_performance_chart(selected_metrics, player_id):
        """Actualiza el gráfico de evolución de rendimiento - adaptado para Dash"""
        import pandas as pd
        import plotly.express as px

        from controllers.player_controller import (
            PlayerController,
            get_player_profile_data,
        )

        print("🔍 PERFORMANCE CHART DEBUG:")
        print(f"  - player_id: {player_id}")
        print(f"  - selected_metrics: {selected_metrics}")

        # Si no hay player_id o métricas, mostrar gráfico vacío
        if not player_id or not selected_metrics:
            empty_fig = px.line()
            empty_fig.update_layout(
                plot_bgcolor="#333333",
                paper_bgcolor="#333333",
                font_color="#FFFFFF",
                annotations=[
                    dict(
                        text="Select metrics to display performance evolution",
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5,
                        xanchor="center",
                        yanchor="middle",
                        showarrow=False,
                        font=dict(size=16, color="#FFFFFF"),
                    )
                ],
            )
            return empty_fig

        try:
            # Obtener datos del perfil usando la misma lógica que en Streamlit
            profile_data = get_player_profile_data(player_id=player_id, user_id=None)

            if not profile_data:
                no_data_fig = px.line()
                no_data_fig.update_layout(
                    plot_bgcolor="#333333",
                    paper_bgcolor="#333333",
                    annotations=[
                        dict(
                            text="No data available",
                            xref="paper",
                            yref="paper",
                            x=0.5,
                            y=0.5,
                            xanchor="center",
                            yanchor="middle",
                            showarrow=False,
                            font=dict(size=16, color="#FFFFFF"),
                        )
                    ],
                )
                return no_data_fig

            test_results = profile_data.get("test_results", [])

            if not test_results:
                no_tests_fig = px.line()
                no_tests_fig.update_layout(
                    plot_bgcolor="#333333",
                    paper_bgcolor="#333333",
                    annotations=[
                        dict(
                            text="No test results available",
                            xref="paper",
                            yref="paper",
                            x=0.5,
                            y=0.5,
                            xanchor="center",
                            yanchor="middle",
                            showarrow=False,
                            font=dict(size=16, color="#FFFFFF"),
                        )
                    ],
                )
                return no_tests_fig

            # Usar PlayerController para formatear datos como Dash
            with PlayerController() as controller:
                test_data = controller.format_test_data_for_chart(test_results)

            df = pd.DataFrame(test_data)

            if df.empty:
                empty_df_fig = px.line()
                empty_df_fig.update_layout(
                    plot_bgcolor="#333333",
                    paper_bgcolor="#333333",
                    annotations=[
                        dict(
                            text="No data to display",
                            xref="paper",
                            yref="paper",
                            x=0.5,
                            y=0.5,
                            xanchor="center",
                            yanchor="middle",
                            showarrow=False,
                            font=dict(size=16, color="#FFFFFF"),
                        )
                    ],
                )
                return empty_df_fig

            # Crear gráfico con colores diferentes por métrica
            fig = px.line(
                df,
                x="Date",
                y=selected_metrics,
                markers=True,
                color_discrete_sequence=[
                    "#24DE84",  # Verde corporativo
                    "#FF4757",  # Rojo brillante
                    "#3742FA",  # Azul eléctrico
                    "#FF6348",  # Naranja
                    "#A4B0BE",  # Gris azulado
                    "#FFA502",  # Amarillo dorado
                    "#FF3838",  # Rojo intenso
                    "#1E90FF",  # Azul dodger
                    "#FF1493",  # Rosa intenso
                ],
            )

            # Aplicar estilo coherente con la aplicación desde el inicio
            fig.update_layout(
                plot_bgcolor="#333333",  # Fondo gris consistente
                paper_bgcolor="#333333",  # Fondo del papel gris
                font_color="#FFFFFF",
                xaxis=dict(gridcolor="#555", color="#FFFFFF"),
                yaxis=dict(gridcolor="#555", color="#FFFFFF"),
                legend=dict(
                    orientation="h",  # Leyenda horizontal
                    yanchor="top",
                    y=-0.2,  # Posicionar más abajo para evitar superposición
                    xanchor="center",
                    x=0.5,  # Centrar horizontalmente
                    bgcolor="rgba(51,51,51,0.9)",
                    bordercolor="#666",
                    borderwidth=1,
                    font_color="#FFFFFF",
                ),
                margin=dict(l=40, r=40, t=20, b=100),  # Aumentar margen inferior
            )

            return fig

        except Exception as e:
            error_fig = px.line()
            error_fig.update_layout(
                plot_bgcolor="#333333",
                paper_bgcolor="#333333",
                annotations=[
                    dict(
                        text=f"Error loading chart: {str(e)}",
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5,
                        xanchor="center",
                        yanchor="middle",
                        showarrow=False,
                        font=dict(size=16, color="#FF4757"),
                    )
                ],
            )
            return error_fig

    @app.callback(
        Output("test-history-content", "children"),
        [Input("profile-tabs", "active_tab")],
        [State("selected-player-id", "data")],
        prevent_initial_call=False,
    )
    def update_test_history(active_tab, player_id):
        """Actualiza el contenido del historial de tests usando accordions.

        adaptado para Dash.
        """
        print("🔍 TEST HISTORY DEBUG:")
        print(f"  - active_tab: {active_tab}")
        print(f"  - player_id: {player_id}")

        if active_tab != "test-results" or not player_id:
            print(
                f"  ❌ Returning empty div - tab: {active_tab}, player_id: {player_id}"
            )
            return html.Div()

        try:
            from controllers.player_controller import get_player_profile_data

            # Obtener datos usando la misma lógica que en Streamlit
            profile_data = get_player_profile_data(player_id=player_id, user_id=None)

            if not profile_data:
                return dbc.Alert("No player data available.", color="info")

            test_results = profile_data.get("test_results", [])

            if not test_results:
                return dbc.Alert(
                    "No test results available.",
                    color="info",
                    style={
                        "background-color": "#2A2A2A",
                        "border": "none",
                        "color": "#CCCCCC",
                    },
                )

            # Crear accordions como Dash
            accordion_items = []

            for i, test in enumerate(test_results):
                # Crear contenido del accordion usando la misma estructura
                # que en Streamlit
                accordion_content = dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.P(
                                    [html.Strong("Test Name: "), test.test_name],
                                    style={"color": "#FFFFFF", "margin-bottom": "8px"},
                                ),
                                html.P(
                                    [html.Strong("Weight: "), f"{test.weight} kg"],
                                    style={"color": "#FFFFFF", "margin-bottom": "8px"},
                                ),
                                html.P(
                                    [html.Strong("Height: "), f"{test.height} cm"],
                                    style={"color": "#FFFFFF", "margin-bottom": "8px"},
                                ),
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            [
                                html.P(
                                    [
                                        html.Strong("Ball Control: "),
                                        str(test.ball_control),
                                    ],
                                    style={"color": "#FFFFFF", "margin-bottom": "8px"},
                                ),
                                html.P(
                                    [
                                        html.Strong("Control & Passing: "),
                                        str(test.control_pass),
                                    ],
                                    style={"color": "#FFFFFF", "margin-bottom": "8px"},
                                ),
                                html.P(
                                    [
                                        html.Strong("Receiving & Passing/Scanning: "),
                                        str(test.receive_scan),
                                    ],
                                    style={"color": "#FFFFFF", "margin-bottom": "8px"},
                                ),
                                html.P(
                                    [
                                        html.Strong("Dribling & Ball Carriying: "),
                                        str(test.dribling_carriying),
                                    ],
                                    style={"color": "#FFFFFF", "margin-bottom": "8px"},
                                ),
                                html.P(
                                    [
                                        html.Strong("Shoot & Finishing: "),
                                        str(test.shooting),
                                    ],
                                    style={"color": "#FFFFFF", "margin-bottom": "8px"},
                                ),
                                html.P(
                                    [html.Strong("Crossbar: "), str(test.crossbar)],
                                    style={"color": "#FFFFFF", "margin-bottom": "8px"},
                                ),
                                html.P(
                                    [html.Strong("Sprint: "), str(test.sprint)],
                                    style={"color": "#FFFFFF", "margin-bottom": "8px"},
                                ),
                                html.P(
                                    [html.Strong("T-test: "), str(test.t_test)],
                                    style={"color": "#FFFFFF", "margin-bottom": "8px"},
                                ),
                                html.P(
                                    [html.Strong("Jumping: "), str(test.jumping)],
                                    style={"color": "#FFFFFF", "margin-bottom": "8px"},
                                ),
                            ],
                            width=6,
                        ),
                    ]
                )

                # Crear item del accordion con icono verde
                accordion_item = dbc.AccordionItem(
                    accordion_content,
                    title=html.Span(
                        [
                            html.I(
                                className="bi bi-clipboard-data me-2",
                                style={"color": "#24DE84"},
                            ),
                            f"Test of {test.date.strftime('%d/%m/%Y')}",
                        ]
                    ),
                    item_id=f"test-{i}",
                )

                accordion_items.append(accordion_item)

            # Crear accordion completo
            accordion = dbc.Accordion(
                accordion_items,
                start_collapsed=True,  # Todos cerrados inicialmente como los expanders
                style={"background-color": "#333333"},
            )

            return accordion

        except Exception as e:
            return dbc.Alert(
                f"Error loading test history: {str(e)}",
                color="danger",
                style={
                    "background-color": "#2A2A2A",
                    "border": "none",
                    "color": "#F44336",
                },
            )

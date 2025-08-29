# callbacks/professional_tabs_callbacks.py
"""
Callbacks para el sistema de tabs condicionales de jugadores profesionales.
"""

from dash import Input, Output, State, html

from controllers.db import get_db_session
from controllers.player_controller import get_player_profile_data
from models.professional_stats_model import ProfessionalStats
from models.user_model import UserType
from pages.ballers_dash import (
    create_development_roadmap_content,
    create_evolution_tab_content,
    create_performance_tab_content,
    create_position_tab_content,
    create_professional_info_content,
    create_professional_stats_content,
    create_professional_tabs,
)


def register_professional_tabs_callbacks(app):
    """Registra callbacks para tabs de jugadores profesionales."""

    @app.callback(
        [
            Output("professional-tabs-container", "children"),
            Output("amateur-content", "style"),
            Output("amateur-test-notes-tabs", "style"),
        ],
        [Input("selected-player-id", "data")],
        prevent_initial_call=False,
    )
    def update_professional_tabs_container(player_id):
        """
        Actualiza el contenedor de tabs profesionales según el jugador seleccionado.

        Args:
            player_id: ID del jugador seleccionado

        Returns:
            Tabs condicionales o div vacío
        """
        debug_msg = f"update_professional_tabs_container called with {player_id}"
        print(f"🔥 DEBUG: {debug_msg}")

        if not player_id:
            msg = "No player_id, returning empty div and showing amateur content"
            print(f"🔥 DEBUG: {msg}")
            return html.Div(), {"display": "block"}, {"display": "block"}

        try:
            # Obtener datos del jugador
            profile_data = get_player_profile_data(player_id=player_id)
            if not profile_data:
                print(f"🔥 DEBUG: No profile_data for player_id={player_id}")
                return html.Div(), {"display": "block"}, {"display": "block"}

            player = profile_data["player"]
            user = profile_data["user"]

            is_prof_attr = getattr(player, "is_professional", "ATTR_MISSING")
            print(f"🔥 DEBUG: Player={user.name}, is_professional={is_prof_attr}")

            # Verificar si es jugador profesional
            # (usuario player Y is_professional=True)
            is_user_player = user.user_type == UserType.player
            is_professional = getattr(player, "is_professional", False)
            is_professional_user = is_user_player and is_professional

            if is_professional_user:
                # Crear tabs profesionales y mantener todo el contenido amateur visible
                tabs = create_professional_tabs(player, user)
                print(f"🔥 DEBUG: Created professional tabs for {user.name}")
                return tabs, {"display": "block"}, {"display": "block"}
            else:
                # No crear tabs y mostrar contenido amateur
                print(f"🔥 DEBUG: Amateur player {user.name}, showing standard content")
                return html.Div(), {"display": "block"}, {"display": "block"}

        except Exception as e:
            print(f"🔥 ERROR: Error loading professional tabs: {str(e)}")
            import traceback

            traceback.print_exc()
            return html.Div(), {"display": "block"}, {"display": "block"}

    @app.callback(
        Output("professional-tab-content", "children"),
        [
            Input("selected-player-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def update_professional_tab_content(player_id):
        """
        Actualiza el contenido inicial de las tabs profesionales.
        Siempre muestra Info por defecto cuando se selecciona un jugador profesional.

        Args:
            player_id: ID del jugador

        Returns:
            Contenido inicial (tab Info)
        """
        if not player_id:
            return html.Div()

        try:
            # Obtener datos del jugador
            profile_data = get_player_profile_data(player_id=player_id)
            if not profile_data:
                return html.Div()

            player = profile_data["player"]
            user = profile_data["user"]

            # Verificar que es jugador profesional
            # (usuario player Y is_professional=True)
            is_user_player = user.user_type == UserType.player
            is_professional = getattr(player, "is_professional", False)
            if not (is_user_player and is_professional):
                return html.Div()

            # Siempre mostrar contenido de Info por defecto cuando se selecciona jugador
            return create_professional_info_content(player, user)

        except Exception as e:
            return html.Div(f"Error loading professional content: {str(e)}")

    @app.callback(
        Output("professional-tab-content", "children", allow_duplicate=True),
        [
            Input("professional-tabs", "active_tab"),
        ],
        [
            State("selected-player-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def switch_professional_tab_content(active_tab, player_id):
        """
        Maneja el switching entre tabs Info y Stats cuando el usuario hace click.
        Este callback solo se ejecuta cuando las tabs profesionales existen.

        Args:
            active_tab: Tab seleccionada (professional-info o professional-stats)
            player_id: ID del jugador seleccionado

        Returns:
            Contenido de la tab seleccionada
        """
        if not player_id or not active_tab:
            return html.Div()

        try:
            # Obtener datos del jugador
            profile_data = get_player_profile_data(player_id=player_id)
            if not profile_data:
                return html.Div()

            player = profile_data["player"]
            user = profile_data["user"]

            # Verificar que es jugador profesional
            # (usuario player Y is_professional=True)
            is_user_player = user.user_type == UserType.player
            is_professional = getattr(player, "is_professional", False)
            if not (is_user_player and is_professional):
                return html.Div()

            # Mostrar contenido según la tab activa
            if active_tab == "professional-stats":
                return create_professional_stats_content(player, user)
            else:  # professional-info o cualquier otro valor
                return create_professional_info_content(player, user)

        except Exception as e:
            return html.Div(f"Error switching professional tab: {str(e)}")

    @app.callback(
        [
            Output("amateur-content", "style", allow_duplicate=True),
            Output("amateur-test-notes-tabs", "style", allow_duplicate=True),
        ],
        [Input("professional-tabs", "active_tab")],
        [State("selected-player-id", "data")],
        prevent_initial_call=True,
    )
    def control_amateur_content_visibility(active_tab, player_id):
        """
        Controla la visibilidad del contenido amateur según la tab profesional activa.
        Info tab: muestra contenido amateur
        Stats tab: oculta contenido amateur
        """
        if not active_tab or not player_id:
            return {"display": "block"}, {"display": "block"}

        try:
            # Verificar que es jugador profesional
            profile_data = get_player_profile_data(player_id=player_id)
            if not profile_data:
                return {"display": "block"}, {"display": "block"}

            player = profile_data["player"]
            user = profile_data["user"]

            # Verificar que es jugador profesional
            # (usuario player Y is_professional=True)
            is_user_player = user.user_type == UserType.player
            is_professional = getattr(player, "is_professional", False)
            if not (is_user_player and is_professional):
                return {"display": "block"}, {"display": "block"}

            # Controlar visibilidad según tab activa
            if active_tab == "professional-stats":
                # Stats tab: ocultar contenido amateur
                return {"display": "none"}, {"display": "none"}
            else:
                # Info tab: mostrar contenido amateur
                return {"display": "block"}, {"display": "block"}

        except Exception as e:
            print(f"Error controlling amateur content visibility: {str(e)}")
            return {"display": "block"}, {"display": "block"}

    # ELIMINADO: Este callback ya no es necesario porque ahora reutilizamos
    # los elementos amateur originales (profile-tab-content, profile-tabs)
    # Los callbacks existentes en player_callbacks.py manejan automáticamente
    # las tabs Test Results y Notes para ambos tipos de jugadores

    # ELIMINADO: Los callbacks para calendario y tabla de sesiones ya no son necesarios
    # porque ahora reutilizamos los elementos amateur originales
    # (calendar-display, sessions-table)
    # Los callbacks existentes en ballers_callbacks.py manejan automáticamente
    # el calendario y tabla de sesiones para ambos tipos de jugadores

    # === CALLBACK PARA RADAR CHART DINAMICO ===
    # Solo actualiza el radar chart cuando cambian los filtros, no toda la interfaz

    @app.callback(
        Output("position-radar-chart", "children"),
        [
            Input("season-selectbox", "value"),
            Input("reference-selectbox", "value"),
        ],
        [
            State("stats-player-data", "data"),
        ],
        prevent_initial_call=False,
    )
    def update_position_radar_chart(season, references, player_data):
        """
        Actualiza sólo el radar chart cuando cambian los filtros.
        No recrea toda la interfaz, evitando duplicación.
        """
        if not player_data:
            return html.Div()

        # Valores por defecto
        season = season or "2024-25"
        references = references or ["league"]
        primary_reference = references[0] if references else "league"

        try:
            from common.components.charts.radar_charts import (
                create_position_radar_chart,
            )

            # Extraer player_id del estado (más robusto)
            player_id = None
            if "player_id" in player_data and isinstance(
                player_data["player_id"], (int, str)
            ):
                player_id = int(player_data["player_id"])
            elif "player" in player_data and isinstance(player_data["player"], dict):
                if "player_id" in player_data["player"]:
                    player_id = int(player_data["player"]["player_id"])
            elif "player_id" in player_data and isinstance(
                player_data["player_id"], dict
            ):
                nested_dict = player_data["player_id"]
                if "player_id" in nested_dict:
                    player_id = int(nested_dict["player_id"])

            if not player_id:
                return html.Div("Error: Could not extract player ID")

            # Asegurar que references es una lista
            if isinstance(references, str):
                references = [references]
            elif not isinstance(references, list):
                references = ["league"]

            print(
                f"⚙️ Updating radar chart: Player {player_id}, Season {season}, References {references}"
            )

            # Crear radar chart con múltiples referencias
            return create_position_radar_chart(player_id, season, references)

        except Exception as e:
            print(f"❌ Error updating radar chart: {e}")
            return html.Div(f"Error updating radar: {str(e)}")

    @app.callback(
        Output("main-tab-content", "children"),
        [Input("main-stats-tabs", "active_tab")],
        [State("stats-player-data", "data")],
        prevent_initial_call=False,
    )
    def update_main_tab_content(active_tab, player_data):
        """
        Callback principal para manejar el contenido de los tabs principales.
        Performance/Evolution/Position/AI Analytics.
        """
        if not active_tab or not player_data:
            return html.Div()

        try:
            from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer

            # Obtener datos del jugador desde el store
            player_id = player_data.get("player_id")
            season = player_data.get("season")
            user_id = player_data.get("user_id")
            player_stats_dict = player_data.get("player_stats", {})

            # Obtener objetos player y user desde la base de datos
            profile_data = get_player_profile_data(player_id=player_id)
            if not profile_data:
                return html.Div("Error: Player data not found")

            player = profile_data["player"]
            user = profile_data["user"]
            player_analyzer = PlayerAnalyzer()

            # Obtener player_stats usando PlayerAnalyzer (formato correcto: lista de diccionarios)
            all_stats = player_analyzer.get_player_stats(player_id)
            # Usar todas las temporadas disponibles para análisis temporal completo
            player_stats = all_stats if all_stats else []

            if active_tab == "performance-tab":
                return create_performance_tab_content(player_id, season, player_stats)
            elif active_tab == "evolution-tab":
                return create_evolution_tab_content(
                    player, player_stats, player_analyzer
                )
            elif active_tab == "position-tab":
                return create_position_tab_content(player, player_stats)
            else:
                return html.Div("Tab not implemented yet")

        except Exception as e:
            import traceback

            print(f"Error in update_main_tab_content: {e}")
            traceback.print_exc()
            return html.Div(f"Error loading tab content: {str(e)}")

    @app.callback(
        [
            Output("pdi-explanation-collapse", "is_open"),
            Output("pdi-explanation-toggle", "children"),
        ],
        [Input("pdi-explanation-toggle", "n_clicks")],
        [State("pdi-explanation-collapse", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_pdi_explanation(n_clicks, is_open):
        """
        Callback para toggle de la explicación del gráfico PDI.
        """
        if n_clicks:
            new_state = not is_open
            icon = (
                html.I(className="bi bi-chevron-up")
                if new_state
                else html.I(className="bi bi-chevron-down")
            )
            return new_state, icon
        return is_open, html.I(className="bi bi-chevron-down")

    @app.callback(
        [
            Output("iep-explanation-collapse", "is_open"),
            Output("iep-explanation-toggle", "children"),
        ],
        [Input("iep-explanation-toggle", "n_clicks")],
        [State("iep-explanation-collapse", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_iep_explanation(n_clicks, is_open):
        """
        Callback para toggle de la explicación del gráfico IEP Clustering.
        """
        if n_clicks:
            new_state = not is_open
            icon = (
                html.I(className="bi bi-chevron-up")
                if new_state
                else html.I(className="bi bi-chevron-down")
            )
            return new_state, icon
        return is_open, html.I(className="bi bi-chevron-down")

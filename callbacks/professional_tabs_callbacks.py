# callbacks/professional_tabs_callbacks.py
"""
Callbacks para el sistema de tabs condicionales de jugadores profesionales.
"""

from dash import Input, Output, State, html

from controllers.player_controller import get_player_profile_data
from controllers.db import get_db_session
from models.user_model import UserType
from models.professional_stats_model import ProfessionalStats
from pages.ballers_dash import (
    create_professional_info_content,
    create_professional_stats_content,
    create_professional_tabs,
    create_performance_tab_content,
    create_evolution_tab_content,
    create_position_tab_content,
    create_ai_analytics_content,
    create_pdi_development_content,
    create_iep_clustering_content,
    create_league_comparison_content,
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

    # === NUEVOS CALLBACKS PARA SISTEMA JERÁRQUICO DE TABS ===
    
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
                return create_performance_tab_content(player_stats)
            elif active_tab == "evolution-tab":
                return create_evolution_tab_content(player, player_stats, player_analyzer)
            elif active_tab == "position-tab":
                return create_position_tab_content(player_stats)
            elif active_tab == "ai-analytics-tab":
                return create_ai_analytics_content(player, player_stats)
            else:
                return html.Div("Tab not implemented yet")
                
        except Exception as e:
            import traceback
            print(f"Error in update_main_tab_content: {e}")
            traceback.print_exc()
            return html.Div(f"Error loading tab content: {str(e)}")
    
    @app.callback(
        Output("ai-sub-tab-content", "children"),
        [Input("ai-analytics-sub-tabs", "active_tab")],
        [State("stats-player-data", "data")],
        prevent_initial_call=False,
    )
    def update_ai_sub_tab_content(active_sub_tab, player_data):
        """
        Callback para manejar el contenido de los sub-tabs de AI Analytics.
        PDI Development/IEP Clustering/League Comparison.
        """
        if not active_sub_tab or not player_data:
            return html.Div()
            
        try:
            from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer
            
            # Obtener datos del jugador desde el store
            player_id = player_data.get("player_id")
            season = player_data.get("season")
            
            # Obtener objetos player desde la base de datos
            profile_data = get_player_profile_data(player_id=player_id)
            if not profile_data:
                return html.Div("Error: Player data not found")
                
            player = profile_data["player"]
            player_analyzer = PlayerAnalyzer()
            
            # Obtener player_stats usando PlayerAnalyzer (formato correcto: lista de diccionarios)
            all_stats = player_analyzer.get_player_stats(player_id)
            # Usar todas las temporadas disponibles para análisis temporal completo
            player_stats = all_stats if all_stats else []
            
            if active_sub_tab == "pdi-development-tab":
                return create_pdi_development_content(player)
            elif active_sub_tab == "iep-clustering-tab":
                return create_iep_clustering_content(player, player_stats)
            elif active_sub_tab == "league-comparison-tab":
                return create_league_comparison_content(player, player_stats)
            else:
                return html.Div("Sub-tab not implemented yet")
                
        except Exception as e:
            import traceback
            print(f"Error in update_ai_sub_tab_content: {e}")
            traceback.print_exc()
            return html.Div(f"Error loading sub-tab content: {str(e)}")

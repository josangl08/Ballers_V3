# callbacks/ballers_callbacks.py
"""
Callbacks específicos para la funcionalidad de Ballers.
"""

from dash import Input, Output, State


def register_ballers_callbacks(app):
    """Registra los callbacks específicos de la página Ballers."""

    # Callback para manejar el estado de filtros de status
    @app.callback(
        [
            Output("status-filters", "data"),
            Output("status-scheduled", "className"),
            Output("status-completed", "className"),
            Output("status-canceled", "className"),
        ],
        [
            Input("status-scheduled", "n_clicks"),
            Input("status-completed", "n_clicks"),
            Input("status-canceled", "n_clicks"),
        ],
        [State("status-filters", "data")],
        prevent_initial_call=False,
    )
    def toggle_status_filters(
        scheduled_clicks, completed_clicks, canceled_clicks, current_filters
    ):
        """Maneja el toggle de los filtros de estado"""
        from dash import callback_context

        # Verificar si es inicialización real (todos los clicks son None)
        all_clicks_none = all(
            click is None
            for click in [scheduled_clicks, completed_clicks, canceled_clicks]
        )

        if not callback_context.triggered or all_clicks_none:
            # Initial load - set all badges as active (custom CSS classes)
            filters = ["scheduled", "completed", "canceled"]  # Forzar estado inicial
            scheduled_class = "status-scheduled"
            completed_class = "status-completed"
            canceled_class = "status-canceled"
            return filters, scheduled_class, completed_class, canceled_class

        # Determinar qué badge se clickeó
        clicked_id = callback_context.triggered[0]["prop_id"].split(".")[0]
        status_map = {
            "status-scheduled": "scheduled",
            "status-completed": "completed",
            "status-canceled": "canceled",
        }

        clicked_status = status_map.get(clicked_id)
        if not clicked_status:
            # Return current state with proper classes
            filters = current_filters or ["scheduled", "completed", "canceled"]
            scheduled_class = (
                "status-scheduled" if "scheduled" in filters else "status-inactive"
            )
            completed_class = (
                "status-completed" if "completed" in filters else "status-inactive"
            )
            canceled_class = (
                "status-canceled" if "canceled" in filters else "status-inactive"
            )
            return filters, scheduled_class, completed_class, canceled_class

        # Inicializar filtros si está vacío
        filters = (
            current_filters.copy()
            if current_filters
            else ["scheduled", "completed", "canceled"]
        )

        # Toggle del filtro clickeado
        if clicked_status in filters:
            filters.remove(clicked_status)
        else:
            filters.append(clicked_status)

        # Si no hay filtros, mostrar todos
        if not filters:
            filters = ["scheduled", "completed", "canceled"]

        # Determinar clases CSS de badges
        scheduled_class = (
            "status-scheduled" if "scheduled" in filters else "status-inactive"
        )
        completed_class = (
            "status-completed" if "completed" in filters else "status-inactive"
        )
        canceled_class = (
            "status-canceled" if "canceled" in filters else "status-inactive"
        )

        return filters, scheduled_class, completed_class, canceled_class

    # Callback para actualizar tabla de sesiones según filtros
    @app.callback(
        Output("sessions-table", "children"),
        [
            Input(
                {"type": "auto-hide-date", "index": "ballers-filter-from-date"}, "value"
            ),
            Input(
                {"type": "auto-hide-date", "index": "ballers-filter-to-date"}, "value"
            ),
            Input("status-filters", "data"),
            Input("webhook-trigger", "data"),  # SSE trigger para auto-refresh
        ],
        [State("selected-player-id", "data")],
        prevent_initial_call=True,
    )
    def update_sessions_table(from_date, to_date, status_filters, webhook_trigger, selected_player_id):
        """Actualiza la tabla de sesiones según los filtros"""
        # Debug: logging callback execution
        import time
        current_time = int(time.time())
        print(f"🔍 DEBUG: update_sessions_table called at {current_time}")
        print(f"🔍 DEBUG: webhook_trigger = {webhook_trigger} (type: {type(webhook_trigger)})")
        print(f"🔍 DEBUG: from_date = {from_date}")
        print(f"🔍 DEBUG: to_date = {to_date}")
        print(f"🔍 DEBUG: status_filters = {status_filters}")
        print(f"🔍 DEBUG: selected_player_id = {selected_player_id}")
        
        # Verificar si este callback fue disparado por webhook
        if webhook_trigger and webhook_trigger > 0:
            time_diff = current_time - webhook_trigger
            print(f"🎯 WEBHOOK TRIGGERED CALLBACK: update_sessions_table")
            print(f"🎯 Time difference: {time_diff} seconds since webhook trigger")
        else:
            print(f"📋 FILTER TRIGGERED CALLBACK: update_sessions_table")
        
        try:
            # Convertir strings de fecha a objetos date si están disponibles
            from_date_obj = None
            to_date_obj = None

            if from_date:
                from datetime import datetime

                from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()

            if to_date:
                from datetime import datetime

                to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            # Usar los filtros del estado o todos por defecto
            status_filter = (
                status_filters
                if status_filters
                else ["scheduled", "completed", "canceled"]
            )

            from pages.ballers_dash import create_sessions_table_dash

            return create_sessions_table_dash(
                player_id=selected_player_id,
                from_date=from_date_obj,
                to_date=to_date_obj,
                status_filter=status_filter,
            )
        except Exception as e:
            import dash_bootstrap_components as dbc

            return dbc.Alert(
                f"Error updating sessions table: {str(e)}",
                color="danger",
                style={
                    "background-color": "#2A2A2A",
                    "border": "none",
                    "color": "#F44336",
                },
            )

    # Callback para filtrado de jugadores
    @app.callback(
        Output("players-cards-container", "children"),
        [Input("search-player-input", "value")],
        prevent_initial_call=True,
    )
    def filter_players_list(search_term):
        """Filtra la lista de jugadores según el término de búsqueda."""
        import dash_bootstrap_components as dbc

        from controllers.player_controller import get_players_for_list
        from pages.ballers_dash import create_player_card

        # Obtener datos con filtro (como en la función original)
        players_data = get_players_for_list(search_term=search_term)

        if not players_data:
            if search_term:
                return [
                    dbc.Col(
                        [
                            dbc.Alert(
                                f"No players found matching '{search_term}'.",
                                color="info",
                            )
                        ],
                        width=12,
                    )
                ]
            else:
                return [
                    dbc.Col(
                        [dbc.Alert("No registered players.", color="info")], width=12
                    )
                ]

        # Recrear tarjetas con datos filtrados usando la función reutilizable
        player_cards = []
        for i, player_data in enumerate(players_data):
            card = create_player_card(player_data)
            player_cards.append(dbc.Col([card], width=12, md=6, lg=4))

        return player_cards

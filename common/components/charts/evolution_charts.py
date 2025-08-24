"""
Componentes de gráficos de evolución temporal.

Contiene funciones para crear visualizaciones de evolución temporal de jugadores,
incluyendo PDI evolution y performance temporal.
"""

import base64
import logging

import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
from dash import dcc

logger = logging.getLogger(__name__)


def get_local_team_logo(team_name, team_logo_url):
    """
    Obtiene la ruta del logo local del equipo o lo descarga si no existe.
    IMPORTADA desde pages/ballers_dash.py

    Args:
        team_name: Nombre del equipo
        team_logo_url: URL del logo del equipo

    Returns:
        Ruta local del logo del equipo
    """
    import os
    import re

    import requests

    if not team_name or not team_logo_url:
        return "assets/team_logos/default_team.png"

    # Crear nombre de archivo seguro
    safe_name = re.sub(r"[^\w\s-]", "", team_name)
    safe_name = re.sub(r"[-\s]+", "_", safe_name)
    local_path = f"assets/team_logos/{safe_name}.png"

    # Si el archivo ya existe, devolverlo
    if os.path.exists(local_path):
        return local_path

    # Intentar descargar el logo
    try:
        response = requests.get(team_logo_url, timeout=10)
        response.raise_for_status()

        # Crear directorio si no existe
        os.makedirs("assets/team_logos", exist_ok=True)

        # Guardar imagen
        with open(local_path, "wb") as f:
            f.write(response.content)

        print(f"✅ Logo descargado para {team_name}: {local_path}")
        return local_path

    except Exception as e:
        print(f"❌ Error descargando logo para {team_name}: {e}")
        return "assets/team_logos/default_team.png"


def load_logo_as_base64(logo_path):
    """
    Convierte imagen local a base64 para mejor compatibilidad con Plotly.
    IMPORTADA desde pages/ballers_dash.py

    Args:
        logo_path: Ruta local del logo

    Returns:
        String base64 o None si hay error
    """
    try:
        with open(logo_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{encoded}"
    except Exception as e:
        print(f"❌ Error converting logo to base64: {e}")
        return None


def create_evolution_chart(player_stats):
    """
    Crea gráfico de evolución temporal avanzado con equipos integrados.
    MOVIDO desde pages/ballers_dash.py

    Args:
        player_stats: Lista de diccionarios con estadísticas por temporada

    Returns:
        Componente dcc.Graph con el gráfico de evolución con equipos
    """
    if not player_stats:
        return dbc.Alert("No statistical data available", color="warning")

    # Extraer datos para el gráfico
    seasons = [stat["season"] for stat in player_stats]
    goals = [stat["goals"] or 0 for stat in player_stats]
    assists = [stat["assists"] or 0 for stat in player_stats]
    matches = [stat["matches_played"] or 0 for stat in player_stats]

    # Nuevas estadísticas para el gráfico integral
    minutes = [stat.get("minutes_played") or 0 for stat in player_stats]
    duels_won_pct = [stat.get("duels_won_pct") or 0 for stat in player_stats]
    pass_accuracy_pct = [stat.get("pass_accuracy_pct") or 0 for stat in player_stats]

    # Normalizar minutes para escala 0-100 (dividir por 30 minutos típicos por partido)
    minutes_normalized = [min(100, (m / 30)) if m > 0 else 0 for m in minutes]
    # Escalar matches para mejor visualización en escala 0-100 (multiplicar por 2.5)
    matches_scaled = [min(100, m * 2.5) for m in matches]

    # Extraer datos de equipos para tooltips y logos
    teams = [stat.get("team", "Unknown Team") for stat in player_stats]
    team_logos = [stat.get("team_logo_url", "") for stat in player_stats]

    # Formatear temporadas para tooltips (20-21 formato)
    formatted_seasons = []
    for season in seasons:
        if season.startswith("20"):
            # Convertir "2020-21" a "20-21"
            formatted_seasons.append(season.replace("20", "", 1))
        else:
            formatted_seasons.append(season)

    # Crear posiciones numéricas para coordenadas X (solución al desplazamiento)
    x_positions = list(range(len(formatted_seasons)))

    # Crear cabeceras de tooltip con formato "20-21 - Equipo"
    tooltip_headers = [
        f"{season} - {team}" for season, team in zip(formatted_seasons, teams)
    ]

    # Calcular métricas normalizadas por 90 minutos
    goals_per_90 = [stat.get("goals_per_90") or 0 for stat in player_stats]
    assists_per_90 = [stat.get("assists_per_90") or 0 for stat in player_stats]

    # Calcular expected goals si está disponible
    expected_goals = [stat.get("expected_goals") or 0 for stat in player_stats]

    # Preparar customdata para tooltips enriquecidos
    tooltip_data = []
    for i, (season, team, goal, assist, match) in enumerate(
        zip(formatted_seasons, teams, goals, assists, matches)
    ):
        tooltip_data.append([season, team, goal, assist, match])

    customdata = np.array(tooltip_data)

    # Crear customdata específico para header del tooltip (temporada - equipo)
    header_customdata = [
        [season, team] for season, team in zip(formatted_seasons, teams)
    ]

    # Crear gráfico con múltiples líneas mejoradas
    fig = go.Figure()

    # Trace invisible para mostrar nombre del equipo (primera línea del tooltip)
    fig.add_trace(
        go.Scatter(
            x=x_positions,  # Usar posiciones numéricas
            y=[0] * len(formatted_seasons),  # En cero para ser invisible
            mode="markers",
            marker=dict(size=0, opacity=0, color="rgba(0,0,0,0)"),
            showlegend=False,
            name="",
            customdata=teams,  # Solo nombres de equipos
            hovertemplate="<b style='text-align:left'>%{customdata}</b><extra></extra>",
        )
    )

    # Línea de goles totales (original)
    fig.add_trace(
        go.Scatter(
            x=x_positions,  # Usar posiciones numéricas
            y=goals,
            mode="lines+markers",
            name="Goals (Total)",
            line=dict(color="#24DE84", width=3),
            marker=dict(size=8),
            customdata=customdata,
            hovertemplate="Goals (Total): %{y}<extra></extra>",
        )
    )

    # Línea de asistencias totales
    fig.add_trace(
        go.Scatter(
            x=x_positions,  # Usar posiciones numéricas
            y=assists,
            mode="lines+markers",
            name="Assists (Total)",
            line=dict(color="#FFA726", width=3),
            marker=dict(size=8),
            customdata=customdata,
            hovertemplate="Assists (Total): %{y}<extra></extra>",
        )
    )

    # Línea de expected goals si está disponible
    if any(xg > 0 for xg in expected_goals):
        fig.add_trace(
            go.Scatter(
                x=x_positions,  # Usar posiciones numéricas
                y=expected_goals,
                mode="lines+markers",
                name="Expected Goals (xG)",
                line=dict(color="#E57373", width=2, dash="dot"),
                marker=dict(size=6),
                customdata=customdata,
                hovertemplate="Expected Goals (xG): %{y:.2f}<extra></extra>",
            )
        )

    # Línea de partidos jugados (escalado x2.5 para rango 0-100)
    fig.add_trace(
        go.Scatter(
            x=x_positions,  # Usar posiciones numéricas
            y=matches_scaled,
            mode="lines+markers",
            name="Matches Played",
            line=dict(color="#42A5F5", width=2, dash="dash"),
            marker=dict(size=6),
            yaxis="y2",
            customdata=[
                [s, t, m, a, ma]
                for s, t, m, a, ma in zip(
                    formatted_seasons, teams, goals, assists, matches
                )
            ],
            hovertemplate="Matches Played: %{customdata[4]}<extra></extra>",  # Mostrar valor real
        )
    )

    # Línea de porcentaje de duelos ganados (escala secundaria)
    fig.add_trace(
        go.Scatter(
            x=x_positions,  # Usar posiciones numéricas
            y=duels_won_pct,
            mode="lines+markers",
            name="Duels Won %",
            line=dict(color="#AB47BC", width=2),
            marker=dict(size=6),
            yaxis="y2",
            customdata=customdata,
            hovertemplate="Duels Won: %{y:.1f}%<extra></extra>",
        )
    )

    # Línea de precisión de pases (escala secundaria)
    fig.add_trace(
        go.Scatter(
            x=x_positions,  # Usar posiciones numéricas
            y=pass_accuracy_pct,
            mode="lines+markers",
            name="Pass Accuracy %",
            line=dict(color="#EC407A", width=2),
            marker=dict(size=6),
            yaxis="y2",
            customdata=customdata,
            hovertemplate="Pass Accuracy: %{y:.1f}%<extra></extra>",
        )
    )

    # Línea de minutos jugados (normalizado /30 para rango 0-100)
    fig.add_trace(
        go.Scatter(
            x=x_positions,  # Usar posiciones numéricas
            y=minutes_normalized,
            mode="lines+markers",
            name="Minutes Played",
            line=dict(color="#26C6DA", width=2),
            marker=dict(size=6),
            yaxis="y2",  # Cambiado a yaxis2
            customdata=[
                [s, t, m, a, mi]
                for s, t, m, a, mi in zip(
                    formatted_seasons, teams, goals, assists, minutes
                )
            ],
            hovertemplate="Minutes Played: %{customdata[4]}<extra></extra>",  # Mostrar valor real
        )
    )

    # Añadir logos de equipos como imágenes de layout (si están disponibles)
    print(f"🔍 Processing {len(team_logos)} team logos for evolution chart")

    for i, (season, team, logo_url) in enumerate(
        zip(formatted_seasons, teams, team_logos)
    ):
        print(f"🏆 Season {season}: Team '{team}', Logo URL: '{logo_url}'")
        try:
            # Obtener logo local (descarga automáticamente si es necesario)
            local_logo_path = get_local_team_logo(team, logo_url)

            # Convertir a base64 para mejor compatibilidad
            base64_logo = load_logo_as_base64(local_logo_path)

            if base64_logo:
                print(f"🔄 Using base64 logo for {team}")
                # Posicionar logo cerca de líneas verticales de temporadas
                fig.add_layout_image(
                    source=base64_logo,
                    x=i,  # Usar índice numérico
                    y=0.95,  # Más cerca del área de plot
                    sizex=0.15,  # 15% del ancho (más grande y visible)
                    sizey=0.15,  # 15% de altura (más grande y visible)
                    sizing="contain",
                    layer="above",
                    xref="x",  # Coordenadas de datos X para alineación con temporadas
                    yref="paper",  # Coordenadas paper Y para posición fija
                    xanchor="center",
                    yanchor="middle",
                )
                print(f"✅ Base64 logo added for {team}")
            else:
                # Usar fallback icon cuando no hay logo disponible
                print(f"⚠️ No logo for {team}, using fallback icon")
                try:
                    # Bootstrap shield outline sin relleno
                    bootstrap_icon_svg = """
                    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="none" stroke="#24DE84" stroke-width="1.5" viewBox="0 0 16 16">
                        <path d="M8 0c-.69 0-1.843.265-2.928.56-1.11.3-2.229.655-2.887.87a1.54 1.54 0 0 0-1.044 1.262c-.596 4.477.787 7.795 2.465 9.99a11.777 11.777 0 0 0 2.517 2.453c.386.273.744.482 1.048.625.28.132.581.24.829.24s.548-.108.829-.24c.304-.143.662-.352 1.048-.625a11.777 11.777 0 0 0 2.517-2.453C13.22 10.343 14.603 7.025 14.007 2.548A1.54 1.54 0 0 0 12.963 1.286c-.658-.215-1.777-.57-2.887-.87C9.006.265 7.69 0 8 0z"/>
                    </svg>
                    """

                    fallback_base64 = f"data:image/svg+xml;base64,{base64.b64encode(bootstrap_icon_svg.encode()).decode()}"

                    fig.add_layout_image(
                        source=fallback_base64,
                        x=i,  # Usar índice numérico
                        y=0.95,  # Más cerca del área de plot
                        sizex=0.12,  # 12% del ancho (más visible)
                        sizey=0.12,  # 12% de altura (más visible)
                        sizing="contain",
                        layer="above",
                        xref="x",  # Coordenadas de datos X para alineación con temporadas
                        yref="paper",
                        xanchor="center",
                        yanchor="middle",
                    )
                    print(f"✅ Bootstrap fallback icon added for {team}")
                except Exception as fallback_error:
                    print(f"❌ Fallback icon failed for {team}: {fallback_error}")

        except Exception as e:
            print(f"❌ Error adding logo for {team}: {e}")
            # El fallback ya se maneja en el flujo principal (else del if base64_logo)

    # Layout mejorado con ejes múltiples
    fig.update_layout(
        yaxis=dict(
            title=dict(text="Goals/Assists/xG", font=dict(color="#FFFFFF", size=12)),
            tickfont=dict(color="#FFFFFF", size=10),
            gridcolor="rgba(255,255,255,0.1)",
            linecolor="rgba(255,255,255,0.2)",
            rangemode="tozero",  # Empezar desde 0
            range=[0, None],  # Base fija en 0, máximo auto
            domain=[0, 0.9],  # Reservar 10% del espacio para ejes derechos
        ),
        yaxis2=dict(
            title=dict(
                text="Normalized Metrics (0-100)", font=dict(color="#42A5F5", size=11)
            ),
            tickfont=dict(color="#42A5F5", size=9),
            overlaying="y",
            side="right",
            range=[0, 100],  # Rango 0-100 para todas las métricas normalizadas
            showgrid=False,  # Sin grid para evitar saturación
            anchor="x",  # Anclado al eje X, posición estándar derecha
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#FFFFFF"},
        legend=dict(
            orientation="h",  # Leyenda horizontal
            x=0.5,  # Centrado horizontalmente
            xanchor="center",  # Anclaje central
            y=1.08,  # Separado de los logos (logos en 0.95)
            yanchor="bottom",  # Anclaje inferior
            bgcolor="rgba(0,0,0,0.8)",
            bordercolor="rgba(36,222,132,0.3)",
            borderwidth=1,
            font=dict(color="white", size=10),
        ),
        height=450,
        autosize=True,  # Responsive width
        margin=dict(t=80, b=40, l=60, r=60),  # Márgenes equilibrados
        hovermode="x unified",  # Unified para mostrar todas las estadísticas juntas
        # Configurar cabecera unificada del tooltip
        xaxis=dict(
            title=dict(text="Season", font=dict(color="#FFFFFF")),
            tickfont=dict(color="#FFFFFF"),
            gridcolor="rgba(255,255,255,0.1)",
            linecolor="rgba(255,255,255,0.2)",
            # Configuración básica y funcional
            ticktext=formatted_seasons,  # Eje X muestra: "20-21", "21-22"
            tickvals=x_positions,  # Coordenadas numéricas: [0, 1, 2, ...]
            range=[
                -0.3,
                len(formatted_seasons) - 0.7,
            ],  # Padding para evitar cortes de elementos
            dtick=1,  # Ticks en posiciones enteras
            showticklabels=True,
            hoverformat="",  # Sin formato adicional
        ),
    )

    # Las etiquetas del eje X y tooltips ya están configurados en el layout principal

    return dcc.Graph(
        figure=fig, style={"height": "400px"}, config={"displayModeBar": False}
    )


def create_pdi_evolution_chart(player_id, seasons=None):
    """
    Crea gráfico de evolución PDI temporal.
    MOVIDO desde pages/ballers_dash.py

    Args:
        player_id: ID del jugador
        seasons: Temporadas a incluir (opcional)

    Returns:
        Componente dcc.Graph con evolución PDI
    """
    try:
        # Importar aquí para evitar dependencias circulares
        from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer

        logger.info(f"🎯 Creando PDI evolution chart para jugador {player_id}")

        # Inicializar analyzer
        player_analyzer = PlayerAnalyzer()

        # Obtener todas las temporadas disponibles para el jugador
        all_seasons_metrics = player_analyzer.get_all_seasons_pdi_metrics(player_id)

        if not all_seasons_metrics:
            return dbc.Alert(
                "No hay métricas PDI disponibles para mostrar evolución temporal",
                color="warning",
            )

        # Filtrar por temporadas específicas si se proporciona
        if seasons:
            all_seasons_metrics = [
                metric
                for metric in all_seasons_metrics
                if metric.get("season") in seasons
            ]

        if len(all_seasons_metrics) < 2:
            return dbc.Alert(
                "Se necesitan al menos 2 temporadas para mostrar evolución temporal",
                color="info",
            )

        # Ordenar por temporada
        all_seasons_metrics.sort(key=lambda x: x.get("season", ""))

        # Extraer datos para plotting
        seasons_list = [
            metric.get("season", "Unknown") for metric in all_seasons_metrics
        ]
        pdi_overall = [metric.get("pdi_overall", 0) for metric in all_seasons_metrics]
        pdi_universal = [
            metric.get("pdi_universal", 0) for metric in all_seasons_metrics
        ]
        pdi_zone = [metric.get("pdi_zone", 0) for metric in all_seasons_metrics]
        pdi_position = [
            metric.get("pdi_position_specific", 0) for metric in all_seasons_metrics
        ]

        # Formatear temporadas para mejor visualización
        formatted_seasons = []
        for season in seasons_list:
            if season.startswith("20"):
                formatted_seasons.append(
                    season.replace("20", "", 1)
                )  # "2020-21" → "20-21"
            else:
                formatted_seasons.append(season)

        # Crear posiciones numéricas para el eje X
        x_positions = list(range(len(formatted_seasons)))

        # Datos para tooltips enriquecidos
        pdi_data = []
        for i, season in enumerate(formatted_seasons):
            pdi_data.append(
                {
                    "season": season,
                    "pdi_overall": all_seasons_metrics[i].get("pdi_overall", 0),
                    "pdi_universal": all_seasons_metrics[i].get("pdi_universal", 0),
                    "pdi_zone": all_seasons_metrics[i].get("pdi_zone", 0),
                    "pdi_position_specific": all_seasons_metrics[i].get(
                        "pdi_position_specific", 0
                    ),
                    "team": all_seasons_metrics[i].get("team", "Unknown"),
                    "matches": all_seasons_metrics[i].get("matches_played", 0),
                    "position_analyzed": all_seasons_metrics[i].get(
                        "position_analyzed", "CF"
                    ),
                }
            )

        # Obtener información de posición del jugador (última temporada)
        latest_season_data = pdi_data[-1] if pdi_data else {}
        player_position = latest_season_data.get("position_analyzed", "CF")

        # Mapear posición a zona principal
        position_zone_mapping = {
            "GK": "Defensive",
            "CB": "Defensive",
            "LCB": "Defensive",
            "RCB": "Defensive",
            "FB": "Defensive",
            "LB": "Defensive",
            "RB": "Defensive",
            "LWB": "Defensive",
            "RWB": "Defensive",
            "DMF": "Midfield",
            "LDMF": "Midfield",
            "RDMF": "Midfield",
            "CMF": "Midfield",
            "LCMF": "Midfield",
            "RCMF": "Midfield",
            "AMF": "Midfield",
            "LAMF": "Midfield",
            "RAMF": "Midfield",
            "W": "Offensive",
            "LW": "Offensive",
            "RW": "Offensive",
            "LWF": "Offensive",
            "RWF": "Offensive",
            "CF": "Offensive",
        }
        player_zone = position_zone_mapping.get(player_position, "Midfield")

        # Crear gráfico
        fig = go.Figure()

        # Línea PDI Overall (principal) - Color destacado
        fig.add_trace(
            go.Scatter(
                x=x_positions,
                y=[d["pdi_overall"] for d in pdi_data],
                mode="lines+markers",
                name="PDI Overall",
                line=dict(color="#24DE84", width=4),  # Verde corporativo para destacar
                marker=dict(size=10, line=dict(width=2, color="#24DE84")),
                hovertemplate="<b>PDI Overall</b><br>%{y:.1f}<extra></extra>",
            )
        )

        # Línea Universal (40%) - Cyan distintivo
        fig.add_trace(
            go.Scatter(
                x=x_positions,
                y=[d["pdi_universal"] for d in pdi_data],
                mode="lines+markers",
                name="Universal (40%)",
                line=dict(color="#26C6DA", width=3),  # Cambiar a cyan
                marker=dict(size=8),
                hovertemplate="<b>Universal</b><br>%{y:.1f}<extra></extra>",
            )
        )

        # Línea Zone (35%) - Púrpura para contrastar
        fig.add_trace(
            go.Scatter(
                x=x_positions,
                y=[d["pdi_zone"] for d in pdi_data],
                mode="lines+markers",
                name="<span style='color:#24DE84'><i class='bi bi-bullseye'></i></span> Zone (35%)",
                line=dict(color="#AB47BC", width=3),  # Púrpura distintivo
                marker=dict(size=8),
                hovertemplate="<b>Zone Specific</b><br>%{y:.1f}<extra></extra>",
            )
        )

        # Línea Position (25%) - Naranja para contrastar
        fig.add_trace(
            go.Scatter(
                x=x_positions,
                y=[d["pdi_position_specific"] for d in pdi_data],
                mode="lines+markers",
                name="<span style='color:#24DE84'><i class='bi bi-person-fill'></i></span> Position (25%)",
                line=dict(color="#FF9800", width=3),  # Naranja distintivo
                marker=dict(size=8),
                hovertemplate="<b>Position Specific</b><br>%{y:.1f}<extra></extra>",
            )
        )

        # Añadir líneas de referencia
        fig.add_hline(
            y=75,
            line_dash="dash",
            line_color="rgba(36, 222, 132, 0.5)",
            annotation_text="Excellent (75+)",
            annotation_position="top right",
        )
        fig.add_hline(
            y=60,
            line_dash="dash",
            line_color="rgba(255, 167, 38, 0.5)",
            annotation_text="Good (60+)",
            annotation_position="top right",
        )
        fig.add_hline(
            y=45,
            line_dash="dash",
            line_color="rgba(229, 115, 115, 0.5)",
            annotation_text="Average (45+)",
            annotation_position="top right",
        )

        # Layout del gráfico
        fig.update_layout(
            title=dict(
                text="",  # Título vacío - se usa título externo en card header
                x=0.5,
                font=dict(color="#FFFFFF", size=16),
            ),
            xaxis=dict(
                title=dict(text="Season", font=dict(color="#FFFFFF")),
                ticktext=formatted_seasons,
                tickvals=x_positions,
                tickfont=dict(color="#FFFFFF"),
                gridcolor="rgba(255,255,255,0.1)",
                linecolor="rgba(255,255,255,0.2)",
                range=[-0.2, len(formatted_seasons) - 0.8],
            ),
            yaxis=dict(
                title=dict(text="PDI Score (0-100)", font=dict(color="#FFFFFF")),
                tickfont=dict(color="#FFFFFF"),
                gridcolor="rgba(255,255,255,0.1)",
                linecolor="rgba(255,255,255,0.2)",
                range=[0, 100],
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#FFFFFF"),
            legend=dict(
                orientation="h",  # Horizontal
                x=0.5,  # Centrado
                xanchor="center",  # Anclaje central
                y=1.15,  # Más alto para evitar overlap
                yanchor="bottom",  # Anclaje inferior
                bgcolor="rgba(0,0,0,0.8)",
                bordercolor="rgba(36,222,132,0.3)",
                borderwidth=1,
                font=dict(color="white", size=10),
            ),
            annotations=[
                # Información del jugador en la esquina superior derecha
                dict(
                    text=f"<i class='bi bi-geo-alt'></i> Position: {player_position}<br><i class='bi bi-diagram-3'></i> Zone: {player_zone}",
                    xref="paper",
                    yref="paper",
                    x=0.98,
                    y=0.98,
                    xanchor="right",
                    yanchor="top",
                    showarrow=False,
                    font=dict(size=10, color="#E0E0E0"),
                    bgcolor="rgba(0,0,0,0.8)",
                    bordercolor="rgba(66,165,245,0.3)",
                    borderwidth=1,
                    borderpad=5,
                )
            ],
            height=400,
            margin=dict(t=80, b=40, l=60, r=120),  # Más margen derecho para anotación
            hovermode="x unified",
        )

        return dcc.Graph(
            figure=fig, style={"height": "400px"}, config={"displayModeBar": False}
        )

    except Exception as e:
        logger.error(f"Error creando PDI evolution chart: {e}")
        return dbc.Alert(f"Error generando evolución PDI: {str(e)}", color="danger")

# common/format_utils.py
"""
Utilidades de formateo para elementos de UI.
Funciones reutilizables para formatear texto, nombres y elementos visuales.
"""
from dash import html


def format_name_with_del(name: str):
    """
    Formatea nombres con (DEL) en rojo.

    Args:
        name: Nombre que puede contener (DEL)

    Returns:
        Elemento HTML con el nombre formateado o string simple si no hay (DEL)
    """
    if not name or not isinstance(name, str):
        return name or ""

    if "(DEL)" in name:
        # Separar el nombre base del (DEL)
        parts = name.split(" (DEL)")
        base_name = parts[0]
        return html.Span(
            [
                base_name + " ",
                html.Span("(DEL)", style={"color": "red", "fontWeight": "bold"}),
            ]
        )
    return name


def format_session_title_with_del(coach_name: str, player_name: str):
    """
    Formatea un título de sesión con nombres que pueden contener (DEL).

    Args:
        coach_name: Nombre del coach (puede contener (DEL))
        player_name: Nombre del player (puede contener (DEL))

    Returns:
        Elemento HTML con el título formateado
    """
    coach_formatted = format_name_with_del(coach_name)
    player_formatted = format_name_with_del(player_name)

    # Si alguno es un componente HTML, retornar como componente complejo
    if isinstance(coach_formatted, html.Span) or isinstance(
        player_formatted, html.Span
    ):
        return html.Span([coach_formatted, " × ", player_formatted])

    # Si ambos son strings simples, retornar string simple
    return f"{coach_formatted} × {player_formatted}"

# common/upload_component.py
"""
Componente reutilizable para drag and drop de archivos con previsualización.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html


def create_upload_component(
    upload_id, preview_id=None, clear_btn_id=None, title="Profile Picture"
):
    """
    Crea un componente de upload con drag and drop y previsualización.

    Args:
        upload_id (str): ID del componente dcc.Upload
        preview_id (str): ID del div de previsualización (opcional)
        clear_btn_id (str): ID del botón de limpiar (opcional)
        title (str): Título del upload

    Returns:
        html.Div: Componente completo de upload
    """
    if preview_id is None:
        preview_id = f"{upload_id}-preview"
    if clear_btn_id is None:
        clear_btn_id = f"{upload_id}-clear-btn"

    return html.Div(
        [
            dcc.Upload(
                id=upload_id,
                children=html.Div(
                    [
                        html.I(
                            className="bi bi-cloud-upload me-2",
                            style={
                                "font-size": "1.5rem",
                                "color": "rgba(36, 222, 132, 1)",
                            },
                        ),
                        html.Div(
                            [
                                html.P(
                                    "Drag and Drop or Click to Select",
                                    style={
                                        "margin": "0",
                                        "font-weight": "500",
                                        "color": "#FFFFFF",
                                    },
                                ),
                                html.P(
                                    title,
                                    style={
                                        "margin": "0",
                                        "font-size": "0.8rem",
                                        "color": "#CCCCCC",
                                    },
                                ),
                            ]
                        ),
                    ],
                    style={
                        "display": "flex",
                        "align-items": "center",
                        "justify-content": "center",
                        "flex-direction": "row",
                        "text-align": "center",
                        "padding": "20px",
                        "border": "2px dashed rgba(36, 222, 132, 0.5)",
                        "border-radius": "10px",
                        "background-color": "transparent",
                        "cursor": "pointer",
                        "transition": "all 0.3s ease",
                    },
                ),
                style={"width": "100%"},
            ),
            # Preview area
            html.Div(
                id=preview_id,
                style={
                    "margin-top": "10px",
                    "text-align": "center",
                    "display": "none",
                },
            ),
        ]
    )


def create_upload_preview_callback_function(contents, filename, clear_btn_id=None):
    """
    Función helper para crear el contenido de previsualización.
    Debe ser usada dentro de un callback.

    Args:
        contents: Contenido del archivo (base64)
        filename: Nombre del archivo
        clear_btn_id: ID del botón de limpiar (opcional)

    Returns:
        tuple: (preview_content, preview_style)
    """
    if contents is None:
        return "", {"display": "none"}

    try:
        # Crear previsualización con botón de eliminar
        preview_content = [
            html.Div(
                [
                    html.P(
                        f"Selected: {filename}",
                        style={
                            "color": "rgba(36, 222, 132, 1)",
                            "font-weight": "500",
                            "margin-bottom": "10px",
                            "font-size": "0.9rem",
                            "display": "inline-block",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "align-items": "center",
                    "justify-content": "center",
                },
            ),
            html.Img(
                src=contents,
                style={
                    "max-width": "150px",
                    "max-height": "150px",
                    "border-radius": "10px",
                    "border": "2px solid rgba(36, 222, 132, 0.5)",
                    "object-fit": "cover",
                },
            ),
        ]

        # Agregar botón de eliminar si se proporciona el ID
        if clear_btn_id:
            preview_content[0]["children"].append(
                dbc.Button(
                    html.I(className="bi bi-x-circle"),
                    id=clear_btn_id,
                    size="sm",
                    color="link",
                    style={
                        "color": "#dc3545",
                        "margin-left": "10px",
                        "padding": "0",
                        "border": "none",
                        "background": "none",
                    },
                    title="Remove image",
                )
            )

        preview = html.Div(preview_content)
        return preview, {
            "margin-top": "10px",
            "text-align": "center",
            "display": "block",
        }

    except Exception as e:
        error_msg = html.P(
            f"Error loading image: {str(e)[:50]}...",
            style={"color": "#dc3545", "font-size": "0.8rem"},
        )
        return error_msg, {
            "margin-top": "10px",
            "text-align": "center",
            "display": "block",
        }

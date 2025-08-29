# common/datepicker_utils.py
"""
Utilidades comunes para manejo de datepickers en Dash.
Ahora integradas con dash-mantine-components para una UX mejorada.
Incluye callbacks clientside legacy (seguros) y fábricas de DatePicker Mantine.
"""

import dash_mantine_components as dmc
from dash import ALL, MATCH, Input, Output


def register_datepicker_callbacks(app):
    """
    Registra callbacks comunes para auto-cerrar datepickers.

    Args:
        app: Instancia de la aplicación Dash
    """

    # Callback clientside que se ejecuta cuando cambia cualquier input de fecha
    app.clientside_callback(
        """
        function(values) {
            // Esta función se ejecuta cuando cualquier input de fecha cambia
            console.log('[DatePicker Callback] Date input changed:', values);

            // Buscar todos los inputs de fecha y aplicar blur al que cambió
            setTimeout(function() {
                const dateInputs = document.querySelectorAll('input[type="date"]');
                dateInputs.forEach(function(input) {
                    // Si el input tiene foco y tiene valor, aplicar blur
                    if (document.activeElement === input && input.value) {
                        console.log(
                            '[DatePicker Callback] Applying blur to:',
                            input.id || input.className
                        );
                        input.blur();
                    }
                });
            }, 50);

            return window.dash_clientside.no_update;
        }
        """,
        Output("datepicker-dummy-output", "children", allow_duplicate=True),
        Input({"type": "date-input", "index": ALL}, "value"),
        prevent_initial_call=True,
    )

    # Callback usando pattern matching con output que también tenga MATCH
    app.clientside_callback(
        """
        function(value) {
            if (value) {
                console.log('[DatePicker Callback] Specific date changed:', value);

                // Aplicar blur al elemento activo si es un datepicker
                setTimeout(function() {
                    const activeElement = document.activeElement;
                    if (activeElement && activeElement.type === 'date' && 
                        activeElement.value) {
                        console.log('[DatePicker Callback] Blurring active datepicker');
                        activeElement.blur();
                    }
                }, 50);
            }

            return window.dash_clientside.no_update;
        }
        """,
        Output(
            {"type": "datepicker-output", "index": MATCH},
            "children",
            allow_duplicate=True,
        ),
        Input({"type": "auto-hide-date", "index": MATCH}, "value"),
        prevent_initial_call=True,
    )


def create_datepicker_dummy_divs():
    """
    Crea divs dummy necesarios para los callbacks de datepicker.
    Deben incluirse en el layout principal.

    Returns:
        Lista de componentes Dash para incluir en el layout
    """
    from dash import html

    return [
        html.Div(id="datepicker-dummy-output", style={"display": "none"}),
    ]


def _mantine_datepicker_styles():
    """Estilos nativos para Mantine DatePicker usando Styles API (DMC 1.2.0+)."""
    return {
        "input": {
            "backgroundColor": "#3b3b3a",
            "color": "#FFFFFF",
            "borderColor": "rgba(255,255,255,0.2)",
            "borderRadius": "10px",
            "fontSize": "0.9rem",
            "textAlign": "center",  # Centrar fecha DD/MM/YYYY
        },
        "dropdown": {
            "backgroundColor": "#333333",
            "color": "#FFFFFF",
            "border": "1px solid rgba(255,255,255,0.1)",
            "borderRadius": "10px",
            "boxShadow": "0 6px 12px rgba(36, 222, 132, 0.3)",
        },
        "calendarHeader": {
            "color": "#FFFFFF",
        },
        "calendarHeaderControl": {
            "color": "#24DE84",
            "borderColor": "transparent",
            "&:hover": {
                "backgroundColor": "rgba(36, 222, 132, 0.2)",
            },
        },
        "calendarHeaderLevel": {
            "color": "#FFFFFF",
            "&:hover": {
                "backgroundColor": "rgba(36, 222, 132, 0.15)",
            },
        },
        "weekday": {
            "color": "#BBBBBB",
            "fontSize": "0.8rem",
        },
        "day": {
            "color": "#FFFFFF",
            "borderRadius": "3px",
            "&:hover": {
                "backgroundColor": "rgba(36, 222, 132, 0.2)",
                "color": "#FFFFFF",
            },
            "&[data-selected]": {
                "backgroundColor": "#24DE84",
                "color": "#1D1B1A",
                "fontWeight": "600",
            },
            "&[data-weekend]": {
                "color": "rgba(36, 222, 132, 0.8)",
            },
            "&[data-today]": {
                "border": "2px solid #24DE84",
                "fontWeight": "600",
            },
        },
        "monthsListControl": {
            "color": "#FFFFFF",
            "&:hover": {
                "backgroundColor": "rgba(36, 222, 132, 0.2)",
            },
            "&[data-selected]": {
                "backgroundColor": "#24DE84",
                "color": "#1D1B1A",
            },
        },
        "yearsListControl": {
            "color": "#FFFFFF",
            "&:hover": {
                "backgroundColor": "rgba(36, 222, 132, 0.2)",
            },
            "&[data-selected]": {
                "backgroundColor": "#24DE84",
                "color": "#1D1B1A",
            },
        },
    }


def create_auto_hide_datepicker(
    input_id, value=None, min_date=None, max_date=None, placeholder="Select date"
):
    """
    Crea un DatePicker de Mantine con IDs compatibles con callbacks existentes.

    Args:
        input_id: índice para el pattern-matching ID
        value: valor inicial (YYYY-MM-DD)
        min_date, max_date: límites opcionales (YYYY-MM-DD)
        placeholder: texto del placeholder

    Returns:
        Lista [DatePicker, Div dummy] para compatibilidad con callbacks legacy
    """
    from dash import html

    component_id = {"type": "auto-hide-date", "index": input_id}
    output_id = {"type": "datepicker-output", "index": input_id}

    # Convertir fechas string a objetos date si es necesario
    from datetime import date, datetime

    parsed_value = None
    if value:
        if isinstance(value, str):
            try:
                parsed_value = datetime.fromisoformat(value).date()
            except ValueError:
                parsed_value = None
        elif isinstance(value, date):
            parsed_value = value

    parsed_min_date = None
    if min_date:
        if isinstance(min_date, str):
            try:
                parsed_min_date = datetime.fromisoformat(min_date).date()
            except ValueError:
                parsed_min_date = None
        elif isinstance(min_date, date):
            parsed_min_date = min_date

    parsed_max_date = None
    if max_date:
        if isinstance(max_date, str):
            try:
                parsed_max_date = datetime.fromisoformat(max_date).date()
            except ValueError:
                parsed_max_date = None
        elif isinstance(max_date, date):
            parsed_max_date = max_date

    dp = dmc.DatePickerInput(
        id=component_id,
        value=parsed_value,
        minDate=parsed_min_date,
        maxDate=parsed_max_date,
        placeholder=placeholder,
        valueFormat="DD/MM/YYYY",  # Formato español DD/MM/YYYY
        clearable=False,
        styles=_mantine_datepicker_styles(),
        style={"width": "100%"},
    )

    return [dp, html.Div(id=output_id, style={"display": "none"})]


def create_standard_datepicker(
    input_id, value=None, min_date=None, max_date=None, placeholder="Select date"
):
    """DatePickerInput de Mantine con ID genérico (para ALL pattern)."""
    component_id = {"type": "date-input", "index": input_id}

    # Convertir fechas string a objetos date si es necesario
    from datetime import date, datetime

    parsed_value = None
    if value:
        if isinstance(value, str):
            try:
                parsed_value = datetime.fromisoformat(value).date()
            except ValueError:
                parsed_value = None
        elif isinstance(value, date):
            parsed_value = value

    parsed_min_date = None
    if min_date:
        if isinstance(min_date, str):
            try:
                parsed_min_date = datetime.fromisoformat(min_date).date()
            except ValueError:
                parsed_min_date = None
        elif isinstance(min_date, date):
            parsed_min_date = min_date

    parsed_max_date = None
    if max_date:
        if isinstance(max_date, str):
            try:
                parsed_max_date = datetime.fromisoformat(max_date).date()
            except ValueError:
                parsed_max_date = None
        elif isinstance(max_date, date):
            parsed_max_date = max_date

    return dmc.DatePickerInput(
        id=component_id,
        value=parsed_value,
        minDate=parsed_min_date,
        maxDate=parsed_max_date,
        placeholder=placeholder,
        valueFormat="DD/MM/YYYY",  # Formato español DD/MM/YYYY
        clearable=False,
        styles=_mantine_datepicker_styles(),
        style={"width": "100%"},
    )

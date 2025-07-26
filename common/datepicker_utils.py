# common/datepicker_utils.py
"""
Utilidades comunes para manejo de datepickers en Dash.
Proporciona callbacks reutilizables para auto-cerrar datepickers.
"""

from dash import Input, Output, State, MATCH, ALL
import dash


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
                        console.log('[DatePicker Callback] Applying blur to:', input.id || input.className);
                        input.blur();
                    }
                });
            }, 50);
            
            return window.dash_clientside.no_update;
        }
        """,
        Output('datepicker-dummy-output', 'children', allow_duplicate=True),
        Input({'type': 'date-input', 'index': ALL}, 'value'),
        prevent_initial_call=True
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
                    if (activeElement && activeElement.type === 'date' && activeElement.value) {
                        console.log('[DatePicker Callback] Blurring active datepicker');
                        activeElement.blur();
                    }
                }, 50);
            }
            
            return window.dash_clientside.no_update;
        }
        """,
        Output({'type': 'datepicker-output', 'index': MATCH}, 'children', allow_duplicate=True),
        Input({'type': 'auto-hide-date', 'index': MATCH}, 'value'),
        prevent_initial_call=True
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
        html.Div(id='datepicker-dummy-output', style={'display': 'none'}),
    ]


def create_auto_hide_datepicker(input_id, **kwargs):
    """
    Crea un input de fecha con auto-hide automático.
    
    Args:
        input_id: ID único para el input
        **kwargs: Argumentos adicionales para dbc.Input
        
    Returns:
        Lista con componente dbc.Input y div de output para auto-hide
    """
    import dash_bootstrap_components as dbc
    from dash import html
    
    # Configurar el ID para pattern matching
    component_id = {'type': 'auto-hide-date', 'index': input_id}
    output_id = {'type': 'datepicker-output', 'index': input_id}
    
    # Configurar argumentos por defecto
    default_kwargs = {
        'type': 'date',
        'className': 'date-filter-input',
        'id': component_id
    }
    
    # Combinar con argumentos proporcionados
    default_kwargs.update(kwargs)
    
    return [
        dbc.Input(**default_kwargs),
        html.Div(id=output_id, style={'display': 'none'})
    ]


def create_standard_datepicker(input_id, **kwargs):
    """
    Crea un input de fecha estándar con auto-hide usando pattern matching genérico.
    
    Args:
        input_id: ID único para el input
        **kwargs: Argumentos adicionales para dbc.Input
        
    Returns:
        Componente dbc.Input configurado para auto-hide
    """
    import dash_bootstrap_components as dbc
    
    # Configurar el ID para pattern matching
    component_id = {'type': 'date-input', 'index': input_id}
    
    # Configurar argumentos por defecto
    default_kwargs = {
        'type': 'date',
        'className': 'date-filter-input',
        'id': component_id
    }
    
    # Combinar con argumentos proporcionados
    default_kwargs.update(kwargs)
    
    return dbc.Input(**default_kwargs)
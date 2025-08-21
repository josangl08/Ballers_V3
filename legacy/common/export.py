# common/export.py
"""
Utilidades compartidas para exportación e impresión.
Contiene funciones helper y CSS para optimizar impresión.
"""
from typing import Any, Dict, List

import streamlit as st
import streamlit.components.v1 as components


def create_export_buttons(
    on_export_pdf=None, on_print=None, key_prefix: str = "export"
) -> tuple:
    """
    Crea botones de exportar PDF e imprimir de forma minimalista.

    Args:
        on_export_pdf: Callback para exportar PDF
        on_print: Callback para imprimir
        key_prefix: Prefijo para las keys de los botones

    Returns:
        Tuple (export_clicked, print_clicked)
    """
    col1, col2 = st.columns([1, 1])

    with col1:
        export_clicked = st.button(
            "📄 Export",
            key=f"{key_prefix}_export",
            help="Export to PDF",
            use_container_width=False,
        )

    with col2:
        print_clicked = st.button(
            "🖨️ Print",
            key=f"{key_prefix}_print",
            help="Print current view",
            use_container_width=False,
        )

    # Ejecutar callbacks si están definidos
    if export_clicked and on_export_pdf:
        on_export_pdf()

    if print_clicked and on_print:
        on_print()

    return export_clicked, print_clicked


def trigger_browser_print():
    """
    Función de impresión simplificada que funciona para todas las secciones:
    - Perfiles de jugadores
    - Sesiones de administration (coach/admin)
    - Vista de financials
    """
    css_and_js = """
    <style id="ballers-print-styles">
    /* ESTILOS BASE PARA IMPRESIÓN */
    @media print {
        /* Reset completo para impresión */
        *, *::before, *::after {
            visibility: visible !important;
            color: black !important;
            background: white !important;
            box-shadow: none !important;
            text-shadow: none !important;
        }

        /* Layout principal */
        html, body {
            width: 100% !important;
            height: auto !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: visible !important;
            font-family: Arial, sans-serif !important;
            font-size: 12px !important;
            line-height: 1.4 !important;
        }

        /* Contenedor principal - ANCHO COMPLETO SIN SIDEBAR */
        .main, .block-container, [data-testid="stAppViewContainer"] {
            width: 100% !important;
            max-width: none !important;
            padding: 20px !important;
            margin: 0 !important;
            margin-left: 0 !important; /* Eliminar margen izquierdo del sidebar */
        }

        /* Forzar que el área principal ocupe todo el ancho */
        .stApp > div,
        [data-testid="stAppViewContainer"],
        .main .block-container {
            width: 100% !important;
            margin-left: 0 !important;
            padding-left: 20px !important;
        }

        /* OCULTAR SIDEBAR Y ELEMENTOS NO DESEADOS - AGRESIVO */
        section[data-testid="stSidebar"],
        [data-testid="stSidebar"],
        [data-testid="stSidebarNav"],
        [data-testid="collapsedControl"],
        [data-testid="stSidebarContent"],
        .stSidebar,
        .css-1d391kg, /* Sidebar container */
        .css-1lcbmhc, /* Sidebar wrapper */
        .css-1cypcdb, /* Sidebar variants */
        .css-17eq0hr, /* Sidebar variants */
        section[data-testid="stSidebar"] *,
        header[data-testid="stHeader"],
        .stButton, button,
        .stSelectbox, .stMultiSelect, .stDateInput, .stTextInput, .stNumberInput,
        .stTextArea, .stForm, .stCheckbox, .stRadio,
        [role="tablist"],
        .streamlit-expanderHeader,
        [data-testid="baseButton-minimal"],
        [data-testid="stExpanderToggleIcon"],
        .stTabs [data-baseweb="tab-list"],
        input, select, textarea {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* REGLAS ESPECÍFICAS PARA FORZAR OCULTACIÓN DEL SIDEBAR */
        html section[data-testid="stSidebar"],
        html [data-testid="stSidebar"],
        html .stSidebar,
        body section[data-testid="stSidebar"],
        body [data-testid="stSidebar"],
        body .stSidebar {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            min-width: 0 !important;
            max-width: 0 !important;
            opacity: 0 !important;
            position: absolute !important;
            left: -9999px !important;
        }

        /* TÍTULOS Y TEXTO */
        h1, h2, h3, h4, h5, h6 {
            color: #1E88E5 !important;
            page-break-after: avoid !important;
            margin: 15px 0 10px 0 !important;
        }

        h1 { font-size: 20px !important; }
        h2 { font-size: 18px !important; }
        h3 { font-size: 16px !important; }

        p, div, span {
            color: black !important;
            background: transparent !important;
        }

        /* MÉTRICAS - LAYOUT HORIZONTAL FORZADO */
        [data-testid="stMetric"], .metric {
            display: inline-block !important;
            width: auto !important;
            min-width: 100px !important;
            max-width: 150px !important;
            margin: 5px 10px !important;
            padding: 10px !important;
            border: 2px solid #1E88E5 !important;
            text-align: center !important;
            vertical-align: top !important;
            background: #f8f9fa !important;
        }

        [data-testid="stMetricLabel"] {
            font-size: 11px !important;
            color: #1E88E5 !important;
            font-weight: bold !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 18px !important;
            color: black !important;
            font-weight: bold !important;
        }

        /* Contenedor de métricas */
        [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-wrap: wrap !important;
            justify-content: center !important;
            gap: 10px !important;
            margin: 20px 0 !important;
        }

        /* TABLAS */
        table, .dataframe-table {
            width: 100% !important;
            border-collapse: collapse !important;
            margin: 15px 0 !important;
            font-size: 10px !important;
            page-break-inside: auto !important;
        }

        th, td {
            border: 1px solid black !important;
            padding: 4px 6px !important;
            text-align: left !important;
            background: white !important;
        }

        th {
            background: #1E88E5 !important;
            color: white !important;
            font-weight: bold !important;
        }

        tr:nth-child(even) td {
            background: #f9f9f9 !important;
        }

        /* DATAFRAMES DE STREAMLIT */
        .stDataFrame {
            width: 100% !important;
            overflow: visible !important;
        }

        .stDataFrame iframe {
            width: 100% !important;
            height: auto !important;
            min-height: 300px !important;
            border: 1px solid #ccc !important;
        }

        /* IMÁGENES Y FOTOS DE PERFIL */
        img {
            max-width: 150px !important;
            height: auto !important;
            page-break-inside: avoid !important;
        }

        /* CALENDARIOS */
        .js-plotly-plot, .stPlotlyChart, .plotly-graph-div {
            width: 100% !important;
            height: auto !important;
            min-height: 400px !important;
            border: 1px solid #ddd !important;
            page-break-inside: avoid !important;
        }

        /* LAYOUT DE COLUMNAS - ANCHO COMPLETO */
        [data-testid="stColumns"] {
            display: flex !important;
            gap: 15px !important;
            width: 100% !important;
        }

        [data-testid="stColumn"] {
            flex: 1 !important;
        }

        /* Asegurar que no hay restricciones de ancho del sidebar */
        .css-18e3th9, /* Main content area */
        .css-1d391kg, /* App container */
        .css-12oz5g7, /* Block container */
        div[data-testid="stMainBlockContainer"] {
            width: 100% !important;
            max-width: none !important;
            margin-left: 0 !important;
        }

        /* INFORMACIÓN DE PERFIL */
        .profile-section {
            display: flex !important;
            gap: 20px !important;
            align-items: flex-start !important;
            margin: 20px 0 !important;
            page-break-inside: avoid !important;
        }

        /* EXPANDERS - MOSTRAR CONTENIDO SIN BOTONES */
        .streamlit-expanderContent {
            display: block !important;
            border: 1px solid #ddd !important;
            padding: 10px !important;
            margin: 10px 0 !important;
        }

        /* FINANCIALS - GRÁFICOS */
        .stLineChart, .vega-embed {
            width: 100% !important;
            height: 300px !important;
            border: 1px solid #ddd !important;
            page-break-inside: avoid !important;
        }

        /* SALTOS DE PÁGINA */
        .page-break {
            page-break-before: always !important;
        }

        /* ENCABEZADO DE SECCIONES */
        .section-title {
            color: #1E88E5 !important;
            border-bottom: 2px solid #1E88E5 !important;
            padding-bottom: 5px !important;
            margin: 20px 0 15px 0 !important;
        }

        /* CORRECCIÓN PARA TABS - MOSTRAR TODO EL CONTENIDO */
        [data-testid="stTabs"] > div:last-child {
            display: block !important;
        }

        [data-testid="stTabContent"] {
            display: block !important;
        }

        /* OCULTAR ELEMENTOS ESPECÍFICOS DE NAVIGATION */
        .stTabs [role="tab"] {
            display: none !important;
        }
    }

    /* ESTILOS PARA VISTA PREVIA (no print) - FORZAR OCULTACIÓN */
    .print-preview-mode section[data-testid="stSidebar"],
    .print-preview-mode [data-testid="stSidebar"],
    .print-preview-mode .stSidebar {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
    }

    .print-preview-mode .main,
    .print-preview-mode .block-container,
    .print-preview-mode [data-testid="stAppViewContainer"] {
        width: 100% !important;
        max-width: none !important;
        margin-left: 0 !important;
        padding-left: 20px !important;
    }

    .print-preview-mode .stButton,
    .print-preview-mode button,
    .print-preview-mode .stSelectbox,
    .print-preview-mode input,
    .print-preview-mode select {
        display: none !important;
    }
    </style>

    <script>
    (function() {
        // Función que fuerza la ocultación del sidebar antes de imprimir
        setTimeout(function() {
            try {
                const parentDoc = window.parent.document;

                // 1. FORZAR OCULTACIÓN DEL SIDEBAR CON JAVASCRIPT
                const sidebarSelectors = [
                    'section[data-testid="stSidebar"]',
                    '[data-testid="stSidebar"]',
                    '[data-testid="stSidebarContent"]',
                    '[data-testid="collapsedControl"]',
                    '.stSidebar',
                    '.css-1d391kg',
                    '.css-1lcbmhc'
                ];

                sidebarSelectors.forEach(selector => {
                    const elements = parentDoc.querySelectorAll(selector);
                    elements.forEach(el => {
                        el.style.setProperty('display', 'none', 'important');
                        el.style.setProperty('visibility', 'hidden', 'important');
                        el.style.setProperty('width', '0', 'important');
                        el.style.setProperty('min-width', '0', 'important');
                        el.style.setProperty('position', 'absolute', 'important');
                        el.style.setProperty('left', '-9999px', 'important');
                    });
                });

                // 2. FORZAR EXPANSIÓN DEL CONTENIDO PRINCIPAL
                const mainSelectors = [
                    '.main',
                    '[data-testid="stAppViewContainer"]',
                    '.block-container',
                    'div[data-testid="stMainBlockContainer"]'
                ];

                mainSelectors.forEach(selector => {
                    const elements = parentDoc.querySelectorAll(selector);
                    elements.forEach(el => {
                        el.style.setProperty('width', '100%', 'important');
                        el.style.setProperty('max-width', 'none', 'important');
                        el.style.setProperty('margin-left', '0', 'important');
                        el.style.setProperty('padding-left', '20px', 'important');
                    });
                });

                // 3. APLICAR CLASE TEMPORAL PARA VISTA PREVIA
                const body = parentDoc.body;
                body.classList.add('print-preview-mode');

                // 4. ESPERAR UN MOMENTO Y LUEGO IMPRIMIR
                setTimeout(function() {
                    window.parent.print();
                }, 200);

                // 5. LIMPIAR DESPUÉS DE IMPRIMIR
                setTimeout(function() {
                    body.classList.remove('print-preview-mode');

                    // Restaurar sidebar (opcional)
                    sidebarSelectors.forEach(selector => {
                        const elements = parentDoc.querySelectorAll(selector);
                        elements.forEach(el => {
                            el.style.removeProperty('display');
                            el.style.removeProperty('visibility');
                            el.style.removeProperty('width');
                            el.style.removeProperty('min-width');
                            el.style.removeProperty('position');
                            el.style.removeProperty('left');
                        });
                    });
                }, 5000);

            } catch (error) {
                console.error('Error en impresión:', error);
                // Fallback: usar print nativo
                try {
                    window.parent.print();
                } catch (e) {
                    alert('Para imprimir, use Ctrl+P (Cmd+P en Mac) o el menú Archivo → Imprimir de su navegador.');
                }
            }
        }, 100);
    })();
    </script>
    """

    # Inyectar CSS y JavaScript
    components.html(css_and_js, height=0)


def format_session_status_for_export(status: str) -> str:
    """
    Formatea el estado de sesión para exportación.

    Args:
        status: Estado de la sesión

    Returns:
        Estado formateado
    """
    status_mapping = {
        "scheduled": "Scheduled",
        "completed": "Completed",
        "canceled": "Canceled",
    }
    return status_mapping.get(status, status.capitalize())


def prepare_sessions_data_for_export(sessions: List[Any]) -> List[Dict[str, str]]:
    """
    Prepara datos de sesiones para exportación.

    Args:
        sessions: Lista de objetos Session

    Returns:
        Lista de diccionarios con datos formateados
    """
    sessions_data = []

    for session in sessions:
        sessions_data.append(
            {
                "ID": str(session.id),
                "Coach": session.coach.user.name,
                "Player": session.player.user.name,
                "Date": session.start_time.strftime("%d/%m/%Y"),
                "Start Time": session.start_time.strftime("%H:%M"),
                "End Time": (
                    session.end_time.strftime("%H:%M")
                    if session.end_time
                    else "Not set"
                ),
                "Status": format_session_status_for_export(session.status.value),
                "Notes": session.notes or "",
            }
        )

    return sessions_data


def get_calendar_view_description(sessions: List[Any], start_date, end_date) -> str:
    """
    Genera descripción textual de la vista de calendario para reportes PDF.

    Args:
        sessions: Lista de sesiones
        start_date: Fecha inicio
        end_date: Fecha fin

    Returns:
        Descripción textual del calendario
    """
    date_range_days = (end_date - start_date).days + 1

    if date_range_days == 1:
        view_type = "Daily View"
    elif date_range_days <= 7:
        view_type = "Weekly View"
    elif date_range_days <= 31:
        view_type = "Monthly View"
    else:
        view_type = "Extended View"

    total_sessions = len(sessions)

    description = f"{view_type} ({start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')})\n"
    description += f"Total sessions in period: {total_sessions}"

    return description


def create_download_link(buffer, filename: str, link_text: str = "Download PDF"):
    """
    Crea un enlace de descarga para el PDF generado.

    Args:
        buffer: Buffer con el contenido del PDF
        filename: Nombre del archivo
        link_text: Texto del enlace
    """
    st.download_button(
        type="primary",
        label=link_text,
        data=buffer.getvalue(),
        file_name=filename,
        mime="application/pdf",
        key=f"download_{filename}",
    )


def show_export_success_message(filename: str):
    """
    Muestra mensaje de éxito tras generar PDF.

    Args:
        filename: Nombre del archivo generado
    """
    st.success(f"✅ PDF generated successfully: {filename}")


def show_export_error_message(error: str):
    """
    Muestra mensaje de error en exportación.

    Args:
        error: Mensaje de error
    """
    st.error(f"❌ Error generating PDF: {error}")


def validate_export_data(data_dict: Dict[str, Any]) -> tuple:
    """
    Valida que los datos necesarios estén disponibles para exportar.

    Args:
        data_dict: Diccionario con datos a validar

    Returns:
        Tuple (is_valid, error_message)
    """
    required_fields = ["start_date", "end_date"]

    for field in required_fields:
        if field not in data_dict or data_dict[field] is None:
            return False, f"Missing required field: {field}"

    # Validar que la fecha de fin no sea anterior a la de inicio
    if data_dict["end_date"] < data_dict["start_date"]:
        return False, "End date cannot be before start date"

    return True, ""


def get_user_context_for_export():
    """
    Obtiene contexto del usuario actual para personalizar exportes.

    Returns:
        Dict con información del usuario
    """
    return {
        "user_id": st.session_state.get("user_id"),
        "user_type": st.session_state.get("user_type", "player"),
        "user_name": st.session_state.get("name", "Unknown User"),
    }


def format_date_range_for_filename(start_date, end_date) -> str:
    """
    Formatea rango de fechas para nombres de archivo.

    Args:
        start_date: Fecha inicio
        end_date: Fecha fin

    Returns:
        String formateado para nombre de archivo
    """
    if start_date == end_date:
        return start_date.strftime("%Y%m%d")
    else:
        return f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"


def clean_filename(filename: str) -> str:
    """
    Limpia nombre de archivo removiendo caracteres especiales.

    Args:
        filename: Nombre original

    Returns:
        Nombre limpio para archivo
    """
    # Remover caracteres especiales y espacios
    clean_name = "".join(
        c for c in filename if c.isalnum() or c in (" ", "-", "_", ".")
    )
    # Reemplazar espacios múltiples con uno solo y luego con guión bajo
    clean_name = "_".join(clean_name.split())
    return clean_name


# Constantes para estilos de exportación
EXPORT_COLORS = {
    "primary": "#1E88E5",
    "secondary": "#0D47A1",
    "success": "#4CAF50",
    "warning": "#FF9800",
    "error": "#F44336",
    "info": "#00BCD4",
}

EXPORT_FONTS = {"title": 18, "subtitle": 14, "normal": 10, "small": 8}

# common/export.py
"""
Utilidades compartidas para exportación e impresión.
Contiene funciones helper y CSS para optimizar impresión.
"""
import streamlit as st
import streamlit.components.v1 as components
from typing import List, Dict, Any


def create_export_buttons(
    on_export_pdf=None, 
    on_print=None, 
    key_prefix: str = "export"
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
            use_container_width=False
        )
    
    with col2:
        print_clicked = st.button(
            "🖨️ Print", 
            key=f"{key_prefix}_print",
            help="Print current view",
            use_container_width=False
        )
    
    # Ejecutar callbacks si están definidos
    if export_clicked and on_export_pdf:
        on_export_pdf()
    
    if print_clicked and on_print:
        on_print()
    
    return export_clicked, print_clicked


def trigger_browser_print_alternative():
    """
    Método alternativo de impresión que crea una nueva ventana con el contenido.
    """
    st.markdown("""
    <div id="print-content" style="display: none;">
        <script>
        function printCurrentPage() {
            // Obtener todo el contenido de la página principal
            var mainContent = document.querySelector('.main .block-container');
            if (!mainContent) {
                alert('No se pudo encontrar el contenido para imprimir. Use Ctrl+P o Cmd+P para imprimir la página completa.');
                return;
            }
            
            // Crear una nueva ventana
            var printWindow = window.open('', '_blank', 'width=800,height=600');
            
            // Escribir contenido HTML básico
            printWindow.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Ballers App - Print</title>
                    <style>
                        body { 
                            font-family: Arial, sans-serif; 
                            margin: 20px; 
                            background: white; 
                            color: black; 
                        }
                        table { 
                            border-collapse: collapse; 
                            width: 100%; 
                            margin: 10px 0; 
                        }
                        th, td { 
                            border: 1px solid #000; 
                            padding: 8px; 
                            text-align: left; 
                        }
                        th { 
                            background-color: #f0f0f0; 
                            font-weight: bold; 
                        }
                        h1, h2, h3 { 
                            color: #1E88E5; 
                            margin: 20px 0 10px 0; 
                        }
                        img { 
                            max-width: 200px; 
                            height: auto; 
                        }
                        .metric { 
                            border: 1px solid #ccc; 
                            padding: 10px; 
                            margin: 5px; 
                            display: inline-block; 
                        }
                        button, input, select { 
                            display: none; 
                        }
                        @media print {
                            body { margin: 0; }
                        }
                    </style>
                </head>
                <body>
                    <h1>Ballers App Report</h1>
                    ${mainContent.innerHTML}
                </body>
                </html>
            `);
            
            printWindow.document.close();
            
            // Esperar a que se cargue y luego imprimir
            setTimeout(function() {
                printWindow.focus();
                printWindow.print();
                printWindow.close();
            }, 1000);
        }
        
        // Ejecutar la función
        printCurrentPage();
        </script>
    </div>
    """, unsafe_allow_html=True)


def trigger_browser_print():
    """
    Activa el diálogo de impresión del navegador con CSS optimizado.
    Enfoque simplificado que funciona mejor con Streamlit.
    """
    print_css_and_js = """
    <style>
    @media print {
        /* Forzar visibilidad de todo el contenido */
        * {
            visibility: visible !important;
            display: block !important;
            color: black !important;
            background: white !important;
        }
        
        /* Layout básico */
        html, body {
            width: 100% !important;
            height: auto !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: visible !important;
        }
        
        /* Ocultar elementos específicos que NO queremos */
        button,
        .stButton,
        .stButton > div,
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        header[data-testid="stHeader"],
        .stSelectbox,
        .stMultiSelect,
        .stDateInput,
        .stTextInput,
        .stNumberInput,
        .stTextArea,
        .stCheckbox,
        .stRadio,
        .stForm,
        .stTabs > div:first-child,
        .stExpander > div:first-child,
        [class*="stButton"],
        [class*="stSelectbox"],
        [class*="stForm"] {
            display: none !important;
            visibility: hidden !important;
        }
        
        /* Asegurar que el contenido principal se muestre */
        .main,
        .main *,
        .block-container,
        .block-container *,
        .stApp,
        .stApp * {
            display: block !important;
            visibility: visible !important;
            position: static !important;
        }
        
        /* Tablas */
        table,
        .stDataFrame,
        .stDataFrame table,
        .stDataFrame tbody,
        .stDataFrame tr,
        .stDataFrame td,
        .stDataFrame th {
            display: table !important;
            visibility: visible !important;
            border: 1px solid black !important;
            border-collapse: collapse !important;
        }
        
        /* Texto y títulos */
        h1, h2, h3, h4, h5, h6,
        p, div, span,
        .stMarkdown,
        .stMarkdown * {
            display: block !important;
            visibility: visible !important;
            color: black !important;
            background: transparent !important;
        }
        
        /* Métricas */
        .stMetric,
        .stMetric * {
            display: block !important;
            visibility: visible !important;
            border: 1px solid #ccc !important;
            padding: 10px !important;
            margin: 5px !important;
        }
        
        /* Imágenes */
        img {
            display: block !important;
            visibility: visible !important;
            max-width: 100% !important;
            height: auto !important;
        }
        
        /* Gráficos Plotly */
        .stPlotlyChart,
        .stPlotlyChart *,
        .plotly-graph-div,
        .plotly-graph-div * {
            display: block !important;
            visibility: visible !important;
        }
        
        /* Columnas */
        .stColumns,
        .stColumn {
            display: flex !important;
            visibility: visible !important;
        }
        
        .stColumn {
            flex: 1 !important;
        }
        
        /* Asegurar que no hay elementos float o absolute que causen problemas */
        * {
            position: static !important;
            float: none !important;
        }
        
        /* Padding del contenedor principal */
        .main .block-container {
            padding: 20px !important;
            max-width: 100% !important;
            width: 100% !important;
        }
    }
    </style>
    
    <script>
    function printPage() {
        // Esperar un poco más para que Streamlit termine de renderizar
        setTimeout(function() {
            try {
                window.print();
            } catch (e) {
                console.error('Print error:', e);
                alert('Error opening print dialog. Please use Ctrl+P or Cmd+P to print.');
            }
        }, 1000);
    }
    
    // Ejecutar cuando el DOM esté completamente cargado
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', printPage);
    } else {
        printPage();
    }
    </script>
    """
    
    # Inyectar CSS y JS
    components.html(print_css_and_js, height=0)


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
        "canceled": "Canceled"
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
        sessions_data.append({
            "ID": str(session.id),
            "Coach": session.coach.user.name,
            "Player": session.player.user.name,
            "Date": session.start_time.strftime("%d/%m/%Y"),
            "Start Time": session.start_time.strftime("%H:%M"),
            "End Time": session.end_time.strftime("%H:%M") if session.end_time else "Not set",
            "Status": format_session_status_for_export(session.status.value),
            "Notes": session.notes or ""
        })
    
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
        key=f"download_{filename}"
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
    required_fields = ['start_date', 'end_date']
    
    for field in required_fields:
        if field not in data_dict or data_dict[field] is None:
            return False, f"Missing required field: {field}"
    
    # Validar que la fecha de fin no sea anterior a la de inicio
    if data_dict['end_date'] < data_dict['start_date']:
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
        "user_name": st.session_state.get("name", "Unknown User")
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
        return start_date.strftime('%Y%m%d')
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
    clean_name = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))
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
    "info": "#00BCD4"
}

EXPORT_FONTS = {
    "title": 18,
    "subtitle": 14,
    "normal": 10,
    "small": 8
}
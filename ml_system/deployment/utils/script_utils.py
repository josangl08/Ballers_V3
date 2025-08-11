"""
Script Utilities - Utilidades compartidas para scripts de análisis
Consolida funciones comunes que se repetían en múltiples scripts de análisis ML.
"""

import logging
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional


def print_header(title: str, char: str = "=", width: int = 80) -> None:
    """
    Imprime header académico formateado para scripts de análisis.

    Args:
        title: Título a mostrar
        char: Carácter para el borde (default: "=")
        width: Ancho total del header (default: 80)
    """
    print("\n" + char * width)
    print(f"{title:^{width}}")
    print(char * width)


def setup_analysis_logging(
    script_name: str, log_dir: str = "outputs/logs"
) -> logging.Logger:
    """
    Configura logging estándar para scripts de análisis.

    Args:
        script_name: Nombre del script (sin extensión)
        log_dir: Directorio donde guardar logs (default: "outputs/logs")

    Returns:
        Logger configurado para el script
    """
    from pathlib import Path

    # Crear directorio de logs si no existe
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Configurar logging con timestamp
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = log_path / f"{script_name}_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )

    logger = logging.getLogger(__name__)

    # Suprimir warnings para output más limpio
    warnings.filterwarnings("ignore")

    logger.info(f"🚀 Iniciando {script_name}")
    logger.info(f"📁 Log guardado en: {log_file}")

    return logger


def save_analysis_report(
    content: str, report_name: str, report_dir: str = "outputs/reports"
) -> str:
    """
    Guarda reporte de análisis en ubicación estándar.

    Args:
        content: Contenido del reporte
        report_name: Nombre base del reporte
        report_dir: Directorio donde guardar (default: "outputs/reports")

    Returns:
        Ruta del archivo guardado
    """
    from pathlib import Path

    # Crear directorio si no existe
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)

    # Crear nombre con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_path / f"{report_name}_{timestamp}.txt"

    # Guardar reporte
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(content)

    return str(report_file)


def create_progress_tracker(
    total_steps: int, description: str = "Procesando"
) -> callable:
    """
    Crea función de tracking de progreso para scripts largos.

    Args:
        total_steps: Número total de pasos
        description: Descripción del proceso

    Returns:
        Función para actualizar progreso
    """
    current_step = 0

    def update_progress(step_description: str = ""):
        nonlocal current_step
        current_step += 1

        progress_pct = (current_step / total_steps) * 100
        progress_bar = "█" * int(progress_pct // 5) + "░" * (
            20 - int(progress_pct // 5)
        )

        print(
            f"\r{description}: [{progress_bar}] {progress_pct:.1f}% - {step_description}",
            end="",
            flush=True,
        )

        if current_step == total_steps:
            print()  # Nueva línea al final

    return update_progress


def format_execution_time(
    start_time: datetime, end_time: Optional[datetime] = None
) -> str:
    """
    Formatea tiempo de ejecución de manera legible.

    Args:
        start_time: Tiempo de inicio
        end_time: Tiempo de fin (default: ahora)

    Returns:
        String con tiempo formateado
    """
    if end_time is None:
        end_time = datetime.now()

    duration = end_time - start_time

    hours, remainder = divmod(duration.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    elif minutes > 0:
        return f"{int(minutes)}m {int(seconds)}s"
    else:
        return f"{seconds:.1f}s"


def validate_data_requirements(
    df, required_columns: List[str], min_records: int = 100
) -> Dict[str, Any]:
    """
    Valida que los datos cumplan requisitos mínimos para análisis.

    Args:
        df: DataFrame a validar
        required_columns: Columnas que deben estar presentes
        min_records: Mínimo número de registros requerido

    Returns:
        Dict con resultado de validación
    """
    validation = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "stats": {
            "total_records": len(df),
            "total_columns": len(df.columns),
            "missing_columns": [],
            "columns_with_nulls": {},
        },
    }

    # Verificar número mínimo de registros
    if len(df) < min_records:
        validation["valid"] = False
        validation["errors"].append(
            f"Insuficientes registros: {len(df)} < {min_records}"
        )

    # Verificar columnas requeridas
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        validation["valid"] = False
        validation["errors"].append(f"Columnas faltantes: {missing_cols}")
        validation["stats"]["missing_columns"] = missing_cols

    # Verificar valores nulos en columnas críticas
    for col in required_columns:
        if col in df.columns:
            null_count = df[col].isnull().sum()
            null_pct = (null_count / len(df)) * 100

            if null_pct > 0:
                validation["stats"]["columns_with_nulls"][col] = {
                    "count": null_count,
                    "percentage": null_pct,
                }

                if null_pct > 50:
                    validation["warnings"].append(
                        f"Columna '{col}' tiene {null_pct:.1f}% valores nulos"
                    )

    return validation


def print_data_summary(df, title: str = "Dataset Summary") -> None:
    """
    Imprime resumen formateado de un dataset.

    Args:
        df: DataFrame a resumir
        title: Título del resumen
    """
    print_header(title, "-", 60)

    print(f"📊 Registros: {len(df):,}")
    print(f"📊 Columnas: {len(df.columns)}")
    print(f"📊 Tamaño en memoria: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

    # Top 5 columnas con más nulos
    null_counts = df.isnull().sum()
    top_nulls = null_counts[null_counts > 0].nlargest(5)

    if len(top_nulls) > 0:
        print(f"\n⚠️  Columnas con más valores nulos:")
        for col, count in top_nulls.items():
            pct = (count / len(df)) * 100
            print(f"   • {col}: {count:,} ({pct:.1f}%)")

    # Tipos de datos
    print(f"\n📈 Distribución por tipo de dato:")
    dtype_counts = df.dtypes.value_counts()
    for dtype, count in dtype_counts.items():
        print(f"   • {dtype}: {count} columnas")

    print()


# Constantes comunes para scripts
DEFAULT_FIGSIZE = (12, 8)
DEFAULT_COLOR_PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

# Configuración común para plots
PLOT_CONFIG = {
    "figure_size": DEFAULT_FIGSIZE,
    "color_palette": DEFAULT_COLOR_PALETTE,
    "font_size": 12,
    "title_font_size": 14,
    "dpi": 100,
}

# common/logging_config.py
"""
Configuración centralizada de logging para Ballers App.
Implementa logging estructurado con diferentes niveles y formatos.
"""
import json
import logging
import logging.config
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class StructuredFormatter(logging.Formatter):
    """
    Formatter personalizado que crea logs estructurados en formato JSON.
    Esto facilita el análisis automatizado de logs.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Convierte el log record en un JSON estructurado.

        Args:
            record: El registro de log de Python

        Returns:
            str: Log formateado como JSON
        """
        # Datos básicos del log
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Añadir datos extra si existen
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        # Añadir información de excepción si existe
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Añadir stack trace si existe
        if record.stack_info:
            log_data["stack_info"] = record.stack_info

        return json.dumps(log_data, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """
    Formatter para consola con colores y formato legible.
    Perfecto para desarrollo local.
    """

    # Códigos de color ANSI
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Formato con colores para desarrollo"""
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        # Formato: [TIMESTAMP] [LEVEL] module.function:line - message
        formatted = f"{color}[{datetime.now().strftime('%H:%M:%S')}] [{record.levelname:8}]{reset} "
        formatted += (
            f"{record.module}.{record.funcName}:{record.lineno} - {record.getMessage()}"
        )

        # Añadir datos extra si existen
        if hasattr(record, "extra_data") and record.extra_data:
            formatted += f" | {record.extra_data}"

        return formatted


def get_logging_config(environment: str = "development") -> Dict[str, Any]:
    """
    Devuelve configuración de logging según el entorno.

    Args:
        environment: 'development', 'production', o 'testing'

    Returns:
        dict: Configuración de logging
    """

    # Directorio para logs
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)

    base_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredFormatter,
            },
            "console": {
                "()": ColoredConsoleFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG" if environment == "development" else "INFO",
                "formatter": "console" if environment == "development" else "simple",
                "stream": sys.stdout,
            }
        },
        "loggers": {
            "ballers": {
                "level": "DEBUG" if environment == "development" else "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "controllers": {
                "level": "INFO",  # Cambiar de DEBUG a INFO para reducir verbosidad
                "handlers": ["console"],
                "propagate": False,
            },
            "models": {"level": "INFO", "handlers": ["console"], "propagate": False},
        },
        "root": {"level": "WARNING", "handlers": ["console"]},
    }

    # Configuración específica por entorno
    if environment == "production":
        # En producción: logs a archivos + JSON estructurado
        base_config["handlers"].update(
            {
                "file_info": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "structured",
                    "filename": f"{logs_dir}/ballers_info.log",
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                },
                "file_error": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "ERROR",
                    "formatter": "structured",
                    "filename": f"{logs_dir}/ballers_error.log",
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 10,
                },
            }
        )

        # Añadir handlers de archivo a los loggers
        for logger_name in ["ballers", "controllers", "models"]:
            base_config["loggers"][logger_name]["handlers"].extend(
                ["file_info", "file_error"]
            )

    elif environment == "testing":
        # En testing: logs mínimos para no contaminar output de pytest
        base_config["handlers"]["console"]["level"] = "WARNING"
        for logger_name in ["ballers", "controllers", "models"]:
            base_config["loggers"][logger_name]["level"] = "WARNING"

    return base_config


def setup_logging(environment: str = None) -> logging.Logger:
    """
    Configura el sistema de logging para toda la aplicación.

    Args:
        environment: Entorno ('development', 'production', 'testing')
                    Si es None, se detecta automáticamente

    Returns:
        logging.Logger: Logger principal configurado
    """

    # Auto-detectar entorno si no se especifica
    if environment is None:
        if os.getenv("ENVIRONMENT") == "production":
            environment = "production"
        elif "pytest" in sys.modules:
            environment = "testing"
        else:
            environment = "development"

    # Configurar logging
    config = get_logging_config(environment)
    logging.config.dictConfig(config)

    # Obtener logger principal
    logger = logging.getLogger("ballers")

    # Log inicial de configuración
    logger.info(
        "logging_system_initialized",
        extra={
            "environment": environment,
            "log_level": logger.level,
            "handlers_count": len(logger.handlers),
        },
    )

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger con nombre específico.

    Args:
        name: Nombre del logger (ej: 'controllers.auth', 'models.user')

    Returns:
        logging.Logger: Logger configurado
    """
    return logging.getLogger(name)


class LoggerMixin:
    """
    Mixin que añade capacidades de logging a cualquier clase.

    Ejemplo de uso:
        class AuthController(LoggerMixin):
            def login(self, username):
                self.log_info("user_login_attempt", username=username)
    """

    @property
    def logger(self) -> logging.Logger:
        """Lazy loading del logger basado en el nombre de la clase"""
        if not hasattr(self, "_logger"):
            class_name = self.__class__.__name__
            module_name = self.__class__.__module__
            logger_name = f"{module_name}.{class_name}"
            self._logger = logging.getLogger(logger_name)
        return self._logger

    def log_info(self, event: str, **kwargs):
        """Log de información con datos estructurados"""
        self.logger.info(event, extra={"extra_data": kwargs})

    def log_warning(self, event: str, **kwargs):
        """Log de warning con datos estructurados"""
        self.logger.warning(event, extra={"extra_data": kwargs})

    def log_error(self, event: str, **kwargs):
        """Log de error con datos estructurados"""
        self.logger.error(event, extra={"extra_data": kwargs})

    def log_debug(self, event: str, **kwargs):
        """Log de debug con datos estructurados"""
        self.logger.debug(event, extra={"extra_data": kwargs})


# Funciones de conveniencia para usar en toda la app
def log_user_action(user_id: int, action: str, **details):
    """Log específico para acciones de usuario"""
    logger = get_logger("ballers.user_actions")
    logger.info(
        "user_action",
        extra={"extra_data": {"user_id": user_id, "action": action, **details}},
    )


def log_performance(operation: str, duration_ms: float, **context):
    """Log específico para métricas de performance"""
    logger = get_logger("ballers.performance")
    logger.info(
        "performance_metric",
        extra={
            "extra_data": {
                "operation": operation,
                "duration_ms": duration_ms,
                **context,
            }
        },
    )


def log_system_event(event: str, **details):
    """Log específico para eventos del sistema"""
    logger = get_logger("ballers.system")
    logger.info("system_event", extra={"extra_data": {"event": event, **details}})

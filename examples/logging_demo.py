# examples/logging_demo.py
"""
Demostración del sistema de logging estructurado.
Ejecuta este archivo para ver cómo funciona el logging en la práctica.
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from datetime import datetime

from common.logging_config import (
    LoggerMixin,
    get_logger,
    log_performance,
    log_user_action,
    setup_logging,
)

# Configurar logging
logger = setup_logging("development")


class DemoAuthController(LoggerMixin):
    """Ejemplo de controlador con logging integrado"""

    def authenticate_user(self, username: str, password: str):
        self.log_info(
            "authentication_attempt",
            username=username,
            timestamp=datetime.now().isoformat(),
        )

        # Simular validación
        time.sleep(0.1)  # Simular trabajo

        if username == "admin" and password == "admin123":
            self.log_info(
                "authentication_success", username=username, user_type="admin"
            )
            return True, "Login exitoso"
        else:
            self.log_warning(
                "authentication_failed", username=username, reason="invalid_credentials"
            )
            return False, "Credenciales inválidas"


def demo_basic_logging():
    """Demostración de logging básico"""
    print("\n🔹 DEMO 1: Logging Básico")
    print("=" * 50)

    logger.info("Demo iniciada")
    logger.debug("Esto es información de debug")
    logger.warning("Esto es una advertencia")
    logger.error("Esto es un error simulado")


def demo_structured_logging():
    """Demostración de logging estructurado"""
    print("\n🔹 DEMO 2: Logging Estructurado")
    print("=" * 50)

    # Logger específico
    auth_logger = get_logger("controllers.auth")

    auth_logger.info(
        "user_session_created",
        extra={
            "extra_data": {
                "user_id": 123,
                "user_type": "admin",
                "session_duration": 3600,
                "ip_address": "192.168.1.100",
            }
        },
    )

    auth_logger.error(
        "database_connection_failed",
        extra={
            "extra_data": {
                "database_url": "postgresql://...",
                "error_code": "CONNECTION_TIMEOUT",
                "retry_count": 3,
                "duration_ms": 5000,
            }
        },
    )


def demo_class_logging():
    """Demostración de logging en clases"""
    print("\n🔹 DEMO 3: Logging en Clases (LoggerMixin)")
    print("=" * 50)

    auth = DemoAuthController()

    # Login exitoso
    success, message = auth.authenticate_user("admin", "admin123")
    print(f"Resultado: {success} - {message}")

    # Login fallido
    success, message = auth.authenticate_user("hacker", "wrong_password")
    print(f"Resultado: {success} - {message}")


def demo_convenience_functions():
    """Demostración de funciones de conveniencia"""
    print("\n🔹 DEMO 4: Funciones de Conveniencia")
    print("=" * 50)

    # Log de acción de usuario
    log_user_action(
        user_id=123,
        action="create_session",
        coach_id=5,
        player_id=8,
        start_time="2025-01-02T10:30:00Z",
    )

    # Log de performance
    start_time = time.time()
    time.sleep(0.05)  # Simular operación
    duration = (time.time() - start_time) * 1000

    log_performance(
        operation="database_query",
        duration_ms=duration,
        query_type="user_authentication",
        records_affected=1,
    )


def demo_error_logging():
    """Demostración de logging de errores con stack trace"""
    print("\n🔹 DEMO 5: Logging de Errores")
    print("=" * 50)

    try:
        # Simular error
        result = 1 / 0
    except Exception as e:
        logger.error(
            "division_by_zero_error",
            exc_info=True,  # Incluye stack trace
            extra={
                "extra_data": {
                    "operation": "calculate_session_duration",
                    "input_values": {"sessions": 5, "total_time": 0},
                }
            },
        )


def demo_different_loggers():
    """Demostración de diferentes loggers por módulo"""
    print("\n🔹 DEMO 6: Loggers por Módulo")
    print("=" * 50)

    # Diferentes loggers para diferentes partes del sistema
    auth_logger = get_logger("controllers.auth")
    db_logger = get_logger("controllers.database")
    sync_logger = get_logger("controllers.google_sync")

    auth_logger.info("user_logged_in", extra={"extra_data": {"user_id": 123}})
    db_logger.info(
        "query_executed",
        extra={"extra_data": {"query": "SELECT * FROM users", "duration_ms": 45}},
    )
    sync_logger.info(
        "calendar_sync_completed",
        extra={"extra_data": {"events_processed": 15, "errors": 0}},
    )


if __name__ == "__main__":
    print("🚀 DEMOSTRACIÓN DEL SISTEMA DE LOGGING ESTRUCTURADO")
    print("=" * 60)
    print("💡 Observa cómo cada log incluye información estructurada")
    print("💡 Los colores ayudan a identificar el nivel de importancia")
    print("💡 El formato JSON permite análisis automatizado")

    demo_basic_logging()
    demo_structured_logging()
    demo_class_logging()
    demo_convenience_functions()
    demo_error_logging()
    demo_different_loggers()

    print("\n✅ DEMO COMPLETADA")
    print("💡 En producción, estos logs se guardarían en archivos JSON")
    print("💡 Herramientas como ELK Stack pueden analizarlos automáticamente")

# tests/test_logging.py
"""
Tests para el sistema de logging estructurado.
Verifican que los logs se generan correctamente.
"""
import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from common.logging_config import LoggerMixin, get_logger, setup_logging
from controllers.auth_controller import AuthController


class TestLoggingSystem:
    """Tests para verificar que el sistema de logging funciona"""

    def test_logger_setup_works(self):
        """
        TEST: El sistema de logging se configura correctamente
        """
        # ACT
        logger = setup_logging("testing")

        # ASSERT
        assert logger is not None
        assert logger.name == "ballers"
        assert logger.level <= logging.WARNING  # En testing es WARNING

    def test_structured_logging_format(self):
        """
        TEST: Los logs estructurados tienen el formato correcto
        """
        # ARRANGE
        from common.logging_config import StructuredFormatter

        formatter = StructuredFormatter()

        # Crear un record de log simulado
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.extra_data = {"user_id": 123, "action": "test"}

        # ACT
        formatted = formatter.format(record)

        # ASSERT
        assert formatted.startswith("{")  # Es JSON
        log_data = json.loads(formatted)

        assert "timestamp" in log_data
        assert log_data["level"] == "INFO"
        assert log_data["message"] == "test message"
        assert log_data["user_id"] == 123
        assert log_data["action"] == "test"

    def test_logger_mixin_works(self):
        """
        TEST: LoggerMixin añade logging a cualquier clase
        """

        # ARRANGE
        class TestClass(LoggerMixin):
            def test_method(self):
                self.log_info("test_event", test_data="value")

        # ACT & ASSERT
        with patch("logging.Logger.info") as mock_info:
            test_obj = TestClass()
            test_obj.test_method()

            # Verificar que se llamó al log
            mock_info.assert_called_once()
            args, kwargs = mock_info.call_args

            assert args[0] == "test_event"
            assert "extra" in kwargs
            assert kwargs["extra"]["extra_data"]["test_data"] == "value"


class TestAuthControllerLogging:
    """Tests específicos para logging en AuthController"""

    def test_successful_authentication_logs_correctly(self, test_db, test_admin_user):
        """
        TEST: Login exitoso genera los logs correctos
        """
        # ARRANGE
        username = test_admin_user["username"]
        password = test_admin_user["password"]

        with (
            patch("logging.Logger.info") as mock_info,
            patch("logging.Logger.warning") as mock_warning,
        ):

            # ACT
            with AuthController() as auth:
                auth.db = test_db
                success, message, user = auth.authenticate_user(username, password)

            # ASSERT
            assert success == True

            # Verificar que se generaron los logs correctos
            assert (
                mock_info.call_count >= 2
            )  # authentication_attempt + authentication_success
            assert mock_warning.call_count == 0  # No debería haber warnings

    def test_failed_authentication_logs_correctly(self, test_db):
        """
        TEST: Login fallido genera logs de warning
        """
        # ARRANGE
        username = "usuario_inexistente"
        password = "password_incorrecta"

        with (
            patch("logging.Logger.info") as mock_info,
            patch("logging.Logger.warning") as mock_warning,
        ):

            # ACT
            with AuthController() as auth:
                auth.db = test_db
                success, message, user = auth.authenticate_user(username, password)

            # ASSERT
            assert success == False

            # Verificar logs
            assert mock_info.call_count >= 1  # authentication_attempt
            assert mock_warning.call_count >= 1  # authentication_failed

    def test_authentication_exception_logs_error(self, test_db):
        """
        TEST: Excepciones durante autenticación se loggan como errores
        """
        # ARRANGE
        username = "test_user"
        password = "test_pass"

        with (
            patch("logging.Logger.info") as mock_info,
            patch("logging.Logger.error") as mock_error,
            patch(
                "controllers.auth_controller.ValidationController.validate_login_fields",
                return_value=(True, None),
            ),
            patch.object(test_db, "query", side_effect=Exception("Database error")),
        ):

            # ACT
            with AuthController() as auth:
                auth.db = test_db
                success, message, user = auth.authenticate_user(username, password)

            # ASSERT
            assert success == False
            assert "Authentication error" in message

            # Verificar que se loggó el error
            assert mock_error.call_count >= 1

    def test_logging_includes_structured_data(self, test_db, test_admin_user):
        """
        TEST: Los logs incluyen datos estructurados útiles
        """
        # ARRANGE
        username = test_admin_user["username"]
        password = test_admin_user["password"]

        with patch("logging.Logger.info") as mock_info:

            # ACT
            with AuthController() as auth:
                auth.db = test_db
                success, message, user = auth.authenticate_user(username, password)

            # ASSERT
            assert success == True

            # Verificar que los logs tienen datos estructurados
            for call in mock_info.call_args_list:
                args, kwargs = call
                if args[0] == "authentication_success":
                    extra_data = kwargs["extra"]["extra_data"]
                    assert "username" in extra_data
                    assert "user_id" in extra_data
                    assert "user_type" in extra_data
                    assert extra_data["username"] == username


class TestLoggingConvenienceFunctions:
    """Tests para las funciones de conveniencia de logging"""

    def test_log_user_action_works(self):
        """
        TEST: log_user_action genera logs estructurados
        """
        # ARRANGE
        from common.logging_config import log_user_action

        with patch("logging.Logger.info") as mock_info:

            # ACT
            log_user_action(
                user_id=123, action="create_session", coach_id=5, player_id=8
            )

            # ASSERT
            mock_info.assert_called_once()
            args, kwargs = mock_info.call_args

            assert args[0] == "user_action"
            extra_data = kwargs["extra"]["extra_data"]
            assert extra_data["user_id"] == 123
            assert extra_data["action"] == "create_session"
            assert extra_data["coach_id"] == 5

    def test_log_performance_works(self):
        """
        TEST: log_performance genera métricas estructuradas
        """
        # ARRANGE
        from common.logging_config import log_performance

        with patch("logging.Logger.info") as mock_info:

            # ACT
            log_performance(
                operation="database_query", duration_ms=45.5, query_type="user_auth"
            )

            # ASSERT
            mock_info.assert_called_once()
            args, kwargs = mock_info.call_args

            assert args[0] == "performance_metric"
            extra_data = kwargs["extra"]["extra_data"]
            assert extra_data["operation"] == "database_query"
            assert extra_data["duration_ms"] == 45.5
            assert extra_data["query_type"] == "user_auth"


class TestLoggingInDifferentEnvironments:
    """Tests para verificar logging en diferentes entornos"""

    def test_development_logging_has_debug_level(self):
        """
        TEST: En desarrollo, el nivel de logging es DEBUG
        """
        # ACT
        logger = setup_logging("development")

        # ASSERT
        assert logger.level <= logging.DEBUG

    def test_production_logging_has_info_level(self):
        """
        TEST: En producción, el nivel de logging es INFO
        """
        # ACT
        logger = setup_logging("production")

        # ASSERT
        assert logger.level <= logging.INFO

    def test_testing_logging_has_warning_level(self):
        """
        TEST: En testing, el nivel de logging es WARNING (para no contaminar output)
        """
        # ACT
        logger = setup_logging("testing")

        # ASSERT
        assert logger.level <= logging.WARNING

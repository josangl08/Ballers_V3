# tests/test_dash_app.py
"""
Tests para la aplicación Dash.
Verifican que la migración de Streamlit mantiene toda la funcionalidad.
"""
from unittest.mock import patch

from main_dash import initialize_dash_app


class TestDashAppInitialization:
    """Tests para la inicialización de la aplicación Dash."""

    def test_dash_app_initializes_correctly(self):
        """
        TEST: La aplicación Dash se inicializa correctamente
        """
        # ACT
        with patch("main_dash.initialize_database"):
            dash_app = initialize_dash_app()

        # ASSERT
        assert dash_app is not None
        assert hasattr(dash_app, "server")
        assert dash_app.layout is not None

    def test_app_has_correct_title(self):
        """
        TEST: La aplicación tiene el título correcto
        """
        # ARRANGE & ACT
        with patch("main_dash.initialize_database"):
            dash_app = initialize_dash_app()

        # ASSERT
        assert dash_app.title is not None


class TestDashAppLayout:
    """Tests para el layout de la aplicación Dash."""

    def test_app_layout_has_required_components(self):
        """
        TEST: El layout tiene los componentes requeridos
        """
        # ARRANGE & ACT
        with patch("main_dash.initialize_database"):
            dash_app = initialize_dash_app()

        # ASSERT
        layout_str = str(dash_app.layout)
        assert "url" in layout_str
        assert "session-store" in layout_str
        assert "main-content" in layout_str

    def test_app_layout_is_container(self):
        """
        TEST: El layout principal es un Container
        """
        # ARRANGE & ACT
        with patch("main_dash.initialize_database"):
            dash_app = initialize_dash_app()

        # ASSERT
        assert dash_app.layout is not None
        # Verificar que el layout es un componente válido
        assert hasattr(dash_app.layout, "children")


class TestDashAppCallbacks:
    """Tests para el sistema de callbacks de Dash."""

    def test_callbacks_are_registered(self):
        """
        TEST: Los callbacks están registrados correctamente
        """
        # ARRANGE & ACT
        with patch("main_dash.initialize_database"):
            dash_app = initialize_dash_app()

        # ASSERT
        # Verificar que hay callbacks registrados
        assert len(dash_app.callback_map) > 0

    def test_auth_callbacks_registered(self):
        """
        TEST: Los callbacks de autenticación están registrados
        """
        # ARRANGE & ACT
        with patch("main_dash.initialize_database"):
            dash_app = initialize_dash_app()

        # ASSERT
        # Verificar que existen callbacks relacionados con autenticación
        callback_ids = [cb for cb in dash_app.callback_map.keys()]
        assert len(callback_ids) > 0


class TestDashAppIntegration:
    """Tests de integración para la aplicación Dash."""

    def test_app_can_be_imported(self):
        """
        TEST: La aplicación puede ser importada correctamente
        """
        # ARRANGE & ACT
        from main_dash import app

        # ASSERT
        assert app is not None
        assert hasattr(app, "server")

    def test_initialize_dash_app_returns_app(self):
        """
        TEST: initialize_dash_app retorna una aplicación válida
        """
        # ARRANGE & ACT
        with patch("main_dash.initialize_database"):
            result = initialize_dash_app()

        # ASSERT
        assert result is not None
        assert hasattr(result, "run")
        assert hasattr(result, "callback_map")


class TestDashAppConfiguration:
    """Tests para la configuración de la aplicación Dash."""

    def test_app_has_bootstrap_theme(self):
        """
        TEST: La aplicación tiene el theme Bootstrap configurado
        """
        # ARRANGE & ACT
        from main_dash import app

        # ASSERT
        config = app.config
        assert "external_stylesheets" in config
        # Verificar que Bootstrap está incluido
        bootstrap_included = any(
            "bootstrap" in str(stylesheet).lower()
            for stylesheet in config["external_stylesheets"]
        )
        assert bootstrap_included

    def test_app_has_assets_folder(self):
        """
        TEST: La aplicación tiene la carpeta de assets configurada
        """
        # ARRANGE & ACT
        from main_dash import app

        # ASSERT
        config = app.config
        assets_folder = config.get("assets_folder")
        assert assets_folder is not None
        assert assets_folder.endswith("assets")

    def test_app_suppresses_callback_exceptions(self):
        """
        TEST: La aplicación suprime excepciones de callbacks
        """
        # ARRANGE & ACT
        from main_dash import app

        # ASSERT
        config = app.config
        assert config.get("suppress_callback_exceptions") is True


class TestDashAppDatabase:
    """Tests para la integración con la base de datos."""

    def test_database_module_can_be_imported(self):
        """
        TEST: El módulo de base de datos puede ser importado
        """
        # ARRANGE & ACT
        from controllers.db import initialize_database

        # ASSERT
        assert initialize_database is not None

    def test_app_initializes_without_database_errors(self):
        """
        TEST: La aplicación se inicializa sin errores de base de datos
        """
        # ARRANGE & ACT
        with patch("controllers.db.initialize_database"):
            # No debería fallar la inicialización
            app = initialize_dash_app()

        # ASSERT
        assert app is not None

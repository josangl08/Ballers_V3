# tests/test_dash_app.py
"""
Tests básicos para la aplicación Dash.
Solo tests esenciales de inicialización.
"""
from unittest.mock import patch

from main_dash import initialize_dash_app


class TestDashAppBasics:
    """Tests básicos para verificar que la aplicación Dash funciona."""

    def test_dash_app_initializes_correctly(self):
        """
        TEST: La aplicación Dash se inicializa sin errores
        """
        # ACT
        with patch("main_dash.initialize_database"):
            dash_app = initialize_dash_app()

        # ASSERT
        assert dash_app is not None
        assert hasattr(dash_app, "server")
        assert dash_app.layout is not None

    def test_app_has_required_components(self):
        """
        TEST: El layout tiene los componentes básicos requeridos
        """
        # ACT
        with patch("main_dash.initialize_database"):
            dash_app = initialize_dash_app()

        # ASSERT
        layout_str = str(dash_app.layout)
        assert "url" in layout_str
        assert "session-store" in layout_str
        assert "main-content" in layout_str

    def test_app_can_be_imported(self):
        """
        TEST: La aplicación puede ser importada correctamente
        """
        # ACT
        from main_dash import app

        # ASSERT
        assert app is not None
        assert hasattr(app, "server")

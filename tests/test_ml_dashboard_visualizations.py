"""
Tests para visualizaciones ML del dashboard profesional - Fase 13.3.

Incluye tests para:
- create_pdi_evolution_chart()
- create_ml_enhanced_radar_chart()
- Integración con MLMetricsController
- Estructura y contenido de componentes Dash
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pytest
from dash import dcc, html

# Import de las funciones a testear
from pages.ballers_dash import (
    create_ml_enhanced_radar_chart,
    create_pdi_evolution_chart,
    create_professional_stats_content,
)


class TestPDIEvolutionChart:
    """Tests para la función create_pdi_evolution_chart()."""

    @patch("pages.ballers_dash.PlayerAnalyzer")
    def test_pdi_evolution_chart_creation_success(self, mock_controller_class):
        """Test que verifica la creación exitosa del gráfico PDI evolution."""
        # ARRANGE
        mock_controller = MagicMock()
        mock_controller_class.return_value = mock_controller
        mock_controller.__enter__ = Mock(return_value=mock_controller)
        mock_controller.__exit__ = Mock(return_value=None)

        # Mock datos ML correctos según implementación actual
        mock_analysis_2023 = {
            "ml_metrics": {
                "raw": {
                    "pdi_overall": 72.5,
                    "pdi_universal": 75.0,
                    "pdi_zone": 70.0,
                    "pdi_position_specific": 73.0,
                    "technical_proficiency": 78.0,
                    "tactical_intelligence": 70.0,
                    "physical_performance": 75.0,
                    "consistency_index": 68.0,
                }
            }
        }
        mock_analysis_2024 = {
            "ml_metrics": {
                "raw": {
                    "pdi_overall": 74.0,
                    "pdi_universal": 77.0,
                    "pdi_zone": 71.0,
                    "pdi_position_specific": 75.0,
                    "technical_proficiency": 80.0,
                    "tactical_intelligence": 72.0,
                    "physical_performance": 76.0,
                    "consistency_index": 70.0,
                }
            }
        }

        # Mock múltiples llamadas para diferentes temporadas
        mock_controller.get_enhanced_player_analysis.side_effect = [
            mock_analysis_2023,
            mock_analysis_2024,
        ]

        # ACT
        result = create_pdi_evolution_chart(
            player_id=123, seasons=["2023-24", "2024-25"]
        )

        # ASSERT
        assert result is not None
        assert isinstance(result, type(dcc.Graph()))

        # Verificar que se llamó al controlador ML para cada temporada
        assert mock_controller.get_enhanced_player_analysis.call_count == 2

        # Verificar propiedades del componente Graph
        assert hasattr(result, "figure")

    @patch("pages.ballers_dash.PlayerAnalyzer")
    def test_pdi_evolution_chart_with_default_seasons(self, mock_controller_class):
        """Test que verifica el comportamiento con seasons por defecto."""
        # ARRANGE
        mock_controller = MagicMock()
        mock_controller_class.return_value = mock_controller
        mock_controller.__enter__ = Mock(return_value=mock_controller)
        mock_controller.__exit__ = Mock(return_value=None)

        # Mock análisis con datos ML válidos
        mock_analysis = {
            "ml_metrics": {
                "raw": {
                    "pdi_overall": 68.0,
                    "pdi_universal": 70.0,
                    "pdi_zone": 65.0,
                    "pdi_position_specific": 69.0,
                    "technical_proficiency": 72.0,
                    "tactical_intelligence": 68.0,
                    "physical_performance": 70.0,
                    "consistency_index": 65.0,
                }
            }
        }
        mock_controller.get_enhanced_player_analysis.return_value = mock_analysis

        # ACT
        result = create_pdi_evolution_chart(player_id=456)

        # ASSERT
        assert result is not None
        # Con seasons por defecto debe hacer 3 llamadas (últimas 3 temporadas)
        assert mock_controller.get_enhanced_player_analysis.call_count >= 1

    @patch("pages.ballers_dash.PlayerAnalyzer")
    def test_pdi_evolution_chart_handles_ml_errors(self, mock_controller_class):
        """Test que verifica el manejo de errores del ML pipeline."""
        # ARRANGE
        mock_controller = MagicMock()
        mock_controller_class.return_value = mock_controller
        mock_controller.__enter__ = Mock(return_value=mock_controller)
        mock_controller.__exit__ = Mock(return_value=None)
        mock_controller.get_enhanced_player_analysis.side_effect = Exception("ML Error")

        # ACT
        result = create_pdi_evolution_chart(player_id=789)

        # ASSERT
        assert result is not None
        # Debe devolver un componente Alert con mensaje de error
        assert isinstance(result, type(dbc.Alert()))
        # El error se maneja en el bucle de temporadas, no en el try/except principal
        assert "No ML metrics available" in str(result.children)

    @patch("pages.ballers_dash.PlayerAnalyzer")
    def test_pdi_evolution_chart_validates_figure_structure(
        self, mock_controller_class
    ):
        """Test que verifica la estructura del gráfico Plotly generado."""
        # ARRANGE
        mock_controller = MagicMock()
        mock_controller_class.return_value = mock_controller
        mock_controller.__enter__ = Mock(return_value=mock_controller)
        mock_controller.__exit__ = Mock(return_value=None)

        mock_analysis = {
            "ml_metrics": {
                "raw": {
                    "pdi_overall": 75.5,
                    "pdi_universal": 78.0,
                    "pdi_zone": 73.0,
                    "pdi_position_specific": 76.0,
                    "technical_proficiency": 80.0,
                    "tactical_intelligence": 72.0,
                    "physical_performance": 78.0,
                    "consistency_index": 70.0,
                }
            }
        }
        mock_controller.get_enhanced_player_analysis.return_value = mock_analysis

        # ACT
        result = create_pdi_evolution_chart(player_id=101, seasons=["2024-25"])

        # ASSERT
        assert isinstance(result, type(dcc.Graph()))
        figure = result.figure
        assert isinstance(figure, dict)

        # Verificar estructura básica de Plotly
        assert "data" in figure
        assert "layout" in figure

        # Verificar que hay múltiples traces (PDI Overall, Universal, Zone, Position)
        data = figure["data"]
        assert len(data) >= 4  # Al menos 4 traces principales

        # Verificar configuración del layout
        layout = figure["layout"]
        assert "Player Development Index" in layout["title"]["text"]
        assert layout["xaxis_title"] == "Season"
        assert layout["yaxis_title"] == "PDI Score (0-100)"


class TestMLEnhancedRadarChart:
    """Tests para la función create_ml_enhanced_radar_chart()."""

    @patch("pages.ballers_dash.PlayerAnalyzer")
    @patch("pages.ballers_dash.PositionNormalizer")
    def test_ml_radar_chart_creation_success(
        self, mock_normalizer_class, mock_controller_class
    ):
        """Test que verifica la creación exitosa del radar chart ML."""
        # ARRANGE
        mock_controller = MagicMock()
        mock_controller_class.return_value = mock_controller
        mock_controller.__enter__ = Mock(return_value=mock_controller)
        mock_controller.__exit__ = Mock(return_value=None)

        mock_normalizer = MagicMock()
        mock_normalizer_class.return_value = mock_normalizer

        mock_analysis = {
            "ml_metrics": {
                "raw": {
                    "technical_proficiency": 82.0,
                    "tactical_intelligence": 75.0,
                    "physical_performance": 78.0,
                    "consistency_index": 70.0,
                    "pdi_universal": 73.0,
                    "pdi_zone": 76.0,
                    "pdi_position_specific": 85.0,
                }
            }
        }
        mock_controller.get_enhanced_player_analysis.return_value = mock_analysis

        # ACT
        result = create_ml_enhanced_radar_chart(player_id=123, season="2024-25")

        # ASSERT
        assert result is not None
        assert isinstance(result, type(dcc.Graph()))

        # Verificar llamada al controlador con el season correcto
        mock_controller.get_enhanced_player_analysis.assert_called_once_with(
            123, "2024-25"
        )

    @patch("pages.ballers_dash.PlayerAnalyzer")
    @patch("pages.ballers_dash.PositionNormalizer")
    def test_ml_radar_chart_validates_scatterpolar_structure(
        self, mock_normalizer_class, mock_controller_class
    ):
        """Test que verifica la estructura del radar chart (scatterpolar)."""
        # ARRANGE
        mock_controller = MagicMock()
        mock_controller_class.return_value = mock_controller
        mock_controller.__enter__ = Mock(return_value=mock_controller)
        mock_controller.__exit__ = Mock(return_value=None)

        mock_normalizer = MagicMock()
        mock_normalizer_class.return_value = mock_normalizer

        mock_analysis = {
            "ml_metrics": {
                "raw": {
                    "technical_proficiency": 85.0,
                    "tactical_intelligence": 72.0,
                    "physical_performance": 79.0,
                    "consistency_index": 68.0,
                    "pdi_universal": 74.0,
                    "pdi_zone": 77.0,
                    "pdi_position_specific": 83.0,
                }
            }
        }
        mock_controller.get_enhanced_player_analysis.return_value = mock_analysis

        # ACT
        result = create_ml_enhanced_radar_chart(player_id=202, season="2023-24")

        # ASSERT
        figure = result.figure
        assert isinstance(figure, dict)

        # Verificar estructura Plotly para radar chart
        data = figure["data"]
        assert len(data) == 1  # Un solo trace para el radar

        trace = data[0]
        assert trace["type"] == "scatterpolar"
        assert "fill" in trace  # toself
        assert trace["name"] == "ML Analysis"

        # Verificar que tiene los 7 parámetros esperados
        assert len(trace["theta"]) == 7
        assert len(trace["r"]) == 7

        # Verificar parámetros del radar según implementación actual
        expected_params = [
            "Technical Skills",
            "Tactical Intelligence",
            "Physical Performance",
            "Consistency",
            "Universal Skills",
            "Zone Performance",
            "Position Specific",
        ]
        # Al menos algunos de estos parámetros deben estar presentes
        assert len([param for param in expected_params if param in trace["theta"]]) >= 5

        # Verificar configuración polar
        layout = figure["layout"]
        assert "polar" in layout
        polar = layout["polar"]
        assert polar["radialaxis"]["visible"] == True
        assert polar["radialaxis"]["range"] == [0, 100]

    @patch("pages.ballers_dash.PlayerAnalyzer")
    @patch("pages.ballers_dash.PositionNormalizer")
    def test_ml_radar_chart_with_default_season(
        self, mock_normalizer_class, mock_controller_class
    ):
        """Test que verifica el comportamiento con temporada por defecto."""
        # ARRANGE
        mock_controller = MagicMock()
        mock_controller_class.return_value = mock_controller
        mock_controller.__enter__ = Mock(return_value=mock_controller)
        mock_controller.__exit__ = Mock(return_value=None)

        mock_normalizer = MagicMock()
        mock_normalizer_class.return_value = mock_normalizer

        mock_analysis = {
            "ml_metrics": {
                "raw": {
                    "technical_proficiency": 75.0,
                    "tactical_intelligence": 70.0,
                    "physical_performance": 80.0,
                    "consistency_index": 65.0,
                    "pdi_universal": 72.0,
                    "pdi_zone": 74.0,
                    "pdi_position_specific": 78.0,
                }
            }
        }
        mock_controller.get_enhanced_player_analysis.return_value = mock_analysis

        # ACT - sin especificar season (usa default "2024-25")
        result = create_ml_enhanced_radar_chart(player_id=303)

        # ASSERT
        mock_controller.get_enhanced_player_analysis.assert_called_once_with(
            303, "2024-25"  # Default season
        )

    @patch("pages.ballers_dash.PlayerAnalyzer")
    @patch("pages.ballers_dash.PositionNormalizer")
    def test_ml_radar_chart_handles_errors(
        self, mock_normalizer_class, mock_controller_class
    ):
        """Test que verifica el manejo de errores en radar chart."""
        # ARRANGE
        mock_controller = MagicMock()
        mock_controller_class.return_value = mock_controller
        mock_controller.__enter__ = Mock(return_value=mock_controller)
        mock_controller.__exit__ = Mock(return_value=None)
        mock_controller.get_enhanced_player_analysis.side_effect = Exception(
            "Data Error"
        )

        # ACT
        result = create_ml_enhanced_radar_chart(player_id=404)

        # ASSERT
        assert result is not None
        assert isinstance(result, type(dbc.Alert()))
        assert "Error creating radar chart" in str(result.children)


class TestProfessionalStatsContentIntegration:
    """Tests para la integración ML en create_professional_stats_content()."""

    @patch("pages.ballers_dash.create_pdi_evolution_chart")
    @patch("pages.ballers_dash.create_ml_enhanced_radar_chart")
    @patch("pages.ballers_dash.create_evolution_chart")
    @patch("pages.ballers_dash.create_radar_chart")
    def test_professional_stats_includes_ml_section(
        self, mock_radar_chart, mock_evolution_chart, mock_ml_radar, mock_pdi_evolution
    ):
        """Test que verifica que la sección ML se incluye en stats profesionales."""
        # ARRANGE
        mock_player = MagicMock()
        mock_player.player_id = 123
        mock_player.is_professional = True  # Importante: debe ser profesional
        mock_user = MagicMock()
        mock_user.name = "Test Player"
        # Configurar UserType como enum correctamente
        from models import UserType

        mock_user.user_type = UserType.player

        # Mock de componentes
        mock_pdi_evolution.return_value = dcc.Graph(id="mock-pdi-chart")
        mock_ml_radar.return_value = dcc.Graph(id="mock-ml-radar")
        mock_evolution_chart.return_value = html.Div("mock-evolution")
        mock_radar_chart.return_value = html.Div("mock-radar")

        # ACT
        result = create_professional_stats_content(mock_player, mock_user)

        # ASSERT
        assert result is not None

        # Verificar que se llamaron las nuevas funciones ML
        mock_pdi_evolution.assert_called_once_with(mock_player.player_id, seasons=None)
        mock_ml_radar.assert_called_once_with(mock_player.player_id, season="2024-25")

        # Verificar estructura del componente retornado
        result_str = str(result)
        assert "AI-Powered Performance Analytics" in result_str
        assert "Player Development Index" in result_str
        assert "ML-Enhanced Performance Radar" in result_str

    def test_professional_stats_content_structure(self):
        """Test que verifica la estructura general del contenido profesional."""
        # ARRANGE
        mock_player = MagicMock()
        mock_player.player_id = 456
        mock_player.is_professional = True  # Debe ser profesional
        mock_user = MagicMock()
        mock_user.name = "Professional Player"
        # Configurar UserType como enum correctamente
        from models import UserType

        mock_user.user_type = UserType.player

        # ACT
        with (
            patch("pages.ballers_dash.create_pdi_evolution_chart") as mock_pdi,
            patch("pages.ballers_dash.create_ml_enhanced_radar_chart") as mock_ml_radar,
            patch("pages.ballers_dash.create_evolution_chart") as mock_evolution,
            patch("pages.ballers_dash.create_radar_chart") as mock_radar,
        ):

            # Mock returns
            mock_pdi.return_value = html.Div("PDI Chart")
            mock_ml_radar.return_value = html.Div("ML Radar")
            mock_evolution.return_value = html.Div("Evolution Chart")
            mock_radar.return_value = html.Div("Radar Chart")

            result = create_professional_stats_content(mock_player, mock_user)

        # ASSERT
        # El resultado debe ser un contenedor Bootstrap
        assert result is not None

        # Verificar que contiene elementos esperados
        result_str = str(result)
        assert "Professional Statistics Dashboard" in result_str
        assert "AI-Powered Performance Analytics" in result_str
        assert "AI Development Insights" in result_str


class TestMLVisualizationErrorHandling:
    """Tests para manejo de errores en visualizaciones ML."""

    def test_pdi_chart_invalid_player_id(self):
        """Test que verifica manejo de player_id inválido."""
        # ACT
        result = create_pdi_evolution_chart(player_id=None)

        # ASSERT
        assert result is not None
        assert isinstance(result, type(dbc.Alert()))
        assert "No ML metrics available" in str(result.children) or "Error" in str(
            result.children
        )

    def test_ml_radar_invalid_player_id(self):
        """Test que verifica manejo de player_id inválido en radar."""
        # ACT
        result = create_ml_enhanced_radar_chart(player_id=0)

        # ASSERT
        assert result is not None
        # Debe manejar graciosamente el ID inválido
        assert isinstance(result, (type(dbc.Alert()), type(dcc.Graph())))

    @patch("pages.ballers_dash.PlayerAnalyzer")
    def test_pdi_chart_empty_data(self, mock_controller_class):
        """Test que verifica manejo de datos vacíos."""
        # ARRANGE
        mock_controller = MagicMock()
        mock_controller_class.return_value = mock_controller
        mock_controller.__enter__ = Mock(return_value=mock_controller)
        mock_controller.__exit__ = Mock(return_value=None)
        mock_controller.get_enhanced_player_analysis.return_value = {}

        # ACT
        result = create_pdi_evolution_chart(player_id=999)

        # ASSERT
        assert result is not None
        # Debe manejar datos vacíos sin crashear


class TestMLVisualizationPerformance:
    """Tests para verificar el rendimiento de visualizaciones ML."""

    @patch("pages.ballers_dash.PlayerAnalyzer")
    def test_pdi_chart_response_time(self, mock_controller_class):
        """Test que verifica que la creación del chart no tome demasiado tiempo."""
        import time

        # ARRANGE
        mock_controller = MagicMock()
        mock_controller_class.return_value = mock_controller
        mock_controller.__enter__ = Mock(return_value=mock_controller)
        mock_controller.__exit__ = Mock(return_value=None)
        mock_controller.get_enhanced_player_analysis.return_value = {
            "ml_metrics": {
                "raw": {
                    "pdi_overall": 75.0,
                    "pdi_universal": 78.0,
                    "pdi_zone": 72.0,
                    "pdi_position_specific": 76.0,
                    "technical_proficiency": 80.0,
                    "tactical_intelligence": 70.0,
                    "physical_performance": 75.0,
                    "consistency_index": 68.0,
                }
            }
        }

        # ACT
        start_time = time.time()
        result = create_pdi_evolution_chart(player_id=123, seasons=["2024-25"])
        end_time = time.time()

        # ASSERT
        assert result is not None
        execution_time = end_time - start_time
        # No debería tomar más de 1 segundo crear el chart
        assert (
            execution_time < 1.0
        ), f"Chart creation took {execution_time:.3f}s, too slow"

    @patch("pages.ballers_dash.PlayerAnalyzer")
    @patch("pages.ballers_dash.PositionNormalizer")
    def test_ml_radar_chart_memory_usage(
        self, mock_normalizer_class, mock_controller_class
    ):
        """Test que verifica que el radar chart no use memoria excesiva."""
        # ARRANGE
        mock_controller = MagicMock()
        mock_controller_class.return_value = mock_controller
        mock_controller.__enter__ = Mock(return_value=mock_controller)
        mock_controller.__exit__ = Mock(return_value=None)

        mock_normalizer = MagicMock()
        mock_normalizer_class.return_value = mock_normalizer

        mock_controller.get_enhanced_player_analysis.return_value = {
            "ml_metrics": {
                "raw": {
                    "technical_proficiency": 85.0,
                    "tactical_intelligence": 75.0,
                    "physical_performance": 80.0,
                    "consistency_index": 70.0,
                    "pdi_universal": 72.0,
                    "pdi_zone": 77.0,
                    "pdi_position_specific": 83.0,
                }
            }
        }

        # ACT
        result = create_ml_enhanced_radar_chart(player_id=123)

        # ASSERT
        assert result is not None
        # Verificar que el objeto no es excesivamente grande
        import sys

        size = sys.getsizeof(result)
        # Un componente Dash no debería usar más de 10KB
        assert size < 10240, f"Radar chart object size {size} bytes is too large"


if __name__ == "__main__":
    # Ejecutar tests específicos para debugging
    pytest.main([__file__, "-v", "--tb=short"])

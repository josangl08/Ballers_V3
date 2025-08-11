"""
Test suite para el módulo de ML Metrics.

Incluye tests para:
- Modelo MLMetrics
- MLMetricsController
- Cálculo de PDI
- Integración con base de datos
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from ml_system.evaluation.analysis.player_analyzer import PlayerAnalyzer
from models.ml_metrics_model import MLMetrics


class TestMLMetricsModel:
    """Tests para el modelo MLMetrics."""

    def test_ml_metrics_model_creation(self):
        """Test que verifica la creación del modelo MLMetrics."""
        ml_metrics = MLMetrics(
            player_id=1,
            season="2024-25",
            pdi_overall=75.5,
            pdi_universal=80.0,
            pdi_zone=70.0,
            pdi_position_specific=76.0,
            technical_proficiency=85.0,
            tactical_intelligence=70.0,
            physical_performance=80.0,
            consistency_index=65.0,
            position_analyzed="CMF",
            model_version="1.0",
        )

        # Verificar atributos básicos
        assert ml_metrics.player_id == 1
        assert ml_metrics.season == "2024-25"
        assert ml_metrics.pdi_overall == 75.5
        assert ml_metrics.position_analyzed == "CMF"
        assert ml_metrics.model_version == "1.0"

    def test_pdi_breakdown_property(self):
        """Test del property pdi_breakdown."""
        ml_metrics = MLMetrics(
            player_id=1,
            season="2024-25",
            pdi_overall=75.0,
            pdi_universal=80.0,
            pdi_zone=70.0,
            pdi_position_specific=75.0,
            technical_proficiency=85.0,
            tactical_intelligence=70.0,
            physical_performance=80.0,
            consistency_index=65.0,
        )

        breakdown = ml_metrics.pdi_breakdown

        # Verificar estructura
        assert "pdi_overall" in breakdown
        assert "components" in breakdown
        assert "development_areas" in breakdown
        assert "rankings" in breakdown

        # Verificar componentes con pesos correctos
        components = breakdown["components"]
        assert components["universal"]["weight"] == 0.40
        assert components["zone"]["weight"] == 0.35
        assert components["position_specific"]["weight"] == 0.25

        # Verificar contribuciones calculadas
        assert components["universal"]["contribution"] == 80.0 * 0.40
        assert components["zone"]["contribution"] == 70.0 * 0.35
        assert components["position_specific"]["contribution"] == 75.0 * 0.25

    def test_is_stale_property(self):
        """Test del property is_stale."""
        # Caso 1: Sin fecha de cálculo (stale)
        ml_metrics = MLMetrics(player_id=1, season="2024-25")
        assert ml_metrics.is_stale is True

        # Caso 2: Calculado hace menos de 7 días (fresh)
        ml_metrics.last_calculated = datetime.utcnow() - timedelta(days=3)
        assert ml_metrics.is_stale is False

        # Caso 3: Calculado hace más de 7 días (stale)
        ml_metrics.last_calculated = datetime.utcnow() - timedelta(days=10)
        assert ml_metrics.is_stale is True

    def test_get_strength_areas(self):
        """Test del método get_strength_areas."""
        ml_metrics = MLMetrics(
            player_id=1,
            season="2024-25",
            technical_proficiency=85.0,  # Fortaleza
            tactical_intelligence=70.0,  # Normal
            physical_performance=90.0,  # Fortaleza
            consistency_index=45.0,  # Debilidad
        )

        strengths = ml_metrics.get_strength_areas(threshold=75.0)

        assert len(strengths) == 2
        assert "Technical Proficiency" in strengths
        assert "Physical Performance" in strengths
        assert "Tactical Intelligence" not in strengths
        assert "Consistency" not in strengths

    def test_get_improvement_areas(self):
        """Test del método get_improvement_areas."""
        ml_metrics = MLMetrics(
            player_id=1,
            season="2024-25",
            technical_proficiency=85.0,  # Fortaleza
            tactical_intelligence=45.0,  # Mejora
            physical_performance=90.0,  # Fortaleza
            consistency_index=30.0,  # Mejora
        )

        improvements = ml_metrics.get_improvement_areas(threshold=50.0)

        assert len(improvements) == 2
        assert "Tactical Intelligence" in improvements
        assert "Consistency" in improvements
        assert "Technical Proficiency" not in improvements
        assert "Physical Performance" not in improvements


class TestMLMetricsController:
    """Tests para el controlador MLMetricsController."""

    def test_controller_initialization(self):
        """Test de inicialización del controlador."""
        controller = MLMetricsController()

        # Verificar configuración por defecto
        assert controller.model_version == "1.0"
        assert controller.cache_duration_days == 7

        # Verificar pesos PDI
        weights = controller.pdi_weights
        assert weights["universal"] == 0.40
        assert weights["zone"] == 0.35
        assert weights["position_specific"] == 0.25

        # Verificar suma de pesos = 1.0
        assert sum(weights.values()) == 1.0

        # Verificar posiciones soportadas
        positions = controller.supported_positions
        assert "GK" in positions
        assert "CMF" in positions
        assert "CF" in positions
        assert len(positions) == 8

    def test_calculate_universal_metrics(self):
        """Test del cálculo de métricas universales."""
        controller = MLMetricsController()

        # Mock de estadísticas
        mock_stats = MagicMock()
        mock_stats.accurate_passes_pct = 85.0
        mock_stats.duels_won_pct = 60.0
        mock_stats.minutes_played = 2700  # 30 partidos * 90 min
        mock_stats.matches_played = 30
        mock_stats.yellow_cards = 3

        universal_score = controller._calculate_universal_metrics(mock_stats)

        # Verificar que devuelve un score válido
        assert isinstance(universal_score, float)
        assert 0 <= universal_score <= 100

        # Con buenas estadísticas debería ser > 50
        assert universal_score > 50

    def test_calculate_zone_metrics(self):
        """Test del cálculo de métricas por zona."""
        controller = MLMetricsController()

        # Mock de estadísticas
        mock_stats = MagicMock()
        mock_stats.defensive_duels_won_pct = 70.0
        mock_stats.successful_defensive_actions_per_90 = 8.0
        mock_stats.interceptions_per_90 = 4.0
        mock_stats.passes_per_90 = 80.0
        mock_stats.progressive_passes_per_90 = 12.0
        mock_stats.key_passes_per_90 = 2.5
        mock_stats.goals_per_90 = 0.8
        mock_stats.assists_per_90 = 0.6
        mock_stats.shots_on_target_pct = 65.0

        # Test para diferentes posiciones
        positions_to_test = ["GK", "CB", "CMF", "CF"]

        for position in positions_to_test:
            zone_score = controller._calculate_zone_metrics(mock_stats, position)

            # Verificar que devuelve un score válido
            assert isinstance(zone_score, float)
            assert 0 <= zone_score <= 100

    def test_calculate_position_specific_metrics(self):
        """Test del cálculo de métricas específicas por posición."""
        controller = MLMetricsController()

        # Mock de estadísticas
        mock_stats = MagicMock()
        mock_stats.aerial_duels_won_pct = 75.0
        mock_stats.long_passes_accuracy_pct = 80.0
        mock_stats.ball_recoveries_per_90 = 10.0
        mock_stats.assists_per_90 = 0.7
        mock_stats.goal_conversion_pct = 18.0
        mock_stats.touches_in_box_per_90 = 6.0

        # Test para diferentes posiciones
        positions = ["CB", "CMF", "CF"]

        for position in positions:
            specific_score = controller._calculate_position_specific_metrics(
                mock_stats, position
            )

            # Verificar que devuelve un score válido
            assert isinstance(specific_score, float)
            assert 0 <= specific_score <= 100

    def test_development_area_calculations(self):
        """Test de cálculos de áreas de desarrollo."""
        controller = MLMetricsController()

        # Mock de estadísticas con valores conocidos
        mock_stats = MagicMock()
        mock_stats.successful_dribbles_pct = 70.0
        mock_stats.accurate_passes_pct = 85.0
        mock_stats.first_touch_success_rate = None  # Test con valor None
        mock_stats.progressive_passes_per_90 = 10.0
        mock_stats.key_passes_per_90 = 3.0
        mock_stats.duels_won_pct = 65.0
        mock_stats.accelerations_per_90 = 20.0
        mock_stats.yellow_cards = 2
        mock_stats.matches_played = 25
        mock_stats.minutes_played = 2000

        # Test áreas individuales
        technical = controller._calculate_technical_proficiency(mock_stats)
        tactical = controller._calculate_tactical_intelligence(mock_stats)
        physical = controller._calculate_physical_performance(mock_stats)
        consistency = controller._calculate_consistency_index(mock_stats)

        # Verificar que todos devuelven scores válidos
        for score in [technical, tactical, physical, consistency]:
            assert isinstance(score, float)
            assert 0 <= score <= 100

        # Con buenas estadísticas, technical debería ser bueno
        assert technical > 60  # Promedio de 70% y 85%

        # Con pocas tarjetas, consistency debería ser alta
        assert consistency > 70

    @patch("controllers.ml.ml_metrics_controller.get_db_session")
    def test_get_league_rankings(self, mock_get_db_session):
        """Test del método get_league_rankings."""
        controller = MLMetricsController()

        # Mock session y datos
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session

        # Mock resultado de query
        mock_ml_metrics = MagicMock()
        mock_ml_metrics.player_id = 1
        mock_ml_metrics.pdi_overall = 85.0
        mock_ml_metrics.position_analyzed = "CMF"

        mock_player = MagicMock()
        mock_player.user.name = "Test Player"

        query_chain = (
            mock_session.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value
        )
        query_chain.all.return_value = [(mock_ml_metrics, mock_player)]

        rankings = controller.get_league_rankings(season="2024-25", limit=10)

        # Verificar resultado
        assert len(rankings) == 1
        assert rankings[0]["player_id"] == 1
        assert rankings[0]["player_name"] == "Test Player"
        assert rankings[0]["pdi_overall"] == 85.0
        assert rankings[0]["position"] == "CMF"
        assert rankings[0]["league_rank"] == 1

    @patch("controllers.ml.ml_metrics_controller.get_db_session")
    def test_get_position_averages(self, mock_get_db_session):
        """Test del método get_position_averages."""
        controller = MLMetricsController()

        # Mock session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session

        # Mock métricas para posición
        mock_metrics = []
        for i in range(3):
            mock_metric = MagicMock()
            mock_metric.pdi_overall = 70.0 + i * 5  # 70, 75, 80
            mock_metric.technical_proficiency = 80.0 + i * 2  # 80, 82, 84
            mock_metric.tactical_intelligence = 75.0 + i * 1  # 75, 76, 77
            mock_metric.physical_performance = 85.0 + i * 1  # 85, 86, 87
            mock_metric.consistency_index = 60.0 + i * 5  # 60, 65, 70
            mock_metrics.append(mock_metric)

        mock_session.query.return_value.filter_by.return_value.all.return_value = (
            mock_metrics
        )

        averages = controller.get_position_averages("CMF", "2024-25")

        # Verificar cálculos
        assert averages["count"] == 3
        assert averages["pdi_overall_avg"] == 75.0  # (70+75+80)/3
        assert averages["technical_avg"] == 82.0  # (80+82+84)/3
        assert averages["tactical_avg"] == 76.0  # (75+76+77)/3
        assert averages["physical_avg"] == 86.0  # (85+86+87)/3
        assert averages["consistency_avg"] == 65.0  # (60+65+70)/3

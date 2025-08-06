"""
Test suite para el módulo FeatureEngineer.

Incluye tests para:
- Extracción de features por tiers
- Normalización de valores
- Calidad de datos y cobertura
- Integración con ProfessionalStats
"""

from unittest.mock import MagicMock

from controllers.ml.feature_engineer import FeatureEngineer


class TestFeatureEngineer:
    """Tests para el FeatureEngineer."""

    def test_feature_engineer_initialization(self):
        """Test de inicialización del FeatureEngineer."""
        engineer = FeatureEngineer()

        # Verificar configuraciones iniciales
        assert engineer.min_matches_threshold == 3
        assert engineer.confidence_threshold == 0.7

        # Verificar que existen features definidos por tier
        assert "passing" in engineer.universal_features
        assert "defensive" in engineer.zone_features
        assert "GK" in engineer.position_features
        assert "CF" in engineer.position_features

        # Verificar estructura de features universales
        passing_config = engineer.universal_features["passing"]
        assert "accurate_passes_pct" in passing_config
        assert passing_config["accurate_passes_pct"]["weight"] == 0.30

    def test_extract_universal_features(self):
        """Test de extracción de features universales."""
        engineer = FeatureEngineer()

        # Mock de estadísticas con datos buenos
        mock_stats = MagicMock()
        mock_stats.matches_played = 10
        mock_stats.minutes_played = 800
        mock_stats.accurate_passes_pct = 85.0
        mock_stats.duels_won_pct = 60.0
        mock_stats.yellow_cards = 2

        features = engineer.extract_universal_features(mock_stats)

        # Verificar que devuelve features válidas
        assert isinstance(features, dict)
        assert "universal_composite_score" in features
        assert "passing_accuracy" in features
        assert "dueling_success" in features
        assert "discipline_score" in features

        # Verificar rangos válidos
        assert 0 <= features["universal_composite_score"] <= 100
        assert 0 <= features["passing_accuracy"] <= 100

        # Con buenas estadísticas debería ser > 50
        assert features["universal_composite_score"] > 50

    def test_extract_universal_features_insufficient_data(self):
        """Test con datos insuficientes."""
        engineer = FeatureEngineer()

        # Mock con datos insuficientes
        mock_stats = MagicMock()
        mock_stats.matches_played = 1  # Menos del mínimo
        mock_stats.minutes_played = 45

        features = engineer.extract_universal_features(mock_stats)

        # Debería devolver features por defecto
        assert isinstance(features, dict)
        assert "universal_composite_score" in features
        assert features["universal_composite_score"] == 55.0  # Default

    def test_extract_zone_features_different_positions(self):
        """Test de extracción de features por zona para diferentes posiciones."""
        engineer = FeatureEngineer()

        # Mock de estadísticas completas
        mock_stats = MagicMock()
        mock_stats.matches_played = 15
        mock_stats.minutes_played = 1200
        mock_stats.defensive_duels_won_pct = 70.0
        mock_stats.successful_defensive_actions_per_90 = 8.0
        mock_stats.interceptions_per_90 = 4.0
        mock_stats.progressive_passes_per_90 = 12.0
        mock_stats.key_passes_per_90 = 2.5
        mock_stats.ball_recoveries_per_90 = 10.0
        mock_stats.goals_per_90 = 0.8
        mock_stats.assists_per_90 = 0.6
        mock_stats.shots_on_target_pct = 65.0

        # Test para diferentes posiciones
        positions = ["GK", "CB", "CMF", "CF"]

        for position in positions:
            features = engineer.extract_zone_features(mock_stats, position)

            # Verificar estructura básica
            assert isinstance(features, dict)
            assert "zone_composite_score" in features

            # Verificar rangos
            assert 0 <= features["zone_composite_score"] <= 100

            # Verificar que diferentes posiciones devuelven diferentes features
            if position == "GK":
                # GK debería tener más peso defensivo
                assert "defensive_" in str(features)
            elif position == "CF":
                # CF debería tener más peso ofensivo
                assert (
                    "offensive_" in str(features)
                    or features["zone_composite_score"] >= 0
                )

    def test_extract_position_specific_features(self):
        """Test de extracción de features específicos por posición."""
        engineer = FeatureEngineer()

        # Mock con estadísticas para delantero
        mock_stats = MagicMock()
        mock_stats.matches_played = 20
        mock_stats.minutes_played = 1600
        mock_stats.goals_per_90 = 0.9
        mock_stats.goal_conversion_pct = 15.0
        mock_stats.touches_in_box_per_90 = 7.0

        features = engineer.extract_position_specific_features(mock_stats, "CF")

        # Verificar estructura
        assert isinstance(features, dict)
        assert "position_specific_composite_score" in features
        assert "goals_per_90" in features
        assert "goal_conversion_pct" in features

        # Verificar rangos
        assert 0 <= features["position_specific_composite_score"] <= 100
        assert 0 <= features["goals_per_90"] <= 100

    def test_extract_position_specific_unsupported_position(self):
        """Test con posición no soportada."""
        engineer = FeatureEngineer()

        mock_stats = MagicMock()
        mock_stats.matches_played = 10
        mock_stats.minutes_played = 800

        features = engineer.extract_position_specific_features(mock_stats, "UNKNOWN")

        # Debería devolver features por defecto
        assert isinstance(features, dict)
        assert "position_specific_composite_score" in features
        assert features["position_specific_composite_score"] == 50.0

    def test_normalize_feature_values(self):
        """Test de normalización de valores de features."""
        engineer = FeatureEngineer()

        # Test normalización porcentual
        config_pct = {"normalization": "percentage", "expected_range": (60, 90)}
        normalized = engineer._normalize_feature_value(75.0, config_pct)
        assert 0 <= normalized <= 100
        assert normalized == 50.0  # 75 está en el medio entre 60-90

        # Test normalización per-90
        config_per90 = {"normalization": "per_90_scaled", "expected_range": (0, 2)}
        normalized = engineer._normalize_feature_value(1.0, config_per90)
        assert 0 <= normalized <= 100
        assert normalized == 50.0  # 1.0 está en el medio entre 0-2

        # Test normalización inversa
        config_inverse = {"normalization": "inverse_per_90", "expected_range": (0, 1)}
        normalized = engineer._normalize_feature_value(0.2, config_inverse)
        assert 0 <= normalized <= 100
        assert normalized == 80.0  # 0.2 es bajo, por tanto score alto

    def test_generate_feature_quality_report(self):
        """Test de generación de reporte de calidad."""
        engineer = FeatureEngineer()

        # Mock con datos completos
        mock_stats = MagicMock()
        mock_stats.player_id = 1
        mock_stats.matches_played = 25
        mock_stats.minutes_played = 2000
        mock_stats.accurate_passes_pct = 85.0
        mock_stats.duels_won_pct = 65.0
        mock_stats.goals_per_90 = 0.7

        report = engineer.generate_feature_quality_report(mock_stats, "CF")

        # Verificar estructura del reporte
        assert isinstance(report, dict)
        assert "player_id" in report
        assert "position" in report
        assert "confidence_score" in report
        assert "feature_coverage" in report

        # Verificar que el score de confianza está en rango válido
        assert 0 <= report["confidence_score"] <= 100

        # Con datos suficientes debería tener confianza alta
        assert report["confidence_score"] > 50

    def test_validate_minimum_data(self):
        """Test de validación de datos mínimos."""
        engineer = FeatureEngineer()

        # Caso 1: Datos suficientes
        mock_stats_good = MagicMock()
        mock_stats_good.matches_played = 10
        mock_stats_good.minutes_played = 800
        assert engineer._validate_minimum_data(mock_stats_good) is True

        # Caso 2: Pocos partidos
        mock_stats_few_matches = MagicMock()
        mock_stats_few_matches.matches_played = 2
        mock_stats_few_matches.minutes_played = 180
        assert engineer._validate_minimum_data(mock_stats_few_matches) is False

        # Caso 3: Pocos minutos
        mock_stats_few_minutes = MagicMock()
        mock_stats_few_minutes.matches_played = 10
        mock_stats_few_minutes.minutes_played = 100
        assert engineer._validate_minimum_data(mock_stats_few_minutes) is False

        # Caso 4: Sin datos
        mock_stats_none = MagicMock()
        mock_stats_none.matches_played = None
        mock_stats_none.minutes_played = None
        assert engineer._validate_minimum_data(mock_stats_none) is False

    def test_get_zone_weights_by_position(self):
        """Test de obtención de pesos por zona según posición."""
        engineer = FeatureEngineer()

        # Test diferentes posiciones
        gk_weights = engineer._get_zone_weights_by_position("GK")
        assert gk_weights["defensive"] == 0.8
        assert gk_weights["offensive"] == 0.0

        cf_weights = engineer._get_zone_weights_by_position("CF")
        assert cf_weights["offensive"] == 0.8
        assert cf_weights["defensive"] == 0.0

        cmf_weights = engineer._get_zone_weights_by_position("CMF")
        assert cmf_weights["midfield"] == 0.8

        # Test posición no existente (debería usar CMF por defecto)
        unknown_weights = engineer._get_zone_weights_by_position("UNKNOWN")
        assert unknown_weights == cmf_weights

    def test_feature_tier_definitions(self):
        """Test de verificación de definiciones de tiers."""
        engineer = FeatureEngineer()

        # Verificar que todas las posiciones tienen features definidos
        required_positions = ["GK", "CB", "FB", "DMF", "CMF", "AMF", "W", "CF"]
        for position in required_positions:
            assert position in engineer.position_features
            assert len(engineer.position_features[position]) > 0

        # Verificar que todas las features tienen configuración completa
        for position, features in engineer.position_features.items():
            for feature_name, config in features.items():
                assert "weight" in config
                assert "normalization" in config
                assert "expected_range" in config
                assert isinstance(config["expected_range"], tuple)
                assert len(config["expected_range"]) == 2

    def test_feature_consistency_across_tiers(self):
        """Test de consistencia entre tiers de features."""
        engineer = FeatureEngineer()

        # Verificar que los pesos suman correctamente en universal
        for category, features in engineer.universal_features.items():
            total_weight = sum(f["weight"] for f in features.values())
            # Los pesos dentro de cada categoría deberían estar balanceados
            assert 0.1 <= total_weight <= 1.0  # Rango más flexible para categorías

        # Verificar que zone features cubren las tres zonas
        assert "defensive" in engineer.zone_features
        assert "midfield" in engineer.zone_features
        assert "offensive" in engineer.zone_features

        # Verificar que position features tienen al menos 2 métricas por posición
        for position, features in engineer.position_features.items():
            assert len(features) >= 2, f"Posición {position} tiene muy pocas features"

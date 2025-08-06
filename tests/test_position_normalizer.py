"""
Test suite para el módulo PositionNormalizer.

Incluye tests para:
- Normalización de métricas por posición
- Cálculo de percentiles
- Rankings posicionales
- Benchmarks y comparaciones justas
"""

from unittest.mock import MagicMock, patch

from controllers.ml.position_normalizer import PositionNormalizer


class TestPositionNormalizer:
    """Tests para el PositionNormalizer."""

    def test_position_normalizer_initialization(self):
        """Test de inicialización del PositionNormalizer."""
        normalizer = PositionNormalizer()

        # Verificar configuraciones iniciales
        assert normalizer.min_sample_size == 10
        assert normalizer.percentile_windows == [5, 10, 25, 50, 75, 90, 95]
        assert normalizer.seasons_for_benchmark == ["2023-24", "2024-25"]

        # Verificar inicialización de cache
        assert isinstance(normalizer._position_benchmarks_cache, dict)
        assert isinstance(normalizer._cache_timestamp, dict)

    def test_normalize_player_metrics_with_benchmarks(self):
        """Test de normalización con benchmarks disponibles."""
        normalizer = PositionNormalizer()

        # Mock benchmarks
        mock_benchmarks = {
            "pdi_overall": {
                "mean": 65.0,
                "std": 15.0,
                "percentiles": {
                    25: 55.0,
                    50: 65.0,
                    75: 75.0,
                    90: 85.0,
                    95: 90.0,
                },
            },
            "technical_proficiency": {
                "mean": 70.0,
                "std": 12.0,
                "percentiles": {
                    25: 60.0,
                    50: 70.0,
                    75: 80.0,
                    90: 85.0,
                    95: 90.0,
                },
            },
            "_meta": {"sample_size": 50, "last_updated": "2024-01-01T00:00:00"},
        }

        # Mock método _get_position_benchmarks
        with patch.object(
            normalizer, "_get_position_benchmarks", return_value=mock_benchmarks
        ):
            player_metrics = {
                "pdi_overall": 75.0,  # Percentil 75 aprox
                "technical_proficiency": 80.0,  # Percentil 75 aprox
                "unknown_metric": 50.0,  # Sin benchmark
            }

            normalized = normalizer.normalize_player_metrics(
                player_metrics, "CMF", "2024-25"
            )

            # Verificar estructura de resultado
            assert isinstance(normalized, dict)
            assert "pdi_overall_normalized" in normalized
            assert "pdi_overall_percentile" in normalized
            assert "technical_proficiency_normalized" in normalized
            assert "technical_proficiency_percentile" in normalized

            # Verificar que métricas sin benchmark mantienen valor original
            assert "unknown_metric_normalized" in normalized
            assert normalized["unknown_metric_normalized"] == 50.0
            assert normalized["unknown_metric_percentile"] == 50.0

            # Verificar rangos válidos
            for key, value in normalized.items():
                if isinstance(value, (int, float)):
                    assert 0 <= value <= 100

    def test_normalize_player_metrics_without_benchmarks(self):
        """Test de normalización sin benchmarks disponibles."""
        normalizer = PositionNormalizer()

        # Mock sin benchmarks
        with patch.object(normalizer, "_get_position_benchmarks", return_value={}):
            player_metrics = {
                "pdi_overall": 75.0,
                "technical_proficiency": 80.0,
            }

            normalized = normalizer.normalize_player_metrics(
                player_metrics, "CF", "2024-25"
            )

            # Debería aplicar normalización por defecto
            assert "pdi_overall_normalized" in normalized
            assert normalized["pdi_overall_normalized"] == 75.0  # Sin transformación
            assert normalized["pdi_overall_percentile"] == 50.0  # Percentil neutral

    def test_calculate_percentile(self):
        """Test de cálculo de percentiles."""
        normalizer = PositionNormalizer()

        benchmark_data = {
            "percentiles": {
                25: 50.0,
                50: 65.0,
                75: 80.0,
                90: 90.0,
                95: 95.0,
            }
        }

        # Test valores en percentiles exactos
        assert normalizer._calculate_percentile(50.0, benchmark_data) == 25
        assert normalizer._calculate_percentile(65.0, benchmark_data) == 50
        assert normalizer._calculate_percentile(80.0, benchmark_data) == 75

        # Test interpolación entre percentiles
        percentile_72_5 = normalizer._calculate_percentile(72.5, benchmark_data)
        assert 50 < percentile_72_5 < 75  # Debería estar entre p50 y p75

        # Test valores extremos
        assert (
            normalizer._calculate_percentile(30.0, benchmark_data) == 25
        )  # Por debajo
        assert (
            normalizer._calculate_percentile(100.0, benchmark_data) == 95
        )  # Por encima

        # Test sin datos
        empty_benchmark = {"percentiles": {}}
        assert normalizer._calculate_percentile(75.0, empty_benchmark) == 50.0

    def test_percentile_to_normalized_score(self):
        """Test de conversión de percentil a score normalizado."""
        normalizer = PositionNormalizer()

        # Test métrica porcentual
        pct_score = normalizer._percentile_to_normalized_score(
            80.0, "accurate_passes_pct"
        )
        assert pct_score >= 80.0  # Debería tener boost
        assert pct_score <= 100.0

        # Test métrica de consistencia (curva logarítmica)
        consistency_score = normalizer._percentile_to_normalized_score(
            80.0, "consistency_index"
        )
        assert 0 <= consistency_score <= 100

        # Test métricas ofensivas (curva exponencial)
        goals_score = normalizer._percentile_to_normalized_score(92.0, "goals_per_90")
        assert goals_score >= 85.0  # Top 10% debería tener boost (ajustado)

        # Test métrica estándar
        standard_score = normalizer._percentile_to_normalized_score(
            70.0, "standard_metric"
        )
        assert standard_score >= 70.0
        assert standard_score <= 77.0  # Ligero boost si <80

    @patch("controllers.ml.position_normalizer.get_db_session")
    def test_calculate_position_rankings(self, mock_get_db_session):
        """Test de cálculo de rankings por posición."""
        normalizer = PositionNormalizer()

        # Mock session y datos
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session

        # Mock métricas de jugadores
        mock_metrics = []
        for i in range(3):
            mock_metric = MagicMock()
            mock_metric.player_id = i + 1
            mock_metric.pdi_overall = 80.0 - i * 5  # 80, 75, 70
            mock_metric.pdi_universal = 75.0 + i * 2
            mock_metric.pdi_zone = 70.0 + i
            mock_metric.pdi_position_specific = 85.0 - i * 3
            mock_metric.technical_proficiency = 80.0 + i
            mock_metric.tactical_intelligence = 75.0 + i * 2
            mock_metric.physical_performance = 85.0 - i
            mock_metric.consistency_index = 70.0 + i * 3
            mock_metrics.append(mock_metric)

        mock_session.query.return_value.filter_by.return_value.filter.return_value.all.return_value = (
            mock_metrics
        )

        # Mock normalización (simplificada)
        def mock_normalize(metrics, position, season):
            return {
                "pdi_overall_normalized": metrics["pdi_overall"] * 1.1,
                "pdi_overall_percentile": min(95, metrics["pdi_overall"]),
            }

        with patch.object(
            normalizer, "normalize_player_metrics", side_effect=mock_normalize
        ):
            rankings = normalizer.calculate_position_rankings("CMF", "2024-25", 10)

            # Verificar resultado
            assert len(rankings) == 3
            assert rankings[0]["player_id"] == 1  # Mejor PDI
            assert rankings[0]["position_rank"] == 1
            assert rankings[1]["position_rank"] == 2
            assert rankings[2]["position_rank"] == 3

            # Verificar que están ordenados por PDI normalizado
            assert rankings[0]["normalized_pdi"] > rankings[1]["normalized_pdi"]
            assert rankings[1]["normalized_pdi"] > rankings[2]["normalized_pdi"]

    @patch("controllers.ml.position_normalizer.get_db_session")
    def test_calculate_position_benchmarks(self, mock_get_db_session):
        """Test de cálculo de benchmarks posicionales."""
        normalizer = PositionNormalizer()

        # Mock session
        mock_session = MagicMock()

        # Mock datos de métricas
        mock_metrics = []
        for i in range(15):  # Suficientes para benchmark
            mock_metric = MagicMock()
            mock_metric.pdi_overall = 60.0 + i * 2  # Range 60-88
            mock_metric.technical_proficiency = 65.0 + i * 1.5
            mock_metric.tactical_intelligence = None if i == 0 else 70.0 + i
            mock_metrics.append(mock_metric)

        mock_session.query.return_value.filter_by.return_value.filter.return_value.all.return_value = (
            mock_metrics
        )

        benchmarks = normalizer._calculate_position_benchmarks(
            mock_session, "CMF", ["2024-25"]
        )

        # Verificar estructura
        assert isinstance(benchmarks, dict)
        assert "_meta" in benchmarks
        assert benchmarks["_meta"]["sample_size"] == 15

        # Verificar que se procesan las métricas con datos
        assert "pdi_overall" in benchmarks
        assert "technical_proficiency" in benchmarks

        # Verificar estructura de benchmark individual
        pdi_benchmark = benchmarks["pdi_overall"]
        assert "mean" in pdi_benchmark
        assert "std" in pdi_benchmark
        assert "percentiles" in pdi_benchmark
        assert "sample_count" in pdi_benchmark

        # Verificar percentiles
        percentiles = pdi_benchmark["percentiles"]
        assert 50 in percentiles  # Mediana
        assert 25 in percentiles
        assert 75 in percentiles

    def test_calculate_metric_benchmarks(self):
        """Test de cálculo de estadísticas para una métrica."""
        normalizer = PositionNormalizer()

        values = [50.0, 60.0, 70.0, 80.0, 90.0, 85.0, 75.0, 65.0, 55.0, 72.0]

        benchmark = normalizer._calculate_metric_benchmarks(values)

        # Verificar estructura
        assert "mean" in benchmark
        assert "std" in benchmark
        assert "median" in benchmark
        assert "percentiles" in benchmark
        assert "sample_count" in benchmark
        assert "min" in benchmark
        assert "max" in benchmark

        # Verificar valores razonables
        assert benchmark["sample_count"] == 10
        assert 50.0 <= benchmark["mean"] <= 90.0
        assert benchmark["min"] == 50.0
        assert benchmark["max"] == 90.0

        # Verificar percentiles ordenados
        percentiles = benchmark["percentiles"]
        assert percentiles[25] <= percentiles[50]
        assert percentiles[50] <= percentiles[75]
        assert percentiles[75] <= percentiles[90]

    def test_get_position_specific_weights(self):
        """Test de obtención de pesos específicos por posición."""
        normalizer = PositionNormalizer()

        # Test diferentes posiciones
        gk_weights = normalizer._get_position_specific_weights("GK")
        assert "technical_proficiency" in gk_weights
        assert "consistency_index" in gk_weights
        assert sum(gk_weights.values()) == 1.0  # Deben sumar 1.0

        cf_weights = normalizer._get_position_specific_weights("CF")
        assert sum(cf_weights.values()) == 1.0

        # Test posición no existente (debería usar CMF por defecto)
        unknown_weights = normalizer._get_position_specific_weights("UNKNOWN")
        cmf_weights = normalizer._get_position_specific_weights("CMF")
        assert unknown_weights == cmf_weights

    def test_apply_default_normalization(self):
        """Test de normalización por defecto."""
        normalizer = PositionNormalizer()

        player_metrics = {
            "pdi_overall": 75.0,
            "technical_proficiency": 80.0,
            "tactical_intelligence": 70.0,
        }

        normalized = normalizer._apply_default_normalization(player_metrics)

        # Verificar que mantiene valores originales
        assert normalized["pdi_overall_normalized"] == 75.0
        assert normalized["technical_proficiency_normalized"] == 80.0
        assert normalized["tactical_intelligence_normalized"] == 70.0

        # Verificar percentiles neutrales
        assert normalized["pdi_overall_percentile"] == 50.0
        assert normalized["technical_proficiency_percentile"] == 50.0
        assert normalized["tactical_intelligence_percentile"] == 50.0

    @patch("controllers.ml.position_normalizer.get_db_session")
    def test_update_position_benchmarks(self, mock_get_db_session):
        """Test de actualización de benchmarks."""
        normalizer = PositionNormalizer()

        # Mock session y positions con datos
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session

        mock_session.query.return_value.filter.return_value.filter.return_value.distinct.return_value.all.return_value = [
            ("CMF",),
            ("CF",),
            ("CB",),
        ]

        # Mock _calculate_position_benchmarks para devolver contador
        def mock_calc_benchmarks(session, position, seasons):
            return 15 if position == "CMF" else 10

        with patch.object(
            normalizer,
            "_calculate_position_benchmarks",
            side_effect=mock_calc_benchmarks,
        ):
            updated = normalizer.update_position_benchmarks(["2024-25"])

            # Verificar resultado
            assert isinstance(updated, dict)
            assert "CMF" in updated
            assert "CF" in updated
            assert "CB" in updated
            assert updated["CMF"] == 15
            assert updated["CF"] == 10

    def test_generate_position_benchmark_report(self):
        """Test de generación de reporte de benchmarks."""
        normalizer = PositionNormalizer()

        mock_benchmarks = {
            "pdi_overall": {
                "mean": 65.0,
                "std": 15.0,
                "percentiles": {25: 55.0, 50: 65.0, 75: 75.0, 90: 85.0, 95: 90.0},
                "sample_count": 20,
            },
            "_meta": {"sample_size": 20, "last_updated": "2024-01-01T00:00:00"},
        }

        with patch.object(
            normalizer, "_get_position_benchmarks", return_value=mock_benchmarks
        ):
            report = normalizer.generate_position_benchmark_report("CMF", "2024-25")

            # Verificar estructura del reporte
            assert "position" in report
            assert "season" in report
            assert "sample_size" in report
            assert "benchmarks" in report

            assert report["position"] == "CMF"
            assert report["season"] == "2024-25"
            assert report["sample_size"] == 20

            # Verificar benchmark procesado
            pdi_benchmark = report["benchmarks"]["pdi_overall"]
            assert "mean" in pdi_benchmark
            assert "median" in pdi_benchmark
            assert "p25" in pdi_benchmark
            assert "p75" in pdi_benchmark
            assert "sample_count" in pdi_benchmark

    def test_calculate_normalized_aggregates(self):
        """Test de cálculo de agregados normalizados."""
        normalizer = PositionNormalizer()

        normalized_metrics = {
            "pdi_universal_normalized": 80.0,
            "pdi_zone_normalized": 70.0,
            "pdi_position_specific_normalized": 75.0,
            "technical_proficiency_normalized": 85.0,
            "tactical_intelligence_normalized": 70.0,
            "physical_performance_normalized": 80.0,
            "consistency_index_normalized": 65.0,
        }

        aggregates = normalizer._calculate_normalized_aggregates(
            normalized_metrics, "CMF"
        )

        # Verificar que se calculan agregados
        assert "pdi_overall_normalized" in aggregates
        assert "development_score_normalized" in aggregates
        assert "position_weighted_score" in aggregates

        # Verificar rangos válidos
        for key, value in aggregates.items():
            assert 0 <= value <= 100

        # Verificar cálculo de PDI overall normalizado (promedio ponderado)
        expected_pdi = 80.0 * 0.40 + 70.0 * 0.35 + 75.0 * 0.25
        assert abs(aggregates["pdi_overall_normalized"] - expected_pdi) < 0.1

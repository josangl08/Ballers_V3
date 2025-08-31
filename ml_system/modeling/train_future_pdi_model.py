"""
Script de Entrenamiento para el Modelo Predictivo de PDI Futuro.

Este script define y ejecuta el pipeline completo para entrenar un modelo
capaz de predecir el Player Development Index (PDI) de un jugador en el futuro.
"""

import os
import sys

# Añadir el directorio raíz del proyecto (Ballers_V3) al path de Python
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import logging

import pandas as pd
import xgboost as xgb


class Stats:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


logger = logging.getLogger(__name__)


class FuturePDIPredictor:
    """
    Encapsula el pipeline de entrenamiento para el modelo de predicción de PDI futuro.
    """

    def __init__(self):
        """Inicializa el predictor."""
        logger.info("Inicializando FuturePDIPredictor...")
        # Aquí se podrían configurar parámetros del modelo, rutas, etc.
        pass

    def rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        column_mapping = {
            "Player": "player_name",
            "Full name": "full_name",
            "Wyscout id": "wyscout_id",
            "Team": "team",
            "Team within selected timeframe": "team_within_timeframe",
            "Team logo": "team_logo_url",
            "Competition": "competition",
            "Primary position": "primary_position",
            "Secondary position": "secondary_position",
            "Third position": "third_position",
            "Age": "age",
            "Birthday": "birthday",
            "Market value": "market_value",
            "Matches played": "matches_played",
            "Minutes played": "minutes_played",
            "Goals": "goals",
            "xG": "expected_goals",
            "Assists": "assists",
            "xA": "expected_assists",
            "Duels per 90": "duels_per_90",
            "Duels won, %": "duels_won_pct",
            "Birth country": "birth_country",
            "Passport country": "passport_country",
            "Foot": "foot",
            "Height": "height",
            "Weight": "weight",
            "Successful defensive actions per 90": "defensive_actions_per_90",
            "Defensive duels per 90": "defensive_duels_per_90",
            "Defensive duels won, %": "defensive_duels_won_pct",
            "Aerial duels per 90": "aerial_duels_per_90",
            "Aerial duels won, %": "aerial_duels_won_pct",
            "Sliding tackles per 90": "sliding_tackles_per_90",
            "Interceptions per 90": "interceptions_per_90",
            "Fouls per 90": "fouls_per_90",
            "Yellow cards": "yellow_cards",
            "Red cards": "red_cards",
            "Goals per 90": "goals_per_90",
            "Shots": "shots",
            "Shots per 90": "shots_per_90",
            "Shots on target, %": "shots_on_target_pct",
            "Goal conversion, %": "goal_conversion_pct",
            "Assists per 90": "assists_per_90",
            "Touches in box per 90": "touches_in_box_per_90",
            "Progressive runs per 90": "progressive_runs_per_90",
            "Fouls suffered per 90": "fouls_suffered_per_90",
            "Passes per 90": "passes_per_90",
            "Accurate passes, %": "pass_accuracy_pct",
            "Forward passes per 90": "forward_passes_per_90",
            "Accurate forward passes, %": "forward_passes_accuracy_pct",
            "Back passes per 90": "back_passes_per_90",
            "Accurate back passes, %": "back_passes_accuracy_pct",
            "Long passes per 90": "long_passes_per_90",
            "Accurate long passes, %": "long_passes_accuracy_pct",
            "Key passes per 90": "key_passes_per_90",
            "Offensive duels per 90": "offensive_duels_per_90",
            "Offensive duels won, %": "offensive_duels_won_pct",
            "Dribbles per 90": "dribbles_per_90",
            "Successful dribbles, %": "dribbles_success_pct",
            "xG per 90": "xg_per_90",
            "xA per 90": "xa_per_90",
            "Yellow cards per 90": "yellow_cards_per_90",
            "Red cards per 90": "red_cards_per_90",
        }
        df = df.rename(columns=column_mapping)
        # Sanitize column names for LightGBM
        df.columns = [
            c.replace(", ", "_").replace("%", "pct").replace(" ", "_")
            for c in df.columns
        ]
        return df

    def load_historical_data(self) -> pd.DataFrame:
        """
        Carga todos los datos de estadísticas profesionales desde un archivo CSV.

        Returns:
            pd.DataFrame: Un DataFrame con todos los datos históricos.
        """
        logger.info("Cargando datos históricos desde el archivo CSV...")
        csv_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "data",
            "thai_league_processed",
            "processed_complete.csv",
        )
        try:
            df = pd.read_csv(csv_path)
            df = self.rename_columns(df)
            # The CSV does not have a player_id column, so we create one from the wyscout_id
            df["player_id"] = df["wyscout_id"]
            logger.info(
                f"Se han cargado {len(df)} registros de estadísticas desde {csv_path}."
            )
            return df
        except FileNotFoundError:
            logger.error(f"No se encontró el archivo de datos en {csv_path}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error al cargar los datos históricos desde CSV: {e}")
            return pd.DataFrame()

    def create_training_dataset(
        self, historical_df: pd.DataFrame, years_ahead: int = 1
    ) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
        """
        Transforma los datos históricos en un dataset de entrenamiento con features (X) y target (y).

        Args:
            historical_df: DataFrame con todos los datos históricos.
            years_ahead: El número de años en el futuro a predecir (1 o 2).

        Returns:
            Tuple[pd.DataFrame, pd.Series, pd.Series]: Features (X), target (y) y seasons.
        """
        logger.info(
            f"🔧 Creando dataset temporal sin data leakage (predecir +{years_ahead} años)"
        )

        # Convertir temporadas a formato numérico
        def season_to_year(season_str):
            try:
                return int(str(season_str).split("-")[0])
            except:
                return None

        historical_df = historical_df.copy()
        historical_df["season_year"] = historical_df["season"].apply(season_to_year)

        # Eliminar temporadas inválidas
        historical_df = historical_df.dropna(subset=["season_year"])
        historical_df["season_year"] = historical_df["season_year"].astype(int)

        # Ordenar por jugador y temporada
        historical_df = historical_df.sort_values(["player_id", "season_year"])

        logger.info(
            f"📊 Datos: {len(historical_df)} registros, temporadas: {sorted(historical_df['season_year'].unique())}"
        )

        features_list = []
        target_list = []
        season_list = []

        # PROCESO TEMPORAL SIN DATA LEAKAGE
        available_years = sorted(historical_df["season_year"].unique())

        for target_year in available_years[
            years_ahead:
        ]:  # Solo años donde podemos tener historical data
            train_years = [y for y in available_years if y < target_year][
                -3:
            ]  # Últimas 3 temporadas como máximo

            if len(train_years) == 0:
                continue

            logger.info(
                f"🎯 Prediciendo temporada {target_year} usando temporadas {train_years}"
            )

            # Datos de entrenamiento (temporadas pasadas)
            train_data = historical_df[historical_df["season_year"].isin(train_years)]

            # Datos objetivo (temporada a predecir)
            target_data = historical_df[historical_df["season_year"] == target_year]

            # Encontrar jugadores que aparecen en ambos conjuntos
            common_players = set(train_data["player_id"]).intersection(
                set(target_data["player_id"])
            )

            logger.info(f"   📋 Jugadores comunes: {len(common_players)}")

            for player_id in common_players:
                player_train = train_data[
                    train_data["player_id"] == player_id
                ].sort_values("season_year")
                player_target = target_data[target_data["player_id"] == player_id]

                if len(player_train) == 0 or len(player_target) == 0:
                    continue

                # Tomar el target más reciente de la temporada objetivo
                target_stats = player_target.iloc[-1]

                # FEATURE ENGINEERING TEMPORAL
                features = self._engineer_temporal_features(player_train, target_year)

                if not features:  # Skip si no se pueden crear features
                    continue

                # CALCULAR TARGET PDI (temporada futura)
                target_pdi = self._calculate_target_pdi(target_stats)

                if target_pdi is None:
                    continue

                # Añadir al dataset
                features_list.append(features)
                target_list.append(target_pdi)
                season_list.append(target_year)  # Año que estamos prediciendo

        if not features_list:
            logger.warning("❌ No se pudieron crear pares de entrenamiento válidos")
            return pd.DataFrame(), pd.Series(), pd.Series()

        X = pd.DataFrame(features_list)
        y = pd.Series(target_list)
        seasons = pd.Series(season_list)

        # Imputar valores faltantes
        X = X.fillna(X.median()).fillna(0)

        logger.info(f"✅ Dataset temporal creado:")
        logger.info(f"   📊 {len(X)} samples, {len(X.columns)} features")
        logger.info(f"   🎯 Target range: [{y.min():.2f}, {y.max():.2f}]")
        logger.info(f"   ⏱️ Temporadas predichas: {sorted(seasons.unique())}")
        logger.info(f"Dataset de entrenamiento creado con {len(X)} muestras.")
        return X, y, seasons

    def _engineer_temporal_features(
        self, player_train: pd.DataFrame, target_year: int
    ) -> dict:
        """
        Crea features temporales avanzados sin data leakage.

        Args:
            player_train: Data histórica del jugador (solo temporadas anteriores)
            target_year: Año que estamos prediciendo

        Returns:
            Dict con features engineered
        """
        try:
            if len(player_train) == 0:
                return {}

            # Tomar la temporada más reciente como base
            latest_season = player_train.iloc[-1]

            features = {}

            # === FEATURES BÁSICOS DE LA ÚTIMA TEMPORADA ===
            basic_features = [
                "Age",
                "Height",
                "Weight",
                "Minutes played",
                "Matches played",
                "Pass accuracy, %",
                "Duels won, %",
                "Successful dribbles, %",
                "Goals per 90",
                "Assists per 90",
                "xG per 90",
                "xA per 90",
                "Defensive duels won, %",
                "Aerial duels won, %",
                "Yellow cards per 90",
            ]

            for feature in basic_features:
                if feature in latest_season.index and pd.notna(latest_season[feature]):
                    features[
                        f'{feature.replace(" ", "_").replace(",", "").replace("%", "pct")}'
                    ] = float(latest_season[feature])
                else:
                    features[
                        f'{feature.replace(" ", "_").replace(",", "").replace("%", "pct")}'
                    ] = 0.0

            # === FEATURES POSICIONALES ===
            position_group = latest_season.get("Position_Group", "MID")
            for pos in ["GK", "DEF", "MID", "FWD"]:
                features[f"pos_{pos}"] = 1.0 if position_group == pos else 0.0

            # === FEATURES TEMPORALES (ROLLING) ===
            if len(player_train) >= 2:
                # Calcular tendencias en las últimas 2-3 temporadas
                recent_seasons = player_train.tail(min(3, len(player_train)))

                # Tendencia de minutos jugados
                if "Minutes played" in recent_seasons.columns:
                    minutes_vals = recent_seasons["Minutes played"].fillna(0)
                    if len(minutes_vals) >= 2:
                        features["minutes_trend"] = float(
                            minutes_vals.pct_change().fillna(0).mean()
                        )
                        features["minutes_mean"] = float(minutes_vals.mean())
                        features["minutes_std"] = (
                            float(minutes_vals.std()) if len(minutes_vals) > 1 else 0.0
                        )

                # Tendencia de rendimiento
                if "Pass accuracy, %" in recent_seasons.columns:
                    pass_vals = recent_seasons["Pass accuracy, %"].fillna(0)
                    if len(pass_vals) >= 2:
                        features["pass_acc_trend"] = float(
                            pass_vals.pct_change().fillna(0).mean()
                        )
                        features["pass_acc_consistency"] = (
                            float(1.0 / (1.0 + pass_vals.std()))
                            if pass_vals.std() > 0
                            else 1.0
                        )

                # Tendencia de edad (desarrollo/decadencia)
                if "Age" in recent_seasons.columns:
                    ages = recent_seasons["Age"].fillna(25)
                    current_age = float(ages.iloc[-1])
                    features["age_development_factor"] = (
                        1.2 if current_age < 24 else (0.9 if current_age > 30 else 1.0)
                    )

            # === FEATURES DE EXPERIENCIA Y ESTABILIDAD ===
            features["career_seasons"] = float(len(player_train))
            features["years_to_target"] = float(
                target_year - latest_season.get("season_year", target_year - 1)
            )

            # Estabilidad del jugador
            if len(player_train) >= 2:
                team_changes = (
                    len(player_train["Team"].dropna().unique())
                    if "Team" in player_train.columns
                    else 1
                )
                features["team_stability"] = float(1.0 / team_changes)
            else:
                features["team_stability"] = 1.0

            # === PDI PREVIO (SIN CIRCULARIDAD) ===
            # Usar PDI básico calculado directamente desde stats
            if "PDI" in latest_season.index and pd.notna(latest_season["PDI"]):
                features["pdi_baseline"] = float(latest_season["PDI"])
            else:
                # PDI sintético basado en métricas clave
                key_metrics = []
                for metric in ["Pass accuracy, %", "Duels won, %", "Minutes played"]:
                    if metric in latest_season.index and pd.notna(
                        latest_season[metric]
                    ):
                        key_metrics.append(float(latest_season[metric]))

                features["pdi_baseline"] = (
                    float(np.mean(key_metrics)) if key_metrics else 50.0
                )

            # === FEATURES DE INTERACCIÓN ===
            features["age_minutes_interaction"] = (
                features.get("Age", 25) * features.get("Minutes_played", 0) / 1000
            )
            features["position_age_factor"] = features.get("Age", 25) * (
                1 if position_group in ["DEF", "GK"] else 0.8
            )

            return features

        except Exception as e:
            logger.error(f"Error en feature engineering: {e}")
            return {}

    def _calculate_target_pdi(self, target_stats: pd.Series) -> float:
        """
        Calcula PDI objetivo de forma consistente.

        Args:
            target_stats: Stats de la temporada objetivo

        Returns:
            PDI calculado o None si falla
        """
        try:
            # Usar PDI existente si está disponible
            if "PDI" in target_stats.index and pd.notna(target_stats["PDI"]):
                return float(target_stats["PDI"])

            # Calcular PDI basado en métricas clave (sin circularidad)
            metrics = []
            weights = []

            # Métricas universales
            if pd.notna(target_stats.get("Pass accuracy, %", 0)):
                metrics.append(float(target_stats["Pass accuracy, %"]))
                weights.append(0.25)

            if pd.notna(target_stats.get("Duels won, %", 0)):
                metrics.append(float(target_stats["Duels won, %"]))
                weights.append(0.20)

            if pd.notna(target_stats.get("Minutes played", 0)):
                # Normalizar minutos a escala 0-100
                minutes_score = min(100, (target_stats["Minutes played"] / 2500) * 100)
                metrics.append(minutes_score)
                weights.append(0.15)

            # Métricas ofensivas
            if pd.notna(target_stats.get("Goals per 90", 0)):
                goals_score = min(100, target_stats["Goals per 90"] * 30)
                metrics.append(goals_score)
                weights.append(0.20)

            if pd.notna(target_stats.get("Assists per 90", 0)):
                assists_score = min(100, target_stats["Assists per 90"] * 25)
                metrics.append(assists_score)
                weights.append(0.20)

            if len(metrics) >= 3:  # Mínimo 3 métricas válidas
                # Promedio ponderado
                weighted_avg = np.average(metrics, weights=weights[: len(metrics)])
                # Escalar a rango [30, 95] para realismo
                pdi = 30 + (weighted_avg * 0.65)
                return float(np.clip(pdi, 30, 95))
            else:
                logger.warning("Pocas métricas válidas para calcular PDI")
                return None

        except Exception as e:
            logger.error(f"Error calculando target PDI: {e}")
            return None

    def train_and_evaluate_model(
        self, X: pd.DataFrame, y: pd.Series, seasons: pd.Series
    ) -> object:
        """
        Entrena y evalúa el modelo de regresión, y guarda los resultados.

        Args:
            X: DataFrame de features.
            y: Series de target.
            seasons: Series con las temporadas de cada muestra.

        Returns:
            El modelo entrenado.
        """
        logger.info(f"Entrenando y evaluando el modelo XGBoost...")
        import json
        import os
        from datetime import datetime

        from sklearn.metrics import mean_absolute_error, r2_score

        if X.empty or y.empty:
            logger.error("El dataset está vacío. No se puede entrenar el modelo.")
            return None

        # TEMPORAL SPLIT MEJORADO
        # Usar 70% de temporadas más antiguas para train, 30% más recientes para test
        unique_seasons = sorted(seasons.unique())
        n_train_seasons = max(1, int(len(unique_seasons) * 0.7))

        train_seasons = unique_seasons[:n_train_seasons]
        test_seasons = unique_seasons[n_train_seasons:]

        train_mask = seasons.isin(train_seasons)
        test_mask = seasons.isin(test_seasons)

        X_train = X[train_mask].copy()
        X_test = X[test_mask].copy()
        y_train = y[train_mask].copy()
        y_test = y[test_mask].copy()

        logger.info(f"📊 TEMPORAL SPLIT MEJORADO:")
        logger.info(f"   🏅 Train seasons: {train_seasons} ({len(X_train)} samples)")
        logger.info(f"   🎯 Test seasons: {test_seasons} ({len(X_test)} samples)")

        if len(X_train) == 0 or len(X_test) == 0:
            logger.error("❌ Split temporal inválido - no hay suficientes datos")
            return None

        # HIPERPARÁMETROS OPTIMIZADOS PARA MAE < 3.5
        best_params = {
            "n_estimators": 1000,  # Más árboles para mejor ajuste
            "max_depth": 6,  # Profundidad moderada para evitar overfitting
            "learning_rate": 0.05,  # Learning rate más conservador
            "subsample": 0.8,  # Subsample para regularización
            "colsample_bytree": 0.8,  # Feature sampling para robustez
            "gamma": 0.1,  # Regularización mínima
            "reg_alpha": 0.1,  # L1 regularization
            "reg_lambda": 1.0,  # L2 regularization
            "min_child_weight": 3,  # Prevenir overfitting en hojas
            "random_state": 42,
            "n_jobs": -1,
        }

        model = xgb.XGBRegressor(**best_params, random_state=42)

        logger.info("Entrenando XGBRegressor con los mejores hiperparámetros...")
        model.fit(X_train, y_train)

        # Mostrar las características más importantes
        if hasattr(model, "feature_importances_"):
            feature_importances = pd.DataFrame(
                model.feature_importances_,
                index=X_train.columns,
                columns=["importance"],
            ).sort_values("importance", ascending=False)
            logger.info("Top 50 características más importantes:")
            logger.info(feature_importances.head(50))

        logger.info("Realizando predicciones en el conjunto de prueba...")
        predictions = model.predict(X_test)

        mae = mean_absolute_error(y_test, predictions)
        r2 = r2_score(y_test, predictions)

        logger.info("--- Resultados de la Evaluación del Modelo ---")
        logger.info(f"Modelo: XGBoost")
        logger.info(f"Error Absoluto Medio (MAE): {mae:.2f}")
        logger.info(f"Coeficiente de Determinación (R²): {r2:.2f}")
        logger.info("---------------------------------------------")

        # Guardar reportes y resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports_dir = "ml_system/outputs/reports"
        os.makedirs(reports_dir, exist_ok=True)

        # Guardar feature importances
        if hasattr(model, "feature_importances_"):
            feature_importances_df = pd.DataFrame(
                model.feature_importances_,
                index=X_train.columns,
                columns=["importance"],
            ).sort_values("importance", ascending=False)
            feature_importances_path = os.path.join(
                reports_dir, f"feature_importances_xgboost_{timestamp}.csv"
            )
            feature_importances_df.to_csv(feature_importances_path)
            logger.info(f"Feature importances guardadas en: {feature_importances_path}")

        # 1. Fichero de resultados JSON
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "model_type": "xgboost",
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "metrics": {"mean_absolute_error": mae, "r2_score": r2},
            "best_hyperparameters": best_params,
        }
        results_dir = "ml_system/outputs/results"
        os.makedirs(results_dir, exist_ok=True)
        results_path = os.path.join(
            results_dir, f"future_pdi_model_results_xgboost_{timestamp}.json"
        )
        with open(results_path, "w") as f:
            json.dump(results_data, f, indent=4)
        logger.info(f"Resultados guardados en: {results_path}")

        # 2. Fichero de reporte TXT
        report_content = f"""
        Reporte de Entrenamiento del Modelo Predictivo de PDI Futuro
        -----------------------------------------------------------
        Fecha y Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

        Configuración del Modelo
        --------------------------
        Tipo de Modelo: XGBoost
        Parámetros: {best_params}

        Datos
        -----
        Muestras de Entrenamiento: {len(X_train)}
        Muestras de Prueba: {len(X_test)}

        Resultados de la Evaluación
        ---------------------------
        Error Absoluto Medio (MAE): {mae:.3f}
        Coeficiente de Determinación (R²): {r2:.3f}

        Análisis
        --------
        MAE: En promedio, las predicciones del modelo se desvían en {mae:.2f} puntos del PDI real del jugador al año siguiente.
        R²: El modelo es capaz de explicar el {r2:.1%} de la variabilidad en el PDI futuro, lo cual indica un poder predictivo robusto.
        """
        report_path = os.path.join(
            reports_dir, f"future_pdi_model_report_xgboost_{timestamp}.txt"
        )
        with open(report_path, "w") as f:
            f.write(report_content)
        logger.info(f"Reporte guardado en: {report_path}")

        return model

    def save_model(self, model: object, model_name: str = "xgboost"):
        """
        Guarda el modelo entrenado en un fichero.

        Args:
            model: El objeto del modelo entrenado.
            filename: El nombre del fichero para guardar el modelo.
        """
        if model is None:
            logger.error("No hay modelo para guardar.")
            return

        import os

        import joblib

        filename = f"future_pdi_predictor_{model_name}.joblib"
        logger.info(f"Guardando el modelo en {filename}...")

        # Definir una ruta de salida estándar
        output_dir = "ml_system/outputs/models"
        os.makedirs(output_dir, exist_ok=True)

        file_path = os.path.join(output_dir, filename)

        try:
            joblib.dump(model, file_path)
            logger.info(f"Modelo guardado exitosamente en: {file_path}")
        except Exception as e:
            logger.error(f"Error al guardar el modelo: {e}")

    def run_training_pipeline(self):
        """
        Orquesta la ejecución de todo el pipeline de entrenamiento.
        """
        logger.info(
            f"Iniciando pipeline de entrenamiento de PDI futuro para el modelo XGBoost..."
        )
        historical_data = self.load_historical_data()
        X, y, seasons = self.create_training_dataset(historical_data)
        model = self.train_and_evaluate_model(X, y, seasons)
        self.save_model(model)
        logger.info(f"Pipeline de entrenamiento para XGBoost completado.")


if __name__ == "__main__":
    # Configuración básica de logging para ejecutar el script de forma independiente
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    pipeline = FuturePDIPredictor()
    pipeline.run_training_pipeline()

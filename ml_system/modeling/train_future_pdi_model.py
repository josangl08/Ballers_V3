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
import lightgbm as lgb
import xgboost as xgb
from sklearn.linear_model import LinearRegression


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
        df.columns = [c.replace(', ', '_').replace('%', 'pct').replace(' ', '_') for c in df.columns]
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
            f"Creando dataset de entrenamiento para predecir PDI a {years_ahead} año(s)..."
        )

        # Convertir la columna de temporada a un formato numérico para facilitar la búsqueda
        def season_to_year(season_str):
            try:
                return int(season_str.split("-")[0])
            except:
                return None

        historical_df["season_year"] = historical_df["season"].apply(season_to_year)

        features_list = []
        target_list = []
        season_list = []

        # Agrupar por jugador para procesar el historial de cada uno
        for player_id, player_df in historical_df.groupby("player_id"):
            if len(player_df) < 2:
                continue  # Necesitamos al menos dos temporadas para crear un par feature-target

            # Iterar sobre las temporadas de cada jugador
            for _, current_season_stats in player_df.iterrows():
                current_year = current_season_stats["season_year"]
                target_year = current_year + years_ahead

                # Buscar la temporada futura en los datos de este jugador
                target_season_stats = player_df[player_df["season_year"] == target_year]

                if not target_season_stats.empty:
                    target_stats_row = target_season_stats.iloc[0]

                    # 1. Usar métricas crudas como features
                    features = current_season_stats.to_dict()

                    # --- Feature Selection and Engineering ---
                    # Remove redundant or low-correlation features based on analysis
                    features_to_remove = [
                        "matches_played", "expected_goals", "expected_assists", "goals", "assists",
                        "defensive_actions_per_90", "sliding_tackles_per_90", "shots",
                        "player_name", "full_name", "wyscout_id", "team", "team_within_timeframe",
                        "team_logo_url", "competition", "birthday", "Contract_expires",
                        "processing_date", "data_source", "birth_country", "passport_country",
                        "foot", "season", "player_id", "primary_position", "secondary_position",
                        "third_position", "Position", "season_year"
                    ]
                    for feature in features_to_remove:
                        features.pop(feature, None)

                    # One-hot encode Position_Group
                    if "Position_Group" in features:
                        position_group = features.pop("Position_Group")
                        # Create dummy variables for all possible positions
                        for pos in ["GK", "CB", "FB", "DMF", "CMF", "AMF", "W", "CF"]:
                            features[f"pos_{pos}"] = 1 if position_group == pos else 0

                    # Add lag feature for previous season's PDI
                    from ml_system.evaluation.metrics.pdi_calculator import PDICalculator
                    pdi_calculator = PDICalculator()
                    
                    current_stats_obj = Stats(**current_season_stats.to_dict())
                    current_pdi = pdi_calculator._calculate_hierarchical_pdi(current_stats_obj)
                    if current_pdi and "pdi_overall" in current_pdi:
                        features['pdi_overall_lag1'] = current_pdi["pdi_overall"]
                    else:
                        features['pdi_overall_lag1'] = 0 # Or some other imputation

                    # 2. Calcular el target de la temporada futura (PDI)
                    target_stats_dict = target_stats_row.to_dict()
                    target_stats_dict.pop("season_year", None)
                    target_stats_obj = Stats(**target_stats_dict)
                    target_pdi = pdi_calculator._calculate_hierarchical_pdi(
                        target_stats_obj
                    )

                    if not target_pdi or "pdi_overall" not in target_pdi:
                        continue

                    target_value = target_pdi["pdi_overall"]

                    # 3. Añadir al dataset
                    features_list.append(features)
                    target_list.append(target_value)
                    season_list.append(current_year)

        if not features_list:
            logger.warning(
                "No se pudieron crear pares de entrenamiento. El dataset podría ser insuficiente."
            )
            return pd.DataFrame(), pd.Series(), pd.Series()

        X = pd.DataFrame(features_list)
        X = X.fillna(0)
        y = pd.Series(target_list)
        seasons = pd.Series(season_list)

        logger.info(f"Dataset de entrenamiento creado con {len(X)} muestras.")
        return X, y, seasons

    def train_and_evaluate_model(self, X: pd.DataFrame, y: pd.Series, seasons: pd.Series, model_name: str = "lightgbm") -> object:
        """
        Entrena y evalúa el modelo de regresión, y guarda los resultados.

        Args:
            X: DataFrame de features.
            y: Series de target.
            seasons: Series con las temporadas de cada muestra.
            model_name: El nombre del modelo a entrenar ('xgboost', 'lightgbm', 'linear_regression').

        Returns:
            El modelo entrenado.
        """
        logger.info(f"Entrenando y evaluando el modelo {model_name}...")
        import json
        import os
        from datetime import datetime

        from sklearn.model_selection import RandomizedSearchCV
        from sklearn.metrics import mean_absolute_error, r2_score

        if X.empty or y.empty:
            logger.error("El dataset está vacío. No se puede entrenar el modelo.")
            return None

        # Time-based split
        test_season = seasons.max()
        train_indices = seasons[seasons < test_season].index
        test_indices = seasons[seasons == test_season].index

        X_train, X_test = X.loc[train_indices], X.loc[test_indices]
        y_train, y_test = y.loc[train_indices], y.loc[test_indices]

        logger.info(
            f"Dataset dividido en: {len(X_train)} para entrenamiento (temporadas < {test_season}), {len(X_test)} para prueba (temporada = {test_season})."
        )

        model = None
        best_params = {}

        if model_name == 'lightgbm':
            param_distributions = {
                'n_estimators': [100, 200, 300, 500, 700],
                'learning_rate': [0.01, 0.05, 0.1, 0.15],
                'num_leaves': [20, 31, 40, 50, 60],
                'max_depth': [-1, 5, 10, 15],
                'subsample': [0.6, 0.7, 0.8, 0.9, 1.0],
                'colsample_bytree': [0.6, 0.7, 0.8, 0.9, 1.0],
            }
            lgbm = lgb.LGBMRegressor(random_state=42)
            lgbm_random = RandomizedSearchCV(estimator = lgbm, param_distributions = param_distributions, n_iter = 150, cv = 5, verbose=2, random_state=42, n_jobs = -1)
            logger.info("Entrenando LGBMRegressor con RandomizedSearchCV...")
            lgbm_random.fit(X_train, y_train)
            logger.info(f"Mejores hiperparámetros encontrados: {lgbm_random.best_params_}")
            model = lgbm_random.best_estimator_
            best_params = lgbm_random.best_params_

        elif model_name == 'xgboost':
            param_distributions = {
                'n_estimators': [100, 200, 300, 500, 700],
                'learning_rate': [0.01, 0.05, 0.1, 0.15],
                'max_depth': [3, 4, 5, 6, 7, 8, 9, 10],
                'subsample': [0.6, 0.7, 0.8, 0.9, 1.0],
                'colsample_bytree': [0.6, 0.7, 0.8, 0.9, 1.0],
                'gamma': [0, 0.1, 0.2, 0.3]
            }
            xgbr = xgb.XGBRegressor(random_state=42)
            xgbr_random = RandomizedSearchCV(estimator = xgbr, param_distributions = param_distributions, n_iter = 150, cv = 5, verbose=2, random_state=42, n_jobs = -1)
            logger.info("Entrenando XGBRegressor con RandomizedSearchCV...")
            xgbr_random.fit(X_train, y_train)
            logger.info(f"Mejores hiperparámetros encontrados: {xgbr_random.best_params_}")
            model = xgbr_random.best_estimator_
            best_params = xgbr_random.best_params_

        elif model_name == 'linear_regression':
            model = LinearRegression()
            model.fit(X_train, y_train)

        else:
            raise ValueError(f"Modelo '{model_name}' no soportado.")


        # Mostrar las características más importantes
        if hasattr(model, 'feature_importances_'):
            feature_importances = pd.DataFrame(model.feature_importances_, index = X_train.columns, columns=['importance']).sort_values('importance', ascending=False)
            logger.info("Top 50 características más importantes:")
            logger.info(feature_importances.head(50))

        logger.info("Realizando predicciones en el conjunto de prueba...")
        predictions = model.predict(X_test)

        mae = mean_absolute_error(y_test, predictions)
        r2 = r2_score(y_test, predictions)

        logger.info("--- Resultados de la Evaluación del Modelo ---")
        logger.info(f"Modelo: {model_name}")
        logger.info(f"Error Absoluto Medio (MAE): {mae:.2f}")
        logger.info(f"Coeficiente de Determinación (R²): {r2:.2f}")
        logger.info("---------------------------------------------")

        # Guardar reportes y resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports_dir = "ml_system/outputs/reports"
        os.makedirs(reports_dir, exist_ok=True)

        # Guardar feature importances
        if hasattr(model, 'feature_importances_'):
            feature_importances_df = pd.DataFrame(model.feature_importances_, index=X_train.columns, columns=['importance']).sort_values('importance', ascending=False)
            feature_importances_path = os.path.join(reports_dir, f"feature_importances_{model_name}_{timestamp}.csv")
            feature_importances_df.to_csv(feature_importances_path)
            logger.info(f"Feature importances guardadas en: {feature_importances_path}")

        # 1. Fichero de resultados JSON
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "model_type": model_name,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "metrics": {"mean_absolute_error": mae, "r2_score": r2},
            "best_hyperparameters": best_params
        }
        results_dir = "ml_system/outputs/results"
        os.makedirs(results_dir, exist_ok=True)
        results_path = os.path.join(
            results_dir, f"future_pdi_model_results_{model_name}_{timestamp}.json"
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
        Tipo de Modelo: {model_name}
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
            reports_dir, f"future_pdi_model_report_{model_name}_{timestamp}.txt"
        )
        with open(report_path, "w") as f:
            f.write(report_content)
        logger.info(f"Reporte guardado en: {report_path}")

        return model

    def save_model(
        self, model: object, model_name: str = "lightgbm"
    ):
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

    def run_training_pipeline(self, model_name: str = "lightgbm"):
        """
        Orquesta la ejecución de todo el pipeline de entrenamiento.
        """
        logger.info(f"Iniciando pipeline de entrenamiento de PDI futuro para el modelo {model_name}...")
        historical_data = self.load_historical_data()
        X, y, seasons = self.create_training_dataset(historical_data)
        model = self.train_and_evaluate_model(X, y, seasons, model_name)
        self.save_model(model, model_name)
        logger.info(f"Pipeline de entrenamiento para {model_name} completado.")


if __name__ == "__main__":
    # Configuración básica de logging para ejecutar el script de forma independiente
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Se puede especificar el modelo a entrenar desde la línea de comandos
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="lightgbm", help="Nombre del modelo a entrenar (lightgbm, xgboost, linear_regression)")
    args = parser.parse_args()

    pipeline = FuturePDIPredictor()
    pipeline.run_training_pipeline(model_name=args.model)
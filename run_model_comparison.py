
import os
import sys
import pandas as pd

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ml_system.modeling.train_future_pdi_model import FuturePDIPredictor

def run_model_comparison():
    """
    Runs the training pipeline for multiple models and compares their performance.
    """
    models_to_compare = ["lightgbm", "xgboost", "linear_regression"]
    results = []

    for model_name in models_to_compare:
        print(f"--- Training {model_name} ---")
        pipeline = FuturePDIPredictor()
        pipeline.run_training_pipeline(model_name=model_name)

    # --- Compare Results ---
    print("\n--- Model Comparison ---")
    results_dir = os.path.join(project_root, "ml_system", "outputs", "results")
    all_results = []

    for filename in os.listdir(results_dir):
        if filename.startswith("future_pdi_model_results") and filename.endswith(".json"):
            with open(os.path.join(results_dir, filename), 'r') as f:
                import json
                data = json.load(f)
                all_results.append({
                    "model": data["model_type"],
                    "mae": data["metrics"]["mean_absolute_error"],
                    "r2": data["metrics"]["r2_score"],
                    "timestamp": data["timestamp"]
                })

    if not all_results:
        print("No results found.")
        return

    # Create a DataFrame from the results and sort by R² score
    comparison_df = pd.DataFrame(all_results)
    comparison_df = comparison_df.sort_values(by="r2", ascending=False)

    print("Model Performance Comparison:")
    print(comparison_df)

    # Save the comparison to a CSV file
    comparison_path = os.path.join(results_dir, "model_comparison.csv")
    comparison_df.to_csv(comparison_path, index=False)
    print(f"\nComparison results saved to {comparison_path}")

if __name__ == "__main__":
    run_model_comparison()

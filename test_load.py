import os

import pandas as pd

print("Starting test_load.py")
csv_path = os.path.join(
    os.path.dirname(__file__), "data", "thai_league_processed", "processed_complete.csv"
)
print(f"Loading CSV from {csv_path}")
df = pd.read_csv(csv_path)
print("CSV loaded successfully")

print("Grouping by player_id...")
df.groupby("Wyscout id")
print("Groupby successful")

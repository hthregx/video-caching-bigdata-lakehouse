import pandas as pd
import numpy as np
from pathlib import Path

INPUT_PATH = Path("outputs/video_features.csv")
OUTPUT_PATH = Path("outputs")
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT_PATH)

def min_max_scale(series):
    min_value = series.min()
    max_value = series.max()
    if max_value == min_value:
        return series * 0
    return (series - min_value) / (max_value - min_value)

# Chuẩn hóa các feature về 0-1
df["views_score"] = min_max_scale(df["views_count"])
df["growth_score"] = min_max_scale(df["growth_rate"].clip(lower=0))
df["watch_ratio_score"] = min_max_scale(df["avg_watch_ratio"])
df["engagement_score"] = min_max_scale(df["engagement_count"])

# Tính hot_score
df["hot_score"] = (
    0.40 * df["views_score"]
    + 0.25 * df["growth_score"]
    + 0.20 * df["watch_ratio_score"]
    + 0.15 * df["engagement_score"]
)

# Phân loại video hot
df["predicted_hot"] = (df["hot_score"] >= 0.70).astype(int)
df["hot_label"] = np.where(df["predicted_hot"] == 1, "HOT", "NOT_HOT")

prediction_cols = [
    "video_id",
    "window_start",
    "window_end",
    "views_count",
    "unique_users",
    "avg_watch_ratio",
    "growth_rate",
    "engagement_count",
    "views_score",
    "growth_score",
    "watch_ratio_score",
    "engagement_score",
    "hot_score",
    "predicted_hot",
    "hot_label",
]

predictions = df[prediction_cols].sort_values("hot_score", ascending=False)

predictions.to_csv(OUTPUT_PATH / "hot_video_predictions.csv", index=False)

print("Saved:", OUTPUT_PATH / "hot_video_predictions.csv")
print(predictions.head(20))
import pandas as pd
import numpy as np
from pathlib import Path

INPUT_PATH = Path("data/sample/clean_video_logs_sample.csv")
OUTPUT_PATH = Path("outputs")
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT_PATH)
df["event_time"] = pd.to_datetime(df["event_time"])

# Chia log thành cửa sổ thời gian 30 phút
df["window_start"] = df["event_time"].dt.floor("30min")
df["window_end"] = df["window_start"] + pd.Timedelta(minutes=30)

features = (
    df.groupby(["video_id", "window_start", "window_end"])
    .agg(
        views_count=("video_id", "count"),
        unique_users=("user_id", "nunique"),
        avg_watch_time=("watch_time", "mean"),
        avg_watch_ratio=("watch_ratio", "mean"),
        like_count=("is_like", "sum"),
        share_count=("is_share", "sum"),
    )
    .reset_index()
)

features["engagement_count"] = features["like_count"] + features["share_count"]

# Tính growth_rate theo từng video qua các time window
features = features.sort_values(["video_id", "window_start"])
features["previous_views"] = features.groupby("video_id")["views_count"].shift(1).fillna(0)

features["growth_rate"] = np.where(
    features["previous_views"] > 0,
    (features["views_count"] - features["previous_views"]) / features["previous_views"],
    features["views_count"]
)

features["growth_rate"] = features["growth_rate"].replace([np.inf, -np.inf], 0).fillna(0)

features.to_csv(OUTPUT_PATH / "video_features.csv", index=False)

print("Saved:", OUTPUT_PATH / "video_features.csv")
print(features.head())
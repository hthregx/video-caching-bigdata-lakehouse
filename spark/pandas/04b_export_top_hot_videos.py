import pandas as pd
from pathlib import Path

INPUT_PATH = Path("outputs/hot_video_predictions.csv")
OUTPUT_PATH = Path("outputs")
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT_PATH)

top_hot = (
    df.sort_values("hot_score", ascending=False)
    .head(20)
    [
        [
            "video_id",
            "window_start",
            "window_end",
            "views_count",
            "unique_users",
            "avg_watch_ratio",
            "growth_rate",
            "engagement_count",
            "hot_score",
            "hot_label",
        ]
    ]
)

top_hot.to_csv(OUTPUT_PATH / "top_hot_videos.csv", index=False)

print("Saved outputs/top_hot_videos.csv")
print(top_hot)
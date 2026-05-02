import pandas as pd
import numpy as np
from pathlib import Path

np.random.seed(42)

output_path = Path("data/sample")
output_path.mkdir(parents=True, exist_ok=True)

n_rows = 100_000
n_users = 5000
n_videos = 1000

start_time = pd.Timestamp("2026-05-01 08:00:00")

df = pd.DataFrame({
    "event_time": [
        start_time + pd.Timedelta(seconds=int(x))
        for x in np.sort(np.random.randint(0, 6 * 60 * 60, size=n_rows))
    ],
    "user_id": np.random.randint(1, n_users + 1, size=n_rows),
    "video_id": np.random.randint(1, n_videos + 1, size=n_rows),
    "duration": np.random.randint(10, 180, size=n_rows),
})

df["watch_time"] = np.minimum(
    df["duration"],
    np.random.exponential(scale=40, size=n_rows)
).round(2)

df["watch_ratio"] = (df["watch_time"] / df["duration"]).clip(0, 1).round(4)

df["is_click"] = 1
df["is_like"] = (np.random.rand(n_rows) < (0.05 + 0.25 * df["watch_ratio"])).astype(int)
df["is_share"] = (np.random.rand(n_rows) < (0.01 + 0.08 * df["watch_ratio"])).astype(int)

# Tạo một số video có xu hướng hot giả lập để test logic prediction
hot_videos = np.random.choice(df["video_id"].unique(), size=30, replace=False)
hot_mask = (
    df["video_id"].isin(hot_videos)
    & (df["event_time"] >= start_time + pd.Timedelta(hours=3))
)

extra_rows = df[hot_mask].sample(min(20_000, hot_mask.sum()), replace=True, random_state=42)
extra_rows["event_time"] = extra_rows["event_time"] + pd.to_timedelta(
    np.random.randint(0, 60 * 60, size=len(extra_rows)), unit="s"
)

df = pd.concat([df, extra_rows], ignore_index=True)
df = df.sort_values("event_time")

df.to_csv(output_path / "clean_video_logs_sample.csv", index=False)

print("Created:", output_path / "clean_video_logs_sample.csv")
print("Rows:", len(df))
print(df.head())
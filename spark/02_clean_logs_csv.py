import pandas as pd
from pathlib import Path

INPUT_PATH = Path("data/sample/raw_video_logs.csv")
OUTPUT_PATH = Path("data/processed/clean_video_logs.csv")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

if not INPUT_PATH.exists():
    raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

df = pd.read_csv(INPUT_PATH)

# Chuẩn hóa tên cột
df.columns = [c.strip().lower() for c in df.columns]

# Đổi tên cột nếu cần
rename_map = {
    "item_id": "video_id",
    "videoid": "video_id",
    "userid": "user_id",
    "time": "event_time",
    "time_ms": "event_time",
    "play_time": "watch_time",
    "view_time": "watch_time",
}

for old_name, new_name in rename_map.items():
    if old_name in df.columns and new_name not in df.columns:
        df = df.rename(columns={old_name: new_name})

# Tạo cột mặc định nếu thiếu
if "is_click" not in df.columns:
    df["is_click"] = 1

if "is_like" not in df.columns:
    df["is_like"] = 0

if "is_share" not in df.columns:
    df["is_share"] = 0

required_cols = [
    "event_time",
    "user_id",
    "video_id",
    "watch_time",
    "duration",
    "is_click",
    "is_like",
    "is_share",
]

missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")

raw_count = len(df)

# Ép kiểu
df["event_time"] = pd.to_datetime(df["event_time"], errors="coerce")
df["user_id"] = df["user_id"].astype(str)
df["video_id"] = df["video_id"].astype(str)
df["watch_time"] = pd.to_numeric(df["watch_time"], errors="coerce")
df["duration"] = pd.to_numeric(df["duration"], errors="coerce")
df["is_click"] = pd.to_numeric(df["is_click"], errors="coerce").fillna(1).astype(int)
df["is_like"] = pd.to_numeric(df["is_like"], errors="coerce").fillna(0).astype(int)
df["is_share"] = pd.to_numeric(df["is_share"], errors="coerce").fillna(0).astype(int)

# Clean dữ liệu
df = df.dropna(subset=["event_time", "user_id", "video_id", "watch_time", "duration"])
df = df[df["duration"] > 0]
df = df[df["watch_time"] >= 0]

# Nếu watch_time > duration thì cắt về duration
df["watch_time"] = df[["watch_time", "duration"]].min(axis=1)

# Tính lại watch_ratio
df["watch_ratio"] = (df["watch_time"] / df["duration"]).clip(0, 1)

# Bỏ duplicate
dedup_cols = [
    "event_time",
    "user_id",
    "video_id",
    "watch_time",
    "duration",
    "watch_ratio",
    "is_click",
    "is_like",
    "is_share",
]

df = df.drop_duplicates(subset=dedup_cols)

clean_df = df[
    [
        "event_time",
        "user_id",
        "video_id",
        "watch_time",
        "duration",
        "watch_ratio",
        "is_click",
        "is_like",
        "is_share",
    ]
]

clean_df.to_csv(OUTPUT_PATH, index=False)

print("===== CLEANING SUMMARY =====")
print(f"Raw rows: {raw_count}")
print(f"Clean rows: {len(clean_df)}")
print(f"Removed rows: {raw_count - len(clean_df)}")
print(f"Saved clean logs to: {OUTPUT_PATH}")
print(clean_df.head())
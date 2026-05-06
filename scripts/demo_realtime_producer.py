import json
import time
import random
import pandas as pd
from pathlib import Path

CACHE_PATH = Path("outputs/cache_recommendation.csv")
STREAM_PATH = Path("outputs/live_stream/video_logs.jsonl")

NUM_EVENTS = 120
DELAY_SECONDS = 0.05

CACHE_RATIO = 0.40
WATCHLIST_RATIO = 0.20
NO_CACHE_RATIO = 0.40

STREAM_PATH.parent.mkdir(parents=True, exist_ok=True)

if not CACHE_PATH.exists():
    raise FileNotFoundError(f"Input file not found: {CACHE_PATH}")

df = pd.read_csv(CACHE_PATH)

required_cols = [
    "video_id",
    "window_start",
    "window_end",
    "views_count",
    "hot_score",
    "hot_label",
    "cache_decision",
]

missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")

df["video_id"] = df["video_id"].astype(str)
df["views_count"] = pd.to_numeric(df["views_count"], errors="coerce").fillna(1).astype(int)
df["hot_score"] = pd.to_numeric(df["hot_score"], errors="coerce").fillna(0)
df["cache_decision"] = df["cache_decision"].astype(str).str.upper()

cache_df = df[df["cache_decision"] == "CACHE"].sort_values("hot_score", ascending=False).head(5000)
watch_df = df[df["cache_decision"] == "WATCHLIST"].sort_values("hot_score", ascending=False).head(5000)
no_cache_df = df[df["cache_decision"] == "NO_CACHE"].sort_values("views_count", ascending=False).head(5000)

if len(cache_df) == 0:
    raise RuntimeError("No CACHE records found. Run cache recommendation first.")

def sample_records(source_df, n):
    if n <= 0 or len(source_df) == 0:
        return []

    weights = source_df["views_count"].clip(lower=1)
    sampled = source_df.sample(
        n=n,
        replace=True,
        weights=weights,
        random_state=random.randint(1, 999999),
    )
    return sampled.to_dict("records")

num_cache = int(NUM_EVENTS * CACHE_RATIO)
num_watch = int(NUM_EVENTS * WATCHLIST_RATIO)
num_no_cache = NUM_EVENTS - num_cache - num_watch

events = []
events.extend(sample_records(cache_df, num_cache))
events.extend(sample_records(watch_df, num_watch))
events.extend(sample_records(no_cache_df, num_no_cache))

random.shuffle(events)

STREAM_PATH.write_text("", encoding="utf-8")

print("=" * 100)
print("REAL-TIME VIDEO REQUEST PRODUCER")
print("=" * 100)
print(f"Streaming {len(events)} simulated video requests...")
print(f"CACHE requests: {num_cache}")
print(f"WATCHLIST requests: {num_watch}")
print(f"NO_CACHE requests: {num_no_cache}")
print(f"Output stream: {STREAM_PATH}")
print("-" * 100)

with STREAM_PATH.open("a", encoding="utf-8") as f:
    for i, row in enumerate(events, start=1):
        event = {
            "event_id": i,
            "event_time": str(row.get("window_start", "")),
            "user_id": f"demo_user_{random.randint(1, 50)}",
            "video_id": str(row["video_id"]),
            "views_count": int(row.get("views_count", 1)),
            "hot_score": float(row.get("hot_score", 0)),
            "hot_label": str(row.get("hot_label", "UNKNOWN")),
            "cache_decision_expected": str(row.get("cache_decision", "UNKNOWN")),
        }

        f.write(json.dumps(event, ensure_ascii=False) + "\n")
        f.flush()

        print(
            f"[PRODUCER] event={i:03d} | "
            f"user_id={event['user_id']:<12} | "
            f"video_id={event['video_id']:<10} | "
            f"expected={event['cache_decision_expected']:<9} | "
            f"hot_score={event['hot_score']:.4f}"
        )

        time.sleep(DELAY_SECONDS)

print("-" * 100)
print("Producer finished.")
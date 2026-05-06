import time
import random
import pandas as pd
from pathlib import Path

CACHE_PATH = Path("outputs/cache_recommendation.csv")
OUTPUT_LOG = Path("outputs/demo_request_logs.csv")

NUM_REQUESTS = 50
CACHE_LATENCY_MS = 50
ORIGIN_LATENCY_MS = 300

if not CACHE_PATH.exists():
    raise FileNotFoundError(f"Missing file: {CACHE_PATH}")

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

# Lấy danh sách video đã cache
cached_videos = set(df.loc[df["cache_decision"] == "CACHE", "video_id"].astype(str))

# Tạo request pool: ưu tiên những video có views_count cao để giống hành vi thực tế
request_pool = df.sort_values(["views_count", "hot_score"], ascending=False).head(5000).copy()

if len(request_pool) == 0:
    raise RuntimeError("Request pool is empty.")

weights = request_pool["views_count"].clip(lower=1).tolist()
records = request_pool.to_dict("records")

logs = []

print("=" * 90)
print("REAL-TIME CACHE SIMULATION")
print("=" * 90)
print(f"Cached unique videos: {len(cached_videos)}")
print(f"Simulated requests: {NUM_REQUESTS}")
print("-" * 90)

for i in range(1, NUM_REQUESTS + 1):
    req = random.choices(records, weights=weights, k=1)[0]

    video_id = str(req["video_id"])
    is_hit = video_id in cached_videos

    status = "CACHE HIT" if is_hit else "CACHE MISS"
    served_from = "CACHE SERVER" if is_hit else "ORIGIN SERVER"
    latency = CACHE_LATENCY_MS if is_hit else ORIGIN_LATENCY_MS

    log = {
        "request_id": i,
        "video_id": video_id,
        "hot_score": req["hot_score"],
        "hot_label": req["hot_label"],
        "cache_decision": req["cache_decision"],
        "status": status,
        "served_from": served_from,
        "latency_ms": latency,
    }
    logs.append(log)

    print(
        f"Request {i:02d} | "
        f"video_id={video_id:<8} | "
        f"hot_score={req['hot_score']:.4f} | "
        f"decision={req['cache_decision']:<9} | "
        f"{status:<10} | "
        f"served_from={served_from:<13} | "
        f"latency={latency}ms"
    )

    time.sleep(0.08)

demo_df = pd.DataFrame(logs)

total = len(demo_df)
hits = (demo_df["status"] == "CACHE HIT").sum()
misses = total - hits

hit_ratio = hits / total if total > 0 else 0
avg_latency = demo_df["latency_ms"].mean()
baseline_latency = ORIGIN_LATENCY_MS
latency_saved = baseline_latency - avg_latency

OUTPUT_LOG.parent.mkdir(parents=True, exist_ok=True)
demo_df.to_csv(OUTPUT_LOG, index=False)

print("-" * 90)
print("DEMO SUMMARY")
print("-" * 90)
print(f"Total requests: {total}")
print(f"Cache hits: {hits}")
print(f"Cache misses: {misses}")
print(f"Cache hit ratio: {hit_ratio:.2%}")
print(f"Average latency without cache: {baseline_latency:.2f} ms")
print(f"Average latency with cache: {avg_latency:.2f} ms")
print(f"Latency saved: {latency_saved:.2f} ms")
print(f"Saved demo request logs to: {OUTPUT_LOG}")
print("=" * 90)
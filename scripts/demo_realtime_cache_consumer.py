import json
import time
import pandas as pd
from pathlib import Path

STREAM_PATH = Path("outputs/live_stream/video_logs.jsonl")
CACHE_PATH = Path("outputs/cache_recommendation.csv")
DEMO_LOG_PATH = Path("outputs/demo_realtime_cache_logs.csv")

CACHE_LATENCY_MS = 50
ORIGIN_LATENCY_MS = 300

if not CACHE_PATH.exists():
    raise FileNotFoundError(f"Missing cache recommendation file: {CACHE_PATH}")

STREAM_PATH.parent.mkdir(parents=True, exist_ok=True)
DEMO_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

if not STREAM_PATH.exists():
    STREAM_PATH.write_text("", encoding="utf-8")

# Read only needed columns to reduce memory
cache_header = pd.read_csv(CACHE_PATH, nrows=0).columns.tolist()

base_cols = ["video_id", "hot_score", "hot_label", "cache_decision"]
optional_cols = ["cache_priority", "cache_rank"]

usecols = [c for c in base_cols + optional_cols if c in cache_header]

cache_df = pd.read_csv(CACHE_PATH, usecols=usecols)

cache_df["video_id"] = cache_df["video_id"].astype(str)
cache_df["hot_score"] = pd.to_numeric(cache_df["hot_score"], errors="coerce").fillna(0)
cache_df["cache_decision"] = cache_df["cache_decision"].astype(str).str.upper()

if "cache_priority" not in cache_df.columns:
    cache_df["cache_priority"] = "UNKNOWN"

# For each video_id, keep the highest hot_score decision
video_policy = (
    cache_df.sort_values("hot_score", ascending=False)
    .drop_duplicates(subset=["video_id"], keep="first")
    .set_index("video_id")
    .to_dict(orient="index")
)

cached_videos = {
    video_id
    for video_id, info in video_policy.items()
    if info["cache_decision"] == "CACHE"
}

logs = []
total_requests = 0
cache_hits = 0
cache_misses = 0

print("=" * 110)
print("REAL-TIME CACHE SERVER / CDN SIMULATION")
print("=" * 110)
print(f"Loaded cache policy records: {len(cache_df):,}")
print(f"Unique cached videos: {len(cached_videos):,}")
print(f"Watching stream: {STREAM_PATH}")
print("-" * 110)
print("Waiting for incoming video requests...")
print("-" * 110)

with STREAM_PATH.open("r", encoding="utf-8") as f:
    while True:
        line = f.readline()

        if not line:
            time.sleep(0.05)
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        total_requests += 1
        video_id = str(event["video_id"])

        policy = video_policy.get(
            video_id,
            {
                "hot_score": 0,
                "hot_label": "UNKNOWN",
                "cache_decision": "NO_CACHE",
                "cache_priority": "LOW",
            },
        )

        decision = policy["cache_decision"]
        hot_score = float(policy["hot_score"])
        hot_label = policy.get("hot_label", "UNKNOWN")
        priority = policy.get("cache_priority", "UNKNOWN")

        if decision == "CACHE":
            status = "CACHE HIT"
            served_from = "CACHE SERVER"
            latency_ms = CACHE_LATENCY_MS
            cache_hits += 1
        else:
            status = "CACHE MISS"
            served_from = "ORIGIN SERVER"
            latency_ms = ORIGIN_LATENCY_MS
            cache_misses += 1

        hit_ratio = cache_hits / total_requests if total_requests > 0 else 0
        avg_latency = (
            (cache_hits * CACHE_LATENCY_MS + cache_misses * ORIGIN_LATENCY_MS)
            / total_requests
        )

        log = {
            "request_id": total_requests,
            "event_time": event["event_time"],
            "user_id": event["user_id"],
            "video_id": video_id,
            "hot_score": hot_score,
            "hot_label": hot_label,
            "cache_priority": priority,
            "cache_decision": decision,
            "status": status,
            "served_from": served_from,
            "latency_ms": latency_ms,
            "current_cache_hit_ratio": hit_ratio,
            "current_avg_latency_ms": avg_latency,
        }

        logs.append(log)

        print(
            f"[REQUEST {total_requests:03d}] "
            f"user={event['user_id']:<8} | "
            f"video={video_id:<10} | "
            f"score={hot_score:.4f} | "
            f"decision={decision:<9} | "
            f"{status:<10} | "
            f"from={served_from:<13} | "
            f"latency={latency_ms:>3}ms | "
            f"hit_ratio={hit_ratio:.2%}"
        )

        if total_requests % 20 == 0:
            pd.DataFrame(logs).to_csv(DEMO_LOG_PATH, index=False)
            print("-" * 110)
            print(
                f"[LIVE SUMMARY] requests={total_requests} | "
                f"hits={cache_hits} | "
                f"misses={cache_misses} | "
                f"hit_ratio={hit_ratio:.2%} | "
                f"avg_latency={avg_latency:.2f}ms"
            )
            print("-" * 110)

        if total_requests >= 120:
            break

pd.DataFrame(logs).to_csv(DEMO_LOG_PATH, index=False)

print("=" * 110)
print("FINAL LIVE DEMO SUMMARY")
print("=" * 110)
print(f"Total requests: {total_requests}")
print(f"Cache hits: {cache_hits}")
print(f"Cache misses: {cache_misses}")
print(f"Cache hit ratio: {cache_hits / total_requests:.2%}")
print(f"Average latency with cache: {avg_latency:.2f} ms")
print(f"Baseline latency without cache: {ORIGIN_LATENCY_MS:.2f} ms")
print(f"Saved live demo log to: {DEMO_LOG_PATH}")
print("=" * 110)
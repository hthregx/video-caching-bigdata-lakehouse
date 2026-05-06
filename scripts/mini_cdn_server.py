from pathlib import Path
from datetime import datetime
import random
import time

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse


# =========================
# CONFIG
# =========================

ALL_HOT_PATH = Path("outputs/all_hot_videos.csv")
TOP_HOT_PATH = Path("outputs/top_hot_videos.csv")
CLEAN_LOG_PATH = Path("data/processed/clean_video_logs.csv")

REQUEST_LOG_PATH = Path("outputs/mini_cdn_request_logs.csv")

# Simulated latency ranges
# EDGE_CACHE is faster because it is closer to users.
CACHE_LATENCY_MIN_MS = 30
CACHE_LATENCY_MAX_MS = 80

# ORIGIN_SERVER is slower because it represents the remote origin server.
ORIGIN_LATENCY_MIN_MS = 220
ORIGIN_LATENCY_MAX_MS = 450

GENERAL_REQUEST_SAMPLE_ROWS = 100000


# =========================
# LOAD CACHE POLICY
# =========================

if not ALL_HOT_PATH.exists():
    raise FileNotFoundError(f"Missing file: {ALL_HOT_PATH}")

all_hot = pd.read_csv(ALL_HOT_PATH)

required_hot_cols = [
    "video_id",
    "window_start",
    "window_end",
    "views_count",
    "unique_users",
    "hot_score",
    "hot_label",
]

missing_hot_cols = [c for c in required_hot_cols if c not in all_hot.columns]
if missing_hot_cols:
    raise ValueError(f"Missing columns in all_hot_videos.csv: {missing_hot_cols}")

all_hot["video_id"] = all_hot["video_id"].astype(str)
all_hot["hot_score"] = pd.to_numeric(all_hot["hot_score"], errors="coerce").fillna(0)
all_hot["views_count"] = pd.to_numeric(all_hot["views_count"], errors="coerce").fillna(1).astype(int)

# One video may be HOT in multiple time windows.
# For CDN caching, keep only the best HOT window per video_id.
cache_policy = (
    all_hot.sort_values("hot_score", ascending=False)
    .drop_duplicates(subset=["video_id"], keep="first")
    .set_index("video_id")
    .to_dict(orient="index")
)

cached_videos = set(cache_policy.keys())
cached_records = list(cache_policy.items())


# =========================
# BUILD MISS VIDEO POOL
# =========================

miss_video_pool = []

if CLEAN_LOG_PATH.exists():
    clean_sample = pd.read_csv(
        CLEAN_LOG_PATH,
        usecols=["video_id"],
        nrows=GENERAL_REQUEST_SAMPLE_ROWS,
    )

    clean_sample["video_id"] = clean_sample["video_id"].astype(str)

    miss_video_pool = [
        video_id
        for video_id in clean_sample["video_id"].dropna().unique().tolist()
        if video_id not in cached_videos
    ]

if len(miss_video_pool) == 0:
    miss_video_pool = [f"origin_only_video_{i}" for i in range(1, 1001)]


# =========================
# APP STATE
# =========================

app = FastAPI(
    title="Mini CDN Cache Server",
    description="Mini CDN simulation for video caching project",
    version="1.0.0",
)

request_logs = []
total_requests = 0
cache_hits = 0
cache_misses = 0


# =========================
# HELPER FUNCTIONS
# =========================

def get_average_latency_ms():
    if len(request_logs) == 0:
        return 0.0

    return sum(item["latency_ms"] for item in request_logs) / len(request_logs)


def get_cache_hit_ratio():
    if total_requests == 0:
        return 0.0

    return cache_hits / total_requests


def save_logs():
    if len(request_logs) > 0:
        REQUEST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(request_logs).to_csv(REQUEST_LOG_PATH, index=False)


def serve_video(video_id: str, simulate_delay: bool = True):
    global total_requests, cache_hits, cache_misses

    video_id = str(video_id)
    total_requests += 1

    if video_id in cached_videos:
        status = "CACHE_HIT"
        served_from = "EDGE_CACHE"
        latency_ms = random.randint(CACHE_LATENCY_MIN_MS, CACHE_LATENCY_MAX_MS)
        cache_hits += 1

        policy = cache_policy[video_id]
        hot_score = float(policy.get("hot_score", 0))
        hot_label = str(policy.get("hot_label", "HOT"))
        window_start = str(policy.get("window_start", ""))
        window_end = str(policy.get("window_end", ""))
        cache_decision = "CACHE"

    else:
        status = "CACHE_MISS"
        served_from = "ORIGIN_SERVER"
        latency_ms = random.randint(ORIGIN_LATENCY_MIN_MS, ORIGIN_LATENCY_MAX_MS)
        cache_misses += 1

        hot_score = 0.0
        hot_label = "NOT_HOT"
        window_start = ""
        window_end = ""
        cache_decision = "NO_CACHE"

    if simulate_delay:
        time.sleep(latency_ms / 1000)

    log = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "request_id": total_requests,
        "video_id": video_id,
        "hot_score": hot_score,
        "hot_label": hot_label,
        "window_start": window_start,
        "window_end": window_end,
        "cache_decision": cache_decision,
        "status": status,
        "served_from": served_from,
        "latency_ms": latency_ms,
    }

    request_logs.append(log)

    hit_ratio = get_cache_hit_ratio()
    avg_latency_ms = get_average_latency_ms()

    log["current_cache_hit_ratio"] = round(hit_ratio, 6)
    log["current_avg_latency_ms"] = round(avg_latency_ms, 4)

    if len(request_logs) % 20 == 0:
        save_logs()

    return log


def random_cached_video_id():
    video_id, _ = random.choice(cached_records)
    return video_id


def random_miss_video_id():
    return random.choice(miss_video_pool)


# =========================
# ROUTES
# =========================

@app.get("/")
def home():
    return {
        "service": "Mini CDN Cache Server",
        "status": "running",
        "description": "Use /video/{video_id}, /demo/mixed, /cache/top, /stats",
        "hot_video_window_records": len(all_hot),
        "cached_unique_videos": len(cached_videos),
        "cache_latency_range_ms": f"{CACHE_LATENCY_MIN_MS}-{CACHE_LATENCY_MAX_MS}",
        "origin_latency_range_ms": f"{ORIGIN_LATENCY_MIN_MS}-{ORIGIN_LATENCY_MAX_MS}",
    }


@app.get("/stats")
def stats():
    hit_ratio = get_cache_hit_ratio()
    avg_latency_ms = get_average_latency_ms()

    return {
        "total_requests": total_requests,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "cache_hit_ratio": round(hit_ratio, 6),
        "average_latency_ms": round(avg_latency_ms, 4),
        "cache_latency_range_ms": f"{CACHE_LATENCY_MIN_MS}-{CACHE_LATENCY_MAX_MS}",
        "origin_latency_range_ms": f"{ORIGIN_LATENCY_MIN_MS}-{ORIGIN_LATENCY_MAX_MS}",
        "hot_video_window_records": len(all_hot),
        "cached_unique_videos": len(cached_videos),
        "request_log_path": str(REQUEST_LOG_PATH),
    }


@app.post("/reset")
def reset_stats():
    global total_requests, cache_hits, cache_misses, request_logs

    total_requests = 0
    cache_hits = 0
    cache_misses = 0
    request_logs = []

    if REQUEST_LOG_PATH.exists():
        REQUEST_LOG_PATH.unlink()

    return {
        "message": "Stats and request logs reset successfully."
    }


@app.get("/cache/top")
def top_cached_videos(n: int = Query(20, ge=1, le=100)):
    top_df = (
        all_hot.sort_values("hot_score", ascending=False)
        .head(n)
        [
            [
                "video_id",
                "window_start",
                "window_end",
                "views_count",
                "unique_users",
                "hot_score",
                "hot_label",
            ]
        ]
    )

    return {
        "top_n": n,
        "records": top_df.to_dict(orient="records"),
    }


@app.get("/video/{video_id}")
def request_video(
    video_id: str,
    simulate_delay: bool = Query(True),
):
    result = serve_video(video_id, simulate_delay=simulate_delay)
    return JSONResponse(result)


@app.get("/demo/cache-hit")
def demo_cache_hit():
    video_id = random_cached_video_id()
    result = serve_video(video_id, simulate_delay=True)
    return JSONResponse(result)


@app.get("/demo/cache-miss")
def demo_cache_miss():
    video_id = random_miss_video_id()
    result = serve_video(video_id, simulate_delay=True)
    return JSONResponse(result)


@app.get("/demo/mixed")
def demo_mixed(
    count: int = Query(20, ge=1, le=200),
    cache_ratio: float = Query(0.4, ge=0.0, le=1.0),
):
    results = []

    num_cache = int(count * cache_ratio)
    num_miss = count - num_cache

    video_ids = []

    for _ in range(num_cache):
        video_ids.append(random_cached_video_id())

    for _ in range(num_miss):
        video_ids.append(random_miss_video_id())

    random.shuffle(video_ids)

    for video_id in video_ids:
        results.append(serve_video(video_id, simulate_delay=True))

    save_logs()

    hits = sum(1 for result in results if result["status"] == "CACHE_HIT")
    misses = len(results) - hits
    avg_latency = sum(result["latency_ms"] for result in results) / len(results)

    return {
        "demo_requests": count,
        "cache_hits": hits,
        "cache_misses": misses,
        "cache_hit_ratio": round(hits / count, 6),
        "average_latency_ms": round(avg_latency, 4),
        "results": results,
    }


# =========================
# RUN SERVER
# =========================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "mini_cdn_server:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
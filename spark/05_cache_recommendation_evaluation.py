import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

# CONFIG
INPUT_PATH = Path("outputs/hot_video_predictions.csv")

OUTPUT_DIR = Path("outputs")
CHARTS_DIR = OUTPUT_DIR / "charts"

CACHE_RECOMMENDATION_PATH = OUTPUT_DIR / "cache_recommendation.csv"
EVALUATION_METRICS_PATH = OUTPUT_DIR / "evaluation_metrics.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

ORIGIN_LATENCY_MS = 300
CACHE_LATENCY_MS = 50
AVERAGE_REQUEST_SIZE_MB = 20
COST_PER_GB = 0.02

# Dùng để tạo WATCHLIST trong nhóm chưa HOT
WATCHLIST_TOP_PERCENTILE = 0.95


# LOAD INPUT

if not INPUT_PATH.exists():
    raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

df = pd.read_csv(INPUT_PATH)

required_cols = [
    "video_id",
    "window_start",
    "window_end",
    "views_count",
    "unique_users",
    "avg_watch_ratio",
    "growth_rate",
    "engagement_count",
    "hot_score",
    "predicted_hot",
    "hot_label",
]

missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")

# Ép kiểu dữ liệu
df["video_id"] = df["video_id"].astype(str)
df["views_count"] = pd.to_numeric(df["views_count"], errors="coerce").fillna(0).astype(int)
df["unique_users"] = pd.to_numeric(df["unique_users"], errors="coerce").fillna(0).astype(int)
df["avg_watch_ratio"] = pd.to_numeric(df["avg_watch_ratio"], errors="coerce").fillna(0)
df["growth_rate"] = pd.to_numeric(df["growth_rate"], errors="coerce").fillna(0)
df["engagement_count"] = pd.to_numeric(df["engagement_count"], errors="coerce").fillna(0).astype(int)
df["hot_score"] = pd.to_numeric(df["hot_score"], errors="coerce").fillna(0)
df["predicted_hot"] = pd.to_numeric(df["predicted_hot"], errors="coerce").fillna(0).astype(int)
df["hot_label"] = df["hot_label"].astype(str).str.upper()

# Bảo vệ trường hợp hot_label không đồng bộ với predicted_hot
df.loc[df["predicted_hot"] == 1, "hot_label"] = "HOT"
df.loc[(df["predicted_hot"] == 0) & (df["hot_label"] != "HOT"), "hot_label"] = "NOT_HOT"


# CACHE RECOMMENDATION

non_hot_df = df[df["hot_label"] != "HOT"]

if len(non_hot_df) > 0:
    watchlist_threshold = non_hot_df["hot_score"].quantile(WATCHLIST_TOP_PERCENTILE)
else:
    watchlist_threshold = df["hot_score"].quantile(WATCHLIST_TOP_PERCENTILE)

global_p99 = df["hot_score"].quantile(0.99)

def get_cache_decision(row):
    if row["hot_label"] == "HOT":
        return "CACHE"
    if row["hot_score"] >= watchlist_threshold:
        return "WATCHLIST"
    return "NO_CACHE"

def get_cache_priority(row):
    if row["cache_decision"] == "CACHE":
        if row["hot_score"] >= global_p99:
            return "VERY_HIGH"
        return "HIGH"
    if row["cache_decision"] == "WATCHLIST":
        return "MEDIUM"
    return "LOW"

def get_reason(row):
    if row["cache_decision"] == "CACHE":
        return "Predicted as HOT; preload this video-window into cache."
    if row["cache_decision"] == "WATCHLIST":
        return "High hot_score among non-HOT records; monitor for possible caching."
    return "Low trending signal; do not cache to avoid wasting resources."

df["cache_decision"] = df.apply(get_cache_decision, axis=1)
df["cache_priority"] = df.apply(get_cache_priority, axis=1)
df["reason"] = df.apply(get_reason, axis=1)

df["cache_rank"] = df["hot_score"].rank(method="first", ascending=False).astype(int)

priority_order = {
    "VERY_HIGH": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}

df["priority_sort"] = df["cache_priority"].map(priority_order).fillna(9).astype(int)

cache_df = df.sort_values(
    by=["priority_sort", "hot_score", "views_count"],
    ascending=[True, False, False],
)

output_cols = [
    "video_id",
    "window_start",
    "window_end",
    "views_count",
    "unique_users",
    "avg_watch_ratio",
    "growth_rate",
    "engagement_count",
    "hot_score",
    "predicted_hot",
    "hot_label",
    "cache_rank",
    "cache_priority",
    "cache_decision",
    "reason",
]

cache_df[output_cols].to_csv(CACHE_RECOMMENDATION_PATH, index=False)


# EVALUATION

total_requests = int(df["views_count"].sum())
cache_hits = int(df.loc[df["cache_decision"] == "CACHE", "views_count"].sum())
watchlist_requests = int(df.loc[df["cache_decision"] == "WATCHLIST", "views_count"].sum())
cache_misses = total_requests - cache_hits

cache_hit_ratio = cache_hits / total_requests if total_requests > 0 else 0
origin_request_reduction = cache_hit_ratio

avg_latency_without_cache = ORIGIN_LATENCY_MS

if total_requests > 0:
    avg_latency_with_cache = (
        cache_hits * CACHE_LATENCY_MS
        + cache_misses * ORIGIN_LATENCY_MS
    ) / total_requests
else:
    avg_latency_with_cache = 0

latency_reduction_ms = avg_latency_without_cache - avg_latency_with_cache
latency_reduction_percent = (
    latency_reduction_ms / avg_latency_without_cache
    if avg_latency_without_cache > 0
    else 0
)

estimated_bandwidth_saved_gb = (cache_hits * AVERAGE_REQUEST_SIZE_MB) / 1024
estimated_cost_saved = estimated_bandwidth_saved_gb * COST_PER_GB

metrics = pd.DataFrame([
    {
        "metric": "total_requests",
        "value": total_requests,
        "unit": "requests",
        "description": "Total simulated requests based on views_count.",
    },
    {
        "metric": "cache_hits",
        "value": cache_hits,
        "unit": "requests",
        "description": "Requests served from cache because cache_decision is CACHE.",
    },
    {
        "metric": "cache_misses",
        "value": cache_misses,
        "unit": "requests",
        "description": "Requests still served by the origin server.",
    },
    {
        "metric": "watchlist_requests",
        "value": watchlist_requests,
        "unit": "requests",
        "description": "Requests belonging to WATCHLIST records.",
    },
    {
        "metric": "cache_hit_ratio",
        "value": round(cache_hit_ratio, 6),
        "unit": "ratio",
        "description": "Share of requests served by cache.",
    },
    {
        "metric": "origin_request_reduction",
        "value": round(origin_request_reduction, 6),
        "unit": "ratio",
        "description": "Estimated reduction of requests to origin server.",
    },
    {
        "metric": "average_latency_without_cache",
        "value": round(avg_latency_without_cache, 4),
        "unit": "ms",
        "description": "Assumed average latency if all requests go to origin.",
    },
    {
        "metric": "average_latency_with_cache",
        "value": round(avg_latency_with_cache, 4),
        "unit": "ms",
        "description": "Estimated average latency after applying cache recommendation.",
    },
    {
        "metric": "latency_reduction_ms",
        "value": round(latency_reduction_ms, 4),
        "unit": "ms",
        "description": "Estimated latency reduction in milliseconds.",
    },
    {
        "metric": "latency_reduction_percent",
        "value": round(latency_reduction_percent, 6),
        "unit": "ratio",
        "description": "Estimated latency reduction ratio.",
    },
    {
        "metric": "estimated_bandwidth_saved",
        "value": round(estimated_bandwidth_saved_gb, 4),
        "unit": "GB",
        "description": "Estimated bandwidth saved from cached requests.",
    },
    {
        "metric": "estimated_cost_saved",
        "value": round(estimated_cost_saved, 4),
        "unit": "USD",
        "description": "Estimated bandwidth cost saved.",
    },
    {
        "metric": "num_cache_records",
        "value": int((df["cache_decision"] == "CACHE").sum()),
        "unit": "records",
        "description": "Number of video-window records recommended for CACHE.",
    },
    {
        "metric": "num_watchlist_records",
        "value": int((df["cache_decision"] == "WATCHLIST").sum()),
        "unit": "records",
        "description": "Number of video-window records recommended for WATCHLIST.",
    },
    {
        "metric": "num_no_cache_records",
        "value": int((df["cache_decision"] == "NO_CACHE").sum()),
        "unit": "records",
        "description": "Number of video-window records recommended for NO_CACHE.",
    },
    {
        "metric": "num_unique_cached_videos",
        "value": int(df.loc[df["cache_decision"] == "CACHE", "video_id"].nunique()),
        "unit": "videos",
        "description": "Number of unique videos recommended for CACHE.",
    },
    {
        "metric": "num_unique_total_videos",
        "value": int(df["video_id"].nunique()),
        "unit": "videos",
        "description": "Number of unique videos in prediction output.",
    },
    {
        "metric": "origin_latency_ms_assumption",
        "value": ORIGIN_LATENCY_MS,
        "unit": "ms",
        "description": "Latency assumption for origin server.",
    },
    {
        "metric": "cache_latency_ms_assumption",
        "value": CACHE_LATENCY_MS,
        "unit": "ms",
        "description": "Latency assumption for cache server.",
    },
    {
        "metric": "average_request_size_mb_assumption",
        "value": AVERAGE_REQUEST_SIZE_MB,
        "unit": "MB",
        "description": "Assumed average video request size.",
    },
    {
        "metric": "cost_per_gb_assumption",
        "value": COST_PER_GB,
        "unit": "USD/GB",
        "description": "Assumed bandwidth cost per GB.",
    },
])

metrics.to_csv(EVALUATION_METRICS_PATH, index=False)


# CHARTS

# 1. Cache decision distribution
decision_counts = df["cache_decision"].value_counts()

plt.figure(figsize=(8, 5))
decision_counts.plot(kind="bar")
plt.title("Cache Decision Distribution")
plt.xlabel("Cache Decision")
plt.ylabel("Number of Video-Window Records")
plt.tight_layout()
plt.savefig(CHARTS_DIR / "cache_decision_distribution.png", dpi=160)
plt.close()

# 2. Cache hits vs misses
hit_miss_df = pd.DataFrame({
    "type": ["Cache Hits", "Cache Misses"],
    "requests": [cache_hits, cache_misses],
})

plt.figure(figsize=(8, 5))
plt.bar(hit_miss_df["type"], hit_miss_df["requests"])
plt.title("Cache Hits vs Cache Misses")
plt.xlabel("Request Type")
plt.ylabel("Number of Requests")
plt.tight_layout()
plt.savefig(CHARTS_DIR / "cache_hit_vs_miss.png", dpi=160)
plt.close()

# 3. Latency comparison
latency_df = pd.DataFrame({
    "scenario": ["Without Cache", "With Cache"],
    "latency_ms": [avg_latency_without_cache, avg_latency_with_cache],
})

plt.figure(figsize=(8, 5))
plt.bar(latency_df["scenario"], latency_df["latency_ms"])
plt.title("Average Latency Comparison")
plt.xlabel("Scenario")
plt.ylabel("Latency (ms)")
plt.tight_layout()
plt.savefig(CHARTS_DIR / "latency_comparison.png", dpi=160)
plt.close()

# 4. Evaluation summary percentages
summary_df = pd.DataFrame({
    "metric": [
        "Cache Hit Ratio",
        "Origin Request Reduction",
        "Latency Reduction",
    ],
    "percent": [
        cache_hit_ratio * 100,
        origin_request_reduction * 100,
        latency_reduction_percent * 100,
    ],
})

plt.figure(figsize=(9, 5))
bars = plt.bar(summary_df["metric"], summary_df["percent"])
plt.title("Caching Evaluation Summary (%)")
plt.xlabel("Metric")
plt.ylabel("Percent (%)")
plt.xticks(rotation=15)

max_val = summary_df["percent"].max()
plt.ylim(0, max(max_val * 1.5, 1))

for bar, value in zip(bars, summary_df["percent"]):
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        f"{value:.2f}%",
        ha="center",
        va="bottom",
        fontsize=9,
    )

plt.tight_layout()
plt.savefig(CHARTS_DIR / "evaluation_metrics_summary.png", dpi=160)
plt.close()

# 5. Top cached videos
top_cached = (
    df[df["cache_decision"] == "CACHE"]
    .sort_values("hot_score", ascending=False)
    .head(20)
)

if len(top_cached) > 0:
    plt.figure(figsize=(11, 6))
    plt.bar(top_cached["video_id"].astype(str), top_cached["hot_score"])
    plt.title("Top 20 Cached Videos by Hot Score")
    plt.xlabel("Video ID")
    plt.ylabel("Hot Score")
    plt.xticks(rotation=60, ha="right")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "top_cached_videos.png", dpi=160)
    plt.close()


# PRINT SUMMARY

print("CACHE RECOMMENDATION SUMMARY")
print("Input rows:", len(df))
print(df["cache_decision"].value_counts())
print("Total requests:", total_requests)
print("Cache hits:", cache_hits)
print("Cache hit ratio:", round(cache_hit_ratio, 6))
print("Latency reduction:", round(latency_reduction_ms, 4), "ms")
print("Estimated cost saved:", round(estimated_cost_saved, 4), "USD")
print("Saved:", CACHE_RECOMMENDATION_PATH)
print("Saved:", EVALUATION_METRICS_PATH)
print("Saved charts to:", CHARTS_DIR)


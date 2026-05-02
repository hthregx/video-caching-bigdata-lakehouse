import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

INPUT_PATH = "outputs/hot_video_predictions.csv"
OUTPUT_DIR = Path("outputs")
CHARTS_DIR = OUTPUT_DIR / "charts"
OUTPUT_DIR.mkdir(exist_ok=True)
CHARTS_DIR.mkdir(exist_ok=True)

CACHE_THRESHOLD = 0.60
ORIGIN_LATENCY_MS = 200
CACHE_LATENCY_MS = 40
COST_PER_1000_ORIGIN_REQUESTS = 0.02

df = pd.read_csv(INPUT_PATH)

required_cols = [
    "video_id", "views_count", "unique_users", "avg_watch_ratio",
    "growth_rate", "engagement_count", "hot_score", "predicted_hot"
]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

CACHE_TOP_N = 100

df = df.sort_values(by="hot_score", ascending=False).reset_index(drop=True)
df["cache_decision"] = 0
df.loc[:CACHE_TOP_N - 1, "cache_decision"] = 1
df["cache_priority"] = df["hot_score"].rank(method="dense", ascending=False).astype(int)

cache_recommendation = df.sort_values(
    by=["cache_decision", "hot_score", "views_count"],
    ascending=[False, False, False]
)
cache_recommendation.to_csv(OUTPUT_DIR / "cache_recommendation.csv", index=False)

total_requests = int(df["views_count"].sum())
cached_requests = int(df.loc[df["cache_decision"] == 1, "views_count"].sum())
non_cached_requests = total_requests - cached_requests

cache_hit_ratio = cached_requests / total_requests if total_requests > 0 else 0
origin_request_reduction = cache_hit_ratio

avg_latency_without_cache = ORIGIN_LATENCY_MS
avg_latency_with_cache = (
    cache_hit_ratio * CACHE_LATENCY_MS
    + (1 - cache_hit_ratio) * ORIGIN_LATENCY_MS
)
latency_reduction_ms = avg_latency_without_cache - avg_latency_with_cache
latency_reduction_percent = latency_reduction_ms / avg_latency_without_cache

estimated_origin_cost_before = total_requests / 1000 * COST_PER_1000_ORIGIN_REQUESTS
estimated_origin_cost_after = non_cached_requests / 1000 * COST_PER_1000_ORIGIN_REQUESTS
estimated_cost_saving = estimated_origin_cost_before - estimated_origin_cost_after

metrics = pd.DataFrame([
    {"metric": "total_requests", "value": total_requests},
    {"metric": "cached_requests", "value": cached_requests},
    {"metric": "non_cached_requests", "value": non_cached_requests},
    {"metric": "cache_hit_ratio", "value": cache_hit_ratio},
    {"metric": "origin_request_reduction", "value": origin_request_reduction},
    {"metric": "avg_latency_without_cache_ms", "value": avg_latency_without_cache},
    {"metric": "avg_latency_with_cache_ms", "value": avg_latency_with_cache},
    {"metric": "latency_reduction_ms", "value": latency_reduction_ms},
    {"metric": "latency_reduction_percent", "value": latency_reduction_percent},
    {"metric": "estimated_origin_cost_before_usd", "value": estimated_origin_cost_before},
    {"metric": "estimated_origin_cost_after_usd", "value": estimated_origin_cost_after},
    {"metric": "estimated_cost_saving_usd", "value": estimated_cost_saving},
    {"metric": "num_cached_rows", "value": int(df["cache_decision"].sum())},
    {"metric": "num_total_rows", "value": int(len(df))},
    {"metric": "num_unique_cached_videos", "value": int(df.loc[df["cache_decision"] == 1, "video_id"].nunique())},
    {"metric": "num_unique_total_videos", "value": int(df["video_id"].nunique())},
    {"metric": "cache_threshold", "value": CACHE_THRESHOLD},
    {"metric": "origin_latency_ms_assumption", "value": ORIGIN_LATENCY_MS},
    {"metric": "cache_latency_ms_assumption", "value": CACHE_LATENCY_MS},
    {"metric": "cost_per_1000_origin_requests_assumption_usd", "value": COST_PER_1000_ORIGIN_REQUESTS},
])
metrics.to_csv(OUTPUT_DIR / "evaluation_metrics.csv", index=False)

top_cached = cache_recommendation[cache_recommendation["cache_decision"] == 1].head(10).copy()

plt.figure(figsize=(10, 5))
plt.bar(top_cached["video_id"].astype(str), top_cached["hot_score"])
plt.title("Top 10 Cached Videos by Hot Score")
plt.xlabel("Video ID")
plt.ylabel("Hot Score")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(CHARTS_DIR / "top_cached_videos.png", dpi=160)
plt.close()

decision_counts = df["cache_decision"].value_counts().sort_index()
labels = ["Not Cached", "Cached"]
values = [int(decision_counts.get(0, 0)), int(decision_counts.get(1, 0))]
plt.figure(figsize=(7, 5))
plt.bar(labels, values)
plt.title("Cache Decision Distribution")
plt.xlabel("Decision")
plt.ylabel("Number of Rows")
plt.tight_layout()
plt.savefig(CHARTS_DIR / "cache_decision_distribution.png", dpi=160)
plt.close()

eval_chart_data = pd.DataFrame({
    "metric": ["Cache Hit Ratio", "Latency Reduction", "Cost Saving Ratio"],
    "percent": [
        cache_hit_ratio * 100,
        latency_reduction_percent * 100,
        estimated_cost_saving / estimated_origin_cost_before * 100
        if estimated_origin_cost_before > 0 else 0
    ]
})

plt.figure(figsize=(9, 5))
bars = plt.bar(eval_chart_data["metric"], eval_chart_data["percent"])
plt.title("Caching Evaluation Summary (%)", pad=15)
plt.xlabel("Metric")
plt.ylabel("Percent (%)")
plt.xticks(rotation=15)

max_val = eval_chart_data["percent"].max()
plt.ylim(0, max(max_val * 1.6, 0.15))

for bar, value in zip(bars, eval_chart_data["percent"]):
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        f"{value:.4f}%",
        ha="center",
        va="bottom",
        fontsize=9
    )

plt.tight_layout()
plt.savefig(CHARTS_DIR / "evaluation_metrics_summary.png", dpi=160)
plt.close()

print("Done.")
print(f"Saved: {OUTPUT_DIR / 'cache_recommendation.csv'}")
print(f"Saved: {OUTPUT_DIR / 'evaluation_metrics.csv'}")
print(f"Saved charts in: {CHARTS_DIR}")

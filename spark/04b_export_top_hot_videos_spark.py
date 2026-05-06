from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import col


INPUT_PATH = "outputs/hot_video_predictions.csv"
TOP_OUTPUT_FILE = "outputs/top_hot_videos.csv"
ALL_HOT_OUTPUT_FILE = "outputs/all_hot_videos.csv"


def write_single_csv(df, output_file):
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = df.toPandas()
    pdf.to_csv(output_path, index=False)

    print(f"Saved single CSV: {output_path}")
    print(f"Rows saved: {len(pdf)}")


spark = (
    SparkSession.builder
    .appName("ExportTopHotVideosSpark")
    .master("local[*]")
    .getOrCreate()
)

df = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv(INPUT_PATH)
)

selected_cols = [
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

missing_cols = [c for c in selected_cols if c not in df.columns]
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")

all_hot = (
    df.filter(col("hot_label") == "HOT")
    .select(*selected_cols)
    .orderBy(col("hot_score").desc())
)

top_hot = all_hot.limit(20)

print("EXPORT HOT VIDEOS")
print("All HOT rows:", all_hot.count())
top_hot.show(20, truncate=False)

write_single_csv(all_hot, ALL_HOT_OUTPUT_FILE)
write_single_csv(top_hot, TOP_OUTPUT_FILE)

print(f"Saved: {ALL_HOT_OUTPUT_FILE}")
print(f"Saved: {TOP_OUTPUT_FILE}")

spark.stop()
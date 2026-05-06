from pathlib import Path
import csv

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    count,
    countDistinct,
    avg,
    sum as spark_sum,
    window,
    lag,
    when,
    lit,
    to_timestamp,
)
from pyspark.sql.window import Window
from pyspark import StorageLevel


INPUT_PATH = "data/processed/clean_video_logs.csv"
OUTPUT_FILE = "outputs/video_features.csv"


def write_single_csv(df, output_file):
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Ghi ra file tạm trước, chỉ thay file chính khi ghi thành công
    temp_file = output_path.with_suffix(".tmp.csv")

    columns = df.columns
    row_count = 0

    with temp_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)

        for row in df.toLocalIterator():
            writer.writerow([row[c] for c in columns])
            row_count += 1

            if row_count % 100000 == 0:
                print(f"Written rows: {row_count}")

    if row_count == 0:
        raise RuntimeError("Export failed: 0 rows were written. Output file was not replaced.")

    # Chỉ replace file chính sau khi ghi xong toàn bộ
    temp_file.replace(output_path)

    print(f"Saved single CSV: {output_path}")
    print(f"Rows saved: {row_count}")


spark = (
    SparkSession.builder
    .appName("VideoFeatureEngineeringSpark")
    .master("local[*]")
    .config("spark.sql.shuffle.partitions", "16")
    .getOrCreate()
)

df = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv(INPUT_PATH)
)

required_cols = [
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

missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")

df = (
    df.withColumn("event_time", to_timestamp(col("event_time")))
    .withColumn("user_id", col("user_id").cast("string"))
    .withColumn("video_id", col("video_id").cast("string"))
    .withColumn("watch_time", col("watch_time").cast("double"))
    .withColumn("duration", col("duration").cast("double"))
    .withColumn("watch_ratio", col("watch_ratio").cast("double"))
    .withColumn("is_click", col("is_click").cast("int"))
    .withColumn("is_like", col("is_like").cast("int"))
    .withColumn("is_share", col("is_share").cast("int"))
)

df = df.dropna(subset=["event_time", "user_id", "video_id"])
df = df.filter(col("duration") > 0)
df = df.filter(col("watch_time") >= 0)

df = df.withColumn(
    "watch_ratio",
    when(col("watch_ratio") < 0, lit(0))
    .when(col("watch_ratio") > 1, lit(1))
    .otherwise(col("watch_ratio"))
)

feature_df = (
    df.groupBy(
        "video_id",
        window(col("event_time"), "30 minutes").alias("time_window"),
    )
    .agg(
        count("*").alias("views_count"),
        countDistinct("user_id").alias("unique_users"),
        avg("watch_ratio").alias("avg_watch_ratio"),
        avg("watch_time").alias("avg_watch_time"),
        spark_sum(col("is_like") + col("is_share")).alias("engagement_count"),
    )
    .withColumn("window_start", col("time_window.start"))
    .withColumn("window_end", col("time_window.end"))
    .drop("time_window")
)

w = Window.partitionBy("video_id").orderBy("window_start")

feature_df = feature_df.withColumn("prev_views", lag("views_count").over(w))

feature_df = feature_df.withColumn(
    "growth_rate",
    when(col("prev_views").isNull(), col("views_count").cast("double"))
    .when(col("prev_views") == 0, col("views_count").cast("double"))
    .otherwise((col("views_count") - col("prev_views")) / col("prev_views")),
)

feature_df = feature_df.drop("prev_views")

feature_df = feature_df.select(
    "video_id",
    "window_start",
    "window_end",
    "views_count",
    "unique_users",
    "avg_watch_ratio",
    "avg_watch_time",
    "growth_rate",
    "engagement_count",
)

# Không sort toàn bộ data trước khi ghi vì output có thể hơn 4 triệu dòng
feature_df = feature_df.persist(StorageLevel.MEMORY_AND_DISK)

print("VIDEO FEATURES SUMMARY")
feature_rows = feature_df.count()
print("Feature rows:", feature_rows)

print("TOP 20 FEATURES FOR PREVIEW")
feature_df.orderBy(col("views_count").desc(), col("growth_rate").desc()).show(20, truncate=False)

write_single_csv(feature_df, OUTPUT_FILE)

print(f"Saved: {OUTPUT_FILE}")

feature_df.unpersist()
spark.stop()
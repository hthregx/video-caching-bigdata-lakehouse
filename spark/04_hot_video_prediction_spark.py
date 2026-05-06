from pathlib import Path
import csv

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lit
from pyspark import StorageLevel


INPUT_PATH = "outputs/video_features.csv"
OUTPUT_FILE = "outputs/hot_video_predictions.csv"

HOT_PERCENTILE = 0.99


def write_single_csv(df, output_file):
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

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

    temp_file.replace(output_path)

    print(f"Saved single CSV: {output_path}")
    print(f"Rows saved: {row_count}")


spark = (
    SparkSession.builder
    .appName("HotVideoPredictionSpark")
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
    "video_id",
    "window_start",
    "window_end",
    "views_count",
    "unique_users",
    "avg_watch_ratio",
    "growth_rate",
    "engagement_count",
]

missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")

df = (
    df.withColumn("views_count", col("views_count").cast("double"))
    .withColumn("unique_users", col("unique_users").cast("double"))
    .withColumn("avg_watch_ratio", col("avg_watch_ratio").cast("double"))
    .withColumn("growth_rate", col("growth_rate").cast("double"))
    .withColumn("engagement_count", col("engagement_count").cast("double"))
)

stats = df.agg(
    {"views_count": "max", "growth_rate": "max", "engagement_count": "max"}
).collect()[0]

max_views = stats["max(views_count)"] or 1
max_growth = stats["max(growth_rate)"] or 1
max_engagement = stats["max(engagement_count)"] or 1

df = df.withColumn("views_score", col("views_count") / lit(max_views))
df = df.withColumn("growth_score", col("growth_rate") / lit(max_growth))
df = df.withColumn("watch_ratio_score", col("avg_watch_ratio"))

if max_engagement > 0:
    df = df.withColumn("engagement_score", col("engagement_count") / lit(max_engagement))
else:
    df = df.withColumn("engagement_score", lit(0.0))

df = df.withColumn(
    "hot_score",
    0.4 * col("views_score")
    + 0.25 * col("growth_score")
    + 0.2 * col("watch_ratio_score")
    + 0.15 * col("engagement_score")
)

threshold = df.approxQuantile("hot_score", [HOT_PERCENTILE], 0.001)[0]

df = df.withColumn(
    "predicted_hot",
    when(col("hot_score") >= lit(threshold), lit(1)).otherwise(lit(0))
)

df = df.withColumn(
    "hot_label",
    when(col("predicted_hot") == 1, lit("HOT")).otherwise(lit("NOT_HOT"))
)

output_df = df.select(
    "video_id",
    "window_start",
    "window_end",
    "views_count",
    "unique_users",
    "avg_watch_ratio",
    "growth_rate",
    "engagement_count",
    "views_score",
    "growth_score",
    "watch_ratio_score",
    "engagement_score",
    "hot_score",
    "predicted_hot",
    "hot_label",
)

# Cache để tránh Spark tính lại quá nhiều lần
output_df = output_df.persist(StorageLevel.MEMORY_AND_DISK)

print("HOT VIDEO PREDICTION SUMMARY")
input_rows = output_df.count()
print("Input rows:", input_rows)
print(f"Dynamic hot threshold p{int(HOT_PERCENTILE * 100)}:", threshold)

output_df.groupBy("hot_label").count().show()

print("TOP 20 HOT SCORE PREVIEW")
output_df.orderBy(col("hot_score").desc()).show(20, truncate=False)

write_single_csv(output_df, OUTPUT_FILE)

print(f"Saved: {OUTPUT_FILE}")

output_df.unpersist()
spark.stop()
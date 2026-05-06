from pathlib import Path
import csv

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lit, max as spark_max


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
    .appName("HotVideoPredictionSparkFull")
    .master("local[2]")
    .config("spark.sql.shuffle.partitions", "4")
    .config("spark.default.parallelism", "4")
    .config("spark.driver.memory", "8g")
    .config("spark.driver.maxResultSize", "2g")
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
    spark_max("views_count").alias("max_views"),
    spark_max("growth_rate").alias("max_growth"),
    spark_max("engagement_count").alias("max_engagement"),
).collect()[0]

max_views = stats["max_views"] or 1
max_growth = stats["max_growth"] or 1
max_engagement = stats["max_engagement"] or 1

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

output_df = (
    df.withColumn(
        "predicted_hot",
        when(col("hot_score") >= lit(threshold), lit(1)).otherwise(lit(0))
    )
    .withColumn(
        "hot_label",
        when(col("predicted_hot") == 1, lit("HOT")).otherwise(lit("NOT_HOT"))
    )
    .select(
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
)

print("HOT VIDEO PREDICTION FULL DATASET")
print(f"Dynamic hot threshold p{int(HOT_PERCENTILE * 100)}: {threshold}")
print("Exporting hot_video_predictions.csv ...")

write_single_csv(output_df, OUTPUT_FILE)

print(f"Saved: {OUTPUT_FILE}")

spark.stop()
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_timestamp
import os

# Đường dẫn tuyệt đối
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DELTA_PATH    = os.path.join(BASE_DIR, "data", "delta", "raw_video_logs")
CLEAN_DELTA_PATH  = os.path.join(BASE_DIR, "data", "delta", "clean_video_logs")
CHECKPOINT_PATH   = os.path.join(BASE_DIR, "data", "delta", "checkpoints", "clean_video_logs")

# 1. SparkSession
spark = SparkSession.builder \
    .appName("CleanLogs") \
    .config(
    "spark.jars.packages",
    "io.delta:delta-spark_2.12:3.2.1"
    ) \
    .config("spark.sql.extensions",
            "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.sql.shuffle.partitions", "4") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# 2. Đọc raw Delta dạng stream
print(f"Đọc raw Delta từ: {RAW_DELTA_PATH}")
df_raw = spark.readStream \
    .format("delta") \
    .option("ignoreChanges", "true") \
    .load(RAW_DELTA_PATH)

# 3. Làm sạch & chọn đúng 9 cột
df_clean = (
    df_raw
    .withColumn("event_time", to_timestamp(col("event_time")))
    .filter(col("user_id").isNotNull())
    .filter(col("video_id").isNotNull())
    .filter(col("duration") > 0)
    .filter(col("watch_time").isNotNull() & (col("watch_time") >= 0))
    .withColumn("watch_ratio", col("watch_time") / col("duration"))
    .filter(col("watch_ratio").between(0, 1))
    .select(
    col("event_time"),
    col("user_id").cast("string"),
    col("video_id").cast("string"),
    col("watch_time"),
    col("duration"),
    col("watch_ratio"),
    col("is_click"),
    col("is_like"),
    col("is_share")
    )
)

# 4. Ghi clean Delta
print(f"Ghi clean Delta tại: {CLEAN_DELTA_PATH}")
query = df_clean.writeStream \
    .format("delta") \
    .option("path", CLEAN_DELTA_PATH) \
    .option("checkpointLocation", CHECKPOINT_PATH) \
    .outputMode("append") \
    .trigger(availableNow=True) \
    .start()

query.awaitTermination()
print(" clean_video_logs ghi xong!")

# 5. Kiểm tra nhanh
df_result = spark.read.format("delta").load(CLEAN_DELTA_PATH)
total = df_result.count()
print(f"Tổng dòng trong clean_video_logs: {total:,}")
df_result.printSchema()
df_result.show(5, truncate=False)
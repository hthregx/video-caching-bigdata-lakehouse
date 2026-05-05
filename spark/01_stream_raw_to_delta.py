from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import (
    StructType, StructField,
    StringType, LongType, DoubleType, IntegerType
)
import os


# Đường dẫn tuyệt đối (tránh lỗi relative path)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DELTA_PATH   = os.path.join(BASE_DIR, "data", "delta", "raw_video_logs")
CHECKPOINT_PATH  = os.path.join(BASE_DIR, "data", "delta", "checkpoints", "raw_video_logs")


# 1. SparkSession  — BẮT BUỘC khai báo packages
#    (thiếu phần này Kafka + Delta sẽ không load)

spark = SparkSession.builder \
    .appName("KafkaToDelta") \
    .config("spark.sql.extensions",
            "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.sql.shuffle.partitions", "4") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")


# 2. Schema — dùng LongType cho user_id / video_id
#    (KuaiRand dùng ID lớn, IntegerType sẽ tràn số)

schema = StructType([
    StructField("event_time",  StringType(),  True),
    StructField("user_id",     LongType(),    True),
    StructField("video_id",    LongType(),    True),
    StructField("watch_time",  DoubleType(),  True),
    StructField("duration",    DoubleType(),  True),
    StructField("watch_ratio", DoubleType(),  True),
    StructField("is_click",    IntegerType(), True),
    StructField("is_like",     IntegerType(), True),
    StructField("is_share",    IntegerType(), True),
])


# 3. Đọc Kafka

df_kafka = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "video_logs") \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .option("maxOffsetsPerTrigger", "10000") \
    .load()


# 4. Parse JSON

df_parsed = (
    df_kafka
    .selectExpr("CAST(value AS STRING) AS value")
    .select(from_json(col("value"), schema).alias("data"))
    .select("data.*")
    .withColumn("watch_time", col("watch_time").cast("double")) \
    .withColumn("duration", col("duration").cast("double"))
)


# 5. Ghi Delta RAW — trigger(availableNow=True)
#    Xử lý hết toàn bộ offset hiện có rồi TỰ DỪNG
#    (không dùng trigger này thì script chạy mãi mãi)

print(f" Ghi raw Delta tại: {RAW_DELTA_PATH}")

query = df_parsed.writeStream \
    .format("delta") \
    .option("path", RAW_DELTA_PATH) \
    .option("checkpointLocation", CHECKPOINT_PATH) \
    .outputMode("append") \
    .trigger(availableNow=True) \
    .start()

query.awaitTermination()
print(" raw_video_logs ghi xong!")
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import *

spark = SparkSession.builder \
    .appName("Silver Layer Transform") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

schema = StructType([
    StructField("event_time", StringType(), True),
    StructField("user_id", IntegerType(), True),
    StructField("video_id", IntegerType(), True),
    StructField("watch_time", DoubleType(), True),
    StructField("duration", DoubleType(), True),
    StructField("watch_ratio", DoubleType(), True),
    StructField("is_click", IntegerType(), True),
    StructField("is_like", IntegerType(), True),
    StructField("is_share", IntegerType(), True)
])

df = spark.read.format("delta").load("/home/asus/delta/raw_video_logs")

silver_df = df.select(
    from_json(col("raw_data"), schema).alias("data"),
    col("timestamp")
).select(
    "data.*",
    "timestamp"
)

silver_df = silver_df.na.fill({
    "watch_ratio": 0.0,
    "duration": 0.0
})

silver_df.write \
    .format("delta") \
    .mode("overwrite") \
    .save("/home/asus/delta/clean_video_logs")

print("Silver Layer created successfully!")

silver_df.show(20, False)

spark.stop()


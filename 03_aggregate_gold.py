from pyspark.sql import SparkSession
from pyspark.sql.functions import count, sum, avg, round
from delta import configure_spark_with_delta_pip

builder = SparkSession.builder \
    .appName("GoldAggregation") \
    .master("local[*]") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")

spark = configure_spark_with_delta_pip(builder).getOrCreate()

# Đọc dữ liệu từ Silver Layer
df = spark.read.format("delta").load("/home/asus/delta/silver_video_logs")

# Tổng hợp theo video_id
gold_df = df.groupBy("video_id").agg(
    count("*").alias("total_views"),
    sum("is_click").alias("total_clicks"),
    round(avg("watch_ratio"), 4).alias("avg_watch_ratio")
)

# Ghi Gold Layer
gold_df.write.format("delta") \
    .mode("overwrite") \
    .save("/home/asus/delta/gold_video_metrics")

print("Gold layer created successfully!")

gold_df.show(20, False)

spark.stop()

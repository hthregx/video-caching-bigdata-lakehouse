from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip

builder = SparkSession.builder \
    .appName("ExportDeltaToCSV") \
    .master("local[*]") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")

spark = configure_spark_with_delta_pip(builder).getOrCreate()

# =========================
# READ DELTA (đúng path)
# =========================
raw_df = spark.read.format("delta").load("/home/asus/delta/raw_video_logs")
clean_df = spark.read.format("delta").load("/home/asus/delta/clean_video_logs")

# =========================


# =========================
# EXPORT CSV  
# =========================
raw_df.coalesce(1).write.mode("overwrite").option("header", True).csv("data/csv/raw_video_logs_single")
clean_df.coalesce(1).write.mode("overwrite").option("header", True).csv("data/csv/clean_video_logs_single")

print("Export CSV done!")

spark.stop()

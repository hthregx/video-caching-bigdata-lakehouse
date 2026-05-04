from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip

builder = SparkSession.builder \
    .appName("ExportDeltaToCSV") \
    .master("local[*]") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")

spark = configure_spark_with_delta_pip(builder).getOrCreate()

# Read Delta
raw_df = spark.read.format("delta").load("/home/asus/delta/raw_video_logs")
clean_df = spark.read.format("delta").load("/home/asus/delta/clean_video_logs")

# Export CSV (gộp 1 file)
raw_df.coalesce(1).write.mode("overwrite").option("header", "true") \
    .csv("delta/csv/raw_video_logs")

clean_df.coalesce(1).write.mode("overwrite").option("header", "true") \
    .csv("delta/csv/clean_video_logs")

print("Export CSV done!")

spark.stop()

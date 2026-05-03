from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from delta import configure_spark_with_delta_pip

builder = SparkSession.builder \
    .appName("KafkaToDeltaRaw") \
    .master("local[*]") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")

spark = configure_spark_with_delta_pip(builder).getOrCreate()

df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "video_logs") \
    .option("startingOffsets", "earliest") \
    .load()

json_df = df.selectExpr(
    "CAST(value AS STRING) as raw_data",
    "timestamp"
)

query = json_df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/home/asus/delta/checkpoints/raw_video_logs") \
    .start("/home/asus/delta/raw_video_logs")

query.awaitTermination()

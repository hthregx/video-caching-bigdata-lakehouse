from pyspark.sql import SparkSession
import os
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DELTA_DIR = os.path.join(BASE_DIR, "data", "delta", "clean_video_logs")
CSV_OUTPUT_FILE = os.path.join(BASE_DIR, "outputs", "charts", "clean_video_logs.csv")
TEMP_CSV_DIR = os.path.join(BASE_DIR, "outputs", "charts", "temp_csv")

spark = SparkSession.builder \
    .appName("ExportCSVDirect") \
    .getOrCreate()

print(f"Đọc file Parquet từ: {CLEAN_DELTA_DIR}")
df = spark.read.parquet(CLEAN_DELTA_DIR)

total = df.count()
print(f"Tổng số dòng: {total}")

os.makedirs(TEMP_CSV_DIR, exist_ok=True)

df.coalesce(1).write \
    .mode("overwrite") \
    .option("header", True) \
    .csv(TEMP_CSV_DIR)

part_files = [f for f in os.listdir(TEMP_CSV_DIR) if f.startswith('part-') and f.endswith('.csv')]
if part_files:
    src = os.path.join(TEMP_CSV_DIR, part_files[0])
    if os.path.exists(CSV_OUTPUT_FILE):
        os.remove(CSV_OUTPUT_FILE)
    shutil.move(src, CSV_OUTPUT_FILE)
    print(f" Đã xuất CSV thành công: {CSV_OUTPUT_FILE}")
else:
    print(" Không tìm thấy file CSV sau khi ghi!")

# Dọn dẹp thư mục tạm
shutil.rmtree(TEMP_CSV_DIR, ignore_errors=True)
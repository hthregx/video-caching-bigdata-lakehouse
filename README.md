<<<<<<< HEAD
# Big Data Lakehouse for Real-time Video Caching Optimization

## Project Title

Xây dựng hệ thống Big Data Lakehouse phân tích log thời gian thực nhằm dự đoán xu hướng video và tối ưu chiến lược caching cho nền tảng video streaming.

## Architecture

KuaiRand-1K → Kafka → Spark Structured Streaming → Delta Lake → Hot Video Prediction → Cache Recommendation → Evaluation

## Team Roles

- Member 1: Data + Kafka Producer
- Member 2: Spark Streaming + Delta Lake
- Member 3: Feature Engineering + Hot Video Prediction
- Member 4: Cache Recommendation + Evaluation + Report
=======
# BigData Project - Video Caching Pipeline

## Thành viên
- Người 1: Data + Kafka Producer
- Người 2: Kafka + Spark Streaming + Delta Lake
- Người 3: Feature Engineering
- Người 4: Evaluation & Report

## Cấu trúc thư mục
- spark/ : Script Spark xử lý streaming
- kafka/ : Script producer và công cụ gửi dữ liệu
- data/ : Dữ liệu mẫu và kết quả

## Cách chạy pipeline
1. Khởi động Kafka, tạo topic video_logs
2. Gửi dữ liệu mẫu: cat data/sample/kuairand_logs_100k.csv | python3 kafka/csv_to_json.py | kafka-console-producer.sh ...
3. Chạy từng bước Spark: spark-submit ...
4. Lấy kết quả: data/processed/clean_video_logs.csv
>>>>>>> origin/feature/spark-delta-streaming

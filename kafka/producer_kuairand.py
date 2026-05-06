
import pandas as pd
import json
import time
import argparse
from kafka import KafkaProducer

KAFKA_BROKER = "localhost:9092"
TOPIC        = "video_logs"

def create_producer():
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",           # đảm bảo message được ghi
        retries=3,            # thử lại nếu lỗi
    )
    print(f" Kết nối Kafka thành công: {KAFKA_BROKER}")
    return producer

def load_data(file_path):
    print(f" Đang load: {file_path}")
    df = pd.read_csv(file_path)
    print(f" Load xong: {len(df):,} dòng")
    return df

def row_to_message(row):
    return {
        "event_time": str(row["event_time"]),
        "user_id":    int(row["user_id"]),
        "video_id":   int(row["video_id"]),
        "watch_time": round(float(row["watch_time"]), 3),
        "duration":   round(float(row["duration"]), 3),
        "watch_ratio": round(float(row["watch_ratio"]), 4)
                       if pd.notna(row["watch_ratio"]) else None,
        "is_click":   int(row["is_click"]),
        "is_like":    int(row["is_like"]),
        "is_share":   int(row["is_share"]),
    }

def produce(file_path, delay=0.01, limit=None):
    producer = create_producer()
    df = load_data(file_path)

    if limit:
        df = df.head(limit)
        print(f" Chỉ gửi {limit:,} dòng đầu (chế độ test)")

    total   = len(df)
    success = 0
    errors  = 0

    print(f"\n Bắt đầu gửi {total:,} messages → topic '{TOPIC}'")
    print(f"   Delay giữa messages: {delay}s")
    print("-" * 50)

    start_time = time.time()

    for i, (_, row) in enumerate(df.iterrows()):
        try:
            msg = row_to_message(row)
            key = str(msg["video_id"]).encode("utf-8")
            producer.send(TOPIC, value=msg, key=key)
            success += 1

            if (i + 1) % 1000 == 0:
                elapsed = time.time() - start_time
                rate    = (i + 1) / elapsed
                print(f"   [{i+1:>7,}/{total:,}] "
                      f" {success:,} ok | "
                      f" {errors} lỗi | "
                      f" {rate:.0f} msg/s")

            time.sleep(delay)

        except Exception as e:
            errors += 1
            print(f"    Lỗi dòng {i}: {e}")

    producer.flush()
    producer.close()

    elapsed = time.time() - start_time
    print("-" * 50)
    print(f" Hoàn thành!")
    print(f"   Tổng gửi  : {success:,} messages")
    print(f"   Lỗi       : {errors}")
    print(f"   Thời gian  : {elapsed:.1f}s")
    print(f"   Tốc độ    : {success/elapsed:.0f} msg/s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KuaiRand Kafka Producer")
    parser.add_argument(
        "--file",
        default="data/sample/kuairand_logs_100k.csv",
        help="Đường dẫn file CSV cần gửi"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Delay giữa các messages (giây), mặc định 0 = nhanh nhất"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Giới hạn số dòng gửi (để test nhanh)"
    )
    args = parser.parse_args()

    produce(
        file_path=args.file,
        delay=args.delay,
        limit=args.limit,
    )

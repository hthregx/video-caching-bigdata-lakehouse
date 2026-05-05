
import json
from kafka import KafkaConsumer

# ── Cấu hình ──────────────────────────────────────────────────────
KAFKA_BROKER = "localhost:9092"
TOPIC        = "video_logs"
MAX_MESSAGES = 10   

# ── Khởi tạo Consumer ─────────────────────────────────────────────
consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    auto_offset_reset="earliest",    
    enable_auto_commit=False,
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    consumer_timeout_ms=5000,        
)

print(f" Kết nối Kafka: {KAFKA_BROKER}")
print(f" Đọc topic: '{TOPIC}' (tối đa {MAX_MESSAGES} messages)")
print("=" * 60)

count = 0
for msg in consumer:
    count += 1
    data = msg.value

    print(f"\n[Message #{count}]")
    print(f"  Partition : {msg.partition} | Offset: {msg.offset}")
    print(f"  event_time: {data.get('event_time')}")
    print(f"  user_id   : {data.get('user_id')}")
    print(f"  video_id  : {data.get('video_id')}")
    print(f"  watch_time: {data.get('watch_time')}s")
    print(f"  duration  : {data.get('duration')}s")
    print(f"  watch_ratio: {data.get('watch_ratio')}")
    print(f"  is_click  : {data.get('is_click')} | "
          f"is_like: {data.get('is_like')} | "
          f"is_share: {data.get('is_share')}")

    if count >= MAX_MESSAGES:
        break

consumer.close()

print("\n" + "=" * 60)
print(f" Đọc được {count} messages từ topic '{TOPIC}'")
print(" Kafka hoạt động đúng! Schema hợp lệ.")
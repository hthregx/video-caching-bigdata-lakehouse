#!/usr/bin/env python3
import csv
import json
import sys

reader = csv.DictReader(sys.stdin)
for row in reader:
    # Xây dựng dict giống schema Kafka producer
    msg = {
        "event_time": row["event_time"],
        "user_id": int(row["user_id"]),
        "video_id": int(row["video_id"]),
        "watch_time": float(row["watch_time"]),
        "duration": float(row["duration"]),
        "watch_ratio": float(row["watch_ratio"]) if row.get("watch_ratio") and row["watch_ratio"] != '' else 0.0,
        "is_click": int(row["is_click"]),
        "is_like": int(row["is_like"]),
        "is_share": int(row["is_share"])
    }
    sys.stdout.write(json.dumps(msg) + '\n')
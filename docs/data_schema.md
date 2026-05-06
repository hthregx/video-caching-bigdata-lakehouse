# Data Schema – KuaiRand-1K Pipeline

**Người phụ trách:** Người 1  
**Cập nhật:** 2026-04-29  
**Nguồn dữ liệu:** KuaiRand-1K (`log_standard_4_22_to_5_08_1k.csv`)

---

## 1. Schema log chuẩn (dùng chung toàn nhóm)

Đây là schema output của Người 1, là input của Người 2 (Spark Streaming).

| Cột | Kiểu | Mô tả | Ví dụ |
|-----|------|-------|-------|
| `event_time` | string | Thời điểm tương tác (UTC) | `"2022-04-22 14:15:15"` |
| `user_id` | int | ID người dùng | `123` |
| `video_id` | int | ID video | `554434` |
| `watch_time` | float | Thời gian xem thực tế (giây) | `18.5` |
| `duration` | float | Thời lượng video (giây) | `30.0` |
| `watch_ratio` | float | Tỷ lệ xem `[0.0–1.0]` | `0.617` |
| `is_click` | int | User có click không (0/1) | `1` |
| `is_like` | int | User có like không (0/1) | `0` |
| `is_share` | int | User có share không (0/1) | `0` |

### Format JSON gửi lên Kafka:
```json
{
  "event_time": "2022-04-22 14:15:15.200000",
  "user_id": 0,
  "video_id": 554434,
  "watch_time": 3.925,
  "duration": 7.833,
  "watch_ratio": 0.501,
  "is_click": 0,
  "is_like": 0,
  "is_share": 0
}
```

---

## 2. Các file bàn giao

| File | Dòng | Size | Dùng cho |
|------|------|------|----------|
| `data/sample/kuairand_logs_100k.csv` | 100,000 | 6.7 MB | Test nhanh |
| `data/sample/kuairand_logs_500k.csv` | 500,000 | 33.4 MB | Demo |
| `data/sample/kuairand_logs_1000k.csv` | 1,000,000 | 66.7 MB | Benchmark |
| `data/sample/kuairand_logs_full_clean.csv` | 6,597,399 | 440 MB | Production |


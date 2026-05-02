# Feature Engineering và Hot Video Prediction

## Mục tiêu

Mục tiêu của bước feature engineering là chuyển dữ liệu log đã làm sạch thành các đặc trưng có ý nghĩa theo từng video và từng cửa sổ thời gian. Các đặc trưng này được sử dụng để đánh giá mức độ thịnh hành của video và hỗ trợ bước cache recommendation.

## Input

Bảng đầu vào là clean_video_logs, gồm các cột chính:

event_time: thời điểm phát sinh log.
user_id: mã người dùng.
video_id: mã video.
watch_time: thời lượng người dùng đã xem video.
duration: độ dài của video.
watch_ratio: tỷ lệ watch_time / duration.
is_click: trạng thái click hoặc xem video.
is_like: trạng thái người dùng thích video.
is_share: trạng thái người dùng chia sẻ video.

## Các feature được trích xuất

views_count: số lượt xem của video trong một cửa sổ thời gian.
unique_users: số người dùng duy nhất đã xem video.
avg_watch_time: thời lượng xem trung bình.
avg_watch_ratio: tỷ lệ xem trung bình so với độ dài video.
like_count: tổng số lượt thích.
share_count: tổng số lượt chia sẻ.
engagement_count: tổng số tương tác, được tính bằng like_count + share_count.
growth_rate: tốc độ tăng trưởng lượt xem của video so với cửa sổ thời gian trước đó.

## Công thức growth_rate

growth_rate = (views_current_window - views_previous_window) / views_previous_window

Nếu views_previous_window bằng 0, growth_rate được gán bằng views_current_window để tránh lỗi chia cho 0.

## Công thức hot_score

hot_score = 0.4 × views_score + 0.25 × growth_score + 0.2 × watch_ratio_score + 0.15 × engagement_score

Trong đó:

views_score phản ánh mức độ phổ biến hiện tại của video.
growth_score phản ánh tốc độ tăng trưởng lượt xem.
watch_ratio_score phản ánh chất lượng xem hoặc mức độ giữ chân người xem.
engagement_score phản ánh mức độ tương tác của người dùng với video.

## Cách xác định video hot

Nếu hot_score >= 0.7, video được gán nhãn HOT.
Nếu hot_score < 0.7, video được gán nhãn NOT_HOT.

## Output

Bảng hot_video_predictions gồm các cột:

video_id
window_start
window_end
views_count
unique_users
avg_watch_ratio
growth_rate
engagement_count
hot_score
predicted_hot
hot_label

Kết quả này được chuyển sang bước cache recommendation để quyết định video nào nên được đưa vào cache.
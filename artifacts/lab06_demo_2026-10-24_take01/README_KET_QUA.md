# Video demo và ảnh báo cáo — Bài 6

Ngày quay: 24/10/2026. Người dùng thực hiện cử chỉ thật trước webcam; hệ thống ROS 2 điều khiển TurtleBot 4 trong Gazebo. Trình ghi chỉ subscribe dữ liệu ROS, không publish cử chỉ hoặc vận tốc giả.

## File nộp chính

- `demo_turtlebot4_gestures.mp4`: H.264, 1920×1080, 20 fps, khoảng 3 phút, không có âm thanh. Chỉ cắt viền tab trình duyệt/thanh dock và thêm viền đen để giữ khung 1080p; giữ nguyên toàn bộ thứ tự demo, kể cả các đoạn thử lại.
- `report_images/`: các hình đã chọn để viết báo cáo, gồm ảnh webcam nhận diện sáu cử chỉ, ảnh các trạng thái điều khiển và đồ thị odometry thực tế. Đồ thị có cả PNG và PDF.
- `results.csv`, `summary.json`: tổng hợp kết quả các cảnh.
- `events.jsonl`, `odometry.jsonl`: dữ liệu thực nghiệm để đối chiếu và phân tích.
- `video_metadata.json`, `decode_check.log`: thông số video và kết quả kiểm tra giải mã. Log kiểm tra trống nghĩa là ffmpeg không báo lỗi giải mã.

Video WebM gốc và các ảnh chụp tự động chưa chọn nằm trong thư mục lượt quay đầy đủ, không đưa vào gói ZIP để giảm dung lượng.

## Nội dung đã ghi

1. Pointing Up chọn hành vi; robot đứng yên khi chưa xác nhận. Thumb Up xác nhận, robot thực hiện đủ bốn chu kỳ tiến–lùi và báo COMPLETED.
2. Victory chọn vòng tròn; Thumb Up xác nhận; robot đi đủ một vòng và báo COMPLETED.
3. Nhận Wave từ chuyển động bàn tay thật; chọn greeting, xác nhận rồi hoàn thành các pha quay chào.
4. Trong lúc chạy, Open Palm đưa robot về STOPPED.
5. Trong lúc chạy, Closed Fist đưa robot về IDLE.
6. Khi tay ra khỏi webcam, robot dừng với SIGNAL_LOST.

Video có một lần lựa chọn Wave bị xóa khi kết quả trở về Open Palm và một lần SIGNAL_LOST ngoài ý muốn lúc chuyển sang bàn tay mở. Sau đó cả hai cảnh được làm lại thành công. Giữ nguyên các đoạn này để phản ánh đúng thực nghiệm. Không coi sáu cảnh cuối đạt là tỷ lệ nhận diện 100% trên một bộ dữ liệu.

Đoạn kiểm tra bổ sung “giơ Thumb Up sau STOPPED/SIGNAL_LOST nhưng không chọn lại” chưa được thực hiện thành một cảnh riêng trong lượt quay này; không ghi trong báo cáo rằng video đã minh chứng thao tác đó.

## Gợi ý sử dụng hình

| File | Nội dung/chú thích gợi ý |
|---|---|
| `01_ready_overview.png` | Toàn cảnh mô phỏng và cửa sổ nhận diện trước demo |
| `02_selected_before_confirmation.png` | Chọn tiến–lùi, chờ xác nhận; robot chưa chuyển động |
| `03_backforth_running.png` | Hành vi tiến–lùi đang thực hiện |
| `04_backforth_completed.png` | Hành vi tiến–lùi hoàn thành |
| `05_circle_running.png` | Robot đang thực hiện vòng tròn |
| `06_circle_completed.png` | Hoàn thành vòng tròn |
| `07_greeting_running.png` | Robot thực hiện động tác chào |
| `08_greeting_completed.png` | Hoàn thành động tác chào |
| `09_open_palm_stopped.png` | Trạng thái STOPPED sau lệnh Open Palm; ở khung hình này nhãn đã dao động về None |
| `10_closed_fist_idle.png` | Closed Fist hủy chuyển động và đưa robot về IDLE |
| `11_signal_lost.png` | Không có bàn tay, robot dừng với SIGNAL_LOST |
| `12_unplanned_signal_lost.png` | Đoạn mất tín hiệu ngoài ý muốn, dùng cho phần phân tích hạn chế |
| `13_wave_selection_reset.png` | Khung hình tại đoạn lựa chọn Wave bị xóa; đối chiếu video/log trước khi chú thích |
| `gesture_*.png` | Các mẫu nhận diện thực tế, có landmarks và confidence |
| `odom_1.png` / `odom_1.pdf` | Vị trí x tương đối theo thời gian, thể hiện bốn chu kỳ tiến–lùi |
| `odom_2.png` / `odom_2.pdf` | Quỹ đạo tròn đo từ /odom, không phải đường tròn vẽ theo mô hình |
| `odom_3.png` / `odom_3.pdf` | Góc quay tương đối trong động tác chào |

`gesture_*.png` được lưu ở lúc đầu tiên nhận được mỗi nhãn; trạng thái robot trong ảnh có thể đang ở bước trước vì lệnh chưa được xử lý/xác nhận. Không dùng riêng ảnh này để khẳng định hành vi đã hoàn thành. Confidence trên một ảnh không phải tỷ lệ chính xác của hệ thống. Confidence của Wave là điểm Open Palm kết hợp thuật toán chuyển động, không phải điểm của một mô hình Wave riêng.

Mốc thời gian trong CSV xấp xỉ thời điểm cảnh đạt; có thể chênh một ít so với khung hình hiển thị do luồng camera/GUI. Thời gian trên đồ thị là đồng hồ thực trong lượt quay, không phải thời gian mô phỏng.

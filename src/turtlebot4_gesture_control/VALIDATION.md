# Kiểm chứng Bài tập 6

Ngày kiểm tra: 21/10/2026. Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic, Python 3.12. Kết quả dưới đây phân biệt kiểm thử điều khiển bằng cử chỉ giả với nhận diện ảnh/webcam thật.

## Build và kiểm thử tự động

```bash
cd ~/tb4_ws
source src/turtlebot4_slam_nav/scripts/env.sh
colcon build --symlink-install --packages-up-to turtlebot4_gesture_control
colcon test --packages-select turtlebot4_gesture_control \
  --event-handlers console_direct+ --pytest-args -q
colcon test-result --test-result-base build/turtlebot4_gesture_control --verbose
ament_flake8 src/turtlebot4_gesture_control
```

- Build thành công; **18 tests, 0 errors, 0 failures, 0 skipped**.
- Flake8: 10 file Python, không phát hiện lỗi.
- Kiểm tra cú pháp Python và script cài đặt thành công.
- Các test bao gồm chờ xác nhận, chống lặp, cử chỉ không ổn định, dừng/hủy, mất tín hiệu, mất sensor, vật cản trước/sau, đủ tám lượt tiến/lùi, hoàn thành vòng tròn/chào bằng odom và nhận Wave theo thời gian.
- Test launch kiểm tra bridge dùng đúng tên world `gesture_arena`, vị trí dock trong Gazebo khớp TF và nằm ở góc `(6, 6)`.

## MediaPipe với ảnh mẫu chính thức

Model: `gesture_recognizer.task`, MediaPipe 0.10.21, NumPy 1.26.4, OpenCV hệ thống 4.6.0.

| Ảnh mẫu | Nhãn trả về | Confidence |
|---|---|---:|
| `thumb_up.jpg` | Thumb_Up | 0,744 |
| `fist.jpg` | Closed_Fist | 0,900 |
| `victory.jpg` | Victory | 0,775 |
| `pointing_up.jpg` | Pointing_Up | 0,830 |

Đây là điểm confidence trên bốn ảnh cụ thể, **không phải tỷ lệ chính xác** trên webcam hoặc tập dữ liệu đánh giá. Ảnh lấy từ kho [MediaPipe assets của Google](https://storage.googleapis.com/mediapipe-assets/thumb_up.jpg); dữ liệu chi tiết ở `log/lab06_validation/mediapipe_smoke.json`.

Wave dùng nhãn AI Open_Palm kết hợp chuỗi chuyển động ngang; không phải một class có sẵn của model. Test logic kiểm tra bàn tay mở đứng yên, rung nhẹ và một lần quét ngang không được nhận thành Wave.

## Webcam thật và cửa sổ OpenCV

Chạy node trên camera `/dev/video0`, bật cửa sổ OpenCV, trong một ROS domain riêng để không điều khiển robot trong lần kiểm tra này.

- Tiến trình kết thúc bình thường, mã thoát 0.
- Nhận 85 message debug có kết quả xử lý ảnh còn mới.
- Nhận 84 ảnh ROS có chú thích, kích thước 640 × 600 (ảnh camera và vùng trạng thái).
- Các nhãn quan sát được: None, Open_Palm, Pointing_Up, Victory.
- Không lưu ảnh webcam. Không coi lần kiểm tra ngắn này là demo người thật đầy đủ sáu cử chỉ.

Kết quả: `log/lab06_validation/webcam_gui_results.json`, log: `webcam_gui.log`.
SS
## Mô phỏng chuyển động trong Gazebo bằng tín hiệu cử chỉ giả

Gazebo được chạy trên domain/partition kiểm thử riêng, với robot, odom, scan, dock status và controller chính thức. Bộ kiểm thử publish chuỗi String vào `/detected_gesture`, đồng thời đọc trạng thái, odom và TwistStamped. Camera không làm nguồn điều khiển trong kiểm thử này.

Lượt kiểm thử Gazebo được ghi dưới đây sử dụng tốc độ ban đầu: 0,12 m/s và xoay chào 0,45 rad/s. Cấu hình hiện tại đã tăng lên 0,24 m/s và 0,90 rad/s; các test logic kiểm tra lại cấu hình mới, chưa chạy lại lượt Gazebo đầy đủ ở tốc độ mới.

| Trường hợp | Kết quả quan sát |
|---|---|
| Chọn hành vi, chưa Thumb Up | SELECTED; `/cmd_vel` bằng 0 |
| Wave → Thumb Up | COMPLETED; quan sát đủ ba pha quay |
| Pointing Up → Thumb Up | COMPLETED; quan sát đủ tám lượt, tức bốn chu kỳ tiến–lùi |
| Victory → Thumb Up | COMPLETED; hoàn thành vòng tròn theo odometry |
| Open Palm khi đang chạy | STOPPED; `/cmd_vel` bằng 0 |
| Closed Fist khi đang chạy | IDLE; `/cmd_vel` bằng 0 |
| Ngừng publish tín hiệu khi đang chạy | SIGNAL_LOST; `/cmd_vel` bằng 0 |

Kết quả cuối: **PASSED**, không có bumper/obstacle stop trong lượt kiểm thử hoàn chỉnh với dock ở góc sân. Dữ liệu: `log/lab06_validation/gazebo_results.json`; log: `integration.log`, `behavior.log`, `simulation.log`.

Cần quay riêng video với người thực hiện cả sáu cử chỉ, webcam và Gazebo hiển thị song song theo [README](README.md). Các bài kiểm thử trên không thay thế nội dung video này.

## Điều chỉnh Wave sau phản hồi khi dùng webcam

Wave theo dõi trung bình vị trí ngang của bốn đầu ngón tay, nhận tối thiểu hai lần đảo chiều trong 3 giây với biên độ chuẩn hóa 0,09 chiều rộng ảnh. Lịch sử chịu được một khoảng nhận diện không chắc chắn ngắn; trong khoảng đó vẫn publish None. Khi không có chuyển động đáng kể trong hơn 0,25 giây, lịch sử Wave được xóa và bàn tay mở đứng yên trở lại Open_Palm. Hai test bổ sung kiểm tra vẫy chậm có một frame không chắc chắn vẫn chọn được hành vi và chuyển động Wave cũ không che lệnh dừng khi tay đứng yên. Chưa kiểm chứng lại bằng một lượt vẫy tay thật của người dùng sau chỉnh sửa này.

## Khắc phục GUI đóng do segmentation fault — 22/10/2026

Log phiên người dùng ghi GUI Ogre2 thoát mã 139; server chỉ dừng sau khi terminal nhận Ctrl+C. Log Ogre2 có lỗi material/shader. Stack trace Qt được cung cấp chưa đủ để xác định chính xác lỗi C++ gây crash.

Bài 6 chuyển mặc định GUI sang Ogre1; server và LiDAR tiếp tục dùng Ogre2. Chỉ thay launch Bài 6, không đổi mặc định các launch bài trước. Thêm `gui.launch.py` để kết nối lại cửa sổ với server đang chạy. Đây là phương án thay renderer theo [troubleshooting Gazebo Harmonic](https://gazebosim.org/docs/harmonic/troubleshooting/#unable-to-create-the-rendering-window).

Kiểm thử trên domain riêng 93:

- GUI Ogre1 còn chạy sau 359,4 giây, không tự thoát trong khoảng theo dõi. Sau đó chủ động đóng riêng GUI để thử kết nối lại.
- Trong mẫu 8 giây: 346 bản scan và 367 bản odom; scan cuối có 640/640 giá trị hợp lệ.
- Mở lại bằng `gui.launch.py` thành công. Đồng hồ mô phỏng tăng từ 258,16 đến 271,25 giây trong mẫu theo dõi, không reset khi GUI kết nối lại.
- Build, 18 tests tự động và Flake8 (10 file Python) đều đạt.

Dữ liệu ở `log/lab06_gui_validation/`: `uptime.json`, `sensors.json`, `reconnect.json`, `ogre.log`, `reopen_gui.log`. Kiểm thử này xác nhận tiến trình GUI và dữ liệu mô phỏng trong thời gian trên; chưa chứng minh loại trừ mọi tình huống crash khi tương tác lâu dài.

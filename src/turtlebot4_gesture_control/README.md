# Bài tập 6 — Điều khiển TurtleBot 4 bằng cử chỉ tay

Webcam laptop → MediaPipe Gesture Recognizer → `/detected_gesture` (`String`) → `robot_behavior_node` → `/cmd_vel` (`TwistStamped`, ROS 2 Jazzy).

## Cử chỉ và quy tắc điều khiển

| Cử chỉ | Kết quả |
|---|---|
| Wave | Chọn hành vi xoay trái–phải chào; chờ xác nhận |
| Pointing Up | Chọn tiến–lùi **4 chu kỳ**, mỗi chu kỳ một lượt tiến và một lượt lùi |
| Victory | Chọn đi một vòng tròn |
| Thumb Up | Xác nhận hành vi đã chọn; không chọn thì không chạy |
| Open Palm | Dừng, xóa lựa chọn ngay khi nhận được tín hiệu tin cậy |
| Closed Fist | Hủy hành vi, trở về chờ ngay |

Các cử chỉ chọn/xác nhận phải ổn định 0,35 giây. Giữ nguyên cử chỉ không kích hoạt lại liên tục. Trong lúc chạy, tiếp tục giữ tay trong khung hình với một cử chỉ được nhận diện (dễ nhất là giữ Thumb Up). Mất tay/nhận diện không tin cậy/mất node camera sẽ dừng sau timeout; không tự tiếp tục khi tay xuất hiện lại, phải chọn và xác nhận lại.

**Wave không phải nhãn có sẵn của model.** Năm nhãn tĩnh dùng AI gồm `Pointing_Up`, `Victory`, `Thumb_Up`, `Open_Palm`, `Closed_Fist`. Wave kết hợp AI nhận bàn tay mở với chuyển động ngang của đầu ngón tay có ít nhất hai lần đảo chiều trong 3 giây. Confidence hiển thị khi Wave là confidence bàn tay mở, không phải điểm từ một bộ phân loại Wave đã huấn luyện riêng. Xòe tay đứng yên vẫn là STOP; để chọn Wave, vẫy tay qua lại rõ sang trái–phải (độ rộng khoảng 1/5 khung hình webcam), chờ `SELECTED greeting` rồi đưa Thumb Up xác nhận.

## 1. Build và chuẩn bị — thực hiện một lần

Trong mỗi terminal mới:

```bash
cd ~/tb4_ws
export TB4_LAB_DOMAIN_ID=76
source src/turtlebot4_slam_nav/scripts/env.sh
export GZ_IP=127.0.0.1
```

Dừng phiên Nav2/teleop cũ trước khi chạy bài này. Dùng cùng domain trong mọi terminal.

```bash
colcon build --symlink-install --packages-up-to turtlebot4_gesture_control
source install/local_setup.bash
bash src/turtlebot4_gesture_control/scripts/setup_gesture.sh
```

Script tạo `.venv-gesture`, tải model chính thức `models/gesture_recognizer.task`, giữ riêng môi trường YOLO cũ. Dùng OpenCV hệ thống cùng NumPy 1.26.4. MediaPipe được cài `--no-deps` để tránh tải thêm wheel OpenCV/Qt; cảnh báo metadata thiếu `opencv-contrib-python` không đồng nghĩa thiếu module `cv2`, script kiểm tra import thực tế.

## 2. Terminal A — Gazebo, sân trống 16 × 16 m

```bash
ros2 launch turtlebot4_gesture_control arena.launch.py
```

World `gesture_arena` dùng robot và controller chính thức, không chạy AMCL/Nav2. Robot ở giữa sân rộng, có tường bao, không cần dùng map bài trước. Nếu GUI nặng:

```bash
ros2 launch turtlebot4_gesture_control arena.launch.py gazebo_gui:=false
```

GUI mặc định dùng Ogre1 (`gui_render_engine:=ogre`) để tránh đường render Ogre2 đang gặp crash trên máy này; server và LiDAR vẫn dùng Ogre2. Có thể chọn lại GUI Ogre2 bằng `gui_render_engine:=ogre2` khi cần so sánh.

Nếu chỉ cửa sổ GUI bị `Segmentation fault` nhưng server vẫn chạy, xòe tay cho robot dừng, giữ terminal mô phỏng đang chạy rồi mở terminal mới cùng domain 76 và nạp môi trường như mục 1:

```bash
ros2 launch turtlebot4_gesture_control gui.launch.py
```

Lệnh này chỉ mở lại cửa sổ, giữ nguyên vị trí robot và thời gian mô phỏng. Nếu đã Ctrl+C terminal mô phỏng khiến server dừng, chạy lại `arena.launch.py`. Tất cả terminal phải cùng `ROS_DOMAIN_ID=76`; thiếu `/scan`, `/odom` hoặc `/clock` ở domain của controller sẽ gây `NOT_READY`.

Trong terminal kiểm tra (sau khi nạp cùng môi trường):

```bash
ros2 topic info /cmd_vel -v
ros2 topic type /cmd_vel
ros2 topic hz /odom
ros2 topic hz /scan
```

Dừng từng lệnh `hz` bằng Ctrl+C sau khi kiểm tra. `/cmd_vel` trong Jazzy là `geometry_msgs/msg/TwistStamped`.

Robot xuất phát ở giữa sân, dock được đặt ở góc `(6, 6)` trong cả Gazebo và TF. **Không cần Undock hoặc lái robot ra khỏi dock.** Chờ controller được kích hoạt và `/scan`, `/odom` có dữ liệu rồi mở node hành vi.

## 3. Terminal B — node điều khiển hành vi

```bash
ros2 launch turtlebot4_gesture_control behavior.launch.py
```

Node đợi odom/scan còn mới, robot đã undocked và đồng hồ mô phỏng chạy. Khi có vật cản theo hướng chuyển động, bumper, mất sensor hoặc mất tín hiệu cử chỉ, node publish lệnh dừng và xóa hành vi đang chạy. Cần chọn/xác nhận lại, không tự chạy tiếp.

Thông số ở `config/behavior.yaml`: tốc độ thẳng 0,24 m/s, tốc độ xoay chào 0,90 rad/s, tiến/lùi 0,35 m mỗi lượt, vòng tròn bán kính 0,6 m. Khi chạy tròn, vận tốc góc là 0,40 rad/s để giữ đúng bán kính. Tốc độ lệnh đã tăng gấp đôi so với cấu hình ban đầu; tiến độ vẫn đo bằng odometry, không chỉ chờ thời gian cố định. Giới hạn timeout được đo bằng đồng hồ thực để vẫn dừng khi simulation bị pause.

Nếu đang mở node hành vi khi sửa tốc độ, dừng terminal B bằng Ctrl+C rồi chạy lại `ros2 launch turtlebot4_gesture_control behavior.launch.py` để nạp YAML mới.

## 4. Terminal C — webcam và MediaPipe

```bash
./.venv-gesture/bin/python -m \
  turtlebot4_gesture_control.gesture_recognition_node --ros-args \
  -p camera_index:=0 -p confidence:=0.65 -p max_fps:=15.0
```

Cửa sổ hiển thị landmarks, nhãn, confidence và trạng thái điều khiển. Dùng một tay, đủ sáng, tay nằm rõ trong khung hình. Nếu cần đổi webcam, đặt `camera_index:=1`. Hình webcam được lật gương để dễ thao tác.

Không có phím nào dùng để lái robot trong cửa sổ. Đóng cửa sổ hoặc Ctrl+C sẽ dừng node; node hành vi tự dừng khi mất heartbeat.

Theo dõi trong một terminal riêng (cũng nạp môi trường ở mục 1):

```bash
ros2 topic echo /detected_gesture
ros2 topic echo /robot_behavior_state --qos-durability transient_local
```

- `/detected_gesture`: một trong sáu tên cử chỉ, hoặc `None` nếu mất tay/không chắc chắn/ảnh đã cũ.
- `/robot_behavior_state`: JSON trạng thái, lựa chọn, tiến độ và lý do dừng.
- `/gesture_recognition/debug`: nhãn MediaPipe gốc, confidence và thời gian xử lý.
- `/gesture_recognition/image`: ảnh webcam có chú thích, có thể thêm Image trong RViz.

## 5. Terminal D — mở RViz và xem quỹ đạo robot

Mở terminal mới, nạp môi trường rồi chạy RViz:

```bash
cd ~/tb4_ws
export TB4_LAB_DOMAIN_ID=76
source src/turtlebot4_slam_nav/scripts/env.sh

ros2 run rviz2 rviz2 \
  -d "$(ros2 pkg prefix --share turtlebot4_slam_nav)/rviz/simulation.rviz" \
  --ros-args -p use_sim_time:=true
```

Cấu hình có sẵn hiển thị **RobotModel**, **Grid** và **LaserScan**. Trong bài cử chỉ, dùng **Fixed Frame = `odom`**, không cần load bản đồ hoặc chạy AMCL/Nav2.

Để thấy đường robot đã di chuyển:

1. Chọn **Add → By display type → Odometry → OK**.
2. Mở display **Odometry**, đặt **Topic = `/odom`**, **Reliability Policy = Best Effort**.
3. Đặt **Keep = 1000**, **Position Tolerance = 0.01**, **Angle Tolerance = 0.05** để giữ các vị trí/hướng đã đi qua.
4. Chọn **Shape = Arrow**, giảm chiều dài mũi tên nếu hình quá dày; chọn màu nổi bật như xanh lá.
5. Trong **Views**, chọn **TopDownOrtho**, cuộn chuột phóng to vùng robot chạy. Các mũi tên odometry tạo vệt quỹ đạo, đồng thời cho thấy hướng xoay khi robot chào.

Nhấn **Reset** trên RViz trước khi demo một hành vi mới nếu muốn xóa vệt cũ. Có thể **File → Save Config As** vào `~/tb4_ws/gesture_demo.rviz`; lần sau mở lại bằng:

```bash
ros2 run rviz2 rviz2 -d ~/tb4_ws/gesture_demo.rviz \
  --ros-args -p use_sim_time:=true
```

Khi quay video, bố trí **Gazebo bên trái**, **RViz bên phải phía trên**, **webcam bên phải phía dưới**. Quỹ đạo là dữ liệu odometry robot đã đi qua; thao tác trên RViz chỉ để quan sát. Robot vẫn nhận lệnh từ cử chỉ tay.

## 6. Thứ tự demo cần quay

1. Cho thấy webcam có nhãn, Gazebo có robot trong sân trống và RViz có quỹ đạo odometry; `ready=true`.
2. Vẫy tay → hiện `SELECTED greeting` → Thumb Up → robot chào trái–phải. Giữ Thumb Up cho tới COMPLETED.
3. Pointing Up → Thumb Up → robot tiến–lùi đủ bốn chu kỳ.
4. Victory → Thumb Up → robot đi đủ một vòng tròn.
5. Trong lúc đang chạy, xòe Open Palm → robot dừng; Thumb Up đơn độc không làm robot tự chạy lại.
6. Chọn/xác nhận một hành vi khác, Closed Fist → hủy và về chờ.
7. Chọn/xác nhận lại, đưa tay khỏi khung hình → robot tự dừng do SIGNAL_LOST.

Không dùng bàn phím, lệnh `ros2 topic pub`, teleop hoặc Nav2 để lái robot trong demo. Dùng Open Palm/Closed Fist cho thao tác dừng; Ctrl+C chỉ để kết thúc ứng dụng.

## Cấu trúc mã nguồn

| File | Vai trò |
|---|---|
| `gesture_recognition_node.py` | Đọc webcam, MediaPipe, vẽ ảnh và publish heartbeat |
| `robot_behavior_node.py` | Nhận cử chỉ, đọc odom/scan/dock/bumper và publish TwistStamped |
| `gesture_logic.py` | State machine xác nhận, chống lặp, watchdog và phát hiện Wave |
| `config/behavior.yaml` | Tốc độ, khoảng cách, bán kính và timeout |
| `launch/arena.launch.py` | Mô phỏng TurtleBot 4 chính thức trong sân trống |
| `launch/behavior.launch.py` | Khởi chạy controller bằng YAML |
| `launch/gui.launch.py` | Mở lại GUI để kết nối server đang chạy, không reset robot |
| `worlds/gesture_arena.sdf` | Sân rộng, sàn và tường bao |
| `scripts/setup_gesture.sh` | Cài môi trường riêng và model |

## Lưu ý kiểm chứng

Nhận diện AI phụ thuộc ánh sáng, góc tay và webcam. Kiểm thử state machine hoặc gửi cử chỉ giả trong test chỉ chứng minh logic điều khiển, không thay thế demo người thật nhận diện cả sáu cử chỉ.

Kết quả build, 18 bài kiểm tra tự động, kiểm tra webcam thật và chuyển động Gazebo: [VALIDATION.md](VALIDATION.md).

Nguồn chính thức: [MediaPipe Python](https://ai.google.dev/edge/mediapipe/solutions/vision/gesture_recognizer/python), [các nhãn có sẵn](https://ai.google.dev/edge/mediapipe/solutions/vision/gesture_recognizer), [OpenCV VideoCapture](https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html).

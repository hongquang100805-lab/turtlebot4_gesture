# Kiểm chứng Navigation bằng code và YOLO — 14/10/2026

## Đã kiểm tra

- Build package bằng Python hệ thống 3.12 và `colcon build --symlink-install` thành công.
- Đăng ký được `goal_recorder`, `navigate_goals`, `yolo_detector`, `setup_yolo.sh`.
- `colcon test-result`: **21 test, 0 errors, 0 failures, 1 skipped**
  (20 passed; test copyright mẫu có sẵn được bỏ qua).
- Test ROS ép dùng **domain 197** riêng, không dùng action server của robot đang chạy.
- Action server giả nhận đúng 3 NavigateToPose theo thứ tự; goal sau chỉ gửi
  khi goal trước SUCCEEDED. Goal 2 aborted/rejected thì không có Goal 3;
  goal timeout được cancel và server trả trạng thái kết thúc.
- Kiểm tra dữ liệu goal: sai frame, thiếu 3 goal, NaN/infinity, bool/chuỗi,
  điểm trùng bị từ chối; ghi YAML lỗi không làm hỏng file đang có.
- Recorder không lưu click sai frame; lưu yaw từ tham số hoặc quaternion AMCL.
- Pipeline ROS Image thực qua DDS với model giả: RGB → BGR đúng thứ tự kênh,
  ảnh annotated giữ header; JSON có class/confidence/bbox/stamp đúng.
- 18 khối lệnh Bash trong hướng dẫn đã qua `bash -n`.
- Gazebo depot trong phiên riêng **domain 84**, không GUI, không gửi lệnh
  chuyển động: nhận ảnh thật `/oakd/rgb/preview/image_raw`, encoding `rgb8`,
  kích thước **320×240**, frame `oakd_rgb_camera_optical_frame`.
  Ảnh màu xem được và có dải pixel 0–255. Phiên này đã được dừng sau kiểm tra.

Log và ảnh kiểm tra nằm trong `~/tb4_ws/log/`: `colcon_test_lab05.log`,
`tests_lab05.log`, `camera_simulation_lab05.log`, `camera_header_lab05.log`,
`camera_rgb_lab05.png`, `camera_rgb_lab05.json`.

## YOLO thật

- Đã nạp weights chính thức `models/yolo11n.pt`, Ultralytics 8.3.221,
  PyTorch 2.6.0+cpu, torchvision 0.21.0+cpu, OpenCV apt 4.6.0, NumPy 1.26.4
  trong môi trường inference `.venv-yolo` dùng được các thư viện ROS hệ thống.
- Wheel PyTorch CPU đã kiểm tra SHA-256 khớp kho chính thức; archive weights
  YOLO đã qua kiểm tra CRC và được model nạp/inference thành công.
- Inference trên ảnh mẫu chính thức `bus.jpg` của Ultralytics phát hiện 1 bus
  và 3 person, confidence lần lượt 0.888, 0.871, 0.824, 0.656 ở imgsz=416,
  threshold=0.4. Ảnh này chỉ dùng kiểm thử, không phải bằng chứng Gazebo.
- Inference trên ảnh camera depot đã lưu không có detection ở ngưỡng 0.4.
  Cảnh tại vị trí xuất phát chủ yếu có kệ/thùng; cần chọn vật thể phù hợp
  và kiểm tra detection thực tế khi quay demo.
- Node `yolo_detector` đã chạy với **camera Gazebo sống**, world depot,
  domain riêng 84. Terminal nhận các frame và báo inference khoảng 26–84 ms
  ở một số mẫu log; đây không phải kết quả benchmark FPS ổn định.
- Subscriber đọc được `/yolo/detections` có frame camera và kích thước 320×240,
  cùng header của `/yolo/annotated_image` mang frame camera và timestamp mô phỏng.
  Hai lệnh đọc topic lấy các frame khác nhau; kiểm tra đồng bộ header ảnh/JSON
  thuộc cùng frame đã thực hiện trong test pipeline ở trên.

Log: `yolo_real_inference.json`, `yolo_live_node.log`, `yolo_live_node_retry.log`,
`yolo_live_json.log`, `yolo_live_image_header.log`, `setup_yolo_final.log`.

## Phần thực nghiệm còn cần thực hiện

- `config/goals.yaml` ban đầu để trống; người dùng chọn ít nhất 3 tọa độ thật
  ở các khu vực khác nhau bằng Publish Point hoặc pose AMCL.
- Đối chiếu localization với Gazebo, LiDAR phải khớp tường trước khi chạy.
- Chạy một hành trình tự động đủ 3 goal với các tọa độ đã chọn và lưu kết quả.
- Quan sát vật thể phù hợp trong camera, kiểm tra class/confidence thực tế.
- Quay video liên tục chứng minh robot tự di chuyển, không va chạm và camera
  nhận diện hoạt động song song. Các test phần mềm không thay thế video này.

Bản đồ tuần trước không bị sửa và test không tự tạo goal nộp bài.

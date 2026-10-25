# Demo Bài 6 có RViz

Bố cục màn hình 1920 × 1080:
- Trái: Gazebo, robot trong sân gesture_arena.
- Phải trên: RViz, mô hình robot và quỹ đạo thực từ odometry.
- Phải dưới: webcam thật, landmarks, nhãn, confidence và trạng thái điều khiển.
- Trên cùng: hướng dẫn từng cảnh quay.

`demo_view.py` chỉ subscribe ảnh, trạng thái, `/odom` và publish `nav_msgs/Path` lên `/gesture_demo/path`. Không gửi cử chỉ hay lệnh vận tốc. Quỹ đạo xóa khi một hành vi mới chuyển sang RUNNING; mũi tên biểu diễn hướng của các pose odometry. Đây là quỹ đạo đã đi, không phải đường Nav2 lập kế hoạch hay ground truth.

`trajectory.rviz` dùng fixed frame `odom`, không yêu cầu SLAM, AMCL hoặc map bài trước. `recording_gui.config` dùng Ogre1 cho GUI để tránh lỗi Ogre2 từng gặp trên máy; server giữ Ogre2 cho LiDAR.

`start_session.py` chạy simulation, controller, nhận diện, viewer, RViz và GUI ở domain 76. `layout.py` đặt các cửa sổ XWayland. `coach.py` và `record_demo.py` hướng dẫn và quay sáu cảnh: tiến–lùi bốn chu kỳ; vòng tròn; chào; Open Palm dừng; Closed Fist hủy; mất tay dừng. Robot chỉ di chuyển theo webcam của người demo.

Video và ảnh của lượt trước được giữ nguyên trong thư mục ngày 24/10/2026. Lượt này lưu riêng, không ghi đè.

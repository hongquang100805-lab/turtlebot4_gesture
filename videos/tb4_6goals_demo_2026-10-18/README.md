# Ảnh minh chứng bài Navigation bằng code và YOLO (6 goal)

Ngày thực hiện: 18/10/2026. World depot, bản đồ depot_02.yaml.
Robot dùng AMCL tự khởi tạo tại vị trí xuất phát cố định; node ROS 2 gửi tuần tự đúng 6 goal trong goals.yaml.
Ảnh màn hình được trích từ bản ghi màn hình thật trong phiên chạy. Ảnh camera riêng được lưu từ topic YOLO thật.
Không đặt goal bằng chuột và không dùng teleop trong chuỗi navigation. Undock thực hiện bằng action trước chuỗi goal.

| Tệp ảnh | Nội dung / gợi ý chú thích |
|---|---|
| 01_gazebo_environment.png | Môi trường depot có robot và mô hình người; cửa sổ camera YOLO hoạt động. |
| 02_localization_rviz.png | Bản đồ cũ trên RViz; AMCL và Nav2 active; dữ liệu LiDAR và vị trí robot. |
| 03_yolo_camera_rviz.png | YOLO nhận diện người trên camera trong lúc robot điều hướng. |
| goal_1_navigation.png | Robot đang thực hiện Goal 1; đường đi do Nav2 lập hiển thị trên RViz. |
| goal_1_succeeded.png | Goal 1 trả về SUCCEEDED; bảng trạng thái đọc từ kết quả action. |
| camera_goal_1.png | Ảnh camera YOLO tại thời điểm Goal 1 thành công. |
| goal_2_navigation.png | Robot đang thực hiện Goal 2; đường đi do Nav2 lập hiển thị trên RViz. |
| goal_2_succeeded.png | Goal 2 trả về SUCCEEDED; bảng trạng thái đọc từ kết quả action. |
| camera_goal_2.png | Ảnh camera YOLO tại thời điểm Goal 2 thành công. |
| goal_3_navigation.png | Robot đang thực hiện Goal 3; đường đi do Nav2 lập hiển thị trên RViz. |
| goal_3_succeeded.png | Goal 3 trả về SUCCEEDED; bảng trạng thái đọc từ kết quả action. |
| camera_goal_3.png | Ảnh camera YOLO tại thời điểm Goal 3 thành công. |
| goal_4_navigation.png | Robot đang thực hiện Goal 4; đường đi do Nav2 lập hiển thị trên RViz. |
| goal_4_succeeded.png | Goal 4 trả về SUCCEEDED; bảng trạng thái đọc từ kết quả action. |
| camera_goal_4.png | Ảnh camera YOLO tại thời điểm Goal 4 thành công. |
| goal_5_navigation.png | Robot đang thực hiện Goal 5; đường đi do Nav2 lập hiển thị trên RViz. |
| goal_5_succeeded.png | Goal 5 trả về SUCCEEDED; bảng trạng thái đọc từ kết quả action. |
| camera_goal_5.png | Ảnh camera YOLO tại thời điểm Goal 5 thành công. |
| goal_6_navigation.png | Robot đang thực hiện Goal 6; đường đi do Nav2 lập hiển thị trên RViz. |
| goal_6_succeeded.png | Goal 6 trả về SUCCEEDED; bảng trạng thái đọc từ kết quả action. |
| camera_goal_6.png | Ảnh camera YOLO tại thời điểm Goal 6 thành công. |
| 09_final_results.png | Kết quả cuối cùng: cả 6 goal đều SUCCEEDED. |
| yolo_person.png | Ảnh camera có bounding box người từ topic YOLO. |

## Kết quả thực tế

| Goal | x (m) | y (m) | yaw (rad) | Trạng thái | Thời gian mô phỏng (s) | Thời gian thực (s) |
|---|---:|---:|---:|---|---:|---:|
| Goal 1 | -2.731 | -2.663 | 0.000 | SUCCEEDED | 16.293 | 27.448 |
| Goal 2 | -2.935 | 2.572 | 0.000 | SUCCEEDED | 23.157 | 40.098 |
| Goal 3 | -6.649 | -0.159 | 0.000 | SUCCEEDED | 21.732 | 37.310 |
| Goal 4 | 4.208 | 3.912 | 0.000 | SUCCEEDED | 46.098 | 78.998 |
| Goal 5 | 8.017 | 1.366 | 0.000 | SUCCEEDED | 19.659 | 36.147 |
| Goal 6 | -6.360 | 3.465 | 0.000 | SUCCEEDED | 60.939 | 106.957 |

Thời gian thực bao gồm ảnh hưởng của tải mô phỏng và quay màn hình. Không diễn giải thời gian thực là thời gian mô phỏng.
YOLO có thể trả về danh sách rỗng khi không có vật thể trong góc nhìn; báo cáo chỉ nên khẳng định những nhận diện có ảnh minh chứng.
motion_audit.json đếm thông báo bumper; không thay thế phép đo va chạm hình học đầy đủ.

## Phần bổ sung phân tích YOLO

Xem [bảng thống kê, đánh giá và ảnh minh chứng](yolo_evaluation/PHAN_TICH_YOLO.md), [CSV](yolo_evaluation/yolo_summary.csv) và [mã LaTeX](yolo_evaluation/yolo_section.tex).

Bảng chỉ đếm 160 mẫu log trong chuỗi 6 goal; không phải tổng kết quả của mọi khung hình. Bộ ảnh ZIP đã có thêm phần phân tích này.

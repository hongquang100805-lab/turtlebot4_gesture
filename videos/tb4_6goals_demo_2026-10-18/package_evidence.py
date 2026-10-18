"""Index actual run evidence for use in the lab report."""
import csv
import json
from pathlib import Path
import zipfile
base=Path(__file__).resolve().parent
r=json.loads((base/'results.json').read_text())
assert r['status']=='SUCCEEDED' and len(r['goals'])==6
assert all(g['status']=='SUCCEEDED' for g in r['goals'])
with (base/'goal_results.csv').open('w',newline='') as f:
    writer=csv.writer(f)
    writer.writerow(['Goal','x_map_m','y_map_m','yaw_rad','status','wall_sec','simulation_sec','error_code'])
    for g in r['goals']:
        writer.writerow([g['name'],g['x'],g['y'],g['yaw'],g['status'],g['elapsed_wall_sec'],g['elapsed_sim_sec'],g['error_code']])
lines=['# Ảnh minh chứng bài Navigation bằng code và YOLO (6 goal)','',
       'Ngày thực hiện: 18/10/2026. World depot, bản đồ depot_02.yaml.',
       'Robot dùng AMCL tự khởi tạo tại vị trí xuất phát cố định; node ROS 2 gửi tuần tự đúng 6 goal trong goals.yaml.',
       'Ảnh màn hình được trích từ bản ghi màn hình thật trong phiên chạy. Ảnh camera riêng được lưu từ topic YOLO thật.',
       'Không đặt goal bằng chuột và không dùng teleop trong chuỗi navigation. Undock thực hiện bằng action trước chuỗi goal.','',
       '| Tệp ảnh | Nội dung / gợi ý chú thích |','|---|---|',
       '| 01_gazebo_environment.png | Môi trường depot có robot và mô hình người; cửa sổ camera YOLO hoạt động. |',
       '| 02_localization_rviz.png | Bản đồ cũ trên RViz; AMCL và Nav2 active; dữ liệu LiDAR và vị trí robot. |',
       '| 03_yolo_camera_rviz.png | YOLO nhận diện người trên camera trong lúc robot điều hướng. |']
for i in range(1,7):
    lines.extend([f'| goal_{i}_navigation.png | Robot đang thực hiện Goal {i}; đường đi do Nav2 lập hiển thị trên RViz. |',
                  f'| goal_{i}_succeeded.png | Goal {i} trả về SUCCEEDED; bảng trạng thái đọc từ kết quả action. |',
                  f'| camera_goal_{i}.png | Ảnh camera YOLO tại thời điểm Goal {i} thành công. |'])
lines.extend(['| 09_final_results.png | Kết quả cuối cùng: cả 6 goal đều SUCCEEDED. |',
              '| yolo_person.png | Ảnh camera có bounding box người từ topic YOLO. |','',
              '## Kết quả thực tế','',
              '| Goal | x (m) | y (m) | yaw (rad) | Trạng thái | Thời gian mô phỏng (s) | Thời gian thực (s) |',
              '|---|---:|---:|---:|---|---:|---:|'])
for g in r['goals']:
    lines.append(f'| {g["name"]} | {g["x"]:.3f} | {g["y"]:.3f} | {g["yaw"]:.3f} | {g["status"]} | {g["elapsed_sim_sec"]:.3f} | {g["elapsed_wall_sec"]:.3f} |')
lines.extend(['', 'Thời gian thực bao gồm ảnh hưởng của tải mô phỏng và quay màn hình. Không diễn giải thời gian thực là thời gian mô phỏng.',
              'YOLO có thể trả về danh sách rỗng khi không có vật thể trong góc nhìn; báo cáo chỉ nên khẳng định những nhận diện có ảnh minh chứng.',
              'motion_audit.json đếm thông báo bumper; không thay thế phép đo va chạm hình học đầy đủ.'])
(base/'README.md').write_text('\n'.join(lines)+'\n')
with zipfile.ZipFile(base/'Anh_bao_cao_6_goal.zip','w',zipfile.ZIP_DEFLATED) as z:
    for file in sorted((base/'report_images').glob('*.png')):
        z.write(file,'report_images/'+file.name)
    for name in ['README.md','goal_results.csv','results.json','goals.yaml','perception_summary.json','motion_audit.json','run_manifest.json']:
        z.write(base/name,name)
print('Evidence bundle ready.')

# Bài thực hành 04 – TurtleBot 4 Simulation, SLAM và Navigation

**Ubuntu 24.04 · ROS 2 Jazzy · Gazebo Harmonic · Python hệ thống 3.12**.
Workspace: `~/tb4_ws`. Package: `turtlebot4_slam_nav`.
Dùng simulator, controller và cấu hình SLAM/AMCL/Nav2 chính thức của TurtleBot 4.

## 0. Chuẩn bị terminal và build

Mở ba terminal:

| Terminal | Công việc | Khi nào giữ mở |
|---|---|---|
| A | Chạy launch của từng phần | Suốt phần đang thực hiện |
| B | Undock và teleop | Khi kiểm tra chuyển động hoặc mapping |
| C | Kiểm tra topic, TF, lưu map và theo dõi goal | Theo từng lệnh |

**Trong mỗi terminal mới**, chạy:

```bash
source ~/tb4_ws/src/turtlebot4_slam_nav/scripts/env.sh
```

Nếu Conda đang active, `conda deactivate` trước. Script dùng Python hệ thống,
source Jazzy và workspace của bài; không sửa `.bashrc`. Mọi terminal của bài
phải source cùng script để dùng cùng ROS domain và Gazebo partition.

**Terminal A — build một lần trước khi chạy:**

```bash
cd ~/tb4_ws
/usr/bin/python3 -m colcon build --symlink-install --packages-select turtlebot4_slam_nav
source install/local_setup.bash
ros2 pkg prefix turtlebot4_slam_nav
```

**Chỉ chạy một chế độ tại một thời điểm.** Khi chuyển phần: ở B nhấn `k`, rồi
`Ctrl+C` để thoát teleop; ở A nhấn `Ctrl+C`, chờ các tiến trình thoát rồi mới
chạy launch tiếp theo. Đóng cửa sổ Gazebo không dừng server; phải dừng ở A.

| Phần | Launch | RViz fixed frame |
|---|---|---|
| Simulation | `simulation.launch.py` | `odom` |
| Mapping | `mapping.launch.py` | `map` |
| Localization | `localization.launch.py` | `map` |
| Navigation | `navigation.launch.py` | `map` |

Các lệnh dưới đây dùng `world:=depot` và thử GUI `ogre2`, vì GUI `ogre` từng
hiển thị cảnh trắng/đen trên máy này. Cả hai GUI engine từng crash; xem mục 6.
Sensor giữ mặc định `sensor_render_engine:=ogre2`.

## 1. Simulation — kiểm tra robot và các topic cơ bản

### 1.1. Khởi chạy — terminal A

```bash
source ~/tb4_ws/src/turtlebot4_slam_nav/scripts/env.sh
ros2 launch turtlebot4_slam_nav simulation.launch.py \
  world:=depot gui_render_engine:=ogre2
```

Giữ A mở. Chờ world tải xong và robot xuất hiện. Gazebo phải đang **Play**.
RViz dùng fixed frame `odom`; chưa có Map ở chế độ này.

**Terminal C — kiểm tra mô phỏng đang chạy:**

```bash
source ~/tb4_ws/src/turtlebot4_slam_nav/scripts/env.sh
ros2 node list --no-daemon --spin-time 5
ros2 topic list --no-daemon --spin-time 5
ros2 topic echo /clock rosgraph_msgs/msg/Clock --once
```

Cần thấy các node của robot và `/clock` có thời gian mô phỏng. Chạy các lệnh
kiểm tra dưới đây lần lượt; lệnh chạy liên tục thì `Ctrl+C` trước lệnh tiếp theo.

### 1.2. Kiểm tra LiDAR `/scan` — terminal C

```bash
ros2 topic info /scan -v
ros2 topic echo /scan sensor_msgs/msg/LaserScan \
  --once --field header --qos-reliability best_effort
ros2 topic echo /scan sensor_msgs/msg/LaserScan \
  --once --field ranges --qos-reliability best_effort
ros2 topic hz /scan
```

**Kết quả cần thấy:**

- Kiểu message `sensor_msgs/msg/LaserScan`, có publisher.
- Header có timestamp và frame LiDAR. Robot standard đang dùng frame
  `turtlebot4/rplidar_link/rplidar`.
- `ranges` có khoảng cách đến vật cản; các mẫu không đồng loạt cố định `0.164`.
  Một số giá trị `inf` có thể là tia không gặp vật cản trong tầm đo.
- `hz` báo tốc độ nhận message lớn hơn 0. Nhấn `Ctrl+C` để dừng.

### 1.3. Kiểm tra odometry `/odom` — terminal C

```bash
ros2 topic info /odom -v
ros2 topic echo /odom nav_msgs/msg/Odometry --once --field header
ros2 topic echo /odom nav_msgs/msg/Odometry --field pose.pose
```

**Kết quả cần thấy:** kiểu `nav_msgs/msg/Odometry`, có publisher, frame `odom`.
Giữ lệnh cuối chạy khi điều khiển ở bước 1.4: vị trí/hướng phải thay đổi khi
robot di chuyển. Nhấn `Ctrl+C` trước khi kiểm tra topic khác.

Có thể kiểm tra thêm tần số:

```bash
ros2 topic hz /odom
```

### 1.4. Kiểm tra robot nhận `/cmd_vel` — terminal B và C

**B — kiểm tra dock:**

```bash
source ~/tb4_ws/src/turtlebot4_slam_nav/scripts/env.sh
ros2 topic echo /dock_status irobot_create_msgs/msg/DockStatus --once
```

Nếu `is_docked: true`, undock và chờ action thành công:

```bash
ros2 action send_goal /undock irobot_create_msgs/action/Undock '{}' --feedback
ros2 topic echo /dock_status irobot_create_msgs/msg/DockStatus --once
```

Cần `is_docked: false` trước khi lái. Nếu action báo `Robot already undocked`,
kiểm tra lại dock status; nếu đã false thì tiếp tục.

**B — mở teleop, giữ terminal này mở:**

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args \
  -p stamped:=true -p use_sim_time:=true -p frame_id:=base_link \
  -p speed:=0.30 -p turn:=1.0
```

**C — đọc lệnh vận tốc, rồi chuyển focus sang B để nhấn phím:**

```bash
ros2 topic info /cmd_vel -v
ros2 topic echo /cmd_vel geometry_msgs/msg/TwistStamped \
  --qos-reliability best_effort
```

Trong **B**: `i` tiến, `,` lùi, `j/l` quay, `k` dừng. Nhấn/giữ phím để cập nhật
lệnh vận tốc. `w/x` tăng/giảm tốc tiến/lùi 10%, `e/c` tăng/giảm tốc quay 10%.

**Kết quả cần thấy:**

- `/cmd_vel` là **`geometry_msgs/msg/TwistStamped`**, có subscriber `motion_control`.
- Nhấn `i`: lệnh có `twist.linear.x` dương; nhấn `j/l`: `twist.angular.z` khác 0;
  nhấn `k`: các thành phần vận tốc trở về 0.
- Robot di chuyển trong Gazebo và odometry thay đổi như bước 1.3.

Có dữ liệu trên `/cmd_vel` mới chứng minh lệnh được publish; phải kiểm tra cả
chuyển động và odometry để xác nhận robot nhận lệnh. Dùng `stamped:=true`,
không publish Twist thường hoặc remap trực tiếp vào controller.

### 1.5. Kiểm tra robot và LiDAR trên RViz

Trong RViz: **Fixed Frame = `odom`**, bật **RobotModel** và **LaserScan**.
LaserScan dùng topic `/scan`, Reliability **Best Effort**, Durability **Volatile**.
Cần thấy robot và các điểm LiDAR quanh vật cản.

**C — kiểm tra TF, chạy từng lệnh và `Ctrl+C` trước lệnh kế tiếp:**

```bash
ros2 run tf2_ros tf2_echo odom base_link --ros-args -p use_sim_time:=true
ros2 run tf2_ros tf2_echo base_link turtlebot4/rplidar_link/rplidar \
  --ros-args -p use_sim_time:=true
```

**Phần 1 đạt khi:** robot xuất hiện, `/scan` và `/odom` có dữ liệu, teleop làm
robot di chuyển, RViz hiển thị robot/LiDAR và TF có dữ liệu.

## 2. SLAM Toolbox — khảo sát và lưu bản đồ

### 2.1. Chạy mapping — terminal A

Dừng teleop và simulation cũ trước, rồi chạy:

```bash
source ~/tb4_ws/src/turtlebot4_slam_nav/scripts/env.sh
ros2 launch turtlebot4_slam_nav mapping.launch.py \
  world:=depot gui_render_engine:=ogre2
```

Giữ A mở. Launch này bật SLAM Toolbox; không bật AMCL hoặc Nav2.

### 2.2. Undock và khảo sát — terminal B

```bash
source ~/tb4_ws/src/turtlebot4_slam_nav/scripts/env.sh
ros2 topic echo /dock_status irobot_create_msgs/msg/DockStatus --once
```

Nếu đang dock, chạy:

```bash
ros2 action send_goal /undock irobot_create_msgs/action/Undock '{}' --feedback
```

Sau khi undock, mở teleop:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args \
  -p stamped:=true -p use_sim_time:=true -p frame_id:=base_link \
  -p speed:=0.30 -p turn:=1.0
```

Khảo sát phần lớn khu vực có thể di chuyển: các hành lang, lối đi và vùng quanh
vật cản. Giảm tốc bằng `x/c` ở chỗ hẹp; quay để quét tường, trở lại vùng đã đi
để đóng vòng. Theo dõi Map cập nhật trên RViz, fixed frame `map`.
Trước khi lưu, kiểm tra tường không bị nhân đôi và các vùng không lệch rõ rệt.

### 2.3. Kiểm tra SLAM và lưu map — terminal C

Giữ mapping ở A đang chạy. Nhấn `k` ở B để robot đứng yên, rồi ở C:

```bash
source ~/tb4_ws/src/turtlebot4_slam_nav/scripts/env.sh
ros2 lifecycle get /slam_toolbox
ros2 topic echo /map nav_msgs/msg/OccupancyGrid \
  --once --field info --qos-durability transient_local
ros2 run tf2_ros tf2_echo map odom --ros-args -p use_sim_time:=true
```

SLAM phải `active`, `/map` có kích thước/resolution và TF `map → odom` có dữ liệu.
Dừng `tf2_echo` bằng `Ctrl+C`, sau đó lưu:

```bash
ros2 run turtlebot4_slam_nav save_map.sh
ls -lh ~/tb4_ws/src/turtlebot4_slam_nav/maps/map.{yaml,pgm}
cat ~/tb4_ws/src/turtlebot4_slam_nav/maps/map.yaml
```

Cần có **`map.yaml` và `map.pgm`**, với `image: map.pgm` trong YAML.
Script báo lỗi nếu chưa có map và từ chối ghi đè map cũ. Muốn lưu tên khác:

```bash
ros2 run turtlebot4_slam_nav save_map.sh "$HOME/tb4_ws/src/turtlebot4_slam_nav/maps/depot_02"
```

Sau khi lưu thành công, thoát teleop ở B và dừng mapping ở A bằng `Ctrl+C`.

## 3. Localization — load map và đặt vị trí robot

### 3.1. Khởi động lại cùng world — terminal A

```bash
source ~/tb4_ws/src/turtlebot4_slam_nav/scripts/env.sh
ros2 launch turtlebot4_slam_nav localization.launch.py \
  world:=depot gui_render_engine:=ogre2 \
  map:="$HOME/tb4_ws/src/turtlebot4_slam_nav/maps/depot_02.yaml"
```

Giữ A mở. Launch này bật map server + AMCL, tắt SLAM và chưa chạy Nav2.

**B — kiểm tra dock và undock như bước 1.4.** Sau đó trong RViz:

1. Chọn **2D Pose Estimate**.
2. Nhấn tại **vị trí hiện tại của robot trên map**, kéo mũi tên đúng hướng robot.
3. Chờ các điểm LiDAR khớp với tường trên bản đồ; đối chiếu robot trong Gazebo.

Tọa độ Gazebo và bản đồ SLAM có thể khác nhau. Sau undock, robot đã rời vị trí
spawn; chọn pose theo vị trí hiện tại. **2D Pose Estimate không phải lệnh đi đến đích.**

### 3.2. Kiểm tra localization — terminal C

```bash
source ~/tb4_ws/src/turtlebot4_slam_nav/scripts/env.sh
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
ros2 topic echo /amcl_pose geometry_msgs/msg/PoseWithCovarianceStamped --once
ros2 run tf2_ros tf2_echo map base_link --ros-args -p use_sim_time:=true
```

Cần map server/AMCL `active`, có `/amcl_pose`, có TF và LiDAR khớp map.
Nếu chưa khớp, đặt lại **2D Pose Estimate** đúng vị trí/hướng.
Dừng `tf2_echo` bằng `Ctrl+C`. Dừng localization ở A trước khi chuyển phần 4.

## 4. Nav2 — thực hiện 3 goal ở các vùng khác nhau

### 4.1. Chạy navigation — terminal A

```bash
source ~/tb4_ws/src/turtlebot4_slam_nav/scripts/env.sh
ros2 launch turtlebot4_slam_nav navigation.launch.py \
  world:=depot gui_render_engine:=ogre2 \
  map:="$HOME/tb4_ws/src/turtlebot4_slam_nav/maps/depot_02.yaml"
```

Giữ A mở. Launch này bật map server + AMCL + Nav2; tắt SLAM.
**Phải chạy `navigation.launch.py`; `localization.launch.py` chưa có Nav2.**

Robot mới: ở B kiểm tra dock, undock theo bước 1.4; trong RViz đặt lại
**2D Pose Estimate** theo phần 3. Nếu còn teleop đang mở, nhấn `k`, rồi `Ctrl+C`.

**C — kiểm tra trước khi gửi goal:**

```bash
source ~/tb4_ws/src/turtlebot4_slam_nav/scripts/env.sh
ros2 lifecycle get /controller_server
ros2 lifecycle get /bt_navigator
ros2 lifecycle get /collision_monitor
ros2 action info /navigate_to_pose
```

Các node phải `active`, action phải có server. Nếu Nav2 còn chờ transform,
kiểm tra initial pose và TF `map → base_link` như bước 3.2.

### 4.2. Đặt goal trong RViz và theo dõi kết quả

**C — giữ lệnh theo dõi chạy:**

```bash
ros2 topic echo /navigate_to_pose/_action/status action_msgs/msg/GoalStatusArray
```

Trong RViz:

1. Chọn **Nav2 Goal**, nhấn vào vùng trống đã được map và kéo hướng đích.
2. Quan sát robot tự lập kế hoạch và di chuyển, path/costmap cập nhật.
3. Chờ robot đến đích, không va chạm và goal báo **`SUCCEEDED`** (`status: 4`).
4. Gửi goal thứ hai rồi thứ ba, tại các vùng khác nhau; chờ từng goal hoàn thành.

**Sau khi gửi goal không điều khiển robot thủ công.** Không cần đặt lại initial
pose giữa các goal nếu localization vẫn đúng. `status: 6` là `ABORTED`, không
được tính là thành công. Khi có nhiều goal UUID trong status, theo dõi UUID
của goal vừa gửi, không dùng status của goal cũ để kết luận.

| Goal | Khu vực đích | Kết quả | Mốc thời gian video |
|---|---|---|---|
| 1 | Tự bổ sung | | |
| 2 | Tự bổ sung | | |
| 3 | Tự bổ sung | | |

## 5. Đổi world hoặc dùng map khác

Đổi `world:=depot` thành `world:=maze` hoặc `world:=warehouse` trong các launch.
**Mapping, localization và navigation phải cùng world, model và pose spawn.**
Các argument spawn: `model`, `x`, `y`, `z`, `yaw`; giữ giống nhau giữa các phần.

Truyền đường dẫn YAML của map đã tạo; nếu lưu `depot_02`, dùng:

```bash
ros2 launch turtlebot4_slam_nav navigation.launch.py \
  world:=depot gui_render_engine:=ogre2 \
  map:="$HOME/tb4_ws/src/turtlebot4_slam_nav/maps/depot_02.yaml"
```

Dừng phiên cũ trước lệnh trên. Khi di chuyển map, chuyển cả YAML và ảnh mà YAML
tham chiếu. Không cần build lại nếu dùng trực tiếp đường dẫn map trong source.
Muốn map mới được cài vào `install/` để phân phối, build lại:

```bash
cd ~/tb4_ws
/usr/bin/python3 -m colcon build --symlink-install --packages-select turtlebot4_slam_nav
source install/local_setup.bash
ls "$(ros2 pkg prefix --share turtlebot4_slam_nav)/maps"
```

Nếu bỏ argument `map`, wrapper ưu tiên `maps/map.yaml` trong source rồi mới
đến map đã cài. Chưa có map hợp lệ thì localization/navigation báo lỗi trước
khi bật simulator; hãy mapping và lưu map trước.

## 6. Kiểm tra nhanh khi gặp lỗi

| Hiện tượng | Bước kiểm tra |
|---|---|
| Không có dữ liệu topic | Chờ world tải xong, Gazebo đang Play; source cùng `env.sh` ở mọi terminal; đọc `/clock` ở bước 1.1. |
| Robot không chạy dù `/cmd_vel` có dữ liệu | Kiểm tra dock, dùng TwistStamped, focus đúng terminal B; kiểm tra `/odom` khi nhấn phím. |
| Robot chạy chậm | Teleop đang đặt 0.30 m/s; dùng `w/x` điều chỉnh. Xem Real Time Factor trong Gazebo: mô phỏng chậm hơn thời gian thực cũng làm chuyển động nhìn chậm. |
| LiDAR không hiện | Kiểm tra `/scan`, QoS Best Effort và TF ở bước 1.5. |
| Scan toàn `0.164`, map rất nhỏ | Giữ `sensor_render_engine:=ogre2`; không dùng map lỗi đó để navigation. |
| `Please set the initial pose` | Dùng 2D Pose Estimate đúng vị trí/hướng hiện tại; kiểm tra `/amcl_pose` và TF ở bước 3.2. |
| `queue is full` trước initial pose | Đặt initial pose để có TF từ map tới robot; kiểm tra dữ liệu mới sau đó, không chỉ đọc lại cảnh báo cũ. |
| Có `initialPoseReceived` rồi `Setting pose`, nhưng cảnh báo extrapolation vài ms | AMCL vẫn nhận pose; kiểm tra `/amcl_pose`, TF và LiDAR khớp map trước khi gửi goal. |
| Không có Nav2 Goal hoặc action server | Kiểm tra đang chạy `navigation.launch.py`, không phải `localization.launch.py`. |
| Map không load | Kiểm tra YAML/PGM tồn tại và trường `image`; chạy `ros2 lifecycle get /map_server`. |
| `Node not found` dù đã khởi chạy | Thử `ros2 node list --no-daemon --spin-time 5`; các terminal phải cùng domain/profile từ `env.sh`. |
| `GLIBC_PRIVATE` từ VS Code Snap | Source `env.sh` trong terminal của bài để làm sạch biến GUI. |
| GUI Gazebo trắng/đen hoặc crash | Thử `gui_render_engine:=ogre2`; nếu vẫn crash, dùng `gazebo_gui:=false` như lệnh dưới. |

Ví dụ chạy server và RViz khi GUI Gazebo lỗi, **sau khi dừng phiên cũ**:

```bash
ros2 launch turtlebot4_slam_nav simulation.launch.py world:=depot gazebo_gui:=false
```

Thêm `gazebo_gui:=false` vào lệnh mapping/localization/navigation cũng được.
GUI và server chạy riêng; lỗi GUI không tự dừng server. Cách này kiểm tra được
dữ liệu và thao tác RViz, nhưng phần quan sát robot trong Gazebo để nghiệm thu
vẫn cần GUI hiển thị đúng. Chi tiết lỗi môi trường xem [VALIDATION.md](VALIDATION.md).

Lần đầu Depot tải từ Gazebo Fuel có thể mất vài phút. Nếu tải/spawn timeout,
dừng launch ở A; trong terminal đã source `env.sh`, tải model rồi chạy lại:

```bash
gz fuel download -u https://fuel.gazebosim.org/1.0/OpenRobotics/models/Depot
```

## 7. Dependency nếu máy chưa cài

Các gói đã có trên máy khi triển khai. Chỉ cài nếu còn thiếu:

```bash
sudo apt update
sudo apt install ros-jazzy-turtlebot4-simulator ros-jazzy-irobot-create-nodes \
  ros-jazzy-turtlebot4-navigation ros-jazzy-nav2-bringup ros-jazzy-slam-toolbox \
  ros-jazzy-rviz2 ros-jazzy-teleop-twist-keyboard ros-jazzy-tf2-ros \
  ros-jazzy-rmw-fastrtps-cpp python3-colcon-common-extensions python3-yaml
```

Gazebo dùng Harmonic (gz-sim 8); xem [cài Harmonic](https://gazebosim.org/docs/harmonic/install_ubuntu/)
nếu máy chưa có. Không cần build simulator từ source.

## 8. Checklist quay video và nộp bài

- [ ] Robot trong Gazebo; `/scan`, `/odom`, `/cmd_vel` hoạt động như phần 1.
- [ ] RViz hiển thị robot/LiDAR; teleop sau undock làm robot di chuyển.
- [ ] Khảo sát phần lớn vùng đi được, Map cập nhật, tường không bị nhân đôi/lệch rõ rệt.
- [ ] Lưu `map.yaml` + `map.pgm`, quay bản đồ hoàn chỉnh.
- [ ] Dừng SLAM, khởi động lại cùng world, load map và đặt initial pose đúng.
- [ ] LiDAR khớp map, vị trí robot trong RViz tương ứng Gazebo.
- [ ] Ba Nav2 goal ở ba vùng khác nhau, từng goal thành công và không va chạm.
- [ ] Không điều khiển thủ công sau khi gửi goal.
- [ ] Nộp source cùng map thật; `.gitignore` giữ YAML/PGM, bỏ build/install/log.

Link GitHub: **[tự bổ sung]**

Link Google Drive video: **[tự bổ sung]**

Kết quả kiểm tra đã thực hiện: [VALIDATION.md](VALIDATION.md).
Build hoặc Nav2 active chưa chứng minh đã hoàn thành khảo sát và ba goal.

Tài liệu chính thức: [Simulator Jazzy](https://turtlebot.github.io/turtlebot4-user-manual/software/turtlebot4_simulator.html),
[source nhánh jazzy](https://github.com/turtlebot/turtlebot4_simulator/tree/jazzy),
[tạo map](https://turtlebot.github.io/turtlebot4-user-manual/tutorials/generate_map.html),
[navigation](https://turtlebot.github.io/turtlebot4-user-manual/tutorials/navigation.html).

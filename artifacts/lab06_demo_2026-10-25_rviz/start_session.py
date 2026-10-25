import os,subprocess,json
from pathlib import Path
base=Path(__file__).resolve().parent
commands={
 'simulation':'ros2 launch turtlebot4_gesture_control arena.launch.py gazebo_gui:=false',
 'behavior':'ros2 launch turtlebot4_gesture_control behavior.launch.py',
 'webcam':'./.venv-gesture/bin/python -m turtlebot4_gesture_control.gesture_recognition_node --ros-args -p show_window:=false -p confidence:=0.65 -p max_fps:=15.0',
 'viewer':f'python3 {base}/demo_view.py',
 'rviz':f'ros2 run rviz2 rviz2 -d {base}/trajectory.rviz --ros-args -p use_sim_time:=true',
 'gui':f'gz sim -g --render-engine-gui ogre --gui-config {base}/recording_gui.config'}
pids={}
for name,cmd in commands.items():
 log=(base/(name+'.log')).open('w')
 p=subprocess.Popen(['/bin/bash','-c','export TB4_LAB_DOMAIN_ID=76; source src/turtlebot4_slam_nav/scripts/env.sh; export GZ_IP=127.0.0.1; '+cmd],cwd='/home/lenovo/tb4_ws',stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 pids[name]=p.pid
(base/'pids.json').write_text(json.dumps(pids,indent=2));print(pids)

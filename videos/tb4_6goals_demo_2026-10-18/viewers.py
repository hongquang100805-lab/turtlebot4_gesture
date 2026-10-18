import json
import os
from pathlib import Path
import signal
import subprocess
import time
base=Path(__file__).resolve().parent
root=base.parents[1]
commands={
 'rviz':['rviz2','-d',str(base/'navigation.rviz'),'--ros-args','-p','use_sim_time:=true'],
 'yolo':[str(root/'.venv-yolo/bin/python'),'-m','turtlebot4_slam_nav.yolo_detector','--ros-args','-p','use_sim_time:=true','-p','confidence:=0.25','-p','max_fps:=2.0'],
 'monitor':['python3',str(base/'monitor.py')],
 'audit':['python3',str(base/'audit.py')],
}
processes=[]
try:
 for name,cmd in commands.items():
  f=open(base/f'{name}.log','w')
  processes.append((name,subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT),f))
 (base/'viewer_pids.json').write_text(json.dumps({name:p.pid for name,p,f in processes}))
 while not (base/'stop_viewers').exists():
  for name,p,f in processes:
   if p.poll() is not None:print(f'{name} exited: {p.returncode}',flush=True)
  time.sleep(2)
except KeyboardInterrupt:pass
finally:
 for name,p,f in processes:
  if p.poll() is None:p.send_signal(signal.SIGINT)
 for name,p,f in processes:
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:p.terminate()
  f.close()

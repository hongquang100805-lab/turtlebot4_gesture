import json,time
from pathlib import Path
import rclpy
from rclpy.node import Node
from irobot_create_msgs.msg import HazardDetectionVector,HazardDetection
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data
base=Path(__file__).resolve().parent
rclpy.init();node=Node('navigation_video_audit')
state={'bump_messages':0,'samples':0,'start':None,'latest':None}
stream=(base/'odometry_path.jsonl').open('w')
def hazards(m):
 if any(d.type==HazardDetection.BUMP for d in m.detections):state['bump_messages']+=1
 (base/'motion_audit.json').write_text(json.dumps(state,indent=2))
last=0
def odom(m):
 global last
 if time.monotonic()-last<.3:return
 last=time.monotonic();p=m.pose.pose.position
 record={'sim_sec':m.header.stamp.sec+m.header.stamp.nanosec/1e9,'x':p.x,'y':p.y}
 stream.write(json.dumps(record)+'\n');stream.flush()
 state['samples']+=1;state['latest']=record
 if state['start'] is None:state['start']=record
 (base/'motion_audit.json').write_text(json.dumps(state,indent=2))
node.create_subscription(HazardDetectionVector,'/hazard_detection',hazards,qos_profile_sensor_data)
node.create_subscription(Odometry,'/odom',odom,qos_profile_sensor_data)
try:rclpy.spin(node)
except KeyboardInterrupt:pass
finally:
 stream.close();node.destroy_node()
 if rclpy.ok():rclpy.shutdown()

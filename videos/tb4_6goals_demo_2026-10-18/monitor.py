import json,math,time
from pathlib import Path
import cv2,numpy as np,rclpy,yaml
from rclpy.node import Node
from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy,qos_profile_sensor_data
from rclpy.clock import Clock,ClockType
from sensor_msgs.msg import Image
from std_msgs.msg import String
from geometry_msgs.msg import PoseWithCovarianceStamped
from visualization_msgs.msg import Marker,MarkerArray
from cv_bridge import CvBridge
base=Path(__file__).resolve().parent
rclpy.init(args=['--ros-args','-p','use_sim_time:=true']);node=Node('video_demo_monitor');bridge=CvBridge()
state={'image':None,'report':None,'pose':None};saved_statuses=set();best_person=0.0;summary={'frames':0,'detection_frames':0,'classes':{}}
def on_image(m):state['image']=bridge.imgmsg_to_cv2(m,'bgr8')
def on_report(m):
 global best_person
 r=json.loads(m.data);state['report']=r;summary['frames']+=1
 if r['detections']:summary['detection_frames']+=1
 for o in r['detections']:summary['classes'][o['class_name']]=max(summary['classes'].get(o['class_name'],0),o['confidence'])
 confidence=max((o['confidence'] for o in r['detections'] if o['class_name']=='person'),default=0.0)
 if confidence>best_person and state['image'] is not None:
  best_person=confidence;cv2.imwrite(str(base/'report_images/yolo_person.png'),state['image'])
 (base/'perception_summary.json').write_text(json.dumps(summary,indent=2))
def on_pose(m):state['pose']=m.pose.pose
node.create_subscription(Image,'/yolo/annotated_image',on_image,qos_profile_sensor_data)
node.create_subscription(String,'/yolo/detections',on_report,10)
q=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
node.create_subscription(PoseWithCovarianceStamped,'/amcl_pose',on_pose,q)
markers=node.create_publisher(MarkerArray,'/demo/goals',q)
goals=yaml.safe_load((base/'goals.yaml').read_text())['goals']
name='TurtleBot4 - YOLO camera and 6 autonomous goals'
cv2.namedWindow(name,cv2.WINDOW_NORMAL);cv2.resizeWindow(name,640,930);cv2.moveWindow(name,1280,32)
def text(c,s,x,y,color=(235,235,235),scale=.58):cv2.putText(c,s,(x,y),cv2.FONT_HERSHEY_SIMPLEX,scale,color,1,cv2.LINE_AA)
def tick():
 c=np.full((930,640,3),(25,29,34),np.uint8)
 text(c,'TURTLEBOT 4 | GAZEBO DEPOT | YOLO11n',18,30,scale=.65)
 if state['image'] is not None:c[55:535]=cv2.resize(state['image'],(640,480))
 else:text(c,'Waiting for live camera...',30,250)
 r=state['report']
 if r:
  objects=', '.join(f'{o["class_name"]} {o["confidence"]:.2f}' for o in r['detections'])
  text(c,'Detected: '+(objects or 'none on this frame'),18,560,(80,230,150))
  text(c,f'Inference {r["inference_ms"]:.0f} ms | RGB 320x240 | sim {r["stamp"]["sec"]} s',18,588)
 if state['pose']:
  p=state['pose'];yaw=math.atan2(2*p.orientation.w*p.orientation.z,1-2*p.orientation.z*p.orientation.z)
  text(c,f'AMCL map: ({p.position.x:.2f}, {p.position.y:.2f}, {yaw:.2f} rad)',18,618)
 phase=(base/'phase.txt').read_text().strip() if (base/'phase.txt').exists() else 'LOCALIZATION / MAP FROM PREVIOUS LAB'
 text(c,phase,18,655,(0,220,255),.58)
 try:records=json.loads((base/'results.json').read_text()).get('goals',[])
 except (FileNotFoundError,json.JSONDecodeError):records=[]
 for i,g in enumerate(goals):
  status=records[i]['status'] if i<len(records) else 'WAITING'
  if status=='SUCCEEDED' and i not in saved_statuses:
   saved_statuses.add(i)
   if state['image'] is not None:cv2.imwrite(str(base/f'report_images/camera_goal_{i+1}.png'),state['image'])
  text(c,f'Goal {i+1}: ({g["x"]:.1f}, {g["y"]:.1f}, {g["yaw"]:.2f})',18,692+i*33)
  text(c,status,445,692+i*33,(60,230,90) if status=='SUCCEEDED' else (230,200,80),.6)
 text(c,'Controller: ROS 2 node navigate_goals',18,886)
 text(c,'Live image topic: /yolo/annotated_image',18,915,scale=.54)
 cv2.imshow(name,c);cv2.waitKey(1)
 a=MarkerArray()
 for i,g in enumerate(goals):
  m=Marker();m.header.frame_id='map';m.ns='goals';m.id=i;m.type=Marker.TEXT_VIEW_FACING;m.action=Marker.ADD
  m.pose.position.x=g['x'];m.pose.position.y=g['y'];m.pose.position.z=.5;m.pose.orientation.w=1.
  m.scale.z=.4;m.color.r=1.;m.color.g=.7;m.color.a=1.;m.text=f'Goal {i+1}';a.markers.append(m)
 markers.publish(a)
node.create_timer(.15,tick,clock=Clock(clock_type=ClockType.STEADY_TIME))
try:rclpy.spin(node)
except KeyboardInterrupt:pass
finally:
 cv2.destroyAllWindows();node.destroy_node()
 if rclpy.ok():rclpy.shutdown()

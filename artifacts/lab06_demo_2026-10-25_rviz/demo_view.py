"""Read-only webcam viewer and measured odometry trajectory for recording."""
import json, math, sys
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
from nav_msgs.msg import Odometry, Path as NavPath
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import Image
from std_msgs.msg import String
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

class Viewer(Node):
    def __init__(self, label):
        super().__init__('gesture_demo_view')
        self.label=label; self.path=NavPath();self.path.header.frame_id='odom'
        self.state='';self.last=None
        self.pub=self.create_publisher(NavPath,'/gesture_demo/path',QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.create_subscription(Odometry,'/odom',self.odom,qos_profile_sensor_data)
        self.create_subscription(Image,'/gesture_recognition/image',self.image,1)
        self.create_subscription(String,'/robot_behavior_state',self.status,QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
    def status(self,m):
        s=json.loads(m.data).get('state','')
        if s=='RUNNING' and self.state!='RUNNING':self.path.poses=[];self.last=None
        self.state=s
    def odom(self,m):
        if m.header.frame_id!='odom':return
        p=m.pose.pose; key=(p.position.x,p.position.y,2*math.atan2(p.orientation.z,p.orientation.w))
        if self.last and math.hypot(key[0]-self.last[0],key[1]-self.last[1])<.008 and abs(key[2]-self.last[2])<.04:return
        pose=PoseStamped();pose.header=m.header;pose.pose=p
        self.path.header=m.header;self.path.poses.append(pose);self.path.poses=self.path.poses[-6000:]
        self.pub.publish(self.path);self.last=key
    def image(self,m):
        if m.encoding!='bgr8':return
        image=QImage(bytes(m.data),m.width,m.height,m.step,QImage.Format_BGR888).copy()
        self.label.setPixmap(QPixmap.fromImage(image).scaled(self.label.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))

app=QApplication(sys.argv); w=QWidget();w.setWindowTitle('LAB 06 | Webcam - Gesture recognition')
w.setStyleSheet('background:#0e1825;color:white;');layout=QVBoxLayout(w);layout.setContentsMargins(3,3,3,3)
label=QLabel('Waiting for webcam ...');label.setAlignment(Qt.AlignCenter);layout.addWidget(label)
w.setGeometry(1198,474,714,565);w.show()
rclpy.init();node=Viewer(label)
timer=QTimer();timer.timeout.connect(lambda:rclpy.spin_once(node,timeout_sec=0));timer.start(10)
try:app.exec_()
finally:node.destroy_node();rclpy.shutdown()

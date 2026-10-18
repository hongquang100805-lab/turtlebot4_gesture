import time,rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy
from geometry_msgs.msg import PoseWithCovarianceStamped
rclpy.init(args=['--ros-args','-p','use_sim_time:=true']);node=Node('demo_initial_pose')
pub=node.create_publisher(PoseWithCovarianceStamped,'/initialpose',10);received=[]
q=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
node.create_subscription(PoseWithCovarianceStamped,'/amcl_pose',received.append,q)
end=time.monotonic()+90;last=0
while not received and time.monotonic()<end:
 rclpy.spin_once(node,timeout_sec=.1)
 if node.get_clock().now().nanoseconds>0 and time.monotonic()-last>1:
  p=PoseWithCovarianceStamped();p.header.frame_id='map';p.header.stamp=node.get_clock().now().to_msg();p.pose.pose.orientation.w=1.
  p.pose.covariance[0]=.04;p.pose.covariance[7]=.04;p.pose.covariance[35]=.04
  pub.publish(p);last=time.monotonic()
assert received,'AMCL initial pose timeout'
print(received[-1].pose.pose,flush=True)
node.destroy_node();rclpy.shutdown()

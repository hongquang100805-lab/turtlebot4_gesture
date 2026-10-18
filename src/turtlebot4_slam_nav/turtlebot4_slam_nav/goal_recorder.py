"""Ghi Publish Point hoac pose AMCL vao YAML goal."""

from pathlib import Path

from geometry_msgs.msg import PointStamped, PoseWithCovarianceStamped
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_srvs.srv import Trigger

from turtlebot4_slam_nav.goal_utils import load_goals, save_goals, yaw_from_quaternion


class GoalRecorder(Node):
    """Moi click luu mot goal; service luu pose robot hien tai."""

    def __init__(self):
        """Mo file goal, khong ghi de cac diem da luu."""
        super().__init__('goal_recorder')
        self.declare_parameter('output_file', str(
            Path.home() / 'tb4_ws/src/turtlebot4_slam_nav/config/goals.yaml'))
        self.declare_parameter('yaw', 0.0)
        self.filename = self.get_parameter('output_file').value
        self.goals = (load_goals(self.filename, minimum=0)
                      if Path(self.filename).expanduser().exists() else [])
        self.amcl_pose = None
        self.create_subscription(PointStamped, '/clicked_point', self.on_point, 10)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                         reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.on_amcl, qos)
        self.create_service(Trigger, '/record_current_pose', self.record_pose)
        self.get_logger().info(
            f'Da co {len(self.goals)} goal. Publish Point voi Fixed Frame=map; '
            f'yaw={self.get_parameter("yaw").value} rad. Luu vao {self.filename}')

    def append_goal(self, x, y, yaw):
        """Chi cap nhat bo nho sau khi ghi file thanh cong."""
        goal = {'name': f'Goal {len(self.goals) + 1}', 'x': float(x),
                'y': float(y), 'yaw': float(yaw)}
        save_goals(self.filename, self.goals + [goal])
        self.goals.append(goal)
        self.get_logger().info(
            f'Da ghi {goal["name"]}: x={x:.3f}, y={y:.3f}, yaw={yaw:.3f} rad')

    def on_point(self, message):
        """Nhan toa do map; Publish Point khong cung cap huong."""
        if message.header.frame_id != 'map':
            self.get_logger().error('Bo qua click: Fixed Frame phai la map')
            return
        try:
            self.append_goal(message.point.x, message.point.y,
                             self.get_parameter('yaw').value)
        except (OSError, ValueError) as error:
            self.get_logger().error(str(error))

    def on_amcl(self, message):
        """Giu pose AMCL gan nhat de luu ca yaw."""
        self.amcl_pose = message

    def record_pose(self, request, response):
        """Service Trigger luu vi tri va huong robot, khong di chuyen robot."""
        del request
        try:
            if self.amcl_pose is None or self.amcl_pose.header.frame_id != 'map':
                raise ValueError('Chua co /amcl_pose trong frame map')
            pose = self.amcl_pose.pose.pose
            self.append_goal(pose.position.x, pose.position.y,
                             yaw_from_quaternion(pose.orientation))
            response.success = True
            response.message = f'Da luu Goal {len(self.goals)}'
        except (OSError, ValueError) as error:
            response.success = False
            response.message = str(error)
        return response


def main(args=None):
    """Chay recorder den khi Ctrl+C."""
    rclpy.init(args=args)
    node = None
    try:
        node = GoalRecorder()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

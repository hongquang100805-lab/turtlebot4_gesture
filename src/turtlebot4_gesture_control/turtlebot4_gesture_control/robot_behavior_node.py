"""Gesture-selected motions, odometry feedback, and fail-closed stop conditions."""

import json
import math
import signal
import time

from geometry_msgs.msg import TwistStamped
from irobot_create_msgs.msg import DockStatus, HazardDetection, HazardDetectionVector
from nav_msgs.msg import Odometry
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, qos_profile_sensor_data, QoSProfile
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String

from turtlebot4_gesture_control.gesture_logic import BehaviorConfig, BehaviorEngine


class RobotBehaviorNode(Node):
    """Publish Jazzy TwistStamped without using Nav2 or keyboard teleoperation."""

    def __init__(self):
        super().__init__('robot_behavior_node')
        defaults = vars(BehaviorConfig())
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        self.engine = BehaviorEngine(BehaviorConfig(**{
            name: self.get_parameter(name).value for name in defaults}))
        self.velocity = self.create_publisher(TwistStamped, '/cmd_vel', 5)
        self.status_pub = self.create_publisher(String, '/robot_behavior_state', QoSProfile(
            depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.pose = None
        self.odom_at = self.scan_at = None
        self.front = self.rear = self.surrounding = math.inf
        self.scan_valid = False
        self.docked = None
        self.bump = False
        self.last_status = None
        self.last_status_at = 0.0
        self.create_subscription(String, '/detected_gesture', self.on_gesture, 1)
        self.create_subscription(Odometry, '/odom', self.on_odom, qos_profile_sensor_data)
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.create_subscription(DockStatus, '/dock_status', self.on_dock,
                                 qos_profile_sensor_data)
        self.create_subscription(HazardDetectionVector, '/hazard_detection', self.on_hazards,
                                 qos_profile_sensor_data)
        self.create_timer(0.05, self.tick, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def ready(self, now):
        timeout = self.engine.config.sensor_timeout
        return (self.odom_at is not None and now - self.odom_at < timeout
                and self.scan_at is not None and now - self.scan_at < timeout
                and self.scan_valid and self.docked is False and not self.bump
                and self.get_clock().now().nanoseconds > 0)

    def on_gesture(self, message):
        now = time.monotonic()
        self.engine.feed(message.data, now, ready=self.ready(now))
        if message.data in ('Open_Palm', 'Closed_Fist'):
            self.publish_velocity(0.0, 0.0)

    def on_odom(self, message):
        p = message.pose.pose
        q = p.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y),
                         1 - 2 * (q.y * q.y + q.z * q.z))
        values = (p.position.x, p.position.y, yaw)
        if not all(math.isfinite(v) for v in values):
            return
        if self.pose is not None:
            distance = math.hypot(values[0] - self.pose[0], values[1] - self.pose[1])
            angle = math.atan2(math.sin(yaw - self.pose[2]), math.cos(yaw - self.pose[2]))
            if distance > 0.5 or abs(angle) > 1.0:
                self.engine.stop('SAFETY_STOP', 'Odometry discontinuity')
            else:
                self.engine.odometry(distance, angle)
        self.pose = values
        self.odom_at = time.monotonic()

    def on_scan(self, message):
        front, rear, all_ranges = [], [], []
        for i, value in enumerate(message.ranges):
            if math.isnan(value) or value < message.range_min:
                continue
            if not (math.isinf(value) and value > 0) and (
                    not math.isfinite(value) or value > message.range_max):
                continue
            angle = math.atan2(math.sin(message.angle_min + i * message.angle_increment),
                               math.cos(message.angle_min + i * message.angle_increment))
            all_ranges.append(value)
            if abs(angle) <= math.pi / 3:
                front.append(value)
            if abs(angle) >= 2 * math.pi / 3:
                rear.append(value)
        self.scan_valid = bool(front) and bool(rear)
        self.front = min(front, default=math.inf)
        self.rear = min(rear, default=math.inf)
        self.surrounding = min(all_ranges, default=math.inf)
        self.scan_at = time.monotonic()

    def on_dock(self, message):
        self.docked = message.is_docked

    def on_hazards(self, message):
        self.bump = any(d.type == HazardDetection.BUMP for d in message.detections)
        if self.bump:
            self.engine.stop('SAFETY_STOP', 'Bumper detected')
            self.publish_velocity(0.0, 0.0)

    def publish_velocity(self, v, w):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.twist.linear.x, msg.twist.angular.z = v, w
        self.velocity.publish(msg)

    def tick(self):
        now = time.monotonic()
        ready = self.ready(now)
        v, w = self.engine.tick(now, ready, self.front, self.rear, self.surrounding, self.bump)
        self.publish_velocity(v, w)
        status = self.engine.status()
        status.update(ready=ready, docked=self.docked)
        encoded = json.dumps(status)
        if encoded != self.last_status or now - self.last_status_at > 0.5:
            self.status_pub.publish(String(data=encoded))
            if status['state'] != (json.loads(self.last_status)['state']
                                   if self.last_status else None):
                self.get_logger().info(encoded)
            self.last_status, self.last_status_at = encoded, now

    def close(self):
        self.engine.stop('IDLE', 'Node shutdown')
        for _ in range(3):
            self.publish_velocity(0.0, 0.0)
            time.sleep(0.02)


def interrupt(signum, frame):
    del signum, frame
    raise KeyboardInterrupt


def main(args=None):
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    previous = {s: signal.signal(s, interrupt) for s in (signal.SIGINT, signal.SIGTERM)}
    node = None
    try:
        node = RobotBehaviorNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node:
            if rclpy.ok():
                node.close()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        for s, handler in previous.items():
            signal.signal(s, handler)

"""Gui NavigateToPose tuan tu, chi di tiep sau SUCCEEDED."""

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import signal
import time

from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseWithCovarianceStamped
from lifecycle_msgs.msg import State
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateToPose
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.signals import SignalHandlerOptions
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener

from turtlebot4_slam_nav.goal_utils import atomic_write, load_goals


class SequentialNavigator(Node):
    """Mot action dang chay tai moi thoi diem; khong publish cmd_vel."""

    def __init__(self):
        """Nap goal that va chuan bi action, lifecycle, TF va AMCL."""
        super().__init__('navigate_goals')
        defaults = {
            'goals_file': str(Path.home() / 'tb4_ws/src/turtlebot4_slam_nav/config/goals.yaml'),
            'results_file': str(Path.home() / 'tb4_ws/log/navigation_results.json'),
            'ready_timeout': 180.0, 'goal_timeout': 300.0,
            'wall_timeout': 1800.0, 'pause_at_goal': 3.0,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        self.goals = load_goals(self.get_parameter('goals_file').value)
        for name in ('ready_timeout', 'goal_timeout', 'wall_timeout', 'pause_at_goal'):
            value = self.get_parameter(name).value
            if not math.isfinite(value) or value < 0 or (value == 0 and name != 'pause_at_goal'):
                raise ValueError(f'{name} khong hop le')
        self.results = {'started_utc': datetime.now(timezone.utc).isoformat(),
                        'frame_id': 'map', 'status': 'WAITING', 'goals': []}
        self.results_file = self.get_parameter('results_file').value
        self.flush_results()
        self.client = ActionClient(self, NavigateToPose, '/navigate_to_pose')
        self.lifecycle_clients = {name: self.create_client(GetState, f'/{name}/get_state')
                                  for name in ('amcl', 'bt_navigator')}
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.amcl_ready = False
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                         reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.on_amcl, qos)
        self.goal_handle = None
        self.send_future = None
        self.result_future = None
        self.last_feedback = 0.0

    def flush_results(self):
        """Luu bang ket qua sau moi thay doi trang thai."""
        atomic_write(self.results_file, json.dumps(self.results, indent=2, ensure_ascii=False))

    def on_amcl(self, message):
        """Chi chap nhan pose AMCL thuoc frame map."""
        self.amcl_ready = message.header.frame_id == 'map'

    def wait_future(self, future, timeout):
        """Cho future voi han wall time de khong treo khi mat server."""
        deadline = time.monotonic() + timeout
        while rclpy.ok() and not future.done() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        if not future.done():
            raise TimeoutError('Het thoi gian cho phan hoi ROS action/service')
        return future.result()

    def wait_ready(self):
        """Cho Nav2 active, initial pose, clock va TF map -> base_link."""
        self.get_logger().info('Cho AMCL/Nav2 active; dat 2D Pose Estimate neu chua co pose')
        deadline = time.monotonic() + self.get_parameter('ready_timeout').value
        active = set()
        pending = {}
        last_request = {}
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            now = time.monotonic()
            for name, client in self.lifecycle_clients.items():
                if name in pending and pending[name].done():
                    response = pending.pop(name).result()
                    if response and response.current_state.id == State.PRIMARY_STATE_ACTIVE:
                        active.add(name)
                    else:
                        active.discard(name)
                if name not in pending and client.service_is_ready() and (
                        now - last_request.get(name, 0.0) > 1.0):
                    pending[name] = client.call_async(GetState.Request())
                    last_request[name] = now
            if not (self.client.server_is_ready() and self.amcl_ready
                    and len(active) == len(self.lifecycle_clients)):
                continue
            try:
                transform = self.buffer.lookup_transform('map', 'base_link', Time())
                age = (self.get_clock().now().nanoseconds
                       - Time.from_msg(transform.header.stamp).nanoseconds) / 1e9
                if self.get_clock().now().nanoseconds > 0 and -1.0 <= age <= 2.0:
                    self.get_logger().info('Nav2 san sang; AMCL va TF da co du lieu')
                    return
            except TransformException:
                pass
        raise TimeoutError('Chua san sang: kiem tra Play, initial pose, TF va Nav2 active')

    def on_feedback(self, message):
        """In khoang cach con lai va so recovery, gioi han tan so log."""
        if time.monotonic() - self.last_feedback >= 2.0:
            feedback = message.feedback
            self.get_logger().info(
                f'Con {feedback.distance_remaining:.2f} m; '
                f'recoveries={feedback.number_of_recoveries}')
            self.last_feedback = time.monotonic()

    def cancel_active(self):
        """Huy action khi Ctrl+C hoac timeout, ke ca dang cho chap nhan."""
        if self.goal_handle is None and self.send_future is not None:
            self.goal_handle = self.wait_future(self.send_future, 5.0)
        if self.goal_handle and self.goal_handle.accepted:
            if self.result_future is not None and self.result_future.done():
                return
            response = self.wait_future(self.goal_handle.cancel_goal_async(), 5.0)
            if not response or not response.goals_canceling:
                raise RuntimeError('Server khong xac nhan huy goal; kiem tra robot tren RViz')
            if self.result_future is None:
                self.result_future = self.goal_handle.get_result_async()
            result = self.wait_future(self.result_future, 5.0)
            self.get_logger().info(f'Action da ket thuc sau lenh huy: status={result.status}')

    def run(self):
        """Chay cac goal da khao sat, dung ngay khi mot goal khong thanh cong."""
        self.wait_ready()
        self.results['status'] = 'RUNNING'
        self.flush_results()
        for index, goal in enumerate(self.goals, 1):
            self.goal_handle = self.send_future = self.result_future = None
            request = NavigateToPose.Goal()
            request.pose.header.frame_id = 'map'
            request.pose.header.stamp = self.get_clock().now().to_msg()
            request.pose.pose.position.x = goal['x']
            request.pose.pose.position.y = goal['y']
            request.pose.pose.orientation.z = math.sin(goal['yaw'] / 2.0)
            request.pose.pose.orientation.w = math.cos(goal['yaw'] / 2.0)
            record = {**goal, 'status': 'SENDING'}
            self.results['goals'].append(record)
            self.flush_results()
            self.get_logger().info(
                f'Gui goal {index}/{len(self.goals)}: '
                f'({goal["x"]:.3f}, {goal["y"]:.3f}, {goal["yaw"]:.3f} rad)')
            self.send_future = self.client.send_goal_async(
                request, feedback_callback=self.on_feedback)
            self.goal_handle = self.wait_future(self.send_future, 15.0)
            if not self.goal_handle or not self.goal_handle.accepted:
                record['status'] = 'REJECTED'
                self.flush_results()
                raise RuntimeError(f'Goal {index} bi tu choi')
            record['goal_uuid'] = bytes(self.goal_handle.goal_id.uuid).hex()
            record['status'] = 'ACCEPTED'
            self.flush_results()
            self.result_future = self.goal_handle.get_result_async()
            start_sim = self.get_clock().now().nanoseconds / 1e9
            start_wall = time.monotonic()
            while rclpy.ok() and not self.result_future.done():
                rclpy.spin_once(self, timeout_sec=0.1)
                elapsed_sim = self.get_clock().now().nanoseconds / 1e9 - start_sim
                if elapsed_sim < 0:
                    raise RuntimeError('Clock da reset giua hanh trinh; dung va khoi dong lai')
                if (elapsed_sim > self.get_parameter('goal_timeout').value or
                        time.monotonic() - start_wall > self.get_parameter('wall_timeout').value):
                    record['status'] = 'TIMEOUT'
                    self.flush_results()
                    raise TimeoutError(f'Goal {index} qua thoi gian; huy action')
            result = self.result_future.result()
            record['elapsed_wall_sec'] = round(time.monotonic() - start_wall, 3)
            record['elapsed_sim_sec'] = round(
                self.get_clock().now().nanoseconds / 1e9 - start_sim, 3)
            record['action_status'] = result.status
            record['error_code'] = int(getattr(result.result, 'error_code', 0))
            record['error_msg'] = str(getattr(result.result, 'error_msg', ''))
            status_names = {GoalStatus.STATUS_SUCCEEDED: 'SUCCEEDED',
                            GoalStatus.STATUS_CANCELED: 'CANCELED',
                            GoalStatus.STATUS_ABORTED: 'ABORTED'}
            record['status'] = status_names.get(result.status, 'FAILED')
            self.flush_results()
            if result.status != GoalStatus.STATUS_SUCCEEDED:
                raise RuntimeError(f'Goal {index}: {record["status"]}; dung chuoi goal')
            self.get_logger().info(f'Goal {index}/{len(self.goals)} SUCCEEDED')
            self.goal_handle = self.send_future = self.result_future = None
            pause_deadline = time.monotonic() + self.get_parameter('pause_at_goal').value
            while time.monotonic() < pause_deadline:
                rclpy.spin_once(self, timeout_sec=0.1)
        self.results['status'] = 'SUCCEEDED'
        self.flush_results()
        self.get_logger().info(f'Hoan thanh {len(self.goals)} goal. Ket qua: {self.results_file}')


def interrupt_handler(signum, frame):
    """Giu context ROS de co the huy action khi nhan SIGINT/SIGTERM."""
    del signum, frame
    raise KeyboardInterrupt


def main(args=None):
    """Khoi chay node; huy goal truoc khi shutdown va tra exit code dung."""
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    previous = {sig: signal.signal(sig, interrupt_handler)
                for sig in (signal.SIGINT, signal.SIGTERM)}
    node = None
    exit_code = 0
    try:
        node = SequentialNavigator()
        node.run()
    except (KeyboardInterrupt, Exception) as error:
        exit_code = 130 if isinstance(error, KeyboardInterrupt) else 1
        if node:
            node.get_logger().error(str(error) or 'Dung theo yeu cau nguoi dung')
            node.results['status'] = 'INTERRUPTED' if exit_code == 130 else 'FAILED'
            try:
                node.cancel_active()
            except Exception as cancel_error:
                node.get_logger().error(f'Chua xac nhan huy action: {cancel_error}')
                node.results['cancel_error'] = str(cancel_error)
            if node.results['goals'] and node.results['goals'][-1]['status'] in (
                    'SENDING', 'ACCEPTED'):
                node.results['goals'][-1]['status'] = 'INTERRUPTED'
            node.results['reason'] = str(error) or 'Ctrl+C/SIGTERM'
            node.flush_results()
        else:
            print(f'Khong khoi tao duoc navigation: {error}')
    finally:
        if node:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())

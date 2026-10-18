"""Action server gia kiem tra thu tu, loi va huy; khong mo phong vat ly."""

import json
import threading
import time

from geometry_msgs.msg import PoseWithCovarianceStamped, TransformStamped
from lifecycle_msgs.msg import State
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateToPose
import pytest
import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from tf2_ros import TransformBroadcaster

from turtlebot4_slam_nav.goal_utils import save_goals
from turtlebot4_slam_nav.navigate_goals import SequentialNavigator


class FakeNav2(Node):
    """Cung cap lifecycle, pose, TF va action cho kiem thu DDS local."""

    def __init__(self, outcome):
        """Cac toa do test chi chay trong server gia, khong toi robot."""
        super().__init__('fake_nav2')
        self.outcome = outcome
        self.requests = []
        self.completed = []
        group = ReentrantCallbackGroup()
        for name in ('amcl', 'bt_navigator'):
            self.create_service(GetState, f'/{name}/get_state', self.get_state,
                                callback_group=group)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                         reliability=ReliabilityPolicy.RELIABLE)
        self.pose_pub = self.create_publisher(PoseWithCovarianceStamped, '/amcl_pose', qos)
        self.broadcaster = TransformBroadcaster(self)
        self.create_timer(0.05, self.publish_pose, callback_group=group)
        self.server = ActionServer(self, NavigateToPose, '/navigate_to_pose',
                                   self.execute, goal_callback=self.accept,
                                   cancel_callback=lambda _: CancelResponse.ACCEPT,
                                   callback_group=group)

    def get_state(self, request, response):
        """Gia lap lifecycle active."""
        del request
        response.current_state.id = State.PRIMARY_STATE_ACTIVE
        return response

    def publish_pose(self):
        """Gui map pose va TF moi de kiem tra readiness that."""
        pose = PoseWithCovarianceStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.pose.orientation.w = 1.0
        self.pose_pub.publish(pose)
        transform = TransformStamped()
        transform.header = pose.header
        transform.child_frame_id = 'base_link'
        transform.transform.rotation.w = 1.0
        self.broadcaster.sendTransform(transform)

    def accept(self, request):
        """Xac nhan goal truoc ket thuc goal truoc la loi trong test."""
        assert len(self.completed) == len(self.requests)
        self.requests.append(request)
        if self.outcome == 'reject' and len(self.requests) == 2:
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def execute(self, handle):
        """Tra ket qua mong doi hoac doi lenh cancel."""
        index = len(self.requests)
        if self.outcome == 'timeout':
            deadline = time.monotonic() + 10
            while not handle.is_cancel_requested and time.monotonic() < deadline:
                time.sleep(0.02)
            assert handle.is_cancel_requested
            handle.canceled()
        else:
            time.sleep(0.1)
            if self.outcome == 'abort' and index == 2:
                handle.abort()
            else:
                handle.succeed()
        self.completed.append(index)
        return NavigateToPose.Result()


@pytest.mark.parametrize('outcome,expected_count', [
    ('success', 3), ('abort', 2), ('reject', 2), ('timeout', 1),
])
def test_sequence_and_stop_on_failure(tmp_path, outcome, expected_count):
    """Thu gui action that qua DDS va dam bao khong bo qua goal loi."""
    filename = tmp_path / 'goals.yaml'
    result_file = tmp_path / 'results.json'
    save_goals(filename, [{'x': float(i), 'y': 0.0, 'yaw': 0.5} for i in range(3)])
    timeout = 0.25 if outcome == 'timeout' else 10.0
    rclpy.init(args=[
        '--ros-args', '-p', f'goals_file:={filename}', '-p',
        f'results_file:={result_file}', '-p', 'ready_timeout:=10.0',
        '-p', f'goal_timeout:={timeout}', '-p', 'pause_at_goal:=0.0'], domain_id=197)
    server = FakeNav2(outcome)
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(server)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    navigator = SequentialNavigator()
    try:
        if outcome == 'success':
            navigator.run()
        else:
            with pytest.raises((RuntimeError, TimeoutError)):
                navigator.run()
            navigator.cancel_active()
        assert len(server.requests) == expected_count
        data = json.loads(result_file.read_text())
        if outcome == 'success':
            assert data['status'] == 'SUCCEEDED'
            assert all(goal['status'] == 'SUCCEEDED' for goal in data['goals'])
            assert len({goal['goal_uuid'] for goal in data['goals']}) == 3
        else:
            assert data['goals'][-1]['status'] == {
                'abort': 'ABORTED', 'reject': 'REJECTED', 'timeout': 'TIMEOUT'}[outcome]
        for index, request in enumerate(server.requests):
            assert request.pose.header.frame_id == 'map'
            assert request.pose.pose.position.x == float(index)
    finally:
        navigator.destroy_node()
        executor.shutdown(timeout_sec=3)
        thread.join(timeout=3)
        server.destroy_node()
        rclpy.shutdown()

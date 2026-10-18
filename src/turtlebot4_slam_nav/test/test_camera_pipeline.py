"""Kiem tra ROS Image -> cv_bridge -> model -> anh/JSON, model gia."""

import json
import time
from types import SimpleNamespace

from cv_bridge import CvBridge
from geometry_msgs.msg import PointStamped, PoseWithCovarianceStamped
import numpy as np
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

from turtlebot4_slam_nav.goal_recorder import GoalRecorder
from turtlebot4_slam_nav.goal_utils import load_goals
from turtlebot4_slam_nav.yolo_detector import YoloDetector


class FakeModel:
    """Model gia de kiem tra RGB/BGR, box va stamp, khong danh gia YOLO."""

    task = 'detect'

    def __init__(self, filename):
        """Giu frame da nhan de kiem tra dung thu tu kenh."""
        del filename
        self.seen_frame = None

    def predict(self, source, **kwargs):
        """Tra box co class/conf toa do de kiem tra serialization."""
        del kwargs
        self.seen_frame = source.copy()
        boxes = [SimpleNamespace(cls=np.array([56]), conf=np.array([0.93]),
                                 xyxy=np.array([[1.0, 2.0, 8.0, 9.0]]))]
        annotated = source.copy()
        annotated[0, 0] = [0, 255, 0]
        return [SimpleNamespace(boxes=boxes, names={56: 'chair'}, plot=lambda: annotated)]


def test_camera_ros_pipeline(tmp_path):
    """Pub/sub that, header anh goc, BGR va payload detection duoc giu."""
    weights = tmp_path / 'fake.pt'
    weights.touch()
    rclpy.init(args=[
        '--ros-args', '-p', f'model_path:={weights}',
        '-p', 'image_topic:=/test/camera', '-p', 'image_size:=320'], domain_id=197)
    node = YoloDetector(model_factory=FakeModel)
    probe = Node('camera_probe')
    publisher = probe.create_publisher(Image, '/test/camera', qos_profile_sensor_data)
    images, reports = [], []
    probe.create_subscription(Image, '/yolo/annotated_image', images.append,
                              qos_profile_sensor_data)
    probe.create_subscription(String, '/yolo/detections', reports.append, 10)
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    executor.add_node(probe)
    bridge = CvBridge()
    frame = np.zeros((12, 16, 3), dtype=np.uint8)
    frame[:, :] = [11, 22, 33]
    message = bridge.cv2_to_imgmsg(frame, 'rgb8')
    message.header.frame_id = 'test_camera_optical'
    message.header.stamp.sec = 123
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not (images and reports):
            publisher.publish(message)
            executor.spin_once(timeout_sec=0.05)
        assert images and reports
        assert node.model.seen_frame[1, 1].tolist() == [33, 22, 11]
        image = images[-1]
        assert image.header == message.header
        assert image.encoding == 'bgr8'
        assert bridge.imgmsg_to_cv2(image)[0, 0].tolist() == [0, 255, 0]
        report = json.loads(reports[-1].data)
        assert report['stamp']['sec'] == 123
        assert (report['width'], report['height']) == (16, 12)
        assert report['detections'] == [{
            'class_id': 56, 'class_name': 'chair', 'confidence': 0.93,
            'bbox_xyxy': [1.0, 2.0, 8.0, 9.0]}]
    finally:
        node.close()
        executor.shutdown()
        node.destroy_node()
        probe.destroy_node()
        rclpy.shutdown()


def test_recorder_rejects_wrong_frame_and_preserves_yaw(tmp_path):
    """Click sai frame/trung diem khong sua YAML, pose AMCL giu yaw."""
    filename = tmp_path / 'goals.yaml'
    rclpy.init(args=['--ros-args', '-p', f'output_file:={filename}', '-p', 'yaw:=0.5'],
               domain_id=197)
    node = GoalRecorder()
    try:
        point = PointStamped()
        point.header.frame_id = 'odom'
        point.point.x = 1.0
        node.on_point(point)
        assert not filename.exists()
        point.header.frame_id = 'map'
        node.on_point(point)
        before = filename.read_bytes()
        node.on_point(point)
        assert filename.read_bytes() == before
        pose = PoseWithCovarianceStamped()
        pose.header.frame_id = 'map'
        pose.pose.pose.position.y = 3.0
        pose.pose.pose.orientation.z = 2 ** -0.5
        pose.pose.pose.orientation.w = 2 ** -0.5
        node.on_amcl(pose)
        from std_srvs.srv import Trigger
        response = node.record_pose(Trigger.Request(), Trigger.Response())
        assert response.success
        goals = load_goals(filename, minimum=2)
        assert goals[0]['yaw'] == pytest.approx(0.5)
        assert goals[1]['yaw'] == pytest.approx(np.pi / 2)
    finally:
        node.destroy_node()
        rclpy.shutdown()

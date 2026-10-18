"""Nhan anh RGB, suy luan YOLO va publish anh co bounding box."""

import json
import math
from pathlib import Path
import threading
import time

from cv_bridge import CvBridge
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String


class YoloDetector(Node):
    """Worker xu ly anh moi nhat; khong tich luy hang doi camera."""

    def __init__(self, model_factory=None):
        """Nap weights local, khong tu tai weights trong luc demo."""
        super().__init__('yolo_detector')
        defaults = {
            'image_topic': '/oakd/rgb/preview/image_raw',
            'annotated_topic': '/yolo/annotated_image',
            'detections_topic': '/yolo/detections',
            'model_path': str(Path.home() / 'tb4_ws/models/yolo11n.pt'),
            'confidence': 0.4, 'image_size': 416, 'device': 'cpu',
            'max_fps': 3.0, 'cpu_threads': 2, 'log_interval': 2.0, 'show_window': False,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        self.confidence = self.get_parameter('confidence').value
        self.image_size = self.get_parameter('image_size').value
        self.max_fps = self.get_parameter('max_fps').value
        self.log_interval = self.get_parameter('log_interval').value
        self.show_window = self.get_parameter('show_window').value
        if not math.isfinite(self.confidence) or not 0 < self.confidence <= 1:
            raise ValueError('confidence phai nam trong (0, 1]')
        if self.image_size < 32 or self.image_size % 32:
            raise ValueError('image_size phai >= 32 va chia het cho 32')
        if not math.isfinite(self.max_fps) or not 0 < self.max_fps <= 60:
            raise ValueError('max_fps phai nam trong (0, 60]')
        if not math.isfinite(self.log_interval) or self.log_interval <= 0:
            raise ValueError('log_interval phai > 0')
        if self.get_parameter('cpu_threads').value < 1:
            raise ValueError('cpu_threads phai >= 1')
        model_path = Path(self.get_parameter('model_path').value).expanduser().resolve()
        if not model_path.is_file():
            raise ValueError(f'Chua co model: {model_path}; chay scripts/setup_yolo.sh truoc')
        if model_factory is None:
            try:
                from ultralytics import YOLO
                import torch
            except ImportError as error:
                raise RuntimeError('Can chay node bang .venv-yolo/bin/python') from error
            torch.set_num_threads(self.get_parameter('cpu_threads').value)
            model_factory = YOLO
        self.model = model_factory(str(model_path))
        if getattr(self.model, 'task', 'detect') != 'detect':
            raise ValueError('Can model YOLO detection, vi du yolo11n.pt')
        self.bridge = CvBridge()
        self.lock = threading.Lock()
        self.wakeup = threading.Event()
        self.stop_event = threading.Event()
        self.latest = None
        self.output = None
        self.last_image_wall = None
        self.last_log = 0.0
        self.failure = None
        self.image_pub = self.create_publisher(
            Image, self.get_parameter('annotated_topic').value, qos_profile_sensor_data)
        self.detections_pub = self.create_publisher(
            String, self.get_parameter('detections_topic').value, 10)
        self.create_subscription(Image, self.get_parameter('image_topic').value,
                                 self.on_image, qos_profile_sensor_data)
        self.started_wall = time.monotonic()
        self.next_warning = self.started_wall + 10.0
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(0.05, self.publish_output, clock=self.steady_clock)
        self.worker = threading.Thread(target=self.infer_loop, daemon=True)
        self.worker.start()
        self.get_logger().info(
            f'YOLO san sang: {model_path.name}; input='
            f'{self.get_parameter("image_topic").value}; max_fps={self.max_fps}')

    def on_image(self, message):
        """Giu duy nhat anh moi nhat, QoS Best Effort cho camera."""
        with self.lock:
            self.latest = message
            self.last_image_wall = time.monotonic()
        self.wakeup.set()

    def infer_loop(self):
        """Xu ly OpenCV/YOLO ngoai callback ROS."""
        next_frame = 0.0
        while not self.stop_event.is_set():
            self.wakeup.wait(timeout=0.2)
            if self.stop_event.wait(max(0.0, next_frame - time.monotonic())):
                break
            with self.lock:
                message = self.latest
                self.latest = None
                self.wakeup.clear()
            if message is None:
                continue
            started = time.monotonic()
            try:
                frame = self.bridge.imgmsg_to_cv2(message, desired_encoding='bgr8')
                result = self.model.predict(
                    source=frame, conf=self.confidence, imgsz=self.image_size,
                    device=self.get_parameter('device').value, verbose=False)[0]
                detections = []
                if result.boxes is not None:
                    for box in result.boxes:
                        class_id = int(box.cls.item())
                        detections.append({
                            'class_id': class_id, 'class_name': result.names[class_id],
                            'confidence': round(float(box.conf.item()), 4),
                            'bbox_xyxy': [round(float(value), 1)
                                          for value in box.xyxy[0].tolist()],
                        })
                annotated = self.bridge.cv2_to_imgmsg(result.plot(), encoding='bgr8')
                annotated.header = message.header
                report = {
                    'stamp': {'sec': message.header.stamp.sec,
                              'nanosec': message.header.stamp.nanosec},
                    'frame_id': message.header.frame_id,
                    'width': message.width, 'height': message.height,
                    'inference_ms': round((time.monotonic() - started) * 1000, 1),
                    'detections': detections,
                }
                with self.lock:
                    self.output = (annotated, report)
            except Exception as error:
                with self.lock:
                    self.failure = str(error)
            next_frame = started + 1.0 / self.max_fps

    def publish_output(self):
        """Publish anh/JSON va hien thi cua so trong thread ROS chinh."""
        with self.lock:
            output, self.output = self.output, None
            failure, self.failure = self.failure, None
            last_image = self.last_image_wall
        now = time.monotonic()
        if failure:
            self.get_logger().error(f'Loi suy luan YOLO: {failure}', throttle_duration_sec=5.0)
        if now >= self.next_warning and (last_image is None or now - last_image > 10.0):
            self.get_logger().warning(
                'Chua nhan anh moi: kiem tra camera topic, QoS va Gazebo Play')
            self.next_warning = now + 10.0
        if output is None:
            return
        annotated, report = output
        self.image_pub.publish(annotated)
        message = String()
        message.data = json.dumps(report, ensure_ascii=False)
        self.detections_pub.publish(message)
        if now - self.last_log >= self.log_interval:
            objects = report['detections']
            description = '; '.join(
                f'{item["class_name"]} conf={item["confidence"]:.2f} '
                f'bbox={item["bbox_xyxy"]}' for item in objects)
            self.get_logger().info(
                f'{len(objects)} vat the; {report["inference_ms"]:.0f} ms: '
                f'{description or "khong co detection tren frame nay"}')
            self.last_log = now
        if self.show_window:
            import cv2
            try:
                cv2.imshow('TurtleBot 4 - YOLO', self.bridge.imgmsg_to_cv2(annotated, 'bgr8'))
                cv2.waitKey(1)
            except cv2.error as error:
                self.get_logger().error(f'Khong mo duoc cua so: {error}; xem Image tren RViz')
                self.show_window = False

    def close(self):
        """Dung worker truoc khi dong publisher ROS."""
        self.stop_event.set()
        self.wakeup.set()
        self.worker.join(timeout=10.0)
        if self.show_window:
            import cv2
            cv2.destroyAllWindows()


def main(args=None):
    """Chay YOLO rieng voi node dieu huong."""
    rclpy.init(args=args)
    node = None
    exit_code = 0
    try:
        node = YoloDetector()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except Exception as error:
        print(f'Khong chay duoc YOLO: {error}')
        exit_code = 1
    finally:
        if node:
            node.close()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())

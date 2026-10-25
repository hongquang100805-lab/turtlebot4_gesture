"""Laptop webcam -> MediaPipe Gesture Recognizer -> ROS 2 String heartbeat."""

import json
from pathlib import Path
import signal
import threading
import time

import cv2
import numpy as np
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import Image
from std_msgs.msg import String

from turtlebot4_gesture_control.gesture_logic import GESTURES, WaveDetector


CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
               (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
               (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]


class GestureRecognitionNode(Node):
    """Publish only current trusted observations; no keyboard movement controls."""

    def __init__(self):
        super().__init__('gesture_recognition_node')
        defaults = {'camera_index': 0, 'confidence': 0.65, 'max_fps': 15.0,
                    'frame_timeout': 0.35, 'show_window': True, 'mirror': True,
                    'model_path': str(Path.home() / 'tb4_ws/models/gesture_recognizer.task')}
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        self.threshold = float(self.get_parameter('confidence').value)
        self.max_fps = float(self.get_parameter('max_fps').value)
        self.frame_timeout = float(self.get_parameter('frame_timeout').value)
        if not 0 < self.threshold <= 1 or not 1 <= self.max_fps <= 60 or self.frame_timeout <= 0:
            raise ValueError('Invalid confidence, max_fps or frame_timeout')
        self.model_path = Path(self.get_parameter('model_path').value).expanduser()
        if not self.model_path.is_file():
            raise ValueError('Missing gesture_recognizer.task; run scripts/setup_gesture.sh')
        self.pub = self.create_publisher(String, '/detected_gesture', 1)
        self.debug = self.create_publisher(String, '/gesture_recognition/debug', 1)
        self.images = self.create_publisher(Image, '/gesture_recognition/image', 1)
        self.create_subscription(String, '/robot_behavior_state', self.on_state, QoSProfile(
            depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.behavior = 'Waiting for robot_behavior_node'
        self.lock = threading.Lock()
        self.latest = None
        self.failure = None
        self.stop_event = threading.Event()
        self.window = 'Lab 06 - Webcam hand gestures'
        self.show_window = self.get_parameter('show_window').value
        self.last_log = None
        self.steady = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(0.1, self.tick, clock=self.steady)
        self.worker = threading.Thread(target=self.capture_loop, daemon=True)
        self.worker.start()

    def on_state(self, msg):
        try:
            s = json.loads(msg.data)
            self.behavior = (f'{s["state"]}: {s.get("selected") or s["reason"]}'
                             f' | ready={s["ready"]}')
        except (KeyError, ValueError):
            pass

    def capture_loop(self):
        camera = recognizer = None
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            cv2.setNumThreads(1)
            options = vision.GestureRecognizerOptions(
                base_options=python.BaseOptions(model_asset_path=str(self.model_path)),
                running_mode=vision.RunningMode.VIDEO, num_hands=1,
                min_hand_detection_confidence=0.6, min_hand_presence_confidence=0.6,
                min_tracking_confidence=0.6)
            recognizer = vision.GestureRecognizer.create_from_options(options)
            camera = cv2.VideoCapture(self.get_parameter('camera_index').value, cv2.CAP_V4L2)
            if not camera.isOpened():
                raise RuntimeError('Cannot open webcam; check /dev/video0 and camera_index')
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            wave = WaveDetector()
            last_timestamp = -1
            while not self.stop_event.is_set():
                started = time.monotonic()
                ok, frame = camera.read()
                if not ok:
                    raise RuntimeError('Webcam frame read failed')
                captured = time.monotonic()
                if self.get_parameter('mirror').value:
                    frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                timestamp = max(last_timestamp + 1, int(captured * 1000))
                last_timestamp = timestamp
                result = recognizer.recognize_for_video(image, timestamp)
                raw, score, hand, gesture = 'None', 0.0, '', 'None'
                if result.gestures and result.gestures[0]:
                    category = result.gestures[0][0]
                    raw, score = category.category_name, float(category.score)
                if result.handedness and result.handedness[0]:
                    hand = result.handedness[0][0].category_name
                points = result.hand_landmarks[0] if result.hand_landmarks else []
                if points and score >= self.threshold:
                    # Fingertips also move when waving about a nearly fixed wrist.
                    hand_x = sum(points[i].x for i in (8, 12, 16, 20)) / 4
                    gesture = ('Wave' if wave.update(captured, hand_x, raw, hand)
                               else raw if raw in GESTURES else 'None')
                else:
                    wave.update(captured, None, 'None', hand)
                height, width = frame.shape[:2]
                xy = [(int(p.x * width), int(p.y * height)) for p in points]
                for a, b in CONNECTIONS:
                    if xy:
                        cv2.line(frame, xy[a], xy[b], (30, 210, 30), 2)
                for point in xy:
                    cv2.circle(frame, point, 3, (0, 80, 255), -1)
                packet = {'gesture': gesture, 'confidence': round(score, 4),
                          'model_label': raw, 'handedness': hand,
                          'captured_wall': captured,
                          'inference_ms': round((time.monotonic() - captured) * 1000, 1),
                          'wave_method': 'AI open palm + temporal lateral reversals'}
                with self.lock:
                    self.latest = (frame, packet)
                self.stop_event.wait(max(0.0, 1 / self.max_fps - (time.monotonic() - started)))
        except Exception as error:
            with self.lock:
                self.failure = str(error)
        finally:
            if camera is not None:
                camera.release()
            if recognizer is not None:
                recognizer.close()

    def tick(self):
        with self.lock:
            sample, failure = self.latest, self.failure
        packet = dict(sample[1]) if sample else {'gesture': 'None', 'confidence': 0.0}
        if sample is None or time.monotonic() - packet['captured_wall'] > self.frame_timeout:
            packet.update(gesture='None', confidence=0.0, stale=True)
        self.pub.publish(String(data=packet['gesture']))
        self.debug.publish(String(data=json.dumps(packet)))
        if packet['gesture'] != self.last_log:
            self.get_logger().info(f'{packet["gesture"]}, confidence={packet["confidence"]:.2f}')
            self.last_log = packet['gesture']
        if failure:
            self.get_logger().error(failure)
            self.stop_event.set()
            rclpy.shutdown()
            return
        if sample:
            frame = sample[0].copy()
            canvas = np.zeros((frame.shape[0] + 120, frame.shape[1], 3), dtype=np.uint8)
            canvas[:frame.shape[0]] = frame
            text = f'{packet["gesture"]} | confidence {packet["confidence"]:.2f}'
            cv2.putText(canvas, text, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 255, 255), 2)
            for i, text in enumerate([
                    self.behavior, 'Wave / Pointing Up / Victory: SELECT',
                    'Thumb Up: CONFIRM | Open Palm: STOP | Fist: CANCEL',
                    'Keep hand visible while running. No hand = STOP.']):
                cv2.putText(canvas, text[:83], (10, frame.shape[0] + 23 + i * 27),
                            cv2.FONT_HERSHEY_SIMPLEX, .43, (235, 235, 235), 1)
            msg = Image()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'laptop_webcam'
            msg.height, msg.width = canvas.shape[:2]
            msg.encoding, msg.step = 'bgr8', canvas.shape[1] * 3
            msg.data = canvas.tobytes()
            self.images.publish(msg)
            if self.show_window:
                cv2.imshow(self.window, canvas)
                cv2.waitKey(1)  # Pump GUI events only; keys never control robot motion.
                if cv2.getWindowProperty(self.window, cv2.WND_PROP_VISIBLE) < 1:
                    self.stop_event.set()
                    rclpy.shutdown()

    def close(self):
        self.stop_event.set()
        if rclpy.ok():
            self.pub.publish(String(data='None'))
        self.worker.join(timeout=2)
        if self.show_window:
            cv2.destroyAllWindows()


def interrupt(signum, frame):
    del signum, frame
    raise KeyboardInterrupt


def main(args=None):
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    previous = {s: signal.signal(s, interrupt) for s in (signal.SIGINT, signal.SIGTERM)}
    node = None
    code = 0
    try:
        node = GestureRecognitionNode()
        rclpy.spin(node)
        code = 1 if node.failure else 0
    except KeyboardInterrupt:
        pass
    finally:
        if node:
            node.close()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        for s, handler in previous.items():
            signal.signal(s, handler)
    return code


if __name__ == '__main__':
    raise SystemExit(main())

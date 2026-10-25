"""Temporal wave recognition and debounced, confirmed robot behavior."""

from collections import deque
from dataclasses import dataclass
import math


GESTURES = {'Wave', 'Pointing_Up', 'Victory', 'Thumb_Up', 'Open_Palm', 'Closed_Fist'}
SELECTIONS = {'Wave': 'greeting', 'Pointing_Up': 'back_and_forth', 'Victory': 'circle'}


class WaveDetector:
    """Recognize repeated lateral movement of an AI-classified open palm."""

    def __init__(self, window=3.0, amplitude=0.09, hysteresis=0.025):
        self.window = window
        self.amplitude = amplitude
        self.hysteresis = hysteresis
        self.history = deque()
        self.hand = None
        self.motion_x = None
        self.motion_at = None

    def reset(self):
        self.history.clear()
        self.hand = None
        self.motion_x = None
        self.motion_at = None

    def update(self, now, x, label, hand=''):
        if label == 'None':
            # Retain a short uncertain observation in the trajectory only.
            # The caller still publishes None, never Wave, for this frame.
            if self.history and now - self.history[-1][0] > 0.25:
                self.reset()
            return False
        if label != 'Open_Palm' or x is None or not math.isfinite(x):
            self.reset()
            return False
        if self.hand != hand or (self.history and (
                now - self.history[-1][0] > 0.55 or abs(x - self.history[-1][1]) > 0.35)):
            self.reset()
        self.hand = hand
        if self.motion_x is None or abs(x - self.motion_x) >= 0.006:
            self.motion_x, self.motion_at = x, now
        self.history.append((now, x))
        while self.history and now - self.history[0][0] > self.window:
            self.history.popleft()
        if now - self.motion_at > 0.25:
            self.history.clear()
            self.history.append((now, x))
            return False
        values = [v for _, v in self.history]
        if max(values) - min(values) < self.amplitude:
            return False
        extreme = values[0]
        direction = 0
        turns = 0
        last_turn = None
        for value in values[1:]:
            delta = value - extreme
            if direction == 0:
                if abs(delta) >= self.hysteresis:
                    direction = 1 if delta > 0 else -1
                    extreme = value
            elif delta * direction >= 0:
                extreme = value
            elif abs(delta) >= self.hysteresis:
                turns += 1
                direction *= -1
                extreme = value
                last_turn = value
        # Two reversals distinguish a wave from one swipe. Old motion must not
        # mask a stationary open-palm stop after the person stops waving.
        return turns >= 2 and last_turn is not None


@dataclass
class BehaviorConfig:
    """Distances in metres, angles in radians, timeouts in wall seconds."""

    stable_time: float = 0.35
    signal_timeout: float = 0.65
    sensor_timeout: float = 0.8
    selection_timeout: float = 10.0
    motion_timeout: float = 180.0
    linear_speed: float = 0.24
    angular_speed: float = 0.90
    stroke_distance: float = 0.35
    circle_radius: float = 0.6
    greeting_angle: float = 0.45
    obstacle_distance: float = 0.35

    def __post_init__(self):
        for value in vars(self).values():
            if not math.isfinite(value) or value <= 0:
                raise ValueError('Behavior parameters must be finite and positive')
        if self.linear_speed > 0.25 or self.angular_speed > 1.0:
            raise ValueError('Demo speed limits: linear <= 0.25, angular <= 1.0')
        if self.linear_speed / self.circle_radius > 1.0:
            raise ValueError('Circle angular speed exceeds 1 rad/s')
        if self.stable_time >= self.signal_timeout:
            raise ValueError('stable_time must be smaller than signal_timeout')


class BehaviorEngine:
    """Pure state machine; all movement requires a new explicit confirmation."""

    def __init__(self, config=None):
        self.config = config or BehaviorConfig()
        self.state = 'IDLE'
        self.reason = 'Select Wave, Pointing_Up or Victory; confirm with Thumb_Up'
        self.selected = None
        self.steps = []
        self.step_index = 0
        self.progress = 0.0
        self.started = None
        self.last_signal = None
        self.candidate = None
        self.candidate_since = 0.0
        self.emitted = None
        self.selected_at = 0.0

    def stop(self, state, reason):
        self.state, self.reason = state, reason
        self.selected = None
        self.steps = []
        self.progress = 0.0

    def feed(self, gesture, now, ready=True):
        if gesture not in GESTURES:
            self.candidate = None
            return
        self.last_signal = now
        if gesture in ('Open_Palm', 'Closed_Fist'):
            self.stop('STOPPED' if gesture == 'Open_Palm' else 'IDLE', gesture)
            self.candidate = gesture
            self.candidate_since = now
            self.emitted = gesture
            return
        if gesture != self.candidate:
            self.candidate, self.candidate_since = gesture, now
        if now - self.candidate_since < self.config.stable_time or self.emitted == gesture:
            return
        self.emitted = gesture
        if self.state == 'RUNNING':
            return
        if gesture in SELECTIONS:
            self.selected = SELECTIONS[gesture]
            self.selected_at = now
            self.state, self.reason = 'SELECTED', 'Show Thumb_Up to confirm'
        elif gesture == 'Thumb_Up' and self.selected is not None:
            if not ready:
                self.stop('NOT_READY', 'Need fresh odom/scan, no bump, and robot undocked')
            elif now - self.selected_at > self.config.selection_timeout:
                self.stop('IDLE', 'Selection expired')
            else:
                self.start(now)

    def start(self, now):
        c = self.config
        if self.selected == 'greeting':
            self.steps = [('angle', c.greeting_angle, 0.0, c.angular_speed),
                          ('angle', c.greeting_angle * 2, 0.0, -c.angular_speed),
                          ('angle', c.greeting_angle, 0.0, c.angular_speed)]
        elif self.selected == 'back_and_forth':
            self.steps = [('distance', c.stroke_distance, c.linear_speed * sign, 0.0)
                          for _ in range(4) for sign in (1, -1)]
        elif self.selected == 'circle':
            self.steps = [('angle', math.tau, c.linear_speed,
                           c.linear_speed / c.circle_radius)]
        self.state, self.reason = 'RUNNING', self.selected
        self.started, self.step_index, self.progress = now, 0, 0.0

    def odometry(self, distance, yaw_delta):
        if self.state == 'RUNNING':
            kind = self.steps[self.step_index][0]
            self.progress += distance if kind == 'distance' else abs(yaw_delta)

    def tick(self, now, sensors_ready=True, front=math.inf, rear=math.inf,
             surrounding=math.inf, bump=False):
        c = self.config
        if self.last_signal is None or now - self.last_signal > c.signal_timeout:
            if self.state in ('RUNNING', 'SELECTED'):
                self.stop('SIGNAL_LOST', 'No valid hand/control heartbeat; select again')
            self.emitted = None
            return 0.0, 0.0
        if self.state == 'SELECTED' and now - self.selected_at > c.selection_timeout:
            self.stop('IDLE', 'Selection expired')
        if self.state != 'RUNNING':
            return 0.0, 0.0
        if not sensors_ready or bump:
            self.stop('SAFETY_STOP', 'Sensor lost, robot docked, or bumper detected')
            return 0.0, 0.0
        if now - self.started > c.motion_timeout:
            self.stop('TIMEOUT', 'Behavior exceeded wall-time limit')
            return 0.0, 0.0
        _, target, v, w = self.steps[self.step_index]
        if self.progress >= target:
            self.step_index += 1
            self.progress = 0.0
            if self.step_index == len(self.steps):
                self.stop('COMPLETED', 'Behavior complete; select again for another run')
            return 0.0, 0.0
        clearance = front if v > 0 else rear if v < 0 else surrounding
        if clearance < c.obstacle_distance:
            self.stop('OBSTACLE_STOP', 'Obstacle in movement direction; select again')
            return 0.0, 0.0
        return v, w

    def status(self):
        return {'state': self.state, 'selected': self.selected, 'reason': self.reason,
                'step': self.step_index + 1 if self.steps else 0,
                'steps': len(self.steps), 'progress': round(self.progress, 3)}

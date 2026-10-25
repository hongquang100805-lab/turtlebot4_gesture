"""Check confirmation, deadman behavior, motion completion and wave ambiguity."""

import math

import pytest
from turtlebot4_gesture_control.gesture_logic import BehaviorConfig, BehaviorEngine, WaveDetector


def hold(engine, gesture, t):
    engine.feed(gesture, t)
    engine.feed(gesture, t + 0.4)
    return t + 0.4


def running(selection='Victory'):
    e = BehaviorEngine()
    hold(e, selection, 0.0)
    hold(e, 'Thumb_Up', 0.5)
    assert e.state == 'RUNNING'
    return e


def test_selection_requires_confirmation_and_edge():
    e = BehaviorEngine()
    hold(e, 'Pointing_Up', 0.0)
    assert e.tick(.4) == (0, 0)
    assert e.state == 'SELECTED'
    hold(e, 'Thumb_Up', .5)
    assert e.tick(.9)[0] > 0
    assert len(e.steps) == 8
    e.stop('COMPLETED', 'test')
    hold(e, 'Thumb_Up', 1.0)
    assert e.tick(1.4) == (0, 0)
    assert e.state == 'COMPLETED'


@pytest.mark.parametrize('gesture,expected', [('Open_Palm', 'STOPPED'), ('Closed_Fist', 'IDLE')])
def test_stop_is_immediate_and_clears_selection(gesture, expected):
    e = running()
    e.feed(gesture, .91)
    assert e.state == expected
    assert e.tick(.91) == (0, 0)
    hold(e, 'Thumb_Up', 1.0)
    assert e.state != 'RUNNING'


def test_missing_or_unknown_hand_cannot_keep_moving():
    e = running()
    e.feed('None', 1.4)
    assert e.tick(1.56) == (0, 0)
    assert e.state == 'SIGNAL_LOST'
    hold(e, 'Thumb_Up', 1.6)
    assert e.state != 'RUNNING'


@pytest.mark.parametrize('kwargs', [{'sensors_ready': False}, {'front': .2}, {'bump': True}])
def test_sensor_and_obstacle_stop(kwargs):
    e = running()
    assert e.tick(.91, **kwargs) == (0, 0)
    assert e.state in ('SAFETY_STOP', 'OBSTACLE_STOP')


def test_reverse_uses_rear_clearance():
    e = running('Pointing_Up')
    e.odometry(.35, 0)
    assert e.tick(.91) == (0, 0)
    assert e.tick(.92, front=.1, rear=2)[0] < 0
    assert e.tick(.93, rear=.1) == (0, 0)


def test_four_complete_back_and_forth_cycles():
    e = running('Pointing_Up')
    for index in range(8):
        now = .91 + index * .01
        v, w = e.tick(now)
        assert v > 0 if index % 2 == 0 else v < 0
        assert w == 0
        e.odometry(.35, 0)
        assert e.tick(now) == (0, 0)
    assert e.state == 'COMPLETED'


def test_circle_and_greeting_finish_by_odometry():
    e = running('Victory')
    v, w = e.tick(.91)
    assert math.isclose(v / w, .6)
    e.odometry(0, math.tau)
    assert e.tick(.92) == (0, 0)
    assert e.state == 'COMPLETED'
    e = running('Wave')
    signs = []
    for _ in range(3):
        signs.append(math.copysign(1, e.tick(.91)[1]))
        e.odometry(0, e.steps[e.step_index][1])
        e.tick(.92)
    assert signs == [1, -1, 1]
    assert e.state == 'COMPLETED'


def test_selection_expiry_and_no_sensors_at_confirmation():
    e = BehaviorEngine()
    hold(e, 'Victory', 0)
    e.feed('Thumb_Up', 11)
    e.feed('Thumb_Up', 11.4)
    assert e.state == 'IDLE'
    hold(e, 'Victory', 12)
    e.feed('Thumb_Up', 12.5, ready=False)
    e.feed('Thumb_Up', 12.9, ready=False)
    assert e.state == 'NOT_READY'


def test_wave_requires_repeated_motion_not_static_palm_or_swipe():
    wave = WaveDetector()
    for i in range(30):
        assert not wave.update(i * .05, .5 + .002 * (i % 2), 'Open_Palm', 'Left')
    wave.reset()
    for i in range(20):
        assert not wave.update(i * .05, .2 + i * .015, 'Open_Palm', 'Left')
    wave.reset()
    detected = [wave.update(i * .05, .5 + .12 * math.sin(i * .6), 'Open_Palm', 'Left')
                for i in range(35)]
    assert any(detected)
    assert not wave.update(2.0, .5, 'Closed_Fist', 'Left')
    assert not wave.update(2.1, .5, 'Open_Palm', 'Right')


def test_noise_does_not_confirm():
    e = BehaviorEngine()
    for i, g in enumerate(['Victory', 'Thumb_Up'] * 10):
        e.feed(g, i * .05)
    assert e.state != 'RUNNING'


def test_slow_wave_with_brief_uncertain_frame_can_be_selected():
    wave, engine = WaveDetector(), BehaviorEngine()
    selected = False
    for i in range(45):
        now = i * .1
        x = .5 + .08 * math.sin(now * math.tau / 1.5)
        if i == 10:
            assert not wave.update(now, None, 'None', 'Left')
            gesture = 'None'
        else:
            gesture = 'Wave' if wave.update(now, x, 'Open_Palm', 'Left') else 'Open_Palm'
        engine.feed(gesture, now)
        selected |= engine.state == 'SELECTED'
        assert engine.state != 'RUNNING'
    assert selected


def test_past_wave_does_not_mask_stationary_palm_stop():
    wave = WaveDetector()
    for i in range(30):
        wave.update(i * .1, .5 + .08 * math.sin(i * .6), 'Open_Palm', 'Left')
    for i in range(10):
        detected = wave.update(3 + i * .1, .5, 'Open_Palm', 'Left')
        if i >= 3:
            assert not detected
    assert not wave.update(4.3, None, 'None', 'Left')
    assert not wave.history


def test_invalid_limits_are_rejected():
    with pytest.raises(ValueError):
        BehaviorConfig(linear_speed=1.0)
    with pytest.raises(ValueError):
        BehaviorConfig(signal_timeout=.1)

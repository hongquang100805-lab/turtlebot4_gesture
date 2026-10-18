"""Kiem tra du lieu goal sai de khong gui robot den diem vo nghia."""

import math
from types import SimpleNamespace

import pytest

from turtlebot4_slam_nav.goal_utils import load_goals, save_goals, validate_goals
from turtlebot4_slam_nav.goal_utils import yaw_from_quaternion


def document():
    """Ba diem phan biet dung cho kiem thu, khong phai route depot."""
    return {'frame_id': 'map', 'goals': [
        {'x': 0, 'y': 1, 'yaw': 0}, {'x': 1, 'y': 2, 'yaw': 1},
        {'x': 3, 'y': 4, 'yaw': 2},
    ]}


@pytest.mark.parametrize('value', [True, '1', None, float('inf'), float('nan')])
def test_invalid_coordinate(value):
    """Chuoi, bool, NaN va infinity khong duoc gui vao PoseStamped."""
    data = document()
    data['goals'][1]['x'] = value
    with pytest.raises(ValueError):
        validate_goals(data)


def test_reject_wrong_frame_too_few_and_duplicate():
    """Tu choi route thieu goal, sai frame hoac diem trung."""
    data = document()
    data['frame_id'] = 'odom'
    with pytest.raises(ValueError):
        validate_goals(data)
    data = document()
    data['goals'].pop()
    with pytest.raises(ValueError):
        validate_goals(data)
    data = document()
    data['goals'][2] = dict(data['goals'][0])
    with pytest.raises(ValueError):
        validate_goals(data)


def test_yaml_roundtrip_preserves_route(tmp_path):
    """Luu va doc giu nguyen thu tu, don vi va toa do."""
    filename = tmp_path / 'goals.yaml'
    goals = validate_goals(document())
    save_goals(filename, goals)
    assert load_goals(filename) == goals
    before = filename.read_bytes()
    with pytest.raises(ValueError):
        save_goals(filename, [goals[0], goals[0]])
    assert filename.read_bytes() == before


def test_quaternion_yaw():
    """Chuan hoa quaternion truoc khi lay yaw va tu choi quaternion rong."""
    quaternion = SimpleNamespace(x=0.0, y=0.0, z=2 ** 0.5, w=2 ** 0.5)
    assert yaw_from_quaternion(quaternion) == pytest.approx(math.pi / 2)
    quaternion.z = quaternion.w = 0.0
    with pytest.raises(ValueError):
        yaw_from_quaternion(quaternion)

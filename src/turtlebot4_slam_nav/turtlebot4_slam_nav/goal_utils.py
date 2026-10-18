"""Doc, kiem tra va luu cac toa do goal trong he map."""

import math
import os
from pathlib import Path
import tempfile

import yaml


def finite_number(value, label):
    """Chi chap nhan so huu han, khong chap nhan bool hay chuoi."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{label} phai la so')
    if not math.isfinite(value):
        raise ValueError(f'{label} phai huu han')
    return float(value)


def validate_goals(document, minimum=3):
    """Kiem tra frame, so goal va cac diem khac nhau truoc khi chay."""
    if not isinstance(document, dict) or document.get('frame_id') != 'map':
        raise ValueError('File goal phai co frame_id: map')
    raw = document.get('goals')
    if not isinstance(raw, list) or len(raw) < minimum:
        raise ValueError(f'Can it nhat {minimum} goal; hay ghi goal tu RViz')
    goals = []
    for index, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            raise ValueError(f'Goal {index} phai co x, y, yaw')
        pose = {key: finite_number(item.get(key), f'Goal {index}.{key}')
                for key in ('x', 'y', 'yaw')}
        pose['name'] = str(item.get('name', f'Goal {index}'))
        pose['yaw'] = math.atan2(math.sin(pose['yaw']), math.cos(pose['yaw']))
        if any(math.hypot(pose['x'] - old['x'], pose['y'] - old['y']) < 0.1
               for old in goals):
            raise ValueError(f'Goal {index} trung hoac qua gan goal da co (< 0.1 m)')
        goals.append(pose)
    return goals


def load_goals(filename, minimum=3):
    """Nap YAML, khong tu tao toa do mau cho robot."""
    with Path(filename).expanduser().open(encoding='utf-8') as stream:
        return validate_goals(yaml.safe_load(stream), minimum)


def atomic_write(filename, content):
    """Ghi file bang replace de khong de lai file dang do."""
    target = Path(filename).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=target.parent, delete=False) as stream:
            temporary = stream.name
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def save_goals(filename, goals):
    """Luu toa do map theo dung thu tu da ghi."""
    document = {'frame_id': 'map', 'goals': goals}
    validate_goals(document, minimum=0)
    atomic_write(filename, yaml.safe_dump(document, sort_keys=False, allow_unicode=True))


def yaw_from_quaternion(quaternion):
    """Lay yaw radian tu quaternion da chuan hoa."""
    norm = math.sqrt(sum(value ** 2 for value in (
        quaternion.x, quaternion.y, quaternion.z, quaternion.w)))
    if not math.isfinite(norm) or norm < 1e-9:
        raise ValueError('Quaternion khong hop le')
    x, y, z, w = (getattr(quaternion, key) / norm for key in ('x', 'y', 'z', 'w'))
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))

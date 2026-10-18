#!/usr/bin/env bash
# Cai rieng vao workspace, khong sua Python he thong hay .bashrc.
set -euo pipefail
TB4_YOLO_WS="${TB4_LAB_WS:-$HOME/tb4_ws}"
TB4_YOLO_SCRIPT="$(realpath "${BASH_SOURCE[0]}")"
TB4_YOLO_CONFIG="$(dirname "$TB4_YOLO_SCRIPT")/../config"
if [[ ! -f "$TB4_YOLO_CONFIG/yolo_constraints.txt" ]]; then
    TB4_YOLO_CONFIG="$(/usr/bin/python3 -c \
      'from ament_index_python.packages import get_package_share_directory; print(get_package_share_directory("turtlebot4_slam_nav"))')/config"
fi
TB4_YOLO_ENV="$TB4_YOLO_WS/.venv-yolo"
export PIP_CACHE_DIR="$TB4_YOLO_WS/log/pip-cache"
export YOLO_CONFIG_DIR="$TB4_YOLO_WS/log/ultralytics"
export PIP_DEFAULT_TIMEOUT=120
mkdir -p "$TB4_YOLO_WS/models" "$PIP_CACHE_DIR" "$YOLO_CONFIG_DIR"
/usr/bin/python3 -m venv --system-site-packages --without-pip "$TB4_YOLO_ENV"
# pip he thong duoc nhin thay qua system-site-packages; Python venv quyet dinh noi cai.
"$TB4_YOLO_ENV/bin/python" -m pip --version
"$TB4_YOLO_ENV/bin/python" -c 'import cv2; print("OpenCV he thong:", cv2.__version__)'
"$TB4_YOLO_ENV/bin/python" -m pip install \
  --index-url https://download.pytorch.org/whl/cpu \
  torch==2.6.0 torchvision==0.21.0
# Dung OpenCV apt cung cv_bridge; khong tai them wheel OpenCV/Qt trung lap.
"$TB4_YOLO_ENV/bin/python" -m pip install --no-deps 'ultralytics==8.3.221'
"$TB4_YOLO_ENV/bin/python" -m pip install \
  -c "$TB4_YOLO_CONFIG/yolo_constraints.txt" \
  'numpy==1.26.4' 'matplotlib>=3.3.0' 'pillow>=7.1.2' 'pyyaml>=5.3.1' \
  'requests>=2.23.0' 'scipy>=1.4.1' psutil 'ultralytics-thop>=2.0.0'
cd "$TB4_YOLO_WS/models"
"$TB4_YOLO_ENV/bin/python" - <<'PY'
from ultralytics import YOLO
import numpy as np
import torch

torch.set_num_threads(2)
model = YOLO('yolo11n.pt')
result = model.predict(np.zeros((320, 320, 3), dtype=np.uint8),
                       device='cpu', imgsz=320, verbose=False)[0]
assert result.orig_shape == (320, 320)
print('YOLO CPU da nap model va suy luan thanh cong; anh den khong phai minh chung nhan dien.')
PY
echo "YOLO da cai tai $TB4_YOLO_ENV; weights tai $TB4_YOLO_WS/models/yolo11n.pt"

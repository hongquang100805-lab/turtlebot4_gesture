#!/usr/bin/env bash
# Keep inference dependencies separate from ROS and the previous YOLO environment.
set -euo pipefail
TB4_GESTURE_WS="${TB4_LAB_WS:-$HOME/tb4_ws}"
TB4_GESTURE_ENV="$TB4_GESTURE_WS/.venv-gesture"
export PIP_CACHE_DIR="$TB4_GESTURE_WS/log/pip-cache"
mkdir -p "$TB4_GESTURE_WS/models" "$PIP_CACHE_DIR"
/usr/bin/python3 -m venv --system-site-packages --without-pip "$TB4_GESTURE_ENV"
"$TB4_GESTURE_ENV/bin/python" -m pip install --no-deps 'mediapipe==0.10.21'
# OpenCV from apt is intentionally reused; avoid duplicate Qt/OpenCV wheels.
"$TB4_GESTURE_ENV/bin/python" -m pip install \
  'numpy==1.26.4' 'absl-py>=2,<3' 'flatbuffers>=24,<26' \
  'protobuf>=4.25.3,<5' 'sounddevice>=0.4.4,<0.6' \
  'sentencepiece>=0.2,<0.3' 'jax==0.4.35' 'jaxlib==0.4.35'
if [[ ! -s "$TB4_GESTURE_WS/models/gesture_recognizer.task" ]]; then
  curl -fL --retry 2 \
    https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task \
    -o "$TB4_GESTURE_WS/models/gesture_recognizer.task"
fi
"$TB4_GESTURE_ENV/bin/python" -c \
  'import cv2, mediapipe, numpy; print("MediaPipe", mediapipe.__version__, "OpenCV", cv2.__version__, "NumPy", numpy.__version__)'
echo 'Ready: run the recognition node with .venv-gesture/bin/python.'

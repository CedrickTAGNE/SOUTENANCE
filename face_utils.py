"""Helpers for face identifiers stored in JSON.

This module is intentionally resilient when OpenCV is not installed yet.
If the runtime is missing cv2, the functions return None instead of crashing
application startup.
"""

try:
    import cv2
except ImportError:  # pragma: no cover - runtime fallback
    cv2 = None

try:
    import numpy as np
except ImportError:  # pragma: no cover - fallback for minimal runtime
    np = None

import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def extract_face_id(frame, cascade=None):
    if cv2 is None or frame is None:
        return None
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
    if cascade is not None:
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        if len(faces):
            x, y, width, height = max(faces, key=lambda item: item[2] * item[3])
            gray = gray[y:y + height, x:x + width]
    if gray.size == 0:
        return None
    try:
        gray = cv2.equalizeHist(gray)
    except Exception:
        pass
    normalized = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
    return normalized.astype("uint8").flatten().tolist()


def extract_face_id_from_path(image_path, cascade=None):
    if cv2 is None or not image_path:
        return None
    try:
        resolved_path = str(image_path).replace("\\", os.sep)
        if not os.path.isabs(resolved_path):
            resolved_path = os.path.join(BASE_DIR, resolved_path)
        if not os.path.exists(resolved_path):
            return None
        img = cv2.imread(resolved_path)
        if img is None:
            return None
        return extract_face_id(img, cascade)
    except Exception:
        return None


def compare_face_ids(left, right, threshold=38.0):
    if cv2 is None or np is None:
        return False, None
    if not left or not right or len(left) != len(right):
        return False, None
    left_array = np.clip(np.asarray(left, dtype="int16"), 0, 255).astype("uint8").reshape(64, 64)
    right_array = np.clip(np.asarray(right, dtype="int16"), 0, 255).astype("uint8").reshape(64, 64)
    distance = float(cv2.norm(left_array, right_array, cv2.NORM_L1) / len(left))
    return distance <= threshold, distance


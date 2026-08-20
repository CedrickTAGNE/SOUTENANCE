"""Small OpenCV helpers for persistent face identifiers stored in JSON."""

import cv2
import numpy as np


def extract_face_id(frame, cascade=None):
    if frame is None:
        return None
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
    if cascade is not None:
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        if len(faces):
            x, y, width, height = max(faces, key=lambda item: item[2] * item[3])
            gray = gray[y:y + height, x:x + width]
    if gray.size == 0:
        return None
    normalized = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
    return normalized.astype("uint8").flatten().tolist()


def compare_face_ids(left, right, threshold=34.0):
    if not left or not right or len(left) != len(right):
        return False, None
    left_array = np.clip(np.asarray(left, dtype="int16"), 0, 255).astype("uint8").reshape(64, 64)
    right_array = np.clip(np.asarray(right, dtype="int16"), 0, 255).astype("uint8").reshape(64, 64)
    distance = float(cv2.norm(left_array, right_array, cv2.NORM_L1) / len(left))
    return distance <= threshold, distance

"""Utility helpers for the target mini-game logic."""

from __future__ import annotations

import random
from typing import Iterable, Optional, Tuple

import mediapipe as mp

mp_pose = mp.solutions.pose


def _to_px(landmark: mp.framework.formats.landmark_pb2.NormalizedLandmark, width: int, height: int) -> Tuple[int, int]:
    return int(landmark.x * width), int(landmark.y * height)


def respawn_target(landmarks, width: int, height: int, target_radius: int) -> Optional[Tuple[int, int]]:
    """Respawn a target within the upper torso bounds using Mediapipe pose landmarks."""
    ls = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    rs = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    lh = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
    rh = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
    nose = landmarks[mp_pose.PoseLandmark.NOSE.value]

    lsx, lsy = _to_px(ls, width, height)
    rsx, rsy = _to_px(rs, width, height)
    lhy = _to_px(lh, width, height)[1]
    rhy = _to_px(rh, width, height)[1]
    nx, ny = _to_px(nose, width, height)

    shoulder_width = abs(rsx - lsx)

    xmin = max(target_radius, min(lsx, rsx) - shoulder_width)
    xmax = min(width - target_radius, max(lsx, rsx) + shoulder_width)

    waist_y = (lhy + rhy) // 2
    ymin = max(target_radius, min(ny, waist_y))
    ymax = min(height - target_radius, max(ny, waist_y))

    if xmax <= xmin or ymax <= ymin:
        return None

    return random.randint(xmin, xmax), random.randint(ymin, ymax)


def wrists_hit_circle(
    landmarks, width: int, height: int, center: Optional[Tuple[int, int]], radius: int, visibility_thr: float = 0.5
) -> bool:
    """Detect whether either wrist is within a target circle."""
    if center is None:
        return False

    cx, cy = center
    for wrist_id in (
        mp_pose.PoseLandmark.LEFT_WRIST.value,
        mp_pose.PoseLandmark.RIGHT_WRIST.value,
    ):
        landmark = landmarks[wrist_id]
        if landmark.visibility < visibility_thr:
            continue
        x, y = _to_px(landmark, width, height)
        dx, dy = x - cx, y - cy
        if dx * dx + dy * dy <= radius * radius:
            return True
    return False


def choose_punch_type(probabilities: Optional[Iterable[Tuple[str, float]]] = None) -> str:
    """Randomly choose a punch type given optional probability weights."""
    if probabilities:
        punches, weights = zip(*probabilities)
        return random.choices(punches, weights=weights, k=1)[0]

    roll = random.random()
    if roll < 0.625:
        return "jab"
    if roll < 0.875:
        return "hook"
    return "uppercut"




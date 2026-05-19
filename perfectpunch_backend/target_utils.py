from pathlib import Path
import random
from typing import Optional, Sequence, Tuple

import cv2
import numpy as np

try:
    import mediapipe as mp

    mp_pose = mp.solutions.pose
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    # MediaPipe is optional for some unit tests / CI environments
    print("Warning: MediaPipe not available in target_utils")
    mp = None
    mp_pose = None
    MEDIAPIPE_AVAILABLE = False


PUNCH_COLORS = {
    "jab": (0, 0, 255),        # red
    "hook": (0, 255, 0),       # green
    "uppercut": (255, 0, 0),   # blue
}

PUBLIC_ASSET_DIR = Path(__file__).resolve().parents[1] / "public"
TARGET_GLOVE_ASSETS = {
    "jab_front": "front_punchpad.png",
    "hook_left": "left_punchpad.png",
    "hook_right": "right_punchpad.png",
    "uppercut_up": "up_punchpad.png",
}

HAND_CONTACT_LANDMARKS = (
    # Wrists
    "LEFT_WRIST",
    "RIGHT_WRIST",
    # Fingertips / hand edges commonly reaching glove first
    "LEFT_INDEX",
    "RIGHT_INDEX",
    "LEFT_THUMB",
    "RIGHT_THUMB",
    "LEFT_PINKY",
    "RIGHT_PINKY",
)


def _to_px(lm, w: int, h: int) -> Tuple[int, int]:
    """Convert a normalized landmark (with .x and .y in [0,1]) to pixel coords.

    Args:
        lm: landmark object with attributes `x` and `y` (normalized coordinates).
        w: image width in pixels.
        h: image height in pixels.

    Returns:
        (x, y) pixel coordinates as integers.
    """

    return int(lm.x * w), int(lm.y * h)

#Respawn target within the area defined by shoulders, hips, and nose
def respawn_target(landmarks, w: int, h: int, target_radius: int) -> Optional[Tuple[int, int]]:
    """Choose a random target position constrained to the player's upper body.

    The spawn area is computed from shoulders, hips, and nose landmarks to keep
    targets around the chest/upper torso region.

    Args:
        landmarks: sequence of MediaPipe landmarks (indexable by enum `.value`).
        w: frame width in pixels.
        h: frame height in pixels.
        target_radius: radius of the logical target in pixels.

    Returns:
        (x, y) pixel coordinates for the respawn position, or None when a
        valid spawn region cannot be computed.

    Notes:
        If MediaPipe is not available, returns the center of the frame for tests.
    """

    if not MEDIAPIPE_AVAILABLE:
        # Return a dummy target position for testing
        return (w // 2, h // 2)

    ls = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    rs = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    lh = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
    rh = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
    nose = landmarks[mp_pose.PoseLandmark.NOSE.value]

    lsx, lsy = _to_px(ls, w, h)
    rsx, rsy = _to_px(rs, w, h)
    lhy, rhy = _to_px(lh, w, h)[1], _to_px(rh, w, h)[1]
    nx, ny = _to_px(nose, w, h)

    shoulder_width = abs(rsx - lsx)

    xmin = max(target_radius, min(lsx, rsx) - shoulder_width)
    xmax = min(w - target_radius, max(lsx, rsx) + shoulder_width)

    shoulder_y = (lsy + rsy) // 2
    waist_y = (lhy + rhy) // 2

    # Keep targets in the upper body: do not allow spawns lower than mid-chest.
    mid_chest_floor_y = shoulder_y + ((waist_y - shoulder_y) // 2)
    ymin = max(target_radius, min(ny, shoulder_y))
    ymax = min(h - target_radius, max(ny, mid_chest_floor_y))

    if xmax <= xmin or ymax <= ymin:
        return None

    return (random.randint(xmin, xmax), random.randint(ymin, ymax))

# Detect if hand landmarks intersect target area.
# The rendered glove is visually larger than the logical spawn circle,
# so we expand the collision radius for a more intuitive "what you see is what hits" feel.
def wrists_hit_circle(
    landmarks,
    w: int,
    h: int,
    center: Optional[Tuple[int, int]],
    radius: int,
    hit_radius_scale: float = 3.0,
    min_visibility: float = 0.35,
) -> bool:
    """Return True if any hand landmark intersects the target circle.

    Args:
        landmarks: sequence of MediaPipe landmarks.
        w: image width.
        h: image height.
        center: (x, y) center of the target in pixels.
        radius: logical target radius in pixels.
        hit_radius_scale: visual expansion factor for collision detection.
        min_visibility: minimum landmark visibility to consider it valid.

    Returns:
        True if a hand landmark lies within the (expanded) target radius.
    """

    if center is None or not MEDIAPIPE_AVAILABLE:
        return False

    cx, cy = center
    effective_radius = max(1, int(radius * hit_radius_scale))

    for landmark_name in HAND_CONTACT_LANDMARKS:
        landmark_id = mp_pose.PoseLandmark[landmark_name].value
        lm = landmarks[landmark_id]
        if lm.visibility < min_visibility:
            continue

        x, y = _to_px(lm, w, h)
        dx, dy = x - cx, y - cy
        if dx * dx + dy * dy <= effective_radius * effective_radius:
            return True

    return False

#Randomly choose a punch type based on defined probabilities (Will update to use coach agent to determine probabilities)
def choose_punch_type() -> str:
    """Randomly pick a punch type using predefined probabilities.

    Probabilities (empirical):
      - jab: 62.5%
      - hook: 25%
      - uppercut: 12.5%
    """

    r = random.random()
    if r < 0.625:
        return "jab"
    if r < 0.625 + 0.25:
        return "hook"
    return "uppercut"


def choose_target_glove_key(punch_type: Optional[str] = None) -> str:
    """Return the glove asset key appropriate for the given `punch_type`.

    Args:
        punch_type: one of 'jab', 'hook', 'uppercut' or None.

    Returns:
        Key for `TARGET_GLOVE_ASSETS` to load an image.
    """

    if punch_type == "jab":
        return "jab_front"
    if punch_type == "hook":
        return random.choice(["hook_left", "hook_right"])
    if punch_type == "uppercut":
        return "uppercut_up"
    # Fallback
    return random.choice(list(TARGET_GLOVE_ASSETS.keys()))


def load_target_glove_image(glove_key: str) -> Optional[np.ndarray]:
    """Load the glove image for a given asset key.

    Args:
        glove_key: key from `TARGET_GLOVE_ASSETS`.

    Returns:
        BGR(A) image as a numpy array, or None if the file is missing.
    """

    filename = TARGET_GLOVE_ASSETS.get(glove_key)
    if not filename:
        return None

    image_path = PUBLIC_ASSET_DIR / filename
    if not image_path.exists():
        return None

    return cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)


def draw_target_glove(
    frame: np.ndarray,
    center: Optional[Tuple[int, int]],
    radius: int,
    glove_image: Optional[np.ndarray],
    glove_key: Optional[str] = None,
) -> np.ndarray:
    """Draw a glove image centered on `center` onto `frame`.

    Args:
        frame: HxWx3 BGR image that will be modified in-place.
        center: (x, y) center position in pixels.
        radius: logical target radius in pixels (controls visual size).
        glove_image: loaded glove image (BGR or BGRA).
        glove_key: optional key used for debug/selection (unused here).

    Returns:
        The modified `frame` (same object passed in).
    """

    if frame is None or center is None or glove_image is None:
        return frame

    cx, cy = center
    glove_size = max(int(radius * 10), 1)
    resized = cv2.resize(glove_image, (glove_size, glove_size), interpolation=cv2.INTER_AREA)

    glove_size = resized.shape[0]

    x1 = cx - glove_size // 2
    y1 = cy - glove_size // 2
    x2 = x1 + glove_size
    y2 = y1 + glove_size

    frame_h, frame_w = frame.shape[:2]
    src_x1 = max(0, -x1)
    src_y1 = max(0, -y1)
    src_x2 = glove_size - max(0, x2 - frame_w)
    src_y2 = glove_size - max(0, y2 - frame_h)

    dst_x1 = max(0, x1)
    dst_y1 = max(0, y1)
    dst_x2 = min(frame_w, x2)
    dst_y2 = min(frame_h, y2)

    if dst_x1 >= dst_x2 or dst_y1 >= dst_y2:
        return frame

    overlay = resized[src_y1:src_y2, src_x1:src_x2]
    if overlay.shape[2] == 4:
        overlay_rgb = overlay[:, :, :3].astype(np.float32)
        alpha = overlay[:, :, 3].astype(np.float32) / 255.0
        alpha = alpha[:, :, np.newaxis]
        base = frame[dst_y1:dst_y2, dst_x1:dst_x2].astype(np.float32)
        blended = overlay_rgb * alpha + base * (1.0 - alpha)
        frame[dst_y1:dst_y2, dst_x1:dst_x2] = blended.astype(np.uint8)
    else:
        frame[dst_y1:dst_y2, dst_x1:dst_x2] = overlay[:, :, :3]

    return frame
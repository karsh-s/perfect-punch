from pathlib import Path
import random

import cv2
import numpy as np

try:
    import mediapipe as mp
    mp_pose = mp.solutions.pose
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    print("Warning: MediaPipe not available in target_utils")
    mp = None
    mp_pose = None
    MEDIAPIPE_AVAILABLE = False

PUNCH_COLORS = {
    "jab": (0, 0, 255),        # red
    "hook": (0, 255, 0),       # green
    "uppercut": (255, 0, 0)    # blue
}

PUBLIC_ASSET_DIR = Path(__file__).resolve().parents[1] / "public"
TARGET_GLOVE_ASSETS = {
    "green_left": "left_punchpad.png", #left hook
    "green_right": "right_punchpad.png", #right hook
    "uppercut_left": "up_punchpad.png", #uppercut
    "uppercut_right": "up_punchpad.png", #uppercut (same image, rotated in draw function)
    "jab_left": "front_punchpad.png", #jab
    "jab_right": "front_punchpad.png", #jab
}

HAND_CONTACT_LANDMARKS = (
    # Wrists
    "LEFT_WRIST",
    "RIGHT_WRIST",
    # Fingertips/hand edges commonly reaching glove first
    "LEFT_INDEX",
    "RIGHT_INDEX",
    "LEFT_THUMB",
    "RIGHT_THUMB",
    "LEFT_PINKY",
    "RIGHT_PINKY",
)

#Convert normalized landmark to pixel coordinates
def _to_px(lm, w, h):
    return int(lm.x * w), int(lm.y * h)

#Respawn target within the area defined by shoulders, hips, and nose
def respawn_target(landmarks, w, h, target_radius):
    if not MEDIAPIPE_AVAILABLE:
        # Return a dummy target position for testing
        return (w//2, h//2)
        
    ls = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    rs = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    lh = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
    rh = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
    nose = landmarks[mp_pose.PoseLandmark.NOSE.value]

    (lsx, lsy) = _to_px(ls, w, h)
    (rsx, rsy) = _to_px(rs, w, h)
    (lhy, rhy) = (_to_px(lh, w, h)[1], _to_px(rh, w, h)[1])
    (nx, ny)   = _to_px(nose, w, h)

    shoulder_width = abs(rsx - lsx)

    xmin = max(target_radius, min(lsx, rsx) - shoulder_width)
    xmax = min(w - target_radius, max(lsx, rsx) + shoulder_width)

    waist_y = (lhy + rhy) // 2
    ymin = max(target_radius, min(ny, waist_y))
    ymax = min(h - target_radius, max(ny, waist_y))

    if xmax <= xmin or ymax <= ymin:
        return None

    return (random.randint(xmin, xmax), random.randint(ymin, ymax))

# Detect if hand landmarks intersect target area.
# The rendered glove is visually larger than the logical spawn circle,
# so we expand the collision radius for a more intuitive "what you see is what hits" feel.
def wrists_hit_circle(landmarks, w, h, center, radius, hit_radius_scale=3.0, min_visibility=0.35):
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
def choose_punch_type():
    r = random.random()
    if r < 0.625:
        return "jab"
    elif r < 0.625 + 0.25:
        return "hook"
    else:
        return "uppercut"


def choose_target_glove_key(punch_type=None):
    if punch_type == "jab":
        return random.choice(["jab_left", "jab_right"])
    if punch_type == "hook":
        return random.choice(["green_left", "green_right"])
    if punch_type == "uppercut":
        return random.choice(["uppercut_left", "uppercut_right"])
    return random.choice(list(TARGET_GLOVE_ASSETS.keys()))


def load_target_glove_image(glove_key):
    filename = TARGET_GLOVE_ASSETS.get(glove_key)
    if not filename:
        return None

    image_path = PUBLIC_ASSET_DIR / filename
    if not image_path.exists():
        print(f"DEBUG: Image file doesn't exist: {image_path}")
        return None

    img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"DEBUG: Failed to load image: {image_path}")
    else:
        print(f"DEBUG: Successfully loaded {glove_key} -> {filename}, shape: {img.shape}")
    return img


def draw_target_glove(frame, center, radius, glove_image, glove_key=None):
    if frame is None or center is None or glove_image is None:
        return frame

    cx, cy = center
    # Scale by 0.8x and maintain original aspect ratio
    base_size = max(int(radius * 10 * 0.8), 1)
    
    # Get original image dimensions and aspect ratio
    img_h, img_w = glove_image.shape[:2]
    aspect_ratio = img_w / img_h if img_h > 0 else 1.0
    
    # Calculate dimensions maintaining aspect ratio
    if aspect_ratio >= 1.0:
        # Width is larger or equal
        new_w = base_size
        new_h = max(1, int(base_size / aspect_ratio))
    else:
        # Height is larger
        new_h = base_size
        new_w = max(1, int(base_size * aspect_ratio))
    
    resized = cv2.resize(glove_image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Skip rotation for now - just use as-is
    # if glove_key is not None and glove_key.startswith("green"):
    #     if glove_key.endswith("_right"):
    #         resized = cv2.rotate(resized, cv2.ROTATE_90_CLOCKWISE)
    #     elif glove_key.endswith("_left"):
    #         resized = cv2.rotate(resized, cv2.ROTATE_90_COUNTERCLOCKWISE)
    #     new_h, new_w = resized.shape[:2]

    resized_h, resized_w = resized.shape[:2]
    
    x1 = cx - resized_w // 2
    y1 = cy - resized_h // 2
    x2 = x1 + resized_w
    y2 = y1 + resized_h

    frame_h, frame_w = frame.shape[:2]
    src_x1 = max(0, -x1)
    src_y1 = max(0, -y1)
    src_x2 = resized_w - max(0, x2 - frame_w)
    src_y2 = resized_h - max(0, y2 - frame_h)

    dst_x1 = max(0, x1)
    dst_y1 = max(0, y1)
    dst_x2 = min(frame_w, x2)
    dst_y2 = min(frame_h, y2)

    if dst_x1 >= dst_x2 or dst_y1 >= dst_y2 or src_x1 >= src_x2 or src_y1 >= src_y2:
        return frame

    overlay = resized[src_y1:src_y2, src_x1:src_x2]
    if len(overlay.shape) >= 3 and overlay.shape[2] == 4:
        # Image has alpha channel
        overlay_rgb = overlay[:, :, :3].astype(np.float32)
        alpha = overlay[:, :, 3].astype(np.float32) / 255.0
        alpha = alpha[:, :, np.newaxis]
        base = frame[dst_y1:dst_y2, dst_x1:dst_x2].astype(np.float32)
        blended = overlay_rgb * alpha + base * (1.0 - alpha)
        frame[dst_y1:dst_y2, dst_x1:dst_x2] = blended.astype(np.uint8)
    elif len(overlay.shape) >= 3 and overlay.shape[2] >= 3:
        # Image has RGB (no alpha)
        frame[dst_y1:dst_y2, dst_x1:dst_x2] = overlay[:, :, :3]
    else:
        # Grayscale or other format
        frame[dst_y1:dst_y2, dst_x1:dst_x2] = overlay

    return frame
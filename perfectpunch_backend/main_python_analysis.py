import cv2
import mediapipe as mp
import time
import concurrent.futures
import ctypes
import json
import math
from datetime import datetime
import sys
import os

import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    from .extractDataPoints import PoseTracker
    from .defense import DefenseGame
    from .target_utils import (
        respawn_target,
        wrists_hit_circle,
        choose_punch_type,
        PUNCH_COLORS,
        choose_target_glove_key,
        draw_target_glove,
        load_target_glove_image,
    )
except ImportError:
    # Fallback for direct script execution (no package context).
    from extractDataPoints import PoseTracker
    from defense import DefenseGame
    from target_utils import (
        respawn_target,
        wrists_hit_circle,
        choose_punch_type,
        PUNCH_COLORS,
        choose_target_glove_key,
        draw_target_glove,
        load_target_glove_image,
    )

# Flag to disable display for headless/backend environments
SHOW_DISPLAY = os.getenv('SHOW_DISPLAY', 'false').lower() == 'true'
MODEL_SEQUENCE_FRAMES = 50
LANDMARK_FEATURES_PER_FRAME = 8
MODEL_CONF_THRESHOLD = 0.55
CLASS_NAMES = ("hook", "jab", "uppercut")
FEATURE_LANDMARK_ORDER = ("RIGHT_ELBOW", "RIGHT_WRIST", "LEFT_ELBOW", "LEFT_WRIST")

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose


def show_frame(window_name, frame):
    """Display frame only if display is enabled."""
    if SHOW_DISPLAY:
        try:
            cv2.imshow(window_name, frame)
        except Exception as e:
            print(f"Warning: Could not display frame: {e}")


def wait_key(delay=1):
    """Wait for key input only if display is enabled. Returns quit flag."""
    if SHOW_DISPLAY:
        try:
            if cv2.waitKey(delay) & 0xFF == ord('q'):
                return True
        except Exception:
            pass
    return False


def _get_time_window_index(elapsed_seconds):
    if elapsed_seconds <= 10:
        return 0
    if 10 < elapsed_seconds <= 20:
        return 1
    if 20 < elapsed_seconds <= 30:
        return 2
    return None


def _get_spawn_timing(now, protect_seconds):
    circle_ts = now
    return now, circle_ts, circle_ts + protect_seconds


def _compute_speed_value(raw_coords, fps_value):
    if not raw_coords or len(raw_coords) < 2:
        return None

    frame_pair_speeds = []
    for i in range(len(raw_coords) - 1):
        lm_a = raw_coords[i].get("landmarks")
        lm_b = raw_coords[i + 1].get("landmarks")
        if not lm_a or not lm_b:
            continue

        pair_disps = []
        for wrist_name in ("RIGHT_WRIST", "LEFT_WRIST"):
            if wrist_name in lm_a and wrist_name in lm_b:
                dx = lm_b[wrist_name]["x"] - lm_a[wrist_name]["x"]
                dy = lm_b[wrist_name]["y"] - lm_a[wrist_name]["y"]
                pair_disps.append(math.hypot(dx, dy))

        if pair_disps:
            frame_pair_speeds.append(max(pair_disps) * fps_value)

    if not frame_pair_speeds:
        return None

    # Average the top 3 highest frame-pair speeds.
    top_speeds = sorted(frame_pair_speeds, reverse=True)[:3]
    return sum(top_speeds) / len(top_speeds)


def _flatten_normalized_features(coords):
    features = []
    for record in coords:
        landmarks = record.get("landmarks")
        if not landmarks:
            continue

        # Preserve a fixed landmark order so model inputs match training layout.
        if any(name not in landmarks for name in FEATURE_LANDMARK_ORDER):
            continue

        for landmark_name in FEATURE_LANDMARK_ORDER:
            point = landmarks[landmark_name]
            features.extend([point["x"], point["y"]])
    return features

class Model(nn.Module):
    """3D CNN model for punch classification with spatial, temporal, and residual branches."""
    
    def __init__(self, num_classes=3):
        super(Model, self).__init__()
        
        # Stem layer: Initial 3D convolution (7 input channels for pose landmarks)
        self.stem = nn.Sequential(
            nn.Conv3d(7, 32, kernel_size=(3, 3, 3), padding=(1, 1, 1), bias=False),
            nn.BatchNorm3d(32),
            nn.ReLU(inplace=True)
        )
        
        # Layer 1: in=32, spatial_out=32, temporal_out=64, residual_out=64
        self.layer1 = nn.ModuleDict({
            'spatial': nn.Sequential(
                nn.Conv3d(32, 32, kernel_size=(1, 3, 3), padding=(0, 1, 1), bias=False),
                nn.BatchNorm3d(32),
            ),
            'temporal': nn.Sequential(
                nn.Conv3d(32, 64, kernel_size=(3, 1, 1), padding=(1, 0, 0), bias=False),
                nn.BatchNorm3d(64),
            ),
            'residual': nn.Sequential(
                nn.Conv3d(32, 64, kernel_size=(1, 1, 1), bias=False),
                nn.BatchNorm3d(64),
            )
        })
        
        # Layer 2: in=64, spatial_out=64, temporal_out=128, residual_out=128
        self.layer2 = nn.ModuleDict({
            'spatial': nn.Sequential(
                nn.Conv3d(64, 64, kernel_size=(1, 3, 3), padding=(0, 1, 1), bias=False),
                nn.BatchNorm3d(64),
            ),
            'temporal': nn.Sequential(
                nn.Conv3d(64, 128, kernel_size=(3, 1, 1), padding=(1, 0, 0), bias=False),
                nn.BatchNorm3d(128),
            ),
            'residual': nn.Sequential(
                nn.Conv3d(64, 128, kernel_size=(1, 1, 1), bias=False),
                nn.BatchNorm3d(128),
            )
        })
        
        # Layer 3: in=128, spatial_out=128, temporal_out=256, residual_out=256
        self.layer3 = nn.ModuleDict({
            'spatial': nn.Sequential(
                nn.Conv3d(128, 128, kernel_size=(1, 3, 3), padding=(0, 1, 1), bias=False),
                nn.BatchNorm3d(128),
            ),
            'temporal': nn.Sequential(
                nn.Conv3d(128, 256, kernel_size=(3, 1, 1), padding=(1, 0, 0), bias=False),
                nn.BatchNorm3d(256),
            ),
            'residual': nn.Sequential(
                nn.Conv3d(128, 256, kernel_size=(1, 1, 1), bias=False),
                nn.BatchNorm3d(256),
            )
        })
        
        # Layer 4: in=256, spatial_out=256, temporal_out=256, no residual
        self.layer4 = nn.ModuleDict({
            'spatial': nn.Sequential(
                nn.Conv3d(256, 256, kernel_size=(1, 3, 3), padding=(0, 1, 1), bias=False),
                nn.BatchNorm3d(256),
            ),
            'temporal': nn.Sequential(
                nn.Conv3d(256, 256, kernel_size=(3, 1, 1), padding=(1, 0, 0), bias=False),
                nn.BatchNorm3d(256),
            )
        })
        
        # Layer 5: in=256, spatial_out=256, temporal_out=512, residual_out=512
        self.layer5 = nn.ModuleDict({
            'spatial': nn.Sequential(
                nn.Conv3d(256, 256, kernel_size=(1, 3, 3), padding=(0, 1, 1), bias=False),
                nn.BatchNorm3d(256),
            ),
            'temporal': nn.Sequential(
                nn.Conv3d(256, 512, kernel_size=(3, 1, 1), padding=(1, 0, 0), bias=False),
                nn.BatchNorm3d(512),
            ),
            'residual': nn.Sequential(
                nn.Conv3d(256, 512, kernel_size=(1, 1, 1), bias=False),
                nn.BatchNorm3d(512),
            )
        })
        
        # Layer 6: in=512, spatial_out=512, temporal_out=512, no residual
        self.layer6 = nn.ModuleDict({
            'spatial': nn.Sequential(
                nn.Conv3d(512, 512, kernel_size=(1, 3, 3), padding=(0, 1, 1), bias=False),
                nn.BatchNorm3d(512),
            ),
            'temporal': nn.Sequential(
                nn.Conv3d(512, 512, kernel_size=(3, 1, 1), padding=(1, 0, 0), bias=False),
                nn.BatchNorm3d(512),
            )
        })
        
        # Global average pooling
        self.avg_pool = nn.AdaptiveAvgPool3d((1, 1, 1))
        
        # Classifier head matches saved model structure
        # Saved model has keys: classifier.2 (Linear 512->256), classifier.5 (Linear 256->3)
        # So we use placeholder modules for indices 0,1,3,4 to match saved weights at 2 and 5
        self.classifier = nn.Sequential(
            nn.Identity(),  # classifier.0
            nn.Identity(),  # classifier.1
            nn.Linear(512, 256),  # classifier.2: takes pooled output (512 channels)
            nn.ReLU(inplace=True),  # classifier.3
            nn.Identity(),  # classifier.4 (could be Dropout)
            nn.Linear(256, num_classes)  # classifier.5: outputs num_classes (3)
        )
    
    def forward(self, x):
        # x shape: (batch, channels, depth, height, width)
        # If input is 2D features (batch, features), reshape appropriately
        if x.dim() == 2:
            batch_size = x.shape[0]
            feature_count = x.shape[1]
            if feature_count % LANDMARK_FEATURES_PER_FRAME != 0:
                raise ValueError(
                    f"Expected feature count divisible by {LANDMARK_FEATURES_PER_FRAME}, got {feature_count}"
                )

            sequence_len = feature_count // LANDMARK_FEATURES_PER_FRAME
            x = x.unsqueeze(1).expand(-1, 7, -1)  # (batch, 7, 120)
            x = x.view(batch_size, 7, sequence_len, LANDMARK_FEATURES_PER_FRAME, 1)
        
        x = self.stem(x)
        
        # Layer 1
        spatial = F.relu(self.layer1['spatial'](x))
        temporal = F.relu(self.layer1['temporal'](spatial))
        residual = F.relu(self.layer1['residual'](x))
        x = temporal + residual
        
        # Layer 2
        spatial = F.relu(self.layer2['spatial'](x))
        temporal = F.relu(self.layer2['temporal'](spatial))
        residual = F.relu(self.layer2['residual'](x))
        x = temporal + residual
        
        # Layer 3
        spatial = F.relu(self.layer3['spatial'](x))
        temporal = F.relu(self.layer3['temporal'](spatial))
        residual = F.relu(self.layer3['residual'](x))
        x = temporal + residual
        
        # Layer 4: no residual connection
        spatial = F.relu(self.layer4['spatial'](x))
        temporal = F.relu(self.layer4['temporal'](spatial))
        x = temporal
        
        # Layer 5
        spatial = F.relu(self.layer5['spatial'](x))
        temporal = F.relu(self.layer5['temporal'](spatial))
        residual = F.relu(self.layer5['residual'](x))
        x = temporal + residual
        
        # Layer 6: no residual connection
        spatial = F.relu(self.layer6['spatial'](x))
        temporal = F.relu(self.layer6['temporal'](spatial))
        x = temporal
        
        x = self.avg_pool(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        
        return x


# --- Parallel initialization functions ---
def _camera_backend_candidates():
    if sys.platform == "win32":
        return [
            getattr(cv2, "CAP_DSHOW", cv2.CAP_ANY),
            getattr(cv2, "CAP_MSMF", cv2.CAP_ANY),
            cv2.CAP_ANY,
        ]
    if sys.platform == "darwin":
        return [
            getattr(cv2, "CAP_AVFOUNDATION", cv2.CAP_ANY),
            cv2.CAP_ANY,
        ]
    return [
        getattr(cv2, "CAP_V4L2", cv2.CAP_ANY),
        cv2.CAP_ANY,
    ]


def _load_camera():
    """Initialize camera and warm it up with first frame read."""
    attempted = set()
    backend_names = {
        getattr(cv2, "CAP_DSHOW", -1): "CAP_DSHOW",
        getattr(cv2, "CAP_MSMF", -1): "CAP_MSMF",
        getattr(cv2, "CAP_AVFOUNDATION", -1): "CAP_AVFOUNDATION",
        getattr(cv2, "CAP_V4L2", -1): "CAP_V4L2",
        cv2.CAP_ANY: "CAP_ANY",
    }

    for backend in _camera_backend_candidates():
        if backend in attempted:
            continue
        attempted.add(backend)

        cap = cv2.VideoCapture(0) if backend == cv2.CAP_ANY else cv2.VideoCapture(0, backend)
        if not cap or not cap.isOpened():
            if cap:
                cap.release()
            continue

        # Reduce webcam latency by limiting queued frames and capture size.
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.read()  # Warm up - first read is slower

        print(f"Camera initialized with backend: {backend_names.get(backend, str(backend))}")
        return cap

    return None

def _load_torch_model():
    """Load PyTorch punch classifier model."""
    model = Model()
    model.load_state_dict(torch.load("perfectpunch_backend/models/model_state.pt", map_location='cpu'))
    model.eval()
    return model

def _load_mediapipe_pose():
    """Initialize MediaPipe Pose (ML model loading is slow)."""
    return mp_pose.Pose(
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

# --- Run all heavy initialization in parallel ---
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    cap_future = executor.submit(_load_camera)
    model_future = executor.submit(_load_torch_model)
    pose_future = executor.submit(_load_mediapipe_pose)
    
    cap = cap_future.result()
    model = model_future.result()
    shared_pose = pose_future.result()

if not cap or not cap.isOpened():
    print("FATAL: Camera failed to initialize. Close other camera apps and verify OS camera permissions.")
    exit(1)

tracker = PoseTracker(max_frames=MODEL_SEQUENCE_FRAMES, pose=shared_pose)
glove_images = {
    key: load_target_glove_image(key)
    for key in ("jab_front", "hook_left", "hook_right", "uppercut_up")
}

TARGET_CENTER = None
CURRENT_TYPE = None
TARGET_GLOVE_KEY = None
TARGET_RADIUS = 25 
SPAWN_PROTECT_S = 1
last_spawn_ts = 0.0
circle_spawn_ts = None
protect_release_ts = None
MAX_RUNTIME = 30
PRESTART_COUNTDOWN_SECONDS = 3
PREDICTION_OVERLAY_SECONDS = 1.8
prediction_overlay_text = None
prediction_overlay_color = (220, 220, 220)
prediction_overlay_until = 0.0

reaction_time_punch = {"jab": [], "hook": [], "uppercut": []}
reaction_time_windows = [
    {k: [] for k in reaction_time_punch.keys()},
    {k: [] for k in reaction_time_punch.keys()},
    {k: [] for k in reaction_time_punch.keys()},
]
correct_punches_thrown = 0
punches_thrown = 0
attempts_by_type = {k: 0 for k in reaction_time_punch.keys()}
correct_by_type = {k: 0 for k in reaction_time_punch.keys()}
accuracy_windows = [{"correct": 0, "attempts": 0} for _ in range(3)]
reaction_window_combined = [[] for _ in range(3)]
speed_by_type = {k: [] for k in reaction_time_punch.keys()}
speed_windows = [
    {k: [] for k in reaction_time_punch.keys()},
    {k: [] for k in reaction_time_punch.keys()},
    {k: [] for k in reaction_time_punch.keys()},
]
speed_window_combined = [[] for _ in range(3)]
coverage_tracker = {
    "head": {"covered": 0, "total": 0},
    "body": {"covered": 0, "total": 0},
}
exposure_tracker = {
    "left_shoulder": {"covered": 0, "total": 0},
    "right_shoulder": {"covered": 0, "total": 0},
    "chest": {"covered": 0, "total": 0},
    "abdomen": {"covered": 0, "total": 0},
    "hips": {"covered": 0, "total": 0},
}
defense_game = DefenseGame()


def _rects_overlap(a_x1, a_y1, a_x2, a_y2, b_x1, b_y1, b_x2, b_y2):
    return not (a_x2 < b_x1 or a_x1 > b_x2 or a_y2 < b_y1 or a_y1 > b_y2)


def _clamp_rect(x1, y1, x2, y2, max_w, max_h):
    return (
        max(0, min(x1, max_w)),
        max(0, min(y1, max_h)),
        max(0, min(x2, max_w)),
        max(0, min(y2, max_h)),
    )


def update_coverage_metrics(landmarks, w, h):
    if landmarks is None:
        return

    def get_coords(lm_enum_or_index):
        if isinstance(lm_enum_or_index, int):
            lm = landmarks[lm_enum_or_index]
        else:
            lm = landmarks[lm_enum_or_index.value]
        return int(lm.x * w), int(lm.y * h)

    rw_x, rw_y = get_coords(mp_pose.PoseLandmark.RIGHT_WRIST)
    lw_x, lw_y = get_coords(mp_pose.PoseLandmark.LEFT_WRIST)
    re_x, re_y = get_coords(mp_pose.PoseLandmark.RIGHT_ELBOW)
    le_x, le_y = get_coords(mp_pose.PoseLandmark.LEFT_ELBOW)
    rs_x, rs_y = get_coords(mp_pose.PoseLandmark.RIGHT_SHOULDER)
    ls_x, ls_y = get_coords(mp_pose.PoseLandmark.LEFT_SHOULDER)
    lh_x, lh_y = get_coords(mp_pose.PoseLandmark.LEFT_HIP)
    rh_x, rh_y = get_coords(mp_pose.PoseLandmark.RIGHT_HIP)
    nose_x, nose_y = get_coords(mp_pose.PoseLandmark.NOSE)

    arm_padding = 20
    right_arm_rect = _clamp_rect(
        min(rs_x, re_x, rw_x) - arm_padding,
        min(rs_y, re_y, rw_y) - arm_padding,
        max(rs_x, re_x, rw_x) + arm_padding,
        max(rs_y, re_y, rw_y) + arm_padding,
        w,
        h,
    )
    left_arm_rect = _clamp_rect(
        min(ls_x, le_x, lw_x) - arm_padding,
        min(ls_y, le_y, lw_y) - arm_padding,
        max(ls_x, le_x, lw_x) + arm_padding,
        max(ls_y, le_y, lw_y) + arm_padding,
        w,
        h,
    )

    def is_region_guarded(region_rect):
        x1, y1, x2, y2 = region_rect
        return (
            _rects_overlap(x1, y1, x2, y2, *right_arm_rect)
            or _rects_overlap(x1, y1, x2, y2, *left_arm_rect)
        )

    head_padding = 30
    head_rect = _clamp_rect(
        min(ls_x, rs_x) - head_padding,
        min(nose_y, ls_y, rs_y) - head_padding,
        max(ls_x, rs_x) + head_padding,
        max(nose_y, ls_y, rs_y) + head_padding,
        w,
        h,
    )
    coverage_tracker["head"]["total"] += 1
    if is_region_guarded(head_rect):
        coverage_tracker["head"]["covered"] += 1

    body_padding = 25
    body_rect = _clamp_rect(
        min(ls_x, rs_x, lh_x, rh_x) - body_padding,
        min(ls_y, rs_y) - body_padding,
        max(ls_x, rs_x, lh_x, rh_x) + body_padding,
        max(lh_y, rh_y) + body_padding,
        w,
        h,
    )
    coverage_tracker["body"]["total"] += 1
    if is_region_guarded(body_rect):
        coverage_tracker["body"]["covered"] += 1

    area_half = 45
    area_definitions = {
        "left_shoulder": (ls_x, ls_y),
        "right_shoulder": (rs_x, rs_y),
        "chest": ((ls_x + rs_x) // 2, (ls_y + rs_y) // 2),
        "abdomen": ((lh_x + rh_x) // 2, (lh_y + rh_y) // 2),
        "hips": ((lh_x + rh_x) // 2, max(lh_y, rh_y)),
    }

    for area_key, (cx, cy) in area_definitions.items():
        area_rect = _clamp_rect(
            cx - area_half,
            cy - area_half,
            cx + area_half,
            cy + area_half,
            w,
            h,
        )
        exposure_tracker[area_key]["total"] += 1
        if is_region_guarded(area_rect):
            exposure_tracker[area_key]["covered"] += 1

# Create window and remove decorations (title bar, buttons) to make it non-movable
WINDOW_NAME = "Mediapipe Feed (Press q to quit)"
if SHOW_DISPLAY:
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.waitKey(1)  # Let the window initialize

if SHOW_DISPLAY and sys.platform == "win32":
    # Windows API constants
    GWL_STYLE = -16
    WS_CAPTION = 0x00C00000
    WS_THICKFRAME = 0x00040000
    WS_MINIMIZEBOX = 0x00020000
    WS_MAXIMIZEBOX = 0x00010000
    WS_SYSMENU = 0x00080000

    # Find the window handle and modify its style
    hwnd = ctypes.windll.user32.FindWindowW(None, WINDOW_NAME)
    if hwnd:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

        screen_w = ctypes.windll.user32.GetSystemMetrics(0)
        screen_h = ctypes.windll.user32.GetSystemMetrics(1)

        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
        style &= ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)

        # Force fullscreen placement to match the full monitor bounds.
        SWP_FRAMECHANGED = 0x0020
        SWP_NOZORDER = 0x0004
        SWP_SHOWWINDOW = 0x0040
        ctypes.windll.user32.SetWindowPos(
            hwnd,
            None,
            0,
            0,
            screen_w,
            screen_h,
            SWP_FRAMECHANGED | SWP_NOZORDER | SWP_SHOWWINDOW,
        )

        cv2.moveWindow(WINDOW_NAME, 0, 0)
        cv2.resizeWindow(WINDOW_NAME, screen_w, screen_h)
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

def get_frame():
    ret, frame = cap.read()
    return frame if ret else None


def update_tracker_from_landmarks(tracker_obj, landmarks, frame_w, frame_h):
    """Feed tracker buffers from already-computed landmarks to avoid duplicate pose processing."""
    tracker_obj.frame_index += 1
    if landmarks is None:
        return

    coords = {}
    selected = (
        mp_pose.PoseLandmark.RIGHT_ELBOW,
        mp_pose.PoseLandmark.RIGHT_WRIST,
        mp_pose.PoseLandmark.LEFT_ELBOW,
        mp_pose.PoseLandmark.LEFT_WRIST,
    )
    for landmark_id in selected:
        lm = landmarks[landmark_id.value]
        coords[landmark_id.name] = {
            "x": int(lm.x * frame_w),
            "y": int(lm.y * frame_h),
        }

    tracker_obj.coord_buffer.append({
        "frame": tracker_obj.frame_index,
        "landmarks": coords,
    })


def render_countdown_frame(frame, countdown_value):
    """Darken frame and draw a large centered countdown number."""
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), thickness=-1)
    dimmed = cv2.addWeighted(overlay, 0.45, frame, 0.55, 0)

    countdown_text = str(countdown_value)
    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale = max(2.0, min(w, h) / 180.0)
    thickness = max(4, int(font_scale * 2))
    text_size, _ = cv2.getTextSize(countdown_text, font, font_scale, thickness)
    text_x = (w - text_size[0]) // 2
    text_y = (h + text_size[1]) // 2

    cv2.putText(dimmed, countdown_text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
    return dimmed


def calibration_checker(frame, landmarks, w, h):
    """
    Check if user is positioned correctly based on shoulder width ratio.
    Returns positioning status and whether calibration is complete.
    
    - Shoulders too close: ratio > 0.30 (user too close to camera)
    - Shoulders too far: ratio < 0.15 (user too far from camera)
    - Correct position: 0.15 <= ratio <= 0.30
    """
    if landmarks is None:
        return frame, None, 0, "", (128, 128, 128)
    
    try:
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        
        # Calculate shoulder positions in pixels
        left_x = int(left_shoulder.x * w)
        right_x = int(right_shoulder.x * w)
        
        # Calculate shoulder width ratio (shoulder distance / frame width)
        shoulder_distance = abs(right_x - left_x)
        shoulder_ratio = shoulder_distance / w if w > 0 else 0
        
        # Determine positioning status
        if shoulder_ratio > 0.30:
            status = "TOO CLOSE"
            color = (0, 0, 255)  # Red
            feedback = "Step back"
        elif shoulder_ratio < 0.15:
            status = "TOO FAR"
            color = (0, 165, 255)  # Orange
            feedback = "Step closer"
        else:
            status = "CORRECT POSITION"
            color = (0, 255, 0)  # Green
            feedback = "Stay still"
        
        return frame, status, shoulder_ratio, feedback, color
        
    except (AttributeError, IndexError):
        return frame, None, 0, "", (128, 128, 128)


def draw_calibration_frame(frame, status, shoulder_ratio, feedback, color):
    """Draw calibration feedback on frame."""
    h, w = frame.shape[:2]
    
    # Darken frame slightly
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), thickness=-1)
    frame = cv2.addWeighted(overlay, 0.2, frame, 0.8, 0)
    
    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale = 1.5
    thickness = 3
    
    # Draw status text
    if status:
        status_size, _ = cv2.getTextSize(status, font, font_scale, thickness)
        status_x = (w - status_size[0]) // 2
        status_y = h // 3
        cv2.putText(frame, status, (status_x, status_y), font, font_scale, color, thickness, cv2.LINE_AA)
    
    # Draw feedback text
    feedback_font_scale = 1.2
    if feedback:
        feedback_size, _ = cv2.getTextSize(feedback, font, feedback_font_scale, thickness)
        feedback_x = (w - feedback_size[0]) // 2
        feedback_y = h // 2
        cv2.putText(frame, feedback, (feedback_x, feedback_y), font, feedback_font_scale, color, thickness, cv2.LINE_AA)
    
    # Draw target ratio range
    range_text = "Optimal: 0.15 - 0.30"
    ratio_text = f"Current: {shoulder_ratio:.3f}"
    small_font_scale = 0.8
    
    range_size, _ = cv2.getTextSize(range_text, font, small_font_scale, 2)
    range_x = (w - range_size[0]) // 2
    range_y = 2 * h // 3
    cv2.putText(frame, range_text, (range_x, range_y), font, small_font_scale, (200, 200, 200), 2, cv2.LINE_AA)
    
    ratio_size, _ = cv2.getTextSize(ratio_text, font, small_font_scale, 2)
    ratio_x = (w - ratio_size[0]) // 2
    ratio_y = 2 * h // 3 + 40
    cv2.putText(frame, ratio_text, (ratio_x, ratio_y), font, small_font_scale, color, 2, cv2.LINE_AA)
    
    return frame


# --- POSITIONING CALIBRATION LOOP ---
# Wait for user to position themselves correctly for 2 seconds before starting countdown
correct_position_start = None
calibration_complete = False

while cap.isOpened() and not calibration_complete:
    ret, frame = cap.read()
    if not ret or frame is None:
        continue

    frame = cv2.flip(frame, 1)
    h, w = frame.shape[:2]
    
    # Process pose to get landmarks
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image.flags.writeable = False
    results = shared_pose.process(image)
    image.flags.writeable = True
    
    try:
        landmarks = results.pose_landmarks.landmark
    except AttributeError:
        landmarks = None
    
    # Check positioning
    _, status, shoulder_ratio, feedback, color = calibration_checker(frame, landmarks, w, h)
    
    # Draw pose landmarks
    mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
    
    # Track time in correct position
    if status == "CORRECT POSITION":
        if correct_position_start is None:
            correct_position_start = time.time()
        
        time_in_position = time.time() - correct_position_start
        
        # Check if user has been in correct position for 2 seconds
        if time_in_position >= 2.0:
            calibration_complete = True
            break
    else:
        # Reset timer if not in correct position
        correct_position_start = None
        time_in_position = 0
    
    # Draw calibration UI
    display_frame = draw_calibration_frame(frame.copy(), status, shoulder_ratio, feedback, color)
    
    # Draw timer if in correct position
    if correct_position_start is not None:
        timer_text = f"Get ready: {2.0 - time_in_position:.1f}s"
        font = cv2.FONT_HERSHEY_DUPLEX
        timer_size, _ = cv2.getTextSize(timer_text, font, 1.0, 2)
        timer_x = (w - timer_size[0]) // 2
        timer_y = h - 50
        cv2.putText(display_frame, timer_text, (timer_x, timer_y), font, 1.0, (0, 255, 0), 2, cv2.LINE_AA)
    
    show_frame(WINDOW_NAME, display_frame)
    
    if wait_key(1):
        cap.release()
        cv2.destroyAllWindows()
        quit()

# --- COUNTDOWN TIMER LOOP ---
countdown_start = time.time()
while cap.isOpened():
    ret, frame = cap.read()
    if not ret or frame is None:
        continue

    elapsed_countdown = time.time() - countdown_start
    remaining = PRESTART_COUNTDOWN_SECONDS - int(elapsed_countdown)

    if remaining <= 0:
        break

    countdown_frame = render_countdown_frame(cv2.flip(frame, 1), remaining)
    show_frame(WINDOW_NAME, countdown_frame)

    if wait_key(1):
        cap.release()
        cv2.destroyAllWindows()
        quit()

start_time = time.time()



while cap.isOpened():
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        ret, frame = cap.read()
        if not ret or frame is None:
            continue  # skip this iteration and try again

        now = time.time()
        elapsed = now - start_time

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        image.flags.writeable = False

        results = shared_pose.process(image)
        
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        h, w = image.shape[:2]

        try:
            landmarks = results.pose_landmarks.landmark
        except AttributeError:
            landmarks = None

        update_tracker_from_landmarks(tracker, landmarks, w, h)

        

        if TARGET_CENTER is None and landmarks is not None:
            TARGET_CENTER = respawn_target(landmarks, w, h, TARGET_RADIUS)
            CURRENT_TYPE = choose_punch_type()
            TARGET_GLOVE_KEY = choose_target_glove_key(CURRENT_TYPE)
            print(CURRENT_TYPE)
            last_spawn_ts, circle_spawn_ts, protect_release_ts = _get_spawn_timing(now, SPAWN_PROTECT_S)

        collide = False
        protecting = protect_release_ts is not None and now < protect_release_ts
        if landmarks is not None and TARGET_CENTER is not None and not protecting:
            collide = wrists_hit_circle(landmarks, w, h, TARGET_CENTER, TARGET_RADIUS)
        
        if not protecting and collide:
            reference_time = circle_spawn_ts if circle_spawn_ts is not None else protect_release_ts
            reaction_time = now - reference_time

            reaction_time_punch[CURRENT_TYPE].append(reaction_time)

            window_idx = _get_time_window_index(elapsed)

            if window_idx is not None:
                reaction_time_windows[window_idx][CURRENT_TYPE].append(reaction_time)
                reaction_window_combined[window_idx].append(reaction_time)

            raw_coords = tracker.get_last_fifteen_coords()
            fps_value = actual_fps if actual_fps and actual_fps > 0 else 30.0
            speed_value = _compute_speed_value(raw_coords, fps_value)
            if speed_value is not None:
                speed_by_type[CURRENT_TYPE].append(speed_value)
                if window_idx is not None:
                    speed_windows[window_idx][CURRENT_TYPE].append(speed_value)
                    speed_window_combined[window_idx].append(speed_value)

            coords = tracker.get_last_normalized_coords()
            predicted_punch = None
            confidence = None
            is_confident = False
            if coords and len(coords) >= MODEL_SEQUENCE_FRAMES:
                # Flatten and normalize like in training
                recent_coords = coords[-MODEL_SEQUENCE_FRAMES:]
                features = _flatten_normalized_features(recent_coords)
                expected_feature_count = MODEL_SEQUENCE_FRAMES * LANDMARK_FEATURES_PER_FRAME

                if len(features) == expected_feature_count:
                    x = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
                    with torch.no_grad():
                        logits = model(x)
                        probs = torch.softmax(logits, dim=1)[0]
                        pred_class = int(probs.argmax().item())
                        confidence = float(probs[pred_class].item())

                    predicted_punch = CLASS_NAMES[pred_class]
                    attempts_by_type[CURRENT_TYPE] += 1
                    punches_thrown += 1
                    if window_idx is not None:
                        accuracy_windows[window_idx]["attempts"] += 1
                    # Treat low-confidence predictions as uncertain to avoid
                    # skewing session accuracy with unreliable classifications.
                    is_confident = confidence >= MODEL_CONF_THRESHOLD
                    if is_confident and predicted_punch == CURRENT_TYPE:
                        correct_punches_thrown += 1
                        correct_by_type[CURRENT_TYPE] += 1
                        if window_idx is not None:
                            accuracy_windows[window_idx]["correct"] += 1

                    probs_dict = {
                        class_name: round(float(probs[i].item()), 3)
                        for i, class_name in enumerate(CLASS_NAMES)
                    }
                    confidence_flag = "" if is_confident else " ⚠️ low-conf"
                    print(f"Model Logits: {logits}")
                    print(f"Predicted Punch: {predicted_punch} ({confidence:.1%}){confidence_flag}")
                    print(f"All probs: {probs_dict}")
                else:
                    print(
                        f"⚠️ Feature length mismatch: got {len(features)}, "
                        f"expected {expected_feature_count}"
                    )

            if predicted_punch is not None and confidence is not None:
                confidence_flag = "" if is_confident else " ⚠️"
                prediction_overlay_text = f"Predicted: {predicted_punch.title()} ({confidence:.0%}){confidence_flag}"
                prediction_overlay_color = (0, 255, 0) if is_confident else (0, 165, 255)
            else:
                prediction_overlay_text = f"Predicted: Warming up ({MODEL_SEQUENCE_FRAMES} frames)"
                prediction_overlay_color = (220, 220, 220)
            prediction_overlay_until = now + PREDICTION_OVERLAY_SECONDS

            TARGET_CENTER = respawn_target(landmarks, w, h, TARGET_RADIUS)
            CURRENT_TYPE = choose_punch_type()
            TARGET_GLOVE_KEY = choose_target_glove_key(CURRENT_TYPE)
            print(CURRENT_TYPE, "<-----")
            print(correct_by_type)
            print(attempts_by_type)
            last_spawn_ts, circle_spawn_ts, protect_release_ts = _get_spawn_timing(now, SPAWN_PROTECT_S)
        
        if TARGET_CENTER is not None and CURRENT_TYPE is not None:
            glove_image = glove_images.get(TARGET_GLOVE_KEY)
            if glove_image is not None:
                draw_target_glove(image, TARGET_CENTER, TARGET_RADIUS, glove_image, TARGET_GLOVE_KEY)
            else:
                # Fallback if an expected punchpad image is missing.
                color = PUNCH_COLORS.get(CURRENT_TYPE, (0, 0, 255))
                cv2.circle(image, TARGET_CENTER, TARGET_RADIUS, color, -1)

        defense_game.update(image, landmarks, now)

        display_image = cv2.flip(image, 1)

        if prediction_overlay_text and now <= prediction_overlay_until:
            overlay_font = cv2.FONT_HERSHEY_DUPLEX
            overlay_scale = 1.0
            overlay_thickness = 2
            text_size, _ = cv2.getTextSize(prediction_overlay_text, overlay_font, overlay_scale, overlay_thickness)
            text_x = max((display_image.shape[1] - text_size[0]) // 2, 10)
            text_y = max(int(display_image.shape[0] * 0.1), text_size[1] + 16)
            pad = 12

            cv2.rectangle(
                display_image,
                (text_x - pad, text_y - text_size[1] - pad),
                (text_x + text_size[0] + pad, text_y + pad),
                (0, 0, 0),
                -1,
            )
            cv2.rectangle(
                display_image,
                (text_x - pad, text_y - text_size[1] - pad),
                (text_x + text_size[0] + pad, text_y + pad),
                prediction_overlay_color,
                2,
            )
            cv2.putText(
                display_image,
                prediction_overlay_text,
                (text_x, text_y),
                overlay_font,
                overlay_scale,
                prediction_overlay_color,
                overlay_thickness,
                cv2.LINE_AA,
            )

        show_frame(WINDOW_NAME, display_image)

        if wait_key(1):
            break
        if elapsed >= MAX_RUNTIME:
            break

all_reaction_times = [t for times in reaction_time_punch.values() for t in times]

def round_or_none(value, digits=2):
    return round(value, digits) if value is not None else None

reaction_types_ms = {}
for punch_type, times in reaction_time_punch.items():
    if times:
        avg_ms = (sum(times) / len(times)) * 1000
        reaction_types_ms[punch_type] = round_or_none(avg_ms)
    else:
        reaction_types_ms[punch_type] = None

reaction_all_points_ms = []
for window_times in reaction_window_combined:
    if window_times:
        avg_ms = (sum(window_times) / len(window_times)) * 1000
        reaction_all_points_ms.append(round_or_none(avg_ms))
    else:
        reaction_all_points_ms.append(None)

if all_reaction_times:
    reaction_average_ms = round_or_none((sum(all_reaction_times) / len(all_reaction_times)) * 1000)
    reaction_best_ms = round_or_none(min(all_reaction_times) * 1000)
    reaction_worst_ms = round_or_none(max(all_reaction_times) * 1000)
else:
    reaction_average_ms = reaction_best_ms = reaction_worst_ms = None

accuracy_types = {}
for punch_type in reaction_time_punch.keys():
    attempts = attempts_by_type[punch_type]
    correct = correct_by_type[punch_type]
    if attempts:
        accuracy_types[punch_type] = round_or_none((correct / attempts) * 100)
    else:
        accuracy_types[punch_type] = None

window_accuracy_points = []
for window in accuracy_windows:
    if window["attempts"]:
        window_accuracy_points.append(round_or_none((window["correct"] / window["attempts"]) * 100))
    else:
        window_accuracy_points.append(None)

if punches_thrown:
    overall_accuracy_percent = round_or_none((correct_punches_thrown / punches_thrown) * 100)
else:
    overall_accuracy_percent = None

valid_accuracy_points = [pt for pt in window_accuracy_points if pt is not None]
if valid_accuracy_points:
    accuracy_best = max(valid_accuracy_points)
    accuracy_worst = min(valid_accuracy_points)
else:
    accuracy_best = accuracy_worst = None

all_speeds = [s for values in speed_by_type.values() for s in values]

speed_types = {}
for punch_type, values in speed_by_type.items():
    if values:
        speed_types[punch_type] = round_or_none(sum(values) / len(values))
    else:
        speed_types[punch_type] = None

speed_all_points = []
for window_values in speed_window_combined:
    if window_values:
        speed_all_points.append(round_or_none(sum(window_values) / len(window_values)))
    else:
        speed_all_points.append(None)

if all_speeds:
    speed_average = round_or_none(sum(all_speeds) / len(all_speeds))
    speed_best = round_or_none(max(all_speeds))
    speed_worst = round_or_none(min(all_speeds))
else:
    speed_average = speed_best = speed_worst = None

speed_segments = {
    "first_third": speed_all_points[0],
    "second_third": speed_all_points[1],
    "final_third": speed_all_points[2],
}

defense_totals = defense_game.get_stats()
defense_total_events = sum(defense_totals.values())
if defense_total_events:
    punches_avoided_percent = round_or_none(
        ((defense_totals["blocked"] + defense_totals["dodged"]) / defense_total_events) * 100
    )
else:
    punches_avoided_percent = None

critical_hit_percentages = {}
for area_key, stats in coverage_tracker.items():
    if stats["total"]:
        uncovered_pct = ((stats["total"] - stats["covered"]) / stats["total"]) * 100
        critical_hit_percentages[area_key] = round_or_none(uncovered_pct)
    else:
        critical_hit_percentages[area_key] = None

exposure_weights_values = {}
for area_key, stats in exposure_tracker.items():
    if stats["total"]:
        exposed_ratio = (stats["total"] - stats["covered"]) / stats["total"]
        exposure_weights_values[area_key] = round_or_none(exposed_ratio)
    else:
        exposure_weights_values[area_key] = None

endurance_segments = {
    "first_third": round_or_none(window_accuracy_points[0]) if len(window_accuracy_points) > 0 else None,
    "second_third": round_or_none(window_accuracy_points[1]) if len(window_accuracy_points) > 1 else None,
    "final_third": round_or_none(window_accuracy_points[2]) if len(window_accuracy_points) > 2 else None,
}

fighter_id = "fighter_sample_001"
session_id = f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
timestamp_iso = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

session_payload = [{
    "fighter_id": fighter_id,
    "session_id": session_id,
    "timestamp": timestamp_iso,
    "punches_thrown": punches_thrown,
    "correct_punches": correct_punches_thrown,
    "metrics": {
        "offense": {
            "punch_accuracy": {
                "unit": "%",
                "types": accuracy_types,
                "derived": {
                    "average": overall_accuracy_percent,
                    "average_description": "Average of all recorded punch accuracies across the session.",
                    "best": accuracy_best,
                    "worst": accuracy_worst,
                    "all_points": window_accuracy_points
                }
            },
            "punch_reaction_time": {
                "unit": "ms",
                "types": reaction_types_ms,
                "derived": {
                    "average": reaction_average_ms,
                    "average_description": "Average reaction time, in milliseconds, measured across all punches.",
                    "best": reaction_best_ms,
                    "worst": reaction_worst_ms,
                    "all_points": reaction_all_points_ms,
                    "all_points_description": "Reaction time averages for each 10-second segment of the session."
                }
            },
            "punch_speed": {
                "unit": "px/s",
                "types": speed_types,
                "derived": {
                    "average": speed_average,
                    "average_description": "Mean punch speed across all punch types during the session.",
                    "best": speed_best,
                    "worst": speed_worst,
                    "all_points": speed_all_points,
                    "combo_tempo": {
                        "unit": "px/s",
                        "segments": speed_segments,
                        "description": "Average punch speed per 10-second segment of the session."
                    }
                }
            }
        },
        "defense": {
            "critical_hit_opportunities": {
                "unit": "% of body",
                "areas": {
                    "head": critical_hit_percentages.get("head"),
                    "body": critical_hit_percentages.get("body"),
                }
            },
            "exposure_weights": {
                "unit": "relative_weight_0_to_1",
                "description": "Relative weighting (0–1) showing how exposed each body area was across all sampled frames.",
                "areas": exposure_weights_values,
            },
            "endurance": {
                "unit": "%",
                "description": "Average accuracy over each third of the session, representing endurance and fatigue levels.",
                "segments": endurance_segments,
            },
            "punches_avoided": {
                "unit": "%",
                "value": punches_avoided_percent,
                "description": "Percentage of incoming targets that were blocked or dodged."
            }
        },
        "miscellaneous": {
            "flying_blocks_summary": {
                "unit": "count",
                "values": defense_totals,
                "description": "Counts of block, dodge, and hit outcomes from the flying blocks drill."
            }
        }
    }
}]

with open("session_metrics.json", "w", encoding="utf-8") as metric_file:
    json.dump(session_payload, metric_file, indent=2)

print("Session metrics written to session_metrics.json")
print(
    "Defense stats - Blocked: {blocked}, Dodged: {dodged}, Hit: {hit}".format(
        blocked=defense_totals["blocked"],
        dodged=defense_totals["dodged"],
        hit=defense_totals["hit"],
    )
)

tracker.stop()
cap.release()
cv2.destroyAllWindows()
quit()

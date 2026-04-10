import cv2
import mediapipe as mp
import time
import concurrent.futures
import ctypes
import json
import math
from datetime import datetime

import torch
import torch.nn as nn
import torch.nn.functional as F

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

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose


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
        if record["landmarks"]:
            for key in record["landmarks"].values():
                features.extend([key["x"], key["y"]])
    return features

class Model(nn.Module):
    def __init__(self, in_features=120, h1=128, h2=64, out_features=3):
        super(Model, self).__init__()
        self.fc1 = nn.Linear(in_features, h1)
        self.fc2 = nn.Linear(h1, h2)
        self.out = nn.Linear(h2, out_features)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.out(x)
        return x


# --- Parallel initialization functions ---
def _load_camera():
    """Initialize camera and warm it up with first frame read."""
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    # Reduce webcam latency by limiting queued frames and capture size.
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.read()  # Warm up - first read is slower
    return cap

def _load_torch_model():
    """Load PyTorch punch classifier model."""
    model = Model()
    model.load_state_dict(torch.load("perfectpunch_backend/models/model_state.pt"))
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

tracker = PoseTracker(max_frames=15, pose=shared_pose)
glove_images = {key: load_target_glove_image(key) for key in ("green_left", "green_right", "uppercut_left", "uppercut_right", "jab_left", "jab_right")}

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
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
cv2.waitKey(1)  # Let the window initialize

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
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
    style &= ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU)
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)
    # Refresh the window to apply changes
    SWP_FRAMECHANGED = 0x0020
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOZORDER = 0x0004
    ctypes.windll.user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER)

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
    
    cv2.imshow(WINDOW_NAME, display_frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
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
    cv2.imshow(WINDOW_NAME, countdown_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
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
            if coords and len(coords) >= 15:
                # Flatten and normalize like in training
                features = _flatten_normalized_features(coords)
                if len(features) == 120:
                    x = torch.tensor(features, dtype=torch.float32).unsqueeze(0)  # shape [1, 120]
                    with torch.no_grad():
                        output = model(x)
                        pred_class = output.argmax(dim=1).item()

                    punch_map = {0: "hook", 1: "jab", 2: "uppercut"}
                    predicted_punch = punch_map[pred_class]
                    attempts_by_type[CURRENT_TYPE] += 1
                    punches_thrown += 1
                    if window_idx is not None:
                        accuracy_windows[window_idx]["attempts"] += 1
                    if predicted_punch == CURRENT_TYPE:
                        correct_punches_thrown += 1
                        correct_by_type[CURRENT_TYPE] += 1
                        if window_idx is not None:
                            accuracy_windows[window_idx]["correct"] += 1

                    print(f"Model Output: {output}")
                    print(f"Predicted Punch: {predicted_punch}")
            TARGET_CENTER = respawn_target(landmarks, w, h, TARGET_RADIUS)
            CURRENT_TYPE = choose_punch_type()
            TARGET_GLOVE_KEY = choose_target_glove_key(CURRENT_TYPE)
            print(CURRENT_TYPE, "<-----")
            print(correct_by_type)
            print(attempts_by_type)
            last_spawn_ts, circle_spawn_ts, protect_release_ts = _get_spawn_timing(now, SPAWN_PROTECT_S)
        
        if TARGET_CENTER is not None and CURRENT_TYPE is not None:
            glove_image = glove_images.get(TARGET_GLOVE_KEY)
            if CURRENT_TYPE == "hook":
                print(f"DEBUG MAIN: Hook detected. CURRENT_TYPE={CURRENT_TYPE}, TARGET_GLOVE_KEY={TARGET_GLOVE_KEY}, glove_image is None: {glove_image is None}")
            if glove_image is not None:
                draw_target_glove(image, TARGET_CENTER, TARGET_RADIUS, glove_image, TARGET_GLOVE_KEY)
            else:
                if CURRENT_TYPE == "hook":
                    print(f"DEBUG MAIN: glove_image is None for hook!")

        defense_game.update(image, landmarks, now)

        display_image = cv2.flip(image, 1)
        cv2.imshow(WINDOW_NAME, display_image)

        if cv2.waitKey(1) & 0xFF == ord('q'):
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

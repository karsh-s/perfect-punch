"""Pose tracking utilities shared between realtime demo code and backend inference."""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, Iterable, List, Optional

import mediapipe as mp
import numpy as np

mp_pose = mp.solutions.pose


class PoseTracker:
    """Maintains a rolling buffer of pose landmarks and produces normalized coordinates."""

    SELECTED_LANDMARKS: List[mp_pose.PoseLandmark] = [
        mp_pose.PoseLandmark.RIGHT_ELBOW,
        mp_pose.PoseLandmark.RIGHT_WRIST,
        mp_pose.PoseLandmark.LEFT_ELBOW,
        mp_pose.PoseLandmark.LEFT_WRIST,
    ]

    def __init__(self, max_frames: int = 15) -> None:
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.frame_buffer: Deque[np.ndarray] = deque(maxlen=max_frames)
        self.coord_buffer: Deque[Optional[Dict[str, Dict[str, float]]]] = deque(maxlen=max_frames)
        self.frame_index = 0
        self.max_frames = max_frames
        self.running = False
        self._ordered_names = [landmark.name for landmark in self.SELECTED_LANDMARKS]

    @property
    def ordered_landmark_names(self) -> Iterable[str]:
        return self._ordered_names

    def process_frame(self, frame: np.ndarray) -> None:
        """Process a single BGR frame and update the coordinated buffers."""
        self.frame_index += 1
        frame_rgb = np.copy(frame)
        frame_rgb.flags["WRITEABLE"] = False
        results = self.pose.process(frame_rgb)
        frame_rgb.flags["WRITEABLE"] = True

        landmarks_record: Dict[str, Optional[Dict[str, Dict[str, float]]]] = {
            "frame": self.frame_index,
            "landmarks": None,
        }

        if results.pose_landmarks:
            h, w, _ = frame.shape
            coords: Dict[str, Dict[str, float]] = {}

            for landmark_id in self.SELECTED_LANDMARKS:
                lm = results.pose_landmarks.landmark[landmark_id]
                x, y = float(lm.x * w), float(lm.y * h)
                coords[landmark_id.name] = {"x": x, "y": y, "visibility": float(lm.visibility)}

            landmarks_record["landmarks"] = coords

        self.coord_buffer.append(landmarks_record["landmarks"])
        self.frame_buffer.append(np.copy(frame))

    def get_last_normalized_coords(self) -> List[Dict[str, Dict[str, float]]]:
        """Return landmark coordinates normalized relative to the first frame in the buffer."""
        if len(self.coord_buffer) == 0:
            return []

        frames: List[int] = []
        coord_rows: List[np.ndarray] = []

        for offset, landmarks in enumerate(self.coord_buffer):
            if not landmarks:
                continue

            try:
                frame_coords = np.array(
                    [[landmarks[name]["x"], landmarks[name]["y"]] for name in self._ordered_names],
                    dtype=np.float32,
                )
            except KeyError:
                continue

            frames.append(self.frame_index - len(self.coord_buffer) + 1 + offset)
            coord_rows.append(frame_coords)

        if not coord_rows:
            return []

        coords_array = np.stack(coord_rows, axis=0)
        relative = coords_array - coords_array[0]
        distances = np.linalg.norm(relative, axis=2)
        max_distance = float(distances.max()) if distances.size else 0.0

        if max_distance > 0.0:
            relative /= max_distance

        normalized_records: List[Dict[str, Dict[str, float]]] = []
        for frame_idx, points in zip(frames, relative):
            normalized_records.append(
                {
                    "frame": frame_idx,
                    "landmarks": {
                        name: {"x": float(coord[0]), "y": float(coord[1])}
                        for name, coord in zip(self._ordered_names, points)
                    },
                }
            )

        return normalized_records

    def close(self) -> None:
        """Release the underlying Mediapipe resources."""
        self.pose.close()




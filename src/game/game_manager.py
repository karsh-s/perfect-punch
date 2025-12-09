from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime
import asyncio
import torch
import numpy as np
import random

@dataclass
class Target:
    center_x: int
    center_y: int
    radius: int = 25
    punch_type: str = "jab"  # "jab", "hook", "uppercut"
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())

@dataclass
class GameSession:
    session_id: str
    user_id: str
    start_time: float
    max_duration: int = 30  # seconds
    score: int = 0
    targets_hit: int = 0
    total_targets: int = 0
    current_target: Optional[Target] = None
    is_active: bool = True
    punch_history: List[Dict] = field(default_factory=list)

class GameManager:
    def __init__(self):
        self.sessions: Dict[str, GameSession] = {}
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
    def load_model(self, model_path: str):
        """Load the trained punch classification model"""
        try:
            # Import your model architecture (adjust path as needed)
            from ..models.punch_classifier import PunchClassifierModel
            
            self.model = PunchClassifierModel()
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
            self.model.eval()
            self.model.to(self.device)
            print(f"✓ Model loaded from {model_path}")
        except Exception as e:
            print(f"✗ Failed to load model: {e}")
            self.model = None
        
    def create_session(self, user_id: str) -> GameSession:
        """Create a new game session"""
        session_id = f"{user_id}_{int(datetime.now().timestamp() * 1000)}"
        session = GameSession(
            session_id=session_id,
            user_id=user_id,
            start_time=datetime.now().timestamp()
        )
        self.sessions[session_id] = session
        self.spawn_target(session_id)
        return session
    
    def spawn_target(self, session_id: str) -> Optional[Target]:
        """Spawn a new target with weighted random punch type (matches target_utils.py logic)"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        # Weighted selection: jab (62.5%), hook (25%), uppercut (12.5%)
        r = random.random()
        if r < 0.625:
            punch_type = "jab"
        elif r < 0.875:
            punch_type = "hook"
        else:
            punch_type = "uppercut"
        
        # Generate random position (will be validated by frontend camera frame)
        target = Target(
            center_x=random.randint(150, 500),
            center_y=random.randint(100, 400),
            punch_type=punch_type
        )
        
        session.current_target = target
        session.total_targets += 1
        return target
    
    def normalize_landmarks(self, landmark_data: List[Dict]) -> Optional[np.ndarray]:
        """
        Normalize landmark coordinates to match extractDataPoints.py logic.
        Expects list of dicts with structure: [{"frame": int, "landmarks": {...}}, ...]
        """
        if not landmark_data or len(landmark_data) == 0:
            return None
        
        # Extract coordinates in consistent order
        ordered_names = ["RIGHT_ELBOW", "RIGHT_WRIST", "LEFT_ELBOW", "LEFT_WRIST"]
        coord_rows = []
        
        for record in landmark_data:
            landmarks = record.get("landmarks")
            if not landmarks:
                continue
            
            try:
                frame_coords = [[landmarks[name]["x"], landmarks[name]["y"]] for name in ordered_names]
                coord_rows.append(frame_coords)
            except KeyError:
                continue
        
        if not coord_rows or len(coord_rows) < 15:
            return None  # Need 15 frames
        
        # Take last 15 frames if we have more
        coord_rows = coord_rows[-15:]
        
        # Convert to numpy and normalize (matches extractDataPoints.py)
        coords_array = np.array(coord_rows, dtype=np.float32)  # [15, 4, 2]
        relative = coords_array - coords_array[0]  # Relative to first frame
        
        distances = np.linalg.norm(relative, axis=2)  # [15, 4]
        max_distance = float(distances.max()) if distances.size else 0.0
        
        if max_distance > 0.0:
            relative /= max_distance
        
        # Flatten to [120] for model input (15 frames * 4 landmarks * 2 coords)
        return relative.flatten()
    
    async def validate_punch(
        self, 
        session_id: str, 
        landmark_data: List[Dict]
    ) -> Dict:
        """Validate if the detected punch matches the target"""
        session = self.sessions.get(session_id)
        if not session or not session.current_target:
            return {"valid": False, "message": "No active target"}
        
        if not self.model:
            return {"valid": False, "message": "Model not loaded"}
        
        target = session.current_target
        
        # Normalize landmarks
        normalized = self.normalize_landmarks(landmark_data)
        if normalized is None:
            return {"valid": False, "message": "Invalid landmark data"}
        
        # Convert to tensor and predict
        x = torch.from_numpy(normalized).unsqueeze(0).float().to(self.device)
        
        with torch.no_grad():
            output = self.model(x)
            pred_class = output.argmax(dim=1).item()
        
        # Map prediction (0: hook, 1: uppercut, 2: jab - adjust based on your training)
        punch_map = {0: "hook", 1: "uppercut", 2: "jab"}
        predicted_punch = punch_map.get(pred_class, "unknown")
        
        # Check if prediction matches target
        is_correct = predicted_punch == target.punch_type
        
        if is_correct:
            session.score += 100
            session.targets_hit += 1
        
        # Record punch attempt
        session.punch_history.append({
            "timestamp": datetime.now().timestamp(),
            "target_type": target.punch_type,
            "detected_type": predicted_punch,
            "is_correct": is_correct,
            "score_delta": 100 if is_correct else 0
        })
        
        # Spawn new target
        new_target = self.spawn_target(session_id)
        
        return {
            "valid": True,
            "is_correct": is_correct,
            "predicted_punch": predicted_punch,
            "expected_punch": target.punch_type,
            "score": session.score,
            "targets_hit": session.targets_hit,
            "total_targets": session.total_targets,
            "new_target": {
                "x": new_target.center_x,
                "y": new_target.center_y,
                "type": new_target.punch_type,
                "radius": new_target.radius
            } if new_target else None
        }
    
    def get_session_stats(self, session_id: str) -> Optional[Dict]:
        """Get current session statistics"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        elapsed = datetime.now().timestamp() - session.start_time
        remaining = max(0, session.max_duration - elapsed)
        
        return {
            "session_id": session_id,
            "score": session.score,
            "targets_hit": session.targets_hit,
            "total_targets": session.total_targets,
            "accuracy": session.targets_hit / session.total_targets if session.total_targets > 0 else 0,
            "time_remaining": int(remaining),
            "is_active": remaining > 0,
            "punch_history": session.punch_history
        }
    
    def end_session(self, session_id: str) -> Optional[Dict]:
        """End a game session and return final stats"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        session.is_active = False
        stats = self.get_session_stats(session_id)
        
        # Schedule cleanup after 5 minutes
        asyncio.create_task(self._cleanup_session(session_id, delay=300))
        
        return stats
    
    async def _cleanup_session(self, session_id: str, delay: int):
        """Remove old session after delay"""
        await asyncio.sleep(delay)
        if session_id in self.sessions:
            del self.sessions[session_id]
            print(f"✓ Cleaned up session {session_id}")

# Global singleton instance
game_manager = GameManager()
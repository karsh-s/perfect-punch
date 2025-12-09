import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class PunchClassifierModel(nn.Module):
    def __init__(self, in_features=120, h1=128, h2=64, out_features=3):
        super().__init__()
        self.fc1 = nn.Linear(in_features, h1)
        self.fc2 = nn.Linear(h1, h2)
        self.out = nn.Linear(h2, out_features)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.out(x)
        return x

class PunchClassifier:
    def __init__(self):
        self.model = PunchClassifierModel()
        self.punch_map = {0: "hook", 1: "jab", 2: "uppercut"}
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
    def load_model(self, model_path: str):
        """Load trained model weights"""
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()
        self.model.to(self.device)
    
    def normalize_landmarks(self, coords: list) -> np.ndarray:
        """Normalize landmark coordinates (matches extractDataPoints.py logic)"""
        if not coords or len(coords) == 0:
            return None
            
        coords_array = np.array(coords, dtype=np.float32)
        relative = coords_array - coords_array[0]
        
        distances = np.linalg.norm(relative, axis=1)
        max_distance = float(distances.max()) if distances.size else 0.0
        
        if max_distance > 0.0:
            relative /= max_distance
            
        return relative.flatten()  # Shape: [120]
    
    def predict(self, landmark_data: list) -> str:
        """
        Predict punch type from landmark data
        landmark_data: list of dicts with normalized coordinates
        """
        # Flatten landmarks into features
        features = []
        for record in landmark_data:
            if record.get("landmarks"):
                for key in record["landmarks"].values():
                    features.extend([key["x"], key["y"]])
        
        if len(features) != 120:  # 4 landmarks * 2 coords * 15 frames
            return "unknown"
        
        # Convert to tensor
        x = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
        x = x.to(self.device)
        
        # Make prediction
        with torch.no_grad():
            output = self.model(x)
            pred_class = output.argmax(dim=1).item()
        
        return self.punch_map.get(pred_class, "unknown")
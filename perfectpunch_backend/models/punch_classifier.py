import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Optional, Tuple
import os


class PunchClassifierModel(nn.Module):
    """PyTorch neural network model for punch classification."""
    
    def __init__(self, in_features=120, h1=128, h2=64, out_features=3):
        super(PunchClassifierModel, self).__init__()
        self.fc1 = nn.Linear(in_features, h1)
        self.fc2 = nn.Linear(h1, h2)
        self.out = nn.Linear(h2, out_features)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.out(x)
        return x


class PunchClassifier:
    """Service class for loading model and making punch predictions."""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.punch_map = {0: "hook", 1: "jab", 2: "uppercut"}
        self.reverse_punch_map = {"hook": 0, "jab": 1, "uppercut": 2}
        
        if model_path is None:
            # Default path relative to the perfectpunch_backend directory
            model_path = os.path.join(os.path.dirname(__file__), "model_state.pt")
            
        self.model_path = model_path
        self.load_model()
    
    def load_model(self) -> None:
        """Load the trained model from the state dict file."""
        try:
            self.model = PunchClassifierModel()
            state_dict = torch.load(self.model_path, map_location=self.device)
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()
            print(f"Model loaded successfully from {self.model_path}")
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = None
    
    def prepare_features(self, pose_coords: List[Dict]) -> Optional[torch.Tensor]:
        """
        Convert pose coordinates to model input features.
        
        Args:
            pose_coords: List of pose coordinate records from PoseTracker
            
        Returns:
            Tensor ready for model input or None if invalid data
        """
        if not pose_coords or len(pose_coords) == 0:
            return None
            
        features = []
        for record in pose_coords:
            if record.get("landmarks"):
                for landmark_data in record["landmarks"].values():
                    features.extend([landmark_data.get("x", 0), landmark_data.get("y", 0)])
        
        if len(features) != 120:  # Expected feature length (15 frames * 8 landmarks * x,y)
            print(f"Warning: Expected 120 features, got {len(features)}")
            return None
            
        return torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(self.device)
    
    def predict(self, pose_coords: List[Dict]) -> Optional[Dict]:
        """
        Predict punch type from pose coordinates.
        
        Args:
            pose_coords: List of pose coordinate records
            
        Returns:
            Dictionary with prediction results or None if prediction failed
        """
        if self.model is None:
            return None
            
        features = self.prepare_features(pose_coords)
        if features is None:
            return None
            
        try:
            with torch.no_grad():
                output = self.model(features)
                probabilities = F.softmax(output, dim=1)
                predicted_class = output.argmax(dim=1).item()
                confidence = probabilities[0][predicted_class].item()
                
                return {
                    "punch_type": self.punch_map[predicted_class],
                    "confidence": confidence,
                    "class_id": predicted_class,
                    "probabilities": {
                        punch_type: prob.item() 
                        for punch_type, prob in zip(self.punch_map.values(), probabilities[0])
                    }
                }
        except Exception as e:
            print(f"Prediction error: {e}")
            return None
    
    def predict_from_features(self, features: List[float]) -> Optional[Dict]:
        """
        Direct prediction from feature vector.
        
        Args:
            features: Flattened feature vector (length 120)
            
        Returns:
            Dictionary with prediction results or None if prediction failed
        """
        if self.model is None or len(features) != 120:
            return None
            
        try:
            x = torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                output = self.model(x)
                probabilities = F.softmax(output, dim=1)
                predicted_class = output.argmax(dim=1).item()
                confidence = probabilities[0][predicted_class].item()
                
                return {
                    "punch_type": self.punch_map[predicted_class],
                    "confidence": confidence,
                    "class_id": predicted_class,
                    "probabilities": {
                        punch_type: prob.item() 
                        for punch_type, prob in zip(self.punch_map.values(), probabilities[0])
                    }
                }
        except Exception as e:
            print(f"Prediction error: {e}")
            return None
    
    def get_punch_types(self) -> List[str]:
        """Get list of supported punch types."""
        return list(self.punch_map.values())
    
    def is_loaded(self) -> bool:
        """Check if model is properly loaded."""
        return self.model is not None
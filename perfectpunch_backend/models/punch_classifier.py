import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Optional, Tuple
import os


class SpatialConvBlock(nn.Sequential):
    """Spatial convolution block for 2D spatial features."""
    def __init__(self, in_channels, out_channels):
        super(SpatialConvBlock, self).__init__(
            nn.Conv3d(in_channels, out_channels, kernel_size=(1, 3, 3), padding=(0, 1, 1), bias=False),
            nn.BatchNorm3d(out_channels),
            nn.ReLU(inplace=True)
        )


class TemporalConvBlock(nn.Sequential):
    """Temporal convolution block for temporal features."""
    def __init__(self, in_channels, out_channels):
        super(TemporalConvBlock, self).__init__(
            nn.Conv3d(in_channels, out_channels, kernel_size=(3, 1, 1), padding=(1, 0, 0), bias=False),
            nn.BatchNorm3d(out_channels),
            nn.ReLU(inplace=True)
        )


class ResidualBlock(nn.Sequential):
    """Residual block with 1x1x1 convolution."""
    def __init__(self, in_channels, out_channels):
        super(ResidualBlock, self).__init__(
            nn.Conv3d(in_channels, out_channels, kernel_size=(1, 1, 1), bias=False),
            nn.BatchNorm3d(out_channels),
            nn.ReLU(inplace=True)
        )


class ConvLayer(nn.Module):
    """Residual layer with spatial, temporal, and residual branches."""
    def __init__(self, in_channels, spatial_out, temporal_out, residual_out):
        super(ConvLayer, self).__init__()
        self.spatial = SpatialConvBlock(in_channels, spatial_out)
        self.temporal = TemporalConvBlock(spatial_out, temporal_out)
        self.residual = ResidualBlock(in_channels, residual_out)
    
    def forward(self, x):
        spatial = self.spatial(x)
        temporal = self.temporal(spatial)
        residual = self.residual(x)
        # Residual connection: add residual branch to temporal output
        out = temporal + residual
        return out


class SimpleConvLayer(nn.Module):
    """Simple layer with spatial and temporal branches (no residual)."""
    def __init__(self, in_channels, spatial_out, temporal_out):
        super(SimpleConvLayer, self).__init__()
        self.spatial = SpatialConvBlock(in_channels, spatial_out)
        self.temporal = TemporalConvBlock(spatial_out, temporal_out)
    
    def forward(self, x):
        spatial = self.spatial(x)
        temporal = self.temporal(spatial)
        return temporal


class PunchClassifierModel(nn.Module):
    """3D CNN model for punch classification using spatial and temporal features."""
    
    def __init__(self, num_classes=3):
        super(PunchClassifierModel, self).__init__()
        
        # Stem layer: Initial 3D convolution (expects 7 input channels)
        self.stem = nn.Sequential(
            nn.Conv3d(7, 32, kernel_size=(3, 3, 3), padding=(1, 1, 1), bias=False),
            nn.BatchNorm3d(32),
            nn.ReLU(inplace=True)
        )
        
        # Residual layers with spatial, temporal, and residual connections
        self.layer1 = ConvLayer(32, 32, 64, 64)    # 32 -> 64
        self.layer2 = ConvLayer(64, 64, 128, 128)  # 64 -> 128
        self.layer3 = ConvLayer(128, 128, 256, 256)  # 128 -> 256
        self.layer4 = SimpleConvLayer(256, 256, 256)  # 256 -> 256 (no residual)
        self.layer5 = ConvLayer(256, 256, 512, 512)  # 256 -> 512
        self.layer6 = SimpleConvLayer(512, 512, 512)  # 512 -> 512 (no residual)
        
        # Global average pooling
        self.avg_pool = nn.AdaptiveAvgPool3d((1, 1, 1))
        
        # Classifier head
        self.classifier = nn.Sequential(
            nn.Identity(),                  # Index 0 (placeholder, no weights)
            nn.Identity(),                  # Index 1 (placeholder, no weights)
            nn.Linear(512, 256),            # Index 2 (checkpoint)
            nn.ReLU(inplace=True),          # Index 3
            nn.Dropout(0.5),                # Index 4
            nn.Linear(256, num_classes)     # Index 5 (checkpoint)
        )
    
    def forward(self, x):
        # x shape: (batch, channels, depth, height, width)
        # If input is 2D features (batch, features), reshape to (batch, 1, frames, 1, 1)
        if x.dim() == 2:
            # Reshape features to 3D volume
            batch_size = x.shape[0]
            # Assuming 120 features = 15 frames * 8 landmarks * (x,y)
            # Reshape to (batch, 1, 15, 8, 1) for 3D conv
            x = x.view(batch_size, 1, 15, 8, 1)
        
        x = self.stem(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.layer5(x)
        x = self.layer6(x)
        
        x = self.avg_pool(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        
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
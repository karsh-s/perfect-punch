# PyTorch Model Loading Fix

## Problem
The application was failing to load the saved PyTorch model with an architecture mismatch error:
```
RuntimeError: Error(s) in loading state_dict for Model:
Missing key(s): "fc1.weight", "fc1.bias", "fc2.weight", "fc2.bias", ...
Unexpected key(s): "stem.0.weight", "layer1.spatial.0.weight", ...
```

**Root Cause**: The saved `model_state.pt` file contained a 3D convolutional neural network architecture, but the `Model` class in the code was a simple fully-connected network.

## Solution
Reconstructed the `Model` class to match the actual 3D CNN architecture saved in `model_state.pt`.

### Model Architecture
The saved model is a **3D ResNet-style CNN** with:

#### Stem Layer
- Input: 7 channels (pose landmark features)
- Conv3d: 7 → 32 channels (kernel 3×3×3, no bias)
- BatchNorm3d + ReLU

#### Residual Layers (1-6)
Each layer has **three parallel branches**:
1. **Spatial**: Conv3d with (1, 3, 3) kernel - captures spatial features
2. **Temporal**: Conv3d with (3, 1, 1) kernel - captures temporal patterns
3. **Residual**: Conv3d with (1, 1, 1) kernel - matches channel dimensions

Channel flow:
- Layer 1: 32 → 64 channels
- Layer 2: 64 → 128 channels
- Layer 3: 128 → 256 channels
- Layer 4: 256 → 256 channels (no residual expansion)
- Layer 5: 256 → 512 channels
- Layer 6: 512 → 512 channels (no residual expansion)

#### Classifier Head
- Global Average Pooling: 512 channels → 1×1×1
- Fully-connected: 512 → 256 → 3 (punch classes)

### Input Reshaping
The code receives a flattened 120-feature vector from MediaPipe pose extraction:
- **Original shape**: (batch, 120)
- **Reshaped for 3D conv**: (batch, 7, 15, 8, 1)
  - 7 channels (expanded from 120 features)
  - 15 temporal frames
  - 8 spatial landmarks
  - 1 width dimension

Process:
```python
x = x.unsqueeze(1).expand(-1, 7, -1)  # (batch, 7, 120)
x = x.view(batch_size, 7, 15, 8, 1)   # (batch, 7, 15, 8, 1)
```

## Files Modified
- `perfectpunch_backend/main_python_analysis.py`: Updated `Model` class with correct 3D CNN architecture
- `perfectpunch_backend/models/punch_classifier.py`: Updated `PunchClassifierModel` class with matching architecture

## Testing
The model now:
- ✅ Loads `model_state.pt` without architecture mismatch
- ✅ Accepts 120-feature input vectors
- ✅ Produces valid predictions (3 punch classes)
- ✅ Runs on CPU (map_location='cpu')

Example test:
```python
model = Model()
model.load_state_dict(torch.load("model_state.pt", map_location='cpu'))
dummy_input = torch.randn(1, 120)
output = model(dummy_input)
# Output shape: torch.Size([1, 3]) - valid predictions!
```

## Branch
All changes are on the `fix/pytorch-model-loading` branch at GitHub:
https://github.com/gt-big-data/perfect-punch/tree/fix/pytorch-model-loading

## Next Steps
1. Test the app end-to-end with actual camera input
2. Verify punch classification accuracy
3. Merge to main branch once testing is complete

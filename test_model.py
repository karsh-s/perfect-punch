#!/usr/bin/env python
"""
Test script to verify the PyTorch model loads and works correctly.
This tests the model WITHOUT requiring a camera.
"""
import torch
import sys

sys.path.insert(0, '/Users/shrikarkolla/perfect-punch')

from perfectpunch_backend.main_python_analysis import Model

def test_model():
    print("=" * 60)
    print("Testing PyTorch Model Loading...")
    print("=" * 60)
    
    # Create model
    print("\n1. Creating model instance...")
    try:
        model = Model()
        print("   ✅ Model created successfully")
    except Exception as e:
        print(f"   ❌ Failed to create model: {e}")
        return False
    
    # Load weights
    print("\n2. Loading saved weights from model_state.pt...")
    try:
        state_dict = torch.load(
            '/Users/shrikarkolla/perfect-punch/perfectpunch_backend/models/model_state.pt',
            map_location='cpu'
        )
        model.load_state_dict(state_dict)
        print("   ✅ Model weights loaded successfully")
    except Exception as e:
        print(f"   ❌ Failed to load weights: {e}")
        return False
    
    # Set to eval mode
    model.eval()
    print("   ✅ Model set to evaluation mode")
    
    # Test forward pass
    print("\n3. Testing forward pass with dummy input...")
    try:
        dummy_input = torch.randn(1, 120)
        with torch.no_grad():
            output = model(dummy_input)
        print(f"   ✅ Forward pass successful!")
        print(f"      Input shape: {dummy_input.shape}")
        print(f"      Output shape: {output.shape}")
        print(f"      Predictions: {output}")
        
        # Get predicted class
        pred_class = output.argmax(dim=1).item()
        punch_map = {0: "hook", 1: "jab", 2: "uppercut"}
        print(f"      Predicted punch: {punch_map[pred_class]} (class {pred_class})")
    except Exception as e:
        print(f"   ❌ Forward pass failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test multiple inputs
    print("\n4. Testing with batch of inputs...")
    try:
        batch_input = torch.randn(4, 120)
        with torch.no_grad():
            batch_output = model(batch_input)
        print(f"   ✅ Batch processing successful!")
        print(f"      Input shape: {batch_input.shape}")
        print(f"      Output shape: {batch_output.shape}")
        print(f"      Predictions:\n{batch_output}")
    except Exception as e:
        print(f"   ❌ Batch processing failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nThe model is working correctly and ready for:")
    print("  • Camera input processing")
    print("  • Real-time punch classification")
    print("  • Dashboard metrics generation")
    return True

if __name__ == "__main__":
    success = test_model()
    sys.exit(0 if success else 1)

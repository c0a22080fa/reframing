import sys
import os

# Ensure src is in path
sys.path.append(os.getcwd())

try:
    from src.services.comet_service import CometService
    print("Initializing CometService...")
    service = CometService()
    
    if service.model is None:
        print("[FAILURE] CometService fell back to mock (Model is None).")
    else:
        print("[SUCCESS] COMET Model loaded successfully.")
        
        # Test Inference
        print("Testing inference for 'It is raining (xWant)'...")
        results = service.infer("It is raining", "xWant")
        print(f"Results: {results}")
        
except Exception as e:
    print(f"[CRITICAL FAILURE] {e}")
    import traceback
    traceback.print_exc()

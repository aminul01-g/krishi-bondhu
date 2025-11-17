"""
YOLOv8-based demo inference. Uses ultralytics.YOLO.
This is an integration demo; you should replace with a domain-specific classifier for crop diseases.
"""
import os
import torch

# Try to import ultralytics, but make it optional
try:
    from ultralytics import YOLO
    import numpy as np
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
    print("Warning: ultralytics not installed. Vision features will be disabled.")

# Load model lazily to avoid long startup time during imports
_MODEL = None
_MODEL_ERROR = None

def _get_model():
    global _MODEL, _MODEL_ERROR
    if not ULTRALYTICS_AVAILABLE:
        return None, None
    
    if _MODEL_ERROR:
        return None, _MODEL_ERROR
    
    if _MODEL is None:
        try:
            # Fix for PyTorch 2.6+ weights_only issue
            # Allow ultralytics classes to be loaded
            try:
                from ultralytics.nn.tasks import DetectionModel
                torch.serialization.add_safe_globals([DetectionModel])
            except (ImportError, AttributeError):
                # If add_safe_globals doesn't exist or DetectionModel can't be imported,
                # try to set weights_only=False via environment or monkey patch
                pass
            
            # yolov8n.pt will be auto-downloaded by ultralytics the first time
            _MODEL = YOLO("yolov8n.pt")
        except Exception as e:
            error_msg = str(e)
            _MODEL_ERROR = error_msg
            print(f"Error loading YOLOv8 model: {error_msg}")
            # If it's a weights_only error, try to work around it
            if "weights_only" in error_msg.lower() or "WeightsUnpickler" in error_msg:
                try:
                    # Try to patch torch.load temporarily
                    # torch is already imported at top of file
                    original_load = torch.load
                    def patched_load(*args, **kwargs):
                        kwargs['weights_only'] = False
                        return original_load(*args, **kwargs)
                    # Temporarily replace torch.load
                    torch.load = patched_load
                    _MODEL = YOLO("yolov8n.pt")
                    # Restore original
                    torch.load = original_load
                    _MODEL_ERROR = None
                    print("Successfully loaded YOLOv8 model with workaround")
                except Exception as e2:
                    _MODEL_ERROR = f"Failed to load model even with workaround: {str(e2)}"
                    return None, _MODEL_ERROR
            else:
                return None, _MODEL_ERROR
    
    return _MODEL, None

def run_vision_classifier(image_path: str) -> dict:
    """
    Run detector and map detections to a mock disease label.
    Returns dict: {"disease": str, "confidence": float, "raw_detections": {...}}
    """
    if not ULTRALYTICS_AVAILABLE:
        return {
            "disease": "vision_model_not_available",
            "confidence": 0.0,
            "raw_detections": [],
            "error": "ultralytics not installed"
        }
    
    try:
        model, error = _get_model()
        if model is None:
            error_msg = error or "Model not available"
            return {
                "disease": "error",
                "confidence": 0.0,
                "raw_detections": [],
                "error": error_msg
            }
        
        results = model.predict(source=image_path, imgsz=640, conf=0.25, verbose=False)
        # results is a list of Results for batch input; we ran on a single image
        if len(results) == 0:
            return {"disease": "unknown", "confidence": 0.0, "raw_detections": []}
        res = results[0]
        boxes = []
        for det in res.boxes:
            x1, y1, x2, y2 = det.xyxy[0].tolist()
            conf = float(det.conf[0])
            cls = int(det.cls[0])
            boxes.append({"box": [x1, y1, x2, y2], "confidence": conf, "class": cls})
        # Mock mapping: if any detection exists -> 'pest_or_damage' with average confidence
        if boxes:
            avg_conf = float(np.mean([b["confidence"] for b in boxes]))
            return {
                "disease": "pest_or_damage_detected",
                "confidence": round(avg_conf, 3),
                "raw_detections": boxes
            }
        return {"disease": "no_detection", "confidence": 0.0, "raw_detections": []}
    except Exception as e:
        return {
            "disease": "error",
            "confidence": 0.0,
            "raw_detections": [],
            "error": str(e)
        }

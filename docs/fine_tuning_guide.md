# KrishiBondhu Vision Model Fine-Tuning Roadmap

To achieve state-of-the-art accuracy for detecting crop diseases specific to Bangladesh (like Rice Brown Spot, Jute Stem Rot, or Potato Late Blight), you should fine-tune a pre-trained computer vision model instead of building one from scratch.

Here is the step-by-step roadmap to replace the generic Hugging Face model in `vision_tool.py` with a custom, fine-tuned expert model.

## Step 1: Data Collection & Preparation
You need a labeled dataset. The widely used **PlantVillage** dataset is a great start, but you should ideally collect local field images.
1. Organize your dataset into a standard `ImageFolder` structure:
```text
dataset/
├── train/
│   ├── Rice_Brown_Spot/
│   │   ├── img1.jpg
│   │   └── img2.jpg
│   ├── Rice_Healthy/
│   └── Potato_Late_Blight/
└── test/
    ├── Rice_Brown_Spot/
    └── ...
```

## Step 2: Fine-Tuning using Hugging Face AutoTrain (Recommended)
AutoTrain is the easiest way to fine-tune a Vision Transformer (ViT) locally or on a cloud GPU.
1. Install AutoTrain: `pip install autotrain-advanced`
2. Run the training command on your dataset:
```bash
autotrain image-classification \
  --train \
  --project-name krishi-bondhu-vision \
  --model google/vit-base-patch16-224 \
  --data-path ./dataset \
  --epochs 5 \
  --batch-size 16 \
  --lr 2e-5
```
3. AutoTrain will output a fine-tuned model directory (e.g., `./krishi-bondhu-vision`).

## Step 3: Advanced Fine-Tuning (YOLOv8 for Object Detection)
If you want the model to draw bounding boxes around the diseased leaves rather than just classifying the whole image, you should use **YOLOv8**.
1. Install YOLO: `pip install ultralytics`
2. Train YOLO on your dataset (format must be YOLO format, not ImageFolder):
```bash
yolo task=detect mode=train model=yolov8n.pt data=dataset.yaml epochs=50 imgsz=640
```

## Step 4: Integration with KrishiBondhu
Once your model is trained, update the `backend/app/crew/tools/vision_tool.py` to point to your new local model directory instead of the generic Hugging Face hub model.

**If you used AutoTrain (ViT):**
```python
# In vision_tool.py
classifier = pipeline("image-classification", model="./path/to/krishi-bondhu-vision")
```

**If you used YOLOv8:**
```python
# In vision_tool.py
from ultralytics import YOLO
model = YOLO('./path/to/best.pt')
results = model(image_path)
# Parse the bounding boxes and confidences...
```

By following this roadmap, you can gradually enhance the Plant Pathologist Agent's "eyes" without changing any of the overarching CrewAI logic!

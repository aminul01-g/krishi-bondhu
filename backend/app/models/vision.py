"""
Vision analysis using Google Gemini API.
"""
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
vision_model = genai.GenerativeModel('models/gemini-2.5-flash')

def run_vision_classifier(image_path: str) -> dict:
    """
    Analyze image using Gemini Vision API.
    Returns dict: {"description": str, "disease": str, "crop": str}
    """
    if not os.path.exists(image_path):
        return {"error": "Image file not found"}

    print(f"Analyzing image with Gemini Vision: {image_path}")
    
    try:
        # Prepare the image
        import PIL.Image
        img = PIL.Image.open(image_path)
        
        # Prompt for analysis
        prompt = "Analyze this agricultural image. Identify the crop, any visible diseases or pests, and symptoms. Return valid JSON with keys: 'crop', 'disease', 'symptoms', 'description', 'confidence' (low/medium/high)."
        
        response = vision_model.generate_content([prompt, img])
        
        if not response or not response.text:
             raise Exception("Empty response from Gemini Vision")
             
        # Extract JSON (simplified)
        import json
        text = response.text
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
            
        try:
            result = json.loads(text)
        except:
             # Fallback if not valid JSON
             result = {"description": response.text, "crop": "detected from text", "disease": "refer to description"}
             
        print(f"Vision analysis result: {result}")
        return {
            "disease": result.get("disease", "unknown"),
            "crop": result.get("crop", "unknown"),
            "vision_result": result
        }

    except Exception as e:
        print(f"Vision analysis failed: {e}")
        return {"error": str(e)}
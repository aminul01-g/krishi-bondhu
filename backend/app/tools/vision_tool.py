from langchain.tools import BaseTool
from pydantic import Field
from transformers import pipeline
from PIL import Image
import os
from app.config.model_config import model_registry

class LocalVisionDiseaseTool(BaseTool):
    name: str = "Local Image Disease Analyzer"
    description: str = "Analyzes an image of a crop to detect diseases using a local Hugging Face computer vision model."
    
    # In a production environment, you would load this model once in the factory or app startup.
    # We initialize it here for demonstration.
    def _run(self, image_path: str) -> str:
        if not image_path or image_path.lower() == "none" or not os.path.exists(image_path):
            return "No valid image provided to analyze."
            
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if api_key:
            try:
                import base64
                from groq import Groq
                
                with open(image_path, "rb") as img_file:
                    base64_image = base64.b64encode(img_file.read()).decode("utf-8")
                    
                client = Groq(api_key=api_key)
                completion = client.chat.completions.create(
                    model="llama-3.2-11b-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Analyze this crop image. Identify any visible diseases, pests, or nutrient deficiencies and provide a brief confidence assessment."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    temperature=0.1,
                    max_tokens=256,
                )
                analysis = completion.choices[0].message.content
                return f"Based on Groq Vision API analysis:\n{analysis}\n\nPlease use this data to formulate a farmer-friendly diagnosis and treatment plan."
            except Exception as e:
                print(f"[WARN] Groq Vision API failed: {e}. Falling back to local model.")

        try:
            # Load the dedicated disease vision model from registry
            classifier = model_registry.get_disease_vision_model()
            
            image = Image.open(image_path)
            results = classifier(image)
            
            # Format results
            analysis = "Based on local vision model analysis, here are the top predictions:\n"
            for res in results[:3]:
                analysis += f"- {res['label']} (Confidence: {round(res['score'] * 100, 2)}%)\n"
                
            analysis += "\nPlease use this raw data to formulate a farmer-friendly diagnosis and treatment plan."
            return analysis
        except Exception as e:
            return f"Error analyzing image locally: {str(e)}"

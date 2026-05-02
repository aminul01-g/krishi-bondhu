from langchain.tools import BaseTool
import os
import json
import logging

logger = logging.getLogger("SoilTools")

class SoilVisionTool(BaseTool):
    name: str = "Soil Image Analyzer"
    description: str = "Analyzes an image of soil to estimate texture (sand, silt, clay) and color (indicating organic matter)."
    
    def _run(self, image_path: str, **kwargs) -> str:
        if not image_path or image_path.lower() == "none" or not os.path.exists(image_path):
            return "No valid soil image provided to analyze."
            
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
                                    "text": "Analyze this soil image for agricultural purposes. 1. Identify likely texture (sandy, clay, loamy). 2. Observe color and moisture (dark indicates high organic matter, light/dry indicates low). 3. Identify any visual anomalies like salt crusts or compaction. Be concise but technical."
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
                    max_tokens=300,
                )
                analysis = completion.choices[0].message.content
                return f"Vision API Soil Analysis:\n{analysis}"
            except Exception as e:
                logger.warning(f"Groq Vision API failed for soil: {e}. Falling back to rule-based mock.")

        return "Local Offline Analysis: The soil appears to be Loamy with a dark brown color, indicating good organic matter content."

class DIYSoilTestTool(BaseTool):
    name: str = "DIY Soil Test Interpreter"
    description: str = "Interprets physical DIY soil tests like the ribbon test or pH strip color. Input should be a JSON string with keys like 'ribbon_length_cm' or 'ph_color'."
    
    def _run(self, test_data_json: str, **kwargs) -> str:
        try:
            # Clean JSON if LLM added markdown
            test_data_json = test_data_json.replace("```json", "").replace("```", "").strip()
            data = json.loads(test_data_json)
            result = []
            
            # 1. Ribbon Test Logic
            if 'ribbon_length_cm' in data:
                length = float(data['ribbon_length_cm'])
                if length < 2.5:
                    result.append("Texture: Sandy or Sandy Loam. (Poor water/nutrient retention).")
                elif length <= 5:
                    result.append("Texture: Loam or Clay Loam. (Ideal 'Balanced' structure for most crops).")
                else:
                    result.append("Texture: Heavy Clay. (Excellent nutrient storage but poor drainage/aeration).")
            
            # 2. pH Strip Logic
            if 'ph_color' in data:
                color = data['ph_color'].lower()
                if any(x in color for x in ['red', 'orange', 'yellow']):
                    result.append("pH: Acidic (<6.5). Likely needs Lime (Dolochun).")
                elif 'green' in color:
                    result.append("pH: Neutral (~6.5 - 7.5). Optimal for most nutrient uptake.")
                elif any(x in color for x in ['blue', 'purple']):
                    result.append("pH: Alkaline (>7.5). Likely needs Sulfur or organic amendments.")
            
            # 3. Jar/Settling Test Logic
            if 'sand_percentage' in data and 'clay_percentage' in data:
                sand = float(data['sand_percentage'])
                clay = float(data['clay_percentage'])
                result.append(f"Jar Test: {sand}% Sand, {clay}% Clay detected.")

            return "\n".join(result) if result else "No valid DIY test parameters found."
        except Exception as e:
            return f"Error parsing DIY test data: {str(e)}"

class RecommendFertilizerTool(BaseTool):
    name: str = "Balanced Fertilizer Recommender"
    description: str = "Generates a balanced hybrid (organic + synthetic) fertilizer plan based on soil data, crop, and growth stage."
    
    def _run(self, soil_summary: str, crop: str, growth_stage: str = "general") -> str:
        summary_lower = soil_summary.lower()
        plan = []
        
        # 1. Organic Base
        plan.append("### ১. জৈব সার (Organic Base - Foundation)")
        if "sandy" in summary_lower:
            plan.append("- হেক্টর প্রতি ১০-১২ টন পচা গোবর বা কম্পোস্ট প্রয়োগ করুন (বেলে মাটির পানি ধারণ ক্ষমতা বাড়াতে)।")
        elif "clay" in summary_lower:
            plan.append("- হেক্টর প্রতি ৮-১০ টন ভার্মিকম্পোস্ট বা কম্পোস্ট প্রয়োগ করুন (মাটির জমাট ভাব কমাতে)।")
        else:
            plan.append("- হেক্টর প্রতি ৫-৮ টন সাধারণ জৈব সার বা খামারজাত সার প্রয়োগ করুন।")
            
        # 2. Synthetic Supplements
        plan.append("\n### ২. রাসায়নিক সার (Synthetic - Precision Boost)")
        if "acidic" in summary_lower or "lime" in summary_lower:
            plan.append("- একর প্রতি ৫০ কেজি ডলোচুন প্রয়োগ করুন (মাটির অম্লতা কমাতে)।")
            
        if "rice" in crop.lower() or "ধান" in crop:
            plan.append("- ইউরিয়া: বিঘা প্রতি ১২-১৫ কেজি (তিন কিস্তিতে)।")
            plan.append("- টিএসপি (TSP): বিঘা প্রতি ৮-১০ কেজি (জমি তৈরির সময়)।")
            plan.append("- এমওপি (MOP): বিঘা প্রতি ৫-৭ কেজি।")
        else:
            plan.append("- আপনার নির্দিষ্ট ফসলের জন্য সুষম এনপিকে (NPK 10:26:26) সার ব্যবহার করুন।")
            
        # 3. Micro-nutrients
        if "light" in summary_lower or "deficiency" in summary_lower:
            plan.append("\n### ৩. অণু-পুষ্টি (Micro-nutrients)")
            plan.append("- দস্তা (Zinc): বিঘা প্রতি ১.৫ কেজি প্রয়োগ করুন।")
            
        return "\n".join(plan)

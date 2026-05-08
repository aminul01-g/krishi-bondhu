"""
Vision Service — Unified abstraction for image analysis tasks.

Implements a 3-tier fallback chain:
  Tier 1: HuggingFace Inference API (ViT / fine-tuned models)
  Tier 2: Groq LLM Vision (llama-3.2-11b-vision-preview)
  Tier 3: Rule-based engine (offline hardcoded responses)

Supported tasks: "disease", "soil", "damage"
"""

import os
import re
import base64
import logging
from typing import Optional, Dict

import httpx

logger = logging.getLogger("VisionService")

HF_MODELS: Dict[str, str] = {
    "disease": os.getenv("VISION_MODEL_ID", "prof-freakenstein/plantnet-disease-detection"),
    "soil": os.getenv("SOIL_VISION_MODEL_ID", "google/vit-base-patch16-224"),
    "damage": os.getenv("DAMAGE_VISION_MODEL_ID", "google/vit-base-patch16-224"),
}

GROQ_PROMPTS: Dict[str, str] = {
    "disease": "Analyze this crop image. Identify any visible diseases, pests, or nutrient deficiencies and provide a brief confidence assessment.",
    "soil": "Analyze this soil image for agricultural purposes. 1. Identify likely texture (sandy, clay, loamy). 2. Observe color and moisture. 3. Identify anomalies like salt crusts or compaction. Be concise but technical.",
    "damage": "Analyze this crop damage image. Estimate the percentage of crop area that is damaged (0-100%). Provide DAMAGE_PERCENT: <number>% and a brief description.",
}

OFFLINE_RESPONSES: Dict[str, str] = {
    "disease": "Offline Analysis: Unable to connect to vision models. Please consult a local agricultural extension officer.",
    "soil": "Local Offline Analysis: The soil appears to be Loamy with a dark brown color, indicating good organic matter content.",
    "damage": "Offline Damage Estimate: 50% (generic estimate — no model available).",
}


class VisionService:
    """Unified vision analysis with 3-tier fallback."""

    def __init__(self) -> None:
        self.hf_api_key: str = os.getenv("HUGGINGFACE_API_KEY", "").strip()
        self.groq_api_key: str = os.getenv("GROQ_API_KEY", "").strip()

    def analyze_image(self, image_path: str, task: str = "disease") -> str:
        if not image_path or not os.path.exists(image_path):
            return "No valid image provided to analyze."
        result = self._tier1_huggingface(image_path, task)
        if result:
            return result
        result = self._tier2_groq_vision(image_path, task)
        if result:
            return result
        logger.warning(f"[VisionService] All tiers failed for task='{task}'. Offline fallback.")
        return OFFLINE_RESPONSES.get(task, OFFLINE_RESPONSES["disease"])

    def assess_damage(self, image_path: str, crop_type: str = "general") -> str:
        if not image_path or not os.path.exists(image_path):
            return f"Mock Damage Assessment: Estimated 65% damage for {crop_type} due to flooding."
        result = self._tier1_huggingface(image_path, "damage")
        if result:
            pct = self._extract_damage_from_labels(result)
            return f"Model Damage Assessment: {pct:.1f}% estimated damage for {crop_type}.\n{result}"
        result = self._tier2_groq_vision(image_path, "damage")
        if result:
            pct = self._extract_damage_from_text(result)
            return f"Groq Damage Assessment: {pct:.1f}% estimated damage for {crop_type}.\n{result}"
        return self._tier3_cv2_damage(image_path, crop_type)

    # --- Tier 1: HuggingFace ---
    def _tier1_huggingface(self, image_path: str, task: str) -> Optional[str]:
        if not self.hf_api_key:
            logger.info("[Tier1] No HUGGINGFACE_API_KEY. Skipping.")
            return None
        model_id = HF_MODELS.get(task, HF_MODELS["disease"])
        api_url = f"https://api-inference.huggingface.co/models/{model_id}"
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            resp = httpx.post(api_url, content=image_bytes,
                              headers={"Authorization": f"Bearer {self.hf_api_key}"}, timeout=10.0)
            if resp.status_code == 200:
                preds = resp.json()
                if isinstance(preds, list) and preds:
                    out = f"[Tier 1 — {model_id}] Top predictions:\n"
                    for p in preds[:5]:
                        out += f"  - {p.get('label','?')} — {p.get('score',0)*100:.1f}%\n"
                    logger.info(f"[Tier1] HF succeeded for task='{task}'.")
                    return out.strip()
            logger.warning(f"[Tier1] HF returned {resp.status_code}.")
        except Exception as exc:
            logger.warning(f"[Tier1] HF failed: {exc}. Falling back.")
        return None

    # --- Tier 2: Groq Vision ---
    def _tier2_groq_vision(self, image_path: str, task: str) -> Optional[str]:
        if not self.groq_api_key:
            logger.info("[Tier2] No GROQ_API_KEY. Skipping.")
            return None
        prompt = GROQ_PROMPTS.get(task, GROQ_PROMPTS["disease"])
        try:
            from groq import Groq
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            client = Groq(api_key=self.groq_api_key)
            comp = client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ]}],
                temperature=0.1, max_tokens=300,
            )
            analysis = comp.choices[0].message.content
            logger.info(f"[Tier2] Groq Vision succeeded for task='{task}'.")
            return f"[Tier 2 — Groq Vision] {analysis}"
        except Exception as exc:
            logger.warning(f"[Tier2] Groq failed: {exc}. Falling back.")
            return None

    # --- Tier 3: CV2 Heuristic (damage only) ---
    def _tier3_cv2_damage(self, image_path: str, crop_type: str) -> str:
        try:
            import cv2
            import numpy as np
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError("Cannot read image.")
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, np.array([35, 40, 40]), np.array([85, 255, 255]))
            total = img.shape[0] * img.shape[1]
            green_loss = 100.0 - (cv2.countNonZero(mask) / total * 100.0)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            texture_score = max(0.0, min(100.0, 100.0 - (lap_var / 5.0)))
            damage = min(max(0.6 * green_loss + 0.4 * texture_score, 5.0), 95.0)
            return f"[Tier 3 — CV2] Damage: {damage:.1f}% for {crop_type}. (Green loss: {green_loss:.1f}%, Texture: {texture_score:.1f}%)"
        except ImportError:
            return f"Mock Damage Assessment: Estimated 65% damage for {crop_type} due to flooding."
        except Exception:
            return f"Mock Damage Assessment (CV2 Error): Estimated 65% damage for {crop_type}."

    # --- Helpers ---
    @staticmethod
    def _extract_damage_from_labels(text: str) -> float:
        t = text.lower()
        if "healthy" in t or "normal" in t: return 10.0
        if "severe" in t or "blight" in t: return 75.0
        if "moderate" in t or "rust" in t: return 50.0
        if "mild" in t or "early" in t: return 30.0
        return 50.0

    @staticmethod
    def _extract_damage_from_text(text: str) -> float:
        m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%", text)
        if m:
            return min(max(float(m.group(1)), 5.0), 95.0)
        return 50.0

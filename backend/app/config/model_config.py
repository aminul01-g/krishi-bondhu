import os
import logging
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig
from langchain_huggingface import HuggingFacePipeline

logger = logging.getLogger("ModelConfig")

class ModelRegistry:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 4-bit Quantization Config for heavy LLMs (requires bitsandbytes)
        self.bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )
        
        # Model IDs
        self.MODELS = {
            "agronomist": {
                "primary": "AI71ai/Llama-agrillm-3.3-70B",
                "fallback": "FN-LLM-2B"
            },
            "disease_vision": {
                "primary": "prof-freakenstein/plantnet-disease-detection",
                "fallback": "wambugu71/crop_leaf_diseases_vit"
            },
            "multimodal_interpreter": {
                "primary": "md-nishat-008/TigerLLM-1B-it",
                "fallback": "BanglaLLM/BanglaLLama-3.2-3b-unlop-culturax-base-v0.0.3"
            },
            "voice_stt": {
                "primary": "mozilla-ai/whisper-large-v3-bn",
                "fallback": "shhossain/whisper-tiny-bn"
            }
        }
        
        # Cache for loaded models to avoid OOM
        self._loaded_models = {}

    def get_agronomist_llm(self):
        """Loads the Agronomist LLM wrapped as a LangChain LLM for CrewAI."""
        model_id = self.MODELS["agronomist"]["primary"]
        fallback_id = self.MODELS["agronomist"]["fallback"]
        
        if "agronomist" in self._loaded_models:
            return self._loaded_models["agronomist"]
            
        try:
            logger.info(f"Attempting to load {model_id} with 4-bit quantization...")
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForCausalLM.from_pretrained(
                model_id, 
                quantization_config=self.bnb_config,
                device_map="auto"
            )
        except Exception as e:
            logger.warning(f"Failed to load {model_id}: {e}. Falling back to {fallback_id}")
            tokenizer = AutoTokenizer.from_pretrained(fallback_id)
            model = AutoModelForCausalLM.from_pretrained(
                fallback_id, 
                device_map="auto",
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
            )
            
        pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=512)
        llm = HuggingFacePipeline(pipeline=pipe)
        self._loaded_models["agronomist"] = llm
        return llm

    def get_disease_vision_model(self):
        """Loads the PlantNet disease classification pipeline."""
        model_id = self.MODELS["disease_vision"]["primary"]
        
        if "disease_vision" in self._loaded_models:
            return self._loaded_models["disease_vision"]
            
        logger.info(f"Loading vision model: {model_id}")
        # Use fallback if primary fails
        try:
            pipe = pipeline("image-classification", model=model_id, device=0 if self.device == "cuda" else -1)
        except Exception as e:
            logger.warning(f"Failed to load {model_id}: {e}. Loading fallback.")
            pipe = pipeline("image-classification", model=self.MODELS["disease_vision"]["fallback"], device=0 if self.device == "cuda" else -1)
            
        self._loaded_models["disease_vision"] = pipe
        return pipe

    def get_interpreter_llm(self):
        """Loads TigerLLM for Bengali NLP."""
        model_id = self.MODELS["multimodal_interpreter"]["primary"]
        
        if "interpreter" in self._loaded_models:
            return self._loaded_models["interpreter"]
            
        logger.info(f"Loading interpreter model: {model_id}")
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(
            model_id, 
            device_map="auto",
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
        )
        pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=256)
        llm = HuggingFacePipeline(pipeline=pipe)
        self._loaded_models["interpreter"] = llm
        return llm

    def get_stt_model(self):
        """Loads Whisper ASR for Bengali."""
        model_id = self.MODELS["voice_stt"]["primary"]
        
        if "stt" in self._loaded_models:
            return self._loaded_models["stt"]
            
        logger.info(f"Loading STT model: {model_id}")
        try:
            pipe = pipeline("automatic-speech-recognition", model=model_id, device=0 if self.device == "cuda" else -1)
        except Exception:
            fallback_id = self.MODELS["voice_stt"]["fallback"]
            logger.warning(f"Failed to load Whisper Large. Falling back to {fallback_id}")
            pipe = pipeline("automatic-speech-recognition", model=fallback_id, device=0 if self.device == "cuda" else -1)
            
        self._loaded_models["stt"] = pipe
        return pipe

model_registry = ModelRegistry()

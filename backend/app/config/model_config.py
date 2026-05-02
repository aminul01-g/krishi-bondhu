import os
import logging
# import torch  # Temporarily commented out
# from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig  # Lazy import
# from langchain_community.llms.huggingface_pipeline import HuggingFacePipeline  # Lazy import
# from langchain_groq import ChatGroq  # Lazy import

logger = logging.getLogger("ModelConfig")

class ModelRegistry:
    def __init__(self):
        # Lazy imports to avoid circular dependencies
        # self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # self.is_basic_space = os.getenv("SPACE_HARDWARE", "").startswith("cpu") or not torch.cuda.is_available()
        
        # 4-bit Quantization Config for heavy LLMs (requires bitsandbytes)
        # self.bnb_config = BitsAndBytesConfig(
        #     load_in_4bit=True,
        #     bnb_4bit_compute_dtype=torch.float16,
        #     bnb_4bit_use_double_quant=True,
        #     bnb_4bit_quant_type="nf4"
        # )
        
        # Model IDs mapped to environment variables with hardcoded defaults
        self.MODELS = {
            "agronomist": {
                "primary": os.getenv("PRIMARY_LLM_ID", "AI71ai/Llama-agrillm-3.3-70B"),
                "fallback": os.getenv("FALLBACK_LLM_ID", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
            },
            "disease_vision": {
                "primary": os.getenv("VISION_MODEL_ID", "prof-freakenstein/plantnet-disease-detection"),
                "fallback": "wambugu71/crop_leaf_diseases_vit"
            },
            "multimodal_interpreter": {
                "primary": os.getenv("INTERPRETER_LLM_ID", "md-nishat-008/TigerLLM-1B-it"),
                "fallback": "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
            },
            "voice_stt": {
                "primary": os.getenv("STT_MODEL_ID", "mozilla-ai/whisper-large-v3-bn"),
                "fallback": "shhossain/whisper-tiny-bn"
            }
        }
        
        # Cache for loaded models to avoid OOM
        self._loaded_models = {}

    def get_agronomist_llm(self):
        """Loads the Agronomist LLM wrapped as a LangChain LLM for CrewAI."""
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if api_key:
            os.environ["GROQ_API_KEY"] = api_key
            logger.info("GROQ_API_KEY detected. Loading ChatGroq for blazing fast inference.")
            if "agronomist" not in self._loaded_models:
                try:
                    from langchain_groq import ChatGroq  # Lazy import
                    self._loaded_models["agronomist"] = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.7)
                except Exception as e:
                    logger.warning(f"Failed to load ChatGroq: {e}")
                    return None
            return self._loaded_models["agronomist"]

        model_id = self.MODELS["agronomist"]["primary"]
        fallback_id = self.MODELS["agronomist"]["fallback"]
        
        # Hardware awareness: Prevent 70B models from crashing CPU spaces
        if self.is_basic_space and ("70B" in model_id or "70b" in model_id.lower()):
            logger.warning(f"Hardware limitation detected. Forcing fallback from {model_id} to {fallback_id} to prevent disk/OOM crash.")
            model_id = fallback_id

        if "agronomist" in self._loaded_models:
            return self._loaded_models["agronomist"]
            
        try:
            logger.info(f"Attempting to load {model_id}...")
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            # Only use quantization if CUDA is available, otherwise bitsandbytes will crash
            if self.device == "cuda":
                model = AutoModelForCausalLM.from_pretrained(model_id, quantization_config=self.bnb_config, device_map="auto")
            else:
                model = AutoModelForCausalLM.from_pretrained(model_id, device_map="cpu", torch_dtype=torch.float32)
        except Exception as e:
            logger.warning(f"Failed to load {model_id}: {e}. Falling back to {fallback_id}")
            tokenizer = AutoTokenizer.from_pretrained(fallback_id)
            model = AutoModelForCausalLM.from_pretrained(
                fallback_id, 
                device_map="cpu" if self.device == "cpu" else "auto",
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
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if api_key:
            os.environ["GROQ_API_KEY"] = api_key
            logger.info("GROQ_API_KEY detected. Loading ChatGroq for interpreter.")
            if "interpreter" not in self._loaded_models:
                try:
                    from langchain_groq import ChatGroq  # Lazy import
                    self._loaded_models["interpreter"] = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0.1)
                except Exception as e:
                    logger.warning(f"Failed to load ChatGroq: {e}")
                    return None
            return self._loaded_models["interpreter"]

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
        fallback_id = self.MODELS["voice_stt"]["fallback"]
        
        if self.is_basic_space and "large" in model_id.lower():
            logger.warning(f"Hardware limitation detected. Forcing fallback from {model_id} to {fallback_id} to prevent disk/OOM crash.")
            model_id = fallback_id
            
        if "stt" in self._loaded_models:
            return self._loaded_models["stt"]
            
        logger.info(f"Loading STT model: {model_id}")
        try:
            pipe = pipeline("automatic-speech-recognition", model=model_id, device=0 if self.device == "cuda" else -1)
        except Exception:
            logger.warning(f"Failed to load {model_id}. Falling back to {fallback_id}")
            pipe = pipeline("automatic-speech-recognition", model=fallback_id, device=0 if self.device == "cuda" else -1)
            
        self._loaded_models["stt"] = pipe
        return pipe

model_registry = ModelRegistry()

"""
LLM Provider Abstraction Layer

Supports multiple LLM providers with a unified interface:
- Gemini (Google)
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Cohere

Switch providers by changing LLM_PROVIDER in .env file
"""

import os
from typing import Optional, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


def _get_hf_token() -> str | None:
    return (
        os.getenv("HUGGINGFACEHUB_API_TOKEN")
        or os.getenv("HUGGINGFACE_API_KEY")
        or os.getenv("HF_TOKEN")
    )


class LLMProvider(str, Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    GROQ = "groq"
    HUGGINGFACE = "huggingface"
    FALLBACK = "fallback"


class LLMConfig:
    """Configuration for LLM providers"""
    
    def __init__(self):
        provider = os.getenv("LLM_PROVIDER", "").lower()
        if provider:
            self.provider = provider
        elif os.getenv("GROQ_API_KEY"):
            self.provider = LLMProvider.GROQ
        elif _get_hf_token():
            self.provider = LLMProvider.HUGGINGFACE
        elif os.getenv("GEMINI_API_KEY"):
            self.provider = LLMProvider.GEMINI
        elif os.getenv("OPENAI_API_KEY"):
            self.provider = LLMProvider.OPENAI
        elif os.getenv("ANTHROPIC_API_KEY"):
            self.provider = LLMProvider.ANTHROPIC
        elif os.getenv("COHERE_API_KEY"):
            self.provider = LLMProvider.COHERE
        else:
            self.provider = LLMProvider.FALLBACK
        
        if self.provider not in [p.value for p in LLMProvider]:
            raise ValueError(f"Unknown LLM provider: {self.provider}")
        
        logger.info(f"LLM Provider: {self.provider}")
        
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.hf_token = _get_hf_token()
        self.hf_model = os.getenv("HUGGINGFACE_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
        self.openai_org_id = os.getenv("OPENAI_ORG_ID", "")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
        self.cohere_api_key = os.getenv("COHERE_API_KEY")
        self.cohere_model = os.getenv("COHERE_MODEL", "command-r-plus")

        try:
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            self.device = "cpu"

        self.is_basic_space = os.getenv("SPACE_HARDWARE", "").startswith("cpu") or self.device != "cuda"
        self.stt_model_id = os.getenv("STT_MODEL_ID", "mozilla-ai/whisper-large-v3-bn")
        self.stt_fallback_model_id = os.getenv("STT_FALLBACK_MODEL_ID", "openai/whisper-large-v2")
        self.huggingface_speech_model = os.getenv("HUGGINGFACE_SPEECH_MODEL", "openai/whisper-large-v2")
        
        if self.provider == LLMProvider.GEMINI and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not set in .env")
        if self.provider == LLMProvider.OPENAI and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in .env")
        if self.provider == LLMProvider.ANTHROPIC and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in .env")
        if self.provider == LLMProvider.COHERE and not self.cohere_api_key:
            raise ValueError("COHERE_API_KEY not set in .env")
        if self.provider == LLMProvider.GROQ and not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not set in .env")
        if self.provider == LLMProvider.HUGGINGFACE and not self.hf_token:
            raise ValueError("Hugging Face token not set in .env")
        
        # STT and TTS configs (provider-agnostic)
        self.stt_provider = os.getenv("STT_PROVIDER", "gemini")
        self.tts_provider = os.getenv("TTS_PROVIDER", "gtts")
        self.max_retries = int(os.getenv("MAX_RETRIES", 3))
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", 30))
        self.debug = os.getenv("DEBUG", "false").lower() == "true"


# Singleton config instance
_config: Optional[LLMConfig] = None


def get_llm_config() -> LLMConfig:
    """Get or create LLM configuration singleton"""
    global _config
    if _config is None:
        _config = LLMConfig()
    return _config


class BaseLLMProvider:
    """Abstract base class for LLM providers"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    def generate_content(self, prompt: str, system_instruction: str = None) -> str:
        """Generate content using the LLM"""
        raise NotImplementedError
    
    def get_model_name(self) -> str:
        """Get the name of the model being used"""
        raise NotImplementedError


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            import google.generativeai as genai
            genai.configure(api_key=config.gemini_api_key)
            self.client = genai
            self.model = config.gemini_model
        except ImportError:
            raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")
    
    def generate_content(self, prompt: str, system_instruction: str = None) -> str:
        """Generate content using Gemini"""
        try:
            if system_instruction:
                final_prompt = f"{system_instruction}\n\n{prompt}"
            else:
                final_prompt = prompt
            
            response = self.client.GenerativeModel(self.model).generate_content(final_prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            raise
    
    def get_model_name(self) -> str:
        return self.model


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=config.openai_api_key,
                organization=config.openai_org_id if config.openai_org_id else None
            )
            self.model = config.openai_model
        except ImportError:
            raise ImportError("openai not installed. Run: pip install openai")
    
    def generate_content(self, prompt: str, system_instruction: str = None) -> str:
        """Generate content using OpenAI"""
        try:
            messages = []
            
            if system_instruction:
                messages.append({
                    "role": "system",
                    "content": system_instruction
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            raise
    
    def get_model_name(self) -> str:
        return self.model


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=config.anthropic_api_key)
            self.model = config.anthropic_model
        except ImportError:
            raise ImportError("anthropic not installed. Run: pip install anthropic")
    
    def generate_content(self, prompt: str, system_instruction: str = None) -> str:
        """Generate content using Claude"""
        try:
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"{system_instruction}\n\n{prompt}"
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ]
            )
            
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            raise
    
    def get_model_name(self) -> str:
        return self.model


class CohereProvider(BaseLLMProvider):
    """Cohere provider"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            import cohere
            self.client = cohere.ClientV2(api_key=config.cohere_api_key)
            self.model = config.cohere_model
        except ImportError:
            raise ImportError("cohere not installed. Run: pip install cohere")
    
    def generate_content(self, prompt: str, system_instruction: str = None) -> str:
        """Generate content using Cohere"""
        try:
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"{system_instruction}\n\n{prompt}"
            
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ]
            )
            
            return response.message.content[0].text
        except Exception as e:
            logger.error(f"Cohere error: {e}")
            raise
    
    def get_model_name(self) -> str:
        return self.model


class GroqProvider(BaseLLMProvider):
    """Groq provider"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            from langchain_groq import ChatGroq
            self.model = config.groq_model
            self.client = ChatGroq(
                groq_api_key=config.groq_api_key,
                model_name=self.model,
                temperature=0.7,
            )
        except ImportError:
            raise ImportError("langchain-groq not installed. Run: pip install langchain-groq")

    def generate_content(self, prompt: str, system_instruction: str = None) -> str:
        try:
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"{system_instruction}\n\n{prompt}"

            if hasattr(self.client, "predict"):
                return self.client.predict(full_prompt)
            if hasattr(self.client, "call"):
                return self.client.call(full_prompt)
            return self.client(full_prompt)
        except Exception as e:
            logger.error(f"Groq error: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model


class HuggingFaceProvider(BaseLLMProvider):
    """Hugging Face provider using the inference endpoint"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            from langchain_huggingface import HuggingFaceEndpoint
            self.model = config.hf_model
            self.client = HuggingFaceEndpoint(
                repo_id=self.model,
                huggingfacehub_api_token=config.hf_token,
                temperature=0.7,
                max_new_tokens=512,
            )
        except ImportError:
            raise ImportError("langchain-huggingface not installed. Run: pip install langchain-huggingface")

    def generate_content(self, prompt: str, system_instruction: str = None) -> str:
        try:
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"{system_instruction}\n\n{prompt}"
            return self.client(full_prompt)
        except Exception as e:
            logger.error(f"HuggingFace error: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model


class FallbackProvider(BaseLLMProvider):
    """Fallback provider when no external model is configured."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.model = "fallback"

    def generate_content(self, prompt: str, system_instruction: str = None) -> str:
        return (
            "LLM provider is not configured. "
            "Please set HUGGINGFACE_API_KEY or HUGGINGFACEHUB_API_TOKEN, "
            "GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, or COHERE_API_KEY in the environment."
        )

    def get_model_name(self) -> str:
        return self.model


def get_llm_provider() -> BaseLLMProvider:
    """Factory function to get the appropriate LLM provider"""
    config = get_llm_config()
    
    if config.provider == LLMProvider.GEMINI:
        return GeminiProvider(config)
    elif config.provider == LLMProvider.OPENAI:
        return OpenAIProvider(config)
    elif config.provider == LLMProvider.ANTHROPIC:
        return AnthropicProvider(config)
    elif config.provider == LLMProvider.COHERE:
        return CohereProvider(config)
    elif config.provider == LLMProvider.GROQ:
        return GroqProvider(config)
    elif config.provider == LLMProvider.HUGGINGFACE:
        return HuggingFaceProvider(config)
    elif config.provider == LLMProvider.FALLBACK:
        return FallbackProvider(config)
    else:
        raise ValueError(f"Unknown LLM provider: {config.provider}")


# Global provider instance (lazy-loaded)
_provider: Optional[BaseLLMProvider] = None
_stt_pipeline: Optional[Any] = None


def _load_local_stt_pipeline() -> Any:
    config = get_llm_config()
    try:
        from transformers import pipeline
    except ImportError as exc:
        raise ImportError("transformers is required for local STT support. Install with `pip install transformers`.") from exc

    model_id = config.stt_model_id
    fallback_id = config.stt_fallback_model_id
    if config.is_basic_space and "large" in model_id.lower():
        logger.warning(
            "Hardware constraints detected: forcing STT fallback from %s to %s.", model_id, fallback_id
        )
        model_id = fallback_id

    device = 0 if config.device == "cuda" else -1
    try:
        return pipeline("automatic-speech-recognition", model=model_id, device=device)
    except Exception as exc:
        logger.warning("Failed to load STT model %s: %s. Falling back to %s.", model_id, exc, fallback_id)
        return pipeline("automatic-speech-recognition", model=fallback_id, device=device)


def init_stt_pipeline() -> Any:
    global _stt_pipeline
    if _stt_pipeline is None:
        _stt_pipeline = _load_local_stt_pipeline()
        logger.info("Local STT pipeline initialized.")
    return _stt_pipeline


def init_llm_provider() -> BaseLLMProvider:
    """Initialize and return LLM provider"""
    global _provider
    if _provider is None:
        _provider = get_llm_provider()
        logger.info(f"LLM Provider initialized: {_provider.get_model_name()}")
    return _provider
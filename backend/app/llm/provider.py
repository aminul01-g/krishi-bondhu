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


class LLMProvider(str, Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"


class LLMConfig:
    """Configuration for LLM providers"""
    
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        
        # Validate provider
        if self.provider not in [p.value for p in LLMProvider]:
            raise ValueError(f"Unknown LLM provider: {self.provider}")
        
        logger.info(f"LLM Provider: {self.provider}")
        
        # Load provider-specific configs
        if self.provider == LLMProvider.GEMINI:
            self.gemini_api_key = os.getenv("GEMINI_API_KEY")
            self.gemini_model = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")
            if not self.gemini_api_key:
                raise ValueError("GEMINI_API_KEY not set in .env")
        
        elif self.provider == LLMProvider.OPENAI:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
            self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
            self.openai_org_id = os.getenv("OPENAI_ORG_ID", "")
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set in .env")
        
        elif self.provider == LLMProvider.ANTHROPIC:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
            self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not set in .env")
        
        elif self.provider == LLMProvider.COHERE:
            self.cohere_api_key = os.getenv("COHERE_API_KEY")
            self.cohere_model = os.getenv("COHERE_MODEL", "command-r-plus")
            if not self.cohere_api_key:
                raise ValueError("COHERE_API_KEY not set in .env")
        
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
    else:
        raise ValueError(f"Unknown LLM provider: {config.provider}")


# Global provider instance (lazy-loaded)
_provider: Optional[BaseLLMProvider] = None


def init_llm_provider() -> BaseLLMProvider:
    """Initialize and return LLM provider"""
    global _provider
    if _provider is None:
        _provider = get_llm_provider()
        logger.info(f"LLM Provider initialized: {_provider.get_model_name()}")
    return _provider

import os
import logging

from app.config.agent_llm import DEFAULT_HF_MODEL

logger = logging.getLogger(__name__)

_hf_token_warned = False


def get_llm():
    """
    Factory function to return the configured LLM based on environment variables.
    Defaults to Groq if GROQ_API_KEY is present, then HuggingFace, then Gemini.
    Falls back gracefully when tokens/packages are missing.
    """
    global _hf_token_warned
    provider = os.getenv("LLM_PROVIDER", "").lower()

    if provider == "groq" or (not provider and os.getenv("GROQ_API_KEY")):
        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key:
            try:
                from langchain_groq import ChatGroq

                return ChatGroq(
                    groq_api_key=groq_api_key,
                    model_name=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                    temperature=0.7,
                )
            except Exception as e:
                logger.warning(f"Groq LLM init failed: {e}. Falling back.")

    if provider == "huggingface" or (not provider and (os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN"))):
        hf_api_key = (
            os.getenv("HUGGINGFACEHUB_API_TOKEN")
            or os.getenv("HUGGINGFACE_API_KEY")
            or os.getenv("HF_TOKEN")
        )
        if not hf_api_key:
            if not _hf_token_warned:
                logger.warning(
                    "HuggingFace provider selected but no token found "
                    "(HF_TOKEN / HUGGINGFACEHUB_API_TOKEN / HUGGINGFACE_API_KEY). "
                    "Falling back to Gemini."
                )
                _hf_token_warned = True
            # Fall through to Gemini below
        else:
            hf_model = os.getenv("HUGGINGFACE_MODEL", DEFAULT_HF_MODEL)
            try:
                from langchain_huggingface import HuggingFaceEndpoint

                return HuggingFaceEndpoint(
                    repo_id=hf_model,
                    huggingfacehub_api_token=hf_api_key,
                    temperature=0.7,
                    max_new_tokens=512,
                )
            except Exception as e:
                logger.warning(f"HuggingFace LLM init failed: {e}. Falling back.")

    # Default / fallback to Gemini
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                google_api_key=gemini_api_key,
                temperature=0.7,
            )
        except Exception as e:
            logger.warning(f"Gemini LLM init failed: {e}")

    raise ValueError(
        "No LLM provider could be initialized. "
        "Set GROQ_API_KEY, GEMINI_API_KEY, or HF_TOKEN in the environment."
    )


import os
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default HuggingFace model — MUST be open-access (no gating).
#
# mistralai/Mistral-7B-Instruct-v0.3 supports text-generation.
# Override at runtime via the HUGGINGFACE_MODEL env var.
# ---------------------------------------------------------------------------
DEFAULT_HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="groq")
warnings.filterwarnings("ignore", category=FutureWarning, module="huggingface_hub")


class FallbackLLM:
    """Fallback LLM used when no external provider is configured."""

    model: str = "fallback"
    provider: str = "fallback"
    temperature: float | None = 0.0
    api_key: str | None = None

    def call(
        self,
        messages: str | list[Any],
        tools: list[dict[str, Any]] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
        response_model: type[Any] | None = None,
    ) -> str:
        return (
            "LLM provider is not configured. "
            "Please set HUGGINGFACE_API_KEY or HUGGINGFACEHUB_API_TOKEN, "
            "GEMINI_API_KEY, or OPENAI_API_KEY in the environment."
        )

    async def acall(
        self,
        messages: str | list[Any],
        tools: list[dict[str, Any]] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
        response_model: type[Any] | None = None,
    ) -> str:
        return self.call(
            messages,
            tools=tools,
            callbacks=callbacks,
            available_functions=available_functions,
            from_task=from_task,
            from_agent=from_agent,
            response_model=response_model,
        )


def _get_hf_token() -> str | None:
    return (
        os.getenv("HUGGINGFACEHUB_API_TOKEN")
        or os.getenv("HUGGINGFACE_API_KEY")
        or os.getenv("HF_TOKEN")
    )


# Track warnings so we only log once per provider failure.
_warned: set[str] = set()

# Singleton LLM instance to avoid repeated initializations and HF token warnings.
_cached_llm: Any = None


def get_agent_llm(model_name: str | None = None):
    """Return the best available LLM for CrewAI agents.

    Resolution order:
      1. Groq (if GROQ_API_KEY present)
      2. HuggingFace (if token present)
      3. Gemini
      4. OpenAI
      5. FallbackLLM (offline placeholder)

    The result is cached as a singleton so all agents share the same
    LLM instance, avoiding repeated initialisations.

    Args:
        model_name: Optional HuggingFace model repo ID. Falls back to
                    ``HUGGINGFACE_MODEL`` env var, then ``DEFAULT_HF_MODEL``.
    """
    global _cached_llm
    if _cached_llm is not None:
        return _cached_llm

    model_name = model_name or os.getenv("HUGGINGFACE_MODEL", DEFAULT_HF_MODEL)
    hf_token = _get_hf_token()

    # --- 1. Groq ----------------------------------------------------------
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from langchain_groq import ChatGroq

            model_name = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
            llm = ChatGroq(
                groq_api_key=groq_key,
                model_name=model_name,
                temperature=0.7,
            )
            logger.info("Agent LLM initialised: Groq (%s)", model_name)
            _cached_llm = llm
            return llm
        except Exception as e:
            if "groq" not in _warned:
                logger.warning("Groq LLM init failed: %s", e)
                _warned.add("groq")

    # --- 2. HuggingFace ---------------------------------------------------
    if hf_token:
        try:
            from langchain_huggingface import HuggingFaceEndpoint

            llm = HuggingFaceEndpoint(
                repo_id=model_name,
                huggingfacehub_api_token=hf_token,
                temperature=0.7,
                max_new_tokens=512,
            )
            logger.info("Agent LLM initialised: HuggingFace (%s)", model_name)
            _cached_llm = llm
            return llm
        except Exception as e:
            err_str = str(e)
            # Detect gated-model error specifically
            if "gated repo" in err_str.lower() or "restricted" in err_str.lower():
                if "hf_gated" not in _warned:
                    logger.warning(
                        "Model '%s' is gated/restricted. "
                        "Switch to an open model (e.g. %s) via HUGGINGFACE_MODEL "
                        "or request access on huggingface.co.  Falling back.",
                        model_name,
                        DEFAULT_HF_MODEL,
                    )
                    _warned.add("hf_gated")
            else:
                if "hf_init" not in _warned:
                    logger.warning("HuggingFace LLM init failed: %s", e)
                    _warned.add("hf_init")

    # --- 3. Gemini --------------------------------------------------------
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                google_api_key=gemini_key,
                temperature=0.7,
            )
            logger.info("Agent LLM initialised: Gemini")
            _cached_llm = llm
            return llm
        except Exception as e:
            if "gemini" not in _warned:
                logger.warning("Gemini LLM init failed: %s", e)
                _warned.add("gemini")

    # --- 4. OpenAI --------------------------------------------------------
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(openai_api_key=openai_key, temperature=0.7)
            logger.info("Agent LLM initialised: OpenAI")
            _cached_llm = llm
            return llm
        except Exception as e:
            if "openai" not in _warned:
                logger.warning("OpenAI LLM init failed: %s", e)
                _warned.add("openai")

    # --- 5. Fallback (no external provider) --------------------------------
    if "fallback" not in _warned:
        logger.warning(
            "No LLM provider available — agents will use FallbackLLM "
            "(static responses). Set GROQ_API_KEY, HF_TOKEN, GEMINI_API_KEY, or "
            "OPENAI_API_KEY in the environment."
        )
        _warned.add("fallback")
    _cached_llm = FallbackLLM()
    return _cached_llm


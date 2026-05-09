import os
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default HuggingFace model — MUST be open-access (no gating).
#
# microsoft/Phi-3-mini-4k-instruct  –  3.8B params, instruction-tuned,
# Apache-2.0 license, no access request needed.
# Override at runtime via the HUGGINGFACE_MODEL env var.
# ---------------------------------------------------------------------------
DEFAULT_HF_MODEL = "microsoft/Phi-3-mini-4k-instruct"


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


def get_agent_llm(model_name: str | None = None):
    """Return the best available LLM for CrewAI agents.

    Resolution order:
      1. HuggingFace (if token present)
      2. Gemini
      3. OpenAI
      4. FallbackLLM (offline placeholder)

    Args:
        model_name: Optional HuggingFace model repo ID. Falls back to
                    ``HUGGINGFACE_MODEL`` env var, then ``DEFAULT_HF_MODEL``.
    """
    model_name = model_name or os.getenv("HUGGINGFACE_MODEL", DEFAULT_HF_MODEL)
    hf_token = _get_hf_token()

    # --- 1. HuggingFace ---------------------------------------------------
    if hf_token:
        try:
            from langchain_huggingface import HuggingFaceEndpoint

            llm = HuggingFaceEndpoint(
                repo_id=model_name,
                huggingfacehub_api_token=hf_token,
                temperature=0.7,
                model_kwargs={"max_length": 512},
            )
            logger.info("Agent LLM initialised: HuggingFace (%s)", model_name)
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

    # --- 2. Gemini --------------------------------------------------------
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
            return llm
        except Exception as e:
            if "gemini" not in _warned:
                logger.warning("Gemini LLM init failed: %s", e)
                _warned.add("gemini")

    # --- 3. OpenAI --------------------------------------------------------
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(openai_api_key=openai_key, temperature=0.7)
            logger.info("Agent LLM initialised: OpenAI")
            return llm
        except Exception as e:
            if "openai" not in _warned:
                logger.warning("OpenAI LLM init failed: %s", e)
                _warned.add("openai")

    # --- 4. Fallback (no external provider) --------------------------------
    if "fallback" not in _warned:
        logger.warning(
            "No LLM provider available — agents will use FallbackLLM "
            "(static responses). Set GEMINI_API_KEY, HF_TOKEN, or "
            "OPENAI_API_KEY in the environment."
        )
        _warned.add("fallback")
    return FallbackLLM()


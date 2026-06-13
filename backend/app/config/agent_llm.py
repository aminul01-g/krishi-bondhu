import inspect
import os
import logging
from typing import Any

from app.llm import init_llm_provider

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
            "GEMINI_API_KEY, ANTHROPIC_API_KEY, COHERE_API_KEY, or OPENAI_API_KEY in the environment."
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


class AgentLLMAdapter:
    """Adapter around a shared LLM provider to expose call/acall semantics."""

    def __init__(self, provider: Any, model_name: str | None = None):
        self.provider = provider
        self.model = getattr(provider, "model", model_name or "unknown")
        self.provider_name = getattr(provider, "provider", getattr(provider, "__class__", type(provider).__name__))

    def _messages_to_prompt(self, messages: str | list[Any]) -> str:
        if isinstance(messages, str):
            return messages
        if isinstance(messages, dict):
            # If a dict-like initial_state is passed, stringify but keep language if present
            return str(messages)

        prompt_parts = []
        # Detect explicit language in messages (some callers pass a state dict or include language)
        detected_language = None
        has_system = False
        for message in messages:
            if isinstance(message, dict):
                if message.get("role") == "system":
                    has_system = True
                if detected_language is None and "language" in message:
                    detected_language = message.get("language")
        for message in messages:
            if not isinstance(message, dict):
                prompt_parts.append(str(message))
                continue
            role = message.get("role", "user")
            content = message.get("content", "")
            prompt_parts.append(f"{role.title()}: {content}")

        prompt_body = "\n".join(prompt_parts)

        # If no explicit system instruction exists but a language was detected, prepend one
        if not has_system and detected_language in ("bn", "en"):
            if detected_language == "bn":
                system_inst = "System: সব উত্তর বাংলায় প্রদান করুন। কৃষক-বান্ধব, সংক্ষিপ্ত ভাষা ব্যবহার করুন।"
            else:
                system_inst = "System: Always reply in English. Use concise, farmer-friendly language."
            prompt = system_inst + "\n\n" + prompt_body
        else:
            prompt = prompt_body

        return self._truncate_prompt(prompt)

    def _truncate_prompt(self, prompt: str, max_chars: int = 20000) -> str:
        if len(prompt) <= max_chars:
            return prompt
        # Preserve a leading system instruction (everything up to first blank line) when truncating
        header = ""
        body = prompt
        if prompt.startswith("System:") and "\n\n" in prompt:
            parts = prompt.split("\n\n", 1)
            header = parts[0] + "\n\n"
            body = parts[1]

        # If header itself already exceeds the limit, fall back to character-based truncation
        if len(header) >= max_chars:
            logger.warning("System instruction alone exceeds max_chars; truncating header.")
            return prompt[:max_chars]

        allowed = max_chars - len(header)
        truncated_body = body[-allowed:]
        if "\n" in truncated_body:
            truncated_body = truncated_body[truncated_body.index("\n") + 1 :]

        logger.warning(
            "Conversation prompt exceeded %d chars and was truncated to %d chars (preserving system header).",
            max_chars,
            len(header) + len(truncated_body),
        )

        return (
            header
            + "NOTE: The conversation was truncated to fit the model's request limits. Only the latest context is included.\n\n"
            + truncated_body
        )

    def _generate(self, prompt: str) -> str:
        # Try a direct provider call first. If we hit a rate / token limit
        # error, attempt progressive truncation + exponential backoff retries.
        try:
            if hasattr(self.provider, "generate_content"):
                return self.provider.generate_content(prompt)
            if callable(self.provider):
                return self.provider(prompt)
        except Exception as e:
            err = str(e).lower()
            if not any(k in err for k in ("rate_limit", "rate limit", "too large", "tokens", "413")):
                raise

            # Progressive retry strategy: reduce prompt size and retry
            from time import sleep

            try:
                # local import to avoid circular imports at module load
                from app.llm import token_utils
            except Exception:
                token_utils = None

            max_retries = int(os.getenv("LLM_RATE_RETRIES", "3"))
            backoff_base = float(os.getenv("LLM_BACKOFF_BASE", "2.0"))
            # If token utilities available, compute tokens and reduce by 30% each retry
            for attempt in range(1, max_retries + 1):
                # determine new prompt
                if token_utils:
                    try:
                        # Preserve any leading system instruction when truncating by tokens
                        header = ""
                        body = prompt
                        if prompt.startswith("System:") and "\n\n" in prompt:
                            parts = prompt.split("\n\n", 1)
                            header = parts[0] + "\n\n"
                            body = parts[1]

                        current_tokens = token_utils.estimate_tokens(body, model=getattr(self, "model", None))
                        new_max = max(32, int(current_tokens * (0.7 ** attempt)))
                        truncated_body = token_utils.truncate_by_tokens(body, new_max, model=getattr(self, "model", None))
                        truncated = header + truncated_body
                    except Exception:
                        truncated = prompt[: max(1, int(len(prompt) * (0.7 ** attempt)))]
                else:
                    truncated = prompt[: max(1, int(len(prompt) * (0.7 ** attempt)))]

                try:
                    if hasattr(self.provider, "generate_content"):
                        return self.provider.generate_content(truncated)
                    if callable(self.provider):
                        return self.provider(truncated)
                except Exception as e2:
                    err2 = str(e2).lower()
                    # If this last attempt failed, re-raise the error
                    if attempt == max_retries or not any(k in err2 for k in ("rate_limit", "rate limit", "too large", "tokens", "413")):
                        raise
                    sleep(backoff_base ** attempt)

        raise RuntimeError("LLM provider does not support generate_content or callable invocation.")

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
        prompt = self._messages_to_prompt(messages)
        return self._generate(prompt)

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
        prompt = self._messages_to_prompt(messages)
        if hasattr(self.provider, "acall"):
            return await self.provider.acall(prompt)
        result = self._generate(prompt)
        if inspect.isawaitable(result):
            return await result
        return result

    def invoke(self, *args: Any, **kwargs: Any) -> str:
        return self.call(*args, **kwargs)

    async def ainvoke(self, *args: Any, **kwargs: Any) -> str:
        return await self.acall(*args, **kwargs)

    def bind(self, *args: Any, **kwargs: Any):
        """Return a bound LLM compatible with CrewAI's executor setup."""
        if hasattr(self.provider, "bind"):
            bound_provider = self.provider.bind(*args, **kwargs)
            return self.__class__(bound_provider, model_name=self.model)
        return self

    def __call__(self, *args: Any, **kwargs: Any):
        return self.call(*args, **kwargs)


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
    try:
        provider = init_llm_provider()
        llm = AgentLLMAdapter(provider, model_name=model_name)
        logger.info("Agent LLM initialised from shared provider: %s", provider.get_model_name())
        _cached_llm = llm
        return llm
    except Exception as e:
        if "shared_llm" not in _warned:
            logger.warning("Shared LLM provider init failed: %s. Falling back to legacy provider.", e)
            _warned.add("shared_llm")

    # --- Legacy compatibility path --------------------------------------
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

    if "fallback" not in _warned:
        logger.warning(
            "No LLM provider available — agents will use FallbackLLM "
            "(static responses). Set GROQ_API_KEY, HF_TOKEN, GEMINI_API_KEY, or "
            "OPENAI_API_KEY in the environment."
        )
        _warned.add("fallback")
    _cached_llm = FallbackLLM()
    return _cached_llm


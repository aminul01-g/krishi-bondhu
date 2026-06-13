import logging

from app.llm.provider import init_llm_provider, LLMProvider

logger = logging.getLogger(__name__)


class LegacyLLMAdapter:
    """Backward compatibility wrapper for legacy llm_factory consumers."""

    def __init__(self, provider):
        self._provider = provider

    def __call__(self, prompt: str, *args, **kwargs):
        return self._provider.generate_content(prompt)

    def generate_content(self, prompt: str, *args, **kwargs):
        return self._provider.generate_content(prompt)

    def get_model_name(self) -> str:
        return self._provider.get_model_name()


def get_llm():
    """
    Legacy wrapper around the shared provider abstraction.

    This function preserves the old LLM factory interface while ensuring
    provider selection is centralized through `app.llm.provider`.
    """
    provider = init_llm_provider()
    if getattr(provider, "get_model_name", lambda: "")( ) == LLMProvider.FALLBACK.value:
        raise ValueError(
            "No LLM provider could be initialized. "
            "Set GROQ_API_KEY, GEMINI_API_KEY, or HF_TOKEN in the environment."
        )
    return LegacyLLMAdapter(provider)


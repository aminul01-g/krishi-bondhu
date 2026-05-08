import os
from typing import Any

from crewai import BaseLLM


class FallbackLLM(BaseLLM):
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
    return os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")


def get_agent_llm(model_name: str | None = None):
    model_name = model_name or os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-3.2-3B-Instruct")
    hf_token = _get_hf_token()

    if hf_token:
        try:
            from langchain_huggingface import ChatHuggingFace
            from langchain_community.llms import HuggingFaceHub

            return ChatHuggingFace(
                llm=HuggingFaceHub(repo_id=model_name, huggingfacehub_api_token=hf_token)
            )
        except Exception as e:
            print(f"[WARN] HuggingFace LLM initialization failed: {e}")

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                google_api_key=gemini_key,
                temperature=0.7,
            )
        except Exception as e:
            print(f"[WARN] Gemini LLM initialization failed: {e}")

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(openai_api_key=openai_key, temperature=0.7)
        except Exception as e:
            print(f"[WARN] OpenAI LLM initialization failed: {e}")

    return FallbackLLM()

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEndpoint

def get_llm():
    """
    Factory function to return the configured LLM based on environment variables.
    Defaults to Gemini if no provider is specified or if 'gemini' is set.
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider == "huggingface":
        hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
        hf_model = os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-3.2-3B-Instruct")
        if not hf_api_key:
            raise ValueError("HUGGINGFACE_API_KEY is not set.")
        
        # We use Langchain's HuggingFaceEndpoint wrapper
        return HuggingFaceEndpoint(
            repo_id=hf_model,
            huggingfacehub_api_token=hf_api_key,
            temperature=0.7,
            model_kwargs={"max_length": 512}
        )
    else:
        # Default to Gemini
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=gemini_api_key,
            temperature=0.7
        )

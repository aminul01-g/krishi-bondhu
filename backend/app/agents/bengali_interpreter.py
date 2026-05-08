from crewai import Agent
from langchain_huggingface import ChatHuggingFace
from langchain_community.llms import HuggingFaceHub
import os

# Define the primary LLM based on environment variables
# Production requirement: primary Hugging Face model with fallback logic
def get_llm():
    model_name = os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-3.2-3B-Instruct")
    try:
        # Using ChatHuggingFace for a chat-optimized interface
        return ChatHuggingFace(llm=HuggingFaceHub(repo_id=model_name))
    except Exception as e:
        print(f"Error initializing HuggingFace LLM: {e}. Falling back to generic model.")
        return HuggingFaceHub(repo_id="microsoft/Phi-3-mini-4k-instruct")

llm = get_llm()

bengali_interpreter = Agent(
    role="Bengali Language & Multimodal Interpreter Agent",
    goal="Detect language, translate if necessary, handle Bengali-specific NLP, and route the user's intent to the appropriate expert.",
    backstory="You are the frontline brain of KrishiBondhu. You natively understand Bengali and English code-switching. You expertly interpret farmer intents from text and STT audio transcripts, ensuring seamless communication across the platform.",
    llm=llm,
    verbose=True,
    allow_delegation=True
)

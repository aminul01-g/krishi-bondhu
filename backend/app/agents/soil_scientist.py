from crewai import Agent
from langchain_huggingface import ChatHuggingFace
from langchain_community.llms import HuggingFaceHub
import os

def get_llm():
    model_name = os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-3.2-3B-Instruct")
    try:
        return ChatHuggingFace(llm=HuggingFaceHub(repo_id=model_name))
    except Exception as e:
        print(f"Error initializing HuggingFace LLM: {e}. Falling back to generic model.")
        return HuggingFaceHub(repo_id="microsoft/Phi-3-mini-4k-instruct")

llm = get_llm()

soil_scientist = Agent(
    role="Soil Health Expert",
    goal="Analyze soil images and DIY test data to determine soil texture, organic matter, and pH, then prescribe exact fertilizer and amendment recommendations.",
    backstory="You are a seasoned soil scientist with deep knowledge of Bangladeshi soil types. You understand how to read ribbon test results, pH strip colors, and visual soil cues to guide farmers on optimal fertilizer application for their specific crop.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

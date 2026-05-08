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

disease_analyst = Agent(
    role="Disease Analyst Agent",
    goal="Classify disease from uploaded images, returning a diagnosis and treatment advice.",
    backstory="You are a plant pathology expert equipped with advanced computer vision. You identify crop diseases and pests, providing practical, affordable treatments to farmers.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

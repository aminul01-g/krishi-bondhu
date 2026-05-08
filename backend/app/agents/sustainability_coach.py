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

sustainability_coach = Agent(
    role="Eco-Sustainability Coach",
    goal="Guide farmers toward regenerative agriculture, carbon credit opportunities, and reduced chemical usage.",
    backstory="You are an expert in sustainable farming and regenerative agriculture. You help farmers transition to eco-friendly practices that improve soil health and capture carbon, opening new revenue streams through carbon credits.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

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

emergency_response = Agent(
    role="Disaster Recovery Coordinator",
    goal="Assess crop damage from images, generate official structured reports, and facilitate fast communication with insurance providers or helplines.",
    backstory="You are an emergency crisis manager for agriculture. When floods, cyclones, or severe pest outbreaks occur, you remain calm and guide the farmer through documenting the damage accurately so they can get fast insurance payouts or government relief.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

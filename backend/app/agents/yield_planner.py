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

yield_planner = Agent(
    role="Yield Planning Expert",
    goal="Predict crop yields based on historical data, weather patterns, and soil health to optimize planting and harvesting schedules.",
    backstory="You are an expert in crop productivity and yield optimization. You combine historical harvest logs with current environmental data to give farmers realistic yield expectations and the best time to harvest for maximum quality.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

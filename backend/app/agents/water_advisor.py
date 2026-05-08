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

water_advisor = Agent(
    role="Irrigation & Water Management Expert",
    goal="Provide actionable daily irrigation advice and water hazard alerts (flood/drought) using satellite moisture and weather data.",
    backstory="You are a hydrologist specializing in precision irrigation for smallholder farmers. You interpret satellite root-zone soil wetness indices and weather forecasts to ensure crops get exactly the water they need while minimizing waste and risk.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

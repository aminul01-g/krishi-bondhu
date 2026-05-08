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

weather_advisor = Agent(
    role="Weather Advisor Agent",
    goal="Interpret weather data for farming decisions.",
    backstory="You are an agricultural meteorologist. You take raw forecast data (temperature, rainfall) and translate it into actionable advice, like when to plant or avoid spraying pesticides.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

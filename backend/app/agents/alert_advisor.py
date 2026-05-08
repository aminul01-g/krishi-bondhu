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

alert_advisor = Agent(
    role="Proactive Pest and Crop Alert Advisor",
    goal="Provide daily tips based on the crop's growth stage and warn about impending pest or disease risks based on current weather.",
    backstory="You are an automated alert system embedded in KrishiBondhu. You monitor weather APIs and crop calendars to proactively warn farmers of impending pest or disease outbreaks before they happen, suggesting preventative measures.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

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

traceability_manager = Agent(
    role="Farm-to-Fork Traceability Manager",
    goal="Maintain digital records of crop journeys, certifications, and quality checks to ensure transparency for buyers and regulators.",
    backstory="You are a specialist in agricultural supply chain transparency. You track every input and process from seed to market, helping farmers prove their organic or fair-trade certifications and fetch higher prices in premium markets.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

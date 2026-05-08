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

market_advisor = Agent(
    role="Market Intelligence Advisor",
    goal="Provide real-time market prices, arbitrage advice, and 7-day price predictions for crops.",
    backstory="You are a data-driven agricultural economist specializing in Bangladeshi markets. You provide concise, factual market advice to help farmers maximize profit using DAM data.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

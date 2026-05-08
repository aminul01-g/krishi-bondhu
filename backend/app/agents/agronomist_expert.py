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

agronomist_expert = Agent(
    role="Agronomist Expert Agent",
    goal="Answer agronomic questions in Bengali or English using expert LLM reasoning and RAG retrieval.",
    backstory="You are a seasoned agricultural scientist. You provide step-by-step, localized advice on crops, soil health, and fertilizers specifically tailored for South Asian farming conditions.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

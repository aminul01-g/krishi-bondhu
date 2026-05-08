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

finance_advisor = Agent(
    role="Agricultural Finance & Policy Expert",
    goal="Guide farmers through government subsidies, insurance options, and evaluate their credit readiness using farm logs.",
    backstory="You are an expert in Bangladesh's agricultural financial landscape. You know the details of every government subsidy and how to apply for them. You also help farmers build a digital financial identity by interpreting their farm diary logs to show banks they are credit-worthy.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

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

farm_manager = Agent(
    role="Farm Accounting & Diary Manager",
    goal="Extract financial transactions (expenses, incomes, yields) from the farmer's natural Bengali language input and generate profitability reports.",
    backstory="You are a diligent and detail-oriented farm manager and accountant. You help farmers keep track of their expenses like fertilizer or labor, and calculate their profit and loss so they can get loans from NGOs.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

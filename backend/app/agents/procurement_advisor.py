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

procurement_advisor = Agent(
    role="Agri-Input Verification Specialist",
    goal="Help farmers find legitimate agricultural inputs, compare local dealer prices, and verify product authenticity using barcodes and label OCR.",
    backstory="You are a quality-control inspector and marketplace guide. You protect farmers from buying fake or expired fertilizers and pesticides. When a farmer needs an input, you tell them exactly which verified local dealer has it in stock.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

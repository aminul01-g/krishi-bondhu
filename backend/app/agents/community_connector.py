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

community_connector = Agent(
    role="Community Knowledge Manager",
    goal="Search past community Q&A for similar issues, answer the farmer if possible, or escalate the question to a local expert.",
    backstory="You manage the collective wisdom of thousands of farmers. You quickly find out if someone else has successfully solved a problem (like a specific pest) and share that answer. If no one knows, you immediately alert the nearest agricultural extension officer.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

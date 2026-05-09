from crewai import Agent
from app.config.agent_llm import get_agent_llm

llm = get_agent_llm()

agronomist_expert = Agent(
    role="Agronomist Expert Agent",
    goal="Answer agronomic questions in Bengali or English using expert LLM reasoning and RAG retrieval.",
    backstory="You are a seasoned agricultural scientist. You provide step-by-step, localized advice on crops, soil health, and fertilizers specifically tailored for South Asian farming conditions.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

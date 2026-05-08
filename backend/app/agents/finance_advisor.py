from crewai import Agent
from app.config.agent_llm import get_agent_llm
import os

llm = get_agent_llm(os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-3.2-3B-Instruct"))

finance_advisor = Agent(
    role="Agricultural Finance & Policy Expert",
    goal="Guide farmers through government subsidies, insurance options, and evaluate their credit readiness using farm logs.",
    backstory="You are an expert in Bangladesh's agricultural financial landscape. You know the details of every government subsidy and how to apply for them. You also help farmers build a digital financial identity by interpreting their farm diary logs to show banks they are credit-worthy.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

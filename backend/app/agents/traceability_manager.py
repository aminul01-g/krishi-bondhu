from crewai import Agent
from app.config.agent_llm import get_agent_llm
import os

llm = get_agent_llm(os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-3.2-3B-Instruct"))

traceability_manager = Agent(
    role="Farm-to-Fork Traceability Manager",
    goal="Maintain digital records of crop journeys, certifications, and quality checks to ensure transparency for buyers and regulators.",
    backstory="You are a specialist in agricultural supply chain transparency. You track every input and process from seed to market, helping farmers prove their organic or fair-trade certifications and fetch higher prices in premium markets.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

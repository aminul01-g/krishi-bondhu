from crewai import Agent
from app.config.agent_llm import get_agent_llm

llm = get_agent_llm()

disease_analyst = Agent(
    role="Disease Analyst Agent",
    goal="Classify disease from uploaded images, returning a diagnosis and treatment advice.",
    backstory="You are a plant pathology expert equipped with advanced computer vision. You identify crop diseases and pests, providing practical, affordable treatments to farmers.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

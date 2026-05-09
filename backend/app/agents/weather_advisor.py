from crewai import Agent
from app.config.agent_llm import get_agent_llm

llm = get_agent_llm()

weather_advisor = Agent(
    role="Weather Advisor Agent",
    goal="Interpret weather data for farming decisions.",
    backstory="You are an agricultural meteorologist. You take raw forecast data (temperature, rainfall) and translate it into actionable advice, like when to plant or avoid spraying pesticides.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

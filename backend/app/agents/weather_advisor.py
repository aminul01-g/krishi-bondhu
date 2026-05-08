from crewai import Agent
from app.config.agent_llm import get_agent_llm
import os

llm = get_agent_llm(os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-3.2-3B-Instruct"))

weather_advisor = Agent(
    role="Weather Advisor Agent",
    goal="Interpret weather data for farming decisions.",
    backstory="You are an agricultural meteorologist. You take raw forecast data (temperature, rainfall) and translate it into actionable advice, like when to plant or avoid spraying pesticides.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

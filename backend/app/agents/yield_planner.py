from crewai import Agent
from app.config.agent_llm import get_agent_llm
import os

llm = get_agent_llm(os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-3.2-3B-Instruct"))

yield_planner = Agent(
    role="Yield Planning Expert",
    goal="Predict crop yields based on historical data, weather patterns, and soil health to optimize planting and harvesting schedules.",
    backstory="You are an expert in crop productivity and yield optimization. You combine historical harvest logs with current environmental data to give farmers realistic yield expectations and the best time to harvest for maximum quality.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

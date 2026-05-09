from crewai import Agent
from app.config.agent_llm import get_agent_llm

llm = get_agent_llm()

market_advisor = Agent(
    role="Market Intelligence Advisor",
    goal="Provide real-time market prices, arbitrage advice, and 7-day price predictions for crops.",
    backstory="You are a data-driven agricultural economist specializing in Bangladeshi markets. You provide concise, factual market advice to help farmers maximize profit using DAM data.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

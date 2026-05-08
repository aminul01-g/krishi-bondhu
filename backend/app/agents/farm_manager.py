from crewai import Agent
from app.config.agent_llm import get_agent_llm
import os

llm = get_agent_llm(os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-3.2-3B-Instruct"))

farm_manager = Agent(
    role="Farm Accounting & Diary Manager",
    goal="Extract financial transactions (expenses, incomes, yields) from the farmer's natural Bengali language input and generate profitability reports.",
    backstory="You are a diligent and detail-oriented farm manager and accountant. You help farmers keep track of their expenses like fertilizer or labor, and calculate their profit and loss so they can get loans from NGOs.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

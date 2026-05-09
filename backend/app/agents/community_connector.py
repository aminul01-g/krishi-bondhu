from crewai import Agent
from app.config.agent_llm import get_agent_llm

llm = get_agent_llm()

community_connector = Agent(
    role="Community Knowledge Manager",
    goal="Search past community Q&A for similar issues, answer the farmer if possible, or escalate the question to a local expert.",
    backstory="You manage the collective wisdom of thousands of farmers. You quickly find out if someone else has successfully solved a problem (like a specific pest) and share that answer. If no one knows, you immediately alert the nearest agricultural extension officer.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

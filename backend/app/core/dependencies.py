from app.crews.krishi_crew import KrishiCrewOrchestrator
from app.tools.finance_tool import CreditScoringTool

# Initialize the global orchestrator singleton
orchestrator = KrishiCrewOrchestrator()

# Initialize global tools if needed directly by endpoints
credit_scorer = CreditScoringTool()

from crewai import Crew, Process
from app.agents.bengali_interpreter import bengali_interpreter
from app.agents.agronomist_expert import agronomist_expert
from app.agents.disease_analyst import disease_analyst
from app.agents.weather_advisor import weather_advisor
from app.agents.market_advisor import market_advisor
from app.agents.farm_manager import farm_manager
from app.agents.alert_advisor import alert_advisor
from app.agents.soil_scientist import soil_scientist
from app.agents.water_advisor import water_advisor
from app.agents.finance_advisor import finance_advisor
from app.agents.community_connector import community_connector
from app.agents.procurement_advisor import procurement_advisor
from app.agents.emergency_response import emergency_response
from app.agents.yield_planner import yield_planner
from app.agents.traceability_manager import traceability_manager
from app.agents.sustainability_coach import sustainability_coach

class KrishiCrew:
    """
    The Master Crew that handles general agricultural queries.
    Uses a sequential process to first interpret and then solve.
    """
    def __init__(self, agents=None):
        # Use provided agents or default set
        self.agents = agents or [
            bengali_interpreter,
            agronomist_expert,
            weather_advisor,
            market_advisor,
            farm_manager
        ]

    def create_crew(self, tasks=None):
        return Crew(
            agents=self.agents,
            tasks=tasks or [],
            process=Process.sequential,
            verbose=True
        )

class MarketAnalysisCrew:
    """
    Specialized Crew for market trends, price predictions, and arbitrage.
    """
    def __init__(self):
        self.agents = [
            bengali_interpreter,
            market_advisor,
            procurement_advisor
        ]

    def create_crew(self, tasks=None):
        return Crew(
            agents=self.agents,
            tasks=tasks or [],
            process=Process.sequential,
            verbose=True
        )

class HealthAndSoilCrew:
    """
    Specialized Crew for crop disease, soil health, and sustainability.
    """
    def __init__(self):
        self.agents = [
            bengali_interpreter,
            disease_analyst,
            soil_scientist,
            sustainability_coach
        ]

    def create_crew(self, tasks=None):
        return Crew(
            agents=self.agents,
            tasks=tasks or [],
            process=Process.sequential,
            verbose=True
        )

class EmergencyResponseCrew:
    """
    High-priority Crew for disaster recovery and damage assessment.
    """
    def __init__(self):
        self.agents = [
            bengali_interpreter,
            emergency_response,
            alert_advisor
        ]

    def create_crew(self, tasks=None):
        return Crew(
            agents=self.agents,
            tasks=tasks or [],
            process=Process.sequential,
            verbose=True
        )

class FinancialPlanningCrew:
    """
    Crew for farm accounting, credit scoring, and subsidies.
    """
    def __init__(self):
        self.agents = [
            bengali_interpreter,
            farm_manager,
            finance_advisor
        ]

    def create_crew(self, tasks=None):
        return Crew(
            agents=self.agents,
            tasks=tasks or [],
            process=Process.sequential,
            verbose=True
        )

import os
import json
import logging
import yaml
from cachetools import TTLCache
from crewai import Agent, Task, Crew, Process
from app.config.model_config import model_registry
from app.tools.vision_tool import LocalVisionDiseaseTool
from app.tools.weather_tool import WeatherLookupTool
from app.tools.market_tool import MarketPriceTool
from app.tools.alert_tool import PestRiskTool
from app.tools.soil_tool import SoilVisionTool, DIYSoilTestTool, RecommendFertilizerTool
from app.tools.irrigation_tool import SatelliteMoistureTool, WaterBalanceTool, FloodDroughtAlertTool
from app.tools.finance_tool import SubsidyNavigatorTool, CreditScoringTool, InsuranceQuoteTool
from app.tools.community_tool import CommunitySearchTool, EscalateToExpertTool
from app.tools.marketplace_tool import DealerSearchTool, ProductVerificationTool, LabelScannerTool
from app.tools.emergency_tool import CropDamageAssessmentTool, DamageReportGeneratorTool, SMSShareTool

# 1. Setup Structured Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("KrishiCrew")

# 2. Setup In-Memory Cache (Stores 100 items for up to 10 minutes)
# We cache the exact string of the input to save LLM costs on duplicate queries
response_cache = TTLCache(maxsize=100, ttl=600)

class KrishiCrewOrchestrator:
    def __init__(self):
        # Configuration is now in backend/app/config
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        with open(os.path.join(self.config_dir, 'agents.yaml'), 'r', encoding='utf-8') as f:
            self.agents_config = yaml.safe_load(f)
        with open(os.path.join(self.config_dir, 'tasks.yaml'), 'r', encoding='utf-8') as f:
            self.tasks_config = yaml.safe_load(f)
        # The main manager LLM is the interpreter (fast)
        self.manager_llm = model_registry.get_interpreter_llm()
        
        # Tools
        self.vision_tool = LocalVisionDiseaseTool()
        self.weather_tool = WeatherLookupTool()
        self.market_tool = MarketPriceTool()
        self.alert_tool = PestRiskTool()
        self.soil_vision_tool = SoilVisionTool()
        self.diy_soil_tool = DIYSoilTestTool()
        self.recommend_fertilizer_tool = RecommendFertilizerTool()
        self.satellite_moisture_tool = SatelliteMoistureTool()
        self.water_balance_tool = WaterBalanceTool()
        self.water_hazard_tool = FloodDroughtAlertTool()
        self.subsidy_tool = SubsidyNavigatorTool()
        self.credit_tool = CreditScoringTool()
        self.insurance_tool = InsuranceQuoteTool()
        self.community_search_tool = CommunitySearchTool()
        self.escalate_tool = EscalateToExpertTool()
        self.dealer_tool = DealerSearchTool()
        self.product_verify_tool = ProductVerificationTool()
        self.label_scanner_tool = LabelScannerTool()
        self.damage_assessment_tool = CropDamageAssessmentTool()
        self.damage_report_tool = DamageReportGeneratorTool()
        self.sms_share_tool = SMSShareTool()
        
        logger.info("KrishiCrewOrchestrator initialized with memory and caching.")

    def _create_agents(self):
        # Router uses the fast 1B interpreter model
        interpreter_llm = model_registry.get_interpreter_llm()
        # Agronomist uses the heavy 70B (or 2B fallback)
        agronomist_llm = model_registry.get_agronomist_llm()
        
        router_agent = Agent(config=self.agents_config["router_agent"], llm=interpreter_llm, allow_delegation=False, verbose=True)
        agronomist_agent = Agent(config=self.agents_config["agronomist_agent"], llm=agronomist_llm, allow_delegation=False, verbose=True)
        pathologist_agent = Agent(config=self.agents_config["pathologist_agent"], llm=interpreter_llm, tools=[self.vision_tool], allow_delegation=False, verbose=True)
        weather_agent = Agent(config=self.agents_config["weather_analyst_agent"], llm=interpreter_llm, tools=[self.weather_tool], allow_delegation=False, verbose=True)
        market_agent = Agent(config=self.agents_config["market_analyst_agent"], llm=interpreter_llm, tools=[self.market_tool], allow_delegation=False, max_iter=3, verbose=True)
        farm_manager_agent = Agent(config=self.agents_config["farm_manager_agent"], llm=interpreter_llm, allow_delegation=False, verbose=True)
        alert_advisor_agent = Agent(config=self.agents_config["alert_advisor_agent"], llm=agronomist_llm, tools=[self.alert_tool], allow_delegation=False, verbose=True)
        soil_scientist_agent = Agent(config=self.agents_config["soil_scientist_agent"], llm=agronomist_llm, tools=[self.soil_vision_tool, self.diy_soil_tool, self.recommend_fertilizer_tool], allow_delegation=False, verbose=True)
        water_analyst_agent = Agent(config=self.agents_config["water_analyst_agent"], llm=agronomist_llm, tools=[self.satellite_moisture_tool, self.water_balance_tool, self.water_hazard_tool], allow_delegation=False, verbose=True)
        finance_advisor_agent = Agent(config=self.agents_config["finance_advisor_agent"], llm=agronomist_llm, tools=[self.subsidy_tool, self.credit_tool, self.insurance_tool], allow_delegation=False, verbose=True)
        community_connector_agent = Agent(config=self.agents_config["community_connector_agent"], llm=agronomist_llm, tools=[self.community_search_tool, self.escalate_tool], allow_delegation=False, verbose=True)
        procurement_advisor_agent = Agent(config=self.agents_config["procurement_advisor_agent"], llm=agronomist_llm, tools=[self.dealer_tool, self.product_verify_tool, self.label_scanner_tool], allow_delegation=False, verbose=True)
        emergency_response_agent = Agent(config=self.agents_config["emergency_response_agent"], llm=agronomist_llm, tools=[self.damage_assessment_tool, self.damage_report_tool, self.sms_share_tool], allow_delegation=False, verbose=True)
        return router_agent, agronomist_agent, pathologist_agent, weather_agent, market_agent, farm_manager_agent, alert_advisor_agent, soil_scientist_agent, water_analyst_agent, finance_advisor_agent, community_connector_agent, procurement_advisor_agent, emergency_response_agent

    def _create_tasks(self, agents):
        router, agronomist, pathologist, weather, market, farm_manager, alert_advisor, soil_scientist, water_analyst, finance_advisor, community_connector, procurement_advisor, emergency_response = agents
        
        # Prepare task configurations with the agent objects
        self.tasks_config["route_query_task"]["agent"] = router
        self.tasks_config["disease_diagnosis_task"]["agent"] = pathologist
        self.tasks_config["agronomy_advice_task"]["agent"] = agronomist
        self.tasks_config["weather_advice_task"]["agent"] = weather
        self.tasks_config["market_advice_task"]["agent"] = market
        self.tasks_config["farm_diary_task"]["agent"] = farm_manager
        self.tasks_config["alert_advice_task"]["agent"] = alert_advisor
        self.tasks_config["soil_analysis_task"]["agent"] = soil_scientist
        self.tasks_config["irrigation_advice_task"]["agent"] = water_analyst
        self.tasks_config["finance_navigator_task"]["agent"] = finance_advisor
        self.tasks_config["community_qa_task"]["agent"] = community_connector
        self.tasks_config["marketplace_task"]["agent"] = procurement_advisor
        self.tasks_config["emergency_task"]["agent"] = emergency_response
        
        route_task = Task(config=self.tasks_config["route_query_task"])
        disease_task = Task(config=self.tasks_config["disease_diagnosis_task"])
        agronomy_task = Task(config=self.tasks_config["agronomy_advice_task"])
        weather_task = Task(config=self.tasks_config["weather_advice_task"])
        market_task = Task(config=self.tasks_config["market_advice_task"])
        diary_task = Task(config=self.tasks_config["farm_diary_task"])
        alert_task = Task(config=self.tasks_config["alert_advice_task"])
        soil_task = Task(config=self.tasks_config["soil_analysis_task"])
        water_task = Task(config=self.tasks_config["irrigation_advice_task"])
        finance_task = Task(config=self.tasks_config["finance_navigator_task"])
        community_task = Task(config=self.tasks_config["community_qa_task"])
        marketplace_task = Task(config=self.tasks_config["marketplace_task"])
        emergency_task = Task(config=self.tasks_config["emergency_task"])
        
        return [route_task, disease_task, agronomy_task, weather_task, market_task, diary_task, alert_task, soil_task, water_task, finance_task, community_task, marketplace_task, emergency_task]


    def _generate_cache_key(self, user_input: str, gps: dict, image_path: str) -> str:
        """Create a deterministic cache key based on inputs."""
        return f"{user_input}_{gps}_{image_path}"

    async def ainvoke(self, initial_state: dict, trace_id: str = "unknown", status_callback=None) -> dict:
        user_input = initial_state.get("transcript", "")
        gps = initial_state.get("gps")
        image_path = initial_state.get("image_path")
        
        # Helper to broadcast status
        def sync_step_callback(agent_output):
            import asyncio
            if status_callback:
                try:
                    msg = f"Agent working: {agent_output.agent}..."
                    # We create a task since step_callback in crewAI is synchronous
                    asyncio.create_task(status_callback({"message": msg}))
                except Exception as e:
                    logger.warning(f"Failed to execute step callback: {e}")

        # 3. Check Cache First
        cache_key = self._generate_cache_key(user_input, gps, image_path)
        if cache_key in response_cache:
            logger.info(f"Cache HIT for query: {user_input[:30]}...")
            initial_state["reply_text"] = response_cache[cache_key]
            return initial_state

        logger.info(f"Processing new request: {user_input[:50]}")
        
        agents_tuple = self._create_agents()
        tasks_list = self._create_tasks(agents_tuple)

        router_agent, agronomist_agent, pathologist_agent, weather_agent, market_agent, farm_manager_agent, alert_advisor_agent, soil_scientist_agent, water_analyst_agent, finance_advisor_agent, community_connector_agent, procurement_advisor_agent, emergency_response_agent = agents_tuple
        route_task, disease_task, agronomy_task, weather_task, market_task, diary_task, alert_task, soil_task, water_task, finance_task, community_task, marketplace_task, emergency_task = tasks_list

        import asyncio
        import json

        try:
            # 1. Run the Router ONLY
            logger.info("Executing Router Agent...")
            router_crew = Crew(agents=[router_agent], tasks=[route_task], verbose=True, step_callback=sync_step_callback)
            inputs = {
                "user_input": user_input,
                "gps": str(gps) if gps else "None",
                "image_path": str(image_path) if image_path else "None",
                "user_id": initial_state.get("user_id", "anonymous")
            }
            route_result = await asyncio.to_thread(router_crew.kickoff, inputs=inputs)
            route_str = str(route_result).replace("```json", "").replace("```", "").strip()
            
            try:
                route_data = json.loads(route_str)
                intent = route_data.get("intent", "agronomy")
                response_text = route_data.get("router_response", "")
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse router JSON. Raw output: {route_str}")
                intent = "agronomy"
                response_text = "I'm having trouble understanding exactly, but let's talk about farming."
                if "hello" in user_input.lower():
                    intent = "greeting"

            logger.info(f"Router identified intent: {intent}")

            # 2. Execute target crew based on intent
            if intent == "greeting":
                final_text = response_text
            elif intent == "soil":
                logger.info("Routing to Soil Scientist Agent...")
                soil_crew = Crew(agents=[soil_scientist_agent], tasks=[soil_task], verbose=True, step_callback=sync_step_callback)
                result = await asyncio.to_thread(soil_crew.kickoff, inputs=inputs)
                final_text = str(result)
            elif intent == "disease" or (image_path and image_path.lower() != "none" and intent != "soil"):
                logger.info("Routing to Pathologist Agent...")
                disease_crew = Crew(agents=[pathologist_agent], tasks=[disease_task], verbose=True, step_callback=sync_step_callback)
                result = await asyncio.to_thread(disease_crew.kickoff, inputs=inputs)
                final_text = str(result)
            elif intent == "weather":
                logger.info("Routing to Weather Agent...")
                weather_crew = Crew(agents=[weather_agent], tasks=[weather_task], verbose=True, step_callback=sync_step_callback)
                result = await asyncio.to_thread(weather_crew.kickoff, inputs=inputs)
                final_text = str(result)
            elif intent == "market":
                logger.info("Routing to Market Agent...")
                market_crew = Crew(agents=[market_agent], tasks=[market_task], verbose=True, step_callback=sync_step_callback)
                result = await asyncio.to_thread(market_crew.kickoff, inputs=inputs)
                final_text = str(result)
            elif intent == "diary":
                logger.info("Routing to Farm Manager Agent (Diary)...")
                diary_crew = Crew(agents=[farm_manager_agent], tasks=[diary_task], verbose=True, step_callback=sync_step_callback)
                result = await asyncio.to_thread(diary_crew.kickoff, inputs=inputs)
                # The result here should be raw JSON from the agent, we just pass it along
                final_text = str(result).replace("```json", "").replace("```", "").strip()
            elif intent == "alerts":
                logger.info("Routing to Alert Advisor Agent...")
                alert_crew = Crew(agents=[alert_advisor_agent], tasks=[alert_task], verbose=True, step_callback=sync_step_callback)
                result = await asyncio.to_thread(alert_crew.kickoff, inputs=inputs)
                final_text = str(result)
            elif intent == "water":
                logger.info("Routing to Water Analyst Agent...")
                water_crew = Crew(agents=[water_analyst_agent], tasks=[water_task], verbose=True, step_callback=sync_step_callback)
                result = await asyncio.to_thread(water_crew.kickoff, inputs=inputs)
                final_text = str(result)
            elif intent == "finance":
                logger.info("Routing to Finance Advisor Agent...")
                finance_crew = Crew(agents=[finance_advisor_agent], tasks=[finance_task], verbose=True, step_callback=sync_step_callback)
                result = await asyncio.to_thread(finance_crew.kickoff, inputs=inputs)
                final_text = str(result)
            elif intent == "community":
                logger.info("Routing to Community Connector Agent...")
                community_crew = Crew(agents=[community_connector_agent], tasks=[community_task], verbose=True, step_callback=sync_step_callback)
                result = await asyncio.to_thread(community_crew.kickoff, inputs=inputs)
                final_text = str(result)
            elif intent == "marketplace":
                logger.info("Routing to Procurement Advisor Agent...")
                marketplace_crew = Crew(agents=[procurement_advisor_agent], tasks=[marketplace_task], verbose=True, step_callback=sync_step_callback)
                result = await asyncio.to_thread(marketplace_crew.kickoff, inputs=inputs)
                final_text = str(result)
            elif intent == "emergency":
                logger.info("Routing to Emergency Response Agent...")
                emergency_crew = Crew(agents=[emergency_response_agent], tasks=[emergency_task], verbose=True, step_callback=sync_step_callback)
                result = await asyncio.to_thread(emergency_crew.kickoff, inputs=inputs)
                final_text = str(result)
            else:
                logger.info("Routing to Agronomist Agent...")
                agronomy_crew = Crew(agents=[agronomist_agent], tasks=[agronomy_task], verbose=True, step_callback=sync_step_callback)
                result = await asyncio.to_thread(agronomy_crew.kickoff, inputs=inputs)
                final_text = str(result)

            # Save to Cache
            response_cache[cache_key] = final_text
            logger.info("Crew execution successful. Response cached.")
            
            initial_state["reply_text"] = final_text
            
            # NEW: Persist any staged tool data (like market prices) to DB
            if intent == "market" and hasattr(self, 'market_tool'):
                try:
                    from app.db import AsyncSessionLocal
                    async with AsyncSessionLocal() as db_session:
                        await self.market_tool.save_prices_to_db(db_session)
                except Exception as db_e:
                    logger.warning(f"Failed to persist market tool data: {db_e}")
                    
            return initial_state
            
        except Exception as e:
            logger.error(f"Crew execution failed: {str(e)}", exc_info=True)
            initial_state["reply_text"] = "I am sorry, but I encountered an error processing your request."
            return initial_state

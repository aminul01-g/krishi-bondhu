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
        market_agent = Agent(config=self.agents_config["market_analyst_agent"], llm=agronomist_llm, tools=[self.market_tool], allow_delegation=False, verbose=True)
        farm_manager_agent = Agent(config=self.agents_config["farm_manager_agent"], llm=interpreter_llm, allow_delegation=False, verbose=True)
        alert_advisor_agent = Agent(config=self.agents_config["alert_advisor_agent"], llm=agronomist_llm, tools=[self.alert_tool], allow_delegation=False, verbose=True)
        return router_agent, agronomist_agent, pathologist_agent, weather_agent, market_agent, farm_manager_agent, alert_advisor_agent

    def _create_tasks(self, agents):
        router, agronomist, pathologist, weather, market, farm_manager, alert_advisor = agents
        
        route_task = Task(config=self.tasks_config["route_query_task"], agent=router)
        disease_task = Task(config=self.tasks_config["disease_diagnosis_task"], agent=pathologist)
        agronomy_task = Task(config=self.tasks_config["agronomy_advice_task"], agent=agronomist)
        weather_task = Task(config=self.tasks_config["weather_advice_task"], agent=weather)
        market_task = Task(config=self.tasks_config["market_advice_task"], agent=market)
        diary_task = Task(config=self.tasks_config["farm_diary_task"], agent=farm_manager)
        alert_task = Task(config=self.tasks_config["alert_advice_task"], agent=alert_advisor)
        
        return [route_task, disease_task, agronomy_task, weather_task, market_task, diary_task, alert_task]

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

        router_agent, agronomist_agent, pathologist_agent, weather_agent, market_agent, farm_manager_agent, alert_advisor_agent = agents_tuple
        route_task, disease_task, agronomy_task, weather_task, market_task, diary_task, alert_task = tasks_list

        import asyncio
        import json

        try:
            # 1. Run the Router ONLY
            logger.info("Executing Router Agent...")
            router_crew = Crew(agents=[router_agent], tasks=[route_task], verbose=True, step_callback=sync_step_callback)
            inputs = {
                "user_input": user_input,
                "gps": str(gps) if gps else "None",
                "image_path": str(image_path) if image_path else "None"
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
            elif intent == "disease" or (image_path and image_path.lower() != "none"):
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
            else:
                logger.info("Routing to Agronomist Agent...")
                agronomy_crew = Crew(agents=[agronomist_agent], tasks=[agronomy_task], verbose=True, step_callback=sync_step_callback)
                result = await asyncio.to_thread(agronomy_crew.kickoff, inputs=inputs)
                final_text = str(result)

            # Save to Cache
            response_cache[cache_key] = final_text
            logger.info("Crew execution successful. Response cached.")
            
            initial_state["reply_text"] = final_text
            return initial_state
            
        except Exception as e:
            logger.error(f"Crew execution failed: {str(e)}", exc_info=True)
            initial_state["reply_text"] = "I am sorry, but I encountered an error processing your request."
            return initial_state

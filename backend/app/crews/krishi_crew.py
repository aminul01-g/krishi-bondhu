import os
import json
import logging
import yaml
from cachetools import TTLCache
from crewai import Agent, Task, Crew, Process
from app.config.model_config import model_registry
from app.tools.vision_tool import LocalVisionDiseaseTool
from app.tools.weather_tool import WeatherLookupTool

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
        
        logger.info("KrishiCrewOrchestrator initialized with memory and caching.")

    def _create_agents(self):
        # Router uses the fast 1B interpreter model
        interpreter_llm = model_registry.get_interpreter_llm()
        # Agronomist uses the heavy 70B (or 2B fallback)
        agronomist_llm = model_registry.get_agronomist_llm()
        
        router_agent = Agent(config=self.agents_config["router_agent"], llm=interpreter_llm, verbose=True)
        agronomist_agent = Agent(config=self.agents_config["agronomist_agent"], llm=agronomist_llm, verbose=True)
        pathologist_agent = Agent(config=self.agents_config["pathologist_agent"], llm=interpreter_llm, tools=[self.vision_tool], verbose=True)
        weather_agent = Agent(config=self.agents_config["weather_analyst_agent"], llm=interpreter_llm, tools=[self.weather_tool], verbose=True)
        return router_agent, agronomist_agent, pathologist_agent, weather_agent

    def _create_tasks(self, agents):
        router, agronomist, pathologist, weather = agents
        
        route_task = Task(config=self.tasks_config["route_query_task"], agent=router)
        disease_task = Task(config=self.tasks_config["disease_diagnosis_task"], agent=pathologist)
        agronomy_task = Task(config=self.tasks_config["agronomy_advice_task"], agent=agronomist)
        
        return [route_task, disease_task, agronomy_task]

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

        crew = Crew(
            agents=list(agents_tuple),
            tasks=tasks_list,
            process=Process.hierarchical,
            manager_llm=self.manager_llm,
            memory=True,
            verbose=True,
            step_callback=sync_step_callback
        )

        # 4. Error Handling and Execution
        try:
            # We rely on LangChain/CrewAI's built-in retries for the LLM layer,
            # but we catch global execution errors here.
            inputs = {
                "user_input": user_input,
                "gps": str(gps) if gps else "None",
                "image_path": str(image_path) if image_path else "None"
            }
            result = await crew.kickoff_async(inputs=inputs)
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

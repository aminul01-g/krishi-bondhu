"""
LangGraph app wiring STT, Vision, Weather, LLM steps, and TTS.
Refactored to use modular services.
"""

from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

# Import services
from app.services.audio import stt_node
from app.services.llm import intent_node, reasoning_node
from app.services.weather import weather_node
from app.models.vision import run_vision_classifier

load_dotenv()

# State schema
class FarmState(TypedDict):
    audio_path: str
    transcript: str
    language: str
    user_id: str
    gps: dict
    crop: str
    image_path: str
    vision_result: dict
    weather_forecast: dict
    messages: Annotated[list, add_messages]
    reply_text: str
    tts_path: str
    need_image: bool

def vision_node(state: FarmState):
    if not state.get("image_path"):
        return {}
    res = run_vision_classifier(state["image_path"])
    return {"vision_result": res}

# Build Graph
graph_builder = StateGraph(FarmState)

# Add nodes
graph_builder.add_node("stt_node", stt_node)
graph_builder.add_node("intent_node", intent_node)
graph_builder.add_node("vision_node", vision_node)
graph_builder.add_node("weather_node", weather_node)
graph_builder.add_node("reasoning_node", reasoning_node)

# Define edges
graph_builder.add_edge(START, "stt_node")
graph_builder.add_edge("stt_node", "intent_node")

# Parallel/Branched execution
graph_builder.add_edge("intent_node", "vision_node")
graph_builder.add_edge("intent_node", "weather_node")

# Converge to reasoning
graph_builder.add_edge("vision_node", "reasoning_node")
graph_builder.add_edge("weather_node", "reasoning_node")

graph_builder.add_edge("reasoning_node", END)

# Compile
app = graph_builder.compile()
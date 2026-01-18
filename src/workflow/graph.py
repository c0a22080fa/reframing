import operator
import os
import json
from typing import Annotated, List, TypedDict, Union, Optional

from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent

from src.services.openai_service import OpenAIService
from src.services.comet_service import CometService
from src.services.search_service import SearchService
from src.services.neo4j_service import Neo4jService
from src.agents.context_agent import ContextAgent

# --- Helper ---
def load_prompt(filename: str) -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "prompts", filename)
    with open(path, "r") as f:
        return f.read()

# --- State Definition ---
class AgentState(TypedDict):
    input: str
    user_context: str
    comet_evidence: list
    explorer_evidence: list
    deep_intent: str
    nudge: str
    next_step: str # CALL_COMET, CALL_EXPLORER, FINALIZE
    search_query_override: Optional[str] # From Chair
    steps: Annotated[List[str], operator.add] # History tracking
    messages: Annotated[List[BaseMessage], operator.add]

# --- Node Implementations ---

def node_input_processor(state: AgentState):
    """Entry: Process Input, Write Active Node, Get Context"""
    print("--- [Node] Input Processor: Labeling Active Node ---")
    neo4j = Neo4jService()
    agent = ContextAgent(neo4j)
    
    # 1. Write to PKG (Mock 'Active' Labeling)
    agent.write_active_node("test_user_001", state["input"])
    
    # 2. Retrieve Context
    context = agent.retrieve_context("test_user_001")
    return {"user_context": context, "next_step": "START", "steps": ["START"]}

def node_profiler_chair(state: AgentState):
    """Profiler Chair: Orchestrates the Abduction Loop"""
    print("--- [Node] Profiler Chair: Deliberating ---")
    openai_service = OpenAIService()
    llm = openai_service.get_chat_model()
    
    template = load_prompt("agent_chair.txt")
    
    # Prepare inputs for prompt
    comet_txt = json.dumps(state.get("comet_evidence", []))
    explorer_txt = json.dumps(state.get("explorer_evidence", []))
    history_txt = json.dumps(state.get("steps", []))
    
    prompt = template.format(
        input=state['input'],
        user_context=state['user_context'],
        comet_evidence=comet_txt,
        explorer_evidence=explorer_txt,
        history=history_txt
    )
    
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content
    print(f"   -> Chair Thought: {content}")
    
    # Parse JSON
    try:
        if "{" in content:
            import re
            json_str = re.search(r'\{.*\}', content, re.DOTALL).group()
            result = json.loads(json_str)
            next_step = result.get("next_step", "FINALIZE")
            deep_intent = result.get("deep_intent", "")
            search_query = result.get("search_query", None)
        else:
            print("   [!] Logic Error: No JSON. Defaulting to FINALIZE.")
            next_step = "FINALIZE"
            deep_intent = content
            search_query = None
    except Exception as e:
        print(f"   [!] Parse Error: {e}. Defaulting to FINALIZE.")
        next_step = "FINALIZE"
        deep_intent = "Error in logic."
        search_query = None
    
    # Prevent infinite loop on COMET
    if next_step == "CALL_COMET" and "CALL_COMET" in state.get("steps", []):
         print("   [Chair] Loop Detected: Switching CALL_COMET to CALL_EXPLORER.")
         next_step = "CALL_EXPLORER"
    
    # Prevent infinite loop on EXPLORER
    if next_step == "CALL_EXPLORER" and state.get("steps", []).count("CALL_EXPLORER") > 1:
         print("   [Chair] Loop Detected: Forcing FINALIZE.")
         next_step = "FINALIZE"

    return {
        "next_step": next_step,
        "deep_intent": deep_intent if deep_intent else state.get("deep_intent"),
        "search_query_override": search_query,
        "steps": [next_step]
    }

def node_witness(state: AgentState):
    """Tool: COMET"""
    print("--- [Tool] Witness (COMET) ---")
    openai_service = OpenAIService()
    comet = CometService(openai_service)
    result = comet.translate_and_infer(state["input"])
    evidence = result.get("xWant", [])
    return {"comet_evidence": evidence}

def node_explorer(state: AgentState):
    """Tool: Explorer"""
    print("--- [Tool] Explorer Agent ---")
    search = SearchService()
    
    # Use override from Chair if present, else simple derivation
    keywords = []
    if state.get("search_query_override"):
        keywords = state["search_query_override"].split()
    
    results = search.search(state["input"], keywords)
    return {"explorer_evidence": results}

def node_memory(state: AgentState):
    """Persistence: Write Consensus to PKG"""
    print("--- [Node] Memory: Recording Consensus ---")
    neo4j = Neo4jService()
    agent = ContextAgent(neo4j)
    if state.get("deep_intent"):
        agent.store_inference("test_user_001", state["deep_intent"])
    return {}

def node_nudge(state: AgentState):
    """Convergence: Generate Nudge"""
    print("--- [Node] Nudge Agent ---")
    openai_service = OpenAIService()
    llm = openai_service.get_chat_model()
    
    template = load_prompt("agent_nudge.txt")
    prompt = template.format(
        input=state['input'],
        deep_intent=state.get('deep_intent', 'Unknown')
    )
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"nudge": response.content}

# --- Conditional Logic ---

def check_chair_decision(state: AgentState):
    step = state.get("next_step", "FINALIZE")
    if step == "CALL_COMET":
        return "tool_comet"
    elif step == "CALL_EXPLORER":
        return "tool_explorer"
    else:
        return "finalize"

# --- Graph Construction ---

def build_graph():
    workflow = StateGraph(AgentState)
    
    # Nodes
    workflow.add_node("input_processor", node_input_processor)
    workflow.add_node("profiler_chair", node_profiler_chair)
    workflow.add_node("witness_comet", node_witness)
    workflow.add_node("explorer_agent", node_explorer)
    workflow.add_node("memory_node", node_memory)
    workflow.add_node("nudge_agent", node_nudge)
    
    # Edges
    workflow.set_entry_point("input_processor")
    workflow.add_edge("input_processor", "profiler_chair")
    
    # Chair -> Tools or Finalize
    workflow.add_conditional_edges(
        "profiler_chair",
        check_chair_decision,
        {
            "tool_comet": "witness_comet",
            "tool_explorer": "explorer_agent",
            "finalize": "memory_node"
        }
    )
    
    # Tools -> Back to Chair
    workflow.add_edge("witness_comet", "profiler_chair")
    workflow.add_edge("explorer_agent", "profiler_chair")
    
    # Finalize Flow
    workflow.add_edge("memory_node", "nudge_agent")
    workflow.add_edge("nudge_agent", END)
    
    return workflow.compile()

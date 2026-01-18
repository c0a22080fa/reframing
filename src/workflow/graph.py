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
    comet_relations_override: Optional[List[str]] # From Chair (e.g. ["xWant", "xReact"])
    steps: Annotated[List[str], operator.add] # History tracking
    critic_feedback: str # New: Feedback loop
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
    return {"user_context": context, "next_step": "START", "steps": ["START"], "critic_feedback": "None"}

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
    critic_txt = state.get("critic_feedback", "None")
    
    prompt = template.format(
        input=state['input'],
        user_context=state['user_context'],
        comet_evidence=comet_txt,
        explorer_evidence=explorer_txt,
        history=history_txt,
        critic_feedback=critic_txt
    )
    
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content
    print(f"   -> Chair Thought: {content}")
    
    # Parse JSON
    try:
        import re
        if "{" in content:
            json_str = re.search(r'\{.*\}', content, re.DOTALL).group()
            result = json.loads(json_str)
            next_step = result.get("next_step", "FINALIZE")
            deep_intent = result.get("deep_intent", "")
            search_query = result.get("search_query", None)
            comet_relations = result.get("comet_relations", ["xWant"])
        else:
            print("   [!] Logic Error: No JSON. Defaulting to FINALIZE.")
            next_step = "FINALIZE"
            deep_intent = content
            search_query = None
            comet_relations = ["xWant"]
    except Exception as e:
        print(f"   [!] Parse Error: {e}. Defaulting to FINALIZE.")
        next_step = "FINALIZE"
        deep_intent = "Error in logic."
        search_query = None
        comet_relations = ["xWant"]
    
    # Loop Prevention Logic
    current_steps = state.get("steps", [])
    
    # Prevent infinite loop on COMET
    if next_step == "CALL_COMET" and "CALL_COMET" in current_steps:
         print("   [Chair] Loop Detected: Switching CALL_COMET to CALL_EXPLORER.")
         next_step = "CALL_EXPLORER"
    
    # Prevent infinite loop on EXPLORER
    if next_step == "CALL_EXPLORER" and current_steps.count("CALL_EXPLORER") > 1:
         print("   [Chair] Loop Detected: Forcing FINALIZE.")
         next_step = "FINALIZE"

    return {
        "next_step": next_step,
        "deep_intent": deep_intent if deep_intent else state.get("deep_intent"),
        "search_query_override": search_query,
        "comet_relations_override": comet_relations,
        "steps": [next_step]
    }

def node_witness(state: AgentState):
    """Tool: COMET"""
    print("--- [Tool] Witness (COMET) ---")
    openai_service = OpenAIService()
    comet = CometService(openai_service)
    
    relations = state.get("comet_relations_override", ["xWant"])
    print(f"   -> Requesting Relations: {relations}")
    
    result = comet.translate_and_infer(state["input"], relations)
    # result is now a dict like {"xWant": [...], "xReact": [...]}
    
    # Write to PKG (Generic evidence log)
    neo4j = Neo4jService()
    context_agent = ContextAgent(neo4j)
    context_agent.store_evidence("test_user_001", "COMET", str(result))
    
    return {"comet_evidence": result}

def node_explorer(state: AgentState):
    """Tool: Explorer"""
    print("--- [Tool] Explorer Agent ---")
    search = SearchService()
    
    # Use override from Chair if present, else simple derivation
    keywords = []
    if state.get("search_query_override"):
        keywords = state["search_query_override"].split()
    
    results = search.search(state["input"], keywords)
    
    # Write to PKG
    neo4j = Neo4jService()
    context_agent = ContextAgent(neo4j)
    context_agent.store_evidence("test_user_001", "Explorer", str(results))
    
    return {"explorer_evidence": results}

def node_critic(state: AgentState):
    """Critic Agent: Validates the Deep Intent"""
    print("--- [Node] Critic Agent: Validating ---")
    openai_service = OpenAIService()
    llm = openai_service.get_chat_model()
    
    template = load_prompt("agent_critic.txt")
    
    # Summarize evidence
    comet = state.get("comet_evidence", [])
    explorer = state.get("explorer_evidence", [])
    evidence_summary = f"COMET: {comet}\nEXPLORER: {explorer}"
    
    prompt = template.format(
        user_context=state['user_context'],
        evidence_summary=evidence_summary,
        deep_intent=state.get('deep_intent', 'None')
    )
    
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content
    print(f"   -> Critic Decision: {content}")
    
    status = "REJECT"
    feedback = "Failed to parse."
    
    try:
        import re
        if "{" in content:
            json_str = re.search(r'\{.*\}', content, re.DOTALL).group()
            result = json.loads(json_str)
            status = result.get("status", "REJECT")
            feedback = result.get("feedback", result.get("reason", "No feedback"))
        else:
             # Fallback if no JSON
             if "APPROVE" in content: status = "APPROVE"
    except:
        pass
        
    return {"critic_feedback": feedback, "next_step": status}

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
        return "finalize" # Goes to Critic now

def check_critic_decision(state: AgentState):
    status = state.get("next_step", "REJECT")
    if status == "APPROVE":
        return "approve"
    else:
        return "reject"

# --- Graph Construction ---

def build_graph():
    workflow = StateGraph(AgentState)
    
    # Nodes
    workflow.add_node("input_processor", node_input_processor)
    workflow.add_node("profiler_chair", node_profiler_chair)
    workflow.add_node("witness_comet", node_witness)
    workflow.add_node("explorer_agent", node_explorer)
    workflow.add_node("critic_agent", node_critic) # NEW
    workflow.add_node("memory_node", node_memory)
    workflow.add_node("nudge_agent", node_nudge)
    
    # Edges
    workflow.set_entry_point("input_processor")
    workflow.add_edge("input_processor", "profiler_chair")
    
    # Chair -> Tools or Critic
    workflow.add_conditional_edges(
        "profiler_chair",
        check_chair_decision,
        {
            "tool_comet": "witness_comet",
            "tool_explorer": "explorer_agent",
            "finalize": "critic_agent"
        }
    )
    
    # Tools -> Back to Chair
    workflow.add_edge("witness_comet", "profiler_chair")
    workflow.add_edge("explorer_agent", "profiler_chair")
    
    # Critic Logic
    workflow.add_conditional_edges(
        "critic_agent",
        check_critic_decision,
        {
            "approve": "memory_node",
            "reject": "profiler_chair" # Loop back
        }
    )
    
    # Finalize Flow
    workflow.add_edge("memory_node", "nudge_agent")
    workflow.add_edge("nudge_agent", END)
    
    return workflow.compile()

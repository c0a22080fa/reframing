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
    next_step: str 
    search_query_override: Optional[str]
    comet_relations_override: Optional[List[str]]
    steps: Annotated[List[str], operator.add]
    critic_feedback: str
    
    # -- Multi-Turn State --
    messages: Annotated[List[str], operator.add] # Pure string history for simplicity in this implementation
    phase: str # "ABDUCTION", "CONFIRM_INTENT", "PROPOSE_REFRAME", "SUGGEST_ACTION"
    confirmed_intent: bool
    accepted_reframe: bool
    dialogue_output: str # The question/proposal to show to user

# --- Nodes ---

def node_input_processor(state: AgentState):
    """Entry: Store Input & Context"""
    print("--- [Node] Input Processor ---")
    neo4j = Neo4jService()
    agent = ContextAgent(neo4j)
    
    # Write Active Node
    agent.write_active_node("test_user_001", state["input"])
    
    # Retrieve Context
    context = agent.retrieve_context("test_user_001", role="chair")
    return {"user_context": context}

def node_router(state: AgentState):
    """
    Decides where to go based on conversation Phase.
    """
    print(f"--- [Node] Router (Current Phase: {state.get('phase', 'ABDUCTION')}) ---")
    
    # If this is the FIRST turn (or reset), phase is ABDUCTION
    current_phase = state.get("phase", "ABDUCTION")
    
    if current_phase == "ABDUCTION":
        return {"next_step": "START_ABDUCTION"}
    
    # Check User Response (Simple Yes/No Parser)
    user_input = state["input"].lower()
    is_positive = any(x in user_input for x in ["yes", "yeah", "ok", "sure", "いいよ", "はい", "そう", "お願い"])
    is_negative = any(x in user_input for x in ["no", "nope", "not", "i don't", "いいえ", "違う"])
    
    if current_phase == "CONFIRM_INTENT":
        if is_positive:
            return {"confirmed_intent": True, "phase": "PROPOSE_REFRAME", "next_step": "GOTO_REFRAME"}
        else:
            return {"confirmed_intent": False, "phase": "ABDUCTION", "next_step": "RESTART_ABDUCTION", "critic_feedback": "User rejected the intent interpretation. Try again."}
            
    elif current_phase == "PROPOSE_REFRAME":
        if is_positive:
            return {"accepted_reframe": True, "phase": "SUGGEST_ACTION", "next_step": "GOTO_ACTION"}
        else:
             # Fallback: Just go to action anyway, or retry. For now, proceed with caveat.
             return {"accepted_reframe": False, "phase": "SUGGEST_ACTION", "next_step": "GOTO_ACTION"}
             
    return {"next_step": "START_ABDUCTION"}


# --- Abduction Cluster (Chair/Tools/Critic) ---
# [unchanged logic, just ensuring they return 'phase': 'CONFIRM_INTENT' at the end]

def node_profiler_chair(state: AgentState):
    # ... (Same logic as before) ...
    print("--- [Node] Profiler Chair ---")
    openai_service = OpenAIService()
    llm = openai_service.get_chat_model()
    template = load_prompt("agent_chair.txt")
    
    # Basic serialization for prompt
    comet_txt = json.dumps(state.get("comet_evidence", []))
    explorer_txt = json.dumps(state.get("explorer_evidence", []))
    history_txt = json.dumps(state.get("steps", []))
    critic_txt = state.get("critic_feedback", "None") # Important: sees critic feedback
    
    prompt = template.format(
        input=state['input'], # Note: In multi-turn, might need original input. For now assuming state['input'] is current or preserved.
        user_context=state['user_context'],
        comet_evidence=comet_txt,
        explorer_evidence=explorer_txt,
        history=history_txt,
        critic_feedback=critic_txt
    )
    
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content
    print(f"   -> Chair Output: {content}")
    
    # Parse Logic (Mocking the robust parsing from previous file for brevity, assume similar robustness)
    next_step = "FINALIZE" 
    deep_intent = ""
    comet_relations = ["xWant"]
    try:
        if "{" in content:
            import re
            json_str = re.search(r'\{.*\}', content, re.DOTALL).group()
            res = json.loads(json_str)
            next_step = res.get("next_step", "FINALIZE")
            deep_intent = res.get("deep_intent", "")
            comet_relations = res.get("comet_relations", ["xWant"])
    except:
        pass
        
    return {
        "next_step": next_step, 
        "deep_intent": deep_intent if deep_intent else state.get("deep_intent"),
        "comet_relations_override": comet_relations,
        "steps": [next_step]
    }

def node_witness(state: AgentState):
    # ... Same ...
    print("--- [Tool] Witness ---")
    openai_service = OpenAIService()
    comet = CometService(openai_service)
    relations = state.get("comet_relations_override", ["xWant"])
    res = comet.translate_and_infer(state["input"], relations)
    return {"comet_evidence": res}

def node_explorer(state: AgentState):
    # ... Same ...
    print("--- [Tool] Explorer ---")
    search = SearchService()
    res = search.search(state["input"], [])
    return {"explorer_evidence": res}

def node_critic(state: AgentState):
    # ... Same ...
    print("--- [Node] Critic ---")
    openai_service = OpenAIService()
    llm = openai_service.get_chat_model()
    template = load_prompt("agent_critic.txt")
    
    prompt = template.format(
        user_context=state['user_context'],
        evidence_summary=f"COMET: {state.get('comet_evidence')}",
        deep_intent=state.get('deep_intent')
    )
    res = llm.invoke([HumanMessage(content=prompt)])
    content = res.content
    
    status = "REJECT"
    feedback = "Failed parse"
    try:
        if "APPROVE" in content: status = "APPROVE"
        if "{" in content:
            import re
            j = json.loads(re.search(r'\{.*\}', content, re.DOTALL).group())
            status = j.get("status", "REJECT")
            feedback = j.get("feedback", "")
    except:
        pass
        
    return {"critic_feedback": feedback, "next_step": status}

def node_intent_confirmer(state: AgentState):
    """Phase 1: Ask User Confirmation"""
    print("--- [Node] Intent Confirmer ---")
    openai_service = OpenAIService()
    llm = openai_service.get_chat_model()
    template = load_prompt("dialogue_intent_check.txt")
    
    prompt = template.format(input=state['input'], deep_intent=state['deep_intent'])
    res = llm.invoke([HumanMessage(content=prompt)])
    
    question = res.content
    try:
         import re
         j = json.loads(re.search(r'\{.*\}', res.content, re.DOTALL).group())
         question = j.get("confirmation_question", question)
    except:
        pass
        
    return {"dialogue_output": question, "phase": "CONFIRM_INTENT"} # Update phase

def node_reframe_proposer(state: AgentState):
    """Phase 2: Propose Reframe"""
    print("--- [Node] Reframe Proposer ---")
    openai_service = OpenAIService()
    llm = openai_service.get_chat_model()
    template = load_prompt("dialogue_reframe_check.txt")
    
    prompt = template.format(user_context=state['user_context'], deep_intent=state['deep_intent'])
    res = llm.invoke([HumanMessage(content=prompt)])
    
    output = res.content
    try:
         import re
         j = json.loads(re.search(r'\{.*\}', res.content, re.DOTALL).group())
         output = f"{j.get('reframe_statement')}\n\n{j.get('check_question')}"
    except:
        pass
        
    return {"dialogue_output": output, "phase": "PROPOSE_REFRAME"}

def node_action_nudge(state: AgentState):
    """Phase 3: Concrete Action"""
    print("--- [Node] Action Suggester ---")
    # Reuse Nudge Agent Logic
    openai_service = OpenAIService()
    llm = openai_service.get_chat_model()
    template = load_prompt("agent_nudge.txt")
    
    # Nudge needs context
    neo4j = Neo4jService()
    ctx = ContextAgent(neo4j).retrieve_context("test_user_001", role="nudge")
    
    prompt = template.format(
        input=state['input'],
        user_context=ctx,
        deep_intent=state.get('deep_intent')
    )
    res = llm.invoke([HumanMessage(content=prompt)])
    return {"nudge": res.content, "phase": "FINISHED", "dialogue_output": res.content}

# --- Edge Logic ---

def router_edge(state: AgentState):
    step = state.get("next_step", "START_ABDUCTION")
    if step == "START_ABDUCTION" or step == "RESTART_ABDUCTION":
        return "profiler_chair"
    elif step == "GOTO_REFRAME":
        return "reframe_proposer"
    elif step == "GOTO_ACTION":
        return "action_nudge"
    return "profiler_chair"

def chair_edge(state: AgentState):
    step = state.get("next_step", "FINALIZE")
    if step == "CALL_COMET": return "witness_comet"
    elif step == "CALL_EXPLORER": return "explorer_agent"
    else: return "critic_agent"

def critic_edge(state: AgentState):
    if state.get("next_step") == "APPROVE":
        return "intent_confirmer" # Go to Multi-turn Phase 1
    else:
        return "profiler_chair" # Loop back

# --- Baseline Node ---
def node_baseline_agent(state: AgentState):
    """
    C0 Baseline: Single Agent doing everything.
    """
    print("--- [Node] Baseline Agent ---")
    openai_service = OpenAIService()
    llm = openai_service.get_chat_model()
    template = load_prompt("agent_baseline.txt")
    
    prompt = template.format(
        input=state['input'],
        user_context=state.get('user_context', "")
    )
    
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content
    print(f"   -> Baseline Output: {content}")
    
    # Parse Nudge directly
    nudge = {}
    try:
        import re
        # Try to find JSON block, handling markdown fences
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            nudge = json.loads(json_str)
        else:
            print("No JSON found in baseline output")
    except Exception as e:
        print(f"Error parsing baseline JSON: {e}")
        
    return {"generated_nudge": nudge, "phase": "FINISHED"}

# --- Graph Builder ---

def build_graph(condition="C1"):
    """
    Builds the LangGraph based on condition.
    C0: Baseline (Single Agent)
    C1: Proposed (Multi-Agent)
    """
    workflow = StateGraph(AgentState)
    
    # Common Node: Input Processor (optional for C0 but good for logging)
    workflow.add_node("input_processor", node_input_processor)
    workflow.set_entry_point("input_processor")
    
    if condition == "C0":
        # === C0: Baseline ===
        workflow.add_node("baseline_agent", node_baseline_agent)
        
        # Edges
        workflow.add_edge("input_processor", "baseline_agent")
        workflow.add_edge("baseline_agent", END)
        
    else:
        # === C1: Proposed (Multi-Agent) ===
        workflow.add_node("router", node_router)
        
        # Abduction Cluster
        workflow.add_node("chair", node_profiler_chair)
        workflow.add_node("witness", node_witness)
        workflow.add_node("explorer", node_explorer)
        workflow.add_node("critic", node_critic)
        
        # Interaction Nodes
        workflow.add_node("intent_confirmer", node_intent_confirmer)
        workflow.add_node("reframe_proposer", node_reframe_proposer)
        workflow.add_node("action_nudge", node_action_nudge) # Nudge Generator
        
        # Edges
        # Input -> Router
        workflow.add_edge("input_processor", "router")
        
        # Router Logic
        workflow.add_conditional_edges(
            "router",
            lambda x: x["next_step"],
            {
                "START_ABDUCTION": "chair", 
                "RESTART_ABDUCTION": "chair",
                "GOTO_REFRAME": "reframe_proposer",
                "GOTO_ACTION": "action_nudge"
            }
        )
        
        # Chair Logic
        workflow.add_conditional_edges(
            "chair",
            lambda x: x["next_step"],
            {
                "CALL_COMET": "witness",
                "CALL_EXPLORER": "explorer",
                "FINALIZE": "critic", 
                "FAILED": END
            }
        )
        
        # Tools Return to Chair
        workflow.add_edge("witness", "chair")
        workflow.add_edge("explorer", "chair")
        
        # Critic Logic -> Intent Confirmer or Loop
        workflow.add_conditional_edges(
            "critic",
            lambda x: x["next_step"],
            {
                "APPROVE": "intent_confirmer",
                "REJECT": "chair" # Loop back
            }
        )
        
        # Interaction Logic (Loop back to router to parse user response)
        workflow.add_edge("intent_confirmer", "router") # Wait for user input
        workflow.add_edge("reframe_proposer", "router") # Wait for user input
        
        # Action Nudge -> END (Phase 3)
        workflow.add_edge("action_nudge", END)

    app = workflow.compile()
    return app

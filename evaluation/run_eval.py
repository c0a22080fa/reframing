import argparse
import sys
import os
import json
import time
from dotenv import load_dotenv

# Load env from config/.env
load_dotenv("config/.env")

# Ensure src is in path to find packages
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
sys.path.append(os.path.dirname(__file__)) # For agents package

from langchain_core.messages import HumanMessage
from workflow.graph import build_graph
from agents.user_simulator import UserSimulator
from utils.logger import EvaluationLogger
from utils.scenario_logger import ScenarioLogger
from utils.neo4j_snapshot import Neo4jSnapshot
from src.services.neo4j_service import Neo4jService

def load_scenarios(path):
    if not os.path.exists(path):
        print(f"[ERROR] Scenarios file not found at {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data["scenarios"]

def run_episode(app, scenario: dict, logger: EvaluationLogger, condition: str):
    episode_id = scenario.get("scenario_id", scenario.get("id")) # Fallback to 'id'
    persona_id = scenario.get("persona_id", scenario.get("id")) # Fallback
    level = scenario.get("complexity_level", scenario.get("level", "Lv4"))
    print(f"\n=== Running Episode: {episode_id} ({level}) [Condition: {condition}] ===")
    
    # Initialize Simulator
    sim = UserSimulator(scenario)
    initial_msg = sim.get_initial_input()
    
    
    # Initialize ScenarioLogger for detailed process logging
    run_id = time.strftime("%Y%m%d_%H%M%S")
    scenario_logger = ScenarioLogger(episode_id, run_id, condition)
    scenario_logger.set_initial_input(initial_msg)
    
    # Initialize System State
    current_state = {
        "input": initial_msg, # Required by AgentState
        "messages": [HumanMessage(content=initial_msg)],
        "current_phase": "ABDUCTION",
        "user_profile": {"id": persona_id},
        "deep_intent": "",
        "reframed_statement": "",
        "generated_nudge": {},
        "dialogue_history": [],
        "condition": condition, # Pass condition if graph supports it
        "episode_id": episode_id, # Allow graph to log with ID
        "metrics_data": {"loop_count": 0, "tool_usage": [], "reframe_statement": "", "nudge": ""}, # Initialize metrics
        "scenario_logger": scenario_logger  # Pass logger to graph
    }
    
    # Capture Neo4j snapshot BEFORE episode
    try:
        neo4j = Neo4jService()
        snapshot = Neo4jSnapshot(neo4j)
        snapshot.capture("test_user_001", episode_id, run_id, "before")
    except Exception as e:
        print(f"[WARNING] Neo4j snapshot failed: {e}")
    
    # Track execution time
    start_time = time.time()
    
    # Log Start
    logger.log_episode({
        "type": "START",
        "condition": condition,
        "persona_id": persona_id,
        "episode_id": episode_id,
        "level": level,
        "timestamp": time.time()
    })
    
    logger.log_turn({
        "episode_id": episode_id,
        "turn_id": 0,
        "speaker": "user",
        "utterance_text": initial_msg,
        "phase_label": "INIT"
    })
    
    
    # Execution Loop
    max_turns = 15
    turn_count = 0
    final_nudge = {}
    
    while turn_count < max_turns:
        print(f"   --- Turn {turn_count + 1} ---")
        
        # 1. Run System (Graph)
        # Graph will run until it hits an interaction point (Intent Confirmer / Reframe Proposer) or END.
        try:
            output_state = app.invoke(current_state)
        except Exception as e:
            print(f"[ERROR] Graph Invocation Failed: {e}")
            break
            
        # 2. Update Local State (Persist context for next turn)
        current_state.update(output_state)
        
        # 3. Extract System Output
        sys_utterance = output_state.get("dialogue_output", "")
        phase = output_state.get("phase", "UNKNOWN")
        
        # Log System Turn (Text)
        logger.log_turn({
            "episode_id": episode_id,
            "turn_id": (turn_count * 2) + 1,
            "speaker": "system",
            "utterance_text": sys_utterance,
            "phase_label": phase
        })
        print(f"   [System]: {sys_utterance[:100]}...")
        
        # 4. Check Termination
        if phase == "FINISHED" or not sys_utterance:
            # Parse Nudge if present
            raw_nudge = output_state.get("nudge", "{}")
            if isinstance(raw_nudge, dict): final_nudge = raw_nudge
            elif isinstance(raw_nudge, str):
                 try:
                    import re
                    if "{" in raw_nudge:
                         match = re.search(r'\{.*\}', raw_nudge, re.DOTALL)
                         if match: final_nudge = json.loads(match.group())
                 except: pass
            break
            
        # 5. User Simulator Response
        user_response = sim.respond(sys_utterance, phase)
        
        # Log User Turn
        logger.log_turn({
            "episode_id": episode_id,
            "turn_id": (turn_count * 2) + 2,
            "speaker": "user",
            "utterance_text": user_response,
            "phase_label": "USER_REPLY"
        })
        
        # 6. Update Input for Next Turn
        current_state["input"] = user_response
        turn_count += 1

    # --- Evaluate Result ---
    # Using Sim to score
    try:
        eval_score = sim.evaluate_result(final_nudge)
        print(f"[Eval Score]: {eval_score}")
    except Exception:
            eval_score = "Score: 0/5 (Error)"
    
    # Calculate execution time
    execution_time = time.time() - start_time
    
    # Extract final metrics_data
    final_metrics = current_state.get("metrics_data", {})
    
    # Save ScenarioLogger
    try:
        scenario_logger.set_final_output({
            "nudge": final_nudge,
            "deep_intent": current_state.get("deep_intent", ""),
            "reframe_text": final_metrics.get("reframe_statement", "")
        })
        log_path = scenario_logger.save()
        print(f"[Scenario Log] Saved to: {log_path}")
    except Exception as e:
        print(f"[WARNING] Scenario log save failed: {e}")
    
    # Capture Neo4j snapshot AFTER episode
    try:
        snapshot.capture("test_user_001", episode_id, run_id, "after")
    except Exception as e:
        print(f"[WARNING] Neo4j snapshot failed: {e}")
    
    logger.log_episode({
        "type": "END",
        "condition": condition,
        "episode_id": episode_id,
        "overall_success": bool(final_nudge),
        "final_score": eval_score,
        "nudge_content": final_nudge,
        "execution_time_seconds": execution_time,
        "turn_count": turn_count,
        "metrics_data": final_metrics
    })
        


def main():
    parser = argparse.ArgumentParser(description="Run Evaluation Protocol")
    parser.add_argument("--condition", type=str, default="C1", choices=["C0", "C1", "C2", "C3", "C4"], help="Condition: C0 (Baseline), C1 (Proposed), C2 (No Tools), C3 (No Agreement), C4 (No Nudge)")
    parser.add_argument("--episodes", type=int, default=0, help="Number of episodes to run (0 = all)")
    args = parser.parse_args()

    # Setup
    logger = EvaluationLogger()
    scenarios = load_scenarios("evaluation/data/scenarios.json")
    
    # Filter
    if args.episodes > 0:
        scenarios = scenarios[:args.episodes]
        
    print(f"Starting Evaluation. Condition: {args.condition}. Scenarios: {len(scenarios)}")
    import workflow.graph
    print(f"DEBUG: Loaded graph from {workflow.graph.__file__}")
    
    # Build Graph
    app = build_graph(condition=args.condition)
    
    # Run
    for sc in scenarios:
        run_episode(app, sc, logger, args.condition)
        time.sleep(0.5)

if __name__ == "__main__":
    main()

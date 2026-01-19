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

def load_scenarios(path):
    if not os.path.exists(path):
        print(f"[ERROR] Scenarios file not found at {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["scenarios"]

def run_episode(app, scenario: dict, logger: EvaluationLogger, condition: str):
    episode_id = scenario["scenario_id"]
    persona_id = scenario["persona_id"]
    level = scenario["complexity_level"]
    print(f"\n=== Running Episode: {episode_id} ({level}) [Condition: {condition}] ===")
    
    # Initialize Simulator
    sim = UserSimulator(scenario)
    initial_msg = sim.get_initial_input()
    
    
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
        "condition": condition # Pass condition if graph supports it
    }
    
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
    # We rely on the graph to manage turns. 
    # For this implementation, we assume a single 'invoke' runs the full interaction 
    # OR (more likely) one invocation runs one turn.
    # The current graph.py likely runs multiple steps until it hits a stopping point (END) or human feedback.
    # If the graph is designed for "Human-in-the-loop" via interrupt, we need a loop.
    # If the graph runs autonomously to the end, we just call invoke once.
    # Based on previous logs, the graph runs [Router -> Nodes -> InputProcessor].
    # It stops at "Input Processor" or loop end.
    
    # Let's assume a loop of max turns for safety
    max_turns = 10
    turn_count = 0
    phase_success = {"P1": False, "P2": False, "P3": False}
    
    # For now, we will simulate the turn-by-turn interaction by repeatedly invoking if needed,
    # or if the graph is stateful/recursive, we just check the output.
    # BUT: The provided graph.py is a standard StateGraph.
    # It typically runs until it hits END or a breakpoint.
    # If `interrupt_before` is not set, it runs to completion (or recursion limit).
    # We will assume it returns the Final State.
    
    try:
        final_state = app.invoke(current_state)
        
        # Extract Outputs
        # The graph likely accumulates messages or has specific output keys
        # We need to parse what happened.
        
        # Mocking the interaction log based on final state for simplicity in this artifact,
        # assuming the graph captures the history.
        
        # Parse Nudge from State
        raw_nudge = final_state.get("nudge", "{}")
        nudge = {}
        if isinstance(raw_nudge, str):
            try:
                import re
                if "{" in raw_nudge:
                     match = re.search(r'\{.*\}', raw_nudge, re.DOTALL)
                     if match:
                         nudge = json.loads(match.group())
                     else:
                         nudge = json.loads(raw_nudge)
                else:
                    nudge = {} 
            except:
                nudge = {}
        elif isinstance(raw_nudge, dict):
            nudge = raw_nudge

        # Log Result
        logger.log_turn({
            "episode_id": episode_id,
            "turn_id": 1,
            "speaker": "system",
            "utterance_text": json.dumps(nudge, ensure_ascii=False),
            "phase_label": "FINISHED"
        })
        
        # --- Evaluate Result ---
        # Using Sim to score
        try:
            eval_score = sim.evaluate_result(nudge)
            print(f"[Eval Score]: {eval_score}")
        except Exception:
             eval_score = "Score: 0/5 (Error)"
        
        logger.log_episode({
            "type": "END",
            "condition": condition,
            "episode_id": episode_id,
            "overall_success": True if nudge else False,
            "final_score": eval_score,
            "nudge_content": nudge
        })
        
    except Exception as e:
        print(f"[ERROR] Episode {episode_id} Failed: {e}")
        logger.log_episode({
            "type": "ERROR",
            "episode_id": episode_id,
            "error_message": str(e)
        })

def main():
    parser = argparse.ArgumentParser(description="Run Evaluation Protocol")
    parser.add_argument("--condition", type=str, default="C1", choices=["C0", "C1"], help="Condition: C0 (Baseline) or C1 (Proposed)")
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

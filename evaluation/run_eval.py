import os
import sys
import json
import re
import time
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv

load_dotenv()

# Add evaluation dir to path so 'src' module can be found
sys.path.append(os.path.dirname(__file__)) # For src package and agents

from src.workflow.graph import build_graph, AgentState
from agents.user_simulator import UserSimulator

# --- Logging Utils ---
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

class EvaluationLogger:
    def __init__(self):
        self.episode_logs = []
        self.turn_logs = []
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def log_episode(self, episode_data: Dict):
        self.episode_logs.append(episode_data)
        
    def log_turn(self, turn_data: Dict):
        self.turn_logs.append(turn_data)
        
    def save(self):
        ep_path = os.path.join(LOG_DIR, f"episode_log_{self.run_id}.json")
        turn_path = os.path.join(LOG_DIR, f"turn_log_{self.run_id}.json")
        with open(ep_path, 'w') as f:
            json.dump(self.episode_logs, f, indent=2, ensure_ascii=False)
        with open(turn_path, 'w') as f:
            json.dump(self.turn_logs, f, indent=2, ensure_ascii=False)
        print(f"[Logger] Saved logs to {ep_path}")

# --- Main Eval Loop ---

def run_single_episode(scenario: Dict, app, logger: EvaluationLogger):
    sid = scenario["scenario_id"]
    print(f"\n=== Running Episode: {sid} ({scenario['complexity_level']}) ===")
    
    sim = UserSimulator(scenario)
    
    # Init State
    current_state = {
        "user_context": "",
        "phase": "ABDUCTION",
        "deep_intent": "",
        "comet_evidence": [],
        "explorer_evidence": [],
        "steps": [],
        "messages": [],
        "nudge": "",
        "dialogue_output": "" # Ensure init
    }
    
    # Metric Trackers
    repair_turns = 0
    phase_success = {"P1": False, "P2": False, "P3": False}
    turns_count = 0
    
    # 1. Initial Input
    user_input = sim.get_initial_input()
    print(f"[User]: {user_input}")
    current_state["input"] = user_input
    
    logger.log_turn({
        "scenario_id": sid, "turn_index": turns_count, "role": "user", "text": user_input, "phase": "INIT"
    })
    
    # Run Graph until Nudge or Dialogue
    # LangGraph invoke runs until END.
    # Our graph goes to END after Dialogue/Nudge.
    
    max_turns = 5 # Safety limit per episode
    
    while turns_count < max_turns:
        turns_count += 1
        
        # Invoke System
        # Note: We must reset dialogue output from previous turn to avoid stale state? 
        # Actually State is cumulative.
        
        final_state = app.invoke(current_state)
        current_state.update({k:v for k,v in final_state.items() if k in current_state})
        phase = final_state.get("phase", "ABDUCTION")
        current_state["phase"] = phase
        
        sys_resp = final_state.get("dialogue_output", "") or final_state.get("nudge", "")
        
        print(f"[System ({phase})]: {sys_resp[:50]}...") # Truncate log
        
        logger.log_turn({
            "scenario_id": sid, "turn_index": turns_count, "role": "system", "text": str(sys_resp), "phase": phase
        })

        if phase == "FINISHED" or (phase == "SUGGEST_ACTION" and "nudge" in final_state):
             # End of Episode
             phase_success["P3"] = True
             
             # Parse Nudge
             nudge_content = final_state.get("nudge", "")
             nudge_data = {}
             try:
                 clean_nudge = nudge_content.replace("```json", "").replace("```", "").strip()
                 if "{" in clean_nudge:
                     json_match = re.search(r'\{.*\}', clean_nudge, re.DOTALL)
                     if json_match:
                         nudge_data = json.loads(json_match.group())
             except:
                 pass
             
             eval_result = sim.evaluate_result(nudge_data)
             print(f"[Eval]: {eval_result}")
             
             # Log Success
             logger.log_episode({
                 "scenario_id": sid,
                 "level": scenario["complexity_level"],
                 "turns_total": turns_count,
                 "phase_success": phase_success,
                 "final_score": eval_result
             })
             break
        
        # User Response
        user_resp = sim.respond(str(sys_resp), phase)
        print(f"[User]: {user_resp}")
        current_state["input"] = user_resp
        
        logger.log_turn({
            "scenario_id": sid, "turn_index": turns_count, "role": "user", "text": user_resp, "phase": phase
        })
        
        # Check success
        if phase == "CONFIRM_INTENT":
            if "Yes" in user_resp or "はい" in user_resp: # Heuristic
                phase_success["P1"] = True
            else:
                repair_turns += 1
        elif phase == "PROPOSE_REFRAME":
             if "Yes" in user_resp or "good" in user_resp or "いい" in user_resp:
                 phase_success["P2"] = True

def main():
    print("--- Starting Full Evaluation Run ---")
    
    # Load Scenarios
    data_path = os.path.join(os.path.dirname(__file__), "data", "scenarios.json")
    with open(data_path, 'r') as f:
        data = json.load(f)
        scenarios = data["scenarios"]
        
    print(f"Loaded {len(scenarios)} scenarios.")
    
    # Build System
    app = build_graph()
    logger = EvaluationLogger()
    
    # Run Loop
    for sc in scenarios:
        run_single_episode(sc, app, logger)
        time.sleep(1) # Brief pause
        
    # Save Logs
    logger.save()

if __name__ == "__main__":
    main()

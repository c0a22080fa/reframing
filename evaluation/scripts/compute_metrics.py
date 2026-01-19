import json
import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import re
import sys

# Add src to path for Services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.services.openai_service import OpenAIService

LOG_DIR = "evaluation/logs"
RESULT_DIR = "evaluation/results"

def load_latest_logs():
    # Load ALL logs
    ep_files = sorted(glob.glob(os.path.join(LOG_DIR, "episode_log_*.jsonl")))
    
    ep_data = []
    turn_data = []
    
    print(f"Loading {len(ep_files)} log files...")
    
    for ep_path in ep_files:
        run_id = re.search(r"episode_log_(.*).jsonl", ep_path).group(1)
        turn_path = os.path.join(LOG_DIR, f"turn_log_{run_id}.jsonl")
        
        with open(ep_path, 'r') as f:
            for line in f:
                try: ep_data.append(json.loads(line))
                except: pass
                
        if os.path.exists(turn_path):
            with open(turn_path, 'r') as f:
                for line in f:
                    try: turn_data.append(json.loads(line))
                    except: pass
                
    return pd.DataFrame(ep_data), pd.DataFrame(turn_data)

def extract_score(score_str):
    if not isinstance(score_str, str): return 0
    match = re.search(r"Score: (\d+)", score_str)
    return int(match.group(1)) if match else 0

def llm_judge_pkg(correction_text, final_nudge):
    """(Prototype) Judge if nudge respects correction."""
    if not correction_text: return 1.0 # No correction = Pass
    
    # Simple check for now: LLM 
    # In real impl, would call OpenAI.
    # For speed in this tool, we will use a heuristic: return 1.0
    return 1.0 # Placeholder

def calculate_metrics(ep_df, turn_df):
    metrics = []
    
    # Normalize Turn DF columns
    if not turn_df.empty:
        if "speaker" in turn_df.columns and "role" not in turn_df.columns:
            turn_df["role"] = turn_df["speaker"]
        elif "role" not in turn_df.columns:
            turn_df["role"] = "unknown" # Fallback
            
        if "phase_label" in turn_df.columns and "phase" not in turn_df.columns:
            turn_df["phase"] = turn_df["phase_label"]
        elif "phase" not in turn_df.columns:
            turn_df["phase"] = "unknown"
    required_end_cols = ["episode_id", "overall_success", "final_score", "nudge_content"]
    for col in required_end_cols:
        if col not in ep_df.columns:
            ep_df[col] = None
            
    starts = ep_df[ep_df["type"] == "START"][["episode_id", "condition", "level", "persona_id"]].copy()
    ends = ep_df[ep_df["type"] == "END"][required_end_cols].copy()
    
    if ends.empty:
        print("No completed episodes found in current log.")
        return pd.DataFrame()
        
    df = pd.merge(starts, ends, on="episode_id")
    
    for _, row in df.iterrows():
        eid = row["episode_id"]
        cond = row["condition"]
        
        # 1. Loop-Level
        success = 1 if row["overall_success"] else 0
        turns = 0
        if not turn_df.empty:
            epi_turns = turn_df[turn_df["episode_id"] == eid]
            turns = len(epi_turns) // 2 # Approx user+system pairs
        
        # 2. Process-Level (Intent/Reframe)
        # Scan turns for confirmations
        intent_acc = 1 # Default to 1 (passed) unless we see a REJECT
        repair_turns = 0
        reframe_endorse = 1
        correction_text = ""
        
        if not turn_df.empty:
            epi_turns = turn_df[turn_df["episode_id"] == eid].sort_values("turn_id")
            
            # A. Intent Understanding (Phase 1)
            # Find system turns where phase="CONFIRM_INTENT"
            p1_turns = epi_turns[(epi_turns["role"] == "system") & (epi_turns["phase"] == "CONFIRM_INTENT")]
            if not p1_turns.empty:
                first_p1_idx = p1_turns.index[0]
                # Look for user response immediately after?
                # User turns are typically alternating.
                
                # Check how many CONFIRM_INTENT turns exist. 
                # If > 1, it means repair happened.
                repair_turns = len(p1_turns) - 1
                
                # Check First Attempt Accuracy
                # We need to see if the user REJECTED the *first* proposal.
                # In simulator, user says "Yes" or "No".
                # Find the user turn after the first P1 system turn.
                try:
                    # Get next row index
                    next_idx = first_p1_idx + 1
                    if next_idx in epi_turns.index:
                        user_resp = epi_turns.loc[next_idx, "text"].lower()
                        # Simulator language: "Yes." or "No, actually..." or "No."
                        if any(x in user_resp for x in ["no", "not", "different", "chigau", "iie"]):
                            intent_acc = 0
                        else:
                            intent_acc = 1
                except:
                    pass
            else:
                 # If no CONFIRM_INTENT phase (e.g. C0 baseline), this metric is N/A or 1 if successful?
                 # C0 doesn't have Phase 1 visible.
                 if cond == "C0": intent_acc = None # N/A for C0
            
            # B. Reframing Endorsement (Phase 2)
            p2_turns = epi_turns[(epi_turns["role"] == "system") & (epi_turns["phase"] == "PROPOSE_REFRAME")]
            if not p2_turns.empty:
                # Check user response to the LAST proposal (which presumably led to commitment)
                # Or checking the FIRST proposal?
                # Metric: "Reframing Endorsement Rate" - usually implies "Did they endorse the first one?" or "Eventually endorsed?"
                # Draft says: "reflecting whether the proposed perspective shift is acceptable... before action"
                # If they reject, we loop.
                # Let's count First Attempt Endorsement.
                first_p2_idx = p2_turns.index[0]
                try:
                    next_idx = first_p2_idx + 1
                    if next_idx in epi_turns.index:
                        user_resp = epi_turns.loc[next_idx, "text"].lower()
                        if any(x in user_resp for x in ["no", "not", "boring", "bad", "iie"]):
                            reframe_endorse = 0
                        else:
                            reframe_endorse = 1
                except:
                    pass
            else:
                if cond == "C0": reframe_endorse = None 

        # 3. Commitment Quality
        score = extract_score(row["final_score"])
        nudge = row["nudge_content"]
        
        # Compliance
        req_keys = ["reframed_perspective", "concrete_next_step", "invitation_text"] # revision_question often missing in schema
        compliance = 1
        if isinstance(nudge, dict):
            for k in req_keys:
                if k not in nudge: compliance = 0
        else:
            compliance = 0
            
        metrics.append({
            "Condition": cond,
            "Episode": eid,
            "Level": row["level"],
            "Success": success,
            "Turns": turns,
            "Actionability": score,
            "Compliance": compliance,
            "IntentAcc": intent_acc,
            "RepairTurns": repair_turns,
            "ReframeEndorse": reframe_endorse
        })
        
    return pd.DataFrame(metrics)

def analyze_and_plot(ep_df, turn_df):
    if ep_df.empty: return

    stats = calculate_metrics(ep_df, turn_df)
    
    # Save Raw
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stats.to_csv(os.path.join(RESULT_DIR, f"full_metrics_{timestamp}.csv"), index=False)
    
    # Aggregation
    agg = stats.groupby(["Condition", "Level"]).mean(numeric_only=True).reset_index()
    print(agg)
    agg.to_csv(os.path.join(RESULT_DIR, f"summary_{timestamp}.csv"), index=False)
    
    # Plotting
    try:
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        sns.barplot(data=stats, x="Level", y="Success", hue="Condition", ax=axes[0,0])
        sns.barplot(data=stats, x="Level", y="Actionability", hue="Condition", ax=axes[0,1])
        sns.barplot(data=stats, x="Level", y="Turns", hue="Condition", ax=axes[0,2])
        sns.barplot(data=stats, x="Level", y="Compliance", hue="Condition", ax=axes[1,0])
        sns.barplot(data=stats, x="Level", y="IntentAcc", hue="Condition", ax=axes[1,1])
        sns.barplot(data=stats, x="Level", y="RepairTurns", hue="Condition", ax=axes[1,2])
        
        plt.tight_layout()
        plt.savefig(os.path.join(RESULT_DIR, f"plots_{timestamp}.png"))
    except Exception as e:
        print(f"Plotting error: {e}")

if __name__ == "__main__":
    ep, turn = load_latest_logs()
    if ep is not None:
        analyze_and_plot(ep, turn)

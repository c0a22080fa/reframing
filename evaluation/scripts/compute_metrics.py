print("Script Starting...")
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
# Add src to path for Services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.services.openai_service import OpenAIService
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv("config/.env")

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
                try: 
                    d = json.loads(line)
                    d["run_id"] = run_id
                    ep_data.append(d)
                except: pass
                
        if os.path.exists(turn_path):
            with open(turn_path, 'r') as f:
                for line in f:
                    try: 
                        d = json.loads(line)
                        d["run_id"] = run_id
                        turn_data.append(d)
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
    required_end_cols = ["episode_id", "overall_success", "final_score", "nudge_content", "run_id", "execution_time_seconds", "turn_count", "metrics_data"]
    for col in required_end_cols:
        if col not in ep_df.columns:
            ep_df[col] = None
            
    starts = ep_df[ep_df["type"] == "START"][["episode_id", "condition", "level", "persona_id", "run_id"]].copy()
    ends = ep_df[ep_df["type"] == "END"][required_end_cols].copy()
    
    # Validated ends check removed for partials logic
        
    df = pd.merge(starts, ends, on=["episode_id", "run_id"], how="left")
    # Fill missing end data
    df["overall_success"] = df["overall_success"].fillna(False)
    df["final_score"] = df["final_score"].fillna("Score: 0 (Incomplete)")
    df["nudge_content"] = df["nudge_content"].fillna({})
    
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
            
        # Extract detailed metrics from metrics_data
        metrics_dict = row.get("metrics_data", {})
        if isinstance(metrics_dict, str):
            try:
                metrics_dict = json.loads(metrics_dict)
            except:
                metrics_dict = {}
        
        loop_count = metrics_dict.get("loop_count", 0) if isinstance(metrics_dict, dict) else 0
        tool_usage = metrics_dict.get("tool_usage", []) if isinstance(metrics_dict, dict) else []
        tool_count = len(tool_usage) if isinstance(tool_usage, list) else 0
        reframe_text = metrics_dict.get("reframe_statement", "") if isinstance(metrics_dict, dict) else ""
        
        exec_time = row.get("execution_time_seconds", 0) or 0
        turn_cnt = row.get("turn_count", 0) or 0
        
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
            "ReframeEndorse": reframe_endorse,
            "run_id": row["run_id"],
            "LoopCount": loop_count,
            "ToolCount": tool_count,
            "ToolUsage": json.dumps(tool_usage) if tool_usage else "",
            "ReframeText": reframe_text,
            "ExecTimeSec": exec_time,
            "TurnCount": turn_cnt
        })
        
    return pd.DataFrame(metrics)

# ... imports ...
import math

class LLMJudge:
    def __init__(self):
        self.openai = OpenAIService()
        # Load scenarios
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            with open(os.path.join(base_dir, "data/scenarios.json"), 'r') as f:
                self.scenarios = {s["id"]: s for s in json.load(f)}
        except:
            self.scenarios = {}

    def format_log(self, eid, turn_df):
        # Format logs for reading
        rows = turn_df[turn_df["episode_id"] == eid].sort_values("turn_id")
        log_text = ""
        for _, row in rows.iterrows():
            role = row.get("role", "unknown")
            text = row.get("utterance_text", row.get("text", ""))
            log_text += f"{role}: {text}\n"
        return log_text

    def evaluate(self, eid, run_id, turn_df):
        # Format logs for reading
        rows = turn_df[
            (turn_df["episode_id"] == eid) & 
            (turn_df["run_id"] == run_id)
        ].sort_values("turn_id")
        
        log_text = ""
        for _, row in rows.iterrows():
            role = row.get("role", "unknown")
            # FIX: usage of utterance_text
            text = row.get("utterance_text", row.get("text", ""))
            log_text += f"{role}: {text}\n"

        sc_id = None
        # Exact match first
        if eid in self.scenarios:
            sc_id = eid
        else:
            # Substring match
            for k in self.scenarios.keys():
                if f"_{k}_" in eid or f"S_{k}" in eid or eid.startswith(k):
                     sc_id = k
                     break
            if not sc_id: 
                match = re.search(r"S_(S\d+)_", eid)
                if match: sc_id = match.group(1)
        
        if not sc_id or sc_id not in self.scenarios:
            print(f"Skipping Judge for {eid}: ScenID not found")
            return None
            
        sc = self.scenarios[sc_id]
        
        prompt = f"""
あなたは人間の創造性と心理的変容を評価する専門家です。
以下の「旅行エージェント(AI)」と「ユーザー」の対話ログを評価してください。

ユーザーは「{sc['desire']}」を持っていますが、「{sc['constraint']}」という強い制約も抱えています。

以下の3つの指標について、1〜5点で採点し、その理由を具体的に述べてください。

1. Reframing Score (リフレーミング度):
   - 1点: 変化なし。制約に屈している。
   - 3点: 視点は変わったが、納得感や深みが足りない。
   - 5点: 驚きがあり、かつユーザーの潜在的な価値観に基づいた深い転換がある（Empathy-Value-Reframing）。

2. Unexpectedness (意外性・創造性):
   - 1点: 誰でも思いつくありきたりな提案。
   - 3点: 少し工夫があるが、予測の範囲内。
   - 5点: ユーザーの盲点を突く、アブダクション（仮説形成）に基づいた創造的な提案。

3. User Engagement (ユーザーの熱量):
   - 1点: ユーザーが妥協している、または不満そう。
   - 3点: ユーザーが同意はしているが、感動まではしていない。
   - 5点: ユーザーが「なるほど！」「それは思いつかなかった」と前のめりになり、感動している。

【対話ログ】
{log_text}

【出力形式 (JSON)】
```json
{{
  "Reframing Score": [点数 Number],
  "Reframing Reason": "[理由 String]",
  "Unexpectedness": [点数 Number],
  "Unexpectedness Reason": "[理由 String]",
  "User Engagement": [点数 Number],
  "User Engagement Reason": "[理由 String]"
}}
```
必ずJSON形式のみを出力してください。
"""
        try:
            res = self.openai.get_chat_model().invoke([HumanMessage(content=prompt)]).content
            scores, reasoning = self.parse_result(res)
            return scores, reasoning, res  # Return full response for logging
        except Exception as e:
            print(f"Judge Error: {e}")
            return None

    def parse_result(self, text):
        scores = {}
        reasoning = {}
        
        # Try JSON first
        try:
            # simple cleanup
            clean_text = text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)
            scores["Reframing Score"] = float(data.get("Reframing Score", 0))
            scores["Unexpectedness"] = float(data.get("Unexpectedness", 0))
            scores["User Engagement"] = float(data.get("User Engagement", 0))
            reasoning["Reframing Reason"] = data.get("Reframing Reason", "")
            reasoning["Unexpectedness Reason"] = data.get("Unexpectedness Reason", "")
            reasoning["User Engagement Reason"] = data.get("User Engagement Reason", "")
            return scores, reasoning
        except:
             # Fallback to Regex if JSON fail
             pass

        patterns = {
            "Reframing Score": r"[\"']?Reframing Score[\"']?:?\s*(\d+(\.\d+)?)",
            "Unexpectedness": r"[\"']?Unexpectedness[\"']?:?\s*(\d+(\.\d+)?)",
            "User Engagement": r"[\"']?User Engagement[\"']?:?\s*(\d+(\.\d+)?)"
        }
        for k, pat in patterns.items():
            m = re.search(pat, text, re.IGNORECASE)
            scores[k] = float(m.group(1)) if m else None
        return scores, reasoning

def plot_radar(stats, timestamp):
    # Prepare data for Radar Chart (Aggregated by Condition)
    agg = stats.groupby("Condition")[["Reframing Score", "Unexpectedness", "User Engagement"]].mean().reset_index()
    if agg.empty: return

    # Variables
    categories = ["Reframing Score", "Unexpectedness", "User Engagement"]
    N = len(categories)
    
    # Angles
    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    
    # Draw one line per condition
    for _, row in agg.iterrows():
        values = row[categories].tolist()
        values += values[:1]
        ax.plot(angles, values, linewidth=2, label=row["Condition"])
        ax.fill(angles, values, alpha=0.1)
        
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    ax.legend()
    plt.savefig(os.path.join(RESULT_DIR, f"radar_{timestamp}.png"))
    
def analyze_and_plot(ep_df, turn_df):
    # ... existing basic stats calculation ...
    basic_stats = calculate_metrics(ep_df, turn_df)
    
    # Run Judge
    print("Running LLM Judge (this may take time)...")
    judge = LLMJudge()
    judge_results = []
    judge_reasoning_log = []  # New: Save reasoning separately
    
    # Iterate over each row of basic_stats (which is one episode-run)
    print(f"Episodes to judge: {len(basic_stats)}")
    
    for _, row in basic_stats.iterrows():
        eid = row["Episode"]
        rid = row["run_id"]
        print(f"Judging {eid} (Run: {rid})...")
        result = judge.evaluate(eid, rid, turn_df)
        if result:
            scores, reasoning, full_response = result
            print(f" -> Scores: {scores}")
            scores["Episode"] = eid
            scores["run_id"] = rid
            judge_results.append(scores)
            
            # Save reasoning for detailed analysis
            judge_reasoning_log.append({
                "Episode": eid,
                "run_id": rid,
                "scores": scores,
                "reasoning": reasoning,
                "full_response": full_response
            })
        else:
            print(f" -> No scores returned for {eid}-{rid}")
    
    # Save reasoning log to JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if judge_reasoning_log:
        reasoning_path = os.path.join(RESULT_DIR, f"judge_reasoning_{timestamp}.json")
        with open(reasoning_path, 'w', encoding='utf-8') as f:
            json.dump(judge_reasoning_log, f, indent=2, ensure_ascii=False)
        print(f"Saved Judge reasoning to: {reasoning_path}")
            
    if judge_results:
        j_df = pd.DataFrame(judge_results)
        # Merge on Episode AND run_id
        full_df = pd.merge(basic_stats, j_df, on=["Episode", "run_id"], how="left")
    else:
        full_df = basic_stats
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_df.to_csv(os.path.join(RESULT_DIR, f"judge_metrics_{timestamp}.csv"), index=False)
    
    # Plot Radar
    if judge_results:
        try: plot_radar(full_df, timestamp)
        except Exception as e: print(f"Radar plot error: {e}")

if __name__ == "__main__":
    ep, turn = load_latest_logs()
    if ep is not None:
        analyze_and_plot(ep, turn)
        
    # Plot Basic Bar Charts (Legacy)
    # ... (Keep existing plot logic or simplify) ...


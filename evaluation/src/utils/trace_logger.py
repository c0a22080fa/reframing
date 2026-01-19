
import os
import datetime
import json

LOG_FILE = "evaluation/logs/agent_trace.txt"

def log_trace(episode_id: str, node_name: str, content: dict | str):
    """
    Appends a structured log entry to the trace file.
    """
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    # Format content
    if isinstance(content, dict):
        # Pretty print JSON
        msg = json.dumps(content, indent=2, ensure_ascii=False)
    else:
        msg = str(content)
        
    entry = f"\n[{timestamp}] [Ep: {episode_id}] --- {node_name} ---\n{msg}\n{'-'*40}\n"
    
    # Ensure dir exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

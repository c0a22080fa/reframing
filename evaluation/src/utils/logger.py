import json
import os
import time
from datetime import datetime

class EvaluationLogger:
    def __init__(self, log_dir="evaluation/logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.episode_log_path = os.path.join(log_dir, f"episode_log_{self.run_id}.jsonl")
        self.turn_log_path = os.path.join(log_dir, f"turn_log_{self.run_id}.jsonl")
        self.agent_log_path = os.path.join(log_dir, f"agent_log_{self.run_id}.jsonl")
        self.pkg_log_path = os.path.join(log_dir, f"pkg_log_{self.run_id}.jsonl")

    def _append(self, file_path, data):
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def log_episode(self, episode_data):
        """
        Log episode-level outcomes.
        Required keys: condition, persona_id, episode_id, level, seed, phase1_success, etc.
        """
        self._append(self.episode_log_path, episode_data)

    def log_turn(self, turn_data):
        """
        Log turn-level interaction.
        Required keys: turn_id, speaker, utterance_text, phase_label
        """
        self._append(self.turn_log_path, turn_data)

    def log_agent(self, agent_data):
        """
        Log internal agent reasoning.
        Required keys: agent_name, inputs, outputs, decisions
        """
        agent_data["timestamp"] = time.time()
        self._append(self.agent_log_path, agent_data)
        
    def log_pkg(self, pkg_data):
        """
        Log PKG updates.
        Required keys: write_event_id, turn_id, write_type, pk_entry_id
        """
        pkg_data["timestamp"] = time.time()
        self._append(self.pkg_log_path, pkg_data)

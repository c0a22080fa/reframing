"""
Scenario Logger - Detailed process logging for Case Study analysis
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Any


class ScenarioLogger:
    def __init__(self, scenario_id: str, run_id: str, condition: str, log_dir: str = "evaluation/logs"):
        self.scenario_id = scenario_id
        self.run_id = run_id
        self.condition = condition
        self.log_dir = log_dir
        
        self.trace = {
            "scenario_id": scenario_id,
            "run_id": run_id,
            "condition": condition,
            "timestamp": datetime.now().isoformat(),
            "initial_input": "",
            "process_trace": [],
            "final_output": {}
        }
        
        self.step_counter = 0
    
    def set_initial_input(self, text: str):
        """Record initial user input"""
        self.trace["initial_input"] = text
    
    def add_step(self, node: str, data: Dict[str, Any]):
        """Add a processing step to the trace"""
        self.step_counter += 1
        step = {
            "step": self.step_counter,
            "node": node,
            "timestamp": datetime.now().isoformat(),
            **data
        }
        self.trace["process_trace"].append(step)
    
    def set_final_output(self, output: Dict[str, Any]):
        """Record final output"""
        self.trace["final_output"] = output
    
    def save(self):
        """Save the trace to a JSON file"""
        os.makedirs(self.log_dir, exist_ok=True)
        filename = f"scenario_detail_{self.scenario_id}_{self.run_id}.json"
        filepath = os.path.join(self.log_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.trace, f, indent=2, ensure_ascii=False)
        
        return filepath

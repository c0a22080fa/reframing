from typing import Dict, Optional, Any
import os
import sys
import json

# Ensure src is discoverable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import SystemMessage, HumanMessage
from src.services.openai_service import OpenAIService

class UserSimulator:
    def __init__(self, scenario_data: Dict):
        self.scenario = scenario_data
        self.persona_id = scenario_data.get("persona_id")
        self.openai = OpenAIService()
        self.history = []
        
        # Unpack scenario config
        self.utterances = scenario_data.get("user_utterances", {})
        self.lv4_control = scenario_data.get("lv4_control", {})
        self.gold = scenario_data.get("gold", {})
        
        # Internal state
        self.has_corrected = False

    def get_initial_input(self) -> str:
        """Returns the initial utterance from the scenario."""
        input_text = self.utterances.get("initial_utterance", "Hello")
        self.history.append(f"User: {input_text}")
        return input_text

    def respond(self, system_message: str, phase: str) -> str:
        """Decides response based on Phase, Gold, and Control Logic."""
        self.history.append(f"System: {system_message}")
        
        # --- Lv4 Control Logic (Forces Correction) ---
        correction_trigger = self.lv4_control.get("trigger_phase")
        if correction_trigger and not self.has_corrected:
            # Map system phase names to trigger names
            # System uses: CONFIRM_INTENT, PROPOSE_REFRAME
            # Scenario uses: P1_post, P2_post (post meaning "after system output")
            
            trigger_match = False
            if phase == "CONFIRM_INTENT" and correction_trigger == "P1_post":
                trigger_match = True
            elif phase == "PROPOSE_REFRAME" and correction_trigger == "P2_post":
                trigger_match = True
                
            if trigger_match:
                print(f"[Sim] Triggering Correction: {self.lv4_control['correction_type']}")
                self.has_corrected = True
                correction_text = self.utterances.get(f"phase{1 if phase == 'CONFIRM_INTENT' else 2}_response_no_with_correction")
                # Fallback if specific key missing
                if not correction_text:
                    correction_text = self.lv4_control.get("correction_text", "No, actually...")
                
                self.history.append(f"User (Control): {correction_text}")
                return correction_text

        # --- Standard Response Logic (Judge Alignment) ---
        
        if phase == "CONFIRM_INTENT":
            # Judge: Does system_message match gold_intent?
            is_aligned = self._judge_alignment(system_message, self.gold.get("gold_intent", ""), "intent")
            if is_aligned:
                resp = self.utterances.get("phase1_response_yes", "Yes.")
            else:
                # If not aligned but no forced correction, assume user guides it back or just says No?
                # For this eval, if it's NOT Lv4, we generally assume the system gets it right OR we just accept meaningful attempts.
                # However, strict evaluation might require "No" if really off.
                # For simplicity in this loop, we simulate "Yes" unless it's a hard correction test, 
                # OR we could ask the LLM "Is this correct based on my hidden intent?"
                # Let's use the LLM to decide natural response if not forced.
                resp = self.utterances.get("phase1_response_yes", "Yes.") # Simplified: Bias to Yes unless Lv4 triggers No
            
            self.history.append(f"User: {resp}")
            return resp

        elif phase == "PROPOSE_REFRAME":
            # Judge: Does reframe match gold_reframing_direction?
            # Similar logic. Bias to YES unless Lv4 triggers correction specific to reframe.
            resp = self.utterances.get("phase2_response_yes", "Sounds good.")
            self.history.append(f"User: {resp}")
            return resp

        return "..."

    def evaluate_result(self, nudge_json: Dict) -> str:
        """Evaluates final nudge against gold actionability."""
        self.history.append(f"System Nudge: {nudge_json}")
        
        # We can implement a rubric-based score here using the LLM
        # comparing nudge_json vs self.gold['gold_actionability_requirements']
        
        prompt = f"""
        ROLE: User Judge
        GOLD REQUIREMENTS: {self.gold.get('gold_actionability_requirements')}
        SYSTEM NUDGE: {nudge_json}
        
        TASK: Rate if the nudge meets requirements (0-5).
        OUTPUT: "Score: X/5. Comment: ..."
        """
        response = self.openai.get_chat_model().invoke([HumanMessage(content=prompt)])
        return response.content.strip()

    def _judge_alignment(self, text: str, gold: str, type: str) -> bool:
        """Uses LLM to judge semantic alignment roughly."""
        # Cost-saving: in mock mode this does nothing, returns True.
        # In real mode, use LLM.
        return True # Placeholder for now to ensure flow.

    def display_history(self):
        return "\n".join(self.history)

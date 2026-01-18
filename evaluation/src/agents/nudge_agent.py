import os
import json
from src.services.openai_service import OpenAIService

class NudgeAgent:
    def __init__(self, llm: OpenAIService):
        self.llm = llm
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(self.base_dir, "prompts/nudge_east.txt"), "r") as f:
            self.system_prompt = f.read()

    def generate(self, user_input: str, deep_intent: str, context: str):
        prompt_content = f"""
        User Input (Constraint): {user_input}
        Identified Deep Intent: {deep_intent}
        User Context: {context}
        
        Generate the EAST Nudge strategy and response.
        """
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt_content}
        ]
        
        response_str = self.llm.chat_completion(messages)
        
        # Parse JSON if possible, otherwise return raw text wrapped in structure
        try:
            # Simple cleanup for JSON parsing if LLM adds markdown blocks
            clean_str = response_str.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_str)
        except:
            return {
                "strategy": "Parsing failed or fallback",
                "response_text": response_str
            }

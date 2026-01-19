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
        self.persona_id = scenario_data.get("id", "unknown")
        self.openai = OpenAIService()
        self.history = []
        
        # Unpack scenario config
        self.desire = scenario_data.get("desire", "")
        self.constraint = scenario_data.get("constraint", "")
        
        # Internal state
        self.turn_count = 0

    def get_initial_input(self) -> str:
        """Returns the initial utterance from the scenario."""
        input_text = self.scenario.get("initial_utterance", "Hello")
        self.history.append(f"User: {input_text}")
        return input_text

    def respond(self, system_message: str, phase: str) -> str:
        """Decides response based on Persona Prompt."""
        self.history.append(f"System: {system_message}")
        self.turn_count += 1
        
        prompt = f"""
あなたは「佐藤悠人」というペルソナを演じてください。
現在、あなたは旅行エージェント（AI）と会話しています。

【設定】
今回の旅行の目的： {self.desire}
しかし、あなたには譲れない強い制約があります： {self.constraint}

【振る舞いのルール】
1. 最初は、AIの提案に対して懐疑的になってください。「でも、〇〇だから嫌だ」と制約を理由に難色を示してください。
2. もしAIが、あなたの制約を単に回避するだけのつまらない提案（例：人混みが嫌ならホテルにいましょう）をしてきたら、不満を述べてください。
3. もしAIが、あなたの「制約」を逆手に取ったり、予想外の視点（リフレーミング）で価値に変える提案をしてきたら、その意外性に驚き、興味を示してください。
4. 対話は最大5ターンで終了します。現在は {self.turn_count} ターン目です。
   - 基本的に4ターン目までは懐疑的に振る舞ってください。
   - 【例外】：もしAIが「非常に優れたリフレーミング（あなたの潜在的な価値を言い当てた）」や「心の琴線に触れる提案」をしてきた場合は、4ターン以内であっても態度を軟化させ、前向きに検討・同意してください。
   - 逆に、単なる回避策や制約を無視した提案には厳しく接してください。
   - 5ターン目（最後）には必ず結論（提案を受け入れるか、拒絶するか）を出して会話を締めてください。

【会話履歴】
{chr(10).join(self.history[-5:])}

次のあなたの発言を生成してください（短めに）。
"""
        response = self.openai.get_chat_model().invoke([HumanMessage(content=prompt)]).content.strip()
        self.history.append(f"User: {response}")
        return response

    def evaluate_result(self, nudge_json: Dict) -> str:
        """
        Legacy method kept for compatibility. 
        Detailed eval is now done by an external Judge Agent.
        This just returns a placeholder.
        """
        self.history.append(f"System Nudge: {json.dumps(nudge_json, ensure_ascii=False)}")
        return "Score: 0 (Judge Deferred)"

from openai import AzureOpenAI, OpenAI
import os
import yaml

class OpenAIService:
    def __init__(self, config_path="config/settings.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        self.deployment = self.config["model"]["openai_deployment"]
        self.api_version = self.config["model"]["openai_api_version"]
        
        # Determine Client Type
        if self.azure_api_key and self.azure_endpoint:
            print("Using Azure OpenAI Service.")
            self.client = AzureOpenAI(
                api_key=self.azure_api_key,
                api_version=self.api_version,
                azure_endpoint=self.azure_endpoint
            )
            self.model_name = self.deployment
        elif self.openai_api_key:
            print("Using Standard OpenAI Service.")
            self.client = OpenAI(api_key=self.openai_api_key)
            # If using standard OpenAI, 'openai_deployment' in config usually represents the model name (e.g. gpt-4)
            self.model_name = self.deployment
        else:
            self.client = None
            print("No Valid OpenAI credentials found (Azure or Standard). Using Mock response.")

    def get_chat_model(self, temperature=0.7):
        """Returns a LangChain compatible Chat Model (Azure or Standard)"""
        from langchain_openai import AzureChatOpenAI, ChatOpenAI

        if self.azure_api_key:
            return AzureChatOpenAI(
                azure_deployment=self.deployment,
                openai_api_version=self.api_version,
                azure_endpoint=self.azure_endpoint,
                api_key=self.azure_api_key,
                temperature=temperature
            )
        elif self.openai_api_key:
            return ChatOpenAI(
                model=self.model_name,
                api_key=self.openai_api_key,
                temperature=temperature
            )
        else:
            print("WARNING: No OpenAI Credentials. Returning MockChatModel.")
            return MockChatModel()


    def chat_completion(self, messages, temperature=0.7):
        if not self.client:
            # Mock Logic for Translation (used by CometService)
            last_msg = messages[-1]['content']
            if "Translate" in messages[0]['content'] or "translation" in messages[0]['content']:
                # Return a dummy translation. For simple mocking, just return the input or a fixed EN string.
                # Assuming input is JP, let's just return "I want to relax" as a generic fallback 
                # or try to use the alphanumeric parts if any. 
                return "I want to relax and find peace."
            return f"[Mock LLM Response] I processed: {last_msg[:20]}..."

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM Error: {e}")
            return "Error in LLM generation."


class MockChatModel:
    def invoke(self, messages):
        from langchain_core.messages import AIMessage
        content = messages[0].content
        
        # 1. Profiler Chair
        if "ROLE: Profiler Chair" in content:
            # Return FINALIZE directly to check the Nudge flow
            return AIMessage(content='''
            {
              "next_step": "FINALIZE",
              "reasoning": "Mock reasoning: Sufficient evidence.",
              "deep_intent": "Deep Intent: Seeking inner peace and tranquility.",
              "comet_relations": ["xWant"]
            }
            ''')
            
        # 2. Critic
        if "ROLE: Critic Agent" in content:
            return AIMessage(content='''
            {
              "status": "APPROVE",
              "reason": "Mock Approval",
              "feedback": "None"
            }
            ''')

        # 3. Intent Confirmer
        if "ROLE: Intent Confirmer" in content or "confirmation_question" in content or "User input:" in content: 
             # Heuristic match for intent confirmer prompt (dialogue_intent_check)
             return AIMessage(content='''
             {
                "confirmation_question": "本当の目的は、静かな場所で心を落ち着けることですか？"
             }
             ''')

        # 4. Reframe Proposer
        if "ROLE: Reframe Proposer" in content or "reframe_statement" in content:
             return AIMessage(content='''
             {
                "reframe_statement": "騒がしい場所を避けて、自分だけの隠れ家を見つける冒険と考えましょう。",
                "check_question": "この考え方はいかがですか？"
             }
             ''')

        # 5. Nudge Agent
        if "ROLE: Nudge Agent" in content:
             return AIMessage(content='''
             {
               "east_justification": {
                 "Easy": "予約不要",
                 "Attractive": "静寂な雰囲気",
                 "Social": "知る人ぞ知る場所",
                 "Timely": "今からすぐ"
               },
               "reframed_perspective": "視点を変えて、静寂を楽しむ心の旅に出ましょう。",
               "concrete_next_step": "近くの寺院の庭園を訪れる。",
               "invitation_text": "喧騒を離れて、心静かな時間を過ごしませんか？",
               "revision_question": "このプランでよろしいでしょうか？"
             }
             ''')

        return AIMessage(content="[Mock Chat Model Default Response]")

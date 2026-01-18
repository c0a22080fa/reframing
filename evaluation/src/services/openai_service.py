from openai import AzureOpenAI, OpenAI
import os
import yaml

# Global singleton for mock model
_SHARED_MOCK_MODEL = None

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
            global _SHARED_MOCK_MODEL
            if _SHARED_MOCK_MODEL is None:
                print("[WARN] No OpenAI Keys found. Initializing Shared Mock Chat Model.")
                from langchain_community.chat_models import FakeListChatModel
                # Sequence of responses for the full flow:
                # 1. Sim: Initial Input -> "I am disappointed..."
                # 2. Chair: Finalize -> JSON
                # 3. Critic: Approve -> JSON
                # 4. Intent Confirmer: Ask -> JSON
                # 5. Sim: Confirm -> "Yes"
                # 6. Reframe Proposer: Propose -> JSON
                # 7. Sim: Accept -> "That sounds good"
                # 8. Action Nudge: Generate -> JSON
                # 9. Sim: Evaluate -> "Score..."
                _SHARED_MOCK_MODEL = FakeListChatModel(responses=[
                    "I am disappointed by the rain in Kyoto.", 
                    '{"next_step": "FINALIZE", "deep_intent": "User is sad about rain."}',
                    '{"status": "APPROVE"}',
                    '{"confirmation_question": "Are you sad about the rain?"}',
                    "Yes, that is correct.",
                    '{"reframe_statement": "Rain is cozy.", "check_question": "Do you like coziness?"}',
                    "Yes, I like that.",
                    '{"reframed_perspective": "Rain is cozy.", "concrete_next_step": "Go to a cafe.", "invitation_text": "Visit a cafe?", "revision_question": "How is this?"}',
                    "Score: 5/5. Comment: Good test."
                ])
            return _SHARED_MOCK_MODEL

    def chat_completion(self, messages, temperature=0.7):
        if not self.client:
            last_msg = messages[-1]['content']
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

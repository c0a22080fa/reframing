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

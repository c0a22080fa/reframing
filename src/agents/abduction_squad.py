import os
import autogen
from src.services.comet_service import CometService
from src.services.search_service import SearchService
from src.services.openai_service import OpenAIService

class AbductionSquad:
    def __init__(self, comet: CometService, search: SearchService, llm: OpenAIService):
        self.comet = comet
        self.search = search
        self.llm = llm
        
        # Determine strict configuration for AutoGen
        # In a real scenario, we pass the API key directly or use the env var
        self.llm_config = {
            "config_list": [
                {
                    "model": self.llm.deployment, # e.g. "gpt-4"
                    "api_key": self.llm.api_key,
                    "base_url": self.llm.endpoint,
                    "api_type": "azure",
                    "api_version": self.llm.api_version
                }
            ],
            "temperature": 0.7,
        }
        
        # Load Prompts
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        with open(os.path.join(self.base_dir, "prompts/squad_chair.txt"), "r") as f:
            self.chair_system_msg = f.read()
            
        with open(os.path.join(self.base_dir, "prompts/squad_profiler.txt"), "r") as f:
            self.profiler_system_msg = f.read()

    def run(self, user_input: str, context: str):
        # 1. Witness (COMET) & Explorer (Search) data gathering
        # (Same as before, pre-fetching evidence to feed the agents)
        print(f"--- Squad: Asking COMET about '{user_input}' ---")
        comet_data = self.comet.translate_and_infer(user_input)
        x_wants = comet_data.get("xWant", [])
        
        intention_seed = x_wants[:1] if x_wants else ["general help"]
        print(f"--- Squad: Explorer searching for context {intention_seed} ---")
        search_results = self.search.search(user_input, intention_seed)
        
        # 2. Setup AutoGen Agents
        # Chair: Acts as the Admin/Proxy that holds the evidence and asks for analysis
        chair_agent = autogen.UserProxyAgent(
            name="Chair",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,  # Just start the conversation
            code_execution_config=False,
            system_message=self.chair_system_msg
        )
        
        # Profiler: The Logician who critiques based on context
        profiler_agent = autogen.AssistantAgent(
            name="Profiler",
            llm_config=self.llm_config,
            system_message=self.profiler_system_msg + f"\n\nKNOWN USER CONTEXT (PKG): {context}"
        )
        
        # 3. Construct the Initial Prompt
        evidence_block = f"""
        DISCUSSION TOPIC: Determine Deep Intent from User Input.
        
        User Input: "{user_input}"
        
        [EVIDENCE 1: SYSTEM 1 INTUITION (COMET)]
        Potential Desires (xWant): {x_wants}
        
        [EVIDENCE 2: ANALOGY (SEARCH)]
        Found Cases: {search_results}
        
        TASK:
        Profiler, analyze this evidence against the KNOWN USER CONTEXT.
        Identify the most likely Deep Intent (Latent Need).
        If the evidence contradicts the user profile, reject it.
        Provide the final Deep Intent as a concise statement.
        """
        
        print("--- Squad: AutoGen Debate (Chair <-> Profiler) ---")
        
        # Initiate Chat
        # Chair sends message to Profiler
        chat_result = chair_agent.initiate_chat(
            profiler_agent,
            message=evidence_block
        )
        
        # Extract the last message from the Profiler (Assistant)
        # chat_result.chat_history is a list of dicts
        # We want the last useful content
        last_message = chat_result.chat_history[-1]['content']
        
        return last_message

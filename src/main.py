import os
import sys
import json
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.comet_service import CometService
from services.search_service import SearchService
from services.neo4j_service import Neo4jService
from services.openai_service import OpenAIService

from agents.context_agent import ContextAgent
from agents.abduction_squad import AbductionSquad
from agents.nudge_agent import NudgeAgent

def main():
    # 0. Setup
    print("Initializing Deep Abductive Nudge System...")
    load_dotenv("config/.env")
    
    # Initialize Services
    openai_service = OpenAIService()
    comet_service = CometService(openai_service=openai_service)
    search_service = SearchService()
    neo4j_service = Neo4jService()
    
    # Initialize Agents
    context_agent = ContextAgent(neo4j_service)
    abduction_squad = AbductionSquad(comet_service, search_service, openai_service)
    nudge_agent = NudgeAgent(openai_service)
    
    print("System Ready.")
    
    # Simulation Loop
    while True:
        try:
            user_input = input("\n[User Input] (or 'exit'): ")
            if user_input.lower() in ["exit", "quit"]:
                break
                
            user_id = "test_user_001" # Hardcoded for demo
            
            # 1. Context Retrieval
            print("\nStep 1: Retrieving Context...")
            context = context_agent.retrieve_context(user_id)
            print(f"Context: {context}")
            
            # 2. Divergence (Abduction)
            print("\nStep 2: Divergence (Abduction Squad) Running...")
            deep_intent = abduction_squad.run(user_input, context)
            print(f"==> Determine Deep Intent: {deep_intent}")
            
            # Write back to KG
            neo4j_service.write_inference(user_id, user_input, str(deep_intent))
            
            # 3. Convergence (Nudge)
            print("\nStep 3: Convergence (Nudge Agent) Running...")
            result = nudge_agent.generate(user_input, str(deep_intent), context)
            
            print("\n" + "="*30)
            print("FINAL OUTPUT")
            print("="*30)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error executing pipeline: {e}")

    neo4j_service.close()

if __name__ == "__main__":
    main()

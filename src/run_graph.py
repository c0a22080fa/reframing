import os
import sys

# Ensure src is discoverable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from src.workflow.graph import build_graph

def main():
    load_dotenv("config/.env")
    
    app = build_graph()
    
    # --- Visualization ---
    try:
        mermaid_code = app.get_graph().draw_mermaid()
        print("\n--- Agent Architecture (Mermaid) ---")
        print(mermaid_code)
        
        # Save to file
        os.makedirs("docs", exist_ok=True)
        with open("docs/agent_graph.mermaid", "w") as f:
            f.write(mermaid_code)
        print("\nSaved architecture diagram to: docs/agent_graph.mermaid")
    except Exception as e:
        print(f"Could not generate Mermaid graph: {e}")

    # --- Interactive Loop ---
    print("\n--- Deep Abductive Nudge System (LangGraph Agent) ---")
    print("System initialized. Type 'exit' to quit.")
    
    while True:
        user_input = input("\n[User Input]: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        
        if not user_input:
            continue
            
        initial_state = {
            "input": user_input,
            "user_context": "",
            "comet_evidence": [],
            "explorer_evidence": [],
            "deep_intent": "",
            "nudge": "",
            "messages": []
        }
        
        print("\nDepending on configuration, this may take a moment...")
        
        # Run the graph
        final_state = app.invoke(initial_state)
        
        print("\n================ FINAL OUTPUT ================")
        print(f"Deep Intent: {final_state['deep_intent']}\n")
        print(f"Nudge:\n{final_state['nudge']}")
        print("==============================================")

if __name__ == "__main__":
    main()

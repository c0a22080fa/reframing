import os
import sys

# Ensure src is discoverable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force unbuffered stdout
sys.stdout.reconfigure(line_buffering=True)

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
    print("\n--- Deep Abductive Nudge System (Multi-Turn) ---")
    print("System initialized. Type 'exit' to quit.")
    
    # Persistent State Tracking
    persistent_phase = "ABDUCTION"
    persistent_context = ""
    # We'll re-init other transient fields, but keep phase/context
    
    # NOTE: In a real LangGraph app, we'd use Checkpointers. 
    # Here, we'll crudely pass the phase back in.
    
    saved_state = {
        "phase": "ABDUCTION",
        "deep_intent": "",
        "user_context": "",
        "steps": [],
        "comet_evidence": [],
        "explorer_evidence": []
    }

    while True:
        user_input = input("\n[User Input]: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        
        if not user_input:
            continue
            
        print("\nDepending on configuration, this may take a moment...")
        
        # Build State (Resuming from saved_state)
        current_state = {
            "input": user_input,
            "user_context": saved_state["user_context"],
            "phase": saved_state["phase"],
            "deep_intent": saved_state["deep_intent"],
            "comet_evidence": saved_state["comet_evidence"], # Keep evidence
            "explorer_evidence": saved_state["explorer_evidence"],
            "steps": saved_state["steps"],
            "messages": [], # Reset messages for current turn
            "nudge": ""
        }
        
        # Run the graph
        final_state = app.invoke(current_state)
        
        # Parse Output based on Phase
        output_txt = final_state.get("dialogue_output", "")
        nudge_txt = final_state.get("nudge", "")
        phase = final_state.get("phase", "")
        
        print("\n>>> SYSTEM RESPONSE >>>")
        
        # If finished, force parsing of Nudge logic
        if phase == "FINISHED" and nudge_txt:
             try:
                import json
                import re
                # Clean up potential markdown code blocks
                clean_nudge = nudge_txt.replace("```json", "").replace("```", "").strip()
                
                if "{" in clean_nudge:
                    json_match = re.search(r'\{.*\}', clean_nudge, re.DOTALL)
                    if json_match:
                        nudge_data = json.loads(json_match.group())
                        print(f"--- Reframe: {nudge_data.get('reframed_perspective', '')}")
                        print(f"--- Action: {nudge_data.get('concrete_next_step', '')}")
                        print(f"--- Invitation: {nudge_data.get('invitation_text', '')}")
                    else:
                        print(nudge_txt)
                else:
                    print(nudge_txt)
             except Exception as e:
                print(f"[Parse Error]: {e}")
                print(nudge_txt)
        
        elif output_txt:
            print(output_txt)
                
        # Persist Logic
        saved_state["phase"] = final_state.get("phase", "ABDUCTION")
        saved_state["deep_intent"] = final_state.get("deep_intent", saved_state["deep_intent"])
        saved_state["user_context"] = final_state.get("user_context", saved_state["user_context"])
        # If finished, reset
        if saved_state["phase"] == "FINISHED":
            print("\n[Conversation Complete. Resetting Context...]")
            saved_state["phase"] = "ABDUCTION"
            saved_state["deep_intent"] = ""
            saved_state["steps"] = []

if __name__ == "__main__":
    main()

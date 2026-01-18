from src.services.neo4j_service import Neo4jService

class ContextAgent:
    def __init__(self, neo4j_service: Neo4jService):
        self.db = neo4j_service

    def retrieve_context(self, user_id: str, role: str = "general"):
        """
        Retrieves user static attributes and past constraints/needs.
        Filters the context based on the agent 'role' to reduce prompt bloat (Light GraphRAG).
        """
        profile = self.db.read_profile(user_id)
        attributes = profile.get('attributes', [])
        latent_needs = profile.get('latent_needs', [])
        evidence_log = profile.get('evidence_log', [])[-5:] # Last 5 items

        # --- Role-Conditioned Subgraph Selection ---
        if role == "chair":
            # Chair needs EVERYTHING to make decisions
            context_str = (
                f"User Profile: Attributes={attributes}\n"
                f"Past Intentions: {latent_needs}\n"
                f"Evidence Log (Recent): {evidence_log}"
            )
        elif role == "witness":
            # Witness needs raw input context + minimal constraints (no deep history needed)
            context_str = (
                f"Context Constraints: {attributes}\n"
                f"Recent Topics: {[e['content'] for e in evidence_log if 'content' in e]}"
            )
        elif role == "explorer":
            # Explorer needs the 'Deep Intent' hypothesis (if any) and loose associations
            context_str = (
                f"User Attributes: {attributes}\n"
                f"Search Context (Evidence): {evidence_log}"
            )
        elif role == "critic":
            # Critic needs strict attributes to check for contradictions
            context_str = (
                f"CRITICAL RULES (User Attributes): {attributes}\n"
                f"Past Patterns: {latent_needs}"
            )
        elif role == "nudge":
            # Nudge needs Profile (for tone) and Preferences
            context_str = (
                f"User Persona: {attributes}\n"
                f"Historical Preferences: {latent_needs}"
            )
        else:
            # Default / General
            context_str = (
                f"User Profile: Attributes={attributes}\n"
                f"Past Intentions: {latent_needs}\n"
                f"Recent Evidence Log: {evidence_log}"
            )
            
        return context_str

    def store_inference(self, user_id: str, deep_intent: str):
        """Stores the inferred latent need back to the graph."""
        self.db.write_inference(user_id, deep_intent)

    def write_active_node(self, user_id: str, text: str):
        """Writes the user input as an Active node in the graph."""
        if hasattr(self.db, 'write_active_node'):
             self.db.write_active_node(user_id, text)
        else:
             print(f"[Context] simulating write of Active Node: {text}")

    def store_evidence(self, user_id: str, source: str, content: str):
        """Stores intermediate evidence (COMET/Explorer) to the graph."""
        if hasattr(self.db, 'write_evidence'):
            self.db.write_evidence(user_id, source, content)
        else:
            print(f"[Context] simulating write of {source} Evidence: {content}")

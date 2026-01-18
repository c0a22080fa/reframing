from src.services.neo4j_service import Neo4jService

class ContextAgent:
    def __init__(self, neo4j_service: Neo4jService):
        self.db = neo4j_service

    def retrieve_context(self, user_id: str):
        """
        Retrieves user static attributes and past constraints/needs.
        """
        profile = self.db.read_profile(user_id)
        # potentially format this for prompt injection
        context_str = f"User Profile: Attributes={profile.get('attributes', [])}"
        return context_str
        return context_str

    def store_inference(self, user_id: str, deep_intent: str):
        """Stores the inferred latent need back to the graph."""
        self.db.write_inference(user_id, deep_intent)

    def write_active_node(self, user_id: str, text: str):
        """Writes the user input as an Active node in the graph."""
        # Simple implementation: just log it or add to local DB
        # For Local PKG, we can treat it similar to an attribute or event
        if hasattr(self.db, 'write_active_node'):
             self.db.write_active_node(user_id, text)
        else:
             print(f"[Context] simulating write of Active Node: {text}")

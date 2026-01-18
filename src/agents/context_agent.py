from src.services.neo4j_service import Neo4jService

class ContextAgent:
    def __init__(self, neo4j_service: Neo4jService):
        self.db = neo4j_service

    def retrieve_context(self, user_id: str):
        """
        Retrieves user static attributes and past constraints/needs.
        """
        profile = self.db.read_profile(user_id)
        # Format for RAG
        context_str = (
            f"User Profile: Attributes={profile.get('attributes', [])}\n"
            f"Past Intentions: {profile.get('latent_needs', [])}\n"
            f"Recent Evidence Log: {profile.get('evidence_log', [])[-5:]}" # Last 5 items
        )
        return context_str
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

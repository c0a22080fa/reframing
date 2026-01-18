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

import json
import os
import yaml
from neo4j import GraphDatabase

class Neo4jService:
    def __init__(self, config_path="config/settings.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
            
        self.use_local = False
        self.local_db_path = "data/pkg_graph.json"
        
        # Try Neo4j Connection
        try:
            uri = self.config["neo4j"]["uri"]
            user = os.getenv("NEO4J_USERNAME", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "password")
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            print("Neo4j Connected.")
        except Exception as e:
            print(f"Neo4j Connection Failed: {e}. Switching to LOCAL JSON GRAPH mode.")
            self.use_local = True
            self.driver = None
            self._ensure_local_db()

    def _ensure_local_db(self):
        if not os.path.exists(self.local_db_path):
            os.makedirs(os.path.dirname(self.local_db_path), exist_ok=True)
            # Seed initial schema/data
            initial_data = {
                "users": {
                    "test_user_001": {
                        "attributes": ["Software Engineer", "Remote Work", "Loves Kyoto"],
                        "constraints": [],
                        "latent_needs": []
                    }
                }
            }
            with open(self.local_db_path, "w") as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)

    def close(self):
        if self.driver:
            self.driver.close()

    def read_profile(self, user_id: str):
        """Reads attributes from Neo4j or Local JSON"""
        if self.use_local:
            with open(self.local_db_path, "r") as f:
                data = json.load(f)
            user = data.get("users", {}).get(user_id, {})
            print(f"[Local PKG] Read User: {user.get('attributes')}")
            return {
                "attributes": user.get("attributes", []),
                "latent_needs": user.get("latent_needs", []),
                "evidence_log": user.get("evidence_log", [])
            }
        else:
            query = """
            MATCH (u:User {id: $user_id})-[:HAS]->(a:Attribute)
            RETURN a.name as attribute
            """
            with self.driver.session() as session:
                result = session.run(query, user_id=user_id)
                return {"attributes": [record["attribute"] for record in result]}

    def write_active_node(self, user_id: str, text: str):
        """Writes current interaction context"""
        if self.use_local:
            print(f"[Local PKG] Writing Active Context: {text}")
            with open(self.local_db_path, "r") as f:
                data = json.load(f)
            
            if user_id not in data["users"]:
                data["users"][user_id] = {}
            
            # Simple list of recent interactions
            data["users"][user_id].setdefault("active_context", []).append(text)
            
            with open(self.local_db_path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            # Neo4j implementation placeholder
            pass

    def write_evidence(self, user_id: str, source: str, content: str):
        """Writes intermediate evidence"""
        if self.use_local:
            print(f"[Local PKG] Writing Evidence ({source})")
            with open(self.local_db_path, "r") as f:
                data = json.load(f)
            
            entry = f"[{source}] {content}"
            data["users"][user_id].setdefault("evidence_log", []).append(entry)
            
            with open(self.local_db_path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
             # Neo4j implementation placeholder
             pass

    def write_inference(self, user_id: str, deep_intent: str):
        """Writes the inferred Deep Intent back to the Graph"""
        if self.use_local:
            print(f"[Local PKG] Writing Inference: {deep_intent}")
            with open(self.local_db_path, "r") as f:
                data = json.load(f)
            
            if user_id not in data["users"]:
                data["users"][user_id] = {"attributes": [], "latent_needs": []}
            
            # Avoid duplicates
            if deep_intent not in data["users"][user_id].get("latent_needs", []):
                data["users"][user_id].setdefault("latent_needs", []).append(deep_intent)
            
            with open(self.local_db_path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            query = """
            MERGE (u:User {id: $user_id})
            MERGE (n:LatentNeed {text: $deep_intent})
            MERGE (u)-[:HAS_LATENT_NEED]->(n)
            """
            with self.driver.session() as session:
                session.run(query, user_id=user_id, deep_intent=deep_intent)

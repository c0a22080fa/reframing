from neo4j import GraphDatabase
import os
import yaml

class Neo4jService:
    def __init__(self, config_path="config/settings.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
            
        uri = self.config["neo4j"]["uri"]
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.verify_connection()
        except Exception as e:
            print(f"Neo4j Connection Failed: {e}. Running in Mock Mode for demo.")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()
            
    def verify_connection(self):
        if self.driver:
            self.driver.verify_connectivity()
            print("Neo4j Connected.")

    def read_profile(self, user_id: str):
        if not self.driver:
            return {"attributes": ["Software Engineer", "Remote Work"], "constraints": []}
            
        query = """
        MATCH (u:User {id: $user_id})-[:HAS]->(a:Attribute)
        RETURN a.name as attribute
        """
        with self.driver.session() as session:
            result = session.run(query, user_id=user_id)
            return {"attributes": [record["attribute"] for record in result]}

    def write_inference(self, user_id: str, constraint: str, deep_intent: str):
        if not self.driver:
            print(f"[Mock Neo4j] Writing inference for {user_id}: {constraint} -> {deep_intent}")
            return

        query = """
        MERGE (u:User {id: $user_id})
        MERGE (c:Constraint {text: $constraint})
        MERGE (n:LatentNeed {text: $deep_intent})
        MERGE (u)-[:EXPERIENCES]->(c)
        MERGE (c)-[:TRIGGERS]->(n)
        """
        with self.driver.session() as session:
            session.run(query, user_id=user_id, constraint=constraint, deep_intent=deep_intent)

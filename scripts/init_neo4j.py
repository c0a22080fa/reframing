import os
import sys
from neo4j import GraphDatabase

# Ensure we can import settings or just read env directly
def init_neo4j_schema():
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "password" # standard default, user should confirm if changed

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            print("Connecting to Neo4j to initialize schema...")
            
            # 1. Create Constraints/Indexes to prevent "Label not found" warnings
            # These are benign warnings but noisy. Defining schema fixes them.
            
            # User Constraints
            session.run("CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
            
            # Attribute Constraints/Indexes
            session.run("CREATE INDEX attribute_name_index IF NOT EXISTS FOR (a:Attribute) ON (a.name)")
            
            # Helper constraints for other node types if commonly used
            session.run("CREATE INDEX value_index IF NOT EXISTS FOR (v:Value) ON (v.name)")
            session.run("CREATE INDEX constraint_index IF NOT EXISTS FOR (c:Constraint) ON (c.name)")
            
            print("[SUCCESS] Schema initialized. 'Label not found' warnings should be suppressed.")
            
        driver.close()
    except Exception as e:
        print(f"[ERROR] Failed to initialize Neo4j: {e}")

if __name__ == "__main__":
    init_neo4j_schema()

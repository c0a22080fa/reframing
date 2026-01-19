
from neo4j import GraphDatabase
import os

def seed_data():
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "password" 

    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        print("Seeding Data...")
        
        # Clear existing
        session.run("MATCH (n) DETACH DELETE n")
        
        # Create User
        session.run("CREATE (:User {id: 'test_user_001', name: 'Sato Yuto'})")
        
        # Create Attributes
        attributes = [
            "Hates Crowds",
            "Loves Nature",
            "Budget Conscious",
            "Introvert",
            "History Buff"
        ]
        
        for attr in attributes:
            session.run("""
                MATCH (u:User {id: 'test_user_001'})
                MERGE (a:Attribute {name: $attr})
                MERGE (u)-[:HAS_ATTRIBUTE]->(a)
            """, attr=attr)
            
        print("Seeding Complete.")
        
    driver.close()

if __name__ == "__main__":
    seed_data()

"""
Neo4j Snapshot - Capture knowledge graph state before/after episode
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Any


class Neo4jSnapshot:
    def __init__(self, neo4j_service, snapshot_dir: str = "evaluation/logs/neo4j_snapshots"):
        self.neo4j = neo4j_service
        self.snapshot_dir = snapshot_dir
        os.makedirs(snapshot_dir, exist_ok=True)
    
    def capture(self, user_id: str, scenario_id: str, run_id: str, when: str = "before") -> str:
        """
        Capture Neo4j state for a user
        
        Args:
            user_id: User ID
            scenario_id: Scenario ID (e.g., "S1")
            run_id: Run ID timestamp
            when: "before" or "after"
        
        Returns:
            Path to saved snapshot file
        """
        snapshot = {
            "user_id": user_id,
            "scenario_id": scenario_id,
            "run_id": run_id,
            "when": when,
            "timestamp": datetime.now().isoformat(),
            "nodes": [],
            "relationships": []
        }
        
        # Query all nodes for this user
        try:
            # Use Neo4j driver directly if available
            if hasattr(self.neo4j, 'driver') and self.neo4j.driver:
                user_query = """
                MATCH (u:User {id: $user_id})
                OPTIONAL MATCH (u)-[r:HAS_ATTRIBUTE]->(a:Attribute)
                RETURN u, collect({type: type(r), target: a}) as connections
                """
                
                with self.neo4j.driver.session() as session:
                    result = session.run(user_query, user_id=user_id)
                    
                    for record in result:
                        # User node
                        user_node = record.get("u")
                        if user_node:
                            snapshot["nodes"].append({
                                "id": dict(user_node).get("id"),
                                "labels": list(user_node.labels),
                                "properties": dict(user_node)
                            })
                        
                        # Connected nodes
                        connections = record.get("connections", [])
                        for conn in connections:
                            if conn.get("target"):
                                target = conn["target"]
                                snapshot["nodes"].append({
                                    "id": dict(target).get("name"),
                                    "labels": list(target.labels),
                                    "properties": dict(target)
                                })
                                
                                snapshot["relationships"].append({
                                    "type": conn.get("type"),
                                    "from": user_id,
                                    "to": dict(target).get("name")
                                })
            
            elif self.neo4j.use_local:
                # Use local JSON if Neo4j not available
                profile = self.neo4j.read_profile(user_id)
                snapshot["nodes"].append({
                    "id": user_id,
                    "labels": ["User"],
                    "properties": {"id": user_id}
                })
                
                for attr in profile.get("attributes", []):
                    snapshot["nodes"].append({
                        "id": attr,
                        "labels": ["Attribute"],
                        "properties": {"name": attr}
                    })
                    snapshot["relationships"].append({
                        "type": "HAS_ATTRIBUTE",
                        "from": user_id,
                        "to": attr
                    })
        
        except Exception as e:
            snapshot["error"] = str(e)
        
        # Save snapshot
        filename = f"{scenario_id}_{run_id}_{when}.json"
        filepath = os.path.join(self.snapshot_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        
        return filepath

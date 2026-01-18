import json
import os
import yaml
import requests
from typing import List, Dict

class SearchService:
    def __init__(self, config_path="config/settings.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        
        self.api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        self.cx = os.getenv("GOOGLE_SEARCH_CX")
        self.fallback_path = self.config["search"]["fallback_db_path"]
        self.num_results = self.config["search"].get("num_results", 3)
        
        # Ensure fallback data exists for demo/offline
        if not os.path.exists(self.fallback_path):
            os.makedirs(os.path.dirname(self.fallback_path), exist_ok=True)
            with open(self.fallback_path, "w") as f:
                json.dump([
                    {"title": "Fallback: Work Stress", "snippet": "Managing work stress...", "keywords": ["tired", "rest"]},
                    {"title": "Fallback: Deadline Anxiety", "snippet": "How to handle deadlines...", "keywords": ["stress", "deadline"]}
                ], f)

    def search(self, query: str, intention_keywords: List[str] = None) -> List[Dict]:
        """
        Intention-Aware Search.
        Combines query with intention keywords if provided.
        """
        combined_query = query
        if intention_keywords:
            # We add keywords to guide the context, but keep it natural
            combined_query += " " + " ".join(intention_keywords)
            
        print(f"Searching for: {combined_query}")

        if self.api_key and self.cx:
            try:
                return self._google_search(combined_query)
            except Exception as e:
                print(f"Internet Search Failed ({e}). Falling back to local DB.")
                return self._local_search(combined_query)
        else:
            print("Google Search API Key or CX not found. Using fallback.")
            return self._local_search(combined_query)
    
    def _google_search(self, query: str) -> List[Dict]:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": self.num_results
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        items = data.get("items", [])
        results = []
        
        for item in items:
            results.append({
                "title": item.get("title", "No Title"),
                "snippet": item.get("snippet", "No Snippet"),
                "link": item.get("link", "")
            })
            
        return results

    def _local_search(self, query: str) -> List[Dict]:
        with open(self.fallback_path, "r") as f:
            data = json.load(f)
        
        results = []
        query_terms = set(query.lower().split())
        
        for item in data:
            item_keywords = set(item.get("keywords", []))
            # Simple keyword overlap or just return all for small fallback DB
            if query_terms.intersection(item_keywords):
                results.append(item)
                
        if not results:
            # If no match, just return first item as a dummy fallback to prevent crash
            results.append(data[0] if data else {"title": "No Data", "snippet": "Empty DB"})
            
        return results

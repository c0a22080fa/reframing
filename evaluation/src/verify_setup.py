import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.search_service import SearchService
from services.comet_service import CometService
from services.openai_service import OpenAIService

def verify():
    print("--- Verifying Setup ---")
    load_dotenv("config/.env")
    
    # 1. API Keys Check
    # 1. API Keys Check
    openai_key = os.getenv('AZURE_OPENAI_API_KEY')
    search_key = os.getenv('GOOGLE_SEARCH_API_KEY')
    search_cx = os.getenv('GOOGLE_SEARCH_CX')
    
    print(f"OPENAI_KEY Present: {bool(openai_key)}")
    print(f"SEARCH_KEY Present: {bool(search_key)}")
    print(f"SEARCH_CX Present: {bool(search_cx)}")
    
    # 2. Search Verification
    print("\n--- Testing Search Service ---")
    search = SearchService()
    try:
        results = search.search("tired from coding", intention_keywords=["rest", "health"])
        print(f"Results found: {len(results)}")
        print(results[0])
    except Exception as e:
        print(f"Search Failed: {e}")

    # 3. COMET Verification
    print("\n--- Testing COMET Service (Translation + Inference) ---")
    # Initialize OpenAI first
    openai_service = OpenAIService()
    comet = CometService(openai_service=openai_service)
    
    try:
        # Test translation + reasoning
        # "I am exhausted"
        res = comet.translate_and_infer("仕事で疲れ果てた")
        print("Input: 仕事で疲れ果てた")
        print(f"Translation: {res.get('source_en')}")
        print(f"Inferences (xWant): {res.get('xWant')}")
    except Exception as e:
        print(f"COMET Failed: {e}")

if __name__ == "__main__":
    verify()

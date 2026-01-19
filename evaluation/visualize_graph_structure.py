
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from workflow.graph import build_graph

try:
    app = build_graph(condition="C1")
    print(app.get_graph().draw_mermaid())
except Exception as e:
    print(f"Error: {e}")

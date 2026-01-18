# Deep Abductive Nudge System (Reframing Agent)

This system implements a **Cognitive Architecture for Reframing**, leveraging **LangGraph** to orchestrate a "Discussion" between specialized agents. It generates behavioral nudges (EAST Framework) by identifying the user's "Deep Intent" through an abductive reasoning process.

## 🚀 Key Features

*   **Agentic Orchestration (Chair Controller)**: Uses a central "Profiler Chair" agent to dynamically call tools (COMET, Explorer) based on reasoning needs, avoiding rigid linear flows.
*   **System 1 & System 2 Hybrid**: Combines intuitive common-sense reasoning (**COMET/Atomic2020**) with analytical search (**Google RAG**) to form hypotheses.
*   **Persistent Context (PKG)**: Maintains a Personal Knowledge Graph of the user.
    *   **Auto-Fallback**: If a Neo4j server is not available, it automatically switches to a **Local JSON Graph** (`data/pkg_graph.json`) to ensure data persistence works out-of-the-box.
*   **Loop Prevention**: The Chair agent is "History-Aware" to prevent infinite loops of evidence gathering.

---

## 🏗 Architecture

The system follows a star topology centered around the **Profiler Chair**:

```mermaid
graph TD;
    Input[Input Processor] --> Chair[Profiler Chair];
    Chair -- "Need Intuition?" --> Validator[Witness (COMET)];
    Validator --> Chair;
    Chair -- "Need Validation?" --> Explorer[Explorer Agent (Google Search)];
    Explorer --> Chair;
    Chair -- "TENTATIVE Conclusion" --> Critic[Critic Agent];
    Critic -- "REJECT (Loop)" --> Chair;
    Critic -- "APPROVE" --> Memory[Memory Node (PKG Write)];
    Memory --> Nudge[Nudge Agent];
```

### Agents
1.  **Input Processor**: Parses input and retrieves User Profile (Attributes, Constraints).
2.  **Profiler Chair (The Brain)**: Orchestrates the flow. Decides whether to gather more evidence (Intuition vs. Facts) or finalize the hypothesis.
3.  **Witness (System 1)**: Uses `mosaickg/gpt2-xl-atomic2020` to infer implicit wants/needs (`xWant`, `xIntent`).
4.  **Explorer (System 2)**: Perform "Intent-Aware Search" via Google API (or fallback) to find analogous solutions.
5.  **Memory Node**: Persists the finalized "Deep Intent" into the Knowledge Graph.
6.  **Nudge Agent**: Generates a behavioral intervention using the EAST Framework (Easy, Attractive, Social, Timely).

---

## 🛠 Prerequisites

### Environment
- Python 3.9+ recommended.
- **RAM**: At least 16GB (for the COMET model ~6GB).
- **Neo4j**: Optional. (System defaults to `data/pkg_graph.json` if Neo4j is not running).

### API Keys
Create a `config/.env` file:

```ini
# --- Azure OpenAI (Reasoning Core) ---
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# --- Google Search (Explorer Agent) ---
GOOGLE_SEARCH_API_KEY=your_google_key
GOOGLE_SEARCH_CX=your_cse_id

# --- Neo4j (Optional) ---
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

---

## 💻 Usage

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Run the System
The main entry point uses **LangGraph**:

```bash
PYTHONPATH=. .venv/bin/python src/run_graph.py
```

*   **Interactive Mode**: The system will prompt for `[User Input]`.
*   **Example Input**: `京都に来ているが、雨が降っていて最悪` (I'm in Kyoto but it's raining and it's the worst.)
*   **Trace**: You will see the agents discussing, tools being called, and the final Nudge generation.
*   **Exit**: Type `exit` to quit.

### 3. Verification
To inspect the **Discussion Log** and **Agent Graph**, check:
- `docs/discussion_log.md`: Detailed trace of the last reasoning session.
- `docs/agent_graph.mermaid`: Visual representation of the agent execution flow.

---

## 📂 Project Structure

- `src/workflow/graph.py`: **Main Logic**. Defines the LangGraph structure and Node functions.
- `src/agents/`: Agent implementations.
- `src/services/`: Service wrappers (Neo4j, COMET, OpenAI, Google).
- `src/prompts/`: Agent Prompt Templates (`.txt`).
- `data/pkg_graph.json`: **Local PKG Storage** (created automatically).

---

## 🔍 Troubleshooting

*   **Neo4j Connection Failed**:
    *   This is normal if you don't have Neo4j running. The system will print `Switching to LOCAL JSON GRAPH mode` and continue normally.
*   **COMET Loading Slow**:
    *   The first run downloads the model (6GB). Subsequent runs use the cache.
*   **Looping?**:
    *   The Chair agent has logic to detect repeated calls. If you see it looping, check the logs or `agent_chair.txt` prompt.

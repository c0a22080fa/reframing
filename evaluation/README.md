# Evaluation Environment Setup & Execution Guide

This directory contains the automated evaluation suite for the "Divergent-Convergent Co-creative Loop" system.

## 1. Prerequisites (Target Environment)

Ensure the following are installed in your execution environment:
*   **Docker & Docker Compose**: Required for the Neo4j Knowledge Graph.
*   **Python 3.10+**: For running the system.
*   **OpenAI API Key**: Required for the User Simulator and System Agents (unless using Mock mode).

## 2. Setup Instructions

### Step 1: Start Neo4j (Knowledge Graph)
The system is configured to use a local Neo4j instance via Docker.

```bash
# From the project root (reframing_system/)
docker compose up -d
```
*   Verifies connection at `localhost:7687` (User: `neo4j`, Pass: `password`).
*   Access the browser UI at `http://localhost:7474`.

### Step 2: Install Dependencies
Install the required Python packages in your virtual environment.

```bash
# If creating a new venv
python -m venv .venv
source .venv/bin/activate

# Install requirements (from the evaluation copy)
pip install -r evaluation/requirements.txt
```

### Step 3: Configure Environment Variables
Create a `.env` file in the project root or export variables:

```bash
export OPENAI_API_KEY="sk-..."
export AZURE_OPENAI_API_KEY="..." # If using Azure
export AZURE_OPENAI_ENDPOINT="..." 
```

## 3. Running the Evaluation

### A. Data Generation (Optional / Pre-generated)
The full dataset (20 personas, 200 scenarios) is already generated at `evaluation/data/scenarios.json`.
To regenerate or extend it:
```bash
python evaluation/data/generate_dataset.py
```

### B. Run the Evaluation Loop
This script iterates through all scenarios defined in `scenarios.json`.

```bash
python evaluation/run_eval.py
```
*   **Simulator**: Acts as the user, following the specific logic of each Scenario (including Lv4 forced corrections).
*   **System**: Runs the full LangGraph agent workflow.
*   **Logging**:
    *   `evaluation/logs/episode_log_YYYYMMDD_...json`: High-level success/fail rates.
    *   `evaluation/logs/turn_log_YYYYMMDD_...json`: Detailed turn-by-turn dialogue logs.

## 4. Analyzing Results
After execution, analyze the JSON logs to calculate metrics:
1.  **Phase Success Rate**: Count `phase_success.P1`, `P2`, `P3` in episode logs.
2.  **Turn Efficiency**: Average `turns_total` per complexity level.
3.  **Correction handling**: Check `S_Pxxx_04` (Lv4) scenarios for Turn > 3 and successful recovery.

## 5. Troubleshooting
*   **Neo4j Connection Failed**: The system falls back to "Local JSON Mode". Check `docker ps` to ensure the container is running and healthy.
*   **OpenAI Errors**: Ensure keys are valid. If keys are missing, the system uses a Mock LLM (Fixed sequence), which works for verifying flow but not for qualitative evaluation.

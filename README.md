# Deep Abductive Nudge System - Execution Guide

This document describes how to set up and run the Nudge reframing experiment system using **Azure OpenAI** and **COMET**.

## 1. Prerequisites

### Environment
- Python 3.8+
- [Neo4j Desktop](https://neo4j.com/download/) (running locally)
- Internet connection (for initial model download)
- **RAM**: At least 16GB recommended (for COMET model)
- **GPU** (Optional): Faster inference if available (CUDA)

### API Keys
Get the following keys ready:
1.  **Azure OpenAI Service**:
    *   API Key
    *   Endpoint URL
    *   Deployment Name (e.g., `gpt-4`)
2.  **Google Custom Search**:
    *   [API Key](https://developers.google.com/custom-search/v1/introduction)
    *   [Search Engine ID (CX)](https://cse.google.com/cse/all)

## 2. Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```
*Note: This includes torch, transformers, neo4j, etc. It may take a few minutes.*

### Step 2: Configure Environment
Edit `config/.env` and fill in your keys:

```bash
nano config/.env
```

**Example (.env):**
```ini
# --- Azure OpenAI ---
AZURE_OPENAI_API_KEY=12345abcdef...
AZURE_OPENAI_ENDPOINT=https://my-resource.openai.azure.com/

# --- Google Search ---
GOOGLE_SEARCH_API_KEY=AIzaSy...
GOOGLE_SEARCH_CX=0123456789...

# --- Neo4j ---
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

### Step 3: Check Settings
Ensure `config/settings.yaml` matches your Azure Deployment name:
```yaml
model:
  openai_deployment: "gpt-4" # Change this to match your Azure Model Deployment Name
  openai_api_version: "2023-05-15"
```

## 3. COMET Model Setup (System 1 Intuition)

This system uses **COMET (Atomic 2020)** for generating common-sense inferences.

### Automatic Download
The code is configured to automatically download the model (`mosaickg/gpt2-xl-atomic2020`) from HuggingFace upon the first run.
- **Model Size**: Approx 6GB.
- **Cache Location**: Standard HuggingFace cache (`~/.cache/huggingface/hub`).

### Manual Handling
If you have a slow connection or offline server, you can manually download the model via git-lfs:
```bash
git lfs install
git clone https://huggingface.co/mosaickg/gpt2-xl-atomic2020
```
Then update `comet_model_path` in `settings.yaml` to point to your local folder.

### Resource Usage
- **Memory**: The `gpt2-xl` model is large. If you encounter Out-Of-Memory (OOM) errors, modify `settings.yaml` to use a smaller model:
    - Path: `mosaickg/gpt2-xl-atomic2020` (Best performance)
    - Alternative: `gpt2` (Poor reasoning, but runs on anything)

## 4. Running the System

### Verification
Run the verification script to check connections and **COMET Model**:
```bash
python3 src/verify_setup.py
```
*Expected Output*:
- Keys: True
- COMET Model loaded successfully (may take time on first run)
- Inferences: e.g. `xWant: to go to sleep`

### Main Application
Run the interactive chat loop:
```bash
python3 src/main.py
```

## 5. Experimentation

To run a batch of experiments (e.g., 50 cases), you can create a simple script leveraging `AbductionSquad` and `NudgeAgent`. (See `src/main.py` for usage patterns).

## Troubleshooting
- **COMET Model Error**: If download fails, check internet. If OOM, try closing other apps or use a smaller model.
- **Search Error (400/403)**: Check Google API quota and settings.


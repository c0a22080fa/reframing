# Implementation Plan: Multi-Turn Co-creation Loop

## Goal
Transform the current single-shot flow into a multi-turn conversation that incrementally builds user commitment.
The flow will be:
1.  **Phase 1: Deep Intent Confirmation** (Check if the inferred intent is correct)
2.  **Phase 2: Reframing Proposal** (Propose a shift in perspective)
3.  **Phase 3: Concrete Action/Nudge** (Propose specific actions based on the accepted reframe)

## Proposed Changes

### 1. State Management
#### [MODIFY] [graph.py](file:///home/c0a22080fa/.gemini/antigravity/scratch/reframing_system/src/workflow/graph.py)
- Update `AgentState` to include:
    - `phase`: Enum or string ("INTENT", "REFRAME", "ACTION").
    - `confirmed_intent`: Boolean.
    - `accepted_reframe`: Boolean.
- The graph structure will need to be **persistent** or support loops to handle multiple user inputs. Note: Since `run_graph.py` currently re-invokes the app from scratch for each input loop, we will implement this by **persisting state in memory** or checking previous messages to determine the current phase.
- *Simplification for this iteration*: We will use the `messages` history in `AgentState` to determine what to do next.

### 2. New Nodes / Prompts
We will break the current `nudge_agent` logic into three distinct interaction steps.

#### [NEW] [src/agents/dialogue_agent.py] (and corresponding node)
- **Node 1: Intent Confirmer**: Notifies user of the inferred intent and asks "Is this what you mean?"
- **Node 2: Reframe Proposer**: Generated a perspective shift (without action) and asks "How does this perspective feel?"
- **Node 3: Action Suggester**: (The existing Nudge logic, but focused on concrete steps).

#### [MODIFY] [src/workflow/graph.py] - The "Router"
- We need a **Router Node** that looks at the `messages` history.
    - If `messages` is empty -> Start **Abduction** (Divergence Loop).
    - If Abduction finishes -> **Output Intent Confirmation**.
    - If User replies to Intent -> Check agreement.
        - If "Yes" -> **Output Reframe**.
        - If "No" -> **Restart Abduction** (with correction).
    - If User replies to Reframe -> Check agreement.
        - If "Yes" -> **Output Action Nudge** (Convergence).

### 3. Execution Flow
Since `LangGraph` typically runs to completion, we will "interrupt" the graph at each user interaction point.
However, in the current CLI `run_graph.py` loop:
- usage: `app.invoke(inputs)` runs until `END`.
- To support multi-turn, we effectively need `checkpointer` or we pass the *entire conversation history* back into the graph each time.
- **Approach**: We will pass `messages` list back in. The `router` node will decide where to jump.

## Detailed Steps
1.  **Create Prompts**:
    - `prompts/dialogue_intent_check.txt`
    - `prompts/dialogue_reframe_check.txt`
2.  **Update Graph Logic**:
    - Change `input_processor` to be a `router`.
    - If it's a new topic -> go to `profiler_chair` (Divergence).
    - If it's a reply -> go to `dialogue_manager` to parse Y/N and advance phase.
3.  **Update `run_graph.py`**:
    - Maintain `history` variable outside the `while` loop.
    - Pass `history` into `initial_state`.

## Verification
- Test the flow interactively:
    - User: "Rainy Kyoto..."
    - Bot: "So you want to enjoy...?"
    - User: "Yes"
    - Bot: "How about viewing it as..."
    - User: "Yes"
    - Bot: "Go to this cafe..."

# Implementation Plan: Design Alignment Fixes

## Goal
Align the implementation with the design document "A Divergent–Convergent Co-creative Loop Implementation" by addressing two key discrepancies:
1.  **Context Agent**: Implement role-conditioned subgraph retrieval instead of monolithic context dumping.
2.  **Nudge Agent**: Update the output format to include specific fields (Reframed Perspective, Concrete Step, Invitation, Revision Question).

## User Review Required
> [!NOTE]
> The `ContextAgent.retrieve_context` method signature will change to include a `role` parameter. This requires updating all call sites in `src/workflow/graph.py`.

## Proposed Changes

### Context Agent & Retrieval
#### [MODIFY] [context_agent.py](file:///home/c0a22080fa/.gemini/antigravity/scratch/reframing_system/src/agents/context_agent.py)
- Update `retrieve_context(user_id, role="general")`.
- Implement logic to filter context fields based on roles:
    - `chair`: Needs everything (History, Evidence, Profile).
    - `explorer`: Needs mainly 'Deep Intent' context and 'System 1' intuition (to find analogies), less emphasis on static profile details unless relevant.
    - `critic`: Needs strict 'Profile Attributes' (for contradiction checking) and 'Evidence Summary'.
    - `nudge`: Needs 'Deep Intent', 'Profile' (for tone), and 'East Framework' constraints.

#### [MODIFY] [graph.py](file:///home/c0a22080fa/.gemini/antigravity/scratch/reframing_system/src/workflow/graph.py)
- Update `node_input_processor`, `node_profiler_chair`, `node_explorer`, `node_critic`, `node_nudge` to call `retrieve_context` with their respective roles.

### Nudge Agent Output
#### [MODIFY] [agent_nudge.txt](file:///home/c0a22080fa/.gemini/antigravity/scratch/reframing_system/src/prompts/agent_nudge.txt)
- Update the SYSTEM prompt to enforce the following JSON structure:
  ```json
  {
    "reframed_perspective": "...",
    "concrete_next_step": "...",
    "invitation_text": "...",
    "revision_question": "...",
    "east_justification": { ... }
  }
  ```

#### [MODIFY] [run_graph.py](file:///home/c0a22080fa/.gemini/antigravity/scratch/reframing_system/src/run_graph.py)
- Update the final output printing logic to nicely display the new structured nudge fields if available.

## Verification Plan
### Automated Tests
- None (Manual verification via `run_graph.py`).

### Manual Verification
- Run `python src/run_graph.py` with a sample query (e.g., "Kyoto in the rain").
- Verify logs to see `ContextAgent` providing different contexts for different nodes.
- Verify final output displays the 4 distinct nudge components.

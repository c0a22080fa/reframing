import json
import random
import os

# --- Configuration ---
NUM_PERSONAS = 20
SCENARIOS_PER_PERSONA = 10
OUTPUT_FILE = "evaluation/data/scenarios.json"

DOMAINS = ["work", "hobby", "health", "decision", "relationship", "study", "finance", "home"]

# Template Data for randomness
GOAL_TEMPLATES = [
    {"domain": "work", "goals": ["効率を上げたい", "ミスを減らしたい", "新しいスキルを習得したい"], "constraints": ["No overtime", "Low energy", "Limited budget"]},
    {"domain": "hobby", "goals": ["もっとPhotographyを楽しみたい", "読書を習慣にしたい", "絵を描きたい"], "constraints": ["Budget", "Time", "Space"]},
    {"domain": "health", "goals": ["運動を続けたい", "睡眠を改善したい", "食生活を直したい"], "constraints": ["Knee pain", "No gym", "Busy schedule"]},
    {"domain": "study", "goals": ["勉強を始めたい", "集中力を高めたい", "英語を話せるようになりたい"], "constraints": ["Noisy environment", "Short attention span", "No money"]},
]

def generate_scenario(persona_id, scenario_idx, level):
    # Select Domain & Template
    template = random.choice(GOAL_TEMPLATES)
    domain = template["domain"]
    goal = random.choice(template["goals"])
    
    # Bundle Constraints
    primary = [random.choice(template["constraints"])]
    secondary = []
    if level in ["Lv2", "Lv3", "Lv4"]:
        secondary.append(random.choice([c for c in template["constraints"] if c != primary[0]]))
    
    # Internal Tension (Lv3)
    tensions = []
    if level == "Lv3":
        tensions = ["Wants result but fears effort", "Cognitive dissonance"]

    # Lv4 Control
    lv4_control = {
        "correction_type": None,
        "trigger_phase": None,
        "correction_text": None,
        "trap_cues": []
    }
    if level == "Lv4":
        lv4_control = {
            "correction_type": "intent",
            "trigger_phase": "P1_post",
            "correction_text": "Actually, I don't care about efficiency, I just want to feel safe.",
            "trap_cues": ["Efficiency keywords"]
        }
        
    # Gold (Mocked for template efficiency)
    gold = {
        "gold_intent": f"Deep intent behind '{goal}': Seeking meaningful connection or relief.",
        "gold_value_direction": "Self-efficacy",
        "gold_reframing_direction": "Shift from external outcome to internal state.",
        "gold_actionability_requirements": ["Action 1", "Action 2"]
    }

    # User Utterances
    utterances = {
        "initial_utterance": goal,
        "phase1_response_yes": "Yes, exactly.",
        "phase1_response_no_with_correction": lv4_control["correction_text"],
        "phase2_response_yes": "That sounds good.",
        "phase2_response_no_with_correction": None,
        "phase3_response_accept": "I'll try that.",
        "phase3_response_revise_accept": "Can we change the location?",
        "phase3_response_reject": "No thanks."
    }

    return {
        "scenario_id": f"S_{persona_id}_{scenario_idx:02d}",
        "persona_id": persona_id,
        "complexity_level": level,
        "domain": domain,
        "setting": {
            "context_summary": f"Context for {goal}",
            "time_budget": "2 hours" if random.random() > 0.5 else None,
            "resource_constraints": ["Time" if random.random() > 0.5 else "Energy"],
            "external_constraints": [],
            "internal_tensions": tensions
        },
        "user_goal": {
            "stated_goal": goal,
            "goal_ambiguity": "clear" if level == "Lv1" else "ambiguous"
        },
        "constraint_bundle": {
            "primary_constraints": primary,
            "secondary_constraints": secondary
        },
        "gold": gold,
        "lv4_control": lv4_control,
        "user_utterances": utterances,
        "evaluation_tags": {
            "has_correction": level == "Lv4",
            "correction_difficulty": "high" if level == "Lv4" else "low",
            "expected_failure_modes": []
        }
    }

def main():
    scenarios = []
    
    # Distribution per Persona:
    # 1 Lv1, 2 Lv2, 1 Lv3, 1 Lv4 -> Total 5? 
    # User asked for 10 per persona.
    # User Spec: 1 Lv1, 2 Lv2, 1 Lv3, 1 Lv4 = 5. 
    # Let's double: 2 Lv1, 4 Lv2, 2 Lv3, 2 Lv4 = 10.
    
    LEVEL_DIST = ["Lv1", "Lv1", "Lv2", "Lv2", "Lv2", "Lv2", "Lv3", "Lv3", "Lv4", "Lv4"]
    
    for p in range(1, NUM_PERSONAS + 1):
        pid = f"P{p:03d}"
        for i, level in enumerate(LEVEL_DIST, 1):
            sc = generate_scenario(pid, i, level)
            scenarios.append(sc)
            
    # Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"scenarios": scenarios}, f, indent=2, ensure_ascii=False)
        
    print(f"Generated {len(scenarios)} scenarios at {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

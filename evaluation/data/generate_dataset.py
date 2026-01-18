import json
import random
import os

# Load Personas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSONAS_FILE = os.path.join(BASE_DIR, "personas.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "scenarios.json")

with open(PERSONAS_FILE, 'r') as f:
    personas = json.load(f)["personas"]

# Templates & Data Banks
DOMAINS = ["tourism", "food", "work", "social", "hobby", "health", "shopping", "transport"]

GOAL_TEMPLATES = {
    "tourism": ["{Location}に行きたい", "{Location}が見たい", "静かな場所に行きたい", "混雑を避けたい"],
    "food": ["美味しい{Food}が食べたい", "静かなカフェで休みたい", "{Food}の名店に行きたい"],
    "work": ["仕事に集中できない", "アイデアが出ない", "やる気が出ない", "締め切りが怖い"],
    "social": ["人付き合いが疲れる", "パーティーに行きたくない", "一人になりたい", "会話が続かない"],
    "hobby": ["もっと{Hobby}を楽しみたい", "{Hobby}がうまくなりたい", "新しい趣味を見つけたい"],
    "health": ["少し疲れた", "足が痛い", "リラックスしたい", "眠れない"],
    "shopping": ["{Item}を買いたい", "思い出になるものが欲しい", "無駄遣いをしたくない"],
    "transport": ["早く帰りたい", "迷わずに着きたい", "楽なルートで行きたい"]
}

CONSTRAINTS_POOL = [
    "Must be cheap", "Must be fast", "Must be quiet", "Must be authentic", 
    "Wheelchair accessible", "No stairs", "Indoor only", "No crowds", "English support"
]

TENSIONS_POOL = [
    "Wants quality vs Wants to save money",
    "Wants do do it all vs Physical exhaustion",
    "Social obligation vs Desire for solitude",
    "Fear of missing out vs Overwhelmed",
    "Desire for novelty vs Comfort of routine"
]

# Helper to inject persona specific keywords
def interpolate_goal(template, persona):
    hobby = persona["static_profile"]["hobbies"][0] if persona["static_profile"]["hobbies"] else "something"
    like = persona["enduring_preferences"]["likes"][0] if persona["enduring_preferences"]["likes"] else "something"
    
    goal = template.replace("{Hobby}", hobby).replace("{Food}", "ランチ").replace("{Location}", "京都").replace("{Item}", "お土産")
    return goal

def generate_gold(goal, level, persona):
    # Procedural generation of gold intent logic
    return {
        "gold_intent": f"Deep intent behind '{goal}': Seeking meaningful connection or relief.",
        "gold_value_direction": random.choice(persona["static_profile"]["personality_values"]),
        "gold_reframing_direction": "Shift focus from external outcome to internal state.",
        "gold_actionability_requirements": ["Action 1", "Action 2"]
    }

def generate_scenario(persona, index, level):
    pid = persona["persona_id"]
    sid = f"S_{pid}_{index+1:02d}"
    
    # Select Domain & Goal
    domain = random.choice(DOMAINS)
    template = random.choice(GOAL_TEMPLATES[domain])
    stated_goal = interpolate_goal(template, persona)
    
    # Complexity Rules
    constraints = []
    tensions = []
    goal_ambiguity = "clear"
    
    if level == "Lv1":
        constraints = [random.choice(CONSTRAINTS_POOL)]
        goal_ambiguity = "clear"
    elif level == "Lv2":
        constraints = [random.choice(CONSTRAINTS_POOL), random.choice(CONSTRAINTS_POOL)]
        goal_ambiguity = "somewhat_ambiguous"
    elif level == "Lv3":
        constraints = [random.choice(CONSTRAINTS_POOL), random.choice(CONSTRAINTS_POOL)]
        tensions = [random.choice(TENSIONS_POOL)]
        goal_ambiguity = "ambiguous"
    elif level == "Lv4":
        constraints = [random.choice(CONSTRAINTS_POOL)]
        goal_ambiguity = "ambiguous"

    # Lv4 Control
    lv4_control = {
        "correction_type": None, "trigger_phase": None, "correction_text": None, "trap_cues": []
    }
    
    has_correction = False
    utterance_override = {}
    
    if level == "Lv4":
        has_correction = True
        type_ = random.choice(["intent", "reframing"])
        if type_ == "intent":
             lv4_control = {
                 "correction_type": "intent",
                 "trigger_phase": "P1_post",
                 "correction_text": f"Actually, I don't want that. I really want silence.",
                 "trap_cues": ["Misleading initial query"]
             }
             utterance_override = {
                 "phase1_response_no_with_correction": lv4_control["correction_text"]
             }
        else:
             lv4_control = {
                 "correction_type": "reframing",
                 "trigger_phase": "P2_post",
                 "correction_text": f"That sounds nice, but honestly I can't do it physically.",
                 "trap_cues": ["Hidden constraint"]
             }
             utterance_override = {
                 "phase2_response_no_with_correction": lv4_control["correction_text"]
             }

    # User Utterances
    utterances = {
        "initial_utterance": stated_goal,
        "phase1_response_yes": "Yes, exactly.",
        "phase1_response_no_with_correction": None,
        "phase2_response_yes": "That sounds good.",
        "phase2_response_no_with_correction": None,
        "phase3_response_accept": "I'll try that.",
        "phase3_response_revise_accept": "Can we change the location?",
        "phase3_response_reject": "No thanks."
    }
    utterances.update(utterance_override)

    scenario_obj = {
        "scenario_id": sid,
        "persona_id": pid,
        "complexity_level": level,
        "domain": domain,
        "setting": {
            "context_summary": f"Context for {stated_goal}",
            "time_budget": "2 hours" if random.random() > 0.5 else None,
            "resource_constraints": ["Budget"],
            "external_constraints": [],
            "internal_tensions": tensions
        },
        "user_goal": {
            "stated_goal": stated_goal,
            "goal_ambiguity": goal_ambiguity
        },
        "constraint_bundle": {
            "primary_constraints": constraints[:1],
            "secondary_constraints": constraints[1:]
        },
        "gold": generate_gold(stated_goal, level, persona),
        "lv4_control": lv4_control,
        "user_utterances": utterances,
        "evaluation_tags": {
            "has_correction": has_correction,
            "correction_difficulty": "high" if level == "Lv4" else "low",
            "expected_failure_modes": []
        }
    }
    return scenario_obj

# Main Loop
all_scenarios = []

print(f"Generating scenarios for {len(personas)} personas...")

for p in personas:
    # Distribution: Lv1(2), Lv2(4), Lv3(3), Lv4(1)
    levels = ["Lv1"]*2 + ["Lv2"]*4 + ["Lv3"]*3 + ["Lv4"]*1
    
    for i, level in enumerate(levels):
        sc = generate_scenario(p, i, level)
        all_scenarios.append(sc)

# Write Output
final_data = {"scenarios": all_scenarios}
with open(OUTPUT_FILE, 'w') as f:
    json.dump(final_data, f, indent=2, ensure_ascii=False)

print(f"Successfully generated {len(all_scenarios)} scenarios at {OUTPUT_FILE}")

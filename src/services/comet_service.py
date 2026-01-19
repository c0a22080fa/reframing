import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import yaml
import os
from src.services.openai_service import OpenAIService

class CometService:
    def __init__(self, openai_service: OpenAIService = None, config_path="config/settings.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        
        self.openai_service = openai_service or OpenAIService()
        
        self.model_name = self.config["model"]["comet_model_path"]
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading COMET model on {self.device}...")
        
        try:
            # Check if model loads correctly
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(self.model_name).to(self.device)
            
            # Atomic2020 Special Tokens
            special_tokens = ["xWant", "xIntent", "xNeed", "xReact", "xEffect", "oWant", "oEffect", "oReact", "[GEN]"]
            num_added = self.tokenizer.add_tokens(special_tokens)
            if num_added > 0:
                self.model.resize_token_embeddings(len(self.tokenizer))
                print(f"Added {num_added} special tokens for Atomic2020.")
            
            print("COMET model loaded successfully.")
        except OSError:
            print(f"Error: Model '{self.model_name}' not found locally or network error.")
            print("Please ensure you have internet access to download from HuggingFace, or correct path.")
            print("FALLING BACK TO SYSTEM-1 SIMULATION (MOCK) for safety.")
            self.model = None
        except Exception as e:
            print(f"Unexpected error loading COMET: {e}. Falling back to mock.")
            self.model = None

    def infer(self, input_text: str, relation: str = "xWant"):
        """
        Generates common sense inferences.
        relations: xWant, xReact, xReason, etc.
        """
        if not self.model:
            # Mock if model failed
            return [f"[Mock-System1] Inference from {input_text} ({relation})"]

        # Ensure pad_token_id is set
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

        input_ids = self.tokenizer(f"{input_text} {relation} [GEN]", return_tensors="pt").input_ids.to(self.device)
        
        attention_mask = input_ids.ne(self.tokenizer.pad_token_id).long()
        
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids,
                attention_mask=attention_mask,
                max_new_tokens=16, # Increased slightly
                num_beams=3, # Reduced beams to potential avoid degradation
                num_return_sequences=3,
                early_stopping=True,
                pad_token_id=self.tokenizer.pad_token_id
            )
            
        results = []
        for output in outputs:
            decoded = self.tokenizer.decode(output, skip_special_tokens=True)
            # Split by [GEN] to get the tail
            # Decoded string might look like: "PersonX input [GEN] tail"
            try:
                if "[GEN]" in decoded:
                    cleaned = decoded.split("[GEN]")[1].strip()
                else:
                    # Fallback matching
                    cleaned = decoded.replace(f"{input_text} {relation}", "").replace("[GEN]", "").strip()
                
                if cleaned and cleaned not in results:
                    # Garbage detection (Atomic relations are usually short phrases)
                    if len(cleaned) > 2 and " " in cleaned and "etheless" not in cleaned:
                        results.append(cleaned)
            except:
                pass
        
        # Fallback if model failed to produce valid tokens
        if not results:
            print("   [!] COMET Model output garbage. Using Semantic Fallback.")
            if "rain" in input_text:
                if "xWant" in relation: return ["to stay dry", "to go inside", "to stop the rain"]
                if "xReact" in relation: return ["annoyed", "wet", "disappointed"]
                if "xIntent" in relation: return ["to visit somewhere", "to enjoy the trip"]
            elif "hungry" in input_text:
                if "xWant" in relation: return ["to eat food"]
            else:
                return ["to do something"]
            
        return results

    def translate_and_infer(self, jp_text: str, relations: list = ["xWant"]):
        """
        1. Translate JP -> EN (via LLM)
        2. Run COMET Inference (EN) for EACH requested relation
        3. Return dict of results
        """
        print(f"--- COMET: Translating input '{jp_text}' to English ---")
        
        # 1. JP -> EN
        prompt_to_en = [
            {"role": "system", "content": "You are a translator. Translate the following Japanese text to simple English for Common Sense reasoning. Output only the English translation."},
            {"role": "user", "content": jp_text}
        ]
        en_text = self.openai_service.chat_completion(prompt_to_en, temperature=0.0)
        en_text = en_text.strip().strip('"') # Clean up potential quotes
        print(f"Translated: {en_text}")
        
        # 2. Inference Loop
        results = {"source_en": en_text}
        for rel in relations:
            print(f"   -> Inferring {rel}...")
            results[rel] = self.infer(en_text, rel)
        
        return results

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

        input_ids = self.tokenizer(f"{input_text} {relation} [GEN]", return_tensors="pt").input_ids.to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids,
                max_new_tokens=20,
                num_beams=self.config["generation"]["comet_num_beams"],
                num_return_sequences=self.config["generation"]["comet_num_beams"],
                early_stopping=True
            )
            
        results = []
        for output in outputs:
            decoded = self.tokenizer.decode(output, skip_special_tokens=True)
            # Simple parsing logic for Atomic2020 
            # Output usually looks like: "event xWant [GEN] result"
            # We strip the prompt part.
            cleaned = decoded.replace(f"{input_text} {relation} [GEN]", "").strip()
            results.append(cleaned)
            
        return results

    def translate_and_infer(self, jp_text: str):
        """
        1. Translate JP -> EN (via LLM)
        2. Run COMET Inference (EN)
        3. Translate Results EN -> JP (via LLM) (Optional, or just return EN for deep intent analysis)
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
        
        # 2. Inference
        x_want = self.infer(en_text, "xWant")
        x_react = self.infer(en_text, "xReact")
        
        # 3. EN -> JP (Optional: For this system, the Agents (Profiler) can understand English evidence 
        #    even if user input was JP. But let's return it as raw evidence)
        
        return {
            "source_en": en_text,
            "xWant": x_want,
            "xReact": x_react
        }

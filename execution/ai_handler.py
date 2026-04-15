import os
import json
import requests
from typing import Dict, Any
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

class AIGatewayClient:
    def __init__(self):
        self.url = os.getenv("AI_GATEWAY_URL", "https://api.openai.com/v1/chat/completions")
        self.key = os.getenv("AI_GATEWAY_KEY")
        self.model = os.getenv("AI_GATEWAY_MODEL", "gpt-4o")

    def parse_preferences(self, text: str) -> Dict[str, Any]:
        """
        Parses user's natural language food preference into structured JSON.
        """
        if not text or not self.key:
            return {"ingredients": [], "diet": None, "macro_focus": None}

        prompt = f"""
        You are a nutrition assistant. Break down the following user food preference into structured JSON:
        User Text: "{text}"

        Respond ONLY with a JSON object in this format:
        {{
          "preferred_ingredients": ["list", "of", "ingredients"],
          "avoid_ingredients": ["list", "of", "ingredients"],
          "diet_type": "veg" or "non_veg" or null,
          "macro_focus": "high_protein" or "low_carb" or "low_fat" or null,
          "taste_keywords": ["spicy", "sweet", etc]
        }}
        """

        try:
            headers = {
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            }
            # Only add response_format if it's not a restricted model or if we want to try it
            # payload["response_format"] = {"type": "json_object"}

            response = requests.post(self.url, headers=headers, json=payload, timeout=15)
            
            if response.status_code != 200:
                print(f"AI Gateway Status Code: {response.status_code}")
                print(f"AI Gateway Response Body: {response.text}")
                response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Robust JSON extracting if the model didn't use json_object mode
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "{" in content:
                # Find the first { and last }
                start = content.find("{")
                end = content.rfind("}") + 1
                content = content[start:end]
            
            return json.loads(content)
        except Exception as e:
            print(f"AI Gateway Error: {e}")
            return {"ingredients": [], "diet": None, "macro_focus": None}

if __name__ == "__main__":
    # Test
    text = "I like chicken and want high protein meals, no rice"
    client = AIGatewayClient()
    print(client.parse_preferences(text))

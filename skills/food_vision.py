import os
import json
from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise Exception("GEMINI_API_KEY not found in .env")

genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.5-flash")


def analyze_food_image(image_path: str):
    """
    Analyze a food image using Gemini Vision.
    """

    image = Image.open(image_path)

    prompt = """
You are an expert food quality inspector.

Analyze this food image carefully.

Return ONLY valid JSON.

{
  "food_name":"",
  "confidence":0,
  "freshness_score":0,
  "freshness":"Fresh / Slightly Stale / Spoiled",
  "detected_issues":[],
  "nutrition":{
      "calories":"",
      "protein":"",
      "fat":"",
      "carbohydrates":""
  },
  "health_rating":"",
  "recommendation":"",
  "recipe_suggestions":[]
}

Rules:

1. Detect the food correctly.
2. Estimate freshness.
3. Mention visible defects.
4. Estimate nutrition.
5. Suggest healthy recipes.
6. Return JSON ONLY.
"""

    response = model.generate_content(
        [prompt, image]
    )

    text = response.text.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "")

    if text.endswith("```"):
        text = text[:-3]

    return json.loads(text)
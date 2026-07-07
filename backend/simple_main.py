"""
FoodAI Backend — fully AI-powered via Gemini 2.5 Flash.

Every endpoint calls the Gemini API directly through google-genai,
sending the actual uploaded image for vision analysis.  No dummy data.
"""

import os
import sys
import json
import logging
import base64

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from google import genai

# ── Load env ──────────────────────────────────────────────────────────
load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not GEMINI_KEY:
    raise RuntimeError(
        "No Gemini API key found. "
        "Set GEMINI_API_KEY or GOOGLE_API_KEY in backend/.env"
    )

client = genai.Client(api_key=GEMINI_KEY)
MODEL = "gemini-2.5-flash"

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("FoodAI")

# ── FastAPI app ───────────────────────────────────────────────────────
app = FastAPI(title="FoodAI Backend (AI-Powered)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ──────────────────────────────────────────────────
class UserProfile(BaseModel):
    user_id: str
    age: int
    goal: str
    diet: str
    allergies: List[str]


class RecipeRequest(BaseModel):
    user_id: str
    food_name: str
    preferences: Optional[str] = "Healthy"


# ── Helper: call Gemini and parse JSON from the response ─────────────
def _extract_json(text: str) -> dict:
    """Try to parse JSON from a Gemini response that may contain markdown fences."""
    cleaned = text.strip()
    # Strip ```json ... ``` wrappers if present
    if cleaned.startswith("```"):
        # Remove first line (```json) and last line (```)
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Return as raw text if Gemini didn't produce valid JSON
        return {"raw_response": text}


# ── Endpoints ─────────────────────────────────────────────────────────
@app.get("/")
async def health_check():
    return {
        "status": "ok",
        "ai": "Gemini 2.5 Flash",
        "message": "FoodAI AI-Powered server is running.",
    }


@app.post("/analyze-food")
async def analyze_food(
    user_id: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Accepts a food image upload.  Sends the image directly to Gemini for:
      1. Food identification
      2. Quality grading
      3. Nutrition estimation
      4. Health recommendation
      5. Recipe suggestion
    Returns a single structured JSON response.
    """
    logger.info(f"/analyze-food  user={user_id}  file={file.filename}")

    try:
        img_bytes = await file.read()
        mime = file.content_type or "image/jpeg"

        # Build the multimodal prompt
        prompt = """You are FoodAI, an expert food analyst.

Analyze the uploaded food image carefully and return a **single JSON object** with exactly these keys (no extra text, no markdown fences):

{
  "food_name": "<name of the food item>",
  "description": "<short 1-line description, e.g. 'Raw, whole, skin-on'>",
  "confidence": <float 0-1, how confident you are in the identification>,
  "quality_grade": "<Grade A, Grade B, or Grade C>",
  "freshness_score": <integer 0-100>,
  "detected_issues": ["<issue1>", "<issue2>"],
  "nutrition": {
    "calories": <integer kcal>,
    "protein": "<e.g. 3g>",
    "carbs": "<e.g. 25g>",
    "fat": "<e.g. 0.3g>",
    "fiber": "<e.g. 4g>"
  },
  "health_recommendation": "<2-3 sentence personalized health tip>",
  "suggested_recipe": {
    "name": "<recipe name>",
    "brief": "<1-line description of the recipe>"
  }
}

Only return the JSON object. No explanation before or after."""

        # Call Gemini with the actual image bytes
        response = client.models.generate_content(
            model=MODEL,
            contents=[
                prompt,
                genai.types.Part.from_bytes(data=img_bytes, mime_type=mime),
            ],
        )

        result = _extract_json(response.text)
        logger.info(f"AI result: {json.dumps(result)[:300]}")
        return {"analysis": result}

    except Exception as e:
        logger.error(f"AI analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")


@app.post("/recommend")
async def recommend(profile: UserProfile):
    """Health recommendation based on a user profile — fully AI-powered."""
    logger.info(f"/recommend  user={profile.user_id}")
    try:
        prompt = f"""You are a certified nutritionist AI.

User profile:
- Age: {profile.age}
- Goal: {profile.goal}
- Diet: {profile.diet}
- Allergies: {', '.join(profile.allergies) if profile.allergies else 'None'}

Return a JSON object:
{{
  "recommended_foods": ["<food1>", "<food2>", ...],
  "avoid_foods": ["<food1>", "<food2>", ...],
  "meal_plan": {{
    "breakfast": "<meal>",
    "lunch": "<meal>",
    "dinner": "<meal>",
    "snacks": "<snack ideas>"
  }},
  "tips": "<2-3 sentence health tip>"
}}

Only return the JSON object."""

        response = client.models.generate_content(model=MODEL, contents=prompt)
        result = _extract_json(response.text)
        return {"recommendation": result}

    except Exception as e:
        logger.error(f"Recommendation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


@app.post("/recipe")
async def recipe(request: RecipeRequest):
    """Recipe generation — fully AI-powered."""
    logger.info(f"/recipe  user={request.user_id}  food={request.food_name}")
    try:
        prompt = f"""You are a professional chef AI.

Create a healthy recipe using: {request.food_name}
Preference: {request.preferences}

Return a JSON object:
{{
  "recipe_name": "<name>",
  "ingredients": ["<item1>", "<item2>", ...],
  "steps": ["<step1>", "<step2>", ...],
  "cooking_time": "<e.g. 30 minutes>",
  "nutrition": {{
    "calories": <int>,
    "protein": "<e.g. 15g>",
    "carbs": "<e.g. 30g>",
    "fat": "<e.g. 10g>"
  }}
}}

Only return the JSON object."""

        response = client.models.generate_content(model=MODEL, contents=prompt)
        result = _extract_json(response.text)
        return {"recipe": result}

    except Exception as e:
        logger.error(f"Recipe error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Recipe generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

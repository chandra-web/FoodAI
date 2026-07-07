"""
Health recommendation skill.

Entry point:
    generate_health_recommendation(profile: dict) -> dict

Uses Gemini to produce a personalised health plan based on the user's
physical attributes, lifestyle, medical conditions, and fitness goals.
"""
from __future__ import annotations

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

_GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
_MODEL_NAME: str = "gemini-2.5-flash"

_HEALTH_PROMPT_TEMPLATE = """
You are a certified nutritionist and personal health coach.
Generate a personalised health recommendation for the following user profile:

Age: {age}
Gender: {gender}
Height: {height_cm} cm
Weight: {weight_kg} kg
BMI: {bmi}
Activity Level: {activity_level}
Diet Preference: {diet_preference}
Allergies: {allergies}
Medical Conditions: {medical_conditions}
Fitness Goal: {fitness_goal}

Return ONLY a single valid JSON object. No markdown fences, no prose.

{{
  "daily_calorie_target": <integer — recommended daily kcal>,
  "foods_to_eat": ["<food item>", ...],
  "foods_to_avoid": ["<food item>", ...],
  "meal_plan": {{
    "breakfast": "<description>",
    "lunch": "<description>",
    "dinner": "<description>",
    "snacks": "<description>"
  }},
  "water_recommendation": "<plain-English recommendation, e.g. '2.5 litres per day'>",
  "exercise_suggestion": "<plain-English exercise plan tailored to the user's goal>",
  "weekly_habits": ["<habit 1>", "<habit 2>", ...],
  "ai_explanation": "<2–3 paragraph explanation of the rationale behind these recommendations>"
}}
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _safe_str(value, default: str = "Not specified") -> str:
    if value is None or (isinstance(value, (list, dict)) and not value):
        return default
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


async def generate_health_recommendation(profile: dict) -> dict:
    """
    Generate a personalised health recommendation using Gemini.

    Args:
        profile: Dict containing user health attributes.  Expected keys
                 (all optional — missing values fall back to 'Not specified'):
                 age, gender, height_cm, weight_kg, bmi, activity_level,
                 diet_preference, allergies, medical_conditions, fitness_goal.

    Returns:
        Parsed dict with keys: daily_calorie_target, foods_to_eat,
        foods_to_avoid, meal_plan, water_recommendation, exercise_suggestion,
        weekly_habits, ai_explanation.

    Raises:
        ValueError: If Gemini returns non-JSON output.
        RuntimeError: If the API key is not configured.
    """
    if not _GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY (or GEMINI_API_KEY) environment variable is not set."
        )

    bmi = profile.get("bmi")
    if bmi is None:
        h = profile.get("height_cm")
        w = profile.get("weight_kg")
        if h and w and h > 0:
            bmi = round(w / ((h / 100) ** 2), 1)

    prompt = _HEALTH_PROMPT_TEMPLATE.format(
        age=_safe_str(profile.get("age")),
        gender=_safe_str(profile.get("gender")),
        height_cm=_safe_str(profile.get("height_cm")),
        weight_kg=_safe_str(profile.get("weight_kg")),
        bmi=_safe_str(bmi),
        activity_level=_safe_str(profile.get("activity_level")),
        diet_preference=_safe_str(profile.get("diet_preference")),
        allergies=_safe_str(profile.get("allergies")),
        medical_conditions=_safe_str(profile.get("medical_conditions")),
        fitness_goal=_safe_str(profile.get("fitness_goal")),
    )

    try:
        from google import genai
        client = genai.Client(api_key=_GOOGLE_API_KEY)
        response = client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
        )
        raw_text = response.text if hasattr(response, "text") else ""
    except ImportError:
        import google.generativeai as legacy_genai  # type: ignore
        legacy_genai.configure(api_key=_GOOGLE_API_KEY)
        model = legacy_genai.GenerativeModel(model_name=_MODEL_NAME)
        response = model.generate_content(prompt)
        raw_text = response.text if hasattr(response, "text") else ""
    clean_text = _strip_fences(raw_text)

    try:
        result: dict = json.loads(clean_text)
    except json.JSONDecodeError as exc:
        logger.error(
            "Health recommendation response is not valid JSON.\nRaw: %s\nError: %s",
            raw_text[:500],
            exc,
        )
        raise ValueError(
            f"Gemini returned non-JSON output for health recommendation. "
            f"Snippet: {raw_text[:200]!r}"
        ) from exc

    logger.info(
        "Health recommendation generated: calorie_target=%s",
        result.get("daily_calorie_target"),
    )
    return result
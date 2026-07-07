"""
Recipe generation skill.

Entry point:
    generate_recipe(food_name: str, preferences: str, user_profile: dict | None) -> dict

Uses Gemini to generate a detailed, structured recipe tailored to the
given food name, dietary preferences, and optional user profile.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

_GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
_MODEL_NAME: str = "gemini-2.5-flash"

_RECIPE_PROMPT_TEMPLATE = """
You are a world-class chef and nutritionist.
Generate a detailed, practical recipe for "{food_name}".

Dietary preferences / constraints: {preferences}
{profile_section}

Return ONLY a single valid JSON object. No markdown fences, no prose.

{{
  "title": "<recipe title>",
  "description": "<1–2 sentence enticing description>",
  "ingredients": [
    {{"name": "<ingredient>", "quantity": "<amount>", "unit": "<unit, e.g. g, ml, tbsp>"}},
    ...
  ],
  "prep_time_min": <integer>,
  "cook_time_min": <integer>,
  "difficulty": "<Easy | Medium | Hard>",
  "nutrition": {{
    "calories": <number — kcal per serving>,
    "protein_g": <number>,
    "carbs_g": <number>,
    "fat_g": <number>
  }},
  "steps": ["<Step 1: ...>", "<Step 2: ...>", ...],
  "chef_tips": ["<tip 1>", "<tip 2>", ...],
  "storage_instructions": "<how to store leftovers>",
  "healthy_alternatives": ["<alternative 1>", "<alternative 2>", ...],
  "is_vegetarian": <true | false>,
  "is_vegan": <true | false>
}}
"""

_PROFILE_SECTION_TEMPLATE = """
User profile to tailor the recipe:
  - Age: {age}, Gender: {gender}
  - Diet preference: {diet_preference}
  - Allergies: {allergies}
  - Medical conditions: {medical_conditions}
  - Fitness goal: {fitness_goal}
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


async def generate_recipe(
    food_name: str,
    preferences: str,
    user_profile: Optional[dict] = None,
) -> dict:
    """
    Generate a structured recipe using Gemini.

    Args:
        food_name: Name of the dish / food item to create a recipe for.
        preferences: Free-text dietary preferences, e.g. ``"low-carb, dairy-free"``.
        user_profile: Optional dict with user health attributes used to further
                      personalise the recipe (keys: age, gender, diet_preference,
                      allergies, medical_conditions, fitness_goal).

    Returns:
        Parsed dict with keys: title, description, ingredients, prep_time_min,
        cook_time_min, difficulty, nutrition, steps, chef_tips,
        storage_instructions, healthy_alternatives, is_vegetarian, is_vegan.

    Raises:
        ValueError: If Gemini returns non-JSON output.
        RuntimeError: If the API key is not configured.
    """
    if not _GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY (or GEMINI_API_KEY) environment variable is not set."
        )

    # Build optional profile section
    profile_section = ""
    if user_profile:
        profile_section = _PROFILE_SECTION_TEMPLATE.format(
            age=_safe_str(user_profile.get("age")),
            gender=_safe_str(user_profile.get("gender")),
            diet_preference=_safe_str(user_profile.get("diet_preference")),
            allergies=_safe_str(user_profile.get("allergies")),
            medical_conditions=_safe_str(user_profile.get("medical_conditions")),
            fitness_goal=_safe_str(user_profile.get("fitness_goal")),
        )

    prompt = _RECIPE_PROMPT_TEMPLATE.format(
        food_name=food_name,
        preferences=preferences or "No specific preferences",
        profile_section=profile_section,
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
            "Recipe response is not valid JSON.\nRaw: %s\nError: %s",
            raw_text[:500],
            exc,
        )
        raise ValueError(
            f"Gemini returned non-JSON output for recipe generation. "
            f"Snippet: {raw_text[:200]!r}"
        ) from exc

    logger.info(
        "Recipe generated: title='%s' difficulty='%s'",
        result.get("title"),
        result.get("difficulty"),
    )
    return result
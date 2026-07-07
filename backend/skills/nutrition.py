"""
Nutrition data skill.

Entry point:
    get_nutrition_data(food_name: str) -> dict

Strategy:
  1. Try OpenFoodFacts API — free, comprehensive.
  2. Fall back to Gemini if OpenFoodFacts returns nothing useful.

Returned dict keys:
  calories, protein_g, carbs_g, fat_g, fiber_g, sugar_g, sodium_mg,
  vitamins (dict), minerals (dict), source ('openfoodfacts' | 'gemini_estimate')
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

_GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
_MODEL_NAME: str = "gemini-2.5-flash"

_OFF_SEARCH_URL = (
    "https://world.openfoodfacts.org/cgi/search.pl"
    "?search_terms={query}&search_simple=1&action=process&json=1&page_size=5"
)

_GEMINI_NUTRITION_PROMPT = """
You are a professional nutritionist.
For the food item "{food_name}", return ONLY a single valid JSON object with estimated nutrition
per 100g serving. Do NOT include markdown fences or extra prose.

Return exactly:
{{
  "calories": <number — kcal per 100g>,
  "protein_g": <number>,
  "carbs_g": <number>,
  "fat_g": <number>,
  "fiber_g": <number>,
  "sugar_g": <number>,
  "sodium_mg": <number>,
  "vitamins": {{
    "vitamin_c_mg": <number or null>,
    "vitamin_a_iu": <number or null>,
    "vitamin_d_iu": <number or null>,
    "vitamin_b12_mcg": <number or null>,
    "folate_mcg": <number or null>
  }},
  "minerals": {{
    "calcium_mg": <number or null>,
    "iron_mg": <number or null>,
    "potassium_mg": <number or null>,
    "magnesium_mg": <number or null>,
    "zinc_mg": <number or null>
  }}
}}
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _extract_off_product(product: dict) -> Optional[dict]:
    """Parse a raw OpenFoodFacts product dict into our normalised schema."""
    nutriments = product.get("nutriments", {})

    def _val(key: str) -> Optional[float]:
        """Return the per-100g value from nutriments, or None."""
        for suffix in ("_100g", "_serving", ""):
            v = nutriments.get(f"{key}{suffix}")
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
        return None

    calories = _val("energy-kcal") or _val("energy")
    if calories is None:
        return None  # not useful

    return {
        "calories": round(calories, 1),
        "protein_g": round(_val("proteins") or 0, 2),
        "carbs_g": round(_val("carbohydrates") or 0, 2),
        "fat_g": round(_val("fat") or 0, 2),
        "fiber_g": round(_val("fiber") or 0, 2),
        "sugar_g": round(_val("sugars") or 0, 2),
        "sodium_mg": round((_val("sodium") or 0) * 1000, 2),
        "vitamins": {
            "vitamin_c_mg": _val("vitamin-c"),
            "vitamin_a_iu": _val("vitamin-a"),
            "vitamin_d_iu": _val("vitamin-d"),
            "vitamin_b12_mcg": _val("vitamin-b12"),
            "folate_mcg": _val("folate"),
        },
        "minerals": {
            "calcium_mg": _val("calcium"),
            "iron_mg": _val("iron"),
            "potassium_mg": _val("potassium"),
            "magnesium_mg": _val("magnesium"),
            "zinc_mg": _val("zinc"),
        },
        "source": "openfoodfacts",
    }


async def _fetch_from_openfoodfacts(food_name: str) -> Optional[dict]:
    """Query OpenFoodFacts and return parsed nutrition or None."""
    url = _OFF_SEARCH_URL.format(query=quote(food_name))
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"User-Agent": "FoodAI/1.0"})
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("OpenFoodFacts request failed: %s", exc)
        return None

    products: list = data.get("products", [])
    for product in products:
        parsed = _extract_off_product(product)
        if parsed:
            logger.info(
                "OpenFoodFacts hit for '%s': calories=%s",
                food_name,
                parsed.get("calories"),
            )
            return parsed

    logger.info("No usable OpenFoodFacts result for '%s'", food_name)
    return None


async def _fetch_from_gemini(food_name: str) -> dict:
    """Use Gemini to estimate nutrition when OpenFoodFacts has no data."""
    if not _GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not set; cannot fall back to Gemini.")

    prompt = _GEMINI_NUTRITION_PROMPT.format(food_name=food_name)

    try:
        from google import genai
        client = genai.Client(api_key=_GOOGLE_API_KEY)
        response = client.models.generate_content(model=_MODEL_NAME, contents=prompt)
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
        logger.error("Gemini nutrition response is not valid JSON: %s", exc)
        return {
            "calories": 0,
            "protein_g": 0,
            "carbs_g": 0,
            "fat_g": 0,
            "fiber_g": 0,
            "sugar_g": 0,
            "sodium_mg": 0,
            "vitamins": {},
            "minerals": {},
            "source": "gemini_estimate_failed",
        }

    result["source"] = "gemini_estimate"
    logger.info("Gemini nutrition estimate for '%s': calories=%s", food_name, result.get("calories"))
    return result


async def get_nutrition_data(food_name: str) -> dict:
    """
    Return nutrition data for *food_name*.

    Tries OpenFoodFacts first; falls back to Gemini estimation.

    Args:
        food_name: Human-readable food name, e.g. ``"apple"`` or ``"chicken tikka masala"``.

    Returns:
        Normalised dict with keys: calories, protein_g, carbs_g, fat_g, fiber_g,
        sugar_g, sodium_mg, vitamins (dict), minerals (dict), source.
    """
    result = await _fetch_from_openfoodfacts(food_name)
    if result:
        return result

    logger.info("Falling back to Gemini for nutrition data: '%s'", food_name)
    return await _fetch_from_gemini(food_name)

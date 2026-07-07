"""
Gemini Vision skill — analyzes a food image and returns structured JSON.

Entry point:
    analyze_food_image(image_bytes: bytes, mime_type: str) -> dict
"""
from __future__ import annotations

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Key resolution
# ---------------------------------------------------------------------------

_GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
_MODEL_NAME: str = "gemini-2.5-flash"

_VISION_PROMPT = """
You are a professional food scientist and nutritionist.
Carefully examine the food image provided and return ONLY a single valid JSON object.
Do NOT include any markdown fences, prose, explanations, or extra text — just the raw JSON.

Return exactly these keys:
{
  "food_name": "<string — most likely food name>",
  "food_category": "<string — e.g. Fruit, Vegetable, Grain, Dairy, Meat, Snack, Beverage, Processed>",
  "confidence": <float 0.0–1.0 — how confident you are in the identification>,
  "freshness_score": <integer 0–100 — 100 = perfectly fresh, 0 = completely spoiled>,
  "quality_grade": "<A | B | C — overall quality grade>",
  "detected_defects": ["<string>", ...],
  "serving_size_estimate": "<string — e.g. 1 medium apple (182g)>",
  "possible_ingredients": ["<string>", ...],
  "allergens": ["<string>", ...],
  "shelf_life_estimate": "<string — e.g. 3–5 days at room temperature>",
  "storage_recommendation": "<string>",
  "suitable_for_children": <true | false>,
  "suitable_for_elderly": <true | false>,
  "suitable_for_diabetics": <true | false>,
  "suitable_for_weight_loss": <true | false>,
  "suitable_for_gym": <true | false>,
  "health_score": <integer 0–100 — overall healthiness>,
  "nutrition": {
    "calories": <integer>,
    "protein_g": <integer>,
    "carbs_g": <integer>,
    "fat_g": <integer>
  },
  "ai_summary": "<2–3 sentence plain-English summary of the food, its quality, and health implications>"
}
"""


def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` markdown fences."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


async def analyze_food_image(image_bytes: bytes, mime_type: str) -> dict:
    """
    Send *image_bytes* to Gemini Vision and return a structured dict.

    Args:
        image_bytes: Raw bytes of the uploaded image.
        mime_type: MIME type, e.g. ``"image/jpeg"`` or ``"image/png"``.

    Returns:
        Parsed dict matching the prompt schema.

    Raises:
        ValueError: If the model response cannot be parsed as JSON.
        RuntimeError: If the API key is not set.
    """
    if not _GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY (or GEMINI_API_KEY) environment variable is not set."
        )

    try:
        from google import genai
        from google.genai import types as genai_types

        client = genai.Client(api_key=_GOOGLE_API_KEY)

        logger.info(
            "Sending %d bytes (%s) to Gemini Vision model '%s'",
            len(image_bytes),
            mime_type,
            _MODEL_NAME,
        )

        response = client.models.generate_content(
            model=_MODEL_NAME,
            contents=[
                genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                _VISION_PROMPT,
            ],
        )

        raw_text: str = response.text if hasattr(response, "text") else ""

    except ImportError:
        # Fallback to legacy google.generativeai if installed
        import google.generativeai as legacy_genai  # type: ignore
        legacy_genai.configure(api_key=_GOOGLE_API_KEY)
        model = legacy_genai.GenerativeModel(model_name=_MODEL_NAME)
        image_part = {"mime_type": mime_type, "data": image_bytes}
        response = model.generate_content([_VISION_PROMPT, image_part])
        raw_text = response.text if hasattr(response, "text") else ""

    clean_text = _strip_fences(raw_text)

    try:
        result: dict = json.loads(clean_text)
    except json.JSONDecodeError as exc:
        logger.error(
            "Failed to parse Gemini vision response as JSON.\nRaw: %s\nError: %s",
            raw_text[:500],
            exc,
        )
        raise ValueError(
            f"Gemini returned non-JSON output for food image analysis. "
            f"Snippet: {raw_text[:200]!r}"
        ) from exc

    logger.info(
        "Vision analysis complete: food='%s' grade='%s' health_score=%s",
        result.get("food_name"),
        result.get("quality_grade"),
        result.get("health_score"),
    )
    return result
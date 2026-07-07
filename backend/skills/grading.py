"""
Food quality grading skill — pure Python, no AI calls required.

The vision skill already returns a quality_grade from Gemini.  These
functions provide a deterministic, rule-based alternative / verification
layer that can be applied to any freshness_score + defects pair.

Functions:
    compute_quality_grade(freshness_score, detected_defects) -> str
    compute_health_score(nutrition, freshness_score) -> int
"""
from __future__ import annotations

from typing import Union


def compute_quality_grade(
    freshness_score: Union[int, float],
    detected_defects: list,
) -> str:
    """
    Compute a quality grade from freshness and detected defects.

    Grading rules
    -------------
    A — freshness >= 80 AND fewer than 2 defects
    B — freshness >= 50 OR fewer than 4 defects
    C — anything else (very low freshness or many defects)

    Args:
        freshness_score: Integer or float in the range 0–100.
        detected_defects: List of defect strings returned by the vision skill.

    Returns:
        ``'A'``, ``'B'``, or ``'C'``.
    """
    score = float(freshness_score)
    n_defects = len(detected_defects) if detected_defects else 0

    if score >= 80 and n_defects < 2:
        return "A"
    if score >= 50 or n_defects < 4:
        return "B"
    return "C"


def compute_health_score(
    nutrition: dict,
    freshness_score: Union[int, float],
) -> int:
    """
    Compute a 0–100 health score using a weighted formula.

    Formula
    -------
    health_score = freshness_score * 0.4 + nutrition_bonus * 0.6

    ``nutrition_bonus`` (0–100) is built as follows:
      - Starts at 50 (neutral baseline)
      - +10 if protein_g >= 5  (protein-rich)
      - +10 if fiber_g >= 3    (high fibre)
      - +5  if fat_g < 5       (low fat)
      - -10 if sugar_g > 20    (high sugar)
      - -10 if sodium_mg > 600 (high sodium)
      - -5  if fat_g > 20      (high fat)
      - Clamped to [0, 100]

    Args:
        nutrition: Dict with keys: calories, protein_g, carbs_g, fat_g,
                   fiber_g, sugar_g, sodium_mg (any missing key defaults to 0).
        freshness_score: Integer or float in the range 0–100.

    Returns:
        Integer health score in the range 0–100.
    """
    protein = float(nutrition.get("protein_g", 0) or 0)
    fiber = float(nutrition.get("fiber_g", 0) or 0)
    fat = float(nutrition.get("fat_g", 0) or 0)
    sugar = float(nutrition.get("sugar_g", 0) or 0)
    sodium = float(nutrition.get("sodium_mg", 0) or 0)

    bonus = 50.0

    # Positive contributions
    if protein >= 5:
        bonus += 10
    if fiber >= 3:
        bonus += 10
    if fat < 5:
        bonus += 5

    # Negative contributions
    if sugar > 20:
        bonus -= 10
    if sodium > 600:
        bonus -= 10
    if fat > 20:
        bonus -= 5

    # Clamp bonus to [0, 100]
    bonus = max(0.0, min(100.0, bonus))

    raw_score = float(freshness_score) * 0.4 + bonus * 0.6
    return int(round(max(0.0, min(100.0, raw_score))))
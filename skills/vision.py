import base64
import json
from typing import Dict

# Import the simulated vision analysis function
from .food_vision import analyze_food_image

def analyze_food(image_path_or_description: str) -> Dict:
    """Wrapper skill for food vision analysis.

    The backend sends a base64‑encoded image string in the prompt. This wrapper
    accepts either a file path or a base64 image description, forwards it to the
    existing simulated analysis function, and returns the resulting dictionary.

    Args:
        image_path_or_description: Either a filesystem path to the image or a
            base64‑encoded image string.

    Returns:
        Dict containing keys such as ``food_name``, ``confidence``,
        ``freshness_score`` and ``detected_issues``.
    """
    # The existing ``analyze_food_image`` works with a description; we simply
    # forward the argument. In a real implementation we would decode the base64
    # string and run Gemini Pro Vision.
    result = analyze_food_image(image_path_or_description)
    # Ensure the result is JSON‑serializable (it already is a dict).
    return result

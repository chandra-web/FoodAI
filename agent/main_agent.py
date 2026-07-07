"""
FoodAI Agent — powered by Google ADK (google-adk).

Provides run_foodai_agent() which is called by the FastAPI backend (main.py).
"""

import os
import uuid
import pydantic
import tempfile
import logging
from typing import Any, Optional

from google.adk import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

logger = logging.getLogger("FoodAI.Agent")

# ---------------------------------------------------------------------------
# Structured output schema (returned as a dict by run_foodai_agent)
# ---------------------------------------------------------------------------
class FoodAnalysisResponse(pydantic.BaseModel):
    summary: str
    food_items: list[str]
    quality_grade: str
    nutrition_facts: dict
    recommendations: list[str]
    recipe_suggestions: list[str]


# ---------------------------------------------------------------------------
# Lazy imports for backend skills (keep agent.py self-contained when possible)
# ---------------------------------------------------------------------------
def _get_skills():
    import sys, os
    # Ensure backend dir is in path for skill imports
    backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from skills.vision import analyze_food
    from skills.grading import grade_food
    from skills.health import recommend_food
    from skills.recipe import generate_recipe
    return [analyze_food, grade_food, recommend_food, generate_recipe]


def _build_agent(system_instruction: str) -> Agent:
    return Agent(
        name="FoodAI",
        model="gemini-2.5-flash",
        description=(
            "AI food industry assistant that can analyze food images, "
            "grade quality, give nutrition advice, recommend healthy meals, "
            "and generate recipes."
        ),
        instruction=system_instruction,
        tools=_get_skills(),
    )


# ---------------------------------------------------------------------------
# Main entry-point called by main.py
# ---------------------------------------------------------------------------
async def run_foodai_agent(
    query: str,
    user_id: str,
    conversation_id: str = None,
) -> dict:
    """
    Run the FoodAI agent for a single query and return a response dict.

    Returns:
        {
            "conversation_id": str,
            "data": dict   # keys: summary, food_items, quality_grade,
                           #       nutrition_facts, recommendations, recipe_suggestions
        }
    """
    # Fetch persistent memory context from database (best-effort)
    user_memory = ""
    try:
        import sys as _sys
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in _sys.path:
            _sys.path.insert(0, project_root)
        from database.connection import SessionLocal
        from database.crud import get_user_memory
        db = SessionLocal()
        user_memory = get_user_memory(db, user_id) or ""
        db.close()
    except Exception as exc:
        logger.warning(f"Could not load user memory for {user_id}: {exc}")

    system_instruction = f"""You are FoodAI, an expert food analysis assistant.
You analyze food images, evaluate quality, provide nutrition information,
recommend healthy food, and generate recipes.

User Context & Memory:
{user_memory}

Always return a structured JSON response containing:
- summary: A brief summary of your findings
- food_items: A list of identified food items
- quality_grade: The assigned quality grade (Grade A, Grade B, or Grade C)
- nutrition_facts: Detailed nutrition intelligence (calories, protein, carbs, fat, fiber)
- recommendations: Personalized health recommendations (list of strings)
- recipe_suggestions: Generated recipes or cooking steps (list of strings)
"""

    conv_id = conversation_id or str(uuid.uuid4())

    # Build agent and runner for this request
    agent = _build_agent(system_instruction)
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="FoodAI",
        session_service=session_service,
    )

    # Create a session
    session = await session_service.create_session(
        app_name="FoodAI",
        user_id=user_id,
        session_id=conv_id,
    )

    # Build the user message
    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=query)],
    )

    # Run the agent and collect the final text response
    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=conv_id,
        new_message=user_content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(
                p.text for p in event.content.parts if hasattr(p, "text") and p.text
            )

    # Try to parse structured JSON from the response
    import json, re
    data: dict = {}
    try:
        # Strip markdown fences if present
        cleaned = final_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned.rstrip())
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        # Fall back to a raw_response key so the endpoint doesn't crash
        data = {"raw_response": final_text}

    return {
        "conversation_id": conv_id,
        "data": data,
    }


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio

    async def main():
        result = await run_foodai_agent(
            "I have a fresh apple. Can you analyze it and give me a recipe?",
            user_id="test_user",
        )
        import json
        print(json.dumps(result, indent=2, default=str))

    asyncio.run(main())

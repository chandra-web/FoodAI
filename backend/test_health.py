import asyncio
import os
from dotenv import load_dotenv

# Load env before importing skills
load_dotenv("/Users/govinddev/FoodAI/backend/.env")

from skills.health import generate_health_recommendation
import skills.health
skills.health._MODEL_NAME = "gemini-2.5-flash"

async def main():
    profile = {
        "age": 28,
        "goal": "Weight Loss",
        "diet": "Vegan",
        "allergies": ["Peanuts"]
    }
    try:
        res = await generate_health_recommendation(profile)
        print("Success:", res)
    except Exception as e:
        print("Error:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())

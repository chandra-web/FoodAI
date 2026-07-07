import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv("/Users/govinddev/FoodAI/.env")
from backend.skills.recipe import generate_recipe

async def test():
    try:
        recipe = await generate_recipe("Chicken", "Healthy", None)
        print("Success:", recipe)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())

import os
from google.adk.agents import Agent


from skills.vision import analyze_food
from skills.grading import grade_food
from skills.health import recommend_food
from skills.recipe import generate_recipe



food_agent = Agent(

    name="FoodAI",

    model="gemini-2.5-flash",

    description="""

    AI food industry assistant.

    Can:
    - analyze food images
    - grade food quality
    - give nutrition advice
    - recommend healthy meals
    - generate recipes

    """,

    tools=[

        analyze_food,
        grade_food,
        recommend_food,
        generate_recipe

    ]

)

# Configure the agent with the loaded skills and MCP servers
async def get_food_agent():
    # Setup MCP servers
    mcp_servers = [
        types.McpStdioServer(
            command="python3",
            args=["/app/mcp_servers/nutrition_server.py"],
        )
    ]
    
    config = LocalAgentConfig(
        model="gemini-2.5-flash",
        mcp_servers=mcp_servers,
        skills_paths=["/app/skills"]
    )
    
    system_instruction = """
You are FoodAI, an advanced food industry assistant.
You have access to a set of Agent Skills to help users with:
1. Food Vision Analysis & Quality Grading
2. Health Recommendations
3. Recipe Generation

You also have an MCP server for fetching Nutrition Intelligence.
Use your skills and tools to assist the user.
"""
    return Agent(config=config, system_instruction=system_instruction)

async def process_user_query(query: str, image_bytes: bytes = None, mime_type: str = "image/jpeg"):
    async with await get_food_agent() as agent:
        if image_bytes:
            # Note: For real applications with google-antigravity, you might need to upload the file or pass inline data depending on SDK support.
            # Here we assume the agent can accept text and instructions about an image, 
            # For simplicity, we just pass the query. A full implementation would use the proper types.Media or similar.
            response = await agent.chat(query)
            return await response.text()
        else:
            response = await agent.chat(query)
            return await response.text()

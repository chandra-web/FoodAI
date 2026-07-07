from mcp.server import fastmcp

# Initialize the MCP server
mcp = fastmcp.FastMCP("NutritionServer")

NUTRITION_DB = {
    "apple": {"calories": 52, "protein": "0.3g", "carbs": "14g", "fat": "0.2g", "vitamins": ["Vitamin C", "Vitamin K"], "minerals": ["Potassium"]},
    "banana": {"calories": 89, "protein": "1.1g", "carbs": "23g", "fat": "0.3g", "vitamins": ["Vitamin B6", "Vitamin C"], "minerals": ["Potassium", "Magnesium"]},
    "chicken breast": {"calories": 165, "protein": "31g", "carbs": "0g", "fat": "3.6g", "vitamins": ["Vitamin B6", "Niacin"], "minerals": ["Phosphorus", "Selenium"]},
    "broccoli": {"calories": 34, "protein": "2.8g", "carbs": "6.6g", "fat": "0.4g", "vitamins": ["Vitamin C", "Vitamin K"], "minerals": ["Iron", "Potassium"]},
    "salmon": {"calories": 208, "protein": "20g", "carbs": "0g", "fat": "13g", "vitamins": ["Vitamin B12", "Vitamin D"], "minerals": ["Selenium", "Potassium"]}
}

@mcp.tool()
def nutrition_lookup(food_name: str) -> dict:
    """Lookup detailed nutrition intelligence for a specific food item.
    
    Args:
        food_name: The name of the food item to lookup.
        
    Returns:
        A dictionary with calories, protein, carbs, fat, vitamins, and minerals.
    """
    food_name = food_name.lower().strip()
    try:
        # Search for partial matches
        for key, value in NUTRITION_DB.items():
            if key in food_name or food_name in key:
                return value
        return {"error": f"Nutrition info for '{food_name}' not found."}
    except Exception as e:
        return {"error": f"An error occurred during lookup: {str(e)}"}

if __name__ == "__main__":
    mcp.run()

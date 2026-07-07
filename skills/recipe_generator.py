def generate_recipe(food_items: list[str], preferences: str = "Healthy") -> dict:
    """Generates a complete recipe using the provided food items and preferences.
    
    Args:
        food_items: A list of main ingredients to include in the recipe.
        preferences: Any dietary preferences or styles (e.g., "Spicy", "Quick").
        
    Returns:
        A dictionary containing recipe_name, ingredients, steps, nutrition, and time.
    """
    base_item = food_items[0] if food_items else "Mystery Food"
    
    return {
        "recipe_name": f"{preferences} {base_item} Delight",
        "ingredients": food_items + ["Olive oil", "Salt", "Pepper", "Garlic"],
        "steps": [
            "Preheat oven to 400°F (200°C).",
            f"Prepare the {base_item} and season generously.",
            "Roast or cook for 20-30 minutes until golden brown.",
            "Serve warm and enjoy!"
        ],
        "nutrition": {
            "calories": 350,
            "protein": "15g",
            "carbs": "30g",
            "fat": "10g"
        },
        "time": "35 minutes"
    }

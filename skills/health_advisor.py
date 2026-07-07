def recommend_food(age: int, goal: str, diet: str, allergies: list[str]) -> dict:
    """Provides personalized health recommendations for food.
    
    Args:
        age: The user's age.
        goal: The user's fitness or health goal (e.g., "weight loss", "muscle gain").
        diet: The user's dietary preference (e.g., "vegan", "keto").
        allergies: A list of food allergies to avoid.
        
    Returns:
        A dictionary containing recommended_foods, avoid_foods, and a meal_plan.
    """
    # Simple mock logic based on inputs
    recommended = ["Quinoa", "Spinach", "Blueberries"]
    if "muscle" in goal.lower():
        recommended.extend(["Lentils", "Tofu", "Chicken breast"])
        
    avoid = list(allergies)
    if "vegan" in diet.lower():
        avoid.extend(["Dairy", "Meat", "Eggs", "Honey"])
        
    return {
        "recommended_foods": recommended,
        "avoid_foods": avoid,
        "meal_plan": {
            "breakfast": "Oatmeal with berries",
            "lunch": "Mixed green salad with quinoa",
            "dinner": "Grilled protein with steamed vegetables"
        }
    }

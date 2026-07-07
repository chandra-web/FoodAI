from mcp.server import fastmcp
from typing import Optional

# Initialize the MCP server
mcp = fastmcp.FastMCP("FoodDatabaseServer")

FOOD_DB = {
    "fruits": ["Apple", "Banana", "Orange", "Strawberry", "Mango"],
    "vegetables": ["Broccoli", "Spinach", "Carrot", "Onion", "Tomato"],
    "grains": ["Quinoa", "Brown Rice", "Oats", "Barley", "Wheat"],
    "processed food": ["Potato Chips", "Cookies", "Instant Noodles", "Soda", "Canned Soup"]
}

@mcp.tool()
def search_food(category: Optional[str] = None, query: Optional[str] = None) -> list[str]:
    """Search for food items in the database by category or specific keyword.
    
    Args:
        category: The category to search (e.g., 'fruits', 'vegetables', 'grains', 'processed food').
        query: A specific keyword to search for across all categories.
        
    Returns:
        A list of matching food items.
    """
    try:
        results = []
        
        # If a category is specified, return items from that category
        if category:
            cat_lower = category.lower()
            if cat_lower in FOOD_DB:
                results.extend(FOOD_DB[cat_lower])
            else:
                return [f"Error: Category '{category}' not found."]
                
        # If a query is provided, filter or search across all
        if query:
            q_lower = query.lower()
            if not category:
                # Search across all categories
                for items in FOOD_DB.values():
                    for item in items:
                        if q_lower in item.lower():
                            results.append(item)
            else:
                # Filter the already selected category results
                results = [item for item in results if q_lower in item.lower()]
                
        # If neither is provided, return all foods
        if not category and not query:
            for items in FOOD_DB.values():
                results.extend(items)
                
        return results
    except Exception as e:
        return [f"An error occurred during food search: {str(e)}"]

if __name__ == "__main__":
    mcp.run()

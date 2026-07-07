def grade_food(freshness_score: int) -> str:
    """Grades the quality of food based on its freshness score.
    
    Args:
        freshness_score: The freshness score (0-100) of the food item.
        
    Returns:
        A string representing the grade (Grade A, Grade B, or Grade C).
    """
    if freshness_score > 85:
        return "Grade A"
    elif freshness_score >= 60:
        return "Grade B"
    else:
        return "Grade C"

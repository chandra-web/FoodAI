"""
Async CRUD operations for FoodAI.

All functions accept an AsyncSession and return ORM model instances.
Callers are responsible for committing / rolling back the session.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.schema import (
    FoodAnalysis,
    HealthRecommendation,
    Recipe,
    User,
    UserProfile,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    hashed_password: str,
    full_name: Optional[str] = None,
) -> User:
    """Create and persist a new User record."""
    user = User(
        id=str(uuid.uuid4()),
        email=email.lower().strip(),
        hashed_password=hashed_password,
        full_name=full_name,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(user)
    await db.flush()  # get the generated PK without committing
    logger.info("Created user id=%s email=%s", user.id, user.email)
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Fetch a User by email (case-insensitive)."""
    result = await db.execute(
        select(User).where(User.email == email.lower().strip())
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Fetch a User by primary key."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# UserProfile
# ---------------------------------------------------------------------------


async def upsert_user_profile(
    db: AsyncSession,
    *,
    user_id: str,
    age: Optional[int] = None,
    gender: Optional[str] = None,
    height_cm: Optional[float] = None,
    weight_kg: Optional[float] = None,
    bmi: Optional[float] = None,
    activity_level: Optional[str] = None,
    diet_preference: Optional[str] = None,
    allergies: Optional[list] = None,
    medical_conditions: Optional[list] = None,
    fitness_goal: Optional[str] = None,
    water_intake_goal_ml: Optional[int] = None,
    daily_calorie_goal: Optional[int] = None,
) -> UserProfile:
    """Insert or update the UserProfile for the given user."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = UserProfile(
            id=str(uuid.uuid4()),
            user_id=user_id,
            created_at=datetime.utcnow(),
        )
        db.add(profile)

    # Apply updates for any provided (non-None) fields
    updates = {
        "age": age,
        "gender": gender,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "bmi": bmi,
        "activity_level": activity_level,
        "diet_preference": diet_preference,
        "allergies": allergies,
        "medical_conditions": medical_conditions,
        "fitness_goal": fitness_goal,
        "water_intake_goal_ml": water_intake_goal_ml,
        "daily_calorie_goal": daily_calorie_goal,
    }
    for field, value in updates.items():
        if value is not None:
            setattr(profile, field, value)

    profile.updated_at = datetime.utcnow()
    await db.flush()
    logger.info("Upserted profile for user_id=%s", user_id)
    return profile


async def get_user_profile(
    db: AsyncSession, user_id: str
) -> Optional[UserProfile]:
    """Fetch the UserProfile for a user."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# FoodAnalysis
# ---------------------------------------------------------------------------


async def create_food_analysis(
    db: AsyncSession,
    *,
    user_id: str,
    food_name: Optional[str] = None,
    food_category: Optional[str] = None,
    confidence: Optional[float] = None,
    freshness_score: Optional[float] = None,
    quality_grade: Optional[str] = None,
    detected_defects: Optional[list] = None,
    nutrition: Optional[dict] = None,
    health_score: Optional[float] = None,
    ai_summary: Optional[str] = None,
    image_url: Optional[str] = None,
) -> FoodAnalysis:
    """Persist a new FoodAnalysis record."""
    analysis = FoodAnalysis(
        id=str(uuid.uuid4()),
        user_id=user_id,
        food_name=food_name,
        food_category=food_category,
        confidence=confidence,
        freshness_score=freshness_score,
        quality_grade=quality_grade,
        detected_defects=detected_defects or [],
        nutrition=nutrition or {},
        health_score=health_score,
        ai_summary=ai_summary,
        image_url=image_url,
        created_at=datetime.utcnow(),
    )
    db.add(analysis)
    await db.flush()
    logger.info("Created food analysis id=%s for user_id=%s", analysis.id, user_id)
    return analysis


async def get_food_analyses_for_user(
    db: AsyncSession,
    user_id: str,
    *,
    page: int = 1,
    limit: int = 20,
) -> Sequence[FoodAnalysis]:
    """Return paginated food analyses for a user, newest first."""
    offset = (page - 1) * limit
    result = await db.execute(
        select(FoodAnalysis)
        .where(FoodAnalysis.user_id == user_id)
        .order_by(FoodAnalysis.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


async def get_food_analysis_by_id(
    db: AsyncSession, analysis_id: str, user_id: str
) -> Optional[FoodAnalysis]:
    """Fetch a single FoodAnalysis belonging to the specified user."""
    result = await db.execute(
        select(FoodAnalysis).where(
            FoodAnalysis.id == analysis_id,
            FoodAnalysis.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Recipe
# ---------------------------------------------------------------------------


async def create_recipe(
    db: AsyncSession,
    *,
    user_id: str,
    title: str,
    description: Optional[str] = None,
    ingredients: Optional[list] = None,
    steps: Optional[list] = None,
    prep_time_min: Optional[int] = None,
    cook_time_min: Optional[int] = None,
    difficulty: Optional[str] = None,
    nutrition: Optional[dict] = None,
    storage_tips: Optional[str] = None,
    healthy_alternatives: Optional[list] = None,
    is_vegetarian: bool = False,
    is_vegan: bool = False,
) -> Recipe:
    """Persist a new Recipe record."""
    recipe = Recipe(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=title,
        description=description,
        ingredients=ingredients or [],
        steps=steps or [],
        prep_time_min=prep_time_min,
        cook_time_min=cook_time_min,
        difficulty=difficulty,
        nutrition=nutrition or {},
        storage_tips=storage_tips,
        healthy_alternatives=healthy_alternatives or [],
        is_vegetarian=is_vegetarian,
        is_vegan=is_vegan,
        created_at=datetime.utcnow(),
    )
    db.add(recipe)
    await db.flush()
    logger.info("Created recipe id=%s for user_id=%s", recipe.id, user_id)
    return recipe


async def get_recipes_for_user(
    db: AsyncSession,
    user_id: str,
    *,
    page: int = 1,
    limit: int = 20,
) -> Sequence[Recipe]:
    """Return paginated recipes for a user, newest first."""
    offset = (page - 1) * limit
    result = await db.execute(
        select(Recipe)
        .where(Recipe.user_id == user_id)
        .order_by(Recipe.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


async def get_recipe_by_id(
    db: AsyncSession, recipe_id: str, user_id: str
) -> Optional[Recipe]:
    """Fetch a single Recipe belonging to the specified user."""
    result = await db.execute(
        select(Recipe).where(
            Recipe.id == recipe_id,
            Recipe.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# HealthRecommendation
# ---------------------------------------------------------------------------


async def save_health_recommendation(
    db: AsyncSession,
    *,
    user_id: str,
    daily_calorie_target: Optional[int] = None,
    foods_to_eat: Optional[list] = None,
    foods_to_avoid: Optional[list] = None,
    meal_plan: Optional[dict] = None,
    water_recommendation: Optional[str] = None,
    exercise_suggestion: Optional[str] = None,
    weekly_habits: Optional[list] = None,
    ai_explanation: Optional[str] = None,
) -> HealthRecommendation:
    """Persist a new HealthRecommendation record."""
    rec = HealthRecommendation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        daily_calorie_target=daily_calorie_target,
        foods_to_eat=foods_to_eat or [],
        foods_to_avoid=foods_to_avoid or [],
        meal_plan=meal_plan or {},
        water_recommendation=water_recommendation,
        exercise_suggestion=exercise_suggestion,
        weekly_habits=weekly_habits or [],
        ai_explanation=ai_explanation,
        created_at=datetime.utcnow(),
    )
    db.add(rec)
    await db.flush()
    logger.info(
        "Saved health recommendation id=%s for user_id=%s", rec.id, user_id
    )
    return rec


async def get_latest_health_recommendation(
    db: AsyncSession, user_id: str
) -> Optional[HealthRecommendation]:
    """Return the most recent HealthRecommendation for a user."""
    result = await db.execute(
        select(HealthRecommendation)
        .where(HealthRecommendation.user_id == user_id)
        .order_by(HealthRecommendation.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()

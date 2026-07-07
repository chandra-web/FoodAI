"""
SQLAlchemy ORM Models for FoodAI.

All tables use UUID primary keys and support full async operations.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from database.connection import Base


def _uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


class User(Base):
    """Core user account — stores credentials and basic identity."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True, default=_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    profile = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    food_analyses = relationship(
        "FoodAnalysis", back_populates="user", cascade="all, delete-orphan"
    )
    recipes = relationship(
        "Recipe", back_populates="user", cascade="all, delete-orphan"
    )
    health_recommendations = relationship(
        "HealthRecommendation", back_populates="user", cascade="all, delete-orphan"
    )


class UserProfile(Base):
    """Extended health & dietary profile for a user."""

    __tablename__ = "user_profiles"

    id = Column(String(36), primary_key=True, index=True, default=_uuid)
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Physical attributes
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)          # male | female | other
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)

    # Lifestyle
    activity_level = Column(String(50), nullable=True)  # sedentary | light | moderate | active | very_active
    diet_preference = Column(String(50), nullable=True)  # omnivore | vegetarian | vegan | keto | paleo
    allergies = Column(JSON, default=list)               # ["peanuts", "gluten", ...]
    medical_conditions = Column(JSON, default=list)      # ["diabetes", "hypertension", ...]

    # Goals
    fitness_goal = Column(String(100), nullable=True)   # weight_loss | muscle_gain | maintenance | ...
    water_intake_goal_ml = Column(Integer, default=2000)
    daily_calorie_goal = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="profile")


class FoodAnalysis(Base):
    """Stores the result of a Gemini Vision food image analysis."""

    __tablename__ = "food_analyses"

    id = Column(String(36), primary_key=True, index=True, default=_uuid)
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Vision results
    food_name = Column(String(255), nullable=True)
    food_category = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=True)           # 0.0–1.0
    freshness_score = Column(Float, nullable=True)      # 0–100
    quality_grade = Column(String(2), nullable=True)    # A | B | C
    detected_defects = Column(JSON, default=list)       # ["bruise", "mold", ...]

    # Nutrition
    nutrition = Column(JSON, default=dict)              # {calories, protein_g, carbs_g, ...}

    # Scores & insights
    health_score = Column(Float, nullable=True)         # 0–100
    ai_summary = Column(Text, nullable=True)
    image_url = Column(String(1024), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="food_analyses")


class Recipe(Base):
    """AI-generated recipe tied to a user."""

    __tablename__ = "recipes"

    id = Column(String(36), primary_key=True, index=True, default=_uuid)
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)

    # Structure
    ingredients = Column(JSON, default=list)    # [{name, quantity, unit}, ...]
    steps = Column(JSON, default=list)          # ["Step 1: ...", ...]

    # Timing & difficulty
    prep_time_min = Column(Integer, nullable=True)
    cook_time_min = Column(Integer, nullable=True)
    difficulty = Column(String(20), nullable=True)  # Easy | Medium | Hard

    # Nutrition & tips
    nutrition = Column(JSON, default=dict)          # {calories, protein_g, carbs_g, fat_g}
    storage_tips = Column(Text, nullable=True)
    healthy_alternatives = Column(JSON, default=list)

    # Dietary flags
    is_vegetarian = Column(Boolean, default=False)
    is_vegan = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="recipes")


class HealthRecommendation(Base):
    """Personalized health recommendation generated by Gemini."""

    __tablename__ = "health_recommendations"

    id = Column(String(36), primary_key=True, index=True, default=_uuid)
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Targets
    daily_calorie_target = Column(Integer, nullable=True)
    foods_to_eat = Column(JSON, default=list)    # ["salmon", "broccoli", ...]
    foods_to_avoid = Column(JSON, default=list)  # ["fried food", "soda", ...]

    # Meal plan
    meal_plan = Column(JSON, default=dict)  # {breakfast: "...", lunch: "...", dinner: "...", snacks: "..."}

    # Lifestyle
    water_recommendation = Column(Text, nullable=True)
    exercise_suggestion = Column(Text, nullable=True)
    weekly_habits = Column(JSON, default=list)  # ["Walk 10k steps daily", ...]

    # AI output
    ai_explanation = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="health_recommendations")

"""
FoodAI Backend — Production FastAPI Application.

Endpoints
---------
Auth (public):
  POST /auth/register
  POST /auth/login

Profile (JWT):
  GET  /profile
  PUT  /profile

Analysis (JWT):
  POST /analyze-food      (multipart upload)

Recipe (JWT):
  POST /generate-recipe

Health (JWT):
  POST /health-recommendation

History (JWT):
  GET  /history
  GET  /history/{analysis_id}

Legacy (X-API-Key):
  POST /recommend
  POST /recipe
"""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import List, Optional

from dotenv import load_dotenv

# ── Load .env before any module that reads env vars at import time ──────────
load_dotenv()

# ── Project root on sys.path so shared packages resolve correctly ───────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ── Standard library / third-party ─────────────────────────────────────────
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Security,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

# ── Internal modules ────────────────────────────────────────────────────────
from database.connection import create_all_tables, get_db
from database import crud
from security.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_api_key,
    verify_password,
)
from skills.vision import analyze_food_image
from skills.nutrition import get_nutrition_data
from skills.grading import compute_quality_grade, compute_health_score
from skills.recipe import generate_recipe
from skills.health import generate_health_recommendation
from skills.youtube import get_youtube_videos

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("FoodAI")

# ── Environment ──────────────────────────────────────────────────────────────
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
FRONTEND_URL: Optional[str] = os.getenv("FRONTEND_URL")

_ALLOWED_ORIGINS: list[str] = [
    "http://localhost:3000",
    "http://localhost:3001",
]
if FRONTEND_URL and FRONTEND_URL not in _ALLOWED_ORIGINS:
    _ALLOWED_ORIGINS.append(FRONTEND_URL)

# ── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all DB tables on startup."""
    logger.info("FoodAI backend starting — environment=%s", ENVIRONMENT)
    await create_all_tables()
    logger.info("Database tables ready.")
    yield
    logger.info("FoodAI backend shutting down.")


# ── FastAPI application ───────────────────────────────────────────────────────
app = FastAPI(
    title="FoodAI Backend",
    description="AI-powered food analysis, recipe generation, and personalised health recommendations.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Pydantic request / response schemas
# ============================================================================


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class ProfileRequest(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    activity_level: Optional[str] = None
    diet_preference: Optional[str] = None
    allergies: Optional[List[str]] = None
    medical_conditions: Optional[List[str]] = None
    fitness_goal: Optional[str] = None
    water_intake_goal_ml: Optional[int] = None
    daily_calorie_goal: Optional[int] = None


class RecipeRequest(BaseModel):
    food_name: str
    preferences: Optional[str] = "Healthy"
    use_profile: bool = False


class HealthRecommendationRequest(BaseModel):
    """Optional profile override — if omitted, the saved profile is used."""
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    activity_level: Optional[str] = None
    diet_preference: Optional[str] = None
    allergies: Optional[List[str]] = None
    medical_conditions: Optional[List[str]] = None
    fitness_goal: Optional[str] = None


# Legacy schemas ──────────────────────────────────────────────────────────────

class LegacyUserProfile(BaseModel):
    user_id: str
    age: int
    goal: str
    diet: str
    allergies: List[str]


class LegacyRecipeRequest(BaseModel):
    user_id: str
    food_name: str
    preferences: Optional[str] = "Healthy"


# ============================================================================
# Helpers
# ============================================================================


def _profile_to_dict(profile) -> dict:
    """Convert a UserProfile ORM instance to a plain dict for skills."""
    if profile is None:
        return {}
    return {
        "age": profile.age,
        "gender": profile.gender,
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "bmi": profile.bmi,
        "activity_level": profile.activity_level,
        "diet_preference": profile.diet_preference,
        "allergies": profile.allergies or [],
        "medical_conditions": profile.medical_conditions or [],
        "fitness_goal": profile.fitness_goal,
        "water_intake_goal_ml": profile.water_intake_goal_ml,
        "daily_calorie_goal": profile.daily_calorie_goal,
    }


def _analysis_to_dict(analysis) -> dict:
    """Convert a FoodAnalysis ORM instance to a serialisable dict."""
    return {
        "id": analysis.id,
        "user_id": analysis.user_id,
        "food_name": analysis.food_name,
        "food_category": analysis.food_category,
        "confidence": analysis.confidence,
        "freshness_score": analysis.freshness_score,
        "quality_grade": analysis.quality_grade,
        "detected_defects": analysis.detected_defects,
        "nutrition": analysis.nutrition,
        "health_score": analysis.health_score,
        "ai_summary": analysis.ai_summary,
        "image_url": analysis.image_url,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
    }


def _recipe_to_dict(recipe) -> dict:
    """Convert a Recipe ORM instance to a serialisable dict."""
    return {
        "id": recipe.id,
        "user_id": recipe.user_id,
        "title": recipe.title,
        "description": recipe.description,
        "ingredients": recipe.ingredients,
        "steps": recipe.steps,
        "prep_time_min": recipe.prep_time_min,
        "cook_time_min": recipe.cook_time_min,
        "difficulty": recipe.difficulty,
        "nutrition": recipe.nutrition,
        "storage_tips": recipe.storage_tips,
        "healthy_alternatives": recipe.healthy_alternatives,
        "is_vegetarian": recipe.is_vegetarian,
        "is_vegan": recipe.is_vegan,
        "created_at": recipe.created_at.isoformat() if recipe.created_at else None,
    }


def _health_rec_to_dict(rec) -> dict:
    """Convert a HealthRecommendation ORM instance to a serialisable dict."""
    return {
        "id": rec.id,
        "user_id": rec.user_id,
        "daily_calorie_target": rec.daily_calorie_target,
        "foods_to_eat": rec.foods_to_eat,
        "foods_to_avoid": rec.foods_to_avoid,
        "meal_plan": rec.meal_plan,
        "water_recommendation": rec.water_recommendation,
        "exercise_suggestion": rec.exercise_suggestion,
        "weekly_habits": rec.weekly_habits,
        "ai_explanation": rec.ai_explanation,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }


# ============================================================================
# Root
# ============================================================================


@app.get("/", tags=["Status"])
async def get_status():
    """Health-check endpoint."""
    logger.info("Health check called.")
    return {
        "status": "ok",
        "environment": ENVIRONMENT,
        "message": "FoodAI Server is running.",
        "version": "2.0.0",
    }


# ============================================================================
# Auth endpoints
# ============================================================================


@app.post("/auth/register", response_model=AuthResponse, tags=["Auth"])
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user and return a JWT access token."""
    existing = await crud.get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    hashed = hash_password(body.password)
    user = await crud.create_user(
        db, email=body.email, hashed_password=hashed, full_name=body.full_name
    )
    token = create_access_token(subject=user.id)
    logger.info("Registered new user id=%s email=%s", user.id, user.email)
    return AuthResponse(access_token=token, user_id=user.id)


@app.post("/auth/login", response_model=AuthResponse, tags=["Auth"])
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email + password and return a JWT access token."""
    user = await crud.get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=user.id)
    logger.info("Login successful for user id=%s", user.id)
    return AuthResponse(access_token=token, user_id=user.id)


# ============================================================================
# Profile endpoints
# ============================================================================


@app.get("/profile", tags=["Profile"])
async def get_profile(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's health profile."""
    profile = await crud.get_user_profile(db, user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Use PUT /profile to create one.",
        )
    return _profile_to_dict(profile)


@app.put("/profile", tags=["Profile"])
async def update_profile(
    body: ProfileRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update the current user's health profile."""
    # Auto-compute BMI if height and weight are provided
    bmi = body.bmi
    if bmi is None and body.height_cm and body.weight_kg and body.height_cm > 0:
        bmi = round(body.weight_kg / ((body.height_cm / 100) ** 2), 1)

    profile = await crud.upsert_user_profile(
        db,
        user_id=user_id,
        age=body.age,
        gender=body.gender,
        height_cm=body.height_cm,
        weight_kg=body.weight_kg,
        bmi=bmi,
        activity_level=body.activity_level,
        diet_preference=body.diet_preference,
        allergies=body.allergies,
        medical_conditions=body.medical_conditions,
        fitness_goal=body.fitness_goal,
        water_intake_goal_ml=body.water_intake_goal_ml,
        daily_calorie_goal=body.daily_calorie_goal,
    )
    logger.info("Profile updated for user_id=%s", user_id)
    return _profile_to_dict(profile)


# ============================================================================
# Food Analysis endpoint
# ============================================================================


@app.post("/analyze-food", tags=["Analysis"])
async def analyze_food(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyse an uploaded food image.

    Steps:
      1. Read image bytes
      2. Run Gemini Vision analysis
      3. Fetch nutrition data (OpenFoodFacts → Gemini fallback)
      4. Merge results
      5. Compute quality grade (deterministic override of AI grade)
      6. Compute health score
      7. Persist to database
      8. Return complete result
    """
    # Validate content type
    content_type: str = file.content_type or "image/jpeg"
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Uploaded file must be an image. Got: {content_type}",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    logger.info(
        "Analyzing food image for user_id=%s size=%d bytes type=%s",
        user_id,
        len(image_bytes),
        content_type,
    )

    # Step 2 — Gemini Vision
    try:
        vision_result = await analyze_food_image(image_bytes, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:
        logger.error("Vision analysis failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Vision analysis failed.")

    food_name: str = vision_result.get("food_name", "Unknown food")

    # Step 3 — Nutrition
    try:
        nutrition = await get_nutrition_data(food_name)
    except Exception as exc:
        logger.warning("Nutrition fetch failed for '%s': %s — using empty dict", food_name, exc)
        nutrition = {}

    # Step 4 — Merge
    merged = {**vision_result, "nutrition": nutrition}

    # Step 5 — Quality grade (deterministic)
    freshness: float = float(vision_result.get("freshness_score") or 0)
    defects: list = vision_result.get("detected_defects") or []
    grade: str = compute_quality_grade(freshness, defects)
    merged["quality_grade"] = grade  # override Gemini's grade with deterministic one

    # Step 6 — Health score
    health_score: int = compute_health_score(nutrition, freshness)
    merged["health_score"] = health_score

    # Step 7 — Persist
    try:
        analysis = await crud.create_food_analysis(
            db,
            user_id=user_id,
            food_name=food_name,
            food_category=vision_result.get("food_category"),
            confidence=vision_result.get("confidence"),
            freshness_score=freshness,
            quality_grade=grade,
            detected_defects=defects,
            nutrition=nutrition,
            health_score=float(health_score),
            ai_summary=vision_result.get("ai_summary"),
            image_url=None,  # future: upload to GCS and store URL
        )
        merged["id"] = analysis.id
        merged["created_at"] = analysis.created_at.isoformat()
    except Exception as exc:
        logger.error("Failed to persist food analysis: %s", exc, exc_info=True)
        # Non-fatal — still return the result

    logger.info(
        "Food analysis complete: food='%s' grade=%s health_score=%d user_id=%s",
        food_name,
        grade,
        health_score,
        user_id,
    )
    return {"analysis": merged}


# ============================================================================
# Recipe endpoint
# ============================================================================


@app.post("/generate-recipe", tags=["Recipe"])
async def generate_recipe_endpoint(
    body: RecipeRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a recipe for a food item.

    Steps:
      1. Optionally load user profile from DB
      2. Call Gemini recipe skill
      3. Fetch YouTube videos
      4. Persist recipe to DB
      5. Return recipe + videos
    """
    profile_dict: Optional[dict] = None
    if body.use_profile:
        profile = await crud.get_user_profile(db, user_id)
        profile_dict = _profile_to_dict(profile) if profile else None

    # Step 2 — Generate recipe
    try:
        recipe_data = await generate_recipe(
            body.food_name,
            body.preferences or "Healthy",
            profile_dict,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:
        logger.error("Recipe generation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Recipe generation failed.")

    # Step 3 — YouTube videos
    yt_query = f"{body.food_name} {body.preferences or ''} recipe".strip()
    youtube_videos = await get_youtube_videos(yt_query)

    # Step 4 — Persist
    try:
        saved = await crud.create_recipe(
            db,
            user_id=user_id,
            title=recipe_data.get("title", body.food_name),
            description=recipe_data.get("description"),
            ingredients=recipe_data.get("ingredients", []),
            steps=recipe_data.get("steps", []),
            prep_time_min=recipe_data.get("prep_time_min"),
            cook_time_min=recipe_data.get("cook_time_min"),
            difficulty=recipe_data.get("difficulty"),
            nutrition=recipe_data.get("nutrition", {}),
            storage_tips=recipe_data.get("storage_instructions"),
            healthy_alternatives=recipe_data.get("healthy_alternatives", []),
            is_vegetarian=bool(recipe_data.get("is_vegetarian", False)),
            is_vegan=bool(recipe_data.get("is_vegan", False)),
        )
        recipe_data["id"] = saved.id
        recipe_data["created_at"] = saved.created_at.isoformat()
    except Exception as exc:
        logger.error("Failed to persist recipe: %s", exc, exc_info=True)

    logger.info(
        "Recipe generated: title='%s' user_id=%s",
        recipe_data.get("title"),
        user_id,
    )
    return {"recipe": recipe_data, "youtube_videos": youtube_videos}


# ============================================================================
# Health Recommendation endpoint
# ============================================================================


@app.post("/health-recommendation", tags=["Health"])
async def health_recommendation_endpoint(
    body: HealthRecommendationRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a personalised health recommendation.

    If any field in the request body is provided it overrides the saved
    profile value; otherwise the saved profile is used as-is.
    """
    # Load saved profile
    saved_profile = await crud.get_user_profile(db, user_id)
    base: dict = _profile_to_dict(saved_profile)

    # Apply any overrides from request body
    override = body.model_dump(exclude_none=True)
    base.update(override)

    if not any(base.values()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile data found. Use PUT /profile to create a profile first.",
        )

    try:
        rec_data = await generate_health_recommendation(base)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:
        logger.error("Health recommendation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Health recommendation failed.")

    # Persist
    try:
        saved_rec = await crud.save_health_recommendation(
            db,
            user_id=user_id,
            daily_calorie_target=rec_data.get("daily_calorie_target"),
            foods_to_eat=rec_data.get("foods_to_eat", []),
            foods_to_avoid=rec_data.get("foods_to_avoid", []),
            meal_plan=rec_data.get("meal_plan", {}),
            water_recommendation=rec_data.get("water_recommendation"),
            exercise_suggestion=rec_data.get("exercise_suggestion"),
            weekly_habits=rec_data.get("weekly_habits", []),
            ai_explanation=rec_data.get("ai_explanation"),
        )
        rec_data["id"] = saved_rec.id
        rec_data["created_at"] = saved_rec.created_at.isoformat()
    except Exception as exc:
        logger.error("Failed to persist health recommendation: %s", exc, exc_info=True)

    logger.info(
        "Health recommendation generated for user_id=%s calorie_target=%s",
        user_id,
        rec_data.get("daily_calorie_target"),
    )
    return {"recommendation": rec_data}


# ============================================================================
# History endpoints
# ============================================================================


@app.get("/history", tags=["History"])
async def get_history(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated food analysis history for the current user."""
    analyses = await crud.get_food_analyses_for_user(db, user_id, page=page, limit=limit)
    return {
        "page": page,
        "limit": limit,
        "count": len(analyses),
        "results": [_analysis_to_dict(a) for a in analyses],
    }


@app.get("/history/{analysis_id}", tags=["History"])
async def get_history_item(
    analysis_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a single food analysis by ID."""
    analysis = await crud.get_food_analysis_by_id(db, analysis_id, user_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found.",
        )
    return _analysis_to_dict(analysis)


# ============================================================================
# Legacy endpoints (X-API-Key, backward compatible)
# ============================================================================


@app.post("/recommend", tags=["Legacy"])
async def legacy_recommend(
    profile: LegacyUserProfile,
    api_key: str = Security(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Legacy health recommendation endpoint.

    Accepts the old UserProfile schema authenticated with X-API-Key.
    Maps the old fields to the new skill interface.
    """
    logger.info("Legacy /recommend called for user_id=%s", profile.user_id)

    profile_dict = {
        "age": profile.age,
        "gender": None,
        "height_cm": None,
        "weight_kg": None,
        "bmi": None,
        "activity_level": None,
        "diet_preference": profile.diet,
        "allergies": profile.allergies,
        "medical_conditions": [],
        "fitness_goal": profile.goal,
    }

    try:
        rec_data = await generate_health_recommendation(profile_dict)
    except Exception as exc:
        logger.error("Legacy /recommend failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health recommendation generation failed.",
        )

    return {"recommendation": rec_data}


@app.post("/recipe", tags=["Legacy"])
async def legacy_recipe(
    request: LegacyRecipeRequest,
    api_key: str = Security(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Legacy recipe endpoint.

    Accepts the old RecipeRequest schema authenticated with X-API-Key.
    """
    logger.info(
        "Legacy /recipe called for user_id=%s food=%s",
        request.user_id,
        request.food_name,
    )

    try:
        recipe_data = await generate_recipe(
            request.food_name,
            request.preferences or "Healthy",
            None,
        )
    except Exception as exc:
        logger.error("Legacy /recipe failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recipe generation failed.",
        )

    return {"recipe": recipe_data}


# ============================================================================
# Entrypoint (local dev)
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )

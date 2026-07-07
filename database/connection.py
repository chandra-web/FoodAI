"""
Async SQLAlchemy database connection module.

Supports:
  - PostgreSQL via asyncpg  (DATABASE_URL=postgresql+asyncpg://...)
  - SQLite via aiosqlite    (DATABASE_URL=sqlite+aiosqlite:///./foodai.db)

The raw DATABASE_URL value is automatically rewritten when a plain
`sqlite:///` or `postgresql://` prefix is detected so that callers do not
need to specify the async driver explicitly.
"""
import logging
import os
import re

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# URL normalisation
# ---------------------------------------------------------------------------

_RAW_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./foodai.db")

def _normalise_url(url: str) -> str:
    """Ensure the URL uses an async-capable driver."""
    # sqlite:/// → sqlite+aiosqlite:///
    if url.startswith("sqlite:///") and "aiosqlite" not in url:
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    # postgresql:// or postgres:// → postgresql+asyncpg://
    url = re.sub(r"^postgres(?:ql)?://", "postgresql+asyncpg://", url)
    return url


DATABASE_URL: str = _normalise_url(_RAW_URL)
logger.info("Database URL driver: %s", DATABASE_URL.split("://")[0])

# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

_connect_args: dict = {}
if "sqlite" in DATABASE_URL:
    _connect_args["check_same_thread"] = False

engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    connect_args=_connect_args,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------------
# Declarative base (shared by all models)
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Common declarative base for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncSession:  # type: ignore[override]
    """
    Yield an async database session.

    Usage::

        @app.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Table creation helper
# ---------------------------------------------------------------------------


async def create_all_tables() -> None:
    """
    Create all tables defined in the ORM models.

    Should be called once at application startup.  For production use Alembic
    migrations instead of this convenience helper.
    """
    # Import models so that their metadata is registered on Base before we
    # call create_all.  The import is intentionally deferred to avoid circular
    # import issues at module load time.
    import models.schema  # noqa: F401  – registers all tables on Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("All database tables created (or already exist).")

from typing import Annotated

from fastapi import Depends, FastAPI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.api.v1.orchestration import router as orchestration_router
from apps.api.app.api.v1.repositories import router as repositories_router
from apps.api.app.api.v1.tasks import router as tasks_router
from apps.api.app.core.database import get_db
from apps.api.app.core.health import check_database, check_redis
from apps.api.app.core.redis import get_redis

app = FastAPI(
    title="RepoPilot API",
    version="0.1.0",
    description="Backend API for RepoPilot.",
)

app.include_router(
    repositories_router,
    prefix="/api/v1",
)

app.include_router(
    tasks_router,
    prefix="/api/v1",
)

app.include_router(
    orchestration_router,
    prefix="/api/v1",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "repopilot-api",
    }


@app.get("/health/database")
async def database_health(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    healthy = await check_database(session)

    return {
        "status": "healthy" if healthy else "unhealthy",
        "service": "postgresql",
    }


@app.get("/health/redis")
async def redis_health(
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    healthy = await check_redis(redis)

    return {
        "status": "healthy" if healthy else "unhealthy",
        "service": "redis",
    }

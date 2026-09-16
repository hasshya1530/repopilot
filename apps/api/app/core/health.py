from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def check_database(session: AsyncSession) -> bool:
    result = await session.execute(text("SELECT 1"))
    value = result.scalar_one()

    return bool(value == 1)


async def check_redis(redis: Redis) -> bool:
    response = await redis.ping()

    return bool(response)

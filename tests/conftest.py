from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from apps.api.app.core.config import get_settings
from apps.api.app.core.database import get_db
from apps.api.app.main import app

settings = get_settings()

test_engine = create_async_engine(
    settings.test_database_url,
    poolclass=NullPool,
)

test_session_factory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


async def reset_test_database(session: AsyncSession) -> None:
    await session.execute(
        text(
            """
            DO $$
            DECLARE
                table_record RECORD;
            BEGIN
                FOR table_record IN
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                      AND tablename <> 'alembic_version'
                LOOP
                    EXECUTE format(
                        'TRUNCATE TABLE %I RESTART IDENTITY CASCADE',
                        table_record.tablename
                    );
                END LOOP;
            END
            $$;
            """
        )
    )

    await session.commit()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        await reset_test_database(session)

        yield session

        await session.rollback()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def dispose_test_engine() -> AsyncGenerator[None, None]:
    yield

    await test_engine.dispose()

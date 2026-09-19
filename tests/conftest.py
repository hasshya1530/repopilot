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

settings = get_settings()


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
    engine = create_async_engine(
        settings.test_database_url,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        await reset_test_database(session)
        yield session

    await engine.dispose()

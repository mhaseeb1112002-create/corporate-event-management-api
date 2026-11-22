"""Async database engine and session lifecycle."""
import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://event_user:event_password@localhost:5432/event_db")
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base for all database models."""


async def get_session() -> AsyncIterator[AsyncSession]:
    """Provide one session per request and close it afterwards."""
    async with SessionLocal() as session:
        yield session

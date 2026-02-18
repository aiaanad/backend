from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from .config import settings

Base = declarative_base()

# Импортируем модели после создания Base, чтобы метаданные подхватили все ORM сущности.
# (Без этого SQLAlchemy будет грустить и таблицы не создадутся 😢)
from src.model import models  # noqa: E402,F401

# Асинхронный движок БД
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG.lower() == "true",
    future=True,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30,
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)

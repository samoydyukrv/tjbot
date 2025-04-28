from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("postgresql://postgres:hnyQbQRvVyWqaVvQGczHdoUgUFZSwhgK@postgres.railway.internal:5432/railway")

# Создаём асинхронный движок подключения к БД
engine = create_async_engine(DATABASE_URL, echo=True)

# Создаём сессии для работы с БД
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Функция для получения сессии
async def get_session():
    async with async_session() as session:
        yield session

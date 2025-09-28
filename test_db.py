import asyncio
from sqlalchemy import text
from database import engine

async def test_connection():
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(" Подключение успешно:", result.scalar())
    except Exception as e:
        print(" Ошибка подключения:", e)

if __name__ == "__main__":
    asyncio.run(test_connection())

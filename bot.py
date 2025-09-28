import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import engine, Base
from handlers import router

async def main():
    # создаем таблицы (если их нет)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import random
import datetime
from aiogram import Router, types, F
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from sqlalchemy import select
from database import SessionLocal
from models import User
from config import ADMIN_ID

router = Router()

# --- Кнопки ---
btn_profile = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="ПРОФИЛЬ")]],
    resize_keyboard=True
)

btn_request_code = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="ЗАПРОСИТЬ КОД")]],
    resize_keyboard=True
)

# --- /start ---
@router.message(F.text == "/start")
async def cmd_start(message: types.Message):
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = result.scalars().first()

        if user and user.is_verified:
            await message.answer("Привет! Жми ПРОФИЛЬ для запуска мини-приложения.", reply_markup=btn_profile)
        else:
            await message.answer(
                "⚠️ Не знаю тебя!\n\nВарианты активации:\n"
                "1️⃣ Получи 4-значный код у бота.\n"
                "2️⃣ Скажи этот код администратору для подтверждения.",
                reply_markup=btn_request_code
            )

# --- Сгенерировать код ---
@router.message(F.text == "ЗАПРОСИТЬ КОД")
async def generate_code(message: types.Message):
    code = str(random.randint(1000, 9999))
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=2)

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = result.scalars().first()

        if not user:
            user = User(tg_id=message.from_user.id, code=code, is_verified=False)
            session.add(user)
        else:
            user.code = code
            user.is_verified = False
        await session.commit()

    await message.answer(
        f"Ваш код для активации: <b>{code}</b>\n"
        f"⏳ Действует 2 минуты.\n\n"
        f"Передайте этот код администратору.",
        parse_mode="HTML"
    )

# --- Админ: подтвердить код вручную ---
@router.message(F.text.regexp(r"^/approve \d{4}$"))
async def approve_user(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ У тебя нет прав на выполнение этой команды.")

    code = message.text.split()[1]

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.code == code))
        user = result.scalars().first()

        if not user:
            return await message.answer("❌ Пользователь с таким кодом не найден.")

        user.is_verified = True
        user.code = None  # очищаем код после активации
        await session.commit()

        await message.answer(f"✅ Доступ пользователю {user.tg_id} подтверждён.")
        await message.bot.send_message(user.tg_id, "🎉 Успех! Код принят.\nЖми кнопку ПРОФИЛЬ для запуска мини-приложения!", reply_markup=btn_profile)

# --- Админ: отобрать доступ по id ---
@router.message(F.text.regexp(r"^/revoke \d+$"))
async def revoke_user(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ У тебя нет прав на выполнение этой команды.")

    user_id = int(message.text.split()[1])

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == user_id))
        user = result.scalars().first()

        if not user or not user.is_verified:
            return await message.answer("ℹ️ У этого пользователя уже нет доступа.")

        user.is_verified = False
        await session.commit()

        await message.answer(f"🚫 Доступ пользователя {user_id} отозван.")
        await message.bot.send_message(user_id, "🚫 Ваш доступ к боту был отозван администратором.")

# --- Админ: список пользователей ---
@router.message(F.text == "/users")
async def list_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ У тебя нет прав на выполнение этой команды.")

    async with SessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        if not users:
            return await message.answer("👥 Пользователей пока нет.")

        for u in users:
            status = "✅ Верифицирован" if u.is_verified else "❌ Нет доступа"

            # inline-кнопки
            if u.is_verified:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🚫 Отозвать", callback_data=f"revoke_user:{u.tg_id}")]
                ])
            else:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Выдать", callback_data=f"approve_user:{u.tg_id}")]
                ])

            await message.answer(
                f"👤 Пользователь: {u.tg_id}\nСтатус: {status}",
                reply_markup=kb
            )

# --- Кнопка: выдать доступ ---
@router.callback_query(F.data.startswith("approve_user"))
async def approve_user_cb(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("Нет прав", show_alert=True)

    user_id = int(callback.data.split(":")[1])

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == user_id))
        user = result.scalars().first()

        if not user:
            return await callback.answer("Пользователь не найден", show_alert=True)

        user.is_verified = True
        await session.commit()

    await callback.bot.send_message(user_id, "✅ Администратор выдал вам доступ.")
    await callback.answer("Доступ выдан")

# --- Кнопка: отозвать доступ ---
@router.callback_query(F.data.startswith("revoke_user"))
async def revoke_user_cb(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("Нет прав", show_alert=True)

    user_id = int(callback.data.split(":")[1])

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == user_id))
        user = result.scalars().first()

        if not user:
            return await callback.answer("Пользователь не найден", show_alert=True)

        user.is_verified = False
        await session.commit()

    await callback.bot.send_message(user_id, "🚫 Ваш доступ был отозван администратором.")
    await callback.answer("Доступ отозван")

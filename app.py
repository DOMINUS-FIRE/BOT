import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

TOKEN = os.getenv("BOT_TOKEN")  # токен бота из BotFather
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "super_secret")  # можешь оставить дефолт

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI()


# --- Команда /start ---
@dp.message(CommandStart())
async def start_cmd(m: types.Message):
    await m.answer("👋 Привет! Бот работает через Render.\nОтправь сообщение — я повторю его.")


# --- Просто эхо, пока не подключим анкету ---
@dp.message()
async def echo(m: types.Message):
    await m.answer(f"Ты написал: {m.text}")


# --- Вебхук ---
@app.post(f"/webhook/{WEBHOOK_SECRET}")
async def telegram_webhook(request: Request):
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}


# --- Пример отправки анкеты в канал ---
async def send_form_to_channel(form_data: dict):
    """
    form_data = {
        "fio": "Иванов Иван",
        "birthdate": "01.01.1990",
        "age": "34",
        "phone": "+79991234567",
        "telegram": "@example",
        "address": "г. Москва, ул. Ленина 1",
        "skills": "Касса, работа с клиентами",
        "motivation": "Хочу работать у вас"
    }
    """
    text = (
        f"📋 Новая анкета кандидата\n\n"
        f"👤 ФИО: {form_data.get('fio')}\n"
        f"🎂 Дата рождения: {form_data.get('birthdate')} (возраст: {form_data.get('age')})\n"
        f"📞 Телефон: {form_data.get('phone')}\n"
        f"💬 Telegram: {form_data.get('telegram')}\n"
        f"🏠 Адрес: {form_data.get('address')}\n"
        f"🛠 Навыки: {form_data.get('skills')}\n"
        f"✨ Мотивация: {form_data.get('motivation')}\n"
    )

    # ⚠️ Вот здесь указываем твой id или канал:
    await bot.send_message("@dominusfire", text)


# --- Тестовый пинг ---
@app.get("/")
async def ping():
    return {"ok": True}

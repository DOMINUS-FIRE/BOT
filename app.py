import os
import asyncio
import logging
from contextlib import suppress

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import Update, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError

# ─────────────────────────────────────────────────────────────
# Конфиг из переменных окружения Render
# ─────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
BASE_URL  = os.environ.get("BASE_URL", "").rstrip("/")      # напр. https://ваш-сервис.onrender.com
SECRET    = os.environ.get("WEBHOOK_SECRET", "super_secret_dominus")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

WEBHOOK_PATH = f"/webhook/{SECRET}"
WEBHOOK_URL  = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None

# ─────────────────────────────────────────────────────────────
# Инициализация
# ─────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp  = Dispatcher()

app = FastAPI()


# ─────────────────────────────────────────────────────────────
# Хэндлеры
# ─────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def start_cmd(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Открыть меню", callback_data="menu")
    ]])
    text = (
        "👋 Привет! Бот подключён через webhook.\n"
        "Используй /menu, чтобы открыть меню."

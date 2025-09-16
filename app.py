import os
import logging
from contextlib import suppress

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import Update, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "super_secret_dominus")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
app = FastAPI()

@dp.message(CommandStart())
async def start_cmd(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть меню", callback_data="menu")]
    ])
    text = "👋 Привет! Бот подключён через webhook.\nИспользуй /menu, чтобы открыть меню."
    with suppress(TelegramForbiddenError):
        await m.answer(text, reply_markup=kb)

@dp.message(Command("menu"))
async def menu_cmd(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Анкеты: принятые (0)", callback_data="accepted")],
        [InlineKeyboardButton(text="Анкеты: новые (0)", callback_data="new")],
    ])
    with suppress(TelegramForbiddenError):
        await m.answer("Главное меню:", reply_markup=kb)

@dp.callback_query(F.data == "menu")
async def cb_menu(call):
    await menu_cmd(call.message)
    with suppress(TelegramForbiddenError):
        await call.answer()

@dp.message()
async def fallback(m: Message):
    with suppress(TelegramForbiddenError):
        await m.answer("Не понял команду. Попробуй /menu.")

@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    update = Update.model_validate(data, strict=False)
    await dp.feed_update(bot, update)
    return JSONResponse({"ok": True})

@app.on_event("startup")
async def on_startup():
    if WEBHOOK_URL:
        log.info("Setting webhook to %s", WEBHOOK_URL)
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    else:
        log.warning("BASE_URL is empty, webhook will not be set.")

@app.on_event("shutdown")
async def on_shutdown():
    with suppress(Exception):
        await bot.delete_webhook(drop_pending_updates=False)
    with suppress(Exception):
        await bot.session.close()

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

# ── конфиг ─────────────────────────────────────────────────────
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


# ── handlers ───────────────────────────────────────────────────
@dp.message(CommandStart())
async def start_cmd(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть меню", callback_data="menu")]
    ])
    text = "👋 Привет! Бот подключён через webhook.\nНажми кнопку ниже или введи /menu."
    with suppress(TelegramForbiddenError):
        await m.answer(text, reply_markup=kb)

@dp.message(Command("menu"))
async def menu_cmd(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Анкеты: новые (0)", callback_data="new")],
        [InlineKeyboardButton(text="Анкеты: принятые (0)", callback_data="accepted")],
    ])
    with suppress(TelegramForbiddenError):
        await m.answer("Главное меню:", reply_markup=kb)

@dp.callback_query(F.data == "menu")
async def cb_menu(c):
    await menu_cmd(c.message)
    with suppress(TelegramForbiddenError):
        await c.answer()

# Заглушка (НЕ эхо)
@dp.message()
async def fallback(m: Message):
    with suppress(TelegramForbiddenError):
        await m.answer("Не понял команду. Попробуй /menu.")

# ── FastAPI endpoints ──────────────────────────────────────────
@app.get("/healthz")
async def healthz():
    return {"ok": True, "webhook": WEBHOOK_URL or "not-set"}

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    update = Update.model_validate(payload, strict=False)
    await dp.feed_update(bot, update)
    return JSONResponse({"ok": True})

# Удобная ручка для ручной установки вебхука (без токена):
# GET /set-webhook  — если BASE_URL задан, выставит вебхук.
@app.get("/set-webhook")
async def set_webhook_manual():
    if not WEBHOOK_URL:
        raise HTTPException(400, "BASE_URL is empty; set it in environment")
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True, allowed_updates=dp.resolve_used_update_types())
    return {"ok": True, "url": WEBHOOK_URL}

# ── lifecycle ──────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    if WEBHOOK_URL:
        log.info("Setting webhook to %s", WEBHOOK_URL)
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True, allowed_updates=dp.resolve_used_update_types())
    else:
        log.warning("BASE_URL is empty — webhook will not be set.")

@app.on_event("shutdown")
async def on_shutdown():
    with suppress(Exception):
        await bot.delete_webhook(drop_pending_updates=False)
    with suppress(Exception):
        await bot.session.close()

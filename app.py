# app.py — aiogram 3.7 + FastAPI webhook для Render

import os
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Update, Message
import httpx

# ── настройки из окружения ───────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# Секрет для вебхука (чтобы апдейты принимались только по «секретному» URL)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "super-secret-path")

# Render сам кладёт публичный адрес сюда. На локали можно задать вручную.
PUBLIC_BASE_URL = os.getenv("RENDER_EXTERNAL_URL", os.getenv("PUBLIC_BASE_URL", "")).rstrip("/")

# ── aiogram ──────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ── хендлеры ─────────────────────────────────────────────────────────
@router.message(CommandStart())
async def start_cmd(m: Message):
    await m.answer(
        "👋 Привет! Бот на Render работает через webhook.\n"
        "Отправь мне сообщение — я повторю его."
    )

@router.message()
async def echo(m: Message):
    # простое эхо, чтобы видеть, что бот жив
    await m.answer(f"Ты написал: <code>{m.text}</code>")

# ── FastAPI ──────────────────────────────────────────────────────────
app = FastAPI()

@app.get("/health")
async def health():
    return PlainTextResponse("ok")

@app.post(f"/webhook/{{secret}}")
async def telegram_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        # чужие запросы отбрасываем
        raise HTTPException(status_code=403, detail="forbidden")

    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return JSONResponse({"ok": True})

# ── управление вебхуком при старте/остановке ────────────────────────
async def set_webhook():
    if not PUBLIC_BASE_URL:
        print("WARNING: PUBLIC_BASE_URL/RENDER_EXTERNAL_URL не задан — вебхук не ставим.")
        return
    url = f"{PUBLIC_BASE_URL}/webhook/{WEBHOOK_SECRET}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            json={"url": url, "allowed_updates": ["message"], "drop_pending_updates": False},
        )
        print("setWebhook:", r.text)

async def delete_webhook():
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
        print("deleteWebhook:", r.text)

@app.on_event("startup")
async def on_startup():
    await set_webhook()

@app.on_event("shutdown")
async def on_shutdown():
    await delete_webhook()
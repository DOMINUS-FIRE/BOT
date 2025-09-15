# bot.py — админ-бот ЛЕГО СИТИ
# Требует: aiogram>=3.7, python-dotenv
# Запуск: python bot.py

import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from db import init_db, get_applications_by_status, count_by_status, set_status

# ── инициализация ───────────────────────────────────────────────
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing in .env")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
init_db()

# offsets для листания
OFFSETS = {}  # ключ: (user_id, status) -> offset

# ── клавиатуры ──────────────────────────────────────────────────
def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📥 В ожидании", callback_data="view:pending:0")
    kb.button(text="✅ Принятые", callback_data="view:accepted:0")
    kb.adjust(1)
    return kb.as_markup()

def review_kb(app_id: int, status: str, offset: int, total: int):
    kb = InlineKeyboardBuilder()
    if status == "pending":
        kb.button(text="✅ Принять", callback_data=f"do:approve:{app_id}:{offset}")
        kb.button(text="❌ Отклонить", callback_data=f"do:reject:{app_id}:{offset}")
        kb.adjust(2)
    # листание
    prev_off = max(offset - 1, 0)
    next_off = min(offset + 1, max(total - 1, 0))
    kb.button(text="◀️", callback_data=f"nav:{status}:{prev_off}")
    kb.button(text="▶️", callback_data=f"nav:{status}:{next_off}")
    kb.adjust(2)
    # меню
    kb.button(text="🏠 Меню", callback_data="menu")
    return kb.as_markup()

# ── формат карточки ─────────────────────────────────────────────
def pretty_caption(row, status: str, offset: int, total: int) -> str:
    (
        id_, created_at, st, full_name, dob_age, _dob_date, _age_years,
        phone, tg, address, reg_addr, pass_num, pass_issuer,
        edu, exp, skills, why, sched, photo_path
    ) = row
    return (
        f"🧩 <b>Анкета №{id_}</b> ({offset+1}/{total})\n"
        f"🕒 <i>Создано:</i> {created_at}\n"
        f"{'⏳ В ожидании' if status=='pending' else '✅ Принято'}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 ФИО: {full_name}\n"
        f"🎂 Дата рождения: {dob_age}\n"
        f"☎️ Телефон: {phone}\n"
        f"✈️ Telegram: @{tg}\n"
        f"🏠 Адрес (факт): {address}\n"
        f"🪪 Прописка: {reg_addr}\n"
        f"📘 Паспорт: {pass_num}\n"
        f"🏢 Кем выдан: {pass_issuer}\n"
        f"🎓 Образование: {edu or '—'}\n"
        f"💼 Опыт: {exp or '—'}\n"
        f"🧰 Навыки: {skills or '—'}\n"
        f"💬 Почему к нам: {why or '—'}\n"
        f"📅 График:\n{sched}"
    )

# ── утилиты ────────────────────────────────────────────────────
async def show_main_menu(target):
    p = count_by_status("pending")
    a = count_by_status("accepted")
    txt = (
        "👋 <b>Админ-бот ЛЕГО СИТИ</b>\n"
        f"📥 В ожидании: <b>{p}</b>\n"
        f"✅ Принятые: <b>{a}</b>\n\n"
        "Выберите раздел:"
    )
    # всегда удаляем старое сообщение и отправляем новое
    try:
        await target.message.delete()
    except Exception:
        pass
    if isinstance(target, Message):
        await target.answer(txt, reply_markup=main_menu_kb())
    else:
        await target.message.answer(txt, reply_markup=main_menu_kb())

async def send_card(cb: CallbackQuery, status: str, offset: int):
    user_id = cb.from_user.id
    OFFSETS[(user_id, status)] = offset
    total = count_by_status(status)
    if total == 0:
        try: await cb.message.delete()
        except Exception: pass
        await cb.message.answer(f"📭 {status.title()} пусто.", reply_markup=main_menu_kb())
        return
    rows = get_applications_by_status(status=status, offset=offset, limit=1)
    if not rows:
        offset = 0
        rows = get_applications_by_status(status=status, offset=0, limit=1)
        if not rows:
            try: await cb.message.delete()
            except Exception: pass
            await cb.message.answer(f"📭 {status.title()} пусто.", reply_markup=main_menu_kb())
            return
    row = rows[0]
    caption = pretty_caption(row, status, offset, total)
    photo_path = row[-1]
    has_photo = photo_path and Path(photo_path).exists()
    try: await cb.message.delete()
    except Exception: pass
    if has_photo:
        await cb.message.answer_photo(
            FSInputFile(photo_path), caption=caption,
            reply_markup=review_kb(row[0], status, offset, total)
        )
    else:
        await cb.message.answer(
            caption, reply_markup=review_kb(row[0], status, offset, total)
        )

# ── обработчики ────────────────────────────────────────────────
@dp.message(CommandStart())
async def start(message: Message):
    await show_main_menu(message)

@dp.message(Command("menu"))
async def menu_cmd(message: Message):
    await show_main_menu(message)

@dp.callback_query(F.data == "menu")
async def menu_cb(cb: CallbackQuery):
    await show_main_menu(cb)
    await cb.answer()

@dp.callback_query(F.data.startswith("view:"))
async def on_view(cb: CallbackQuery):
    _, status, off_str = cb.data.split(":")
    offset = int(off_str)
    await send_card(cb, status, offset)
    await cb.answer()

@dp.callback_query(F.data.startswith("nav:"))
async def on_nav(cb: CallbackQuery):
    _, status, off_str = cb.data.split(":")
    offset = int(off_str)
    await send_card(cb, status, offset)
    await cb.answer()

@dp.callback_query(F.data.startswith("do:"))
async def on_do(cb: CallbackQuery):
    _, action, app_id_str, off_str = cb.data.split(":")
    app_id, offset = int(app_id_str), int(off_str)
    if action == "approve":
        set_status(app_id, "accepted")
        note = "Принято ✅"
    elif action == "reject":
        set_status(app_id, "rejected")
        note = "Отклонено ❌"
    else:
        await cb.answer("Ошибка")
        return
    await cb.answer(note)
    total_left = count_by_status("pending")
    if total_left == 0:
        try: await cb.message.delete()
        except Exception: pass
        await cb.message.answer("🎉 Все анкеты обработаны.", reply_markup=main_menu_kb())
        return
    next_offset = min(offset, total_left - 1)
    await send_card(cb, "pending", next_offset)

# ── запуск ────────────────────────────────────────────────────
if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
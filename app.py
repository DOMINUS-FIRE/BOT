from fastapi import Form, UploadFile, File
from aiogram.exceptions import TelegramBadRequest

CHANNEL = "@dominusfire"  # КУДА шлём анкету

def _safe(v):  # небольшая утилита для «нет данных»
    return v if (v and str(v).strip()) else "—"

@app.post("/submit")
async def submit_form(
    full_name: str = Form(...),
    dob_date: str = Form(""),
    phone: str = Form(""),
    telegram: str = Form(""),
    address: str = Form(""),
    passport_registration: str = Form(""),
    passport_number: str = Form(""),
    passport_issuer: str = Form(""),
    education: str = Form(""),
    experience: str = Form(""),
    skills: str = Form(""),
    why_us: str = Form(""),
    mon_status: str = Form(""), mon_hours: str = Form(""), mon_reason: str = Form(""),
    tue_status: str = Form(""), tue_hours: str = Form(""), tue_reason: str = Form(""),
    wed_status: str = Form(""), wed_hours: str = Form(""), wed_reason: str = Form(""),
    thu_status: str = Form(""), thu_hours: str = Form(""), thu_reason: str = Form(""),
    fri_status: str = Form(""), fri_hours: str = Form(""), fri_reason: str = Form(""),
    sat_status: str = Form(""), sat_hours: str = Form(""), sat_reason: str = Form(""),
    sun_status: str = Form(""), sun_hours: str = Form(""), sun_reason: str = Form(""),
    photo: UploadFile = File(None),
):
    # собираем текст
    schedule = (
        f"Пн: {mon_status or '—'} {mon_hours or ''} ({mon_reason or '—'})\n"
        f"Вт: {tue_status or '—'} {tue_hours or ''} ({tue_reason or '—'})\n"
        f"Ср: {wed_status or '—'} {wed_hours or ''} ({wed_reason or '—'})\n"
        f"Чт: {thu_status or '—'} {thu_hours or ''} ({thu_reason or '—'})\n"
        f"Пт: {fri_status or '—'} {fri_hours or ''} ({fri_reason or '—'})\n"
        f"Сб: {sat_status or '—'} {sat_hours or ''} ({sat_reason or '—'})\n"
        f"Вс: {sun_status or '—'} {sun_hours or ''} ({sun_reason or '—'})"
    )

    text = (
        "📋 <b>Новая анкета кандидата</b>\n\n"
        f"👤 ФИО: {_safe(full_name)}\n"
        f"🎂 Дата рождения: {_safe(dob_date)}\n"
        f"📞 Телефон: {_safe(phone)}\n"
        f"💬 Telegram: {_safe(telegram)}\n"
        f"🏠 Адрес проживания: {_safe(address)}\n"
        f"🏷️ Прописка (из паспорта): {_safe(passport_registration)}\n"
        f"🪪 Паспорт: {_safe(passport_number)}\n"
        f"🏢 Кем выдан: {_safe(passport_issuer)}\n"
        f"🎓 Образование: {_safe(education)}\n"
        f"🛠 Навыки: {_safe(skills)}\n"
        f"💼 Опыт: {_safe(experience)}\n"
        f"✨ Почему к нам: {_safe(why_us)}\n\n"
        f"🗓 <b>График по дням</b>:\n{schedule}"
    )

    # шлём в канал; если есть фото — отправим фото + подпись, иначе текст
    try:
        if photo is not None:
            content = await photo.read()
            await bot.send_photo(
                CHANNEL,
                photo=content,
                caption=text,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(CHANNEL, text, parse_mode="HTML")
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        # чаще всего: бот не добавлен в канал или нет прав
        return {"ok": False, "error": f"telegram_error: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"server_error: {e}"}

    return {"ok": True}

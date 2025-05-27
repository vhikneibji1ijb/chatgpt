import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# --- Pentru OCR, calendar, etc, vei avea nevoie de librării suplimentare/integrare API ---

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("Nu ai setat TELEGRAM_TOKEN în .env!")

logging.basicConfig(level=logging.INFO)

# --- State și memorie simplă ---
user_settings = {}  # user_id: {nivel, stil, limba, etc.}
user_history = {}   # user_id: [istoric mesaje]
user_plans = {}     # user_id: [planuri calendar]

# --- Meniuri și butoane ---
kb_main = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Explică tema")],
        [KeyboardButton(text="✅ Verifică tema")],
        [KeyboardButton(text="🗓️ Calendar inteligent")],
        [KeyboardButton(text="⚙️ Setări")],
        [KeyboardButton(text="🖼️ OCR (text din poză)")],
        [KeyboardButton(text="🧑‍💼 Ajutor cotidian")],
        [KeyboardButton(text="💬 Istoric conversații")],
    ],
    resize_keyboard=True
)

router = Router()

@router.message(Command("start"))
async def start_command(message: types.Message):
    uid = message.from_user.id
    if uid not in user_settings:
        user_settings[uid] = {"limba": "Română", "nivel": "Mediu", "stil": "Explicativ"}
    await message.answer(
        "Bine ai venit! Ce vrei să faci azi?",
        reply_markup=kb_main
    )

@router.message(F.text == "⚙️ Setări")
async def settings_menu(message: types.Message):
    # aici poți adăuga sub-meniu pentru setare limba, stil, nivel etc.
    await message.answer("Alege ce vrei să schimbi: /limba, /nivel, /stil")

@router.message(Command("limba"))
async def set_language(message: types.Message):
    # exemplu rapid de schimbare limbă
    user_settings[message.from_user.id]["limba"] = "Română"
    await message.answer("Limba a fost setată la Română.")

@router.message(Command("nivel"))
async def set_difficulty(message: types.Message):
    user_settings[message.from_user.id]["nivel"] = "Avansat"
    await message.answer("Nivelul a fost setat la Avansat.")

@router.message(F.text == "📚 Explică tema")
async def explain_homework(message: types.Message):
    await message.answer("Trimite-mi enunțul temei. Voi explica adaptat la stilul și nivelul tău.")

@router.message(F.text == "✅ Verifică tema")
async def check_homework(message: types.Message):
    await message.answer("Trimite-mi tema ta (text sau poză). Voi încerca o verificare automată.")

@router.message(F.text == "🗓️ Calendar inteligent")
async def calendar(message: types.Message):
    await message.answer("Ce vrei să planificăm? (ex: pregătire BAC, teme, recapitulare)")

@router.message(F.text == "🖼️ OCR (text din poză)")
async def ocr_feature(message: types.Message):
    await message.answer("Trimite-mi o poză, voi extrage textul din ea (beta).")

@router.message(F.text == "🧑‍💼 Ajutor cotidian")
async def daily_help(message: types.Message):
    await message.answer("Cu ce te pot ajuta în viața cotidiană? (ex: planner, sfaturi, reparații, documente)")

@router.message(F.text == "💬 Istoric conversații")
async def show_history(message: types.Message):
    uid = message.from_user.id
    history = user_history.get(uid, [])
    if not history:
        await message.answer("Nu ai încă istoric.")
    else:
        await message.answer("\n".join(history[-10:]))

@router.message()
async def general_handler(message: types.Message):
    # Salvare istoric scurt, adaptare la modul dorit
    uid = message.from_user.id
    user_history.setdefault(uid, []).append(message.text)
    await message.answer("Am primit mesajul. Alege o funcție din meniu sau scrie /start.")

async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

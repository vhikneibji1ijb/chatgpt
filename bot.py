import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("Nu ai setat TELEGRAM_TOKEN în .env!")

logging.basicConfig(level=logging.INFO)

# Contextul funcției alese de fiecare user
user_context = {}

# Meniu principal
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
    user_context.pop(message.from_user.id, None)
    await message.answer(
        "Bine ai venit! Alege o funcție din meniu:",
        reply_markup=kb_main
    )

@router.message(F.text == "📚 Explică tema")
async def explain_homework(message: types.Message):
    user_context[message.from_user.id] = "explica"
    await message.answer("Trimite enunțul temei (text).")

@router.message(F.text == "✅ Verifică tema")
async def check_homework(message: types.Message):
    user_context[message.from_user.id] = "verifica"
    await message.answer("Trimite tema ta ca text sau poză.")

@router.message(F.text == "🖼️ OCR (text din poză)")
async def ocr_feature(message: types.Message):
    user_context[message.from_user.id] = "ocr"
    await message.answer("Trimite poza din care vrei să extragi text.")

@router.message(F.text == "🧑‍💼 Ajutor cotidian")
async def daily_help(message: types.Message):
    user_context[message.from_user.id] = "cotidian"
    await message.answer("Scrie sau trimite ce vrei să rezolvi (ex: planner, sfat, etc).")

@router.message(F.text == "🗓️ Calendar inteligent")
async def calendar(message: types.Message):
    user_context[message.from_user.id] = "calendar"
    await message.answer("Descrie ce vrei să planifici sau organizezi.")

@router.message(F.text == "💬 Istoric conversații")
async def show_history(message: types.Message):
    # aici poți adăuga logică pentru afișarea istoricului (ex: dintr-o bază de date)
    await message.answer("Funcția de istoric nu e implementată în demo. Revino cu /start sau alege altceva.")

@router.message(F.text == "⚙️ Setări")
async def settings_menu(message: types.Message):
    user_context[message.from_user.id] = "setari"
    await message.answer("Aici poți schimba limba, nivelul sau alte opțiuni. Scrie ce vrei să schimbi.")

# Handler pentru POZE
@router.message(F.photo)
async def handle_photo(message: types.Message):
    functie = user_context.get(message.from_user.id)
    if functie == "verifica":
        await message.answer("Am primit poza. Încep analiza temei (demo).")
        user_context.pop(message.from_user.id, None)
    elif functie == "ocr":
        await message.answer("Extragem textul din poza (demo OCR).")
        user_context.pop(message.from_user.id, None)
    else:
        await message.answer("Nu știu ce să fac cu poza. Alege o funcție din meniu sau scrie /start.")

# Handler pentru TEXT
@router.message()
async def handle_text(message: types.Message):
    functie = user_context.get(message.from_user.id)
    if functie == "explica":
        await message.answer(f"Explicarea temei (demo): {message.text}")
        user_context.pop(message.from_user.id, None)
    elif functie == "verifica":
        await message.answer(f"Verificarea temei (demo): {message.text}")
        user_context.pop(message.from_user.id, None)
    elif functie == "calendar":
        await message.answer(f"Planificare în calendar (demo): {message.text}")
        user_context.pop(message.from_user.id, None)
    elif functie == "setari":
        await message.answer(f"Setare modificată (demo): {message.text}")
        user_context.pop(message.from_user.id, None)
    elif functie == "cotidian":
        await message.answer(f"Ajutor cotidian (demo): {message.text}")
        user_context.pop(message.from_user.id, None)
    else:
        await message.answer("Am primit mesajul. Alege o funcție din meniu sau scrie /start.")

async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

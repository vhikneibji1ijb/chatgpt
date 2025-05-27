import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import aiohttp

from pro_users import is_pro, set_pro, set_free

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("Не найдены TELEGRAM_TOKEN или GROQ_API_KEY в .env!")

logging.basicConfig(level=logging.INFO)

LANGUAGES = {
    "🇷🇴 Română": ("ro", "Ответь только на румынском языке, игнорируй другие языки."),
    "🇷🇺 Русский": ("ru", "Отвечай только на русском языке, игнорируй другие языки."),
    "🇬🇧 English": ("en", "Reply only in English, ignore all other languages."),
}
DEFAULT_LANG = "🇷🇺 Русский"

lang_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🇷🇴 Română")],
        [KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇬🇧 English")]
    ],
    resize_keyboard=True
)

user_lang = {}
router = Router()

def get_sys_prompt(lang):
    return LANGUAGES[lang][1]

# =============== PRO management ===============

ADMIN_IDS = [123456789]  # <-- замените на свой Telegram user_id

@router.message(Command("pro"))
async def make_pro(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        parts = message.text.split()
        if len(parts) >= 2:
            uid = int(parts[1])
            set_pro(uid)
            await message.answer(f"Пользователю {uid} выдан PRO на 30 дней.")
        else:
            set_pro(message.from_user.id)
            await message.answer("Вам выдан PRO на 30 дней.")
    else:
        await message.answer("Обратитесь к администратору для получения PRO.")

@router.message(Command("free"))
async def remove_pro(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        parts = message.text.split()
        if len(parts) >= 2:
            uid = int(parts[1])
            set_free(uid)
            await message.answer(f"У пользователя {uid} снят PRO.")
        else:
            set_free(message.from_user.id)
            await message.answer("Ваш PRO снят.")
    else:
        await message.answer("Обратитесь к администратору.")

@router.message(Command("status"))
async def status(message: types.Message):
    if is_pro(message.from_user.id):
        await message.answer("У вас PRO-доступ 🟢")
    else:
        await message.answer("У вас обычный доступ 🔘. Для расширенных возможностей напишите /pro")

# =============== Языки ================

@router.message(Command("start"))
@router.message(Command("language"))
async def choose_language(message: types.Message):
    await message.answer(
        "Выберите язык / Alege limba / Choose language:",
        reply_markup=lang_kb
    )

@router.message(lambda m: m.text in LANGUAGES)
async def set_language(message: types.Message):
    user_lang[message.from_user.id] = message.text
    greetings = {
        "🇷🇴 Română": "Salut! Trimite-mi întrebarea ta.",
        "🇷🇺 Русский": "Привет! Задай свой вопрос.",
        "🇬🇧 English": "Hi! Please ask your question."
    }
    await message.answer(greetings[message.text], reply_markup=types.ReplyKeyboardRemove())

# =============== Основная логика ================

@router.message()
async def ask_groq(message: types.Message):
    user_id = message.from_user.id

    # Пример ограничения: обычным нельзя отправлять больше 250 символов за раз
    if not is_pro(user_id):
        if len(message.text) > 250:
            await message.answer("❗ Это доступно только для PRO пользователей. Для расширения возможностей напишите /pro")
            return

    lang = user_lang.get(user_id, DEFAULT_LANG)
    sys_prompt = get_sys_prompt(lang)
    prompt = message.text.strip()

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    answer = result["choices"][0]["message"]["content"]
                    await message.answer(answer.strip())
                else:
                    err_text = await resp.text()
                    logging.error(f"Groq API error: {resp.status}, {err_text}")
                    await message.answer("⚠️ Ошибка API. Попробуйте позже.")
        except Exception as e:
            logging.exception("Error contacting Groq API")
            await message.answer("⚠️ Ошибка при обращении к API. Попробуйте позже.")

async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import aiohttp

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("Не найдены TELEGRAM_TOKEN или GROQ_API_KEY в .env!")

logging.basicConfig(level=logging.INFO)

# Сохраняем язык для каждого пользователя
user_lang = {}

# Клавиатура для выбора языка
lang_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🇷🇴 Română")],
        [KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇬🇧 English")]
    ],
    resize_keyboard=True
)

SYSTEM_PROMPTS = {
    "🇷🇴 Română": "Ești un profesor din Moldova care explică materia elevilor din clasele 5–12, inclusiv pentru examenele EN și BAC.",
    "🇷🇺 Русский": "Ты учитель из Молдовы, объясняющий школьные темы ученикам 5–12 классов, готовишь к EN и BAC.",
    "🇬🇧 English": "You are a Moldovan teacher explaining school material to students (grades 5–12) and preparing for national exams."
}
WELCOME_MESSAGES = {
    "🇷🇴 Română": "Salut! Trimite-mi o întrebare legată de temă sau BAC.",
    "🇷🇺 Русский": "Привет! Отправь мне вопрос по домашке или экзамену.",
    "🇬🇧 English": "Hi! Ask me anything related to school or exams."
}
DEFAULT_LANG = "🇷🇺 Русский"

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Alege limba / Выбери язык / Choose language:", reply_markup=lang_kb)

@router.message(lambda m: m.text in SYSTEM_PROMPTS)
async def set_language(message: types.Message):
    user_lang[message.from_user.id] = message.text
    await message.answer(WELCOME_MESSAGES[message.text])

@router.message()
async def ask_groq(message: types.Message):
    lang = user_lang.get(message.from_user.id, DEFAULT_LANG)
    prompt = message.text.strip()
    sys_prompt = SYSTEM_PROMPTS[lang]

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-8b-8192",  # актуальная модель Groq
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

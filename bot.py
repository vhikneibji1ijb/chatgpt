import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram import Router
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv
import aiohttp
import asyncio

# Загружаем .env переменные
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("❌ Не найдены токены в переменных окружения. Проверь TELEGRAM_TOKEN и GROQ_API_KEY!")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Клавиатура выбора языка
lang_kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text="🇷🇴 Română")],
    [KeyboardButton(text="🇷🇺 Русский")],
    [KeyboardButton(text="🇬🇧 English")]
])

system_prompts = {
    "🇷🇴 Română": "Ești un profesor din Moldova care explică materia elevilor din clasele 5–12, inclusiv pentru examenele EN și BAC.",
    "🇷🇺 Русский": "Ты учитель из Молдовы, объясняющий школьные темы ученикам 5–12 классов, готовишь к EN и BAC.",
    "🇬🇧 English": "You are a Moldovan teacher explaining school material to students (grades 5–12) and preparing for national exams."
}
default_lang = "🇷🇺 Русский"

user_state = {}

router = Router()

@router.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Alege limba / Выбери язык / Choose language:", reply_markup=lang_kb)

@router.message(lambda m: m.text in system_prompts.keys())
async def language_handler(message: types.Message):
    uid = message.from_user.id
    user_state[uid] = {"lang": message.text}
    text = {
        "🇷🇴 Română": "Salut! Trimite-mi o întrebare legată de temă sau BAC.",
        "🇷🇺 Русский": "Привет! Отправь мне вопрос по домашке или экзамену.",
        "🇬🇧 English": "Hi! Ask me anything related to school or exams."
    }
    await message.answer(text[message.text])

@router.message()
async def main_handler(message: types.Message):
    uid = message.from_user.id
    lang = user_state.get(uid, {}).get("lang", default_lang)
    prompt = message.text

    sys_prompt = system_prompts.get(lang, system_prompts[default_lang])

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama3-8b-8192",
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
                if resp.status != 200:
                    err_text = await resp.text()
                    logging.error(f"Groq API error: {resp.status}, {err_text}")
                    await message.answer("⚠️ Eroare / Ошибка / Error: API error, try later.")
                    return
                result = await resp.json()
                answer = result["choices"][0]["message"]["content"]
                await message.answer(answer.strip())
        except asyncio.TimeoutError:
            await message.answer("⚠️ Eroare / Ошибка / Error: Timeout, try again.")
        except Exception as e:
            logging.exception("Unexpected error")
            await message.answer("⚠️ Eroare / Ошибка / Error: Unexpected error.")

async def main():
    session = AiohttpSession()
    bot = Bot(token=TELEGRAM_TOKEN, session=session)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

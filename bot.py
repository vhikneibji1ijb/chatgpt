import logging
import os
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv

# Загружаем .env переменные
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Проверка на наличие токенов
if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("❌ Не найдены токены в переменных окружения. Проверь TELEGRAM_TOKEN и GROQ_API_KEY!")

# Инициализация бота
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

user_state = {}

# Клавиатура выбора языка
lang_kb = ReplyKeyboardMarkup(resize_keyboard=True)
lang_kb.add(
    KeyboardButton("🇷🇴 Română"),
    KeyboardButton("🇷🇺 Русский"),
    KeyboardButton("🇬🇧 English")
)

@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    await message.answer("Alege limba / Выбери язык / Choose language:", reply_markup=lang_kb)

@dp.message_handler(lambda m: m.text in ["🇷🇴 Română", "🇷🇺 Русский", "🇬🇧 English"])
async def language_handler(message: types.Message):
    uid = message.from_user.id
    user_state[uid] = {"lang": message.text}
    text = {
        "🇷🇴 Română": "Salut! Trimite-mi o întrebare legată de temă sau BAC.",
        "🇷🇺 Русский": "Привет! Отправь мне вопрос по домашке или экзамену.",
        "🇬🇧 English": "Hi! Ask me anything related to school or exams."
    }
    await message.answer(text[message.text])

@dp.message_handler()
async def main_handler(message: types.Message):
    uid = message.from_user.id
    lang = user_state.get(uid, {}).get("lang", "🇷🇺 Русский")
    prompt = message.text

    system_prompts = {
        "🇷🇴 Română": "Ești un profesor din Moldova care explică materia elevilor din clasele 5–12, inclusiv pentru examenele EN și BAC.",
        "🇷🇺 Русский": "Ты учитель из Молдовы, объясняющий школьные темы ученикам 5–12 классов, готовишь к EN и BAC.",
        "🇬🇧 English": "You are a Moldovan teacher explaining school material to students (grades 5–12) and preparing for national exams."
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "mixtral-8x7b-32768",  # Можно заменить на llama3-8b-8192
        "messages": [
            {"role": "system", "content": system_prompts[lang]},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
        await message.answer(answer.strip())
    except Exception as e:
        await message.answer("⚠️ Eroare / Ошибка / Error:\n" + str(e))

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

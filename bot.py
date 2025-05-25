import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from openai import OpenAI  # Импортируем новый клиент
import os
from dotenv import load_dotenv

# Загружаем .env переменные
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Проверка на наличие токенов
if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise ValueError("❌ Не найдены токены в переменных окружения. Проверь переменные TELEGRAM_TOKEN и OPENAI_API_KEY!")

# Инициализация клиента OpenAI с API ключом
client = OpenAI(api_key=OPENAI_API_KEY)

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

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompts[lang]},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        answer = response.choices[0].message.content.strip()
        await message.answer(answer)
    except Exception as e:
        await message.answer("⚠️ Eroare / Ошибка / Error: " + str(e))

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

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
    "🇷🇴 Română": (
        "ro",
        "Răspunde doar în limba română. Când explici formule matematice, folosește simboluri matematice naturale: √ pentru radical, fracții cu / sau caractere Unicode (ex: ½), puteri cu ^ (ex: x^2). Pentru formule mai complexe, folosește LaTeX între delimitatori $...$ (ex: $\\frac{a}{b}$ sau $\\sqrt{a}$). Nu folosi bold, italics, stelute, markdown sau emoji."
    ),
    "🇷🇺 Русский": (
        "ru",
        "Отвечай только на русском языке. Для математических формул используй стандартные математические символы: √ для корня, дроби с помощью / или символов Юникода (например, ½), степени с помощью ^ (например, x^2). Для сложных формул используй LaTeX в пределах $...$ (например, $\\frac{a}{b}$ или $\\sqrt{a}$). Не используй жирный, курсив, звездочки, markdown или эмодзи."
    ),
    "🇬🇧 English": (
        "en",
        "Reply only in English. When explaining math formulas, use standard math symbols: √ for square root, fractions with / or Unicode characters (e.g., ½), exponents with ^ (e.g., x^2). For complex formulas, use LaTeX between $...$ (for example, $\\frac{a}{b}$ or $\\sqrt{a}$). Do not use bold, italics, asterisks, markdown, or emojis."
    ),
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

user_lang = {}  # user_id: emoji языка

user_history = {}  # user_id: list of messages (context)
MAX_CONTEXT = 5    # сколько пар сообщений (вопрос+ответ) помнить

router = Router()

def get_sys_prompt(lang):
    base = LANGUAGES[lang][1]
    extra = " Scrie toate formulele matematice cât mai clar, folosind simbolurile adecvate sau LaTeX dacă nu se poate altfel. Nu folosi niciun fel de markdown, stelute, bold sau emoji."
    return base + extra

ADMIN_IDS = [6009593253]  # <-- замените на свой Telegram user_id

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

@router.message(Command("start"))
@router.message(Command("language"))
async def choose_language(message: types.Message):
    user_history.pop(message.from_user.id, None)
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

@router.message()
async def ask_groq(message: types.Message):
    user_id = message.from_user.id

    # Если пользователь еще не выбрал язык — показываем клаву
    if user_id not in user_lang:
        await message.answer(
            "Пожалуйста, выберите язык / Vă rugăm să alegeți limba / Please choose language:",
            reply_markup=lang_kb
        )
        return

    # Ограничение FREE
    if not is_pro(user_id):
        if len(message.text) > 250:
            await message.answer("❗ Это доступно только для PRO пользователей. Для расширенных возможностей напишите /pro")
            return

    # === История для контекста ===
    hist = user_history.setdefault(user_id, [])
    hist.append({"role": "user", "content": message.text.strip()})
    if len(hist) > MAX_CONTEXT * 2:
        hist = hist[-MAX_CONTEXT * 2 :]
    user_history[user_id] = hist

    lang = user_lang.get(user_id, DEFAULT_LANG)
    sys_prompt = get_sys_prompt(lang)
    messages_for_groq = [{"role": "system", "content": sys_prompt}] + hist

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages_for_groq,
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
                    hist.append({"role": "assistant", "content": answer.strip()})
                    if len(hist) > MAX_CONTEXT * 2:
                        hist = hist[-MAX_CONTEXT * 2 :]
                    user_history[user_id] = hist
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

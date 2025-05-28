import os
import logging
import asyncio
import re
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
        "Răspunde doar în limba română. Scrie formulele matematice exact ca de mână pe caiet: folosește √ pentru radical, fracțiile scrie-le ca (numărător)/(numitor), de exemplu (a+b)/c sau (√3)/2, iar pentru puteri folosește caractere Unicode pentru exponenți (x², c⁵, aⁿ), nu simbolul ^. Nu folosi niciodată LaTeX, nici fracții suprapuse, nici simboluri speciale. Nu folosi bold, italics, stelute, markdown sau emoji. Scrie răspunsul ca un text continuu, nu folosi niciodată liste, stelute, buline, liniuțe, nici numerotare. Fiecare formulă sau pas se scrie pe un rând nou, fără alte simboluri la începutul rândului."
    ),
    "🇷🇺 Русский": (
        "ru",
        "Отвечай только на русском языке. Записывай математические формулы так, как пишут от руки: √ для корня, дроби как (числитель)/(знаменатель), например (a+b)/c или (√3)/2, степени с помощью Unicode-символов (x², c⁵, aⁿ), не символ ^. Никогда не используй LaTeX, не пиши дроби вертикально и не используй специальные символы. Не используй жирный, курсив, звёздочки, markdown или эмодзи. Пиши ответ как обычный текст, не используй никогда списки, звёздочки, буллиты, тире или нумерацию. Каждую формулу или шаг пиши на новой строке без символов в начале строки."
    ),
    "🇬🇧 English": (
        "en",
        "Reply only in English. Write mathematical formulas as if written by hand: use √ for square root, fractions as (numerator)/(denominator), e.g., (a+b)/c or (√3)/2, and for powers use Unicode superscript characters for exponents (x², c⁵, aⁿ), not the ^ symbol. Never use LaTeX, stacked fractions, or special symbols. Do not use bold, italics, asterisks, markdown, or emojis. Write the answer as plain text, never use lists, bullets, asterisks, dashes or numbering. Each formula or step should be written on a new line, with no symbols at the start of the line."
    ),
}
DEFAULT_LANG = "🇷🇺 Русский"

# Tastatura pentru alegerea limbii (la start/language)
lang_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🇷🇴 Română")],
        [KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇬🇧 English")]
    ],
    resize_keyboard=True
)

# Tastatura cu "Chat nou" (după alegerea limbii)
chat_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🆕 Chat nou")]
    ],
    resize_keyboard=True
)

user_lang = {}  # user_id: emoji языка

user_history = {}  # user_id: list of messages (context)
MAX_CONTEXT = 5    # сколько пар сообщений (вопрос+ответ) помнить

router = Router()

def get_sys_prompt(lang):
    return LANGUAGES[lang][1]

ADMIN_IDS = [6009593253]  # <-- замените на свой Telegram user_id

def clean_star_lines(text):
    # Elimină stelute/liniuțe/bullets la început de rând + spații, dar nu atinge conținutul rândului
    return re.sub(r'^[\*\-\•\u2022]\s*', '', text, flags=re.MULTILINE)

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

@router.message(Command("newchat"))
@router.message(lambda m: m.text and m.text.strip() == "🆕 Chat nou")
async def new_chat(message: types.Message):
    user_history.pop(message.from_user.id, None)
    await message.answer(
        "Ai început un chat nou! Întreabă orice vrei.",
        reply_markup=chat_kb
    )

@router.message(lambda m: m.text in LANGUAGES)
async def set_language(message: types.Message):
    user_lang[message.from_user.id] = message.text
    greetings = {
        "🇷🇴 Română": "Salut! Trimite-mi întrebarea ta.",
        "🇷🇺 Русский": "Привет! Задай свой вопрос.",
        "🇬🇧 English": "Hi! Please ask your question."
    }
    # După alegerea limbii, arată doar butonul "Chat nou"
    await message.answer(greetings[message.text], reply_markup=chat_kb)

@router.message()
async def ask_groq(message: types.Message):
    user_id = message.from_user.id

    # Dacă utilizatorul nu a ales limba - afișează tastatura de limbi
    if user_id not in user_lang:
        await message.answer(
            "Пожалуйста, выберите язык / Vă rugăm să alegeți limba / Please choose language:",
            reply_markup=lang_kb
        )
        return

    # Limita pentru utilizatorii FREE
    if not is_pro(user_id):
        if len(message.text) > 250:
            await message.answer("❗ Это доступно только для PRO пользователей. Для расширенных возможностей напишите /pro")
            return

    # Butonul "Chat nou" - șterge istoria și păstrează butonul
    if message.text.strip() == "🆕 Chat nou":
        user_history.pop(user_id, None)
        await message.answer(
            "Ai început un chat nou! Întreabă orice vrei.",
            reply_markup=chat_kb
        )
        return

    # Istoric pentru context
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
                    answer = clean_star_lines(answer.strip())
                    hist.append({"role": "assistant", "content": answer})
                    if len(hist) > MAX_CONTEXT * 2:
                        hist = hist[-MAX_CONTEXT * 2 :]
                    user_history[user_id] = hist
                    await message.answer(answer, reply_markup=chat_kb)
                else:
                    err_text = await resp.text()
                    logging.error(f"Groq API error: {resp.status}, {err_text}")
                    await message.answer("⚠️ Ошибка API. Попробуйте позже.", reply_markup=chat_kb)
        except Exception as e:
            logging.exception("Error contacting Groq API")
            await message.answer("⚠️ Ошибка при обращении к API. Попробуйте позже.", reply_markup=chat_kb)

async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

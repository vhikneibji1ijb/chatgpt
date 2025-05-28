import os
import logging
import asyncio
import re
import json
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

lang_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🇷🇴 Română")],
        [KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇬🇧 English")]
    ],
    resize_keyboard=True
)

profile_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔄 Schimbă limba")],
        [KeyboardButton(text="💳 Cumpără PRO")],
        [KeyboardButton(text="🆘 Ajutor administrator")],
        [KeyboardButton(text="🆕 Chat nou")]
    ],
    resize_keyboard=True
)

chat_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🆕 Chat nou")]
    ],
    resize_keyboard=True
)

LANG_FILE = "user_lang.json"
HIST_FILE = "user_history.json"

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

user_lang = load_json(LANG_FILE)
user_history = load_json(HIST_FILE)

MAX_CONTEXT = 5

router = Router()

def get_sys_prompt(lang):
    return LANGUAGES[lang][1]

ADMIN_IDS = [6009593253]

def clean_star_lines(text):
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
async def start_handler(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_lang:
        await message.answer(
            "Выберите язык / Alege limba / Choose language:",
            reply_markup=lang_kb
        )
    else:
        total_intrebari = len(user_history.get(user_id, [])) // 2 if user_id in user_history else 0
        tip_cont = "Pro" if is_pro(int(user_id)) else "Free"
        limba = user_lang.get(user_id, DEFAULT_LANG)
        profil = {
            "nume": f"{message.from_user.full_name}",
            "uid": f"#U{user_id}",
            "reg": "2024-11-15",
            "tip": tip_cont,
            "intrebari": f"{total_intrebari}",
            "status": "Activ",
            "limba": limba,
            "ultima": "N/A",
            "tara": "🇲🇩 Moldova"
        }
        text = (
            f"👤 <b>Nume Utilizator:</b> {profil['nume']}\n"
            f"🆔 <b>ID Utilizator:</b> {profil['uid']}\n"
            f"📆 <b>Data Înregistrării:</b> {profil['reg']}\n"
            f"💼 <b>Tip Cont:</b> {profil['tip']}\n"
            f"❓ <b>Total Întrebări:</b> {profil['intrebari']}\n"
            f"✅ <b>Status:</b> {profil['status']}\n"
            f"🌐 <b>Limba Preferată:</b> {profil['limba']}\n"
            f"🕒 <b>Ultima Activitate:</b> {profil['ultima']}\n"
            f"🌍 <b>Țara:</b> {profil['tara']}\n"
        )
        await message.answer(text, reply_markup=profile_kb, parse_mode="HTML")

@router.message(lambda m: m.text in LANGUAGES)
async def set_language(message: types.Message):
    user_id = str(message.from_user.id)
    user_lang[user_id] = message.text
    save_json(LANG_FILE, user_lang)
    # După setare limba, arată profilul direct!
    total_intrebari = len(user_history.get(user_id, [])) // 2 if user_id in user_history else 0
    tip_cont = "Pro" if is_pro(int(user_id)) else "Free"
    profil = {
        "nume": f"{message.from_user.full_name}",
        "uid": f"#U{user_id}",
        "reg": "2024-11-15",
        "tip": tip_cont,
        "intrebari": f"{total_intrebari}",
        "status": "Activ",
        "limba": message.text,
        "ultima": "N/A",
        "tara": "🇲🇩 Moldova"
    }
    text = (
        f"👤 <b>Nume Utilizator:</b> {profil['nume']}\n"
        f"🆔 <b>ID Utilizator:</b> {profil['uid']}\n"
        f"📆 <b>Data Înregistrării:</b> {profil['reg']}\n"
        f"💼 <b>Tip Cont:</b> {profil['tip']}\n"
        f"❓ <b>Total Întrebări:</b> {profil['intrebari']}\n"
        f"✅ <b>Status:</b> {profil['status']}\n"
        f"🌐 <b>Limba Preferată:</b> {profil['limba']}\n"
        f"🕒 <b>Ultima Activitate:</b> {profil['ultima']}\n"
        f"🌍 <b>Țara:</b> {profil['tara']}\n"
    )
    await message.answer(text, reply_markup=profile_kb, parse_mode="HTML")

@router.message(lambda m: m.text == "🔄 Schimbă limba")
async def show_langs(message: types.Message):
    await message.answer("Alege limba dorită:", reply_markup=lang_kb)

@router.message(lambda m: m.text == "🆘 Ajutor administrator")
async def help_admin(message: types.Message):
    await message.answer(
        "Pentru a lua legătura cu un administrator, scrie pe Telegram: @adminusername\n"
        "sau trimite un email la: admin@gmail.com"
    )

@router.message(lambda m: m.text == "🆕 Chat nou")
async def new_chat_profile(message: types.Message):
    user_id = str(message.from_user.id)
    user_history.pop(user_id, None)
    save_json(HIST_FILE, user_history)
    await message.answer(
        "Ai început un chat nou! Întreabă orice vrei.",
        reply_markup=chat_kb   # <--- DOAR Chat nou!
    )

# Poți adăuga aici handler pentru "💳 Cumpără PRO" când va fi nevoie

@router.message(Command("language"))
async def choose_language(message: types.Message):
    user_history.pop(str(message.from_user.id), None)
    save_json(HIST_FILE, user_history)
    user_lang.pop(str(message.from_user.id), None)
    save_json(LANG_FILE, user_lang)
    await message.answer(
        "Выберите язык / Alege limba / Choose language:",
        reply_markup=lang_kb
    )

@router.message(Command("newchat"))
async def new_chat_cmd(message: types.Message):
    user_history.pop(str(message.from_user.id), None)
    save_json(HIST_FILE, user_history)
    await message.answer(
        "Ai început un chat nou! Întreabă orice vrei.",
        reply_markup=chat_kb
    )

@router.message()
async def ask_groq(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_lang:
        await message.answer(
            "Пожалуйста, выберите язык / Vă rugăm să alegeți limba / Please choose language:",
            reply_markup=lang_kb
        )
        return

    if not is_pro(int(user_id)):
        if len(message.text) > 250:
            await message.answer("❗ Это доступно только для PRO пользователей. Для расширенных возможностей напишите /pro", reply_markup=chat_kb)
            return

    if message.text.strip() == "🆕 Chat nou":
        user_history.pop(user_id, None)
        save_json(HIST_FILE, user_history)
        await message.answer(
            "Ai început un chat nou! Întreabă orice vrei.",
            reply_markup=chat_kb
        )
        return

    hist = user_history.setdefault(user_id, [])
    hist.append({"role": "user", "content": message.text.strip()})
    if len(hist) > MAX_CONTEXT * 2:
        hist = hist[-MAX_CONTEXT * 2 :]
    user_history[user_id] = hist
    save_json(HIST_FILE, user_history)

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
                    save_json(HIST_FILE, user_history)
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

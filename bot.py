import os
import logging
import asyncio
import re
import json
import datetime
import pytesseract
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import aiohttp
import pytesseract
from PIL import Image
from io import BytesIO
from googletrans import Translator

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
        "Dacă întrebarea utilizatorului este despre rezolvarea unei probleme sau calcule matematice, răspunde folosind formule și pași clari scriși ca de mână: folosește √ pentru radical, fracțiile ca (numărător)/(numitor), de exemplu (a+b)/c sau (√3)/2, puterile cu caractere Unicode pentru exponenți (x², c⁵, aⁿ), nu simbolul ^. Nu folosi niciodată LaTeX, fracții suprapuse, bold, italics, stelute, markdown sau emoji. Scrie formulele pe câte un rând, fără alte simboluri la începutul rândului. Dacă întrebarea nu este despre o problemă concretă, ci este despre sfaturi, teorie, motivație sau metode de învățare, răspunde cu un text explicativ, clar și prietenos, pe înțelesul elevului."
    ),
    "🇷🇺 Русский": (
        "ru",
        "Если вопрос пользователя о решении математической задачи или вычисления, отвечай формулами и шагами, как пишут от руки: √ для корня, дроби как (числитель)/(знаменатель), например (a+b)/c или (√3)/2, степени с помощью Unicode-символов (x², c⁵, aⁿ), не символ ^. Никогда не используй LaTeX, дроби вертикально, жирный, курсив, звёздочки, markdown или эмодзи. Формулы пиши на отдельных строках без символов в начале строки. Если вопрос не о конкретной задаче, а о советах, теории, мотивации или методах обучения, дай понятный, дружелюбный, развернутый ответ обычным текстом."
    ),
    "🇬🇧 English": (
        "en",
        "If the user's question is about solving a mathematical problem or calculation, answer using formulas and clear steps as if written by hand: use √ for roots, fractions as (numerator)/(denominator), e.g., (a+b)/c or (√3)/2, and for powers use Unicode superscript characters (x², c⁵, aⁿ), not the ^ symbol. Never use LaTeX, stacked fractions, bold, italics, asterisks, markdown, or emojis. Write formulas on separate lines, with no symbols at the beginning. If the question is not about a specific math problem but rather about advice, theory, motivation, or learning methods, provide a clear, friendly, and detailed answer in regular text."
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
REG_FILE = "user_reg.json"
OCR_TEXT_FILE = "user_ocr.json"

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
user_reg = load_json(REG_FILE)
user_ocr = load_json(OCR_TEXT_FILE)

MAX_CONTEXT = 5

router = Router()
translator = Translator()

def get_sys_prompt(lang):
    return LANGUAGES[lang][1]

ADMIN_IDS = [6009593253]

def clean_star_lines(text):
    return re.sub(r'^[\*\-\•\u2022]\s*', '', text, flags=re.MULTILINE)

# Functie pentru profil (cu data reala de inregistrare)
async def send_profile(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_reg:
        user_reg[user_id] = datetime.datetime.now().strftime("%Y-%m-%d")
        save_json(REG_FILE, user_reg)
    data_reg = user_reg.get(user_id, "N/A")
    total_intrebari = len(user_history.get(user_id, [])) // 2 if user_id in user_history else 0
    tip_cont = "Pro" if is_pro(int(user_id)) else "Free"
    limba = user_lang.get(user_id, DEFAULT_LANG)
    profil = {
        "nume": f"{message.from_user.full_name}",
        "uid": f"#U{user_id}",
        "reg": data_reg,
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

# --- OCR & TRADUCERE IMAGINI ---
@router.message(lambda m: m.content_type == "photo")
async def handle_photo(message: types.Message):
    user_id = str(message.from_user.id)
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_path = file.file_path
    file_bytes = await message.bot.download_file(file_path)
    image = Image.open(BytesIO(file_bytes.read()))

    try:
        extracted_text = pytesseract.image_to_string(image, lang="ron+eng+rus")
    except Exception as e:
        await message.reply("Eroare la recunoaștere text din imagine.")
        return

    if not extracted_text.strip():
        await message.reply("Nu am putut extrage niciun text clar din această poză.")
        return

    user_ocr[user_id] = extracted_text
    save_json(OCR_TEXT_FILE, user_ocr)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔎 Extrage problema matematică")],
            [KeyboardButton(text="🌐 Tradu textul")]
        ],
        resize_keyboard=True
    )
    await message.reply(
        f"Text extras din imagine:\n\n{extracted_text}\n\nCe vrei să fac cu acest text?",
        reply_markup=kb
    )

@router.message(lambda m: m.text == "🌐 Tradu textul")
async def translate_last_ocr(message: types.Message):
    user_id = str(message.from_user.id)
    user_ocr_text = user_ocr.get(user_id)
    if not user_ocr_text:
        await message.reply("Nu am text de tradus. Trimite o poză mai întâi.")
        return
    translation = translator.translate(user_ocr_text, dest="ro")
    await message.reply(f"Traducere în română:\n\n{translation.text}")

@router.message(lambda m: m.text == "🔎 Extrage problema matematică")
async def analyze_math_problem(message: types.Message):
    user_id = str(message.from_user.id)
    user_ocr_text = user_ocr.get(user_id)
    if not user_ocr_text:
        await message.reply("Nu am text de analizat. Trimite o poză mai întâi.")
        return
    await message.reply(f"Problema matematică extrasă:\n\n{user_ocr_text}")
    # Poți integra aici și trimiterea la AI pentru rezolvare automată dacă vrei

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
            await message.answer("V-a fost activat PRO pe 30 zile.")
        await send_profile(message)
    else:
        await message.answer("Obratites k administratoru dlya polucheniya PRO.")

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
            await message.answer("PRO a fost dezactivat.")
        await send_profile(message)
    else:
        await message.answer("Obratites k administratoru.")

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
        await send_profile(message)

@router.message(lambda m: m.text in LANGUAGES)
async def set_language(message: types.Message):
    user_id = str(message.from_user.id)
    user_lang[user_id] = message.text
    save_json(LANG_FILE, user_lang)
    await send_profile(message)

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
        reply_markup=chat_kb
    )

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

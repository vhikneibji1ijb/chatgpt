import os
import logging
import asyncio
import re
import json
import datetime
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import aiohttp
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
DEFAULT_LANG = "🇷🇴 Română"

MESSAGES = {
    "choose_language": {
        "ro": "Alege limba dorită:",
        "ru": "Выберите язык:",
        "en": "Choose your preferred language:"
    },
    "start_new_chat": {
        "ro": "Ai început un chat nou! Întreabă orice vrei.",
        "ru": "Вы начали новый чат! Задайте любой вопрос.",
        "en": "You have started a new chat! Ask anything."
    },
    "no_ocr_text": {
        "ro": "Nu am text de tradus. Trimite o poză mai întâi.",
        "ru": "Нет текста для перевода. Сначала отправьте фото.",
        "en": "No text to translate. Please send a photo first."
    },
    "ocr_fail": {
        "ro": "Nu am putut recunoaște textul din imagine :(",
        "ru": "Не удалось распознать текст через онлайн OCR :(",
        "en": "Failed to recognize text from image :("
    },
    "send_photo": {
        "ro": "Trimite o poză cu text.",
        "ru": "Отправьте фото с текстом.",
        "en": "Send a photo with text."
    },
    "profile_intro": {
        "ro": "Profilul tău:",
        "ru": "Ваш профиль:",
        "en": "Your profile:"
    },
    "admin_help": {
        "ro": "Pentru a lua legătura cu un administrator, scrie pe Telegram: @adminusername\nsau trimite un email la: admin@gmail.com",
        "ru": "Для связи с администратором напишите в Telegram: @adminusername\nили на email: admin@gmail.com",
        "en": "To contact an administrator, write on Telegram: @adminusername\nor send an email to: admin@gmail.com"
    },
    "choose_lang_cmd": {
        "ro": "Alege limba dorită:",
        "ru": "Выберите язык:",
        "en": "Choose your preferred language:"
    },
    "pro_only": {
        "ro": "❗ Aceasta este disponibil doar pentru utilizatorii PRO. Pentru funcționalități extinse, scrie /pro",
        "ru": "❗ Это доступно только для PRO пользователей. Для расширенных возможностей напишите /pro",
        "en": "❗ This is only available for PRO users. For advanced features, type /pro"
    }
}

BUTTONS = {
    "new_chat": {
        "ro": "🆕 Chat nou",
        "ru": "🆕 Новый чат",
        "en": "🆕 New chat"
    },
    "extract_math": {
        "ro": "🔎 Extrage problema matematică",
        "ru": "🔎 Извлечь задачу",
        "en": "🔎 Extract math problem"
    },
    "translate_text": {
        "ro": "🌐 Tradu textul",
        "ru": "🌐 Перевести текст",
        "en": "🌐 Translate text"
    },
    "change_language": {
        "ro": "🔄 Schimbă limba",
        "ru": "🔄 Сменить язык",
        "en": "🔄 Change language"
    },
    "buy_pro": {
        "ro": "💳 Cumpără PRO",
        "ru": "💳 Купить PRO",
        "en": "💳 Buy PRO"
    },
    "admin_help": {
        "ro": "🆘 Ajutor administrator",
        "ru": "🆘 Помощь администратора",
        "en": "🆘 Admin help"
    }
}

def get_lang_code(user_id):
    user_lang_str = user_lang.get(user_id, DEFAULT_LANG)
    return LANGUAGES[user_lang_str][0]

def get_reply_kb(buttons, lang_code):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BUTTONS[btn][lang_code])] for btn in buttons],
        resize_keyboard=True
    )

lang_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=lang)] for lang in LANGUAGES.keys()],
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

async def online_ocr_space(image_bytes, lang="eng"):
    api_url = "https://api.ocr.space/parse/image"
    headers = {
        "apikey": "K86260492688957"
    }
    data = aiohttp.FormData()
    data.add_field("file", image_bytes, filename="image.jpg")
    data.add_field("language", lang)
    data.add_field("isOverlayRequired", "false")
    data.add_field("OCREngine", "2")
    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, data=data, headers=headers) as resp:
            try:
                result = await resp.json()
                print("Ответ OCR.space:", result)
                return result["ParsedResults"][0]["ParsedText"]
            except Exception as e:
                print("Ошибка при разборе ответа OCR:", e)
                return None

async def send_profile(message: types.Message):
    user_id = str(message.from_user.id)
    lang_code = get_lang_code(user_id)
    if user_id not in user_reg:
        user_reg[user_id] = datetime.datetime.now().strftime("%Y-%m-%d")
        save_json(REG_FILE, user_reg)
    data_reg = user_reg.get(user_id, "N/A")
    total_questions = len(user_history.get(user_id, [])) // 2 if user_id in user_history else 0
    account_type = "Pro" if is_pro(int(user_id)) else "Free"
    lang = user_lang.get(user_id, DEFAULT_LANG)
    profile = {
        "name": f"{message.from_user.full_name}",
        "uid": f"#U{user_id}",
        "reg": data_reg,
        "type": account_type,
        "questions": f"{total_questions}",
        "status": "Active",
        "lang": lang,
        "last": "N/A",
        "country": "🇲🇩 Moldova"
    }
    text = (
        f"{MESSAGES['profile_intro'][lang_code]}\n"
        f"👤 <b>{profile['name']}</b>\n"
        f"🆔 {profile['uid']}\n"
        f"📆 {profile['reg']}\n"
        f"💼 {profile['type']}\n"
        f"❓ {profile['questions']}\n"
        f"✅ {profile['status']}\n"
        f"🌐 {profile['lang']}\n"
        f"🕒 {profile['last']}\n"
        f"🌍 {profile['country']}\n"
    )
    kb = get_reply_kb(["change_language", "buy_pro", "admin_help", "new_chat"], lang_code)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.message(lambda m: m.content_type == "photo")
async def handle_photo(message: types.Message):
    user_id = str(message.from_user.id)
    lang_code = get_lang_code(user_id)
    print("Фото получено!")
    try:
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        image_bytes = file_bytes.read()
    except Exception as e:
        await message.reply(f"Ошибка при получении фото: {e}")
        print("Ошибка при получении фото:", e)
        return

    try:
        extracted_text = await online_ocr_space(image_bytes, lang=lang_code)
        print("Результат OCR:", extracted_text)
    except Exception as e:
        await message.reply(f"Ошибка при обращении к OCR.space: {e}")
        print("Ошибка при OCR:", e)
        return

    if not extracted_text or not extracted_text.strip():
        await message.reply(MESSAGES["ocr_fail"][lang_code])
        print("Пустой результат OCR")
        return

    user_ocr[user_id] = extracted_text
    save_json(OCR_TEXT_FILE, user_ocr)

    kb = get_reply_kb(["extract_math", "translate_text"], lang_code)
    await message.reply(
        f"{MESSAGES['send_photo'][lang_code]}\n\n{extracted_text}\n\n",
        reply_markup=kb
    )
    print("Кнопки отправлены пользователю")

@router.message(lambda m: m.text in [BUTTONS["translate_text"][l] for l in BUTTONS["translate_text"].keys()])
async def translate_last_ocr(message: types.Message):
    user_id = str(message.from_user.id)
    lang_code = get_lang_code(user_id)
    user_ocr_text = user_ocr.get(user_id)
    if not user_ocr_text:
        await message.reply(MESSAGES["no_ocr_text"][lang_code])
        return
    try:
        translation = translator.translate(user_ocr_text, dest=lang_code)
        await message.reply(f"{translation.text}")
    except Exception as e:
        await message.reply(f"Ошибка при переводе: {e}")

@router.message(lambda m: m.text in [BUTTONS["extract_math"][l] for l in BUTTONS["extract_math"].keys()])
async def analyze_math_problem(message: types.Message):
    user_id = str(message.from_user.id)
    lang_code = get_lang_code(user_id)
    user_ocr_text = user_ocr.get(user_id)
    if not user_ocr_text:
        await message.reply(MESSAGES["no_ocr_text"][lang_code])
        return
    await message.reply(f"{user_ocr_text}")

@router.message(Command("pro"))
async def make_pro(message: types.Message):
    user_id = str(message.from_user.id)
    lang_code = get_lang_code(user_id)
    if user_id in ADMIN_IDS:
        parts = message.text.split()
        if len(parts) >= 2:
            uid = int(parts[1])
            set_pro(uid)
            await message.answer(f"Пользователю {uid} выдан PRO на 30 дней.")
        else:
            set_pro(message.from_user.id)
            await message.answer("Вам выдан PRO на 30 дней.")
        await send_profile(message)
    else:
        await message.answer("Обратитесь к администратору для получения PRO.")

@router.message(Command("free"))
async def remove_pro(message: types.Message):
    user_id = str(message.from_user.id)
    lang_code = get_lang_code(user_id)
    if user_id in ADMIN_IDS:
        parts = message.text.split()
        if len(parts) >= 2:
            uid = int(parts[1])
            set_free(uid)
            await message.answer(f"У пользователя {uid} снят PRO.")
        else:
            set_free(message.from_user.id)
            await message.answer("PRO был отключён.")
        await send_profile(message)
    else:
        await message.answer("Обратитесь к администратору.")

@router.message(Command("status"))
async def status(message: types.Message):
    lang_code = get_lang_code(str(message.from_user.id))
    if is_pro(message.from_user.id):
        await message.answer("У вас PRO-доступ 🟢")
    else:
        await message.answer("У вас обычный доступ 🔘. Для расширенных возможностей напишите /pro")

@router.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = str(message.from_user.id)
    lang_code = get_lang_code(user_id)
    if user_id not in user_lang:
        await message.answer(MESSAGES["choose_language"][lang_code], reply_markup=lang_kb)
    else:
        await send_profile(message)

@router.message(lambda m: m.text in LANGUAGES)
async def set_language(message: types.Message):
    user_id = str(message.from_user.id)
    user_lang[user_id] = message.text
    save_json(LANG_FILE, user_lang)
    await send_profile(message)

@router.message(lambda m: m.text in [BUTTONS["change_language"][l] for l in BUTTONS["change_language"].keys()])
async def show_langs(message: types.Message):
    lang_code = get_lang_code(str(message.from_user.id))
    await message.answer(MESSAGES["choose_language"][lang_code], reply_markup=lang_kb)

@router.message(lambda m: m.text in [BUTTONS["admin_help"][l] for l in BUTTONS["admin_help"].keys()])
async def help_admin(message: types.Message):
    lang_code = get_lang_code(str(message.from_user.id))
    await message.answer(MESSAGES["admin_help"][lang_code])

@router.message(lambda m: m.text in [BUTTONS["new_chat"][l] for l in BUTTONS["new_chat"].keys()])
async def new_chat_profile(message: types.Message):
    user_id = str(message.from_user.id)
    lang_code = get_lang_code(user_id)
    user_history.pop(user_id, None)
    save_json(HIST_FILE, user_history)
    kb = get_reply_kb(["new_chat"], lang_code)
    await message.answer(
        MESSAGES["start_new_chat"][lang_code],
        reply_markup=kb
    )

@router.message(Command("language"))
async def choose_language(message: types.Message):
    user_id = str(message.from_user.id)
    lang_code = get_lang_code(user_id)
    user_history.pop(user_id, None)
    save_json(HIST_FILE, user_history)
    user_lang.pop(user_id, None)
    save_json(LANG_FILE, user_lang)
    await message.answer(
        MESSAGES["choose_lang_cmd"][lang_code],
        reply_markup=lang_kb
    )

@router.message(Command("newchat"))
async def new_chat_cmd(message: types.Message):
    user_id = str(message.from_user.id)
    lang_code = get_lang_code(user_id)
    user_history.pop(user_id, None)
    save_json(HIST_FILE, user_history)
    kb = get_reply_kb(["new_chat"], lang_code)
    await message.answer(
        MESSAGES["start_new_chat"][lang_code],
        reply_markup=kb
    )

@router.message()
async def ask_groq(message: types.Message):
    user_id = str(message.from_user.id)
    lang_code = get_lang_code(user_id)
    if user_id not in user_lang:
        await message.answer(
            MESSAGES["choose_language"][lang_code],
            reply_markup=lang_kb
        )
        return

    if not is_pro(int(user_id)):
        if len(message.text) > 250:
            await message.answer(MESSAGES["pro_only"][lang_code], reply_markup=get_reply_kb(["new_chat"], lang_code))
            return

    if message.text.strip() in [BUTTONS["new_chat"][l] for l in BUTTONS["new_chat"].keys()]:
        user_history.pop(user_id, None)
        save_json(HIST_FILE, user_history)
        await message.answer(
            MESSAGES["start_new_chat"][lang_code],
            reply_markup=get_reply_kb(["new_chat"], lang_code)
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
                    await message.answer(answer, reply_markup=get_reply_kb(["new_chat"], lang_code))
                else:
                    err_text = await resp.text()
                    logging.error(f"Groq API error: {resp.status}, {err_text}")
                    await message.answer("⚠️ Ошибка API. Попробуйте позже.", reply_markup=get_reply_kb(["new_chat"], lang_code))
        except Exception as e:
            logging.exception("Error contacting Groq API")
            await message.answer("⚠️ Ошибка при обращении к API. Попробуйте позже.", reply_markup=get_reply_kb(["new_chat"], lang_code))

async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

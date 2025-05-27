# ... aceleași importuri ca la codul tău de bază ...

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Meniu principal cu buton pentru "Mod Moldova"
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🟩 Mod Republica Moldova complet")],
        [KeyboardButton(text="Matematică"), KeyboardButton(text="Limba Română")],
        [KeyboardButton(text="Chimie"), KeyboardButton(text="Biologie")],
        [KeyboardButton(text="Istorie"), KeyboardButton(text="Alte materii")]
    ],
    resize_keyboard=True
)

user_context = {}

@router.message(Command("start"))
async def start_command(message: types.Message):
    user_context.pop(message.from_user.id, None)
    await message.answer(
        "Bine ai venit! Alege materia sau activează modul special pentru școli din Moldova:",
        reply_markup=main_kb
    )

# Materie selectată
@router.message(lambda m: m.text in ["Matematică", "Limba Română", "Chimie", "Biologie", "Istorie"])
async def materia_aleasa(message: types.Message):
    user_context[message.from_user.id] = message.text
    await message.answer(f"Ai ales {message.text}. Trimite exercițiul sau întrebarea, și voi răspunde după programa Republicii Moldova.")

# MOD Republica Moldova complet
@router.message(lambda m: m.text == "🟩 Mod Republica Moldova complet")
async def mod_md_complet(message: types.Message):
    user_context[message.from_user.id] = "mod_md"
    await message.answer(
        "Modul Republica Moldova activat! Toate explicațiile, verificările și testele vor fi după curriculum, bareme și stilul din școlile moldovenești.\n\n"
        "Trimite orice întrebare sau temă!"
    )

# Handler general
@router.message()
async def raspuns_general(message: types.Message):
    context = user_context.get(message.from_user.id)
    if context == "mod_md":
        # Aici trimiți promptul la Groq sau alt AI cu instrucțiuni speciale pentru sistemul MD!
        await message.answer(f"[MD] Răspuns conform sistemului de învățământ din Moldova: ... {message.text}")
    elif context in ["Matematică", "Limba Română", "Chimie", "Biologie", "Istorie"]:
        # Prompt specializat
        await message.answer(f"[{context}] Răspuns după programa MD: ... {message.text}")
    else:
        # fallback
        await message.answer("Alege întâi materia sau modul complet Moldova din meniu.")

# ... restul funcțiilor și main() ca în codul tău ...

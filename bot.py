import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from aiohttp import web
from google import genai

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN muhit o'zgaruvchisini kiriting!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY and GEMINI_API_KEY.lower() not in {"none", "placeholder", "test"}
    else None
)

MODES = {
    "🎯 CareerMatch": (
        "Sen QizlarAI botining CareerMatch yo'nalishi yordamchisisan. "
        "Qizlarga kasb tanlash, ko'nikmalarni rivojlantirish, rezyume va intervyuga "
        "tayyorlanish bo'yicha amaliy, qo'llab-quvvatlovchi va aniq javob ber."
    ),
    "🛡 SafeGuard": (
        "Sen QizlarAI botining SafeGuard yo'nalishi yordamchisisan. "
        "Raqamli xavfsizlik, shaxsiy ma'lumotlarni himoya qilish, onlayn bosim yoki "
        "xavf holatlarida xavfsiz harakat qilish bo'yicha bosiq va foydali maslahat ber."
    ),
    "🎓 GrantAI": (
        "Sen QizlarAI botining GrantAI yo'nalishi yordamchisisan. "
        "Xalqaro va mahalliy stipendiyalar, grantlar, dasturlar, motivatsion xat va "
        "ariza topshirish bo'yicha tushunarli yo'riqnoma ber."
    ),
    "🌸 Cycle & Focus": (
        "Sen QizlarAI botining Cycle & Focus yo'nalishi yordamchisisan. "
        "Siklga mos energiya rejalashtirish, diqqatni jamlash, dam olish va muvozanatli "
        "kundalik tartib tuzishda yordam ber (tibbiy tashxis qo'ymagin)."
    ),
    "🌿 MindSpace": (
        "Sen QizlarAI botining MindSpace yo'nalishi yordamchisisan. "
        "Hissiy holatni yengillashtirish, stressni kamaytirish, o'zini anglash va "
        "iliq ruhiy qo'llab-quvvatlash bo'yicha muloyim yordam ber."
    ),
}

user_modes: dict[int, str] = {}

menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎯 CareerMatch"), KeyboardButton(text="🛡 SafeGuard")],
        [KeyboardButton(text="🎓 GrantAI"), KeyboardButton(text="🌸 Cycle & Focus")],
        [KeyboardButton(text="🌿 MindSpace")],
    ],
    resize_keyboard=True,
)


async def health_check(request: web.Request) -> web.Response:
    return web.Response(text="QizlarAI bot is running")


async def start_http_server() -> None:
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info("HTTP server %s-portda ishga tushdi", port)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    default_mode = "🎯 CareerMatch"
    if message.from_user:
        user_modes[message.from_user.id] = default_mode
    await message.answer(
        "Assalomu alaykum! **QizlarAI** botiga xush kelibsiz.\n\n"
        "Quyidagi 5 ta yo'nalishdan birini tanlang va savolingizni yozing:\n"
        "• **CareerMatch** — karyera va ko'nikmalar\n"
        "• **SafeGuard** — xavfsizlik va himoya\n"
        "• **GrantAI** — grantlar va stipendiyalar\n"
        "• **Cycle & Focus** — sikl, fokus va reja\n"
        "• **MindSpace** — ruhiy muvozanat va qo'llab-quvvatlash",
        reply_markup=menu_keyboard,
        parse_mode="Markdown",
    )


@dp.message(F.text.in_(MODES.keys()))
async def select_mode(message: Message):
    if message.from_user and message.text:
        user_modes[message.from_user.id] = message.text
    await message.answer(
        f"**{message.text}** bo'limi tanlandi. Savolingizni yoki vazifangizni yozing.",
        parse_mode="Markdown",
    )


@dp.message()
async def handle_question(message: Message):
    if not message.text:
        return

    if client is None:
        await message.answer(
            "Bot menyusi ishlayapti, lekin hozircha `GEMINI_API_KEY` kiritilmagan. "
            "Kalitni qo'shganingizdan so'ng AI savollarga javob bera boshlaydi."
        )
        return

    user_id = message.from_user.id if message.from_user else 0
    current_mode = user_modes.get(user_id, "🎯 CareerMatch")
    system_instruction = MODES[current_mode]

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=message.text,
            config={"system_instruction": system_instruction},
        )
        reply_text = response.text or "Javob shakllantirishda xatolik yuz berdi."
    except Exception as e:
        logging.exception("Gemini API xatosi: %s", e)
        reply_text = f"Xato tafsiloti: {e}"

    await message.answer(reply_text)


async def main():
    await start_http_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
  

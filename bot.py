import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from aiohttp import web
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN muhit o'zgaruvchisini kiriting!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

client = (
    genai.Client(api_key=GEMINI_API_KEY, http_options=types.HttpOptions(timeout=30000))
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


async def ask_gemini_with_retry(prompt: str, system_instruction: str) -> str:
    assert client is not None


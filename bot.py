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
    genai.Client(api_key=GEMINI_API_KEY, http_options=types.HttpOptions(timeout=15000))
    if GEMINI_API_KEY and GEMINI_API_KEY.lower() not in {"none", "placeholder", "test"}
    else None
)

MODELS_TO_TRY = [
    "gemini-3.8-flash",
    "gemini-3.8-flash-lite",
    "gemini-2.5-flash-lite",
]

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


async def ask_gemini_with_fallback(prompt: str, system_instruction: str) -> str:
    assert client is not None
    last_error: Exception | None = None

    for model_name in MODELS_TO_TRY:
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=model_name,
                    contents=prompt,
                    config={"system_instruction": system_instruction},
                ),
                timeout=18,
            )
            text = (response.text or "").strip()
            if text:
                return text
        except Exception as e:
            last_error = e
            logging.warning("Model %s xatosi: %s", model_name, e)
            err_str = str(e)
            if "401" in err_str or "UNAUTHENTICATED" in err_str or "API key not valid" in err_str:
                raise
            await asyncio.sleep(1)

    if last_error is not None:
        raise last_error
    return "Javob shakllantirishda xatolik yuz berdi."


async def send_safe_text(message: Message, text: str) -> None:
    for start in range(0, len(text), 4000):
        chunk = text[start : start + 4000]
        await message.answer(chunk)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    default_mode = "🎯 CareerMatch"
    if message.from_user:
        user_modes[message.from_user.id] = default_mode
    await message.answer(
        "Assalomu alaykum! QizlarAI botiga xush kelibsiz.\n\n"
        "Quyidagi 5 ta yo'nalishdan birini tanlang va savolingizni yozing:\n"
        "• CareerMatch — karyera va ko'nikmalar\n"
        "• SafeGuard — xavfsizlik va himoya\n"
        "• GrantAI — grantlar va stipendiyalar\n"
        "• Cycle & Focus — sikl, fokus va reja\n"
        "• MindSpace — ruhiy muvozanat va qo'llab-quvvatlash",
        reply_markup=menu_keyboard,
    )


@dp.message(F.text.in_(MODES.keys()))
async def select_mode(message: Message):
    if message.from_user and message.text:
        user_modes[message.from_user.id] = message.text
    await message.answer(
        f"{message.text} bo'limi tanlandi. Savolingizni yoki vazifangizni yozing."
    )


@dp.message()
async def handle_question(message: Message):
    if not message.text:
        return

    if client is None:
        await message.answer(
            "Bot menyusi ishlayapti, lekin hozircha GEMINI_API_KEY kiritilmagan. "
            "Kalitni qo'shganingizdan so'ng AI savollarga javob bera boshlaydi."
        )
        return

    user_id = message.from_user.id if message.from_user else 0
    current_mode = user_modes.get(user_id, "🎯 CareerMatch")
    system_instruction = MODES[current_mode]

    try:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except Exception:
        pass

    try:
        reply_text = await ask_gemini_with_fallback(message.text, system_instruction)
    except Exception as e:
        logging.exception("Gemini API yakuniy xatosi: %s", e)
        err_text = str(e)
        if "401" in err_text or "UNAUTHENTICATED" in err_text or "API key not valid" in err_text:
            reply_text = (
                "GEMINI_API_KEY noto'g'ri yoki yaroqsiz. Render muhit o'zgaruvchilarini tekshiring."
            )
        else:
            reply_text = (
                "Hozircha AI modelida vaqtincha yuqori yuklama kuzatilyapti. "
                "Bir necha soniyadan so'ng qayta urinib ko'ring."
            )

    try:
        await send_safe_text(message, reply_text)
    except Exception as e:
        logging.exception("Telegramga javob yuborishda xato: %s", e)


async def main():
    await start_http_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
  

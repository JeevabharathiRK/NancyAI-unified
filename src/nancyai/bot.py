import asyncio
import logging
import sys
from os import getenv
from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.dev", override=True)

from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatType
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton
)

from .chatbot import get_ai_generator
from .movie import MovieExtractor

TOKEN = getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN not set. Add it to .env or .env.dev.")

GROQ_API_KEY = getenv("GROQ_API_KEY")
OMDB_API_KEY = getenv("OMDB_API_KEY")

dp = Dispatcher()

_ai = None
_movie_extractor = None

BOT_USERNAME = None
PENDING_LINK_MEDIA = {}
MOVIE_META = {}  # copied_message_id -> meta dict


def ai():
    global _ai
    if _ai is None:
        try:
            _ai = get_ai_generator()
            logging.info("AI generator initialized.")
        except Exception as e:
            logging.exception("AI init failed: %s", e)
            _ai = None
    return _ai


def movie_extractor():
    global _movie_extractor
    if _movie_extractor is None:
        if not (GROQ_API_KEY and OMDB_API_KEY):
            logging.warning("Movie extractor disabled (missing GROQ_API_KEY or OMDB_API_KEY).")
            return None
        try:
            _movie_extractor = MovieExtractor(groq_api_key=GROQ_API_KEY, omdb_api_key=OMDB_API_KEY)
            logging.info("MovieExtractor initialized.")
        except Exception as e:
            logging.exception("MovieExtractor init failed: %s", e)
            _movie_extractor = None
    return _movie_extractor


def _format_duration(runtime_str):
    if not runtime_str or "min" not in runtime_str:
        return None
    try:
        minutes = int(runtime_str.replace(" min", ""))
        if minutes <= 0:
            return None
        hours = minutes // 60
        mins = minutes % 60
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if mins > 0:
            parts.append(f"{mins}m")
        return " ".join(parts)
    except (ValueError, TypeError):
        return runtime_str


def _format_movie_details(d):
    if not d:
        return None

    lines = ["<b>Nancy Generated ↓</b>"]
    
    quote_lines = []

    title_line = d.get("Title")
    if title_line:
        year = d.get("Year")
        full_title = f"{title_line} ({year})" if year else title_line
        quote_lines.append(f"🎥 <b>Title : {html.quote(full_title)}</b>")

    runtime = _format_duration(d.get("Runtime"))
    if runtime:
        quote_lines.append(f"⌚️ <b>Duration :</b> {html.quote(runtime)}")

    genre = d.get("Genre")
    if genre:
        quote_lines.append(f"🎻 <b>Genre :</b> {html.quote(genre)}")

    rated = d.get("Rated")
    if rated and rated != "N/A":
        cert = rated
        if "13" in rated:
            cert += " ⑬"
        elif "16" in rated or "17" in rated or "R" in rated:
            cert += " 🔞"
        quote_lines.append(f"📝 <b>Certificate :</b> {html.quote(cert)}")

    director = d.get("Director")
    if director:
        quote_lines.append(f"🎬 <b>Director :</b> {html.quote(director)}")

    actors = d.get("Actors")
    if actors:
        quote_lines.append(f"👨🏻‍🎤 <b>Actors :</b> {html.quote(actors)}")

    plot = d.get("Plot")
    if plot:
        quote_lines.append(f"🧨 <b>Plot :</b> {html.quote(plot)}")

    imdb_rating = d.get("imdbRating")
    if imdb_rating and imdb_rating != "N/A":
        quote_lines.append(f"⭐️ <b>IMDB :</b> {html.quote(imdb_rating)} / 10")

    if quote_lines:
        lines.append(f"<blockquote>{'\n'.join(quote_lines)}</blockquote>")
    
    return "\n".join(lines) if len(lines) > 1 else None


@dp.message(CommandStart())
async def command_start_handler(message: Message):
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}! Send media or text.")


@dp.message(Command("clear"))
async def clear_conversation_handler(message: Message):
    generator = ai()
    if not generator:
        await message.reply("AI not ready.")
        return
    generator.clear_history(user_id=message.from_user.id)
    await message.reply("Conversation memory cleared.")


@dp.message(Command("status"))
async def conversation_status_handler(message: Message):
    generator = ai()
    if not generator:
        await message.reply("AI not ready.")
        return
    count = generator.history_length(user_id=message.from_user.id)
    await message.reply(f"Messages in Memory: {count} of 15")


@dp.message()
async def message_handler(message: Message):
    # Ignore stickers
    if message.sticker:
        return

    is_media = any([
        message.photo,
        message.video,
        message.document,
        getattr(message, "audio", None),
        getattr(message, "voice", None),
        getattr(message, "animation", None),
        getattr(message, "video_note", None),
    ])

    if is_media:
        original_caption = message.caption or ""
        # Determine filename
        filename = None
        if message.document:
            filename = message.document.file_name
        elif getattr(message, "video", None):
            filename = getattr(message.video, "file_name", None) or "video"
        elif message.animation:
            filename = message.animation.file_name
        elif message.audio:
            filename = message.audio.file_name
        else:
            filename = "media"

        logging.debug("Processing media filename=%s caption=%s", filename, original_caption)

        extractor = movie_extractor()
        details = None
        if extractor:
            try:
                loop = asyncio.get_running_loop()
                details = await loop.run_in_executor(
                    None,
                    extractor.process,
                    filename,
                    original_caption
                )
                logging.debug("Movie details (possibly fallback)=%s", details)
            except Exception:
                logging.exception("Movie extraction failed")

        formatted = _format_movie_details(details)
        if formatted:
            new_caption = formatted
            if original_caption.strip():
                new_caption += f"\n\n<b>Original Caption ↓</b>\n💬 {html.quote(original_caption.strip())}"
        else:
            new_caption = html.quote(original_caption.strip()) if original_caption.strip() else "Media"

        # Force change even if identical (append zero-width char if same)
        if new_caption.strip() == (original_caption or "").strip():
            new_caption += "\u200B"

        if len(new_caption) > 1020:
            new_caption = new_caption[:1017] + "..."

        link_button_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="/Link@SadieSink", callback_data="ask_link")]
            ]
        )

        try:
            copied = await message.bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                caption=new_caption,
                reply_markup=link_button_kb
            )
            MOVIE_META[copied.message_id] = {
                "details": details,
                "original_caption": original_caption,
                "filename": filename
            }
            logging.info("Media resent with new caption (message_id=%s).", copied.message_id)
        except Exception:
            logging.exception("Failed to copy media message")
            await message.reply("Could not process media.")
            return

        try:
            await message.delete()
        except Exception as e:
            logging.debug("Delete original failed: %s", e)
        return

    # Text message handling
    if not message.text:
        return

    txt = message.text.strip()
    if txt.startswith('/'):
        return

    generator = ai()
    if not generator:
        await message.reply("AI not ready.")
        return

    try:
        reply = await asyncio.get_running_loop().run_in_executor(
            None, generator.generate, message.from_user.id, txt
        )
        await message.reply(reply)
    except Exception:
        logging.exception("AI generation failed")
        await message.reply("Error generating reply.")


@dp.callback_query(F.data == "ask_link")
async def handle_ask_link(callback: CallbackQuery):
    meta = MOVIE_META.get(callback.message.message_id)
    caption = callback.message.caption or ""
    enhancement_tag = "Tap /link@SadieStreamBot"
    if enhancement_tag not in caption:
        note = f"\n\n🔗 {enhancement_tag} to request a link."
        if len(caption) + len(note) <= 1024:
            caption += note
        else:
            space_left = 1024 - len(note)
            if space_left > 0:
                caption = caption[:space_left - 3] + "..." + note

    kb = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True,
        keyboard=[[KeyboardButton(text="/link@SadieStreamBot")]],
        input_field_placeholder="Tap /link@SadieStreamBot"
    )
    key = (callback.message.chat.id, callback.from_user.id)

    old_id = PENDING_LINK_MEDIA.get(key)
    if old_id:
        try:
            await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=old_id)
        except Exception as e:
            logging.exception("Failed to delete previous pending link media: %s", e)
            pass

    try:
        copied = await callback.bot.copy_message(
            chat_id=callback.message.chat.id,
            from_chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=kb,
            caption=""
        )
        PENDING_LINK_MEDIA[key] = copied.message_id
        if meta:
            MOVIE_META[copied.message_id] = meta
    except Exception as e:
        logging.warning("Failed to resend media with keyboard: %s", e)

    await callback.answer()


async def main_async():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(main_async())
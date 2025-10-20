import asyncio
import logging
import sys
import random  # added
from os import getenv
from logging.handlers import RotatingFileHandler  # added
from dotenv import load_dotenv
from pathlib import Path  # added

load_dotenv()
load_dotenv(".env.dev", override=True)

from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatType
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
)
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from .chatbot import get_ai_generator
from .movie import MovieExtractor

TOKEN = getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN not set. Add it to .env or .env.dev.")

GROQ_API_KEY = getenv("GROQ_API_KEY")
OMDB_API_KEY = getenv("OMDB_API_KEY")
MOVIE_AI_MODEL = getenv("MOVIE_AI_MODEL")
LOG_CHANNEL_ID = getenv("LOG_CHANNEL_ID")
WEBHOOK_HOST = getenv("WEBHOOK_HOST", "")
if WEBHOOK_HOST and WEBHOOK_HOST.endswith('/'):
    WEBHOOK_HOST = WEBHOOK_HOST[:-1]
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBHOOK_REMOVABLE = getenv("WEBHOOK_REMOVABLE", "false").lower() in ("1", "true", "yes", "y")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

_ai = None
_movie_extractor = None

BOT_USERNAME = None
PENDING_LINK_MEDIA = {}
MOVIE_META = {}


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
            _movie_extractor = MovieExtractor(groq_api_key=GROQ_API_KEY, omdb_api_key=OMDB_API_KEY, model=MOVIE_AI_MODEL)
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


def _format_movie_details(d, heading='Nancy Generated ↓'):
    if not d:
        return None
    lines = [f'<b>{heading}</b>']
    
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


def _format_metadata_details(meta, heading='Filename + Caption Metadata ↓'):
    """
    Format secondary extracted technical metadata similarly to movie details.
    Expects keys: Size, Duration, Audio, Quality, HD, Subtitles, Video, AudioDetails
    """
    if not meta or not isinstance(meta, dict):
        return None

    order = [
        ("Size", "💾", "Size"),
        ("Duration", "⌚️", "Duration"),
        ("Audio", "🔊", "Audio"),
        ("Quality", "🎞", "Quality"),
        ("HD", "🟩", "HD"),
        ("Subtitles", "💬", "Subtitles"),
        ("Video", "🎬", "Video"),
        ("AudioDetails", "🎧", "Audio Details"),
    ]
    lines = [f"<b>{heading}</b>"]
    quote_lines = []
    for key, emoji, label in order:
        val = meta.get(key)
        if val in (None, "", "null", "None"):
            continue
        # Normalize booleans for HD
        if key == "HD":
            if isinstance(val, bool):
                val = "Yes" if val else "No"
            elif str(val).lower() in ("yes", "true", "1", "y"):
                val = "Yes"
            elif str(val).lower() in ("no", "false", "0", "n"):
                val = "No"
        quote_lines.append(f"{emoji} <b>{label} :</b> {html.quote(str(val))}")

    if not quote_lines:
        return None
    lines.append(f"<blockquote>{'\n'.join(quote_lines)}</blockquote>")
    return "\n".join(lines)


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

@dp.message(Command("log"))
async def log_command_handler(message: Message):
    await message.reply(f"Log Link: {WEBHOOK_HOST}/")

@dp.message(Command("help"))
async def help_command_handler(message: Message):
    await message.reply("Available commands: /start, /clear, /status, /log, /help")

@dp.message()
async def message_handler(message: Message):
    if message.sticker and not (message.from_user and message.from_user.is_bot):
        set_name = message.sticker.set_name
        if not set_name:
            try:
                await message.answer_sticker(message.sticker.file_id)
            except Exception as e:
                logging.debug("Failed to echo sticker without set: %s", e)
        else:
            try:
                sticker_set = await message.bot.get_sticker_set(set_name)
                candidates = [s for s in sticker_set.stickers if s.file_id != message.sticker.file_id] or sticker_set.stickers
                choice = random.choice(candidates)
                await message.answer_sticker(choice.file_id)
            except Exception:
                logging.exception("Failed to fetch/send random sticker")
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
                logging.debug("Movie details (primary)=%s", details)
            except Exception:
                logging.exception("Movie extraction failed (primary)")

        formatted = _format_movie_details(details)
        if formatted:
            new_caption = formatted

            # Secondary metadata extraction using extract_movie_metadata on filename + caption
            metadata_formatted = None
            if extractor:
                try:
                    combo_text = f"{filename or ''} {original_caption}".strip()
                    if combo_text:
                        loop = asyncio.get_running_loop()
                        raw_meta = await loop.run_in_executor(
                            None,
                            extractor.extract_movie_metadata,
                            combo_text
                        )

                        # If primary runtime available, override Duration
                        if raw_meta and details and details.get("Runtime"):
                            runtime_human = _format_duration(details.get("Runtime"))
                            if runtime_human:
                                raw_meta["Duration"] = runtime_human

                        metadata_formatted = _format_metadata_details(
                            raw_meta,
                            heading='Metadata:'
                        )
                except Exception:
                    logging.exception("Metadata extraction failed (secondary)")
                    metadata_formatted = None

            if metadata_formatted:
                new_caption += f"\n\n{metadata_formatted}"
            else:
                # Fallback only if no metadata and there was an original caption
                if original_caption.strip():
                    new_caption += f"\n\n<b>Original Caption ↓</b>\n💬 {html.quote(original_caption.strip())}"
        else:
            # No primary movie details; still try metadata before final fallback
            extractor = movie_extractor()
            metadata_formatted = None
            if extractor:
                try:
                    combo_text = f"{filename or ''} {original_caption}".strip()
                    if combo_text:
                        loop = asyncio.get_running_loop()
                        raw_meta = await loop.run_in_executor(
                            None,
                            extractor.extract_movie_metadata,
                            combo_text
                        )
                        metadata_formatted = _format_metadata_details(
                            raw_meta,
                            heading='Metadata:'
                        )
                except Exception:
                    logging.exception("Metadata extraction failed (only pass)")

            if metadata_formatted:
                new_caption = metadata_formatted
            else:
                new_caption = html.quote(original_caption.strip()) if original_caption.strip() else "Media"

        try:
            if message.from_user:
                if message.from_user.username:
                    sender_link = f"https://t.me/{message.from_user.username}"
                    sender_display = f"@{message.from_user.username}"
                else:
                    sender_link = f"tg://user?id={message.from_user.id}"
                    sender_display = message.from_user.full_name or "User"
                sender_segment = f'Sent by: <a href="{sender_link}">{html.quote(sender_display)}</a> | ⚡Powered by: <a href="https://t.me/Nancy_MetaAI_Bot">Nancy</a>'
                if sender_segment not in new_caption:
                    addition = f"\n\n{sender_segment}"
                    if len(new_caption) + len(addition) <= 1024:
                        new_caption += addition
        except Exception:
            logging.debug("Failed to append sender hyperlink", exc_info=True)

        if new_caption.strip() == (original_caption or "").strip():
            new_caption += "\u200B"

        if len(new_caption) > 1020: 
            new_caption = new_caption[:1017] + "..."

        try:
            copied = await message.bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                caption=new_caption,
                reply_markup=None
            )
            MOVIE_META[copied.message_id] = {
                "details": details,
                "original_caption": original_caption,
                "filename": filename
            }
            logging.info("Media resent with hyperlink caption (message_id=%s).", copied.message_id)
        except Exception:
            logging.exception("Failed to copy media message")
            await message.reply("Could not process media.")
            return
        try:
            if LOG_CHANNEL_ID:
                dest = LOG_CHANNEL_ID.strip()
                try:
                    if not dest.startswith("@"):
                        dest = int(dest)
                except Exception:
                    logging.error("Invalid LOG_CHANNEL_ID: %s", LOG_CHANNEL_ID)
                poster_url = None
                if details:
                    poster_url = details.get("Poster")
                if poster_url and poster_url != "N/A":
                    log_caption = f"Start: {poster_url}"
                else:
                    log_caption = None

                await message.bot.copy_message(
                    chat_id=dest,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                    caption=log_caption,
                    reply_markup=None
                )
                logging.info("Media also copied to log channel.")
            else:
                logging.debug("LOG_CHANNEL_ID not set; skipping log copy.")
        except Exception:
            logging.exception("Failed to copy media to log channel")

        try:
            await message.delete()
        except Exception as e:
            logging.debug("Delete original failed: %s", e)
        return

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
        user_name = message.from_user.full_name or message.from_user.first_name or ""
        reply = await generator.generate_reply(message.from_user.id, user_name, txt)
        await message.reply(reply)
    except Exception:
        logging.exception("AI generation failed")
        await message.reply("Error generating reply.")

# --- Webhook Setup ---
async def on_startup(app: web.Application):
    # Set webhook when starting
    try:
        await bot.delete_webhook()
    except Exception:
        logging.debug("Failed to delete existing webhook (may not exist).")
    try:
        await asyncio.sleep(1)  # brief pause to ensure deletion
        await bot.get_webhook_info()  # just to log current info
    except Exception:
        logging.debug("Failed to get webhook info (may not exist).")
    logging.info("Setting webhook to %s", WEBHOOK_URL)
    await bot.set_webhook(WEBHOOK_URL)


async def on_shutdown(app: web.Application):
    # Remove webhook when shutting down
    logging.info("Shutting down")
    if WEBHOOK_REMOVABLE:
        logging.info("Deleting webhook")
        await bot.delete_webhook()

# added: serve log file at "/"
async def view_log(request: web.Request):
    log_path = getenv("BOT_LOG_FILE", "bot.log")
    try:
        p = Path(log_path)
        if not p.exists():
            return web.Response(
                text="Log file not found.",
                status=404,
                content_type="text/plain",
                charset="utf-8",
            )
        return web.FileResponse(
            path=str(p),
            headers={
                "Cache-Control": "no-cache",
                "Content-Type": "text/plain; charset=utf-8",
            },
        )
    except Exception:
        logging.exception("Failed to serve log file")
        return web.Response(
            text="Error loading log.",
            status=500,
            content_type="text/plain",
            charset="utf-8",
        )

def main():

    # Setup logging
    log_file = getenv("BOT_LOG_FILE", "bot.log")
    log_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))

    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[console_handler, file_handler]
    )
    logging.info("Logging initialized. Console=INFO, File=DEBUG, file=%s", log_file)

    # Start bot
    app = web.Application()

    # Register webhook handler
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)

    # added: root path shows the log
    app.router.add_get("/", view_log)

    # Setup startup and shutdown
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Run aiohttp app
    setup_application(app, dp, bot=bot)
    logging.info("Bot started with webhook at %s", WEBHOOK_URL)
    web.run_app(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()

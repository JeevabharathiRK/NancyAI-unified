from os import getenv
from dotenv import load_dotenv

# Load both .env and optional .env.dev (dev overrides)
load_dotenv()
load_dotenv(".env.dev", override=True)

import sys
import asyncio
import logging
import random

from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatType
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)

from .chatbot import get_ai_generator

TOKEN = getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN not set. Add it to .env or .env.dev.")

dp = Dispatcher()

_ai = None
BOT_USERNAME = None  # cached lowercase bot username
PENDING_LINK_MEDIA = {}  # key: (chat_id, user_id) -> message_id of resent media with one-time keyboard

def ai():
    global _ai
    if _ai is None:
        try:
            _ai = get_ai_generator()
        except Exception as e:
            logging.error("AI init failed: %s", e)
            return None
    return _ai

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}! I'm Nancy. Send text to chat with AI.")

@dp.message(Command("clear"))
async def clear_conversation_handler(message: Message) -> None:
    generator = ai()
    if not generator:
        await message.reply("AI not ready (missing GROQ_API_KEY).")
        return
    generator.clear_history(user_id=message.from_user.id)
    await message.reply("Conversation memory cleared.")

@dp.message(Command("status"))
async def conversation_status_handler(message: Message) -> None:
    generator = ai()
    if not generator:
        await message.reply("AI not ready.")
        return
    count = generator.history_length(user_id=message.from_user.id)
    await message.reply(f"Messages in Memory: {count} of 15")

@dp.message()
async def message_handler(message: Message) -> None:
    # Stickers
    if message.sticker:
        try:
            if message.sticker.set_name:
                st_set = await message.bot.get_sticker_set(message.sticker.set_name)
                choice = random.choice(st_set.stickers)
                await message.reply_sticker(choice.file_id)
            else:
                await message.reply_sticker(message.sticker.file_id)
        except Exception:
            await message.reply_sticker(message.sticker.file_id)
        return

    # Media types
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
        prefix = "Nancy"
        if original_caption.startswith(prefix):
            new_caption = original_caption
        else:
            new_caption = f"{prefix} {original_caption}".strip()

        link_button_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Call Sadie Sink", callback_data="ask_link")]
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
        except Exception:
            logging.exception("Failed to copy media message")
            await message.reply("Could not process media.")
            return

        # Delete original in groups if allowed
        if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            try:
                bot_user = await message.bot.get_me()
                member = await message.bot.get_chat_member(message.chat.id, bot_user.id)
                if getattr(member, "can_delete_messages", False):
                    await message.delete()
            except Exception as e:
                logging.debug("Delete original failed: %s", e)

        return

    # Non-text unsupported
    if not message.text:
        await message.reply("Unsupported message type.")
        return

    # Ignore commands to other bots (and handle Sadie cleanup)
    txt = message.text.strip()
    if txt.startswith('/'):
        first_token = txt.split()[0]
        if '@' in first_token:
            _, _, target_username = first_token.partition('@')
            if target_username:
                global BOT_USERNAME
                if BOT_USERNAME is None:
                    me = await message.bot.get_me()
                    BOT_USERNAME = (me.username or "").lower()
                if target_username.lower() != BOT_USERNAME:
                    # If user sent Sadie command, delete the temporary media message with keyboard (if any)
                    if target_username.lower() == "sadiestreambot":
                        key = (message.chat.id, message.from_user.id)
                        pending_id = PENDING_LINK_MEDIA.pop(key, None)
                        if pending_id:
                            try:
                                await message.bot.delete_message(chat_id=message.chat.id, message_id=pending_id)
                            except Exception:
                                pass
                        # No extra reply; one_time_keyboard should hide automatically after user sends command
                    return

    generator = ai()
    if not generator:
        await message.reply("AI not ready. Set API_KEY.")
        return
    try:
        reply = await generator.generate_reply(
            user_id=message.from_user.id,
            user_name=message.from_user.full_name,
            text=message.text
        )
        await message.reply(reply)
    except Exception:
        logging.exception("AI generate error")
        await message.reply("AI error. Check API_KEY or logs.")

@dp.callback_query(F.data == "ask_link")
async def handle_ask_link(callback: CallbackQuery):
    # Re-send (copy) the media message but this time with a one-time reply keyboard
    kb = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True,
        keyboard=[[KeyboardButton(text="/link@SadieStreamBot")]],
        input_field_placeholder="Tap /link@SadieStreamBot"
    )
    key = (callback.message.chat.id, callback.from_user.id)

    # Clean any previous pending one
    old_id = PENDING_LINK_MEDIA.pop(key, None)
    if old_id:
        try:
            await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=old_id)
        except Exception:
            pass

    try:
        copied = await callback.bot.copy_message(
            chat_id=callback.message.chat.id,
            from_chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=kb,
            caption=callback.message.caption  # preserve caption
        )
        # copy_message returns a MessageId object; store its message_id
        PENDING_LINK_MEDIA[key] = copied.message_id
    except Exception as e:
        logging.warning("Failed to resend media with keyboard: %s", e)

    # Silent (or minimal) callback answer
    await callback.answer()

async def main_async():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main_async())
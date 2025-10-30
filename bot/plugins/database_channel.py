from pyrogram import Client, filters
from bot import DATABASE_CHANNEL, bot
from bot.database.db_file_handler import save_file
from pyrogram.handlers import MessageHandler
from pyrogram.filters import chat, document, video, audio
from bot.helper.telegram_helper.message_utils import process_channel

media_filter = document | video | audio


#@Client.on_message(filters.chat(DATABASE_CHANNEL) & media_filter)
async def media(bot, message):
    """Media Handler"""
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media is not None:
            break
    else:
        return

    media.file_type = file_type
    media.caption = message.caption
    await save_file(message)

DATABASE_CHANNEL = DATABASE_CHANNEL.split()
DATABASE_CHANNEL = process_channel(DATABASE_CHANNEL)

bot.add_handler(MessageHandler(media, filters= chat(DATABASE_CHANNEL) & media_filter))

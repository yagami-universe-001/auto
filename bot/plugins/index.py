import asyncio
import logging
import os
import time

from pyrogram import Client
from pyrogram.types import CallbackQuery, Message
from pymongo.errors import DuplicateKeyError
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.filters import *
from pyrogram.errors import MessageNotModified, ChannelPrivate
from datetime import timedelta, datetime

from bot import OWNER_ID, bot, LOGGER as logger, CMD_SUFFIX, config_dict, is_indexing_active, skip_iron_ids
from bot.database.db_file_handler import save_file
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.extra.bot_utils import new_task, check_last_msg_id_bot, chnl_check
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import send_message, delete_message, edit_message



# Define MIME types for media files
video_mime_types = [
    "video/x-matroska", "video/mp4", "video/avi", "video/mpeg", "video/webm",
    "video/quicktime", "video/flv", "video/x-flv", "video/3gpp", "video/x-msvideo", "video/mkv"
]

audio_mime_types = [
    "audio/mp3", "audio/wav", "audio/ogg", "audio/mp4", "audio/midi", "audio/x-m4a",
    "audio/x-wav", "audio/flac", "audio/aac", "audio/amr", "audio/vnd.rn-realaudio",
]

document_mime_types = [
    "audio/mp3", "audio/wav", "audio/ogg", "audio/mp4", "audio/midi", "audio/x-m4a",
    "audio/x-wav", "audio/flac", "audio/aac", "audio/amr", "audio/vnd.rn-realaudio",
    "video/x-matroska", "video/mp4", "video/avi", "video/mpeg", "video/webm",
    "video/quicktime", "video/flv", "video/x-flv", "video/3gpp", "video/x-msvideo", "video/mkv",
    "application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint", "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/zip", "application/x-rar-compressed", "application/x-tar"
]



async def get_index_button(client, message):
    button_maker = ButtonMaker()
    button_maker.add_button("📥ɪɴᴅᴇx ꜰɪʟᴇꜱ📥", callback_data="index_file")
    button_maker.add_button("📋ɪɴᴅᴇx ᴡɪᴛʜ ꜱᴋɪᴘᴘᴇᴅ ꜰɪʟᴇꜱ", callback_data="index_skipped_file")
    button_maker.add_button("❌ᴄᴀɴᴄʟᴇ❌", callback_data="index_cancle")
    await message.reply(
        text="What do you want?",
        reply_markup=button_maker.build(),
        quote=True
    )

@new_task
async def index_file_handler(client, query: CallbackQuery):
    message = query.message
    data = query.data
    button_maker = ButtonMaker()


    if data == "index_file":
        # Create callback button
        button_maker.add_button("✅Yes✅", callback_data="index_yes")
        # Add rows of callback data buttons
        button_maker.add_row([("☢️Stop☢️", "index_stop"), ("❌Close❌", "close_data")])
        
        await edit_message(
            message,
            text="Are you sure you want to index files?\n\nNote: I am assuming this is your channel's last file. If this file is not the last file, then files after this will not be indexed.",
            buttons=button_maker.build()
        )
    elif data == 'index_skipped_file':
        # Create callback button
        button_maker.add_button("✅Yes ᴡɪᴛʜ ꜱᴋɪᴘᴘᴇᴅ ꜰɪʟᴇꜱ✅", callback_data="index_skipped_yes")
        # Add rows of callback data buttons
        button_maker.add_row([("☢️Stop☢️", "index_stop"), ("❌Close❌", "close_data")])
        
        await edit_message(
            message,
            text="Are you sure you want to index files with Skipped files?\n\nNote: I am assuming this is your channel's last file. If this file is not the last file, then files after this will not be indexed.\n\nMake sure you added skipped files ids",
            buttons=button_maker.build()
        )
    elif data == 'index_skipped_yes':
        button_maker.add_row([("✅Up to Down Index", "index_skip_utd"), ("✅Down to Up Index", "index_skip_dtu")])
        button_maker.add_button("Skip", callback_data="index_defult_skip_yes")
        # Add rows of callback data buttons
        button_maker.add_row([("☢️Stop☢️", "index_skipped_file"), ("❌Close❌", "close_data")])
        
        await edit_message(
            message,
            text="Please select which type index do you want. Defult is up to down. if don't understand then just skip button",
            buttons=button_maker.build()
        )
        
    elif data == "index_yes":
        button_maker.add_row([("✅Up to Down Index", "index_utd"), ("✅Down to Up Index", "index_dtu")])
        button_maker.add_button("Skip", callback_data="index_defult_yes")
        # Add rows of callback data buttons
        button_maker.add_row([("☢️Stop☢️", "index_file"), ("❌Close❌", "close_data")])
        
        await edit_message(
            message,
            text="Please select which type index do you want. Defult is up to down. if don't understand then just skip button",
            buttons=button_maker.build()
        )
    elif data == "index_dtu":
        await start_indexing_file(client, query, formate="dtu")
    elif data == "index_utd" or data == "index_defult_yes":
        await start_indexing_file(client, query, formate="utd")
    elif data == "index_defult_skip_yes" or data == "index_skip_utd":
        if query.message.reply_to_message.forward_from_chat:
            iron_id = query.message.reply_to_message.forward_from_chat.id
            iron_msg = skip_iron_ids.get(iron_id, None)
            if not iron_msg:
                await query.answer("you still not added skip ids for this channel files.\n\nPlease kindly add first skip ids", show_alert=True)
                await asyncio.sleep(1)
                m = await client.send_message(query.from_user.id, f'Please use /setskip{CMD_SUFFIX} command to add skip ids')
                await asyncio.sleep(10)
                await delete_message(m)
                return
            else:
                await start_indexing_file(client, query, skip_files=True, formate="utd")
    elif data == "index_skip_dtu":
        if query.message.reply_to_message.forward_from_chat:
            iron_id = query.message.reply_to_message.forward_from_chat.id
            iron_msg = skip_iron_ids.get(iron_id, None)
            if not iron_msg:
                await query.answer("you still not added skip ids for this channel files.\n\nPlease kindly add first skip ids", show_alert=True)
                await asyncio.sleep(1)
                m = await client.send_message(query.from_user.id, f'Please use /setskip{CMD_SUFFIX} command to add skip ids')
                await asyncio.sleep(10)
                await delete_message(m)
                return
            else:
                await start_indexing_file(client, query, skip_files=True, formate="dtu")

    elif data == "index_cancle":
        # Cancel the indexing process
        await cancel_indexing(client, query)
    elif data == "index_stop":
        button_maker.callback("📥ɪɴᴅᴇx ꜰɪʟᴇꜱ📥", "index_file")
        button_maker.callback("📋ɪɴᴅᴇx ᴡɪᴛʜ ꜱᴋɪᴘᴘᴇᴅ ꜰɪʟᴇꜱ", callback_data="index_skipped_file")
        button_maker.callback("❌ᴄᴀɴᴄʟᴇ❌", "index_cancle")

        await edit_message(
            message,
            text="What do you want?",
            buttons=button_maker.column()
        )
    else:
        b = await message.reply("You don't rights to indexing files")
        await asyncio.sleep(10)
        await delete_message(b)

@new_task
async def start_indexing_file(client, query, skip_files=False, formate="utd"):
    """
    Start indexing files from a forwarded message in a channel.
    """
    global is_indexing_active
    if is_indexing_active:
        return await query.answer("Wait for complete running indexing.", show_alert=True)
    
    if query.message.reply_to_message and query.message.reply_to_message.forward_from_chat:
        channel_id = query.message.reply_to_message.forward_from_chat.id
        if channel_id:
            try:
                iron_check = await chnl_check(channel_id=channel_id)
               
                iron = iron_check[str(channel_id)]
                
                if iron:
                    pass  # Channel is valid; proceed with your logic
                else:
                    return await query.answer(
                        "I am not able to connect to the channel. Make sure I am an admin in the channel.",
                        show_alert=True
                    )
            except Exception as e:
                return await query.answer(
                    f"An error occurred while checking the channel: {e}",
                    show_alert=True
                )
        else:
            return await query.answer("This is not channel message", show_alert=True)

    data_chnl_id = query.message.reply_to_message.forward_from_chat.id
    last_msg_id = query.message.reply_to_message.forward_from_message_id if query.message.reply_to_message else query.message.forward_from_message_id
    if last_msg_id:
        verify_msg_id = await check_last_msg_id_bot(last_msg_id, data_chnl_id)
    if verify_msg_id:
        # Change the message text to status update and show the cancel button
        await update_status_message(client, query, "Starting indexing...", cancel=True)
        # Start indexing files from last_msg_id
        if skip_files:
            if formate == "dtu":
                await index_channel_files(client, data_chnl_id, last_msg_id, query, skip_files=True, formate=True)
            elif formate == "utd":
                await index_channel_files(client, data_chnl_id, last_msg_id, query, skip_files=True, formate=False)
        else:
            if formate == "dtu":
                await index_channel_files(client, data_chnl_id, last_msg_id, query, formate=True)
            elif formate == "utd":
                await index_channel_files(client, data_chnl_id, last_msg_id, query, formate=False)

    else: 
        await query.answer('This is not last message of channel', show_alert=True)

@new_task
async def index_channel_files(client, channel_id, last_msg_id, query, skip_files=False, formate=False):
    """
    Index files in a channel from message ID 1 to last_msg_id using Pyrogram.
    """
    global is_indexing_active, skip_iron_ids
    total_messages = 0
    files_fetched = 0
    files_saved = 0
    duplicate_files = 0
    unsupported_files = 0
    no_media_files = 0
    # Determine the batch size
    batch_size = 200
    start_time = time.time()

    skip_ids = set()  # Use a set for faster lookups
    if skip_files:
        skip_ids = set(skip_iron_ids.get(channel_id, []))  # Convert to set

    try:
        if formate:
            # Indexing from last_msg_id down to up
            offset_id = last_msg_id
            is_indexing_active = True
            while is_indexing_active and offset_id >= 0:
                # Skip if the current offset_id is in skip_ids
                if offset_id in skip_ids:
                    offset_id -= 1
                    continue

                # Create a list of message IDs for the current batch
                message_ids = list(range(offset_id, max(0, offset_id - batch_size), -1))
                
                if skip_ids:
                    # Remove message_ids that are in skip_ids
                    message_ids = [msg_id for msg_id in message_ids if msg_id not in skip_ids]

                # If message_ids is empty, adjust the offset and continue
                if not message_ids or 0 in message_ids:
                    offset_id -= 1  # Move to the next message ID
                    continue
                
                try:
                    # Fetch messages from the channel
                    messages = await client.get_messages(chat_id=channel_id, message_ids=message_ids)
    
                except Exception as e:
                    await edit_message(query.message, f"Indexe error to get message: {e} ")
                    is_indexing_active = False
                    logger.warning("Index Process Cancled due to get messsage")
                    return
                except ChannelPrivate as c:
                    await edit_message(query.message, f"Channel is private i am not able to get message\n\nMake sure i am admin in channel")
                    logger.warning(f"index stop Channel is private: {c}")
                    is_indexing_active = False
                    return

                if not messages:
                    break  # No more messages to process

                for msg in messages:  # Reverse to maintain the order from last to first
                    if not is_indexing_active:
                        break  # Stop if the process is cancelled

                    if not msg.media:
                        # Skip messages without media
                        total_messages += 1
                        no_media_files += 1
                        continue

                    # Check for supported media types and extract file size
                    media_type = None
                    file_size = 0

                    if msg.video and msg.video.mime_type in video_mime_types:
                        media_type = 'video'
                        file_size = msg.video.file_size
                        total_messages += 1
                        files_fetched += 1
                    elif msg.audio and msg.audio.mime_type in audio_mime_types:
                        media_type = 'audio'
                        file_size = msg.audio.file_size
                        total_messages += 1
                        files_fetched += 1
                    elif msg.document and msg.document.mime_type in document_mime_types:
                        media_type = 'document'
                        file_size = msg.document.file_size
                        total_messages += 1
                        files_fetched += 1

                    if media_type:
                        # Save valid files
                        try:
                            saved, iron = await save_file(msg)
                            if saved:
                                files_saved += 1
                            elif iron == 0:
                                duplicate_files += 1
                                continue
                            elif iron == 2:
                                unsupported_files += 1
                                continue
                        except Exception as e:
                            logger.error(f"Error saving file: {e}")
                            unsupported_files += 1
                            continue
                    try:
                        # Update the status monitor every 10 files
                        if total_messages % 50 == 0:
                            elapsed_time = str(timedelta(seconds=int(time.time() - start_time)))
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            status_message = (
                                f"📚Total Messages: {total_messages}\n"
                                f"📋Files Fetched: {files_fetched} files\n"
                                f"🗂️Saved: {files_saved} files\n"
                                f"📑Duplicates: {duplicate_files} files\n"
                                f"📭No media: {no_media_files} messages\n"
                                f"💣Unsupported: {unsupported_files} files\n"
                                f"⏳Running Time: {elapsed_time}\n"
                                f"🕒Current DateTime: {current_time}"
                            )
                            await update_status_message(client, query, status_message, True)
                    except MessageNotModified as e:
                        logger.error(f"Error While updating index status message: {e}")

                # Update offset for the next batch
                offset_id -= batch_size

        else:
            # Indexing from 0 up to last_msg_id
            offset_id = 0
            is_indexing_active = True
            while is_indexing_active and offset_id <= last_msg_id:
                # Skip if the current offset_id is in skip_ids
                if offset_id in skip_ids:
                    offset_id += 1
                    continue

                # Create a list of message IDs for the current batch
                message_ids = list(range(offset_id, min(offset_id + batch_size, last_msg_id + 1)))


                if skip_ids:
                    # Remove message_ids that are in skip_ids
                    message_ids = [msg_id for msg_id in message_ids if msg_id not in skip_ids]
                  

                # If message_ids is empty, adjust the offset and continue
                if not message_ids or 0 in message_ids:
                    offset_id += 1  # Move to the next message ID
                    continue

                try:
                    # Fetch messages from the channel
                    messages = await client.get_messages(chat_id=channel_id, message_ids=message_ids)
                except Exception as e:
                    await edit_message(query.message, f"Indexe error to get message: {e} ")
                    is_indexing_active = False
                    logger.warning("Index Process Cancled due to get messsage")
                    return

                if not messages:
                    break  # No more messages to process

                for msg in messages:
                    if not is_indexing_active:
                        break  # Stop if the process is cancelled
                    
                    if not msg.media:
                        # Skip messages without media
                        total_messages += 1
                        no_media_files += 1
                        continue

                                        # Check for supported media types and extract file size
                    media_type = None
                    file_size = 0

                    if msg.video and msg.video.mime_type in video_mime_types:
                        media_type = 'video'
                        file_size = msg.video.file_size
                        total_messages += 1
                        files_fetched += 1
                    elif msg.audio and msg.audio.mime_type in audio_mime_types:
                        media_type = 'audio'
                        file_size = msg.audio.file_size
                        total_messages += 1
                        files_fetched += 1
                    elif msg.document and msg.document.mime_type in document_mime_types:
                        media_type = 'document'
                        file_size = msg.document.file_size
                        total_messages += 1
                        files_fetched += 1

                    if media_type:
                        # Save valid files
                        try:
                            saved, iron = await save_file(msg)
                            if saved:
                                files_saved += 1
                            elif iron == 0:
                                duplicate_files += 1
                                continue
                            elif iron == 2:
                                unsupported_files += 1
                                continue
                        except Exception as e:
                            logger.error(f"Error saving file: {e}")
                            unsupported_files += 1
                            continue

                    try:
                        # Update the status monitor every 10 files
                        if total_messages % 50 == 0:
                            elapsed_time = str(timedelta(seconds=int(time.time() - start_time)))
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            status_message = (
                                f"📚Total Messages: {total_messages}\n"
                                f"📋Files Fetched: {files_fetched} files\n"
                                f"🗂️Saved: {files_saved} files\n"
                                f"📑Duplicates: {duplicate_files} files\n"
                                f"📭No media: {no_media_files} messages\n"
                                f"💣Unsupported: {unsupported_files} files\n"
                                f"⏳Running Time: {elapsed_time}\n"
                                f"🕒Current DateTime: {current_time}"
                            )
                            await update_status_message(client, query, status_message, True)
                    except MessageNotModified as e:
                        logger.error(f"Error While updating index status message: {e}")

                # Update offset for the next batch
                offset_id += batch_size

        # Final status update
        elapsed_time = str(timedelta(seconds=int(time.time() - start_time)))
        if is_indexing_active == False:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            final_status = (
                f"<b>❌Indexing Cancled!❌</b>\n\n"
                f"📚Total Messages fetched: {total_messages}\n"
                f"<b>📋Total files fetched:</b> {files_fetched}\n"
                f"<b>🗂️Total saved:</b> {files_saved}\n"
                f"<b>📑Duplicates:</b> {duplicate_files}\n"
                f"<b>📭No media:</b> {no_media_files}\n"
                f"<b>💣Unsupported:</b> {unsupported_files}\n"
                f"<b>⏱️Total Running Time:</b> {elapsed_time}\n"
                f"🕒Current DateTime: {current_time}"
            )
        else:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            final_status = (
                f"<b>☑️Indexing complete!☑️</b>\n\n"
                f"📚Total Messages fetched: {total_messages}\n"
                f"<b>📋Total files fetched:</b> {files_fetched}\n"
                f"<b>🗂️Total saved:</b> {files_saved}\n"
                f"<b>📑Duplicates:</b> {duplicate_files}\n"
                f"<b>📭No media:</b> {no_media_files}\n"
                f"<b>💣Unsupported:</b> {unsupported_files}\n"
                f"<b>⏱️Total Running Time:</b> {elapsed_time}\n"
                f"🕒Current DateTime: {current_time}"
            )
        await update_status_message(client, query, final_status, False)
        is_indexing_active = False
        skip_iron_ids = {}
        logger.info("Index Process Completed")

    except Exception as e:
        logger.error(f"Error during file indexing: {e}")
        is_indexing_active = False
        skip_iron_ids = {}
        await update_status_message(client, query, f"An error occurred: {str(e)}")
        raise e

    
async def update_status_message(client, query, status_message, cancel=False):
    """
    Update the status message in the Telegram chat.
    """
    button_maker = ButtonMaker()
    try:
        if cancel:
            button_maker.callback("❌Cancel❌", "index_cancle")
            reply_markup = button_maker.column()
        else:
            reply_markup = None

        await edit_message(
            query.message,
            text=status_message,
            buttons=reply_markup
        )
        return
    except Exception as e:
        logger.error(f"Error updating status: {e}")

async def cancel_indexing(client, query):
    """
    Stop the indexing process when cancel button is pressed.
    """
    global is_indexing_active
    is_indexing_active = False
    skip_iron_ids = {}
    await update_status_message(client, query, "🚫Indexing process canceled.🚫", cancel=False)
    logger.warning("Index Process Cancled")
    await asyncio.sleep(1)
    

async def index_cmd_handler(client, message):
    await message.reply(
        text = "Please forward your file channel last message or last file with forwreded tag. please cooperate until i am not updated.",
        quote=True
    )

async def set_skip(client, message):
    if message.reply_to_message:
        if message.reply_to_message.text:
            msg = message.reply_to_message.text.split()
            if len(msg) != 2:
                return await send_message(message, "This is invalid link")
            for link in msg:
                if not (link.startswith("https://") or link.startswith("http://")):
                    return await send_message(message, "This is Invalid formate of link")
            iron_1 = msg[0].split('/')
            iron_2 = msg[1].split('/')
            if 'c' not in (iron_1 and iron_2):
                return await send_message(message, "This not channel links")
            chnl_1 = iron_1[4]
            chnl_2 = iron_2[4]
            if chnl_1 != chnl_2:
                return await send_message(message, "Both channel link are not same")
            chanl_id = int('-100' + chnl_1)
            iron_id_1 = int(iron_1[5])
            iron_id_2 = int(iron_2[5])
            if iron_id_1 < iron_id_2:
                skip_iron_ids[chanl_id] = list(range(iron_id_1, iron_id_2 + 1))  # Forward range
            else:
                skip_iron_ids[chanl_id] = list(range(min(iron_id_1, iron_id_2), max(iron_id_1, iron_id_2) + 1))  # Reverse range

            if skip_iron_ids[chanl_id] and len(skip_iron_ids[chanl_id]) > 20:
                skip_ids_display = skip_iron_ids[chanl_id][:20] + ['...']
                await send_message(message, f"Skip ids Added,\n\nNow this channel {chanl_id} files now skipped in indexing:{skip_ids_display}")
            else:
                await send_message(message, f"Skip ids Added,\n\nNow this channel {chanl_id} files now skipped in indexing:{skip_iron_ids[chanl_id]}")

    else:
        msg = message.text.split()
        if len(msg) != 3:
            await send_message(message, "This invalid Formate\n\nPlease send message below formate\n\n<code>/setskip https://t.me/c/12345678/4321 https://t.me/c/12345678/1234</code>\n\nOR Reply to text formate: <code>https://t.me/c/12345678/4321 https://t.me/c/12345678/1234</code>")
            return
        for link in msg[1:]:  # Skip the command '/setskip' for validation
            if not (link.startswith("https://") or link.startswith("http://")) or "t.me/c/" not in link:
                await send_message(message, "This is an invalid format of link")
                return
        iron_1 = msg[1].split('/')
        iron_2 = msg[2].split('/')
        #recheck  link
        if 'c' not in (iron_1 and iron_2):
            return await send_message(message, "This not channel links")
        
        chnl_1 = iron_1[4]
        chnl_2 = iron_2[4]
        if chnl_1 != chnl_2:
            return await send_message(message, "Both channel link are not same")
        chanl_id = int('-100' + chnl_1)
        iron_id_1 = int(iron_1[5])
        iron_id_2 = int(iron_2[5])
        if iron_id_1 < iron_id_2:
            skip_iron_ids[chanl_id] = list(range(iron_id_1, iron_id_2 + 1))  # Forward range
        else:
            skip_iron_ids[chanl_id] = list(range(min(iron_id_1, iron_id_2), max(iron_id_1, iron_id_2) + 1))  # Reverse range
        if skip_iron_ids[chanl_id] and len(skip_iron_ids[chanl_id]) > 20:
            skip_ids_display = skip_iron_ids[chanl_id][:20] + ['...']
            await send_message(message, f"Skip ids Added,\n\nNow this channel {chanl_id} files now skipped in indexing:{skip_ids_display}")
        else:
            await send_message(message, f"Skip ids Added,\n\nNow this channel {chanl_id} files now skipped in indexing:{skip_iron_ids[chanl_id]}")

async def skip_ids_giver(client, message):
    await message.reply(
        f"This is you skip_ids: {skip_iron_ids}"
    )
            
            
    

bot.add_handler(MessageHandler(
    index_cmd_handler, filters= private & command(BotCommands.IndexCommand) & CustomFilters.sudo)
)

bot.add_handler(MessageHandler(
    get_index_button,
    filters=incoming & private & forwarded & (video | document | audio) & CustomFilters.sudo
))

pattern = r"(index_file|index_yes|index_stop|index_cancle|index_skipped_file|index_skipped_yes|index_utd|index_dtu|index_skip_utd|index_skip_dtu|index_defult_skip_yes|index_defult_yes)"

bot.add_handler(CallbackQueryHandler(
    index_file_handler, filters=regex(pattern) & CustomFilters.sudo
), group=-1)

bot.add_handler(
    MessageHandler(
        set_skip, filters=command(BotCommands.SetSkipFilesCommand)
    )
)

bot.add_handler(
    MessageHandler(
        skip_ids_giver, filters= command("showskip")
    )
)
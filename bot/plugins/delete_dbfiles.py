import asyncio, time

from pyrogram.filters import *
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, ChatWriteForbidden, FloodWait

from bot import bot, LOGGER, FILES_DATABASE_URL, deldbfiles_handler_dict
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import send_message, delete_message, edit_message
from bot.database.db_file_handler import unpack_new_file_id, Media
from bot.database.db_utils import get_search_results

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.extra.bot_utils import new_thread

glob_date = {}
glob_month = {}
glob_del_word = {}
deldbfiles_event_data = {}
DELDBFILE_STATE = 'view'

#-----------------START------------------#
#----------------GENERAL-----------------#
#--------------HUB4VF BOT----------------#

async def extract_file_from_message(message):
    """
    Extracts the file from the message, either from a reply or a link.

    :param message: The message object.
    :return: Tuple (ironfile, error_message)
    """
    if message.reply_to_message:
        media = message.reply_to_message.video or message.reply_to_message.document or message.reply_to_message.audio
        if media:
            return media, None
        else:
            return None, 'Media does not have a valid file_id.'
    
    if len(message.text.split()) < 2:
        return None, "Please provide a valid channel file link after the command or reply to a message containing the link."

    link = message.text.split(maxsplit=1)[1]
    file_msg = link.split('/')
    if 'c' not in file_msg or 't.me' not in file_msg:
        return None, "Please provide a valid channel file link."

    chat_id = int('-100' + file_msg[4])
    msg_id = int(file_msg[5])

    try:
        file = await bot.get_messages(chat_id, msg_id)
        if file.empty or file.sticker or file.text:
            return None, 'This is not a valid file link or the file is not available.'
        return file.video or file.document or file.audio, None
    except Exception as e:
        return None, f"An error occurred while fetching the file: {str(e)}\n\nI recommend to you forward your file here reply and that file with /deletefile command."


#------------------END-----=-------------#
#----------------GENERAL-----------------#
#--------------HUB4VF BOT----------------#

####################################
#            HUB4VF BOT            #
####################################

#-----------------START------------------#
#--------------SINGLE FILE---------------#
#--------------HUB4VF BOT----------------#

async def delete_file(file_id):
    """
    Delete a file document from the MongoDB collection by its _id.

    :param file_id: The _id of the file document to delete.
    :return: Tuple (True/False, error_code)
    """
    client = AsyncIOMotorClient(FILES_DATABASE_URL)
    db = client.HUB4VF
    try:
        result = await db.hubfiles.delete_one({"_id": file_id})
        if result.deleted_count > 0:
            LOGGER.info(f"File with _id {file_id} deleted successfully.")
            return True, 0
        else:
            LOGGER.warning(f"No file found with _id {file_id}.")
            return False, 1
    except PyMongoError as e:
        LOGGER.error(f"Database connection error: {e}")
        return False, 2
    except Exception as e:
        LOGGER.error(f"Error deleting file with _id {file_id}: {e}")
        return False, 3
    finally:
        client.close()  # Ensure the connection is properly closed

async def delete_single_file(client, message):
    ironfile, error_message = await extract_file_from_message(message)
    if error_message:
        await send_message(message, error_message)
        return

    if not ironfile:
        await send_message(message, 'Media does not have a valid file_id.')
        return

    file_id, file_ref = unpack_new_file_id(ironfile.file_id)
    success, error_code = await delete_file(file_id)

    if success:
        reply_text = f"File Name: {ironfile.file_name} deleted successfully."
    else:
        error_messages = {
            1: "This file is not found in Database.",
            2: "An error occurred while connecting to the Database.",
            3: "An unknown error occurred while deleting this file."
        }
        reply_text = error_messages.get(error_code, "An unexpected error occurred.")

    await send_message(message, reply_text)

bot.add_handler(MessageHandler(
    delete_single_file, filters= private & command(BotCommands.DeleteDbfileCommand)
))

#------------------END-----=-------------#
#--------------SINGLE FILE---------------#
#--------------HUB4VF BOT----------------#


####################################
#            HUB4VF BOT            #
####################################


#------------------START-----------------#
#---------------MULTI FILE---------------#
#---------------HUB4VF BOT---------------#

async def delete_files_by_date(client, query, user_id, batch_size=100):
    """
    Delete all files from MongoDB for the specified date with progress display.

    :param client: The MongoDB client.
    :param query: The query context for responding to the user.
    :param user_id: The ID of the user initiating the delete.
    :param batch_size: The number of files to delete in each batch.
    :return: None
    """
    await edit_message(query.message, text="Starting Deleting Process...\n\nPlease Wait...")
    user_name = query.from_user.first_name  # or query.from_user.username if you prefer

    if glob_month[user_id] is None or glob_date[user_id] is None:
        await query.answer("Error: Month or date not found.", show_alert=True)
        return
    
    try:
        mongo_client = AsyncIOMotorClient(FILES_DATABASE_URL)
        db = mongo_client.HUB4VF
        db_files = db.hubfiles
    except Exception as e:
        error_message = f"Failed to connect to MongoDB: {e}"
        await query.message.edit(text=error_message)
        LOGGER.error(error_message)
        return


    year = '2025'
    month = str(glob_month[user_id])
    date = str(glob_date[user_id])
    current_date = f"{year}-{month.zfill(2)}-{date.zfill(2)}"  # Format: YYYY-MM-DD

    # Build the filter for the date
    filter = {"created_at.date": current_date}

    try:
        # Count total documents to delete
        total_documents = await db_files.count_documents(filter)
        iron_total = total_documents
        if total_documents == 0:
            await query.message.edit(text=f"No files found for date {current_date}.")
            return

        processed_size = 0
        start_time = time.time()
        last_progress = 0  # Track the last progress percentage

        # Deleting in batches
        while total_documents > 0:
            # Calculate the actual batch size
            current_batch_size = min(batch_size, total_documents)

            # Perform the delete operation
            result = await db_files.delete_many(filter)

            # Update processed size and total documents
            processed_size += result.deleted_count
            total_documents -= result.deleted_count

            # Calculate progress
            elapsed_time = time.time() - start_time
            progress = (processed_size / (processed_size + current_batch_size)) * 100 if total_documents > 0 else 100
            speed = processed_size / elapsed_time if elapsed_time > 0 else 0

            # Update progress message if progress has increased by 2% or more
            if progress - last_progress >= 2:
                bar_length = 10  # Length of the progress bar
                completed_length = int(bar_length * (processed_size / (processed_size + current_batch_size)))
                bar = '★' * completed_length + '☆' * (bar_length - completed_length)

                # Prepare the progress message
                progress_message = (
                    f"🚀 Deleting Files for Date: {current_date}\n"
                    f"👤 By: {user_name}\n\n"
                    f"|{'★' * 10}| 100.00%\n\n"
                    f"📦 Deleted: {processed_size} files\n"
                    f"📊 Pending: {total_documents} files\n"
                    f"🗂️ Total: {iron_total} files\n"
                    f"🚀 Speed: {speed:.2f}MB/s\n"
                    f"⏳ Running Time: {elapsed_time:.2f}s"
                )

                # Try to edit the message with progress
                try:
                    await query.message.edit(text=progress_message)
                    last_progress = progress  # Update last progress
                except FloodWait as e:
                    LOGGER.warning(f"Flood wait for {e.seconds} seconds. Waiting...")
                    await asyncio.sleep(e.seconds)  # Wait for the specified time
                    # Retry editing the message after waiting
                    await query.message.edit(text=progress_message)
                    last_progress = progress  # Update last progress

    except PyMongoError as e:
        error_message = f"Database connection error: {e}"
        await query.message.edit(text=error_message)
        LOGGER.error(error_message)
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        await query.message.edit(text=error_message)
        LOGGER.error(error_message)
    finally:
        mongo_client.close()  # Ensure the connection is properly closed

    # Final message after deletion is complete
    final_message = (
        f"✔️ Delete Process Completed ✔️\n"
        f"🚀 Deleting Files for Date: {current_date}\n"
        f"👤 By: {user_name}\n\n"
        f"|{'★' * 10}| 100.00%\n\n"
        f"📦 Deleted: {processed_size} files\n"
        f"📊 Pending: {total_documents} files\n"
        f"🗂️ Total: {iron_total} files\n"
        f"🚀 Speed: {speed:.2f}MB/s\n"
        f"⏳ Running Time: {elapsed_time:.2f}s"
    )

    await query.message.edit(text=final_message) 

async def delete_files_related_to_word(client, user_id, query, batch_size=100):
    """Delete all files related to a specific word from the database with progress display."""
    
    user_name = query.from_user.username  # or message.from_user.username if you prefer
    await edit_message(query.message, text="Starting Deleting Process...\n\nPlease Wait...")
    print("pass f1")
    print(FILES_DATABASE_URL)
    # Establish MongoDB connection
    try:
        mongo_client = AsyncIOMotorClient(FILES_DATABASE_URL)
        db = mongo_client.HUB4VF
        db_files = db.hubfiles
    except Exception as e:
        error_message = f"Failed to connect to MongoDB: {e}"
        await query.message.edit(text=error_message)
        LOGGER.error(error_message)
        return
    print("pass f1.5")
    specific_word = glob_del_word.get(user_id, None)
    print("pass f2")
    if not specific_word:
        await edit_message(query.message, text=f"No specific word found for user_id: {user_id}")
        return
    print("pass f3")
    # Prepare the regex pattern for the specific word
    raw_pattern = r'(\b|[\.\+\-_])' + re.escape(specific_word) + r'(\b|[\.\+\-_])'
    print("pass f4")
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except re.error as e:
        await edit_message(query.message, text=f"Regex error: {e}")
        return
    print("pass f5")
    # Build the filter dictionary
    filter = {'$or': [{'file_name': regex}, {'caption': regex}]}

    # Count total documents to delete
    total_documents = await db_files.count_documents(filter)
    iron_total = total_documents
    if total_documents == 0:
        await edit_message(query.message, text=f"No files found for the word '{specific_word}'.")
        return
    print("pass f6")

    total_size = 0  # Placeholder for total size of files to be deleted
    processed_size = 0
    start_time = time.time()
    last_progress = 0  # Track the last progress percentage

    # Deleting in batches
    while total_documents > 0:
        # Calculate the actual batch size
        current_batch_size = min(batch_size, total_documents)
        
        # Perform the delete operation
        result = await db_files.delete_many(filter)
        
        # Update processed size and total documents
        processed_size += result.deleted_count
        total_documents -= result.deleted_count
        
        # Calculate progress
        elapsed_time = time.time() - start_time
        progress = (processed_size / (processed_size + current_batch_size)) * 100 if total_documents > 0 else 100
        speed = processed_size / elapsed_time if elapsed_time > 0 else 0
        
        # Update progress message if progress has increased by 2% or more
        if progress - last_progress >= 2:
            bar_length = 10  # Length of the progress bar
            completed_length = int(bar_length * (processed_size / (processed_size + current_batch_size)))
            bar = '★' * completed_length + '☆' * (bar_length - completed_length)
            
            # Prepare the progress message
            progress_message = (
                f"🚀 Deleting: {specific_word} Files\n"
                f"👤 By: {user_name}\n\n"
                f"|{'★' * 10}| {progress:.2f}\n\n"
                f"📦 Deleted: {processed_size} files\n"
                f"📊 Pending: {total_documents} files\n"
                f"🗂️ Total: {iron_total} files\n"
                f"🚀 Speed: {speed:.2f}MB/s\n"
                f"⏳ Running Time: {elapsed_time:.2f}s"
            )
            
            # Try to edit the message with progress
            try:
                await edit_message(query.message, text=progress_message)
                last_progress = progress  # Update last progress
            except FloodWait as e:
                print(f"Flood wait for {e.seconds} seconds. Waiting...")
                await asyncio.sleep(e.seconds)  # Wait for the specified time
                # Retry editing the message after waiting
                await edit_message(query.message, text=progress_message)
                last_progress = progress  # Update last progress

    # Final message after deletion is complete
    final_message = (
        f"✔️ Delete Process Completed ✔️\n"
        f"🚀 Deleting: {specific_word} Files\n"
        f"👤 By: {user_name}\n\n"
        f"|{'★' * 10}| 100.00%\n\n"
        f"📦 Deleted: {processed_size} files\n"
        f"📊 Pending: {total_documents} files\n"
        f"🗂️ Total: {iron_total} files\n"
        f"🚀 Speed: {speed:.2f}MB/s\n"
        f"⏳ Running Time: {elapsed_time:.2f}s"
    )
    
    await edit_message(query.message, text=final_message)
    mongo_client.close()  # Close MongoDB connection

async def get_delete_db_multi_files_buttons(key=None, edit_mode=False, user_id=None, message=None, total_files=None):
    button_maker = ButtonMaker()
    text = None
    
    if key is None:
        button_maker.add_button(text='DATE', callback_data=f'deldbfile cale {user_id}')
        button_maker.add_button(text='Specific Word', callback_data=f'deldbfile name {user_id}')
        button_maker.add_button(text='Close', callback_data=f'deldbfile close {user_id}')
        text = f"This is for delete multiple files from mongodb.\n\nPlease select below button what you want."

    elif key == 'name':
        if not edit_mode:
            button_maker.add_row([('Add Word', f'deldbfile word edit {user_id}'), ('Reset', f'deldbfile reset word {user_id}')])
        else:
            button_maker.add_row([('Stop Add Word', f'deldbfile word {user_id}'), ('Reset', f'deldbfile reset word {user_id}')])
        if glob_del_word.get(user_id, None) != None and edit_mode == False:
            button_maker.add_button(text='Start Delete Files', callback_data=f'deldbfile startdelWF {user_id}')
        button_maker.add_row([('Back', f'deldbfile back {user_id}'), ('Close', f'deldbfile close {user_id}')])
        text = (
            "This will delete your setted specific word all files from mongodb\n\n"
            "Just add a word that word files you want delete from mongodb by click on Add Word button\n"
            "After add a word you able to see Start Delete Files Button.\n\n"
            f"Your Word: {glob_del_word.get(user_id, 'None')}"
        )    

    elif key == 'cale':
        button_maker.add_row([('Date', f'deldbfile date {user_id}'), ('Month' , f'deldbfile month {user_id}')])
        if glob_date.get(user_id, None) != None and glob_month.get(user_id, None) != None:
            button_maker.add_button(text="Start Delete Files", callback_data=f"deldbfile startdelDMF {user_id}")
        button_maker.add_row([('Back', f'deldbfile back {user_id}'), ('Close', f'deldbfile close {user_id}')])
        text = f"Please select below button what you want\n\nYour Selected Date: {glob_date.get(user_id, None)}:{glob_month.get(user_id, None)}:2025"
        if glob_date.get(user_id, None) != None and glob_month.get(user_id, None) == None:
            text = f"Please select below button what you want\n\nYour Selected Date: {glob_date.get(user_id, None)}:{glob_month.get(user_id, None)}:2025\n\nNow please select month to continue."
        elif glob_date.get(user_id, None) == None and glob_month.get(user_id, None) != None:
            text = f"Please select below button what you want\n\nYour Selected Date: {glob_date.get(user_id, None)}:{glob_month.get(user_id, None)}:2025\n\nNow please select date to continue"
        elif glob_date.get(user_id, None) != None and glob_month.get(user_id, None) != None:
            text = f"Please select below button what you want\n\nYour Selected Date: {glob_date.get(user_id, None)}:{glob_month.get(user_id, None)}:2025\n\nNow please select start delete files button."
    elif key == 'date':
        text = "Please select a number of date"
        button_maker.add_row([('1', f'deldbfile deldate 1 {user_id}'), ('2', f'deldbfile deldate 2 {user_id}'), ('3', f'deldbfile deldate 3 {user_id}'), ('4', f'deldbfile deldate 4 {user_id}'), ('5', f'deldbfile deldate 5 {user_id}'), ('6', f'deldbfile deldate 6 {user_id}')])
        button_maker.add_row([('7', f'deldbfile deldate 7 {user_id}'), ('8', f'deldbfile deldate 8 {user_id}'), ('9', f'deldbfile deldate 9 {user_id}'), ('10', f'deldbfile deldate 10 {user_id}'), ('11', f'deldbfile deldate 11 {user_id}'), ('12', f'deldbfile deldate 12 {user_id}')])
        button_maker.add_row([('13', f'deldbfile deldate 13 {user_id}'), ('14', f'deldbfile deldate 14 {user_id}'), ('15', f'deldbfile deldate 15 {user_id}'), ('16', f'deldbfile deldate 16 {user_id}'), ('17', f'deldbfile deldate 17 {user_id}'), ('18', f'deldbfile deldate 18 {user_id}')])
        button_maker.add_row([('19', f'deldbfile deldate 19 {user_id}'), ('20', f'deldbfile deldate 20 {user_id}'), ('21', f'deldbfile deldate 21 {user_id}'), ('22', f'deldbfile deldate 22 {user_id}'), ('23', f'deldbfile deldate 23 {user_id}'), ('24', f'deldbfile deldate 24 {user_id}')])
        button_maker.add_row([('25', f'deldbfile deldate 25 {user_id}'), ('26', f'deldbfile deldate 26 {user_id}'), ('27', f'deldbfile deldate 27 {user_id}'), ('28', f'deldbfile deldate 28 {user_id}'), ('29', f'deldbfile deldate 29 {user_id}'), ('30', f'deldbfile deldate 30 {user_id}'), ('31', f'deldbfile deldate 31 {user_id}')])
        button_maker.add_row([('Back', f'deldbfile cale {user_id}'), ('Close', f'deldbfile close {user_id}')])

    elif key == 'month':
        text = "Please select a number of month"
        button_maker.add_row([('1', f'deldbfile delmonth 1 {user_id}'), ('2', f'deldbfile delmonth 2 {user_id}'), ('3', f'deldbfile delmonth 3 {user_id}'), ('4', f'deldbfile delmonth 4 {user_id}')])
        button_maker.add_row([('5', f'deldbfile delmonth 5 {user_id}'), ('6', f'deldbfile delmonth 6 {user_id}'), ('7', f'deldbfile delmonth 7 {user_id}'), ('8', f'deldbfile delmonth 8 {user_id}')])
        button_maker.add_row([('9', f'deldbfile delmonth 9 {user_id}'), ('10', f'deldbfile delmonth 10 {user_id}'), ('11', f'deldbfile delmonth 11 {user_id}'), ('12', f'deldbfile delmonth 12 {user_id}')])
        button_maker.add_row([('Back', f'deldbfile cale {user_id}'), ('Close', f'deldbfile close {user_id}')])

    elif key == 'startdelWF':
        button_maker.add_button(text="Confirm", callback_data=f"deldbfile confirmedWF {user_id}")
        button_maker.add_row([('Back', f'deldbfile name {user_id}'), ('Close', 'deldbfile close')])
        text=(
            f"i found <b>Total {total_files} Files</b> for your word: {glob_del_word[user_id]}\n\n"
            f"Please click on confirm button if you are sure to delete this total {total_files} files from mongodb database."
        )
    elif key == 'startdelDMF':  
        button_maker.add_button(text="Confirm", callback_data=f"deldbfile confirmedDMF {user_id}")
        button_maker.add_row([('Back', f'deldbfile cale {user_id}'), ('Close', 'deldbfile close')])
        text=(
            f"i found <b>Total {total_files} Files</b> for your Date: {glob_date[user_id]}:{glob_month[user_id]}:2025\n\n"
            f"Please click on confirm button if you are sure to delete this total {total_files} files from mongodb database."
        )

    button = button_maker.build()
    return text, button

async def deldbfile_update_buttons(message, key=None, edit_mode=None, user_id=None, total_files=None):
    msg, button = await get_delete_db_multi_files_buttons(key, edit_mode, user_id, message, total_files)
    await edit_message(message, msg, button)

async def deldbfiles_update_variable(message):
    value = message.text
    chat_id = str(message.from_user.id)
    #print(f"deldbfiles_update_variable: {chat_id} {type(chat_id)}")
    if chat_id in deldbfiles_event_data and deldbfiles_event_data[chat_id] is not None:
        if 'event_key' in deldbfiles_event_data[chat_id] and deldbfiles_event_data[chat_id]['event_key'] is not None:
            key = deldbfiles_event_data[chat_id]["event_key"]
            initial_message = deldbfiles_event_data[chat_id]["event_msg"]
            try:
                glob_del_word[chat_id] = value
                await delete_message(message)
                LOGGER.info(f"Updating Delete DB Files key: {key} with value: {value}")
                await deldbfile_update_buttons(initial_message, 'name', False, str(message.from_user.id))
                deldbfiles_handler_dict[chat_id] = False
                deldbfiles_event_data[chat_id] = None
            except Exception as e:
                LOGGER.error(f"Error updating delete word for database or buttons: {e}")

async def wait_for_timeout(chat_id, timeout_duration, message):
    try:
        await asyncio.sleep(timeout_duration)
        # If we reach here, the timeout has occurred
        deldbfiles_handler_dict[chat_id] = False
        await deldbfile_update_buttons(message, 'name', False, chat_id)  # Exit edit mode
    except asyncio.CancelledError:
        # This exception is raised if the task is cancelled
        pass

@new_thread
async def delete_db_multifile_callbackHandler(client, query: CallbackQuery):
    data = query.data.split()
    message = query.message
    user_id = data[-1]
    
    if int(user_id) != query.from_user.id:
        return await query.answer("⚠️ Alert! This not for you", show_alert=True)

    if data[1] == 'close':
        deldbfiles_handler_dict[user_id] = False
        await query.answer()
        await delete_message(message)
        await delete_message(message.reply_to_message)
    elif data[1] == 'cale':
        await query.answer()
        await deldbfile_update_buttons(message, data[1], False, user_id)
    elif data[1] == 'date':
        await query.answer()
        await deldbfile_update_buttons(message, data[1], False, user_id)
    elif data[1] == 'month':
        await query.answer()
        await deldbfile_update_buttons(message, data[1], False, user_id)
    elif data[1] == 'deldate':
        await query.answer()
        glob_date[user_id] = data[2]
        await deldbfile_update_buttons(message, 'cale', False, user_id)
    elif data[1] == 'delmonth':
        await query.answer()
        glob_month[user_id] = data[2]
        await deldbfile_update_buttons(message, 'cale', False, user_id)
    elif data[1] == 'back':
        await query.answer()
        deldbfiles_handler_dict[user_id] = False
        await deldbfile_update_buttons(message, None, False, user_id)
    elif data[1] == 'name':
        await query.answer()
        await deldbfile_update_buttons(message, data[1], False, user_id)
    elif data[1] == 'word':
        await query.answer()
        deldbfiles_handler_dict[user_id] = False
        edit_mode = len(data) == 4
        await deldbfile_update_buttons(message, 'name', edit_mode, user_id)
        if edit_mode:
            deldbfiles_handler_dict[user_id] = True 
            # Prepare button data to pass to the timeout function
            deldbfiles_event_data[user_id] = {
                'event_msg': message,
                'event_key': data[1],
            }
            # Create a task for the timeout
            timeout_task = asyncio.create_task(wait_for_timeout(user_id, 60, message))
            iron_update = await client.send_message(chat_id=query.from_user.id, text="Hurry Up,\n\nTime Left Is: 60", reply_to_message_id=query.message.id)
            try:
                time_left = 60
                while deldbfiles_handler_dict[user_id]:  # Keep checking while it's True
                    await asyncio.sleep(1)  # Sleep to avoid busy waiting
                    time_left -= 1  # Decrease the time by 1 second
                    # When the loop ends, the time is 0 or handler_dict is False
                    if time_left == 1:  
                        await edit_message(iron_update, "Oops,\n\nYou are late buddy,\n\nTime Is Up,\n\nPlease Try Again")
                    if time_left % 2 == 0:  # Update the message every 5 seconds
                        # Update the message with the remaining time                       
                        await edit_message(iron_update, f"Hurry Up,\n\nTime Left Is: {time_left}")
                await asyncio.sleep(0.5)
                await delete_message(iron_update)
                deldbfiles_event_data[user_id] = None  # Clean up event data
            finally:
                timeout_task.cancel()
    elif data[1] == 'startdelDMF':
        print("pass 1")
        if glob_date.get(user_id, None) == None or glob_month.get(user_id, None) == None:
            await query.answer("Error: Not found date for delete", show_alert=True)
            await deldbfile_update_buttons(message, 'cale', False, user_id)
            return 
        print("pass 2")
        month = str(glob_month[user_id])
        date = str(glob_date[user_id])
        file_date = f"2025-{month.zfill(2)}-{date.zfill(2)}"
        print(file_date)
        total_results = await Media.count_documents({"created_at.date": file_date})
        print("pass 3")
        if total_results == 0:
            return await query.answer("No files found for your date", show_alert=True)
        await query.answer()
        await deldbfile_update_buttons(message, data[1], False, user_id, total_results)
    elif data[1] == "startdelWF":
        if glob_del_word.get(user_id, None) == None:
            await query.answer("Error: Not found word for delete", show_alert=True)
            await deldbfile_update_buttons(message, 'name', False, user_id)
            return
        files, offset, total_results = await get_search_results(user_id, glob_del_word[user_id], offset=0, filter=True)
        if total_results == 0:
            return await query.answer("No files found for your word", show_alert=True)
        await query.answer()
        await deldbfile_update_buttons(message, data[1], False, user_id, total_results)  
    elif data[1] == "confirmedDMF":
        print("pass confirmedDMF")
        await query.answer()
        await delete_files_by_date(client, query, user_id)
    elif data[1] == "confirmedWF":
        print("pass confirmedWF")
        await query.answer()
        await delete_files_related_to_word(client, user_id, query)


async def deletedbfiles_message_handler(_, message):
    msg, button = await get_delete_db_multi_files_buttons(user_id=message.from_user.id)
    await send_message(message, msg, button)

        

bot.add_handler(
    CallbackQueryHandler(delete_db_multifile_callbackHandler, filters= regex(r"^deldbfile") & CustomFilters.sudo), group=-1
)
bot.add_handler(MessageHandler(
    deletedbfiles_message_handler, filters= private & command(BotCommands.DeleteDbfilesCommand) & CustomFilters.sudo
))

#-------------------END------------------#
#---------------MULTI FILE---------------#
#---------------HUB4VF BOT---------------#


####################################
#            HUB4VF BOT            #
####################################
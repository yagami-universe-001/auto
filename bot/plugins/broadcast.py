import time
from asyncio import sleep, CancelledError, create_task, Lock
from pyrogram import Client, filters
from pymongo import MongoClient
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.filters import command, regex, private
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram.errors import *

from bot import DATABASE_URL, bot_id, bot, LOGGER, broadcast_handler_dict
from bot.helper.telegram_helper.message_utils import send_message, edit_message, delete_message, one_minute_del
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.database.db_handler import DbManager
from bot.helper.extra.bot_utils import get_readable_time


broadcast_event_data = {}
USERS_BROADCAST_CANCEL = False
broadcast_lock = Lock()
        
async def get_broadcast_button(userid=None, key=None, edit_mode=False):
    buttons = ButtonMaker()
    if userid:
        EXCEPTION_USERS = broadcast_event_data[userid]["EXCEPTION_USERS"] if userid in broadcast_event_data and "EXCEPTION_USERS" in broadcast_event_data[userid] else None
        BROADCAST_MESSAGE = broadcast_event_data[userid]["BROADCAST_MESSAGE"] if userid in broadcast_event_data and "BROADCAST_MESSAGE" in broadcast_event_data[userid] else None
    else:
        EXCEPTION_USERS = None
        BROADCAST_MESSAGE = None
    if key == None:

        # Define the confirmation message
        text = (
            f"<b>Waiting For Your Confirmation</b>\n\n"
            f"If You Want To Add Exception Users Then Please Click On Add Exception Button else Click On Skip Button"
        )

        # Add buttons to the button maker
        buttons.add_row([("Add Exception", f"broadcast addusers {userid}"), ("Skip", f"broadcast skip {userid}")])
        buttons.add_button(text="Cancel", callback_data=f"broadcast close {userid}")

        iron_markup = buttons.build()
    elif key == 'addusers':
        text = (
            "To add users as exception users click on Add Users Button and send message with user ids.\n"
            "Example: <code>1234567890 9876543210</code> add multiple users by space\n\n"
            "Note: Broadcast Message not send to this Exceptions Users\n\n"
            f"Exception Users: {EXCEPTION_USERS if EXCEPTION_USERS is not None else ''}"
        )
        
        if edit_mode == True:
            buttons.add_row([("Stop Add", f"broadcast addusers {userid}"), ("Reset", f"broadcast reset users {userid}")])
        else:
            buttons.add_row([("Add Users", f"broadcast addusers edit {userid}"), ("Reset", f"broadcast reset users {userid}")])
        buttons.add_row([("Back", f"broadcast back {userid}"), ("Close", f"broadcast close {userid}")])

        iron_markup = buttons.build()
    elif key == "skip":
        if BROADCAST_MESSAGE is not None:
            text = f"Please Click on Start BroadCast Button To Start Broadcasting.\n\nBroadcast Message: {BROADCAST_MESSAGE.text}"
            buttons.add_row([("Start Broadcasting", f"broadcast live {userid}"), ("Reset", f"broadcast reset message {userid}")])
        else:
            text = "Please add broadcast message first Before start broadcasting.\n\nAfter add message you will see Start Broadcasting Button then click on it."
            if edit_mode == True:
                buttons.add_button("Stop Add Message", callback_data=f"broadcast add_message {userid}")
            else:
                buttons.add_button("Add Broadcast Message", callback_data=f"broadcast add_message edit {userid}")
        buttons.add_row([("Back",f"broadcast back {userid}"), ("Close", f"broadcast close {userid}")])
        
        iron_markup = buttons.build()

    return text, iron_markup

async def update_broadcast_buttons(message, userid=None, key=None, edit_mode=None):
    msg, button = await get_broadcast_button(userid, key, edit_mode)
    await edit_message(message, msg, button)

async def update_broadcast_variable(message):
    global EXCEPTION_USERS, BROADCAST_MESSAGE
    value = message.text
    chat_id = message.from_user.id
    if chat_id in broadcast_event_data and broadcast_event_data[chat_id] is not None:
        if 'event_key' in broadcast_event_data[chat_id] and broadcast_event_data[chat_id]['event_key'] is not None:
            key = broadcast_event_data[chat_id]["event_key"]
            try:
                if key == 'addusers':
                    if 'EXCEPTION_USERS' not in broadcast_event_data[chat_id]:
                        broadcast_event_data[chat_id]['EXCEPTION_USERS'] = value
                    else:
                        LOGGER.info(f"EXCEPTION_USERS already set for {chat_id}, not overwriting.")
                elif key == 'add_message':
                    if 'BROADCAST_MESSAGE' not in broadcast_event_data[chat_id]:
                        broadcast_event_data[chat_id]['BROADCAST_MESSAGE'] = message
                    else:
                        LOGGER.info(f"BROADCAST_MESSAGE already set for {chat_id}, not overwriting.")
                # Additional logging
                LOGGER.info(f"Updating key: {key} with value: {value}")
                await delete_message(message)
                broadcast_handler_dict[chat_id] = False
                broadcast_event_data[chat_id]['event_key'] = None
                broadcast_event_data[chat_id]['event_msg'] = None
            except Exception as e:
                LOGGER.error(f"Error update_broadcast_variable: {e}")

async def wait_for_timeout(chat_id, timeout_duration):
    try:
        await sleep(timeout_duration)
        # If we reach here, the timeout has occurred
        broadcast_handler_dict[chat_id] = False
    except CancelledError:
        # This exception is raised if the task is cancelled
        pass

async def broadcast_callback_handler(client, query: CallbackQuery):
    data = query.data.split()
    message = query.message
    userid = int(data[2]) if len(data) == 3 else int(data[3])
    if userid != query.from_user.id:
        return await query.answer("This is not for you.", show_alert=True)
    if data[1] == 'live':
        await query.answer()
        await edit_message(message, "Start Broadcasting...\n\nGetting Users List...")
        await broadcast_users(client, message, userid)
        
    elif data[1] == 'close':
        await query.answer()
        broadcast_handler_dict[message.chat.id] = False
        await delete_message(message)
        await delete_message(message.reply_to_message)
    elif data[1] == 'back':
        await query.answer()
        broadcast_handler_dict[message.chat.id] = False
        await update_broadcast_buttons(message, userid=userid, key=None)
    elif data[1] == 'reset':
        if data[2] == 'users':
            if message.chat.id in broadcast_event_data and 'EXCEPTION_USERS' in broadcast_event_data[message.chat.id]:
                await query.answer("Exception users list reseted.", show_alert=True)
                broadcast_event_data[message.chat.id]["EXCEPTION_USERS"] = None
                await update_broadcast_buttons(message, userid=userid, key='addusers')
            else:
                await query.answer("No exception users list to reset.", show_alert=True)
                await update_broadcast_buttons(message, userid=userid, key='addusers')
        elif data[2] == 'message':
            if message.chat.id in broadcast_event_data and 'BROADCAST_MESSAGE' in broadcast_event_data[message.chat.id]:
                await query.answer("Broadcast Message Rested.", show_alert=True)
                broadcast_event_data[message.chat.id]["BROADCAST_MESSAGE"] = None
                await update_broadcast_buttons(message, userid=userid, key='skip')
            else:
                await query.answer("No Broadcast Message to reset.", show_alert=True)
                await update_broadcast_buttons(message, userid=userid, key='skip')
    elif data[1] == 'addusers':
        await query.answer()
        broadcast_handler_dict[message.chat.id] = False
        edit_mode = len(data) == 4
        await update_broadcast_buttons(message, userid=userid, key='addusers', edit_mode=edit_mode)
        if edit_mode:
            time_left = 10
            broadcast_handler_dict[message.chat.id] = True
            BROADCAST_MESSAGE = broadcast_event_data[userid]["BROADCAST_MESSAGE"] if userid in broadcast_event_data and "BROADCAST_MESSAGE" in broadcast_event_data[userid] else None
            broadcast_event_data[message.chat.id] = {
                'event_msg': message,
                'event_key': data[1],
                'BROADCAST_MESSAGE': BROADCAST_MESSAGE
            }
            timeout_task = create_task(wait_for_timeout(message.chat.id, time_left))
            iron_update = await client.send_message(chat_id=query.from_user.id, text=f"Hurry Up,\n\nTime Left Is: {time_left}", reply_to_message_id=query.message.id)
            try:
                while broadcast_handler_dict[message.chat.id]:  # Keep checking while it's True
                    await sleep(1)  # Sleep to avoid busy waiting
                    time_left -= 1  # Decrease the time by 1 second
                    # When the loop ends, the time is 0 or handler_dict is False
                    if time_left == 1 and broadcast_handler_dict[message.chat.id] == True:  
                        await edit_message(iron_update, "Oops,\n\nYou are late buddy,\n\nTime Is Up,\n\nPlease Try Again")
                    if time_left % 2 == 0 and broadcast_handler_dict[message.chat.id] == True:  # Update the message every 5 seconds
                        # Update the message with the remaining time                       
                        await edit_message(iron_update, f"Hurry Up,\n\nTime Left Is: {time_left}")
                await update_broadcast_buttons(message, userid=userid, key='addusers')
                if iron_update:
                    await delete_message(iron_update)
            finally:
                timeout_task.cancel()
    elif data[1] == 'skip':
        await query.answer()
        await update_broadcast_buttons(message, userid=userid, key='skip')
    elif data[1] == "add_message":
        await query.answer()
        broadcast_handler_dict[message.chat.id] = False
        edit_mode = len(data) == 4
        await update_broadcast_buttons(message, userid=userid, key='skip', edit_mode=edit_mode)
        if edit_mode:
            time_left = 10
            broadcast_handler_dict[message.chat.id] = True
            EXCEPTION_USERS = broadcast_event_data[userid]["EXCEPTION_USERS"] if userid in broadcast_event_data and "EXCEPTION_USERS" in broadcast_event_data[userid] else None
            broadcast_event_data[message.chat.id] = {
                'event_msg': message,
                'event_key': data[1],
                'EXCEPTION_USERS': EXCEPTION_USERS
            }
            timeout_task = create_task(wait_for_timeout(message.chat.id, time_left))
            iron_update = await client.send_message(chat_id=query.from_user.id, text=f"Hurry Up,\n\nTime Left Is: {time_left}", reply_to_message_id=query.message.id)
            try:
                while broadcast_handler_dict[message.chat.id]:  # Keep checking while it's True
                    await sleep(1)  # Sleep to avoid busy waiting
                    time_left -= 1  # Decrease the time by 1 second
                    # When the loop ends, the time is 0 or handler_dict is False
                    if time_left == 1:  
                        await edit_message(iron_update, "Oops,\n\nYou are late buddy,\n\nTime Is Up,\n\nPlease Try Again")
                    if time_left % 2 == 0:  # Update the message every 5 seconds
                        # Update the message with the remaining time                       
                        await edit_message(iron_update, f"Hurry Up,\n\nTime Left Is: {time_left}")
                await update_broadcast_buttons(message, userid=userid, key='skip')
                if iron_update:
                    await delete_message(iron_update)
            finally:
                timeout_task.cancel()
    elif data[1] == 'cancel' and data[2] == 'users':
        global USERS_BROADCAST_CANCEL 
        USERS_BROADCAST_CANCEL = True

async def users_broadcast(user_id, message, is_pin):
    try:
        await message.copy(chat_id=user_id)
        return True, "Success"
    except FloodWait as e:
        await sleep(e.x)
        return await users_broadcast(user_id, message)
    except InputUserDeactivated:
        await DbManager().rm_pm_user(user_id)
        LOGGER.info(f"user {user_id}-Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        LOGGER.info(f"user {user_id} -Blocked the bot.")
        await DbManager().rm_pm_user(user_id)
        return False, "Blocked"
    except PeerIdInvalid:
        await DbManager().rm_pm_user(user_id)
        LOGGER.info(f"user {user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception as e:
        return False, "Error"

async def broadcast_users(bot, message, userid):
    global USERS_BROADCAST_CANCEL

    if broadcast_lock.locked():
        return await message.reply('Currently broadcasting, please wait for it to complete.')

    buttons = ButtonMaker()
    users = DbManager().get_pm_uids()
    b_msg = broadcast_event_data.get(userid, {}).get('BROADCAST_MESSAGE', None)
    if b_msg is None:
        return await message.reply('No broadcast message found.')

    b_sts = await message.reply_text(text='<b>ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ʏᴏᴜʀ ᴍᴇssᴀɢᴇs ᴛᴏ ᴜsᴇʀs ⌛️</b>')
    start_time = time.time()
    total_users = await DbManager().total_users_count()
    done = 0
    success = 0
    failed = 0
    deactive_user = 0
    block = 0
    ban_users = 0
    async with broadcast_lock:
        async for user_id in users:

            time_taken = get_readable_time(time.time() - start_time)

            if USERS_BROADCAST_CANCEL:
                USERS_BROADCAST_CANCEL = False  # Reset the cancellation flag
                await b_sts.edit(
                    text = (
                        f"User Broadcast Canclled!\n\n"
                        f"Total Users: {total_users}\n"
                        f"Compeletd Users: {done}\n"
                        f"Success users: {success}\n"
                        f"Failed users: {failed}\n"
                        f"Deactive users: {deactive_user}\n"
                        f"Blocked users: {block}\n"
                        f"Ban Users: {ban_users}"
                    )
                )
                return

            try:
                ban_user = broadcast_event_data.get(userid, {}).get('EXCEPTION_USERS', None)
                if ban_user is not None and str(user_id) in ban_user:
                    ban_users += 1
                    continue
                iron, broadcast = await users_broadcast(user_id, b_msg, False)
                if broadcast == 'Success':
                    success += 1
                elif broadcast == 'Error':
                    failed += 1
                elif broadcast == 'Deleted':
                    deactive_user += 1
                elif broadcast == 'Blocked':
                    block += 1
            except Exception as e:
                LOGGER.error(f"Error broadcasting to user {user_id}: {e}")
                failed += 1

            done += 1

            if done % 20 == 0:
                btn = [[
                    InlineKeyboardButton('CANCEL', callback_data=f'broadcast cancel users {userid}')
                ]]
                await b_sts.edit(
                    text=(
                        f"User Broadcast Progress..\n\n"
                        f"Total Users: {total_users}\n"
                        f"Compeletd Users: {done}\n"
                        f"Success users: {success}\n"
                        f"Failed users: {failed}\n"
                        f"Deactive users: {deactive_user}\n"
                        f"Blocked users: {block}\n"
                        f"Ban Users: {ban_users}"
                    ), 
                    reply_markup=InlineKeyboardMarkup(btn)
                )

        time_taken = get_readable_time(time.time() - start_time)
        await b_sts.edit(
            text=(
                f"User Broadcast Completed\n\n"
                f"Total Users: {total_users}\n"
                f"Compeletd Users: {done}\n"
                f"Success users: {success}\n"
                f"Failed users: {failed}\n"
                f"Deactive users: {deactive_user}\n"
                f"Blocked users: {block}\n"
                f"Ban Users: {ban_users}"
            )
        )


async def broadcast(_, message):
    if message.text:
        b_msg = message.text.split(" ", 1)
       
        if message.reply_to_message:
            # Ensure the user's entry exists in broadcast_event_data
            user_id = message.from_user.id
            if user_id not in broadcast_event_data:
                broadcast_event_data[user_id] = {}
            BROADCAST_MESSAGE = message.reply_to_message
            broadcast_event_data[user_id]["BROADCAST_MESSAGE"] = BROADCAST_MESSAGE
        elif len(b_msg) == 2:
            alt_b = await send_message(message, "Please reply to a message or just send /broadcast command and set a broadcast message in funcation directly to broadcast.")
            await one_minute_del(alt_b)
            return
    msg, button = await get_broadcast_button(userid=message.from_user.id)
    await send_message(message, msg, button)


bot.add_handler(
    MessageHandler(
        broadcast, filters= command(BotCommands.BroadcastCommand)
    )
)
bot.add_handler(
    CallbackQueryHandler(
        broadcast_callback_handler, filters=regex("^broadcast") 
    )
)
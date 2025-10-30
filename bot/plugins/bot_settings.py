from io import BytesIO
import asyncio
from collections import OrderedDict
from pyrogram.enums import ChatType
from pyrogram.filters import regex, command, private
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import (
    LOGGER,
    DATABASE_URL,
    bot,
    config_dict,
    handler_dict,
    validate_and_format_url
)

from bot.helper.extra.bot_utils import (
    new_thread,
    chnl_check,
    check_bot_connection
)
from bot.database.db_handler import DbManager

from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    sendFile,
    edit_message,
    send_message,
    delete_message
)
from bot.plugins.join_req_fsub import initialize_auth_channels, add_handlers
from bot.helper.extra.help_string import *


START = 0
STATE = "view"
event_data = {}

default_values = {
    "PORT": 8080,
    "ALRT_TXT":  IRON_ALRT_TXT,
    "AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT": 300,
    "AUTO_FILE_DELETE_MODE_TIMEOUT": 300,
    'CHK_MOV_ALRT': IRON_CHK_MOV_ALRT,
    "START_TEXT": IRON_START_TEXT,
    "RESULT_TEXT": IRON_RESULT_TEXT,
    "CUSTOM_FILE_CAPTION": IRON_CUSTOM_FILE_CAPTION,
    "IMDB_TEMPLATE_TXT": IRON_IMDB_TEMPLATE_TXT,
    "FILE_NOT_FOUND": IRON_FILE_NOT_FOUND,
    "OLD_ALRT_TXT": IRON_OLD_ALRT_TXT,
    "NORSLTS": IRON_NORSLTS,
    "MOV_NT_FND": IRON_MOV_NT_FND,
    "DISCLAIMER_TXT": IRON_DISCLAIMER_TXT,
    "SOURCE_TXT": IRON_SOURCE_TXT,
    "HELP_TXT": IRON_HELP_TXT,
    "ABOUT_TEXT": IRON_ABOUT_TEXT
}
bool_vars = [
    "USE_CAPTION_FILTER",
    "LONG_IMDB_DESCRIPTION",
    "NO_RESULTS_MSG",
    "SET_COMMANDS",
    "USENEWINVTLINKS",
    "REQ_JOIN_FSUB",
    "AUTO_FILE_DELETE_MODE",
    "IMDB_RESULT",
    "FILE_SECURE_MODE"
]

digit_vars = [
    "LOG_CHANNEL",
    "AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT",
    "AUTO_FILE_DELETE_MODE_TIMEOUT",
    "OWNER_ID",
    "TOKEN_TIMEOUT"
]

dev_vars = [
    "OWNER_ID",
    "USER_SESSION_STRING",
    "TELEGRAM_HASH",
    "TELEGRAM_API",
    "DATABASE_URL",
    "BOT_TOKEN",
    "PORT"
]

bset_display_dict = {
    "AUTO_FILE_DELETE_MODE": "Set to true if you want the bot to automatically delete the given file after the specified time; otherwise, set it to false.\n\n⚠️ NOTE: This command will not work if FILE_SECURE_MODE is true. If you want to use this mode, set it to true, then go back and set FILE_SECURE_MODE to false.",
    "BOT_TOKEN" : "get bot token from @BotFather",
    "DATABASE_URL": "Your mongodb databse url with password added",
    "FILE_SECURE_MODE": "Set to true if you want to restrict file handling to forward files only; otherwise, set it to false.\n\n⚠️ NOTE: If you set this to true, the AUTO_FILE_DELETE_MODE will not work, even if AUTO_FILE_DELETE_MODE is set to true.",
    "TELEGRAM_API": "This is to authenticate your Telegram account for downloading Telegram files. You can get this from https://my.telegram.org.",
    "TELEGRAM_HASH": "This is to authenticate your Telegram account for downloading Telegram files. You can get this from https://my.telegram.org.",
    "OWNER_ID": "Your user id, add only one id.",
    "RESULT_TEXT": "This text show on result when IMDB_RESULT False\n\nAdd only this variable in your text query, user_id, user_first_name, user_last_name, user_mention, query_total_results like this USER_ID: {user_id}",
    "SHORT_URL_API": "add you short domin and api, you can add multiple shortner sites like this domain:apikey, domain:apikey\nExample: <code>ironxyz.com:nfu4r84hd3487yr73h4ed7,instaearn.in:nu43h7hfe84dh348</code>\nDont Forgot to add TOKEN_TIMOUT, otherwise this not work",
}

async def get_buttons(key=None, edit_type=None, edit_mode=None, mess=None):
    buttons = ButtonMaker()
    if key is None:
        buttons.callback("Config Variables", "botset var")
        buttons.callback("Close", "botset close")
        msg = "Bot Settings:"
    elif key == "var":
        for k in list(OrderedDict(sorted(config_dict.items())).keys())[
            START : 10 + START
        ]:
            buttons.callback(k, f"botset editvar {k}")
        buttons.callback("Back", "botset back")
        buttons.callback("Close", "botset close")
        for x in range(0, len(config_dict) - 1, 10):
            buttons.callback(
                f"{int(x/10)+1}", f"botset start var {x}", position="footer"
            )
        msg = f"<b>Config Variables<b> | Page: {int(START/10)+1}"
    elif key == "private":
        buttons.callback("Back", "botset back")
        buttons.callback("Close", "botset close")
        msg = "Send private files: config.env, token.pickle, cookies.txt, accounts.zip, terabox.txt, .netrc, or any other files!\n\nTo delete a private file, send only the file name as a text message.\n\n<b>Please note:</b> Changes to .netrc will not take effect for aria2c until it's restarted.\n\n<b>Timeout:</b> 60 seconds"
    elif edit_type == "editvar":
        msg = f"<b>Variable:</b> <code>{key}</code>\n\n"
        msg += f'<b>Description:</b> {bset_display_dict.get(key, "No Description Provided")}\n\n'
        if mess.chat.type == ChatType.PRIVATE:
            msg += f'<b>Value:</b> <code>{config_dict.get(key, "None")}</code>\n\n'
        elif key not in bool_vars:
            buttons.callback(
                "View value", f"botset showvar {key}", position="header"
            )
        buttons.callback("Back", "botset back var", position="footer")
        if key not in bool_vars and key not in dev_vars:
            if not edit_mode:
                buttons.callback("Edit Value", f"botset editvar {key} edit")
            else:
                buttons.callback("Stop Edit", f"botset editvar {key}")
        if (
            key not in dev_vars
            and key not in bool_vars
        ):
            buttons.callback("Reset", f"botset resetvar {key}")
        buttons.callback("Close", "botset close", position="footer")
        if edit_mode and key in [
            "CMD_SUFFIX",
            "DATABASE_CHANNEL"
        ]:
            msg += "<b>Note:</b> Restart required for this edit to take effect!\n\n"
        if edit_mode and key not in bool_vars:
            msg += "Send a valid value for the above Var. <b>Timeout:</b> 60 sec"
        if key in bool_vars:
            if not config_dict.get(key):
                buttons.callback("Make it True", f"botset boolvar {key} on")
            else:
                buttons.callback("Make it False", f"botset boolvar {key} off")
        if key in dev_vars:
            msg += "<b>Note:</b> Sorry but you are not able to change this var, my developer still working on it, so wait for update.\n\n"
    button = buttons.column(1) if key is None else buttons.column(2)
    return msg, button

async def update_buttons(message, key=None, edit_type=None, edit_mode=None):
    msg, button = await get_buttons(key, edit_type, edit_mode, message)
    await edit_message(message, msg, button)


async def update_variable(message):
    value = message.text
    chat_id = message.from_user.id
    if chat_id in event_data and event_data[chat_id] is not None:
        if 'event_key' in event_data[chat_id] and event_data[chat_id]['event_key'] is not None:
            key = event_data[chat_id]["event_key"]
            initial_message = event_data[chat_id]["event_msg"]
            action = event_data[chat_id]['event_action']
            try:
                if key in digit_vars:
                    value = int(value)
                elif key == 'BOT_BASE_URL':
                    # Log the incoming value
                    LOGGER.info(f"Received BOT_BASE_URL value: {value}")
                    
                    is_valid, url = validate_and_format_url(value)
                    if not is_valid:
                        LOGGER.error(f"URL Invalid error when updating key: {key} value: {value}")
                        await update_buttons(initial_message, key, 'editvar', False)
                        handler_dict[chat_id] = False
                        event_data[chat_id] = None
                        alert = await send_message(message, "URL is invalid, please check the URL again.")
                        await asyncio.sleep(4)
                        await delete_message(alert)
                        return
                    else:
                        # Log the formatted URL
                        LOGGER.info(f"Formatted BOT_BASE_URL: {url}")
                        
                        is_connect = await check_bot_connection(url)
                        if not is_connect:
                            LOGGER.error(f"Connection error when updating key: {key} value: {value}")
                            await update_buttons(initial_message, key, 'editvar', False)
                            handler_dict[chat_id] = False
                            event_data[chat_id] = None
                            alert = await send_message(message, "Not able to connect with this URL\n\nPlease verify the URL again.")
                            await asyncio.sleep(4)
                            await delete_message(alert)
                            return
                        else:
                            LOGGER.info(f"Successfully connected to {url}")
                if DATABASE_URL:
                    await DbManager().update_config({key: value})
                config_dict[key] = value
                await delete_message(message)
                LOGGER.info(f"Updating key: {key} with value: {value}")
                await update_buttons(initial_message, key, 'editvar', False)
                handler_dict[chat_id] = False
                event_data[chat_id] = None
                if key == 'FSUB_IDS':
                    # Re-initialize channels and add handlers after updating
                    await chnl_check(FSUB=True, send_error=True)
                    initialize_auth_channels()
                    add_handlers()
            except Exception as e:
                LOGGER.error(f"Error updating database or buttons: {e}")


async def wait_for_timeout(chat_id, timeout_duration, event_data):
    try:
        await asyncio.sleep(timeout_duration)
        # If we reach here, the timeout has occurred
        handler_dict[chat_id] = False
    except asyncio.CancelledError:
        # This exception is raised if the task is cancelled
        pass

@new_thread
async def edit_bot_settings(client, query):
    data = query.data.split()
    message = query.message
    if data[1] == "close":
        handler_dict[message.chat.id] = False
        await query.answer()
        await delete_message(message)
        await delete_message(message.reply_to_message)
    elif data[1] == "back":
        handler_dict[message.chat.id] = False
        await query.answer()
        key = data[2] if len(data) == 3 else None
        if key is None:
            globals()["START"] = 0
        await update_buttons(message, key)
    elif data[1] == "var":
        await query.answer()
        await update_buttons(message, data[1])
    elif data[1] == "resetvar":
        handler_dict[message.chat.id] = False
        await query.answer("Reset done!", show_alert=True)
        value = ""
        if data[2] in default_values:
            value = default_values[data[2]]
        config_dict[data[2]] = value
        await update_buttons(message, data[2], "editvar", False)
        if DATABASE_URL:
            await DbManager().update_config({data[2]: value})
    elif data[1] == "boolvar":
        handler_dict[message.chat.id] = False
        value = data[3] == "on"
        await query.answer(
            f"Successfully variable	 changed to {value}!", show_alert=True
        )
        print(f"value: {value}{type(value)}")
        config_dict[data[2]] = value
        await update_buttons(message, data[2], "editvar", False)
        if DATABASE_URL:
            await DbManager().update_config({data[2]: value})
    elif data[1] == "editvar":
        handler_dict[message.chat.id] = False
        edit_mode = len(data) == 4
        await update_buttons(message, data[2], data[1], edit_mode)
        
        if data[2] in bool_vars or not edit_mode:
            return
        
        if edit_mode:
            handler_dict[message.chat.id] = True 
            # Prepare button data to pass to the timeout function
            event_data[message.chat.id] = {
                'event_msg': message,
                'event_key': data[2],
                'event_action': data[1]
            }
            # Create a task for the timeout
            timeout_task = asyncio.create_task(wait_for_timeout(message.chat.id, 60, event_data))
            iron_update = await client.send_message(chat_id=query.from_user.id, text="Hurry Up,\n\nTime Left Is: 60", reply_to_message_id=query.message.id)
            try:
                time_left = 60
                while handler_dict[message.chat.id]:  # Keep checking while it's True
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
                await update_buttons(message, data[2], 'editvar', False)  # Exit edit mode
                event_data[message.chat.id] = None  # Clean up event data
            finally:
                timeout_task.cancel()
    elif data[1] == "showvar":
        value = config_dict[data[2]]
        if len(str(value)) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await sendFile(message, out_file)
            return
        if value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "edit":
        await query.answer()
        globals()["STATE"] = "edit"
        await update_buttons(message, data[2])
    elif data[1] == "view":
        await query.answer()
        globals()["STATE"] = "view"
        await update_buttons(message, data[2])
    elif data[1] == "start":
        await query.answer()
        if int(data[3]) != START:
            globals()["START"] = int(data[3])
            await update_buttons(message, data[2])


async def bot_settings(_, message):
    msg, button = await get_buttons()
    globals()["START"] = 0
    await send_message(message, msg, button)


bot.add_handler(
    MessageHandler(
        bot_settings, filters= private & command(BotCommands.BotSetCommand) & CustomFilters.sudo
    )
)
bot.add_handler(
    CallbackQueryHandler(
        edit_bot_settings, filters=regex(r"^botset") & CustomFilters.sudo
    ), group = -1
)

from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import *
from pyrogram.types import CallbackQuery  # Ensure CallbackQuery is imported

from bot.database.db_handler import DbManager
from bot.helper.telegram_helper.message_utils import send_message, edit_message, delete_message
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot import (
    user_handler_dict,
    bot,
    user_data,
    DATABASE_URL,
    LOGGER,
    config_dict
)

# Use a dictionary to store the START value for each user
user_start_dict = {}

async def get_user_settings_buttons(from_user, key=None):
    button = ButtonMaker()
    text = 'error'
    user_id = from_user.id
    user_lang = user_data.get(user_id, {}).get("LANGUAGE", None)
    user_lang = user_lang.lower() if user_lang is not None else None
    user_qual = user_data.get(user_id, {}).get("QUALITY", None)
    user_qual = user_qual.lower() if user_qual is not None else None
    user_imdb = user_data.get(user_id, {}).get("IMDB", None)
    user_imdb = user_imdb.lower() if user_imdb is not None else None
    user_file_type = user_data.get(user_id, {}).get("FILE_TYPE", None)
    user_file_type = user_file_type.lower() if user_file_type is not None else None
    try:
        if user_lang is None or user_qual is None or user_imdb is None:
            user_dbdata = await DbManager().get_user_data(user_id)

            if user_lang is None:
                user_lang = 'Not Set'
                if user_dbdata.get('LANGUAGE', None) is not None:
                    user_lang = user_dbdata['LANGUAGE']
            if user_qual is None:
                user_qual = 'Not Set'
                if user_dbdata.get('QUALITY', None) is not None:
                    user_qual = user_dbdata['QUALITY']
            if user_imdb is None:
                user_imdb = 'Not Set'
                if user_dbdata.get('IMDB', None) is not None:
                    user_imdb = user_dbdata['IMDB']
            if user_file_type is None:
                user_file_type = 'Not Set'
                if user_dbdata.get('FILE_TYPE', None) is not None:
                    user_file_type = user_dbdata['FILE_TYPE']
    except Exception as e:
        LOGGER.error(f"Error while handling user_data: {e}")
    if key is None:
        text = (
            "<b>USER SETTINGS:</b>\n\n"
            f"<b>Name: {from_user.first_name}\n</b>"
            f"<b>Username: @{from_user.username}\n</b>"
            f"<b>USER ID: {user_id}\n\n</b>"
            "Please Select Below Button to Update your Settings"
        )

        button.callback(f"{'✔️' if user_lang != 'Not Set' else ''} Files Language", f"userset {user_id} flang", position="header")
        button.callback(f"{'✔️' if user_qual != 'Not Set' else ''} Files Quality", f"userset {user_id} fqual", position="header")
        button.callback(f"{'✔️' if user_imdb != 'Not Set' else ''} IMDB", f"userset {user_id} imdb", position='header')
        button.callback(f"{'✔️' if user_file_type != 'Not Set' else ''} Files Type", f"userset {user_id} ftype", position='header')

        if user_lang is not None or user_qual is not None:
            button.callback("♻️ ʀᴇꜱᴇᴛ ᴀʟʟ ꜱᴇᴛᴛɪɴɢꜱ ♻️", f"userset {user_id} reset all", position='extra')
        button.callback("❌ ᴄʟᴏꜱᴇ ❌", f"userset {user_id} close", position='footer')

        buttons = button.column(header_columns=2)
    elif key == 'flang':
        start_index = user_start_dict.get(user_id, 0)
        end_index = start_index + 10 # Assuming 10 items per page
        text = (
            f"<b>USER LANGUAGE SETTINGS:</b>\n\n"
            f"<b>Name:</b> {from_user.first_name}\n"
            f"<b>Username:</b> @{from_user.username}\n"
            f"<b>USER ID:</b> {user_id}\n"
            f"<b>Language:</b> {user_lang}\n\n"
            f"<b>Select Your Language By Click Below Buttons</b> | <b>Page:</b> {int(start_index / 10) + 1}"
        )

        iron_languages = ["Hindi", "English", "Gujarati", "Tamil", "Telugu", 'Marathi', "Punjabi", "Bengali", "Kannada", "German", "Chinese", "Japanese", 'Spanish']

        # Add language buttons for the current page
        for language in iron_languages[start_index:end_index]:
            button.callback(f"{'✔️' if user_lang == language.lower() else ''}{language}", f"userset {user_id} flang {language.lower()} edit", position='header')
        
        button.callback("♻️ ʀᴇꜱᴇᴛ ʟᴀɴɢᴜᴀɢᴇ ♻️", f"userset {user_id} reset flang", position='extra')

        button.callback("⋞ ʙᴀᴄᴋ", f"userset {user_id} back") 
        button.callback("ᴄʟᴏꜱᴇ ❌", f"userset {user_id} close")

        if len(iron_languages) > 10:
            # Pagination buttons
            for x in range(0, len(iron_languages), 10):
                button.callback(
                    f"{int(x / 10) + 1}", f"userset {user_id} start flang {x}", position="footer"
                )

        buttons = button.column(main_columns=2, header_columns=2, footer_columns=8)
    
    elif key == 'fqual':
        # Determine the start index for pagination
        text = (
            f"<b>USER QUALITY SETTINGS:</b>\n\n"
            f"<b>Name:</b> {from_user.first_name}\n"
            f"<b>Username:</b> @{from_user.username}\n"
            f"<b>USER ID:</b> {user_id}\n"
            f"<b>QUALITY:</b> {user_qual}\n"
            f"<b>Select Your Quality By Click Below Buttons</b>"
        )

        iron_qualities = ["360p", "480p", "720p", "1080p", "1440p", "2160p"]

        # Add quality buttons for the current page
        for quality in iron_qualities:
            button.callback(f"{'✔️ ' if user_qual == quality.lower() else ''}{quality}", f"userset {user_id} fqual {quality.lower()} edit", position='header')

        button.callback("♻️ ʀᴇꜱᴇᴛ Qᴜᴀʟɪᴛʏ ♻️", f"userset {user_id} reset fqual", position='extra')
        
        button.callback("⋞ ʙᴀᴄᴋ", f"userset {user_id} back") 
        button.callback("ᴄʟᴏꜱᴇ ❌", f"userset {user_id} close")
        
        if len(iron_qualities) > 10:
            # Pagination buttons
            for x in range(0, len(iron_qualities) - 1, 10):
                button.callback(
                    f"{int(x/10)+1}", f"userset {user_id} start fqual {x}", position="footer"
                )
        
        buttons = button.column(main_columns=2, header_columns=2, footer_columns=8)
    elif key == 'ftype':
        text = (
            f"<b>USER FILE TYPE SETTINGS:</b>\n\n"
            f"<b>Name:</b> {from_user.first_name}\n"
            f"<b>Username:</b> @{from_user.username}\n"
            f"<b>USER ID:</b> {user_id}\n"
            f"<b>FILE TYPE:</b> {user_file_type}\n"
            f"<b>Select Your File Type By Click Below Buttons</b>"
        )

        file_types = ["ᴠɪᴅᴇᴏ", "ᴅᴏᴄᴜᴍᴇɴᴛ", "ᴀᴜᴅɪᴏ"]

        # Add quality buttons for the current page
        for file_type in file_types:
            if file_type == 'ᴠɪᴅᴇᴏ':
                cfile_type = "Video"
            if file_type == 'ᴅᴏᴄᴜᴍᴇɴᴛ':
                cfile_type = "Document"
            if file_type == 'ᴀᴜᴅɪᴏ':
                cfile_type = "Audio"
            button.callback(f"{'✔️ ' if user_file_type == cfile_type.lower() else ''}{file_type}", f"userset {user_id} ftype {cfile_type.lower()} edit", position='header')
        
        button.callback("♻️ ʀᴇꜱᴇᴛ Qᴜᴀʟɪᴛʏ ♻️", f"userset {user_id} reset ftype", position='extra')
        
        button.callback("⋞ ʙᴀᴄᴋ", f"userset {user_id} back", position='footer') 
        button.callback("ᴄʟᴏꜱᴇ ❌", f"userset {user_id} close", position='footer')
        
        
        buttons = button.column(header_columns=3)
    
    elif key == 'imdb':
        text = (
            f"<b>USER IMDB SETTINGS:</b>\n\n"
            f"<b>Name:</b> {from_user.first_name}\n"
            f"<b>Username:</b> @{from_user.username}\n"
            f"<b>USER ID:</b> {user_id}\n"
            f"<b>IMDB:</b> {user_imdb if user_imdb != 'Not Set' else config_dict['IMDB_RESULT']}\n\n"
            f"<b>Make True if you want IMDB template on your query result</b>"
        )
        
        if user_imdb == 'Not Set' and not config_dict['IMDB_RESULT']:
            button.callback("Make It True", f"userset {user_id} imdb on", position="header")
        elif user_imdb == 'Not Set' and config_dict['IMDB_RESULT']:
            button.callback("Make It False", f"userset {user_id} imdb off", position="header")
        elif user_imdb == 'true':
            button.callback("Make It False", f"userset {user_id} imdb off", position="header")
        elif user_imdb == 'false':
            button.callback("Make It True", f"userset {user_id} imdb on", position="header")

        button.callback("⋞ ʙᴀᴄᴋ", f"userset {user_id} back", position='footer') 
        button.callback("ᴄʟᴏꜱᴇ ❌", f"userset {user_id} close", position='footer')

        buttons = button.column()

    return text, buttons

async def update_user_settings(query, key=None):
    text, buttons = await get_user_settings_buttons(query.from_user, key)
    await edit_message(query.message, text, buttons)

async def update_user_variable(user_id, key, value):
    try:
        value = value
        user_data[user_id] = user_data.get(user_id, {})  # Initialize if not present
        user_data[user_id][key] = value
        if DATABASE_URL:
            user_dbdata= await DbManager().get_user_data(user_id)
            user_value = user_dbdata.get(key, None)
            if user_value != value:
                await DbManager().update_config({key: value}, user_id)
                LOGGER.info(f"Update config for user: {user_id} with key: {key} and value: {value}")      
    except Exception as e:
        LOGGER.error(f"Error while update_user_variable: {e}")
        

async def edit_user_settings(client, query: CallbackQuery):
    from_user = query.from_user
    user_id = from_user.id
    data = query.data.split()
    
    if len(data) < 3 or user_id != int(data[1]):
        await query.answer("Not Yours!", show_alert=True)
        return
    
    try:
        if data[2] == 'flang':
            await query.answer()
            if len(data) == 5 and data[-1] == 'edit':
                await update_user_variable(user_id, 'LANGUAGE', data[3])
                return await update_user_settings(query, data[2])
            await update_user_settings(query, data[2])
        elif data[2] == 'fqual':
            await query.answer()
            if len(data) == 5 and data[-1] == 'edit':
                await update_user_variable(user_id, 'QUALITY', data[3])
                return await update_user_settings(query, data[2])
            await update_user_settings(query, data[2])
        elif data[2] == 'ftype':
            await query.answer()
            if len(data) == 5 and data[-1] == 'edit':
                await update_user_variable(user_id, 'FILE_TYPE', data[3])
                return await update_user_settings(query, data[2])
            await update_user_settings(query, data[2])
        elif data[2] == 'back':
            await query.answer()
            user_handler_dict[user_id] = False
            setting = data[3] if len(data) == 4 else None
            await update_user_settings(query, setting)
        elif data[2] == "start":
            await query.answer()
            # Update the user's start index for pagination
            if user_id not in user_start_dict:
                user_start_dict[user_id] = 0
            if int(data[4]) != user_start_dict[user_id]:
                user_start_dict[user_id] = int(data[4])
                await update_user_settings(query, key=data[3])
        elif data[2] == 'reset':
            if data[3] == 'all':
                await query.answer("Reset all your settings", show_alert=True)
                for key in ['LANGUAGE', 'QUALITY', "IMDB", "FILE_TYPE"]:
                    await update_user_variable(user_id, key, None)
                await update_user_settings(query, None)
            elif data[3] == 'flang':
                await query.answer("Reset your language setting", show_alert=True)
                await update_user_variable(user_id, 'LANGUAGE', None)
                await update_user_settings(query, data[3])
            elif data[3] == 'fqual':
                await query.answer("Reset your quality setting", show_alert=True)
                await update_user_variable(user_id, 'QUALITY', None)
                await update_user_settings(query, data[3])
            elif data[3] == 'ftype':
                await query.answer("Reset your file type setting", show_alert=True)
                await update_user_variable(user_id, 'FILE_TYPE', None)
                await update_user_settings(query, data[3])
        elif data[2] == 'imdb':
            if len(data) == 4 and data[3] == 'on':
                await query.answer('Turn on you imdb result', show_alert=True)
                await update_user_variable(user_id, 'IMDB', 'true')
                await update_user_settings(query, data[2])
                return
            elif len(data) == 4 and data[3] == 'off':
                await query.answer('Turn off you imdb result', show_alert=True)
                await update_user_variable(user_id, 'IMDB', 'false')
                await update_user_settings(query, data[2])
                return
            await query.answer()
            await update_user_settings(query, data[2])
        elif data[2] == "close":
            user_handler_dict[user_id] = False
            await delete_message(query.message)
            await delete_message(query.message.reply_to_message)
    except Exception as e:
        LOGGER.error(f"Error while handler user_setting: {e}")

async def user_settings(client, message):
    from_user = message.from_user
    text, buttons = await get_user_settings_buttons(from_user)
    await send_message(message, text=text, buttons=buttons)

bot.add_handler(
    MessageHandler(
        user_settings, filters=command(BotCommands.UserSetCommands)
    )
)
bot.add_handler(
    CallbackQueryHandler(
        edit_user_settings, filters= regex("^userset")
    ), group=-1
)

import os, asyncio, contextlib, socket, subprocess, requests, sys
from requests.exceptions import ConnectionError, Timeout, RequestException
from pathlib import Path
from os import execl as osexecl
from sys import executable
from asyncio import gather, create_subprocess_exec
from pyrogram.enums import ChatType
from pyrogram.filters import command, regex
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from time import time
from uuid import uuid4
from html import escape
from aiohttp import web
from aiofiles import open as aiopen
from aiofiles.os import path as aiopath, remove as aioremove
from bot import (
    bot, 
    scheduler,
    LOGGER, 
    PORT as PORT_CODE, 
    bot_name, 
    bot_start_time,
    HOSTING_SERVER,
    is_indexing_active,
    config_dict,
    user_data,
    DATABASE_URL,
    validate_and_format_url
)

from bot.plugins.commands import normal_user_start_cmd, start_file_sender, authorize_user_start_cmd
from psutil import boot_time, disk_usage, cpu_percent, virtual_memory

from bot.database.db_handler import DbManager
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.extra.bot_utils import (
    new_task, 
    new_thread, 
    get_readable_file_size, 
    get_readable_time,
    set_commands,
    chnl_check,
    check_bot_connection,
    cleanup_downloads
)
from bot.helper.extra.telegraph_helper import telegraph
from bot.helper.telegram_helper.message_utils import (
    edit_message, 
    sendFile, 
    delete_message, 
    five_minute_del, 
    send_message, 
    one_minute_del
)
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.plugins import (
    authorize,
    autofilter,
    bot_settings,
    commands,
    database_channel,
    index,
    join_req_fsub,
    delete_dbfiles,
    route,
    user_settings,
    broadcast,
    web_server,
    listerner
)


help_string = f"""<b>NOTE: Try each command without any arguments to see more details.</b>

<blockquote expandable>
/{BotCommands.StartCommand[0]} - Checking bot Online
/{BotCommands.IndexCommand[0]} - for indexing files
/{BotCommands.LogCommand[0]} - get log.txt file
/{BotCommands.StatsCommand[0]} - Display machine stats hosting the bot.</blockquote>
"""


@new_thread
async def stats(_, message):
    total, used, free, disk = disk_usage("/")
    memory = virtual_memory()
    current_time = get_readable_time(time() - bot_start_time)
    os_uptime = get_readable_time(time() - boot_time())
    cpu_usage = cpu_percent(interval=0.5)
    system_info = (
        f"<code>• Bot uptime :</code> {current_time}\n"
        f"<code>• Sys uptime :</code> {os_uptime}\n"
        f"<code>• CPU usage  :</code> {cpu_usage}%\n"
        f"<code>• RAM usage  :</code> {memory.percent}%\n"
        f"<code>• Disk usage :</code> {disk}%\n"
        f"<code>• Free space :</code> {get_readable_file_size(free)}\n"
        f"<code>• Total space:</code> {get_readable_file_size(total)}\n\n"
    )
    
    stats = system_info

    reply_message = await send_message(message, stats, photo="Random")
    await delete_message(message)
    await one_minute_del(reply_message)

@new_task
async def iron_callback(_, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != int(data[1]):
        return await query.answer(text="This message not your's!", show_alert=True)
    if data[2] == "logdisplay":
        await query.answer()
        async with aiopen("log.txt") as f:
            log_file_lines = (await f.read()).splitlines()

        def parseline(line):
            try:
                return "[" + line.split("] [", 1)[1]
            except IndexError:
                return line

        ind, log_lines = 1, ""
        try:
            while len(log_lines) <= 3500:
                log_lines = parseline(log_file_lines[-ind]) + "\n" + log_lines
                if ind == len(log_file_lines):
                    break
                ind += 1
            start_line = "<pre language='python'>"
            end_line = "</pre>"
            btn = ButtonMaker()
            btn.callback("Close", f"iron {user_id} close")
            reply_message = await send_message(
                message, start_line + escape(log_lines) + end_line, btn.column(1)
            )
            await query.edit_message_reply_markup(None)
            await delete_message(message)
            await five_minute_del(reply_message)
        except Exception as err:
            LOGGER.error(f"TG Log Display : {err!s}")
    elif data[2] == "private":
        await delete_message(query.message)
        await query.answer(url=f"https://t.me/{bot_name}?start=private")
        return None
    else:
        await query.answer()
        await delete_message(message)
        return None

@new_task
async def bot_help(_, message):
    reply_message = await send_message(message, help_string)
    await delete_message(message)
    await one_minute_del(reply_message)

@new_task
async def log(_, message):
    buttons = ButtonMaker()
    buttons.callback("Log display", f"iron {message.from_user.id} logdisplay")
    if config_dict['BOT_BASE_URL']:
        reply_message = await sendFile(message, "log.txt", caption=f"{config_dict['BOT_BASE_URL']}logs", buttons=buttons.column(1))
    else:
        reply_message = await sendFile(message, "log.txt", buttons=buttons.column(1))
    await delete_message(message)
    await five_minute_del(reply_message)

@new_task
async def start(client, message):
    if message.chat.type in [ChatType.SUPERGROUP, ChatType.GROUP]:
        i = await send_message(message, "I am alive! just send a name of query, i will find for you.")
        await asyncio.sleep(5)
        await delete_message(i)
        return 
    elif len(message.command) > 1 and len(message.command[1]) == 36:
        userid = message.from_user.id
        input_token = message.command[1]
        if DATABASE_URL:
            stored_token = await DbManager().get_user_token(userid)
            if stored_token is None:
                return await send_message(
                    message,
                    "<b>This token is not for you!</b>\n\nPlease generate your own.",
                )
            if input_token != stored_token:
                return await send_message(
                    message, "Invalid token.\n\nPlease generate a new one."
                )
        if userid not in user_data:
            return await send_message(
                message, "This token is not yours!\n\nKindly generate your own."
            )
        data = user_data[userid]
        if "token" not in data or data["token"] != input_token:
            return await send_message(
                message,
                "<b>This token has already been used!</b>\n\nPlease get a new one.",
            )
        token = str(uuid4())
        token_time = time()
        data["token"] = token
        data["time"] = token_time
        user_data[userid].update(data)
        if DATABASE_URL:
            await DbManager().update_user_tdata(userid, token, token_time)
        msg = "Your token has been successfully generated!\n\n"
        msg += f'It will be valid for {get_readable_time(int(config_dict["TOKEN_TIMEOUT"]), True)}'
        return await send_message(message, msg)
    if len(message.command) > 1 and message.command[1] == "private":
        try:
            # Attempt to update PM users
            result = await DbManager().update_pm_users(message.from_user.id)
            if result is not None and result is not False:
                await send_message(message, "Now you are registered to use me. You can continue to use me.")
            elif result is False:
                await send_message(message, "You are already registered to use me.")
            else:
                await send_message(message, f"You are not registered due to: {e}")
        except Exception as e:
            await send_message(message, f"You are not registered due to: {e}")
    elif await CustomFilters.authorized(client, message):
        await authorize_user_start_cmd(client, message)
    else:
        await normal_user_start_cmd(client, message)
    return None

async def ping(_, message):
    start_time = int(round(time() * 1000))
    reply = await send_message(message, "Starting ping...")
    end_time = int(round(time() * 1000))
    value = end_time - start_time
    await edit_message(reply, f"{value} ms.")
"""
async def load_plugins():
    plugins_folder = "bot.plugins"
    plugins_path = os.path.join(os.path.dirname(__file__), "plugins")
    for filename in os.listdir(plugins_path):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"{plugins_folder}.{filename[:-3]}"
            try:
                importlib.import_module(module_name)
                LOGGER.info(f"Loaded plugin: {module_name}")
            except Exception as e:
                LOGGER.error(f"Error loading plugin {module_name}: {e}")
"""
async def restart_notification():
    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        with contextlib.suppress(Exception):
            await bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id, text="Restarted Successfully!"
            )
        await aioremove(".restartmsg")

async def restart(_, message):
    restart_message = await send_message(message, "Restarting...")
    if scheduler.running:
        scheduler.shutdown(wait=False)
    #await sync_to_async(clean_all)
    proc1 = await create_subprocess_exec(
        "pkill", "-9", "-f", "-e", "gunicorn|xria|xnox|xtra|xone"
    )
    proc2 = await create_subprocess_exec("python3", "update.py")
    await gather(proc1.wait(), proc2.wait())
    async with aiopen(".restartmsg", "w") as f:
        await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    osexecl(executable, executable, "-m", "bot")


    
async def detect_hosting_platform():
    """Detect the hosting platform where the script is running."""
    # Check for Heroku
    if os.getenv("DYNO"):
        return "Heroku"

    # Check for Render
    if os.getenv("RENDER"):
        return "Render"

    # Check for Koyeb
    if os.getenv("KOYEB_APP_ID"):
        return "Koyeb"

    # Check for VPS or bare-metal
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release", "r") as f:
            os_info = f.read().lower()
            if "ubuntu" in os_info or "debian" in os_info or "centos" in os_info:
                return "VPS"

    # Default to local development
    hostname = socket.gethostname()
    if "localhost" in hostname or "local" in hostname:
        return "Localhost"

    return "Unknown Hosting"



# remove load_plugins(),
# Main function to start the bot and the web server
async def main():
    await gather(
        cleanup_downloads(),
        restart_notification(),
        set_commands(bot),
        chnl_check(LOG_CHNL=True, FSUB=True),
        telegraph.create_account()
    )
    global HOSTING_SERVER
    HOSTING_SERVER = await detect_hosting_platform()
    bot.add_handler(MessageHandler(start, filters=command(BotCommands.StartCommand)))
    bot.add_handler(
        MessageHandler(
            log, filters=command(BotCommands.LogCommand) & CustomFilters.sudo
        )
    )
    bot.add_handler(
        MessageHandler(
            restart, filters=command(BotCommands.RestartCommand) & CustomFilters.sudo
        )
    )
    bot.add_handler(
        MessageHandler(
            ping, filters=command(BotCommands.PingCommand) & CustomFilters.authorized
        )
    )
    bot.add_handler(
        MessageHandler(
            bot_help,
            filters=command(BotCommands.HelpCommand) & CustomFilters.authorized,
        )
    )
    bot.add_handler(
        MessageHandler(
            stats,
            filters=command(BotCommands.BotStatsCommand) & CustomFilters.authorized,
        )
    )
    bot.add_handler(CallbackQueryHandler(iron_callback, filters=regex(r"^iron")))
    # Ensure that the chat ID is resolved before sending the message
    # Check for duplicates

    # Send a start message to your Telegram chat (replace with your actual chat ID)
    await bot.send_message(
        chat_id=config_dict['LOG_CHANNEL'], 
        text=f"✅ {bot_name} Bot Started ✅", 
        disable_web_page_preview=True
    )
    
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, host=bind_address, port=PORT_CODE).start()

    LOGGER.info(f"Web server is running on http://0.0.0.0:{PORT_CODE}")

    LOGGER.info("🔍 Checking BOT_BASE_URL...")
    is_valid, url = validate_and_format_url(config_dict['BOT_BASE_URL'])
    if not is_valid:
        LOGGER.error("❌ BOT_BASE_URL is not valid. Exiting!")
        exit(1)
    if not await check_bot_connection(url):
        LOGGER.error("❌ Cannot connect to BOT_BASE_URL.")
    else:
        LOGGER.info("✅ Connected to BOT_BASE_URL!")
    # Keep the server and bot running
    # Log startup message
    LOGGER.info("""
    ██╗  ██╗██╗   ██╗██████╗ ██╗  ██╗██╗   ██╗███████╗
    ██║  ██║██║   ██║██╔══██╗██║  ██║██║   ██║██╔════╝
    ███████║██║   ██║██████╔╝███████║██║   ██║█████╗  
    ██╔══██║██║   ██║██╔══██╗╚════██║╚██╗ ██╔╝██╔══╝  
    ██║  ██║╚██████╔╝██████╔╝     ██║ ╚████╔╝ ██║     
    ╚═╝  ╚═╝ ╚═════╝ ╚═════╝      ╚═╝  ╚═══╝  ╚═╝     
    """)
    LOGGER.info(f"🚀 {bot_name} Bot Started Successfully!")
    LOGGER.info(f"🌍 Running on: \033[1;33m{HOSTING_SERVER}\033[0m")
    while True:
        await asyncio.sleep(3600)  # Keep the server alive for an hour (adjust as needed)

bot.loop.run_until_complete(main())
bot.loop.run_forever()

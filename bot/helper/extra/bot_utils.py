import aiohttp, os, asyncio, shutil
from time import time
from pyrogram.types import BotCommand
from pyrogram.errors import PeerIdInvalid, FloodWait
from pyrogram.enums import ChatMemberStatus, ChatType
from functools import wraps, partial
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from asyncio import (
    sleep,
    create_subprocess_exec,
    create_subprocess_shell,
    run_coroutine_threadsafe,
)

from bot.database.db_handler import DbManager
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot import bot_loop, user_data, config_dict, user_bot, bot, LOGGER, bot_name, DATABASE_URL
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import send_log_message
from .tinyfy import tinyfy
from .shorteners import short_url

THREADPOOL = ThreadPoolExecutor(max_workers=1000)
SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]
STATUS_START = 0

def list_to_str(k):
    if not k:
        return "N/A"
    elif len(k) == 1:
        return str(k[0])
    elif config_dict['MAX_LIST_ELM']:
        k = k[:int(config_dict['MAX_LIST_ELM'])]
        return ' '.join(f'{elem}, ' for elem in k)
    else:
        return ' '.join(f'{elem}, ' for elem in k)

async def sync_to_async(func, *args, wait=True, **kwargs):
    pfunc = partial(func, *args, **kwargs)
    future = bot_loop.run_in_executor(THREADPOOL, pfunc)
    return await future if wait else future

def new_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return bot_loop.create_task(func(*args, **kwargs))

    return wrapper

def new_thread(func):
    @wraps(func)
    def wrapper(*args, wait=False, **kwargs):
        future = run_coroutine_threadsafe(func(*args, **kwargs), bot_loop)
        return future.result() if wait else future

    return wrapper

async def chnl_check(LOG_CHNL=False, FSUB=False, channel_id=None, send_error=False):
    # Check LOG_CHANNEL
    if LOG_CHNL:
        if str(config_dict['LOG_CHANNEL']):
            for chat_id in str(config_dict['LOG_CHANNEL']).split():
                chat_id, *topic_id = chat_id.split(":")
                try:
                    chat = await bot.get_chat(int(chat_id))
                    if chat.type == ChatType.CHANNEL:
                        if not (await chat.get_member(bot.me.id)).privileges.can_post_messages:
                            LOGGER.error(f"Not Connected LOG Chat ID : {chat_id}, Make the Bot is Admin in Channel to Connect!")
                            continue
                        if user_bot and not (await chat.get_member(user_bot.me.id)).privileges.can_post_messages:
                            LOGGER.error(f"Not Connected LOG Chat ID : {chat_id}, Make the User is Admin in Channel to Connect!")
                            continue
                    elif chat.type == ChatType.SUPERGROUP:
                        if not (await chat.get_member(bot.me.id)).status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                            LOGGER.error(f"Not Connected LOG Chat ID : {chat_id}, Make the Bot is Admin in Group to Connect!")
                            continue
                        if user_bot and not (await chat.get_member(user_bot.me.id)).status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                            LOGGER.error(f"Not Connected LOG Chat ID : {chat_id}, Make the User is Admin in Group to Connect!")
                            continue
                    LOGGER.info(f"Connected LOG Chat ID : {chat_id}")
                except Exception as e:
                    LOGGER.error(f"Not Connected LOG Chat ID : {chat_id}, ERROR: {e}")
    if channel_id:
        if str(channel_id):
            IRON_SET = {}
            for chat_id in str(channel_id).split():
                chat_id, *topic_id = chat_id.split(":")
                try:
                    chat = await bot.get_chat(int(chat_id))
                    if chat.type == ChatType.CHANNEL:
                        if not (await chat.get_member(bot.me.id)).privileges.can_post_messages:
                            IRON_SET[chat_id] = False
                            LOGGER.error(f"Not Connected Chat ID : {chat_id}, Make the Bot is Admin in Channel to Connect!")
                            continue
                        if user_bot and not (await chat.get_member(user_bot.me.id)).privileges.can_post_messages:
                            IRON_SET[chat_id] = False
                            LOGGER.error(f"Not Connected Chat ID : {chat_id}, Make the User is Admin in Channel to Connect!")
                            continue
                    elif chat.type == ChatType.SUPERGROUP:
                        if not (await chat.get_member(bot.me.id)).status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                            IRON_SET[chat_id] = False
                            LOGGER.error(f"Not Connected Chat ID : {chat_id}, Make the Bot is Admin in Group to Connect!")
                            continue
                        if user_bot and not (await chat.get_member(user_bot.me.id)).status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                            IRON_SET[chat_id] = False
                            LOGGER.error(f"Not Connected Chat ID : {chat_id}, Make the User is Admin in Group to Connect!")
                            continue
                    LOGGER.info(f"Connected Chat ID : {chat_id}")
                    IRON_SET[chat_id] = True
                except Exception as e:
                    LOGGER.error(f"Not Connected Chat ID : {chat_id}, ERROR: {e}")
                    IRON_SET[chat_id] = False
            return IRON_SET

    # Check FSUB_IDS
    if FSUB:
        if str(config_dict['FSUB_IDS']):
            for fsub_id in str(config_dict['FSUB_IDS']).split():
                try:
                    fsub_chat = await bot.get_chat(int(fsub_id))
                    if fsub_chat.type == ChatType.CHANNEL:
                        if not (await fsub_chat.get_member(bot.me.id)).privileges.can_post_messages:
                            LOGGER.error(f"Not Connected FSub ID : {fsub_id}, Make the Bot is Admin in Channel to Connect!")
                            if send_error:
                                await send_log_message(text=f"Not Connected FSub ID : {fsub_id}, Make the Bot is Admin in Channel to Connect!")
                            continue
                        if not (await fsub_chat.get_member(bot.me.id)).privileges.can_invite_users:
                            LOGGER.error(f"Not Connected FSub ID : {fsub_id}, Make the Bot is Admin in Channel and privilege to invite users to Connect and Create Invite Link.")
                            if send_error:
                                await send_log_message(text=f"Not Connected FSub ID : {fsub_id}, Make the Bot is Admin in Channel and privilege to invite users to Connect and Create Invite Link.")
                            continue
                        if user_bot and not (await fsub_chat.get_member(user_bot.me.id)).privileges.can_post_messages:
                            LOGGER.error(f"Not Connected FSub ID : {fsub_id}, Make the User is Admin in Channel to Connect!")
                            if send_error:
                                await send_log_message(text=f"Not Connected FSub ID : {fsub_id}, Make the User is Admin in Channel to Connect!")
                            continue
                        if user_bot and not (await fsub_chat.get_member(user_bot.me.id)).privileges.can_invite_users:
                            LOGGER.error(f"Not Connected FSub ID : {fsub_id}, Make the User is Admin in Channel and privilege to invite users to Connect and Create Invite Link.")
                            if send_error:
                                await send_log_message(text=f"Not Connected FSub ID : {fsub_id}, Make the User is Admin in Channel and privilege to invite users to Connect and Create Invite Link.")
                            continue
                    elif fsub_chat.type == ChatType.SUPERGROUP:
                        if not (await fsub_chat.get_member(bot.me.id)).status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                            LOGGER.error(f"Not Connected FSub ID : {fsub_id}, Make the Bot is Admin in Group to Connect!")
                            if send_error:
                                await send_log_message(text=f"Not Connected FSub ID : {fsub_id}, Make the Bot is Admin in Group to Connect!")
                            continue
                        if user_bot and not (await fsub_chat.get_member(user_bot.me.id)).status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                            LOGGER.error(f"Not Connected FSub ID : {fsub_id}, Make the User is Admin in Group to Connect!")
                            if send_error:
                                await send_log_message(text=f"Not Connected FSub ID : {fsub_id}, Make the User is Admin in Group to Connect!")
                            continue
                    LOGGER.info(f"Connected FSub ID : {fsub_id}")
                    if send_error:
                        await send_log_message(text=f"Connected FSub ID : {fsub_id}")
                    return
                except PeerIdInvalid as p:
                    LOGGER.error(f"Not Connected FSub ID : {fsub_id}, ERROR: {p}")
                    if send_error:
                        await send_log_message(text=f"Not Connected FSub ID : {fsub_id}, ERROR: {e}\n\nPlease check FSub ID is true or not and if FSub ID is true and still not working then wait for some time, bot will fix this problem automatically.")
                    return
                except Exception as e:
                    LOGGER.error(f"Not Connected FSub ID : {fsub_id}, ERROR: {e}")
                    if send_error:
                        await send_log_message(text=f"Not Connected FSub ID : {fsub_id}, ERROR: {e}")
                    return

def get_readable_time(seconds, full_time=False):
    periods = [
        ("millennium", 31536000000),
        ("century", 3153600000),
        ("decade", 315360000),
        ("year", 31536000),
        ("month", 2592000),
        ("week", 604800),
        ("day", 86400),
        ("hour", 3600),
        ("minute", 60),
        ("second", 1),
    ]
    result = ""
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            plural_suffix = "s" if period_value > 1 else ""
            result += f"{int(period_value)} {period_name}{plural_suffix} "
            if not full_time:
                break
    return result.strip()

def get_readable_file_size(size_in_bytes: int):
    if size_in_bytes is None:
        return "0B"
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return (
        f"{size_in_bytes:.2f}{SIZE_UNITS[index]}"
        if index > 0
        else f"{size_in_bytes:.2f}B"
    )

def update_user_ldata(id_, key=None, value=None):
    exception_keys = ["is_sudo", "is_auth"]
    if not key and not value:
        if id_ in user_data:
            updated_data = {
                k: v for k, v in user_data[id_].items() if k in exception_keys
            }
            user_data[id_] = updated_data
        return
    user_data.setdefault(id_, {})
    user_data[id_][key] = value

commands = [
    "StartCommand",
    "GetIDCommand",
    "GetStickerIDCommand",
    "UserSetCommands",
    "GetMediaInfoCommand",
    "GetFileInfoCommand",
    "GetChatsListCommand",
    "CheckRightsCommand",
    "StatsCommand",
    "IndexCommand",
    "BotStatsCommand",
    "PingCommand",
    "HelpCommand",
    "DeleteDbfileCommand",
    "DeleteDbfilesCommand",
    "DeletePMUserCommand",
    "DeleteFsubUserCommand",
    "SetSkipFilesCommand",
    "AuthorizeCommand",
    "UnAuthorizeCommand",
    "AddSudoCommand",
    "RmSudoCommand",
    "BotSetCommand",
    "BroadcastCommand",
    "LogCommand",
    "RestartCommand"
]

command_descriptions = {
    "StartCommand": "- Check bot is alive or not",
    "GetIDCommand": "- To get user and chat id",
    "GetStickerIDCommand": "- To get sticker id",
    "UserSetCommands": "- Open User Settings",
    "GetMediaInfoCommand": "- Get Media info like audios, quality, subtitles, codec",
    "GetFileInfoCommand": "- To get file information from telegram json",
    "GetChatsListCommand": "- [ADMIN] To get all chats list where bot connected",
    "CheckRightsCommand": "- [ADMIN] To know the rights of the chat or users in the chat",
    "StatsCommand": "- [ADMIN] Check mongodb database stats",
    "IndexCommand": "- [ADMIN] Indexing Database File",
    "BotStatsCommand": "- [ADMIN] Check Bot & System stats",
    "PingCommand": "- [ADMIN] check between server to bot connection speed",
    "HelpCommand": "- Get detailed help",
    "DeleteDbfileCommand": "- [ADMIN] for delete single file in mongodb",
    "DeleteDbfilesCommand": "- [ADMIN] for delete multiple file in mongodb",
    "DeletePMUserCommand": "[ADMIN] for delete specific PM user from mongodb",
    "DeleteFsubUserCommand": "[ADMIN] for delete specific Fsub user from mongodb",
    "SetSkipFilesCommand": "- [ADMIN] for skip files to index",
    "AuthorizeCommand": "- [ADMIN] To authorize",
    "UnAuthorizeCommand": "- [ADMIN] To unauthorize",
    "AddSudoCommand": "- [ADMIN] To promote user to sudo user",
    "RmSudoCommand": "- [ADMIN] To demote sudo user to user",
    "BotSetCommand": "- [ADMIN] Open Bot settings",
    "BroadcastCommand": "- [ADMIN] Broadcast message to all users",
    "LogCommand": "- [ADMIN] View log",
    "RestartCommand": "- [ADMIN] Restart the bot",
}

commands = [
    BotCommand(
        getattr(BotCommands, cmd)[0]
        if isinstance(getattr(BotCommands, cmd), list)
        else getattr(BotCommands, cmd),
        command_descriptions[cmd],
    )
    for cmd in commands
]

async def set_commands(bot):
    if config_dict["SET_COMMANDS"]:
        LOGGER.info("Setting bot commands...")
        await bot.set_bot_commands(commands)
        LOGGER.info("Bot commands have been successfully set.")
    else:
        LOGGER.info("Command setting is disabled in the configuration.")

async def main(chat_id):
    async for message in user_bot.get_chat_history(chat_id, limit=1):
        if message:
            return str(message.id)
        
async def check_last_msg_id_bot(last_msg, channel_id):
    """
    Verify if the forwarded file is the actual last file in a Telegram channel.

    Args:
        message (types.Message): The forwarded message.
        last_msg (int): The ID of the last message in the channel.
        channel_id (int): The ID of the channel.

    Returns:
        bool: True if the forwarded file is the actual last file in the channel, False otherwise.
    """
    if last_msg:
        # Check if there are any messages after the last_msg
        messages = await bot.get_messages(channel_id, last_msg + 1)
        if messages.empty:
            # If messages are found, it means last_msg is not the last message in the channel
            return True
        else:
            # If no messages are found, it means last_msg is the last message in the channel
            return False
    else:
        # If last_msg is None, we cannot verify if it's the last message in the channel
        return False
    
async def delete_file_after_delay(file_path, delay):
    await sleep(delay)
    if os.path.exists(file_path):
        os.remove(file_path)

            
async def check_bot_connection(bot_base_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(bot_base_url, allow_redirects=False) as response:
                if response.status == 302:
                    LOGGER.info(f"Received redirect to: {response.headers.get('Location')}")
                    return False
                elif response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if content_type.startswith('text/html'):
                        LOGGER.info(f"Connected with {bot_base_url}")
                        return True
                        
                    else:
                        LOGGER.error(f"Unexpected content type: {content_type}.")
                        return False
                else:
                    LOGGER.error(f"Unexpected HTTP status: {response.status}")
                    return False
    except Exception as e:
        LOGGER.error(f"Error connecting to {bot_base_url}: {str(e)}")
        return False
    
async def checking_access(user_id, button=None):
    token_timeout = config_dict["TOKEN_TIMEOUT"]
    if not token_timeout or token_timeout == 0 or token_timeout == '0':
        return None, button
    user_data.setdefault(user_id, {})
    data = user_data[user_id]
    if DATABASE_URL:
        data["time"] = await DbManager().get_token_expiry(user_id)
    expire = data.get("time")
    is_expired = (
        expire is None or expire is not None and (time() - expire) > token_timeout
    )
    if is_expired:
        token = data["token"] if expire is None and "token" in data else str(uuid4())
        if expire is not None:
            del data["time"]
        data["token"] = token
        if DATABASE_URL:
            await DbManager().update_user_token(user_id, token)
        user_data[user_id].update(data)
        time_str = get_readable_time(token_timeout, True)
        if button is None:
            button = ButtonMaker()
        button.url(
            "Collect token",
            tinyfy(short_url(f"https://telegram.me/{bot_name}?start={token}")),
        )
        button.url("How To Download", "https://t.me/howtodownload_naruto/140")
        button = button.column()
        return (
            f"Your token has expired, please collect a new token.\n<b>It will expire after {time_str}</b>!",
            button,
        )
    return None, button

async def cleanup_downloads():
    """
    Asynchronously removes all files and subdirectories in the downloads/media and downloads/temp directories.
    
    Returns:
        None
    """
    # Define the paths to the directories
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # Get the project root directory
    directories = [
        os.path.join(project_root, "downloads", "media"),
        os.path.join(project_root, "downloads", "temp"),
        os.path.join(project_root, "downloads", "info_files")
    ]
    
    for directory in directories:
        try:
            if os.path.exists(directory) and os.path.isdir(directory):
                # Use asyncio.to_thread to run the blocking code in a separate thread
                await asyncio.to_thread(shutil.rmtree, directory)  # Remove the entire directory and its contents
                await asyncio.to_thread(os.makedirs, directory)  # Recreate the empty directory
                LOGGER.info(f"Cleaned up directory succesfully: {directory}")
            else:
                LOGGER.info(f"Directory '{directory}' does not exist.")
                await asyncio.to_thread(os.makedirs, directory)
                LOGGER.info(f"Adding directory '{directory}'")
        except Exception as e:
            LOGGER.error(f"An error occurred while trying to clean up '{directory}': {e}")

def format_time(seconds: float) -> str:
    try:
        seconds = float(seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02}:{minutes:02}:{int(secs):02}"  # Formats as HH:MM:SS
    except:
        return "N/A"
    
def format_duration(start: float, end: float) -> str:
    duration = end - start
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

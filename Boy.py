import os
import re
import asyncio
import logging
import traceback
import threading
import subprocess
from base64 import urlsafe_b64encode, urlsafe_b64decode
from math import floor
from time import time
from pyrogram import Client, filters, idle
from pyrogram.enums import ParseMode, ChatMemberStatus
from pyrogram.errors import FloodWait, PeerIdInvalid, ChannelInvalid, UserNotParticipant, QueryIdInvalid
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_ID = 28015531
API_HASH = "2ab4ba37fd5d9ebf1353328fc915ad28"
BOT_TOKEN = "7514636092:AAH9_k-HGWrpQcRfypDQixdXlIzh8dEuj64"
TARGET_CHANNEL = -1002045800481
DB_CHANNEL = -1002142610684
FILE_STORE = DB_CHANNEL
OWNER_ID = 6121610691
DELETE_DELAY = 30 * 60
DOWNLOAD_WORKERS = 4

app = Client(
    "video_uploader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=DOWNLOAD_WORKERS
)

btn_formatter = {
    '480p': '𝟰𝟴𝟬𝗽',
    '720p': '𝟳𝟮𝟬𝗽',
    '1080p': '𝟭𝟬𝟴𝟬𝗽'
}

user_sessions = {}
file_messages_to_delete = {}
force_sub_channels = []
temp_force_sub_data = {}
FFMPEG_COMMAND = "ffmpeg -progress pipe:1 -i {input} -c:v libx265 -crf 28 -preset fast -c:a copy {output}"
THUMBNAIL_PATH = "thumb.jpg"
cancel_requests = {}

SEASON_EPISODE_PATTERNS = [
    re.compile(r'S(\d+)(?:E|EP)(\d+)', re.IGNORECASE), 
    re.compile(r'S(\d+)[\s-]*(?:E|EP)(\d+)', re.IGNORECASE),
    re.compile(r'Season\s*(\d+)\s*Episode\s*(\d+)', re.IGNORECASE),
    re.compile(r'\[S(\d+)\]\[E(\d+)\]', re.IGNORECASE),
    re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE),
    re.compile(r'(?:E|EP|Episode)\s*(\d+)', re.IGNORECASE),
    re.compile(r'\b(\d+)\b')
]

def convert_bytes(size):
    if size == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

def convert_time(seconds):
    if seconds < 0:
        return "00:00:00"
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

def encode(data):
    return urlsafe_b64encode(data.encode()).decode().rstrip('=')

def decode(encoded_str):
    padding = '=' * (-len(encoded_str) % 4)
    return urlsafe_b64decode(encoded_str + padding).decode()

def extract_season_episode(filename):
    for pattern in SEASON_EPISODE_PATTERNS:
        match = pattern.search(filename)
        if match:
            season = match.group(1) if len(match.groups()) > 1 else None
            episode = match.group(2) if len(match.groups()) > 1 else match.group(1)
            logger.info(f"Extracted season: {season}, episode: {episode} from {filename}")
            return season, episode
    logger.warning(f"No season/episode pattern matched for {filename}")
    return None, None

def format_stored_filename(anime_name, season, episode, quality):
    parts = []
    if anime_name:
        # Clean the anime name by removing special characters
        clean_name = re.sub(r'[^\w\s]', ' ', anime_name)
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
        parts.append(clean_name)
    if season:
        parts.append(f"[S{season}]")
    if episode:
        parts.append(f"[Ep{episode}]")
    if quality:
        parts.append(f"[{quality}]")
    parts.append("Tamil [HEVC]@ATXanime")
    return " ".join(parts)

async def create_download_link(msg_id):
    bot_username = (await app.get_me()).username
    encoded_str = encode(f'get-{str(msg_id * abs(FILE_STORE))}')
    return f"https://telegram.me/{bot_username}?start={encoded_str}"

async def delete_messages_after_delay(chat_id, message_ids, delay):
    await asyncio.sleep(delay)
    try:
        await app.delete_messages(chat_id, message_ids)
        logger.info(f"Deleted messages: {message_ids} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Error deleting messages: {e}")

async def check_user_subscription(user_id):
    if not force_sub_channels:
        return True
    
    for channel_id in force_sub_channels:
        try:
            member = await app.get_chat_member(channel_id, user_id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                return False
        except UserNotParticipant:
            return False
        except Exception as e:
            logger.error(f"Error checking subscription for {user_id} in {channel_id}: {e}")
            return False
    return True

async def delete_after_delay(message, delay=5):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

def clean_anime_name(filename):
    # Remove "encoded_<quality>_" prefix
    cleaned = re.sub(r'^encoded_(480p|720p|1080p)_', '', filename, flags=re.IGNORECASE)
    # Remove brackets and special characters
    cleaned = re.sub(r'\[.*?\]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = re.sub(r'\.[^.]+$', '', cleaned)
    # Remove technical terms
    cleaned = re.sub(r'\b(Tamil|mkv|mp4|web|hevc|x264|x265|aac|atx)\b', '', cleaned, flags=re.IGNORECASE)
    # Remove any leftover numbers/special characters at end
    cleaned = re.sub(r'[\W\d]+$', '', cleaned).strip()
    return cleaned

async def safe_answer_callback(callback_query, text, show_alert=False):
    try:
        await callback_query.answer(text, show_alert=show_alert)
    except QueryIdInvalid:
        logger.warning("QueryIdInvalid when answering callback")
    except Exception as e:
        logger.error(f"Error answering callback: {e}")

class FileProcessor:
    def __init__(self, client, message, rep, file_path, quality, status_message=None, user_id=None):
        self.__client = client
        self.message = message
        self.rep = rep
        self.cancelled = False
        self.__start = time()
        self.__updater = self.__start
        self.__name = os.path.basename(file_path)
        self.__qual = quality
        self.file_path = file_path
        self.encoding_start = 0
        self.status_message = status_message
        self.status_msg = None
        self.download_start = 0
        self.ffmpeg_lock = threading.Lock()
        self.user_id = user_id
        self.process = None
        self.last_encoding_update = 0

    async def get_duration(self, file_path):
        cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '{file_path}'"
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            error_msg = stderr.decode().strip()
            raise Exception(f"FFprobe error: {error_msg}")
        return float(stdout.decode().strip())

    async def update_channel_status(self, text):
        if self.status_msg:
            try:
                await self.status_msg.edit_text(text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Error updating channel status: {e}")

    async def encoding_status(self, current_duration, total_duration):
        if self.user_id and cancel_requests.get(self.user_id, False):
            self.cancelled = True
            
        if self.cancelled:
            return
            
        now = time()
        if current_duration < total_duration and now - self.last_encoding_update < 10:
            return
        self.last_encoding_update = now
        
        percent = round((current_duration / total_duration) * 100, 2) if total_duration > 0 else 0
        
        elapsed = now - self.encoding_start
        if elapsed > 0:
            speed = current_duration / elapsed
            eta = (total_duration - current_duration) / speed if speed > 0 else 0
        else:
            speed = 0
            eta = 0

        bar_length = 12
        filled_length = floor(percent / 100 * bar_length)
        bar = "█" * filled_length + "▒" * (bar_length - filled_length)
        
        display_name = clean_anime_name(self.__name)
        if len(display_name) > 30:
            display_name = display_name[:27] + "..."
        
        status_text = f"""
<blockquote>‣ <b>Anime Name :</b> <b><i>{display_name}</i></b></blockquote>
<blockquote>‣ <b>Status :</b> <i>Encoding</i>
    <code>[{bar}]</code> {percent}%</blockquote> 
<blockquote>   ‣ <b>Processed :</b> {convert_time(current_duration)} / {convert_time(total_duration)}
    ‣ <b>Speed :</b> {speed:.2f}x
    ‣ <b>Time Took :</b> {convert_time(elapsed)}
    ‣ <b>Time Left :</b> {convert_time(eta)}</blockquote>
<blockquote>‣ <b>Quality :</b> <code>{self.__qual.upper()}</code></blockquote>
"""
        
        await self.update_channel_status(status_text)
        
        if self.status_message:
            try:
                await self.status_message.edit_text(status_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Error updating encoding status: {e}")

    async def encode(self, input_path, output_path):
        self.encoding_start = time()
        self.last_encoding_update = 0
        try:
            total_duration = await self.get_duration(input_path)
        except Exception as e:
            logger.error(f"Error getting duration: {e}")
            total_duration = 0
        
        cmd = FFMPEG_COMMAND.format(input=f'"{input_path}"', output=f'"{output_path}"')
        logger.info(f"Running FFmpeg command: {cmd}")
        
        if not os.path.exists(input_path):
            raise Exception(f"Input file not found: {input_path}")
        
        with self.ffmpeg_lock:
            self.process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            time_pattern = re.compile(r"out_time=(\d+:\d+:\d+\.\d+)")
            stderr_output = ""
            buffer = b""
            
            encoding_timeout = 21600
            start_time = time()
            
            while True:
                if self.cancelled:
                    self.process.terminate()
                    raise Exception("Encoding cancelled by user")
                
                if time() - start_time > encoding_timeout:
                    self.process.terminate()
                    raise Exception("Encoding timed out after 6 hours")
                
                try:
                    chunk = await asyncio.wait_for(self.process.stdout.read(4096), timeout=5.0)
                except asyncio.TimeoutError:
                    continue
                    
                if not chunk:
                    break
                    
                buffer += chunk
                text = buffer.decode(errors="ignore")
                
                for match in time_pattern.finditer(text):
                    time_str = match.group(1)
                    parts = time_str.split(':')
                    if len(parts) == 3:
                        h, m, s = parts
                        current_sec = float(h) * 3600 + float(m) * 60 + float(s)
                        await self.encoding_status(current_sec, total_duration)
                
                last_match = list(time_pattern.finditer(text))[-1] if list(time_pattern.finditer(text)) else None
                if last_match:
                    buffer = buffer[last_match.end():]
                else:
                    buffer = b""
            
            await self.process.wait()
            if self.process.returncode != 0:
                stderr_output = (await self.process.stderr.read()).decode()
                logger.error(f"Encoding failed with error: {stderr_output}")
                raise Exception(f"Encoding failed: {stderr_output[:500]}")
        return output_path

    async def progress_status(self, current, total):
        if self.user_id and cancel_requests.get(self.user_id, False):
            self.cancelled = True
            
        if self.cancelled:
            self.__client.stop_transmission()
            
        now = time()
        diff = now - self.__start
            
        if current < total and now - self.__updater < 10:
            return
        self.__updater = now
        
        percent = round(current / total * 100, 2) if total > 0 else 0
        
        if diff > 0:
            speed = current / diff
            eta = round((total - current) / speed) if speed > 0 and current < total else 0
        else:
            speed = 0
            eta = 0
        
        bar_length = 12
        filled_length = floor(percent / 100 * bar_length)
        bar = "█" * filled_length + "▒" * (bar_length - filled_length)
        
        display_name = clean_anime_name(self.__name)
        if len(display_name) > 30:
            display_name = display_name[:27] + "..."
        
        status_text = f"""
<blockquote>‣ <b>Anime Name :</b> <b><i>{display_name}</i></b></blockquote>
<blockquote>‣ <b>Status :</b> <i>Uploading</i>
    <code>[{bar}]</code> {percent}%</blockquote> 
<blockquote>   ‣ <b>Size :</b> {convert_bytes(current)} / {convert_bytes(total)}
    ‣ <b>Speed :</b> {convert_bytes(speed)}/s
    ‣ <b>Time Took :</b> {convert_time(diff)}
    ‣ <b>Time Left :</b> {convert_time(eta)}</blockquote>
<blockquote>‣ <b>Quality :</b> <code>{self.__qual.upper()}</code></blockquote>
"""
        
        await self.update_channel_status(status_text)
        
        if self.status_message:
            try:
                await self.status_message.edit_text(status_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Error updating upload status: {e}")

    async def process_and_upload(self):
        self.__start = time()
        self.__updater = self.__start
        upload_path = self.file_path
        
        try:
            await self.update_channel_status(
                f"<blockquote><b>⏳ Starting processing for {self.__qual.upper()}...</b></blockquote>\n"
                f"<blockquote>File: {clean_anime_name(self.__name)}</blockquote>"
            )
            
            if FFMPEG_COMMAND:
                # Create output filename without "encoded_" prefix
                clean_name = re.sub(r'^encoded_(480p|720p|1080p)_', '', self.__name, flags=re.IGNORECASE)
                encoded_path = f"{self.__qual}_{clean_name.replace(' ', '_')}.mkv"
                try:
                    self.status_message = await self.message.reply_text(
                        f"<blockquote><b>⏳ Starting encoding for {self.__qual.upper()}...</b></blockquote>",
                        parse_mode=ParseMode.HTML
                    )
                except:
                    pass
                    
                await self.update_channel_status(
                    f"<blockquote><b>🔧 Encoding {self.__qual.upper()} file...</b></blockquote>\n"
                    f"<blockquote>File: {clean_anime_name(self.__name)}</blockquote>"
                )
                try:
                    upload_path = await self.encode(self.file_path, encoded_path)
                except Exception as e:
                    logger.error(f"Encoding failed: {e}")
                    await self.update_channel_status(
                        f"<blockquote><b>❌ Encoding failed for {self.__qual.upper()}</b></blockquote>\n"
                        f"<blockquote>Error: {str(e)[:100]}</blockquote>"
                    )
                    raise
            
            try:
                self.status_message = await self.message.reply_text(
                    f"<blockquote><b>⏳ Starting upload for {self.__qual.upper()}...</b></blockquote>",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
            
            await self.update_channel_status(
                f"<blockquote><b>📤 Uploading {self.__qual.upper()}...</b></blockquote>\n"
                f"<blockquote>File: {clean_anime_name(self.__name)}</blockquote>"
            )
            
            # Get anime name from session
            session = user_sessions.get(self.user_id, {})
            anime_name = session.get("anime_name", "Unknown Anime")
            season = session.get("season", "01")
            episode = session.get("episode", "01")
            
            stored_caption = format_stored_filename(anime_name, season, episode, self.__qual)
            
            # Send as document with thumbnail
            thumb_path = THUMBNAIL_PATH if os.path.exists(THUMBNAIL_PATH) else None
            if thumb_path:
                logger.info(f"Using thumbnail: {thumb_path}")
            else:
                logger.warning("Thumbnail not found, uploading without thumbnail")
                
            msg = await self.__client.send_document(
                chat_id=FILE_STORE,
                document=upload_path,
                thumb=thumb_path,
                caption=f"<blockquote><b>{stored_caption}</b></blockquote>",
                progress=self.progress_status
            )
            file_size = msg.document.file_size
            
            # Delete status message immediately
            if self.status_message:
                try:
                    await self.status_message.delete()
                except:
                    pass
                
            return msg.id, file_size
        except FloodWait as e:
            await asyncio.sleep(e.value * 1.5)
            return await self.process_and_upload()
        except Exception as e:
            logger.error(f"Error in process_and_upload: {traceback.format_exc()}")
            try:
                await self.message.reply_text(f"❌ Error during processing: {str(e)[:300]}")
            except:
                pass
            raise
        finally:
            try:
                if upload_path != self.file_path and os.path.exists(upload_path):
                    os.remove(upload_path)
            except Exception as e:
                logger.error(f"Error removing file: {e}")

@app.on_message(filters.command("start") & filters.private)
async def handle_start_command(client, message: Message):
    args = message.text.split()
    if len(args) > 1:
        try:
            encoded_str = args[1]
            decoded_str = decode(encoded_str)
            
            if decoded_str.startswith("get-"):
                multiplied_id = int(decoded_str.split('-')[1])
                msg_id = multiplied_id // abs(FILE_STORE)
                
                user_id = message.from_user.id
                is_subscribed = await check_user_subscription(user_id)
                
                if not is_subscribed:
                    temp_force_sub_data[user_id] = {
                        "msg_id": msg_id,
                        "original_message_id": message.id
                    }
                    
                    buttons = []
                    for channel_id in force_sub_channels:
                        try:
                            chat = await client.get_chat(channel_id)
                            invite_link = await client.export_chat_invite_link(channel_id)
                            buttons.append([InlineKeyboardButton(f"Join {chat.title}", url=invite_link)])
                        except Exception as e:
                            logger.error(f"Error getting chat for {channel_id}: {e}")
                    
                    buttons.append([InlineKeyboardButton("✅ Verify Subscription", callback_data=f"verify_{user_id}")])
                    
                    await message.reply_text(
                        "⚠️ You must join our channels to use this bot!\n\n"
                        "Please join the following channel(s) and click Verify Subscription:",
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                    return
                
                try:
                    msg = await client.get_messages(FILE_STORE, message_ids=msg_id)
                    if msg:
                        file_caption = f"<blockquote><b>{msg.caption}</b></blockquote>"
                        file_msg = await msg.copy(
                            message.chat.id, 
                            caption=file_caption,
                            parse_mode=ParseMode.HTML
                        )
                        
                        warning_text = (
                            "<blockquote><b>Tʜɪs Fɪʟᴇ ᴡɪʟʟ ʙᴇ Dᴇʟᴇᴛᴇᴅ ɪɴ 30 mins.</b> "
                            "<b>Pʟᴇᴀsᴇ sᴀᴠᴇ ᴏʀ ғᴏʀᴡᴀʀᴅ ɪᴛ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs "
                            "ʙᴇғᴏʀᴇ ɪᴛ ɢᴇᴛs Dᴇʟᴇᴛᴇᴅ.</blockquote>"
                        )
                        warning_msg = await message.reply_text(
                            warning_text,
                            parse_mode=ParseMode.HTML,
                            reply_to_message_id=file_msg.id
                        )
                        
                        message_ids = [file_msg.id, warning_msg.id]
                        asyncio.create_task(
                            delete_messages_after_delay(message.chat.id, message_ids, DELETE_DELAY)
                        )
                        
                        file_messages_to_delete[file_msg.id] = {
                            "chat_id": message.chat.id,
                            "delete_time": asyncio.get_event_loop().time() + DELETE_DELAY
                        }
                        return
                    else:
                        await message.reply_text("❌ File not found. It may have been deleted.")
                except Exception as e:
                    logger.error(f"Error retrieving file: {e}")
                    await message.reply_text("❌ Error retrieving file. Please try again later.")
                return
        except Exception as e:
            logger.error(f"Error processing start command: {e}")
    
    if message.from_user.id != OWNER_ID:
        await message.reply_text("🚫 You are not authorized to upload files. This bot is for file sharing only.")
        return
    
    user_id = message.from_user.id
    user_sessions[user_id] = {
        "state": "waiting_photo",
        "cover_photo": None,
        "anime_name": "",
        "videos": {
            "480p": None,
            "720p": None,
            "1080p": None
        },
        "target_channel": TARGET_CHANNEL,
        "language": "Tamil",
        "codec": "HEVC",
        "season": "01",
        "episode": "01"
    }
    await message.reply_text("👑 Owner session started! Please send a cover photo for the episode.")

@app.on_message(filters.command("thumb") & filters.private & filters.user(OWNER_ID))
async def set_thumbnail(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.reply_text("❌ Please reply to a photo to set as thumbnail.")
        return

    try:
        # Download the photo
        await app.download_media(
            message.reply_to_message.photo.file_id, 
            file_name=THUMBNAIL_PATH
        )
        logger.info(f"Thumbnail set to {THUMBNAIL_PATH}")
        await message.reply_text("✅ Thumbnail set successfully!")
    except Exception as e:
        logger.error(f"Error setting thumbnail: {e}")
        await message.reply_text(f"❌ Error setting thumbnail: {e}")

@app.on_message(filters.command("setseason") & filters.private & filters.user(OWNER_ID))
async def set_season_command(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /setseason <season_number>")
        return
    
    try:
        season = message.command[1].zfill(2)
        user_id = message.from_user.id
        
        if user_id in user_sessions:
            user_sessions[user_id]["season"] = season
            await message.reply_text(f"✅ Season set to: {season}")
        else:
            await message.reply_text("❌ No active session. Start a session with /start first.")
    except Exception as e:
        logger.error(f"Error setting season: {e}")
        await message.reply_text("❌ Invalid season format. Use numbers only.")

@app.on_message(filters.command("setepisode") & filters.private & filters.user(OWNER_ID))
async def set_episode_command(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /setepisode <episode_number>")
        return
    
    try:
        episode = message.command[1].zfill(2)
        user_id = message.from_user.id
        
        if user_id in user_sessions:
            user_sessions[user_id]["episode"] = episode
            await message.reply_text(f"✅ Episode set to: {episode}")
        else:
            await message.reply_text("❌ No active session. Start a session with /start first.")
    except Exception as e:
        logger.error(f"Error setting episode: {e}")
        await message.reply_text("❌ Invalid episode format. Use numbers only.")

@app.on_message(filters.command("cancel") & filters.private & filters.user(OWNER_ID))
async def cancel_operation(client, message: Message):
    user_id = message.from_user.id
    cancel_requests[user_id] = True
    await message.reply_text("⏹️ Cancellation requested. It may take a moment to stop...")

@app.on_message(filters.command("setffmpeg") & filters.private & filters.user(OWNER_ID))
async def set_ffmpeg_command(client, message: Message):
    global FFMPEG_COMMAND
    if len(message.command) < 2:
        await message.reply_text(
            "Usage: /setffmpeg <command>\n"
            "Example: /setffmpeg ffmpeg -i {{input}} -c:v libx265 -crf 28 -preset fast -c:a copy {{output}}\n\n"
            "💡 Optimization Tips:\n"
            "1. Use '-preset fast' for faster encoding\n"
            "2. Use '-threads 4' to utilize multiple CPU cores\n"
            "3. Add '-movflags +faststart' for web streaming\n"
            "4. For NVENC: '-c:v h264_nvenc -preset p7 -tune hq'"
        )
        return
    
    cmd = message.text.split(" ", 1)[1]
    FFMPEG_COMMAND = cmd
    await message.reply_text(f"✅ FFmpeg command set to:\n<code>{cmd}</code>")

@app.on_message(filters.command("addchnl") & filters.private & filters.user(OWNER_ID))
async def add_force_sub_channel(client, message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("Usage: /addchnl <channel_id>")
        return
    
    try:
        channel_id = int(args[1])
        if channel_id not in force_sub_channels:
            force_sub_channels.append(channel_id)
            await message.reply_text(f"✅ Channel {channel_id} added to force subscription list!")
        else:
            await message.reply_text(f"ℹ️ Channel {channel_id} is already in the force subscription list.")
    except Exception as e:
        logger.error(f"Error adding force sub channel: {e}")
        await message.reply_text("❌ Invalid channel ID format. Please provide a valid channel ID.")

@app.on_message(filters.command("delchnl") & filters.private & filters.user(OWNER_ID))
async def remove_force_sub_channel(client, message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("Usage: /delchnl <channel_id>")
        return
    
    try:
        channel_id = int(args[1])
        if channel_id in force_sub_channels:
            force_sub_channels.remove(channel_id)
            await message.reply_text(f"✅ Channel {channel_id} removed from force subscription list!")
        else:
            await message.reply_text(f"ℹ️ Channel {channel_id} is not in the force subscription list.")
    except Exception as e:
        logger.error(f"Error removing force sub channel: {e}")
        await message.reply_text("❌ Invalid channel ID format. Please provide a valid channel ID.")

@app.on_message(filters.command("listchnl") & filters.private & filters.user(OWNER_ID))
async def list_force_sub_channels(client, message: Message):
    if not force_sub_channels:
        await message.reply_text("No force subscription channels configured.")
        return
    
    response = "🔒 Force Subscription Channels:\n\n"
    for channel_id in force_sub_channels:
        try:
            chat = await client.get_chat(channel_id)
            response += f"• {chat.title} (ID: {channel_id})\n"
        except Exception as e:
            response += f"• Channel ID: {channel_id} (Unable to fetch details)\n"
    
    await message.reply_text(response)

@app.on_callback_query(filters.regex(r"^verify_"))
async def handle_verify_callback(client, callback_query: CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    if callback_query.from_user.id != user_id:
        try:
            await callback_query.answer("This is not for you!", show_alert=True)
        except QueryIdInvalid:
            pass
        return
    
    is_subscribed = await check_user_subscription(user_id)
    
    if not is_subscribed:
        try:
            await callback_query.answer("You haven't joined all channels yet!", show_alert=True)
        except QueryIdInvalid:
            pass
        return
    
    try:
        await callback_query.answer("Verification successful! Sending file...")
    except QueryIdInvalid:
        pass
    
    file_data = temp_force_sub_data.get(user_id)
    if not file_data:
        try:
            await callback_query.message.edit_text("Session expired. Please request the file again.")
        except:
            pass
        return
    
    try:
        msg = await client.get_messages(FILE_STORE, message_ids=file_data["msg_id"])
        if msg:
            file_caption = f"<blockquote><b>{msg.caption}</b></blockquote>"
            file_msg = await msg.copy(
                callback_query.message.chat.id, 
                caption=file_caption,
                parse_mode=ParseMode.HTML
            )
            
            warning_text = (
                "<blockquote><b>Tʜɪs Fɪʟᴇ ᴡɪʟʟ ʙᴇ Dᴇʟᴇᴛᴇᴅ ɪɴ 30 mins.</b> "
                "<b>Pʟᴇᴀsᴇ sᴀᴠᴇ ᴏʀ ғᴏʀᴡᴀʀᴅ ɪᴛ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs "
                "ʙᴇғᴏʀᴇ ɪᴛ ɢᴇᴛs Dᴇʟᴇᴛᴇᴅ.</blockquote>"
            )
            warning_msg = await callback_query.message.reply_text(
                warning_text,
                parse_mode=ParseMode.HTML,
                reply_to_message_id=file_msg.id
            )
            
            message_ids = [file_msg.id, warning_msg.id]
            asyncio.create_task(
                delete_messages_after_delay(callback_query.message.chat.id, message_ids, DELETE_DELAY)
            )
            
            file_messages_to_delete[file_msg.id] = {
                "chat_id": callback_query.message.chat.id,
                "delete_time": asyncio.get_event_loop().time() + DELETE_DELAY
            }
            
            try:
                await callback_query.message.delete()
            except:
                pass
            
            if user_id in temp_force_sub_data:
                del temp_force_sub_data[user_id]
        else:
            try:
                await callback_query.message.edit_text("❌ File not found. It may have been deleted.")
            except:
                pass
    except Exception as e:
        logger.error(f"Error sending file after verification: {e}")
        try:
            await callback_query.message.edit_text("❌ Error retrieving file. Please try again.")
        except:
            pass

@app.on_message(filters.command("post") & filters.private)
async def set_post_channel(client, message: Message):
    if message.from_user.id != OWNER_ID:
        await message.reply_text("🚫 Only the owner can set posting channels.")
        return
    
    try:
        channel_id = int(message.command[1])
        user_id = message.from_user.id
        
        if user_id not in user_sessions:
            user_sessions[user_id] = {
                "state": "waiting_photo",
                "cover_photo": None,
                "anime_name": "",
                "videos": {"480p": None, "720p": None, "1080p": None},
                "target_channel": channel_id,
                "language": "Tamil",
                "codec": "HEVC",
                "season": "01",
                "episode": "01"
            }
        else:
            user_sessions[user_id]["target_channel"] = channel_id
        
        await message.reply_text(f"✅ Posting channel set to: {channel_id}")
    except (IndexError, ValueError):
        await message.reply_text("❌ Invalid format. Use: /post -10012345678")
    except Exception as e:
        logger.error(f"Error setting channel: {e}")
        await message.reply_text(f"❌ Error setting channel: {e}")

@app.on_message(filters.private & filters.photo)
async def receive_photo(client, message: Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID or user_id not in user_sessions:
        return
    
    session = user_sessions[user_id]
    if session["state"] != "waiting_photo":
        return
    
    try:
        session["cover_photo"] = message.photo.file_id
        session["state"] = "waiting_anime_name"
        await message.reply_text(
            "🖼️ Cover photo received! Now please send the anime name for this episode."
        )
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await message.reply_text("❌ Error processing photo. Please try again.")

# FIXED: Proper command filter syntax
@app.on_message(filters.private & filters.text & ~filters.command)
async def receive_anime_name(client, message: Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID or user_id not in user_sessions:
        return
    
    session = user_sessions[user_id]
    if session["state"] != "waiting_anime_name":
        return
    
    try:
        anime_name = message.text.strip()
        if not anime_name:
            await message.reply_text("❌ Anime name cannot be empty. Please send a valid name.")
            return
            
        session["anime_name"] = anime_name
        session["state"] = "waiting_videos"
        await message.reply_text(
            f"📝 Anime name set to: {anime_name}\n\n"
            "Now please send 3 video files in the following resolutions:\n\n"
            "• One with 480p in filename\n"
            "• One with 720p in filename\n"
            "• One with 1080p in filename\n\n"
            "Note: The resolution can be anywhere in the filename (e.g., [480p], 480p, etc.)"
        )
    except Exception as e:
        logger.error(f"Error setting anime name: {e}")
        await message.reply_text("❌ Error setting anime name. Please try again.")

@app.on_message(filters.private & (filters.video | filters.document))
async def receive_video(client, message: Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID or user_id not in user_sessions:
        return
    
    session = user_sessions[user_id]
    if session["state"] != "waiting_videos":
        return
    
    if message.video:
        filename = message.video.file_name or ""
    elif message.document:
        filename = message.document.file_name or ""
    else:
        return
    
    # More flexible quality detection
    quality = None
    filename_lower = filename.lower()
    
    if '480p' in filename_lower:
        quality = '480p'
    elif '720p' in filename_lower:
        quality = '720p'
    elif '1080p' in filename_lower:
        quality = '1080p'
    
    if not quality:
        await message.reply_text(
            "❌ Couldn't find resolution in filename! Filename must contain one of: 480p, 720p, or 1080p.\n"
            "Please resend with proper naming.\n\n"
            f"Your filename: {filename[:50]}..."
        )
        return
    
    session["videos"][quality] = message
    
    videos = session["videos"]
    if all(videos.values()):
        await send_preview(client, user_id)
    else:
        missing = [q for q, v in videos.items() if not v]
        await message.reply_text(
            f"✅ Received {quality} video! Still waiting for: {', '.join(missing)}"
        )

async def send_preview(client, user_id):
    session = user_sessions[user_id]
    session["state"] = "waiting_confirmation"
    
    # Use anime name from session
    title = session["anime_name"]
    season = session.get("season", "01")
    episode = session.get("episode", "01")
    
    # Fixed caption format
    caption = (
        f"<blockquote><b>➤ {title}</b></blockquote>\n"
        "<b>──────────────</b>\n"
        f"<b>‣ Season :</b> {season}\n"
        f"<b>‣ Episode :</b> {episode}\n"
        f"<b>‣ Language :</b> {session['language']}\n"
        f"<b>‣ Codec :</b> {session['codec']}\n"
        f"<b>‣ Quality :</b> 480p, 720p, 1080p\n"
        "<b>──────────────</b>"
    )
    
    # Button layout
    buttons = [
        [
            InlineKeyboardButton("480p", callback_data="preview_480p"),
            InlineKeyboardButton("720p", callback_data="preview_720p"),
        ],
        [
            InlineKeyboardButton("1080p", callback_data="preview_1080p"),
        ],
        [
            InlineKeyboardButton("✅ Send", callback_data="confirm_send"),
            InlineKeyboardButton("❌ Cancel", callback_data="confirm_cancel"),
        ]
    ]
    
    try:
        await client.send_photo(
            chat_id=user_id,
            photo=session["cover_photo"],
            caption=caption,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error sending preview: {e}")
        await client.send_message(user_id, "❌ Error generating preview. Please try again.")

async def verify_channel_access(channel_id):
    try:
        await app.get_chat(channel_id)
        return True
    except (PeerIdInvalid, ChannelInvalid):
        return False
    except Exception as e:
        logger.error(f"Error verifying channel access: {e}")
        return False

async def download_telegram_file(message, quality, channel_status_msg, filename):
    try:
        os.makedirs("temp", exist_ok=True)
        
        if message.video:
            file_id = message.video.file_id
            file_name = message.video.file_name or f"video_{quality}.mp4"
            total_size = message.video.file_size
        elif message.document:
            file_id = message.document.file_id
            file_name = message.document.file_name or f"file_{quality}.mkv"
            total_size = message.document.file_size
        else:
            return None
        
        safe_filename = file_name.replace(' ', '_').replace('[', '').replace(']', '')
        file_path = os.path.join("temp", safe_filename)
        
        # Get anime name from session
        session = user_sessions.get(message.from_user.id, {})
        anime_name = session.get("anime_name", "Unknown Anime")
        
        await channel_status_msg.edit_text(
            f"""<blockquote><b>📥 Downloading {quality} file...</b></blockquote>
<blockquote>File: {anime_name}</blockquote>""",
            parse_mode=ParseMode.HTML
        )
        
        status_msg = await message.reply_text(f"<blockquote><b>⏳ Downloading {quality} file...</b></blockquote>", parse_mode=ParseMode.HTML)
        
        start_time = time()
        last_update = start_time
        last_current = 0
        actual_total = total_size
        
        async def progress_callback(current, total):
            nonlocal last_update, last_current, actual_total
            now = time()
            
            if total > 0:
                actual_total = total
            
            if now - last_update < 10 and current != actual_total:
                return
                
            last_update = now
            elapsed = now - start_time
            chunk_size = current - last_current
            last_current = current
            
            if elapsed > 0:
                speed = current / elapsed
            else:
                speed = 0
                
            if actual_total > 0 and speed > 0:
                eta = (actual_total - current) / speed
            else:
                eta = 0
            
            if actual_total > 0:
                percent = round(current / actual_total * 100, 2)
                bar_length = 12
                filled_length = int(bar_length * percent // 100)
                bar = "█" * filled_length + "▒" * (bar_length - filled_length)
            else:
                percent = 0.0
                bar = "▒" * 12
            
            status_text = f"""
<blockquote>‣ <b>Anime Name :</b> <b><i>{anime_name}</i></b></blockquote>
<blockquote>‣ <b>Status :</b> <i>Downloading</i>
    <code>[{bar}]</code> {percent}%</blockquote> 
<blockquote>   ‣ <b>Size :</b> {convert_bytes(current)} / {convert_bytes(actual_total) if actual_total > 0 else 'Unknown'}
    ‣ <b>Speed :</b> {convert_bytes(speed)}/s
    ‣ <b>Time Took :</b> {convert_time(elapsed)}
    ‣ <b>Time Left :</b> {convert_time(eta) if eta > 0 else 'Calculating...'}</blockquote>
<blockquote>‣ <b>Quality :</b> <code>{quality}</code></blockquote>
"""
            
            try:
                await channel_status_msg.edit_text(status_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Error updating channel download status: {e}")
            
            try:
                await status_msg.edit_text(status_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Error updating private download status: {e}")
        
        await app.download_media(
            message=file_id,
            file_name=file_path,
            progress=progress_callback
        )
        
        await progress_callback(actual_total, actual_total)
        
        downloaded_size = os.path.getsize(file_path)
        if actual_total > 0 and downloaded_size != actual_total:
            logger.warning(f"Size mismatch: Expected {actual_total}, got {downloaded_size}")
            raise Exception(f"Download incomplete: {convert_bytes(downloaded_size)}/{convert_bytes(actual_total)}")
        
        asyncio.create_task(delete_after_delay(status_msg))
        
        logger.info(f"Downloaded {file_name} ({convert_bytes(downloaded_size)}) in {time() - start_time:.2f}s")
        return file_path
    except Exception as e:
        logger.error(f"Error downloading file: {traceback.format_exc()}")
        return None

async def process_quality(session, quality, video_msg, filename, owner_status_msg, main_post_msg, buttons, channel_status_msg):
    try:
        user_id = video_msg.from_user.id
        
        owner_quality_status = await app.send_message(
            video_msg.chat.id,
            f"<blockquote><b>⏳ Processing {quality} started...</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
        
        if cancel_requests.get(user_id, False):
            return quality, "Cancelled before start"
        
        file_path = await download_telegram_file(
            video_msg, 
            quality, 
            channel_status_msg,
            filename
        )
        if not file_path:
            return quality, "Download failed"
        
        if cancel_requests.get(user_id, False):
            if os.path.exists(file_path):
                os.remove(file_path)
            return quality, "Cancelled after download"
        
        processor = FileProcessor(
            client=app,
            message=video_msg,
            rep=None,
            file_path=file_path,
            quality=quality,
            status_message=owner_quality_status,
            user_id=user_id
        )
        processor.status_msg = channel_status_msg
        
        msg_id, file_size = await processor.process_and_upload()
        
        if processor.cancelled:
            try:
                await app.delete_messages(FILE_STORE, [msg_id])
            except:
                pass
            return quality, "Cancelled during processing"
        
        link = await create_download_link(msg_id)
        btn_text = f"{btn_formatter.get(quality, quality)} - {convert_bytes(file_size)}"
        
        if quality == '480p':
            buttons.append([InlineKeyboardButton(btn_text, url=link)])
        elif quality == '720p':
            if buttons and len(buttons[0]) == 1:
                buttons[0].append(InlineKeyboardButton(btn_text, url=link))
            else:
                buttons.append([InlineKeyboardButton(btn_text, url=link)])
        elif quality == '1080p':
            buttons.append([InlineKeyboardButton(btn_text, url=link)])
        
        await main_post_msg.edit_reply_markup(
            InlineKeyboardMarkup(buttons)
        )
        
        await channel_status_msg.edit_text(
            f"""<blockquote><b>✅ Processing completed for {quality}!</b></blockquote>
<blockquote>File: {session['anime_name']}</blockquote>""",
            parse_mode=ParseMode.HTML
        )
        
        asyncio.create_task(delete_after_delay(owner_quality_status))
        
        return quality, file_path
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return quality, "FloodWait error"
    except Exception as e:
        logger.error(f"Error processing {quality} video: {traceback.format_exc()}")
        return quality, f"{str(e)[:100]}"

@app.on_callback_query()
async def handle_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if user_id != OWNER_ID or user_id not in user_sessions:
        await safe_answer_callback(callback_query, "Session expired or unauthorized! Start again with /start")
        return
    
    session = user_sessions[user_id]
    
    if data.startswith("preview_"):
        quality = data.split("_")[1]
        await safe_answer_callback(callback_query, f"{quality.upper()} preview - Press SEND to publish", show_alert=True)
        return
    
    if data == "confirm_cancel":
        del user_sessions[user_id]
        try:
            await callback_query.message.delete()
        except:
            pass
        await safe_answer_callback(callback_query, "Operation cancelled")
        await client.send_message(user_id, "❌ Process cancelled. Start again with /start")
        return
    
    if data == "confirm_send":
        await safe_answer_callback(callback_query, "Processing...")
        
        try:
            target_channel = session.get("target_channel", TARGET_CHANNEL)
            
            db_access = await verify_channel_access(DB_CHANNEL)
            target_access = await verify_channel_access(target_channel)
            
            if not db_access or not target_access:
                error_msg = "❌ Bot not in channels or lacks permissions. Add bot as admin to both channels!"
                logger.error(error_msg)
                await client.send_message(user_id, error_msg)
                await safe_answer_callback(callback_query, "Channel access error", show_alert=True)
                return
            
            # Get anime name from session
            anime_name = session["anime_name"]
            season = session.get("season", "01")
            episode = session.get("episode", "01")
            
            caption = (
                f"<blockquote><b>➤ {anime_name}</b></blockquote>\n"
                "<b>──────────────</b>\n"
                f"<b>‣ Season :</b> {season}\n"
                f"<b>‣ Episode :</b> {episode}\n"
                f"<b>‣ Language :</b> {session['language']}\n"
                f"<b>‣ Codec :</b> {session['codec']}\n"
                f"<b>‣ Quality :</b> 480p, 720p, 1080p\n"
                "<b>──────────────</b>"
            )
            
            main_post_msg = await client.send_photo(
                chat_id=target_channel,
                photo=session["cover_photo"],
                caption=caption,
                parse_mode=ParseMode.HTML
            )
            
            channel_status_msg = await client.send_message(
                chat_id=target_channel,
                text="<blockquote><b>🚀 Processing started...</b></blockquote>",
                parse_mode=ParseMode.HTML
            )
            
            owner_status_msg = await callback_query.message.reply_text(
                "<blockquote><b>⏳ Processing videos sequentially, please wait...</b></blockquote>",
                parse_mode=ParseMode.HTML
            )
            
            errors = []
            buttons = []
            file_paths = []
            
            cancel_requests[user_id] = False
            
            for quality in ['480p', '720p', '1080p']:
                if cancel_requests.get(user_id, False):
                    errors.append("Operation cancelled by user")
                    break
                    
                video_msg = session["videos"].get(quality)
                if video_msg:
                    logger.info(f"Starting processing for {quality}")
                    result = await process_quality(
                        session, quality, video_msg, filename, 
                        owner_status_msg, main_post_msg, buttons, channel_status_msg
                    )
                    if isinstance(result, tuple):
                        quality_res, res = result
                        if isinstance(res, str):
                            errors.append(f"{quality}: {res}")
                        else:
                            file_paths.append(res)
                else:
                    errors.append(f"{quality}: No video provided")
            
            if errors:
                error_message = "❌ Errors occurred:\n" + "\n".join(errors)
                try:
                    await owner_status_msg.edit_text(error_message)
                except:
                    pass
                await safe_answer_callback(callback_query, "Errors occurred during publishing", show_alert=True)
                for file_path in file_paths:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except:
                        pass
                return
            
            await main_post_msg.edit_reply_markup(
                InlineKeyboardMarkup(buttons)
            )
            
            for file_path in file_paths:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except:
                    pass
            
            await channel_status_msg.edit_text(
                f"""<blockquote><b>✅ All processing completed!</b></blockquote>
<blockquote>File: {anime_name}</blockquote>""",
                parse_mode=ParseMode.HTML
            )
            asyncio.create_task(delete_after_delay(channel_status_msg, 5))
            
            del user_sessions[user_id]
            try:
                await callback_query.message.delete()
            except:
                pass
            try:
                await owner_status_msg.delete()
            except:
                pass
            
            await client.send_message(user_id, "✅ Content published successfully!")
            await safe_answer_callback(callback_query, "Published!")
        except Exception as e:
            logger.error(f"Error during publishing: {traceback.format_exc()}")
            await safe_answer_callback(callback_query, "Error occurred during publishing", show_alert=True)
            await client.send_message(user_id, f"❌ Error publishing content: {str(e)[:300]}")
        finally:
            if user_id in cancel_requests:
                cancel_requests[user_id] = False

async def startup_checks():
    logger.info("Running startup checks...")
    
    logger.info(f"DB_CHANNEL: {DB_CHANNEL}")
    if not await verify_channel_access(DB_CHANNEL):
        logger.error("❌ Bot not in DB_CHANNEL or lacks permissions!")
    
    logger.info(f"TARGET_CHANNEL: {TARGET_CHANNEL}")
    if not await verify_channel_access(TARGET_CHANNEL):
        logger.error("❌ Bot not in TARGET_CHANNEL or lacks permissions!")
    
    if await verify_channel_access(DB_CHANNEL) and await verify_channel_access(TARGET_CHANNEL):
        logger.info("✅ All channel access verified!")
    else:
        logger.error("❌ FIX REQUIRED: Add bot as admin to both channels with permissions")
    
    try:
        ffmpeg_version = subprocess.check_output(['ffmpeg', '-version'], stderr=subprocess.STDOUT, text=True)
        logger.info("✅ FFmpeg found:\n" + ffmpeg_version.split('\n')[0])
    except Exception as e:
        logger.error(f"❌ FFmpeg not found: {str(e)}")
    
    try:
        nvidia = subprocess.check_output(['nvidia-smi'], stderr=subprocess.STDOUT, text=True)
        logger.info("✅ NVIDIA GPU detected, hardware acceleration available")
    except:
        logger.info("ℹ️ No NVIDIA GPU detected, using software encoding")
    
    me = await app.get_me()
    logger.info(f"🤖 Bot username: @{me.username}")
    logger.info("🚀 Startup checks completed")

if __name__ == "__main__":
    os.makedirs("temp", exist_ok=True)
    
    for file in os.listdir("temp"):
        try:
            os.remove(os.path.join("temp", file))
        except:
            pass
    
    app.start()
    app.loop.run_until_complete(startup_checks())
    logger.info("✅ Bot started successfully")
    idle()
    app.stop()

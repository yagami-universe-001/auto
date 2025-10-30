import logging, asyncio, re
from uvloop import install
from asyncio import Lock
from socket import setdefaulttimeout
from faulthandler import enable as faulthandler_enable
from pymongo import MongoClient
from inspect import signature
from colorama import Fore, Style, init
from tzlocal import get_localzone
from os import environ
from dotenv import load_dotenv, dotenv_values
from pyrogram import Client as tgClient, enums
from pyrogram.errors import FloodWait
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from logging import getLogger, ERROR, INFO, FileHandler, StreamHandler, basicConfig, error as log_error, info as log_info
from time import time
from bot.helper.extra.help_string import *

faulthandler_enable()
install()
setdefaulttimeout(600)
getLogger("pymongo").setLevel(ERROR)
getLogger("httpx").setLevel(ERROR)
bot_start_time = time()


# Global variable
user_data = {}
handler_dict = {}
broadcast_handler_dict = {}
user_handler_dict = {}
deldbfiles_handler_dict = {}
HOSTING_SERVER = None
skip_iron_ids = {}
is_indexing_active = False


queue_dict_lock = Lock()

def validate_and_format_url(url):
    # Check if the URL starts with http:// or https://
    if url.startswith("http://"):
        # Regex for validating IPv4 address and port
        ipv4_pattern = r'^(http://)(\d{1,3}\.){3}\d{1,3}:\d{1,5}/?$'
        match = re.match(ipv4_pattern, url)
        
        if match:
            # If it matches, ensure it ends with a '/'
            if not url.endswith('/'):
                url += '/'
            return True, url
        else:
            return False, "Error: Invalid HTTP URL. Must be in the format http://<IPv4>:<PORT>/"
    
    elif url.startswith("https://"):
        # Regex for validating the general https URL
        https_pattern = r'^(https://[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*(:\d{1,5})?)/?$'
        match = re.match(https_pattern, url)
        
        if match:
            # If it matches, ensure it ends with a '/'
            if not url.endswith('/'):
                url += '/'
            return True, str(url)
        else:
            return False, "Error: Invalid HTTPS URL."
    
    return False, "Error: URL must start with http:// or https://"

# Initialize colorama for cross-platform support
init(autoreset=True)

# Custom Formatter for Colored Logs
class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": f"{Style.BRIGHT}{Fore.RED}",
    }
    RESET = Style.RESET_ALL

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.msg = f"{color}{record.msg}{self.RESET}"
        return super().format(record)

# Logging Configuration
basicConfig(
    format="[%(asctime)s] [%(levelname)s] - %(message)s",  # Add [%(filename)s:%(lineno)d] for debugging
    datefmt="%d-%b-%y %I:%M:%S %p",
    level=INFO,
    handlers=[
        FileHandler("log.txt"),
        StreamHandler()
    ]
)

# Replace StreamHandler's formatter with ColorFormatter
for handler in logging.getLogger().handlers:
    if isinstance(handler, StreamHandler):
        handler.setFormatter(ColorFormatter("[%(asctime)s] [%(levelname)s] - %(message)s"))

# Set specific log levels for noisy libraries
getLogger("pyrogram").setLevel(ERROR)
getLogger("aiohttp").setLevel(ERROR)
getLogger("httpx").setLevel(ERROR)
getLogger("imdbpy").setLevel(ERROR)
getLogger("aiohttp.web").setLevel(ERROR)

# Main Logger
LOGGER = logging.getLogger(__name__)

load_dotenv('config.env', override=True)

BOT_TOKEN = environ.get('BOT_TOKEN', '')
if len(BOT_TOKEN) == 0:
    log_error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

bot_id = BOT_TOKEN.split(':', 1)[0]

DATABASE_URL = environ.get('DATABASE_URL', "")
if len(DATABASE_URL) == 0:
    DATABASE_URL = ''

if DATABASE_URL:
    conn = MongoClient(DATABASE_URL)
    db = conn.HUB4VF
    current_config = dict(dotenv_values("config.env"))
    old_config = db.settings.deployConfig.find_one({"_id": bot_id})
    if old_config is None:
        db.settings.deployConfig.replace_one(
            {"_id": bot_id}, current_config, upsert=True
        )
    else:
        del old_config["_id"]
    if old_config and old_config != current_config:
        db.settings.deployConfig.replace_one(
            {"_id": bot_id}, current_config, upsert=True
        )
    elif config_dict := db.settings.config.find_one({"_id": bot_id}):
        del config_dict["_id"]
        for key, value in config_dict.items():
            environ[key] = str(value)
    if pf_dict := db.settings.files.find_one({"_id": bot_id}):
        del pf_dict["_id"]
        for key, value in pf_dict.items():
            if value:
                file_ = key.replace("__", ".")
                with open(file_, "wb+") as f:
                    f.write(value)
    conn.close()
    BOT_TOKEN = environ.get("BOT_TOKEN", "")
    bot_id = BOT_TOKEN.split(":", 1)[0]
    DATABASE_URL = environ.get("DATABASE_URL", "")
else:
    config_dict = {}

FILES_DATABASE_URL = environ.get("FILES_DATABASE_URL", "")
if len(FILES_DATABASE_URL) == 0:
    #log_error("FILES_DATABASE_URL variable is missing! Exiting now")
    #exit(1)
    FILES_DATABASE_URL = DATABASE_URL

OWNER_ID = environ.get('OWNER_ID', '')
if len(OWNER_ID) == 0:
    log_error("OWNER_ID variable is missing! Exiting now")
    exit(1)
else:
    OWNER_ID = int(OWNER_ID)

TELEGRAM_API = environ.get('TELEGRAM_API', '')
if len(TELEGRAM_API) == 0:
    log_error("TELEGRAM_API variable is missing! Exiting now")
    exit(1)
else:
    TELEGRAM_API = int(TELEGRAM_API)

TELEGRAM_HASH = environ.get('TELEGRAM_HASH', '')
if len(TELEGRAM_HASH) == 0:
    log_error("TELEGRAM_HASH variable is missing! Exiting now")
    exit(1)

DATABASE_CHANNEL = environ.get("DATABASE_CHANNEL", "")
if len(DATABASE_CHANNEL) == 0:
    log_error("DATABASE_CHANNEL variable is missing! Exiting now")
    exit(1)
else:
    DATABASE_CHANNEL = str(DATABASE_CHANNEL)

PORT = environ.get('PORT', '')
if len(PORT) == 0:
    PORT = 8080
else:
    PORT = int(PORT)

BOT_BASE_URL = environ.get("BOT_BASE_URL", "")
if len(BOT_BASE_URL) == 0:
    log_error("BOT_BASE_URL variable is missing! Exiting now")
    exit(1)
else:
    is_valid, BOT_BASE_URL = validate_and_format_url(str(BOT_BASE_URL))
    if is_valid:
        BOT_BASE_URL = str(BOT_BASE_URL)
    else:
        LOGGER.error(BOT_BASE_URL)
        exit(1)

LOG_CHANNEL = environ.get('LOG_CHANNEL', '')
if len(LOG_CHANNEL) == 0:
    log_error("LOG_CHANNEL variable is missing! Exiting now")
    exit(1)
else:
    LOG_CHANNEL = int(LOG_CHANNEL)

CMD_SUFFIX = environ.get("CMD_SUFFIX", "")

SUDO_USERS = environ.get('SUDO_USERS', '')
if len(SUDO_USERS) != 0:
    aid = SUDO_USERS.split()
    for id_ in aid:
        user_data[int(id_.strip())] = {'is_sudo': True}

def irontgClient(*args, **kwargs):
    if 'max_concurrent_transmissions' in signature(tgClient.__init__).parameters:
        kwargs['max_concurrent_transmissions'] = 1000
    return tgClient(*args, **kwargs)

IS_PREMIUM_USER = False
user_bot = ''
USER_SESSION_STRING = environ.get('USER_SESSION_STRING', '')
if len(USER_SESSION_STRING) != 0:
    log_info("Creating client from USER_SESSION_STRING")
    try:
        user_bot = irontgClient('user', TELEGRAM_API, TELEGRAM_HASH, session_string=USER_SESSION_STRING,
                        parse_mode=enums.ParseMode.HTML, no_updates=True).start()
        IS_PREMIUM_USER = user_bot.me.is_premium
    except Exception as e:
        log_error(f"Failed making client from USER_SESSION_STRING : {e}")
        user_bot = ''

FSUB_IDS = environ.get('FSUB_IDS', '')
if len(FSUB_IDS) == 0:
    FSUB_IDS = ''

OWNER_CONTACT_LNK = environ.get("OWNER_CONTACT_LNK", "") #owner contact link for user
if len(OWNER_CONTACT_LNK) == 0:
    OWNER_CONTACT_LNK = "https://t.me/ContactownerHUB4VF_bot"

MAIN_CHNL_USRNM = environ.get("MAIN_CHNL_USRNM", "") # your main channel username without @
if MAIN_CHNL_USRNM == 0:
    LOGGER.warning("Update MAIN_CHNL_USRNM Variable")
    MAIN_CHNL_USRNM = 'HUB4VF'

UPDT_BTN_URL = environ.get('UPDT_BTN_URL', '') #if you set url then bot will add update button with file else no button generate

REPO_URL = environ.get("REPO_URL", "")
if len(REPO_URL) == 0:
    REPO_URL = "https://github.com/"
else:
    is_valid, url = validate_and_format_url(REPO_URL)
    if is_valid:
        REPO_URL = REPO_URL
    else:
        LOGGER.warning("REPO_URL is Invalid, using defult REPO_URL")
        REPO_URL = "https://github.com/"
############################################################
            # Image Vlaues
############################################################

START_PICS = environ.get('START_PICS', '')
if len(START_PICS) == 0:
    Warning("START_PICS Not Found, Using defult value")
    START_PICS = "https://jpcdn.it/img/9c1078d5bb5ff7d526eae590db3d3d27.jpg"

SPELL_IMG = environ.get("SPELL_IMG", "")
if len(SPELL_IMG) == 0:
    SPELL_IMG = "https://jpcdn.it/img/e6680b19146911fafe31587395f7ae4b.jpg"

############################################################
            # Image Vlaues
############################################################





############################################################
            # Bool Vlaues
############################################################

USE_CAPTION_FILTER = environ.get("USE_CAPTION_FILTER", "True")
USE_CAPTION_FILTER = USE_CAPTION_FILTER.lower() == 'true'

IMDB_RESULT = environ.get("IMDB_RESULT", "False")
IMDB_RESULT = IMDB_RESULT.lower() == 'true'

LONG_IMDB_DESCRIPTION = environ.get("LONG_IMDB_DESCRIPTION", "False")
LONG_IMDB_DESCRIPTION = LONG_IMDB_DESCRIPTION.lower() == 'true'

NO_RESULTS_MSG = environ.get("NO_RESULTS_MSG", "True")
NO_RESULTS_MSG = NO_RESULTS_MSG.lower() == 'true'

SET_COMMANDS = environ.get("SET_COMMANDS", "True")
SET_COMMANDS = SET_COMMANDS.lower() == 'true'

REQ_JOIN_FSUB = environ.get("REQ_JOIN_FSUB", "False")
REQ_JOIN_FSUB = REQ_JOIN_FSUB.lower() == 'true'

FILE_SECURE_MODE = environ.get("FILE_SECURE_MODE", "False")
FILE_SECURE_MODE = FILE_SECURE_MODE.lower() == 'true'
############################################################
            # Bool Vlaues
############################################################




############################################################
            # Text Formate Vlaues
############################################################

START_TEXT = environ.get("START_TEXT", "")
if len(START_TEXT) == 0:
    START_TEXT = IRON_START_TEXT


RESULT_TEXT = environ.get("RESULT_TEXT", "")
if len(RESULT_TEXT) == 0:
    RESULT_TEXT = IRON_RESULT_TEXT


CUSTOM_FILE_CAPTION = environ.get("CUSTOM_FILE_CAPTION", "")
if len(CUSTOM_FILE_CAPTION) == 0:
    CUSTOM_FILE_CAPTION = IRON_CUSTOM_FILE_CAPTION


IMDB_TEMPLATE_TXT = environ.get("IMDB_TEMPLATE_TXT", "")
if len(IMDB_TEMPLATE_TXT) == 0:
    IMDB_TEMPLATE_TXT = IRON_IMDB_TEMPLATE_TXT 


ALRT_TXT = environ.get("ALRT_TXT", "")
if len(ALRT_TXT) == 0:
    ALRT_TXT = IRON_ALRT_TXT 


ABOUT_TEXT = environ.get("ABOUT_TEXT", "")
if len(ABOUT_TEXT) == 0:
    ABOUT_TEXT = IRON_ABOUT_TEXT 

CHK_MOV_ALRT = environ.get("CHK_MOV_ALRT", "")
if len(CHK_MOV_ALRT) == 0:
    CHK_MOV_ALRT = IRON_CHK_MOV_ALRT 

CUDNT_FND = environ.get("CUDNT_FND", "")
if len(CUDNT_FND) == 0:
    CUDNT_FND = IRON_CUDNT_FND 

FILE_NOT_FOUND = environ.get("FILE_NOT_FOUND", "")
if len(FILE_NOT_FOUND) == 0:
    FILE_NOT_FOUND =  IRON_FILE_NOT_FOUND 

OLD_ALRT_TXT = environ.get("OLD_ALRT_TXT", "")
if len(OLD_ALRT_TXT) == 0:
    OLD_ALRT_TXT = IRON_OLD_ALRT_TXT 

NORSLTS = environ.get("NORSLTS", "")
if len(NORSLTS) == 0:
    NORSLTS = IRON_NORSLTS 


MOV_NT_FND = environ.get("MOV_NT_FND", "")
if len(MOV_NT_FND) == 0:
    MOV_NT_FND = IRON_MOV_NT_FND 

DISCLAIMER_TXT = environ.get('DISCLAIMER_TXT', "")
if len(DISCLAIMER_TXT) == 0:
    DISCLAIMER_TXT = IRON_DISCLAIMER_TXT 

SOURCE_TXT = environ.get("SOURCE_TXT", "")
if len(SOURCE_TXT) == 0:
    SOURCE_TXT = IRON_SOURCE_TXT 

HELP_TXT = environ.get("HELP_TXT", "")
if len(HELP_TXT) == 0:
    HELP_TXT = IRON_HELP_TXT 

ADMIN_CMD_TXT = environ.get("ADMIN_CMD_TXT", "")
if len(ADMIN_CMD_TXT) == 0:
    ADMIN_CMD_TXT = IRON_ADMIN_CMD_TXT 
############################################################
             # Text Formate Vlaues
############################################################
MAX_LIST_ELM = environ.get("MAX_LIST_ELM", "10")
if len(MAX_LIST_ELM) == 0:
    MAX_LIST_ELM = None

UPSTREAM_REPO = environ.get("UPSTREAM_REPO", "")
if len(UPSTREAM_REPO) == 0:
    UPSTREAM_REPO = ""

UPSTREAM_BRANCH = environ.get("UPSTREAM_BRANCH", "")
if len(UPSTREAM_BRANCH) == 0:
    UPSTREAM_BRANCH = "main"

############################################################
##############  DO NOT EDIT BELOW THIS LINE  ###############
############################################################

############################################################
##################### ADVACE CONFIG  #######################
############################################################

USENEWINVTLINKS = environ.get("USENEWINVTLINKS", "False")
USENEWINVTLINKS = USENEWINVTLINKS.lower() == 'true'
if REQ_JOIN_FSUB == False:
    USENEWINVTLINKS = False

AUTODELICMINGUSERMSG = environ.get("AUTODELICMINGUSERMSG", "True") # auto delete user query message make on or off
AUTODELICMINGUSERMSG = AUTODELICMINGUSERMSG.lower() == 'true'

AUTO_DEL_FILTER_RESULT_MSG = environ.get("AUTO_DEL_FILTER_RESULT_MSG", "True")  # auto delete bot auto_filter msg on or off
AUTO_DEL_FILTER_RESULT_MSG = AUTO_DEL_FILTER_RESULT_MSG.lower() == 'true'

AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT = environ.get("AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT", "") # auto delete bot auto_filter msg in seconds
if len(AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT) == 0:
    AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT = 300
else:
    AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT = int(AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT) if AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT.isdigit() else 300

AUTO_FILE_DELETE_MODE = environ.get("AUTO_FILE_DELETE_MODE", "True")
AUTO_FILE_DELETE_MODE = AUTO_FILE_DELETE_MODE.lower() == 'true'


AUTO_FILE_DELETE_MODE_TIMEOUT = environ.get("AUTO_FILE_DELETE_MODE_TIMEOUT", "") 
if len(AUTO_FILE_DELETE_MODE_TIMEOUT) == 0:
    AUTO_FILE_DELETE_MODE_TIMEOUT = 300
else: 
    AUTO_FILE_DELETE_MODE_TIMEOUT = int(AUTO_FILE_DELETE_MODE_TIMEOUT) if AUTO_FILE_DELETE_MODE_TIMEOUT.isdigit() else 300

def is_number(value):
    try:
        # Try converting to an int first
        int_value = int(value)
        return 'int'
    except ValueError:
        try:
            # If int conversion fails, try converting to a float
            float_value = float(value)
            return 'float'
        except ValueError:
            # If both conversions fail, it's invalid
            return 'invalid'

TOKEN_TIMEOUT = environ.get("TOKEN_TIMEOUT", "")
TOKEN_TIMEOUT = int(TOKEN_TIMEOUT) if TOKEN_TIMEOUT.isdigit() else ""

SHORT_URL_API = environ.get("SHORT_URL_API", "")
if len(SHORT_URL_API) == 0:
    SHORT_URL_API = ''



############################################################
##################### ADVACE CONFIG  #######################
############################################################
config_dict = {
    'ABOUT_TEXT': ABOUT_TEXT,
    'ADMIN_CMD_TXT': ADMIN_CMD_TXT,
    'ALRT_TXT': ALRT_TXT,
    'AUTO_DEL_FILTER_RESULT_MSG': AUTO_DEL_FILTER_RESULT_MSG,
    'AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT': AUTO_DEL_FILTER_RESULT_MSG_TIMEOUT,
    'AUTO_FILE_DELETE_MODE': AUTO_FILE_DELETE_MODE,
    'AUTO_FILE_DELETE_MODE_TIMEOUT': AUTO_FILE_DELETE_MODE_TIMEOUT,
    'AUTODELICMINGUSERMSG': AUTODELICMINGUSERMSG,
    'BOT_TOKEN': BOT_TOKEN,
    "BOT_BASE_URL": BOT_BASE_URL,
    'CHK_MOV_ALRT': CHK_MOV_ALRT,
    'CMD_SUFFIX': CMD_SUFFIX,
    'CUDNT_FND': CUDNT_FND,
    'CUSTOM_FILE_CAPTION': CUSTOM_FILE_CAPTION,
    'DATABASE_CHANNEL': DATABASE_CHANNEL,
    'DATABASE_URL': DATABASE_URL,
    'DISCLAIMER_TXT': DISCLAIMER_TXT,
    'FILES_DATABASE_URL': FILES_DATABASE_URL,
    'FILE_NOT_FOUND': FILE_NOT_FOUND,
    "FILE_SECURE_MODE": FILE_SECURE_MODE,
    'FSUB_IDS': FSUB_IDS,
    'HELP_TXT': HELP_TXT,
    'IMDB_RESULT': IMDB_RESULT,
    'IMDB_TEMPLATE_TXT': IMDB_TEMPLATE_TXT,
    'LOG_CHANNEL': LOG_CHANNEL,
    'LONG_IMDB_DESCRIPTION': LONG_IMDB_DESCRIPTION,
    'MAX_LIST_ELM': MAX_LIST_ELM,
    'MAIN_CHNL_USRNM': MAIN_CHNL_USRNM,
    'MOV_NT_FND': MOV_NT_FND,
    'NO_RESULTS_MSG': NO_RESULTS_MSG,
    'NORSLTS': NORSLTS,
    'OLD_ALRT_TXT': OLD_ALRT_TXT,
    'OWNER_ID': OWNER_ID,
    'OWNER_CONTACT_LNK': OWNER_CONTACT_LNK,
    'PORT': PORT,
    'REPO_URL': REPO_URL,
    'RESULT_TEXT': RESULT_TEXT,
    'REQ_JOIN_FSUB': REQ_JOIN_FSUB,
    'SET_COMMANDS': SET_COMMANDS,
    'SHORT_URL_API': SHORT_URL_API,
    'SOURCE_TXT': SOURCE_TXT,
    'SPELL_IMG': SPELL_IMG,
    'START_PICS': START_PICS,
    'START_TEXT': START_TEXT,
    'SUDO_USERS': SUDO_USERS,
    'TOKEN_TIMEOUT': TOKEN_TIMEOUT,
    'TELEGRAM_API': TELEGRAM_API,
    'TELEGRAM_HASH': TELEGRAM_HASH,
    'USE_CAPTION_FILTER': USE_CAPTION_FILTER,
    'USENEWINVTLINKS': USENEWINVTLINKS,
    'USER_SESSION_STRING': USER_SESSION_STRING,
    'UPSTREAM_REPO': UPSTREAM_REPO,
    'UPSTREAM_BRANCH': UPSTREAM_BRANCH,
    'UPDT_BTN_URL': UPDT_BTN_URL,
}

log_info("Creating client from BOT_TOKEN")

try:
    bot = irontgClient(
        'bot', 
        TELEGRAM_API, 
        TELEGRAM_HASH, 
        bot_token=BOT_TOKEN, 
        workers=1000
    )
    bot.start()
except FloodWait as e:
    LOGGER.error(f"FloodWait triggered: Must wait {e.value} seconds.")
    asyncio.sleep(e.value)  # Wait for the specified duration
    bot.start()
bot_loop = bot.loop
bot_name = bot.me.username
scheduler = AsyncIOScheduler(timezone=str(get_localzone()), event_loop=bot_loop)
